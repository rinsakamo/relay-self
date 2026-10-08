from __future__ import annotations

import asyncio
import json
from collections import deque
from dataclasses import replace
from pathlib import Path

import pytest

from adapters.mineflayer.action_outcome import interpret_world_consequence
from adapters.mineflayer.execution import (
    WorldConsequenceStatus,
    build_mineflayer_command,
    execute_mineflayer_command,
)
from adapters.mineflayer.python_protocol import (
    MINEFLAYER_NEARBY_ENTITY_MAX_DISTANCE,
    MINEFLAYER_NEARBY_ENTITY_MAX_ENTITIES,
    MINEFLAYER_NEARBY_ENTITY_SOURCE_SCOPE,
    MINEFLAYER_VERSION,
    MineflayerAdapterStarted,
    MineflayerEffectResult,
    MineflayerLaunchConfig,
    MineflayerNearbyEntitiesCoverage,
    MineflayerObservation,
    MineflayerPosition,
    MineflayerSnapshot,
)
from relay_self.action import ActionState
from relay_self.action_feedback import (
    ActionFeedbackCriterion,
    LearningFeedbackInterpretationStatus,
    interpret_action_outcome_as_learning_feedback,
)
from relay_self.action_outcome import (
    ActionOutcomeDisposition,
    record_interpreted_action_outcome,
)
from relay_self.action_supervision import ActionSupervisor
from relay_self.attention import (
    AttentionCandidate,
    AttentionCriterion,
    select_attention,
)
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
    classify_concept,
    concept_candidate_from_belief,
)
from relay_self.epoch_continuation import (
    StaleRetainedSnapshot,
    UnauthorizedRetainedRead,
    read_retained_preference,
)
from relay_self.epoch_plan import (
    EpochBinding,
    EpochWorkItem,
    compile_epoch_plan,
    coordinate_planned_epoch,
)
from relay_self.execution_admission import (
    AdmissionDecisionStatus,
    AdmissionPolicy,
    ExecutionAdmissionCriterion,
    admit_control_candidate,
)
from relay_self.execution_binding import (
    ExecutionBinding,
    resolve_execution_binding,
    start_and_propose_bound_execution,
)
from relay_self.execution_descriptor import (
    S17_DESCRIPTOR_SET,
    s17_capability_plan,
)
from relay_self.habit import (
    CueFeature,
    HabitCue,
    HabitRepertoire,
    HabitRule,
    select_habit,
)
from relay_self.intent import IntentCommitment
from relay_self.learning import (
    FeedbackDirection,
    InvalidLearningAuthority,
    LearningPreferenceState,
    LearningTargetMismatch,
    LearningUpdateAuthority,
    LearningUpdateRule,
    MissingLearningAuthority,
    commit_learning_update,
    propose_learning_update,
)
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
    RouteConflictPolicy,
    RouteCriterion,
    RouteDecisionStatus,
    adjudicate_routes,
    control_candidate_from_route_decision,
)
from relay_self.runtime_coordination import coordinate_decision_epoch
from relay_self.skill import SkillState


def provenance(reference: str) -> Provenance:
    return Provenance(source="s18-architecture-freeze", reference=reference)


class FakeSession:
    def __init__(self, messages: tuple[object, ...]) -> None:
        self._messages = deque(messages)
        self.started = MineflayerAdapterStarted(
            session_id="s18-session",
            seq=0,
            mineflayer_version=MINEFLAYER_VERSION,
            config=MineflayerLaunchConfig(),
        )

    async def receive(self):
        return self._messages.popleft()

    async def send_observe(self) -> None:
        return None

    async def send_set_control(
        self,
        action_id: str,
        *,
        control: str,
        state: bool,
    ) -> None:
        assert action_id == "action-move-backward-1"
        assert control == "back"
        assert state is True

    async def send_clear_controls(self, action_id: str) -> None:
        assert action_id == "action-move-backward-1-s15-clear"


def observation(seq: int, z: float) -> MineflayerObservation:
    return MineflayerObservation(
        session_id="s18-session",
        seq=seq,
        kind="probe",
        snapshot=MineflayerSnapshot(
            health=20,
            food=20,
            food_saturation=5,
            oxygen_level=20,
            position=MineflayerPosition(x=0.0, y=64.0, z=z),
            time=None,
            inventory=(),
            nearby_entities=(),
            nearby_entities_coverage=MineflayerNearbyEntitiesCoverage(
                source_scope=MINEFLAYER_NEARBY_ENTITY_SOURCE_SCOPE,
                max_distance=MINEFLAYER_NEARBY_ENTITY_MAX_DISTANCE,
                max_entities=MINEFLAYER_NEARBY_ENTITY_MAX_ENTITIES,
                candidate_count=0,
                truncated=False,
            ),
        ),
    )


def effect(
    seq: int,
    action_id: str,
    effect_name: str,
) -> MineflayerEffectResult:
    return MineflayerEffectResult(
        session_id="s18-session",
        seq=seq,
        action_id=action_id,
        effect=effect_name,
        result="applied",
        error=None,
    )


def _run_epoch_one(supervisor: ActionSupervisor):
    p = PropositionKey("entity", "zombie-1", "nearby")
    evidence = BeliefEvidence(
        "E1",
        p,
        EvidenceRelation.SUPPORT,
        provenance("evidence"),
    )
    attention = select_attention(
        (
            AttentionCandidate(
                "E1",
                "belief-evidence:E1",
                provenance("attention"),
                focus_keys=("zombie-1",),
            ),
        ),
        AttentionCriterion("focus-zombie", focus_key="zombie-1"),
    )
    assert attention.selected[0].candidate_id == "E1"

    belief = assess_belief(
        (evidence,),
        BeliefCriterion("zombie-nearby", p),
    )
    concept = classify_concept(
        concept_candidate_from_belief(
            belief,
            candidate_id="belief:zombie-nearby",
            payload_ref="transient:belief:zombie-nearby",
            provenance=provenance("belief-to-concept"),
        ),
        ConceptCriterion(
            criterion_id="supported-nearby",
            concept=ConceptKey("spatial", "nearby_threat"),
            required_features=(
                ConceptFeature("belief_status", "supported"),
                ConceptFeature("proposition", p.canonical),
            ),
        ),
    )

    base = prediction_state_from_concept(
        concept,
        state_id="threat:zombie-1",
        extra_variables=(StateVariable("comparison_score", 99),),
        provenance=provenance("concept-to-prediction"),
    )
    wait_prediction = predict_transition(
        base,
        TransitionRule(
            rule_id="wait",
            preconditions=(StateVariable("concept", "spatial:nearby_threat"),),
            assignments=(StateVariable("comparison_score", 8),),
            provenance=provenance("wait"),
        ),
    )
    move_prediction = predict_transition(
        base,
        TransitionRule(
            rule_id="move-away",
            preconditions=(StateVariable("concept", "spatial:nearby_threat"),),
            assignments=(StateVariable("comparison_score", 3),),
            provenance=provenance("move"),
        ),
    )
    plan = select_plan(
        (
            plan_candidate_from_prediction(
                wait_prediction,
                candidate_id="WAIT",
                feature_keys=("comparison_score",),
                provenance=provenance("wait-plan"),
            ),
            plan_candidate_from_prediction(
                move_prediction,
                candidate_id="MOVE_AWAY",
                feature_keys=("comparison_score",),
                provenance=provenance("move-plan"),
            ),
        ),
        PlanningCriterion(
            criterion_id="minimize-comparison-score",
            feature_key="comparison_score",
            direction=PlanningDirection.MINIMIZE,
        ),
    )
    assert plan.selected is not None
    assert plan.selected.candidate_id == "MOVE_AWAY"

    repertoire = HabitRepertoire(
        repertoire_id="survival-habits",
        revision=7,
        rules=(
            HabitRule(
                habit_id="H1",
                cue_requirements=(
                    CueFeature("concept", "spatial:nearby_threat"),
                ),
                candidate_ref="MOVE_AWAY",
                priority=10,
                provenance=provenance("habit"),
            ),
        ),
        provenance=provenance("repertoire"),
    )
    habit = select_habit(
        repertoire,
        HabitCue(
            cue_id="nearby-threat",
            features=(
                CueFeature("concept", "spatial:nearby_threat"),
            ),
            provenance=provenance("cue"),
        ),
    )
    assert habit.selected_candidate_ref == "MOVE_AWAY"

    route = adjudicate_routes(
        plan,
        habit,
        RouteCriterion(
            criterion_id="route-fail-closed",
            conflict_policy=RouteConflictPolicy.FAIL_CLOSED,
        ),
        provenance=provenance("route"),
    )
    assert route.status is RouteDecisionStatus.AGREED
    control = control_candidate_from_route_decision(route)
    assert control is not None

    intent = IntentCommitment()
    intent.commit(
        "escape-threat",
        objective="escape the nearby threat",
        at_ns=1,
        provenance=provenance("intent"),
    )
    admission_criterion = ExecutionAdmissionCriterion(
        criterion_id="escape-threat-allow-list",
        policy=AdmissionPolicy.CURRENT_INTENT_ALLOW_LIST,
        required_intent_id="escape-threat",
        allowed_candidate_refs=("MOVE_AWAY",),
    )
    admission = admit_control_candidate(
        control,
        route,
        intent,
        admission_criterion,
        provenance=provenance("admission"),
    )
    assert admission.status is AdmissionDecisionStatus.ADMITTED

    binding = ExecutionBinding(
        binding_id="binding-move-away-1",
        candidate_ref="MOVE_AWAY",
        required_intent_id="escape-threat",
        skill_execution_id="skill-exec-escape-1",
        skill_ref="escape-movement",
        action_id="action-move-backward-1",
        action_ref="MOVE_BACKWARD",
        provenance=provenance("binding"),
    )
    bound = resolve_execution_binding(
        admission,
        control,
        route,
        intent,
        admission_criterion,
        binding,
        provenance=provenance("resolve-binding"),
    )
    skill, proposed, binding_result = start_and_propose_bound_execution(
        bound,
        intent,
        at_ns=10,
        provenance=provenance("start-propose"),
    )
    assert skill.state is SkillState.STARTED
    assert proposed.state is ActionState.PROPOSED

    authorized = proposed.authorize(
        at_ns=11,
        provenance=provenance("authorize"),
        authority="s18-explicit-authority",
    )
    issued = supervisor.issue(
        authorized,
        at_ns=12,
        deadline_ns=100,
        provenance=provenance("issue"),
    )
    assert issued.state is ActionState.ISSUED

    command = build_mineflayer_command(issued, binding_result)
    adapter = FakeSession(
        (
            observation(1, 0.0),
            effect(2, command.action_id, "set_control"),
            effect(3, command.cleanup_action_id, "clear_controls"),
            observation(4, 0.20),
        )
    )
    consequence = asyncio.run(
        execute_mineflayer_command(
            adapter,
            command,
            provenance=provenance("world-consequence"),
        )
    )
    assert consequence.status is WorldConsequenceStatus.EXECUTED

    outcome_interpretation = interpret_world_consequence(
        issued,
        binding_result,
        consequence,
        provenance=provenance("outcome-interpretation"),
    )
    closed = record_interpreted_action_outcome(
        supervisor,
        outcome_interpretation,
        at_ns=20,
    )
    assert closed.state is ActionState.OUTCOME
    assert outcome_interpretation.reason_code == "observed_execution"

    feedback_criterion = ActionFeedbackCriterion(
        criterion_id="risk-from-observed-move",
        target_id="risk_weight",
        required_action_id="action-move-backward-1",
        required_binding_id="binding-move-away-1",
        required_action_ref="MOVE_BACKWARD",
        required_action_state=ActionState.OUTCOME,
        required_outcome_disposition=ActionOutcomeDisposition.OUTCOME,
        required_outcome_reason="observed_execution",
        feedback_direction=FeedbackDirection.INCREASE,
        provenance=provenance("feedback-criterion"),
    )
    feedback_interpretation = interpret_action_outcome_as_learning_feedback(
        closed,
        outcome_interpretation,
        feedback_criterion,
        provenance=provenance("feedback"),
    )
    assert (
        feedback_interpretation.status
        is LearningFeedbackInterpretationStatus.PRODUCED
    )
    assert feedback_interpretation.feedback is not None

    state = LearningPreferenceState(
        target_id="risk_weight",
        value=3,
        minimum=0,
        maximum=10,
        revision=0,
        origin_provenance=provenance("learning-origin"),
    )
    proposal = propose_learning_update(
        state,
        feedback_interpretation.feedback,
        LearningUpdateRule(
            rule_id="bounded-risk-step",
            version=1,
            step=1,
        ),
    )
    committed = commit_learning_update(
        state,
        proposal,
        LearningUpdateAuthority(
            authority_id="s18-learning-authority",
            target_id="risk_weight",
            provenance=provenance("learning-authority"),
        ),
        provenance=provenance("learning-commit"),
    )

    assert committed.previous_state.value == 3
    assert committed.previous_state.revision == 0
    assert committed.new_state.value == 4
    assert committed.new_state.revision == 1

    return committed, intent, closed, feedback_interpretation

def _epoch_one():
    """One caller-invoked admitted coordinator around the real S18 transaction."""
    supervisor = ActionSupervisor()
    result_holder = []

    def invoke():
        result_holder.append(_run_epoch_one(supervisor))
        return None

    result = coordinate_decision_epoch(
        supervisor,
        at_ns=0,
        provenance=provenance("epoch-one-explicit-invoke"),
        decision_step=invoke,
    )
    assert len(result_holder) == 1
    assert not result.cognition_requested
    committed, intent, closed, feedback = result_holder[0]
    assert committed.previous_state.value == 3
    assert committed.previous_state.revision == 0
    assert committed.new_state.value == 4
    assert committed.new_state.revision == 1
    return supervisor, committed, intent, closed, feedback, result


def _epoch_two(supervisor, intent, owner_snapshot, supplied_snapshot, *, expected_revision):
    """Separate caller invocation: ATT/BLF/CNC/PRD/PLAN/ROUTE/fresh ADMISSION.

    A/B alternatives use identical deterministic policies and structured
    external evidence. Only the explicitly supplied owner-local snapshot
    changes; this apparatus does not install a learned utility policy.
    """
    outputs = {}
    criterion = PlanningCriterion(
        criterion_id="s19-minimize-structured-comparison",
        feature_key="comparison_score",
        direction=PlanningDirection.MINIMIZE,
    )
    admission_guard = ExecutionAdmissionCriterion(
        criterion_id="s19-fresh-admission",
        policy=AdmissionPolicy.CURRENT_INTENT_ALLOW_LIST,
        required_intent_id="escape-threat",
        allowed_candidate_refs=("WAIT", "MOVE_AWAY"),
    )
    proposition = PropositionKey("entity", "zombie-1", "nearby")
    evidence = BeliefEvidence(
        "E1", proposition, EvidenceRelation.SUPPORT, provenance("evidence"),
    )
    attention_input = AttentionCandidate(
        "E1", "belief-evidence:E1", provenance("attention"),
        focus_keys=("zombie-1",),
    )
    attention_criterion = AttentionCriterion("focus-zombie", focus_key="zombie-1")
    belief_criterion = BeliefCriterion("zombie-nearby", proposition)
    concept_criterion = ConceptCriterion(
        criterion_id="supported-nearby",
        concept=ConceptKey("spatial", "nearby_threat"),
        required_features=(
            ConceptFeature("belief_status", "supported"),
            ConceptFeature("proposition", proposition.canonical),
        ),
    )
    wait_rule = TransitionRule(
        rule_id="s19-wait",
        preconditions=(StateVariable("concept", "spatial:nearby_threat"),),
        assignments=(StateVariable("action_kind", "wait"),),
        provenance=provenance("s19-wait-rule"),
    )
    move_rule = TransitionRule(
        rule_id="s19-move",
        preconditions=(StateVariable("concept", "spatial:nearby_threat"),),
        assignments=(
            StateVariable("action_kind", "move_away"),
            StateVariable("comparison_score", 7),
        ),
        provenance=provenance("s19-move-rule"),
    )
    route_criterion = RouteCriterion("s19-plan-only", allow_single_source=True)
    outputs["external"] = (
        proposition, evidence, attention_input, attention_criterion,
        belief_criterion, concept_criterion,
    )
    outputs["policies"] = (
        wait_rule, move_rule, criterion, route_criterion, admission_guard,
        "wait_score_is_twice_retained_risk_weight",
    )

    def attention_step():
        outputs["attention"] = select_attention(
            (attention_input,), attention_criterion,
        )
        return None

    def belief_step():
        assert outputs["attention"].selected[0].candidate_id == evidence.evidence_id
        outputs["belief"] = assess_belief((evidence,), belief_criterion)
        return None

    def concept_step():
        outputs["concept"] = classify_concept(
            concept_candidate_from_belief(
                outputs["belief"],
                candidate_id="belief:zombie-nearby",
                payload_ref="transient:belief:zombie-nearby",
                provenance=provenance("belief-to-concept"),
            ),
            concept_criterion,
        )
        return None

    def predict_wait_step():
        read = read_retained_preference(
            owner_snapshot, supplied_snapshot,
            required_target_id="risk_weight",
            expected_revision=expected_revision,
            provenance=provenance("epoch-two-retained-read"),
        )
        # The explicit caller comparison projection is fixed in both A/B
        # branches. PRD itself remains the *existing* stateless predictor.
        original = prediction_state_from_concept(
            outputs["concept"],
            state_id="s19-threat-zombie-1",
            extra_variables=(
                StateVariable("comparison_score", 2 * read.snapshot.value),
                StateVariable("risk_weight", read.snapshot.value),
            ),
            provenance=provenance("s19-concept-retained-to-prediction"),
        )
        record = read.last_update
        lineage_refs = (
            f"learning-target:{read.snapshot.target_id}",
            f"learning-revision:{read.revision}",
        )
        lineage_provenance = (read.origin_provenance, read.read_provenance)
        if record is not None:
            lineage_refs += (
                f"learning-feedback:{record.feedback_id}",
                f"learning-rule:{record.rule_id}:v{record.rule_version}",
                f"learning-authority:{record.authority_id}",
                f"learning-commit-revision:{record.committed_revision}",
            )
            lineage_provenance += (
                record.feedback_provenance,
                record.authority_provenance,
                record.update_provenance,
            )
        state = replace(
            original,
            source_refs=(*original.source_refs, *lineage_refs),
            source_provenance=(*original.source_provenance, *lineage_provenance),
        )
        outputs["read"] = read
        outputs["prediction_input"] = state
        outputs["wait_prediction"] = predict_transition(state, wait_rule)
        return None

    def predict_move_step():
        outputs["move_prediction"] = predict_transition(
            outputs["prediction_input"], move_rule,
        )
        return None

    def plan_step():
        outputs["plan"] = select_plan(
            (
                plan_candidate_from_prediction(
                    outputs["wait_prediction"],
                    candidate_id="WAIT",
                    feature_keys=("comparison_score",),
                    provenance=provenance("s19-wait-plan"),
                ),
                plan_candidate_from_prediction(
                    outputs["move_prediction"],
                    candidate_id="MOVE_AWAY",
                    feature_keys=("comparison_score",),
                    provenance=provenance("s19-move-plan"),
                ),
            ),
            criterion,
        )
        return None

    def route_step():
        outputs["route"] = adjudicate_routes(
            outputs["plan"], None, route_criterion,
            provenance=provenance("s19-route"),
        )
        outputs["control"] = control_candidate_from_route_decision(outputs["route"])
        return None

    def admit_step():
        outputs["admission"] = admit_control_candidate(
            outputs["control"], outputs["route"], intent, admission_guard,
            provenance=provenance("s19-fresh-admission"),
        )
        return None

    work = (
        ("s19-att", "att.select", attention_step),
        ("s19-blf", "blf.assess", belief_step),
        ("s19-cnc", "cnc.classify", concept_step),
        ("s19-prd-wait", "prd.predict", predict_wait_step),
        ("s19-prd-move", "prd.predict", predict_move_step),
        ("s19-plan", "plan.select", plan_step),
        ("s19-route", "route.adjudicate", route_step),
        ("s19-admit", "execution.admit_candidate", admit_step),
    )
    items = tuple(
        EpochWorkItem(work_id=w, operator_id=o, trigger_ref="caller:s19:second")
        for w, o, _ in work
    )
    bindings = tuple(
        EpochBinding(work_id=w, operator_id=o, invoke=fn)
        for w, o, fn in work
    )
    plan = compile_epoch_plan(
        s17_capability_plan(
            enabled_ids=frozenset(
                ("ATT", "BLF", "CNC", "PRD", "PLAN", "ROUTE", "ADMISSION")
            )
        ),
        S17_DESCRIPTOR_SET,
        due_items=items,
        bindings=bindings,
    )
    result = coordinate_planned_epoch(
        supervisor, plan, bindings=bindings, at_ns=30,
        provenance=provenance("epoch-two-explicit-invoke"),
    )
    return outputs, result


def test_two_epochs_with_governed_retention_and_fresh_admission():
    supervisor, commit, intent, closed, feedback, first = _epoch_one()
    assert closed.state is ActionState.OUTCOME
    assert feedback.feedback is not None
    assert commit.record.feedback_id == feedback.feedback.feedback_id
    assert commit.record.authority_id == "s18-learning-authority"
    assert commit.record.previous_revision == 0
    assert commit.record.committed_revision == 1
    assert first.next_action_deadline_ns is None

    # Explicit caller-owned reentry occurs strictly AFTER epoch 1 STOP.
    values, second = _epoch_two(
        supervisor, intent, commit.new_state, commit.new_state, expected_revision=1,
    )
    assert values["read"].snapshot is commit.new_state
    assert values["read"].last_update == commit.record
    assert values["read"].origin_provenance == commit.new_state.origin_provenance
    assert values["read"].read_provenance == provenance("epoch-two-retained-read")
    assert values["prediction_input"].variable("risk_weight").value == 4
    assert f"learning-feedback:{commit.record.feedback_id}" in (
        values["prediction_input"].source_refs
    )
    assert f"learning-authority:{commit.record.authority_id}" in (
        values["prediction_input"].source_refs
    )
    assert commit.record.feedback_provenance in (
        values["prediction_input"].source_provenance
    )
    assert commit.record.authority_provenance in (
        values["prediction_input"].source_provenance
    )
    assert commit.record.update_provenance in (
        values["prediction_input"].source_provenance
    )
    assert values["plan"].selected.candidate_id == "MOVE_AWAY"
    assert values["plan"].candidates[0].feature("comparison_score").value == 8
    assert values["route"].status is RouteDecisionStatus.SELECTED
    assert values["admission"].status is AdmissionDecisionStatus.ADMITTED
    assert values["admission"].current_intent_id == "escape-threat"
    assert second.executed_work_ids == (
        "s19-att", "s19-blf", "s19-cnc", "s19-prd-wait",
        "s19-prd-move", "s19-plan", "s19-route", "s19-admit",
    )
    assert second.cognition_requested is False
    assert first.cognition_requested is False
    assert supervisor.next_deadline_ns is None


def test_no_retained_change_leaves_decision_unchanged():
    supervisor, commit, intent, _, _, _ = _epoch_one()
    old = commit.previous_state
    values, second = _epoch_two(supervisor, intent, old, old, expected_revision=0)
    assert values["plan"].selected.candidate_id == "WAIT"
    assert values["plan"].candidates[0].feature("comparison_score").value == 6
    assert values["admission"].status is AdmissionDecisionStatus.ADMITTED
    assert second.cognition_requested is False
    assert old.value == 3 and old.revision == 0


def test_no_auto_reentry_after_governed_commit():
    supervisor, commit, intent, _, _, first = _epoch_one()
    assert first.cognition_requested is False
    assert commit.new_state.revision == 1
    assert intent.current_intent is not None
    assert supervisor.advance(at_ns=30, provenance=provenance("no-reentry")) == ()
    assert supervisor.next_deadline_ns is None


def test_stale_revision_and_reconstructed_snapshot_fail_closed():
    supervisor, commit, intent, _, _, _ = _epoch_one()
    with pytest.raises(StaleRetainedSnapshot):
        _epoch_two(
            supervisor, intent, commit.new_state, commit.previous_state,
            expected_revision=1,
        )
    with pytest.raises(StaleRetainedSnapshot):
        _epoch_two(
            supervisor, intent, commit.new_state, commit.new_state,
            expected_revision=0,
        )
    with pytest.raises(StaleRetainedSnapshot):
        _epoch_two(
            supervisor, intent, commit.new_state, replace(commit.new_state),
            expected_revision=1,
        )
    assert commit.new_state.value == 4


def test_wrong_owner_provider_text_and_unproven_revision_fail_closed():
    supervisor, commit, intent, _, _, _ = _epoch_one()
    with pytest.raises(UnauthorizedRetainedRead):
        read_retained_preference(
            commit.new_state, commit.new_state,
            required_target_id="other", expected_revision=1,
            provenance=provenance("wrong-target"),
        )
    with pytest.raises(UnauthorizedRetainedRead):
        read_retained_preference(
            "provider-text", "provider-text",
            required_target_id="risk_weight", expected_revision=1,
            provenance=provenance("provider"),
        )
    fabricated = LearningPreferenceState(
        target_id="risk_weight", value=4, minimum=0, maximum=10,
        revision=1, origin_provenance=provenance("fabricated"),
    )
    with pytest.raises(UnauthorizedRetainedRead):
        _epoch_two(supervisor, intent, fabricated, fabricated, expected_revision=1)


def test_learning_commit_authority_remains_separate_from_feedback():
    _, commit, _, _, feedback, _ = _epoch_one()
    proposal = propose_learning_update(
        commit.previous_state, feedback.feedback,
        LearningUpdateRule("bounded-risk-step", version=1, step=1),
    )
    with pytest.raises(MissingLearningAuthority):
        commit_learning_update(
            commit.previous_state, proposal, None,
            provenance=provenance("missing-authority"),
        )
    with pytest.raises(InvalidLearningAuthority):
        commit_learning_update(
            commit.previous_state, proposal,
            LearningUpdateAuthority(
                "denied", "risk_weight", provenance("denied"), granted=False,
            ),
            provenance=provenance("denied-commit"),
        )
    with pytest.raises(LearningTargetMismatch):
        commit_learning_update(
            commit.previous_state, proposal,
            LearningUpdateAuthority("wrong", "other", provenance("wrong")),
            provenance=provenance("wrong-owner-commit"),
        )
    assert commit.previous_state.value == 3 and commit.new_state.value == 4


def test_no_hidden_scheduler_or_commit_in_retained_read():
    source = (
        Path(__file__).resolve().parents[1] / "src/relay_self/epoch_continuation.py"
    ).read_text(encoding="utf-8")
    forbidden = (
        "asyncio.create_task", "threading.Thread", "eval(", "exec(",
        "importlib", "relay_engine(", "global ", "coordinate_decision_epoch(",
        "coordinate_planned_epoch(", "commit_learning_update(",
    )
    assert not any(marker in source for marker in forbidden)


def test_machine_receipt_has_bounded_claims():
    receipt = json.loads(
        (Path(__file__).resolve().parents[1] / "docs/postmain-s19-receipt.json").read_text(
            encoding="utf-8"
        )
    )
    assert receipt["base_head"] == "b5eb5d3416a9c303b855250adea4323e7611f350"
    assert receipt["epoch_count"] == 2
    assert receipt["invocation"] == "explicit_caller_owned"
    assert receipt["retained_handoff"] == {
        "target_id": "risk_weight",
        "before": {"value": 3, "revision": 0},
        "after": {"value": 4, "revision": 1},
    }
    assert receipt["control_choice"] == "WAIT"
    assert receipt["updated_choice"] == "MOVE_AWAY"
    assert receipt["provider_model_calls"] == 0
    assert receipt["autonomous_reentry"] is False
    assert receipt["minecraft_live_field"] == "NOT_RUN"
