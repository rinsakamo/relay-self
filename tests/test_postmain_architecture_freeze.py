from __future__ import annotations

import asyncio
import json
from collections import deque
from pathlib import Path

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
    CriterionKind,
    OperatorEffect,
    S17_CAPABILITY_SPECS,
    S17_DESCRIPTOR_SET,
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
    LearningPreferenceState,
    LearningUpdateAuthority,
    LearningUpdateRule,
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
from relay_self.skill import SkillState


ROOT = Path(__file__).resolve().parents[1]
MANIFEST_PATH = ROOT / "docs" / "postmain-architecture.json"


def provenance(reference: str) -> Provenance:
    return Provenance(source="s18-architecture-freeze", reference=reference)


def manifest() -> dict:
    return json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))


def test_frozen_capability_taxonomy_and_state_scopes() -> None:
    by_id = {spec.capability_id: spec for spec in S17_CAPABILITY_SPECS}
    expected = {
        "MEM",
        "CTL",
        "SKL",
        "TALK",
        "ATT",
        "BLF",
        "CNC",
        "PRD",
        "PLAN",
        "LRN",
        "HABIT",
        "ROUTE",
        "ADMISSION",
        "EXEC_BIND",
        "WORLD_EXEC",
        "ACTION_OUTCOME",
        "FEEDBACK",
    }
    assert set(by_id) == expected

    integration = {
        "ROUTE",
        "ADMISSION",
        "EXEC_BIND",
        "WORLD_EXEC",
        "ACTION_OUTCOME",
        "FEEDBACK",
    }
    assert all(by_id[value].state_scopes == () for value in integration)
    assert by_id["LRN"].state_scopes == ("owner_local.learning_preference",)
    assert by_id["HABIT"].state_scopes == ("owner_local.habit_repertoire",)
    assert by_id["PRD"].criterion_ids == ()


def test_frozen_descriptor_effects_and_criterion_kinds() -> None:
    operators = {
        value.operator_id: value
        for value in S17_DESCRIPTOR_SET.operators
    }
    criteria = {
        value.criterion_id: value
        for value in S17_DESCRIPTOR_SET.criteria
    }

    expected_effects = {
        "att.select": OperatorEffect.READ_ONLY,
        "blf.assess": OperatorEffect.READ_ONLY,
        "cnc.classify": OperatorEffect.READ_ONLY,
        "prd.predict": OperatorEffect.READ_ONLY,
        "plan.select": OperatorEffect.READ_ONLY,
        "lrn.propose_update": OperatorEffect.READ_ONLY,
        "lrn.apply_update": OperatorEffect.OWNER_TRANSITION,
        "habit.select": OperatorEffect.READ_ONLY,
        "route.adjudicate": OperatorEffect.READ_ONLY,
        "execution.admit_candidate": OperatorEffect.READ_ONLY,
        "execution.resolve_binding": OperatorEffect.READ_ONLY,
        "execution.start_and_propose": OperatorEffect.OWNER_TRANSITION,
        "world.build_mineflayer_command": OperatorEffect.READ_ONLY,
        "world.execute_mineflayer_command": OperatorEffect.COORDINATION,
        "action.interpret_world_consequence": OperatorEffect.READ_ONLY,
        "action.record_interpreted_outcome": OperatorEffect.OWNER_TRANSITION,
        "learning.interpret_action_outcome_feedback": OperatorEffect.READ_ONLY,
    }
    for operator_id, effect in expected_effects.items():
        assert operators[operator_id].effect is effect
        assert operators[operator_id].hidden_persistent_state is False

    orientations = {
        "att.explicit_orientation",
        "blf.evidence_support_orientation",
        "cnc.explicit_membership_orientation",
        "plan.explicit_preference_orientation",
        "lrn.explicit_feedback_orientation",
        "habit.explicit_priority_orientation",
        "route.explicit_arbitration_orientation",
        "learning.explicit_outcome_feedback_orientation",
    }
    guards = {
        "admission.explicit_execution_guard",
        "execution.explicit_binding_guard",
        "world.issued_action_binding_guard",
        "action.exact_outcome_lineage_guard",
    }
    for criterion_id in orientations:
        assert criteria[criterion_id].kind is CriterionKind.COGNITIVE_ORIENTATION
    for criterion_id in guards:
        assert criteria[criterion_id].kind is CriterionKind.CONTRACT_GUARD
    assert all(value.mutates_state is False for value in criteria.values())


def test_descriptor_refs_remain_audit_metadata_not_dynamic_dispatch() -> None:
    refs = tuple(
        descriptor.implementation_ref
        for descriptor in S17_DESCRIPTOR_SET.operators
    ) + tuple(
        descriptor.implementation_ref
        for descriptor in S17_DESCRIPTOR_SET.criteria
    )
    assert refs
    assert all("eval(" not in value for value in refs)
    assert all("__import__" not in value for value in refs)
    assert all("import_module" not in value for value in refs)


def test_machine_readable_freeze_matches_frozen_contract() -> None:
    value = manifest()
    assert value["schema_version"] == "1.0"
    assert value["frozen_base_head"] == (
        "64868337510a960c140e96d5d3d20949ad53fb8e"
    )
    assert value["slice_range"] == "S1-S17"
    assert value["architecture_claim"] == (
        "SINGLE_TRANSACTION_COGNITIVE_ACTION_LEARNING_ARCHITECTURE_QUALIFIED"
    )
    assert value["terminal_interpretation"] == (
        "S18_FROZEN_AS_SINGLE_TRANSACTION_COGNITIVE_ACTION_LEARNING_"
        "ARCHITECTURE_WITH_EXPLICIT_OWNERSHIP_AND_AUTHORITY_BOUNDARIES"
    )
    assert value["deterministic_trace"]["trace_id"] == (
        "S18_DETERMINISTIC_TEST_APPARATUS_TRACE_V1"
    )
    assert value["deterministic_trace"]["provider_model_calls"] == 0
    assert value["deterministic_trace"]["autonomous_reentry"] is False
    assert value["live_field"] == {
        "status": "BLOCKED_NOT_RUN",
        "blocker": "genuine Minecraft endpoint unavailable",
        "deterministic_test_evidence_is_not_live_field": True,
    }
    assert value["autonomous_reentry"]["status"] == "NOT_IMPLEMENTED"
    assert value["autonomous_reentry"]["continuous_multi_epoch_operation"] == (
        "NOT_QUALIFIED"
    )


def test_frozen_forbidden_implicit_edges_are_complete() -> None:
    frozen = set(manifest()["forbidden_implicit_edges"])
    required = {
        "ATT -> belief mutation",
        "BLF -> Memory write",
        "CNC -> World truth",
        "PRD -> plan commitment",
        "PLAN -> Current Intent",
        "PLAN -> Action proposal",
        "HABIT -> Action execution",
        "HABIT -> LearningFeedback",
        "ROUTE -> Intent mutation",
        "ADMISSION -> Skill start",
        "EXEC_BIND -> authorization",
        "WORLD_EXEC -> LearningFeedback",
        "WorldConsequence -> Memory",
        "WorldConsequence -> Belief",
        "ACTION_OUTCOME -> LearningFeedback without explicit FEEDBACK criterion",
        "FEEDBACK -> retained update without LRN authority",
        "LRN -> automatic next epoch",
    }
    assert frozen == required


def test_static_source_audit_has_no_hidden_dynamic_runtime_mechanism() -> None:
    paths = (
        "src/relay_self/attention.py",
        "src/relay_self/belief.py",
        "src/relay_self/concept.py",
        "src/relay_self/prediction.py",
        "src/relay_self/planning.py",
        "src/relay_self/learning.py",
        "src/relay_self/habit.py",
        "src/relay_self/route_adjudication.py",
        "src/relay_self/execution_admission.py",
        "src/relay_self/execution_binding.py",
        "adapters/mineflayer/execution.py",
        "adapters/mineflayer/action_outcome.py",
        "src/relay_self/action_outcome.py",
        "src/relay_self/action_feedback.py",
    )
    forbidden = (
        "eval(",
        "exec(",
        "__import__(",
        "importlib.import_module",
        "threading.Thread",
        "asyncio.create_task",
    )
    for relative in paths:
        source = (ROOT / relative).read_text(encoding="utf-8")
        for marker in forbidden:
            assert marker not in source, (relative, marker)


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


def test_canonical_single_transaction_trace_reaches_outcome_and_retained_rev1() -> None:
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
    supervisor = ActionSupervisor()
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

    # Frozen STOP: no second epoch/action is constructed or invoked.
    second_epoch_work: tuple[object, ...] = ()
    provider_model_calls: tuple[object, ...] = ()
    assert second_epoch_work == ()
    assert provider_model_calls == ()
