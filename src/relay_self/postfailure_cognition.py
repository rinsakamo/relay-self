"""S24: explicit post-failure cognition from separate caller World evidence.

This bounded projection does not authenticate physical observations, schedule
epochs, replace Current Intent, authorize Actions, or learn a new policy.
"""
from __future__ import annotations

from dataclasses import dataclass

from adapters.mineflayer.execution import WorldConsequence, WorldConsequenceStatus
from relay_self.action import ActionLifecycle, ActionState
from relay_self.action_supervision import ActionSupervisor
from relay_self.attention import AttentionCandidate, AttentionCriterion, select_attention
from relay_self.belief import (
    BeliefCriterion,
    BeliefEvidence,
    EvidenceRelation,
    PropositionKey,
    assess_belief,
)
from relay_self.concept import (
    ConceptCriterion,
    ConceptFeature,
    ConceptKey,
    ConceptStatus,
    classify_concept,
    concept_candidate_from_belief,
)
from relay_self.epoch_continuation import read_retained_preference
from relay_self.epoch_plan import (
    EpochBinding,
    EpochWorkItem,
    PlannedDecisionEpochResult,
    compile_epoch_plan,
    coordinate_planned_epoch,
)
from relay_self.execution_admission import (
    AdmissionDecisionStatus,
    AdmissionPolicy,
    ExecutionAdmissionCriterion,
    admit_control_candidate,
)
from relay_self.execution_descriptor import S17_DESCRIPTOR_SET, s17_capability_plan
from relay_self.intent import IntentCommitment
from relay_self.learning import LearningPreferenceState
from relay_self.planning import (
    PlanningCriterion,
    PlanningDirection,
    plan_candidate_from_prediction,
    select_plan,
)
from relay_self.prediction import (
    StateVariable,
    TransitionRule,
    predict_transition,
    prediction_state_from_concept,
)
from relay_self.provenance import Provenance
from relay_self.route_adjudication import (
    RouteCriterion,
    adjudicate_routes,
    control_candidate_from_route_decision,
)
from relay_self.skill import SkillExecution, SkillState


class InvalidPostFailureEvidence(ValueError):
    """World evidence, retained revision, or owner lineage is not admissible."""


@dataclass(frozen=True, slots=True)
class PostFailureWorldEvidence:
    """Distinct caller-supplied observation after the S23 Action3 consequence."""

    evidence_id: str
    action_id: str
    binding_id: str
    session_id: str
    consequence_provenance: Provenance
    threat_clearance_cm: int
    observed_at_ns: int
    provenance: Provenance

    def __post_init__(self) -> None:
        for field in ("evidence_id", "action_id", "binding_id", "session_id"):
            _name(field, getattr(self, field))
        for field in ("consequence_provenance", "provenance"):
            _provenance(getattr(self, field))
        if (
            not isinstance(self.threat_clearance_cm, int)
            or isinstance(self.threat_clearance_cm, bool)
            or self.threat_clearance_cm < 0
        ):
            raise InvalidPostFailureEvidence("threat_clearance_cm must be >= 0 integer")
        _time(self.observed_at_ns)


@dataclass(frozen=True, slots=True)
class PostFailureEpochTrace:
    world_evidence: PostFailureWorldEvidence
    retained_revision: int
    wait_score: int
    move_score: int
    selected_candidate: str
    admission_status: AdmissionDecisionStatus
    epoch: PlannedDecisionEpochResult
    stage_ids: tuple[str, ...]
    source_provenance: tuple[Provenance, ...]


def run_explicit_postfailure_epoch(
    supervisor: ActionSupervisor,
    action3: ActionLifecycle,
    consequence3: WorldConsequence,
    recovery_skill: SkillExecution,
    intent: IntentCommitment,
    owner_snapshot: LearningPreferenceState,
    evidence: PostFailureWorldEvidence,
    *,
    at_ns: int,
    provenance: Provenance,
) -> PostFailureEpochTrace:
    """Run fresh ATT-BLF-CNC-PRD-PLAN-ROUTE-ADMISSION, explicitly once.

    The caller supplies a post-Action3 observation. WAIT score is 2*risk if
    clearance <= 100cm and risk if clearance > 100cm. MOVE_AWAY score = 7.
    This fixed comparison rule is an explicit fixture policy, not learned.
    """
    if not isinstance(supervisor, ActionSupervisor):
        raise InvalidPostFailureEvidence("requires ActionSupervisor")
    if not isinstance(action3, ActionLifecycle) or not action3.is_current_snapshot:
        raise InvalidPostFailureEvidence("requires current Action3 snapshot")
    if action3.state is not ActionState.OUTCOME:
        raise InvalidPostFailureEvidence("Action3 must be terminal OUTCOME")
    if supervisor.get(action3.action_id) is not action3:
        raise InvalidPostFailureEvidence("Action3 is not current supervised owner")
    if not isinstance(consequence3, WorldConsequence):
        raise InvalidPostFailureEvidence("requires typed WorldConsequence")
    if consequence3.status is not WorldConsequenceStatus.EXECUTED:
        raise InvalidPostFailureEvidence("requires known executed consequence")
    if not isinstance(recovery_skill, SkillExecution):
        raise InvalidPostFailureEvidence("requires current recovery Skill")
    if not recovery_skill.is_current_snapshot or recovery_skill.state is not SkillState.STARTED:
        raise InvalidPostFailureEvidence("recovery Skill must remain current STARTED")
    if not isinstance(intent, IntentCommitment):
        raise InvalidPostFailureEvidence("requires Current Intent owner")
    current = intent.current_intent
    if current is None or intent.pending_reconsideration is not None:
        raise InvalidPostFailureEvidence("Current Intent must remain active without pending")
    if not isinstance(evidence, PostFailureWorldEvidence):
        raise InvalidPostFailureEvidence("requires typed post-failure evidence")
    if (
        action3.skill_execution_id != recovery_skill.execution_id
        or action3.intent_id != current.intent_id
        or recovery_skill.intent_id != current.intent_id
        or action3.action_id != evidence.action_id
        or consequence3.action_id != evidence.action_id
        or consequence3.binding_id != evidence.binding_id
        or consequence3.session_id != evidence.session_id
        or consequence3.provenance != evidence.consequence_provenance
        or action3.events[-1].provenance != consequence3.provenance
        or evidence.provenance == consequence3.provenance
    ):
        raise InvalidPostFailureEvidence("World/Skill/Action/Intent lineage mismatch")
    if not isinstance(owner_snapshot, LearningPreferenceState):
        raise InvalidPostFailureEvidence("requires typed retained snapshot")
    _time(at_ns)
    _provenance(provenance)
    if evidence.observed_at_ns <= action3.events[-1].at_ns:
        raise InvalidPostFailureEvidence("fresh observation must follow Action3 outcome")
    if at_ns < evidence.observed_at_ns:
        raise InvalidPostFailureEvidence("epoch cannot predate observation")
    if supervisor.last_at_ns is not None and at_ns < supervisor.last_at_ns:
        raise InvalidPostFailureEvidence("epoch clock precedes supervisor clock")

    # Explicit owner-verified retained read; no learning or commit happens here.
    read = read_retained_preference(
        owner_snapshot, owner_snapshot, required_target_id="risk_weight",
        expected_revision=owner_snapshot.revision, provenance=provenance,
    )
    if read.revision != 1 or read.snapshot.value != 4 or read.last_update is None:
        raise InvalidPostFailureEvidence("S24 requires frozen S19 retained rev1/value4")
    outputs: dict[str, object] = {}
    proposition = PropositionKey("world", "zombie-1", "detected")
    belief_evidence = BeliefEvidence(
        evidence.evidence_id, proposition, EvidenceRelation.SUPPORT,
        evidence.provenance,
    )
    focus = AttentionCandidate(
        evidence.evidence_id, f"world-observation:{evidence.evidence_id}",
        evidence.provenance, focus_keys=("zombie-1",),
    )
    attention_rule = AttentionCriterion("s24-focus-threat", focus_key="zombie-1")
    belief_rule = BeliefCriterion("s24-world-detected", proposition)
    concept_rule = ConceptCriterion(
        criterion_id="s24-detected-threat-concept",
        concept=ConceptKey("spatial", "detected_threat"),
        required_features=(
            ConceptFeature("belief_status", "supported"),
            ConceptFeature("proposition", proposition.canonical),
        ),
    )
    wait_score = 2 * read.snapshot.value if evidence.threat_clearance_cm <= 100 else read.snapshot.value
    move_score = 7
    preconditions = (StateVariable("concept", "spatial:detected_threat"),)
    wait_rule = TransitionRule(
        rule_id="s24-wait", preconditions=preconditions,
        assignments=(StateVariable("action_kind", "wait"),),
        provenance=Provenance("s24-fixed-policy", "wait-transition"),
    )
    move_rule = TransitionRule(
        rule_id="s24-move", preconditions=preconditions,
        assignments=(
            StateVariable("action_kind", "move_away"),
            StateVariable("comparison_score", move_score),
        ),
        provenance=Provenance("s24-fixed-policy", "move-transition"),
    )
    plan_rule = PlanningCriterion(
        "s24-minimize-explicit-comparison",
        feature_key="comparison_score", direction=PlanningDirection.MINIMIZE,
    )
    route_rule = RouteCriterion("s24-postfailure-plan-route", allow_single_source=True)
    admission_rule = ExecutionAdmissionCriterion(
        criterion_id="s24-postfailure-fresh-admission",
        policy=AdmissionPolicy.CURRENT_INTENT_ALLOW_LIST,
        required_intent_id=current.intent_id,
        allowed_candidate_refs=("WAIT", "MOVE_AWAY"),
    )

    def att_step():
        outputs["attention"] = select_attention((focus,), attention_rule)
        if outputs["attention"].candidate_ids != (evidence.evidence_id,):
            raise InvalidPostFailureEvidence("fresh evidence not attended")
        return None

    def blf_step():
        if outputs["attention"].selected[0].provenance != belief_evidence.provenance:
            raise InvalidPostFailureEvidence("ATT and BLF evidence differ")
        outputs["belief"] = assess_belief((belief_evidence,), belief_rule)
        return None

    def cnc_step():
        outputs["concept"] = classify_concept(
            concept_candidate_from_belief(
                outputs["belief"], candidate_id="s24-belief:detected-threat",
                payload_ref="transient:s24-detected-threat",
                provenance=provenance,
            ),
            concept_rule,
        )
        if outputs["concept"].status is not ConceptStatus.MATCHED:
            raise InvalidPostFailureEvidence("threat concept is not supported")
        return None

    def wait_step():
        source = prediction_state_from_concept(
            outputs["concept"], state_id="s24-after-recovery",
            extra_variables=(
                StateVariable("comparison_score", wait_score),
                StateVariable("risk_weight", read.snapshot.value),
                StateVariable("threat_clearance_cm", evidence.threat_clearance_cm),
            ),
            provenance=provenance,
        )
        outputs["prediction_input"] = source
        outputs["wait"] = predict_transition(source, wait_rule)
        return None

    def move_step():
        outputs["move"] = predict_transition(outputs["prediction_input"], move_rule)
        return None

    def plan_step():
        outputs["plan"] = select_plan(
            (
                plan_candidate_from_prediction(
                    outputs["wait"], candidate_id="WAIT",
                    feature_keys=("comparison_score",), provenance=provenance,
                ),
                plan_candidate_from_prediction(
                    outputs["move"], candidate_id="MOVE_AWAY",
                    feature_keys=("comparison_score",), provenance=provenance,
                ),
            ),
            plan_rule,
        )
        return None

    def route_step():
        outputs["route"] = adjudicate_routes(
            outputs["plan"], None, route_rule, provenance=provenance,
        )
        outputs["control"] = control_candidate_from_route_decision(outputs["route"])
        return None

    def admission_step():
        outputs["admission"] = admit_control_candidate(
            outputs["control"], outputs["route"], intent, admission_rule,
            provenance=provenance,
        )
        return None

    work = (
        ("s24-att", "att.select", att_step),
        ("s24-blf", "blf.assess", blf_step),
        ("s24-cnc", "cnc.classify", cnc_step),
        ("s24-prd-wait", "prd.predict", wait_step),
        ("s24-prd-move", "prd.predict", move_step),
        ("s24-plan", "plan.select", plan_step),
        ("s24-route", "route.adjudicate", route_step),
        ("s24-admit", "execution.admit_candidate", admission_step),
    )
    due = tuple(EpochWorkItem(w, o, "caller:s24:postfailure") for w, o, _ in work)
    bindings = tuple(EpochBinding(w, o, fn) for w, o, fn in work)
    plan = compile_epoch_plan(
        s17_capability_plan(
            enabled_ids=frozenset(("ATT", "BLF", "CNC", "PRD", "PLAN", "ROUTE", "ADMISSION"))
        ),
        S17_DESCRIPTOR_SET, due_items=due, bindings=bindings,
    )
    epoch = coordinate_planned_epoch(
        supervisor, plan, bindings=bindings, at_ns=at_ns, provenance=provenance,
    )
    selection = outputs["plan"].selected
    if selection is None:
        raise InvalidPostFailureEvidence("no plan selected")
    if outputs["admission"].status is not AdmissionDecisionStatus.ADMITTED:
        raise InvalidPostFailureEvidence("S24 admission not ADMITTED")
    return PostFailureEpochTrace(
        world_evidence=evidence, retained_revision=read.revision,
        wait_score=wait_score, move_score=move_score,
        selected_candidate=selection.candidate_id,
        admission_status=outputs["admission"].status,
        epoch=epoch, stage_ids=epoch.executed_work_ids,
        source_provenance=outputs["prediction_input"].source_provenance,
    )


def _name(field: str, value: object) -> None:
    if not isinstance(value, str) or not value or value != value.strip() or any(
        char.isspace() for char in value
    ):
        raise InvalidPostFailureEvidence(f"{field} must be a structured identifier")


def _time(value: object) -> None:
    if not isinstance(value, int) or isinstance(value, bool) or value < 0:
        raise InvalidPostFailureEvidence("time must be non-negative integer")


def _provenance(value: object) -> None:
    if not isinstance(value, Provenance):
        raise InvalidPostFailureEvidence("provenance must be typed Provenance")
