from __future__ import annotations

import asyncio
from collections import deque
from dataclasses import replace

import pytest

from adapters.mineflayer.execution import (
    MOVE_BACKWARD_ACTION_REF,
    MineflayerCommand,
    WorldConsequenceStatus,
    build_mineflayer_command,
    execute_mineflayer_command,
)
from adapters.mineflayer.action_outcome import interpret_world_consequence
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
from relay_self.action import ActionState, InvalidTransition
from relay_self.action_outcome import (
    ActionOutcomeDisposition,
    InvalidActionOutcomeData,
    record_interpreted_action_outcome,
)
from relay_self.action_supervision import (
    ActionSupervisor,
    UnknownSupervisedAction,
)
from relay_self.attention import (
    AttentionCandidate,
    AttentionCriterion,
    require_attention_selection,
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
from relay_self.epoch_plan import (
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
    S16_ACTION_OUTCOME_CAPABILITY_SPEC,
    S16_ACTION_OUTCOME_CRITERION_DESCRIPTOR,
    S16_ACTION_OUTCOME_RECORD_OPERATOR_DESCRIPTOR,
    S16_ACTION_OUTCOME_TRANSLATE_OPERATOR_DESCRIPTOR,
    S16_DESCRIPTOR_SET,
    CriterionKind,
    OperatorEffect,
    s16_capability_plan,
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
    InvalidLearningData,
    LearningPreferenceState,
    LearningUpdateRule,
    propose_learning_update,
)
from relay_self.persistent_cognition import (
    IdentitySpecification,
    Memory,
    PersistentCognition,
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
from relay_self.relay_engine import ProviderExpression
from relay_self.route_adjudication import (
    RouteConflictPolicy,
    RouteCriterion,
    RouteDecisionStatus,
    adjudicate_routes,
    control_candidate_from_route_decision,
)
from relay_self.skill import SkillState


def provenance(reference: str) -> Provenance:
    return Provenance(
        source="s16-action-outcome-qualification",
        reference=reference,
    )


def intent_owner() -> IntentCommitment:
    owner = IntentCommitment()
    owner.commit(
        "escape-threat",
        objective="escape the nearby threat",
        at_ns=1,
        provenance=provenance("intent"),
    )
    return owner


def route_criterion() -> RouteCriterion:
    return RouteCriterion(
        criterion_id="route-fail-closed",
        conflict_policy=RouteConflictPolicy.FAIL_CLOSED,
    )


def admission_criterion(
    *allowed: str,
) -> ExecutionAdmissionCriterion:
    return ExecutionAdmissionCriterion(
        criterion_id="escape-threat-allow-list",
        policy=AdmissionPolicy.CURRENT_INTENT_ALLOW_LIST,
        required_intent_id="escape-threat",
        allowed_candidate_refs=allowed or ("MOVE_AWAY",),
    )


def binding() -> ExecutionBinding:
    return ExecutionBinding(
        binding_id="binding-move-away-1",
        candidate_ref="MOVE_AWAY",
        required_intent_id="escape-threat",
        skill_execution_id="skill-exec-escape-1",
        skill_ref="escape-movement",
        action_id="action-move-backward-1",
        action_ref=MOVE_BACKWARD_ACTION_REF,
        provenance=provenance("binding"),
    )


def plan_and_habit(
    *,
    wait_score: int = 8,
    move_score: int = 3,
):
    proposition = PropositionKey("entity", "zombie-1", "nearby")
    evidence = BeliefEvidence(
        "E1",
        proposition,
        EvidenceRelation.SUPPORT,
        provenance("evidence:E1"),
    )
    attention = select_attention(
        (
            AttentionCandidate(
                "E1",
                "belief-evidence:E1",
                provenance("attention:E1"),
                focus_keys=("zombie-1",),
            ),
        ),
        AttentionCriterion("focus-zombie", focus_key="zombie-1"),
    )
    require_attention_selection(attention)
    belief = assess_belief(
        (evidence,),
        BeliefCriterion("zombie-nearby", proposition),
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
                ConceptFeature("proposition", proposition.canonical),
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
            preconditions=(
                StateVariable("concept", "spatial:nearby_threat"),
            ),
            assignments=(StateVariable("comparison_score", wait_score),),
            provenance=provenance("rule:wait"),
        ),
    )
    move_prediction = predict_transition(
        base,
        TransitionRule(
            rule_id="move-away",
            preconditions=(
                StateVariable("concept", "spatial:nearby_threat"),
            ),
            assignments=(StateVariable("comparison_score", move_score),),
            provenance=provenance("rule:move-away"),
        ),
    )
    plan = select_plan(
        (
            plan_candidate_from_prediction(
                wait_prediction,
                candidate_id="WAIT",
                feature_keys=("comparison_score",),
                provenance=provenance("prediction-to-plan:wait"),
            ),
            plan_candidate_from_prediction(
                move_prediction,
                candidate_id="MOVE_AWAY",
                feature_keys=("comparison_score",),
                provenance=provenance("prediction-to-plan:move"),
            ),
        ),
        PlanningCriterion(
            criterion_id="minimize-comparison-score",
            feature_key="comparison_score",
            direction=PlanningDirection.MINIMIZE,
        ),
    )
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
                provenance=provenance("habit:H1"),
            ),
        ),
        provenance=provenance("habit-repertoire"),
    )
    habit = select_habit(
        repertoire,
        HabitCue(
            cue_id="nearby-threat",
            features=(CueFeature("concept", concept.concept.canonical),),
            provenance=provenance("habit-cue"),
        ),
    )
    return (
        attention,
        belief,
        concept,
        wait_prediction,
        move_prediction,
        plan,
        repertoire,
        habit,
    )


def s14_chain(
    *,
    wait_score: int = 8,
    move_score: int = 3,
    allowed: tuple[str, ...] = ("MOVE_AWAY",),
):
    (
        attention,
        belief,
        concept,
        wait_prediction,
        move_prediction,
        plan,
        repertoire,
        habit,
    ) = plan_and_habit(wait_score=wait_score, move_score=move_score)
    route = adjudicate_routes(
        plan,
        habit,
        route_criterion(),
        provenance=provenance("route"),
    )
    control = control_candidate_from_route_decision(route)
    owner = intent_owner()
    criterion = admission_criterion(*allowed)
    admission = (
        None
        if control is None
        else admit_control_candidate(
            control,
            route,
            owner,
            criterion,
            provenance=provenance("admission"),
        )
    )
    if admission is None or admission.status is not AdmissionDecisionStatus.ADMITTED:
        return (
            attention,
            belief,
            concept,
            wait_prediction,
            move_prediction,
            plan,
            repertoire,
            habit,
            route,
            control,
            owner,
            criterion,
            admission,
            None,
            None,
            None,
        )
    bound = resolve_execution_binding(
        admission,
        control,
        route,
        owner,
        criterion,
        binding(),
        provenance=provenance("binding-resolution"),
    )
    skill, action, result = start_and_propose_bound_execution(
        bound,
        owner,
        at_ns=10,
        provenance=provenance("start-propose"),
    )
    return (
        attention,
        belief,
        concept,
        wait_prediction,
        move_prediction,
        plan,
        repertoire,
        habit,
        route,
        control,
        owner,
        criterion,
        admission,
        skill,
        action,
        result,
    )


def issued_chain():
    *prefix, owner, criterion, admission, skill, proposed, binding_result = s14_chain()
    assert admission is not None
    assert skill is not None
    assert proposed is not None
    assert binding_result is not None
    authorized = proposed.authorize(
        at_ns=11,
        provenance=provenance("authorization"),
        authority="s15-explicit-authority",
    )
    supervisor = ActionSupervisor()
    issued = supervisor.issue(
        authorized,
        at_ns=12,
        deadline_ns=100,
        provenance=provenance("issue"),
    )
    return (
        *prefix,
        owner,
        criterion,
        admission,
        skill,
        proposed,
        binding_result,
        authorized,
        supervisor,
        issued,
    )


def snapshot(x: float, z: float) -> MineflayerSnapshot:
    return MineflayerSnapshot(
        health=20,
        food=20,
        food_saturation=5,
        oxygen_level=20,
        position=MineflayerPosition(x=x, y=64, z=z),
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
    )


def observation(seq: int, x: float, z: float) -> MineflayerObservation:
    return MineflayerObservation(
        session_id="s15-session",
        seq=seq,
        kind="probe",
        snapshot=snapshot(x, z),
    )


def effect(
    seq: int,
    action_id: str,
    effect_name: str,
    *,
    result: str = "applied",
) -> MineflayerEffectResult:
    return MineflayerEffectResult(
        session_id="s15-session",
        seq=seq,
        action_id=action_id,
        effect=effect_name,
        result=result,
        error=None if result == "applied" else "rejected-by-fixture",
    )


class FakeSession:
    def __init__(self, messages=()) -> None:
        self._messages = deque(messages)
        self.started = MineflayerAdapterStarted(
            session_id="s15-session",
            seq=0,
            mineflayer_version=MINEFLAYER_VERSION,
            config=MineflayerLaunchConfig(),
        )
        self.sent: list[tuple] = []
        self.fail_set_control = False
        self.fail_observe = False

    async def receive(self):
        if not self._messages:
            raise RuntimeError("fixture stream exhausted")
        return self._messages.popleft()

    async def send_observe(self) -> None:
        self.sent.append(("observe",))
        if self.fail_observe:
            raise RuntimeError("adapter disconnected")

    async def send_set_control(
        self,
        action_id: str,
        *,
        control: str,
        state: bool,
    ) -> None:
        self.sent.append(("set_control", action_id, control, state))
        if self.fail_set_control:
            raise RuntimeError("dispatch write failed")

    async def send_clear_controls(self, action_id: str) -> None:
        self.sent.append(("clear_controls", action_id))


def successful_session(command: MineflayerCommand) -> FakeSession:
    return FakeSession(
        (
            observation(1, 0.0, 0.0),
            effect(2, command.action_id, "set_control"),
            effect(3, command.cleanup_action_id, "clear_controls"),
            observation(4, 0.0, 0.20),
        )
    )



def executed_consequence():
    *_, binding_result, _, supervisor, issued = issued_chain()[-4:]
    command = build_mineflayer_command(issued, binding_result)
    consequence = asyncio.run(
        execute_mineflayer_command(
            successful_session(command),
            command,
            provenance=provenance("executed-consequence"),
        )
    )
    assert consequence.status is WorldConsequenceStatus.EXECUTED
    return binding_result, supervisor, issued, consequence


def rejected_consequence():
    *_, binding_result, _, supervisor, issued = issued_chain()[-4:]
    command = build_mineflayer_command(issued, binding_result)
    adapter = FakeSession(
        (
            observation(1, 0.0, 0.0),
            effect(
                2,
                command.action_id,
                "set_control",
                result="rejected",
            ),
        )
    )
    consequence = asyncio.run(
        execute_mineflayer_command(
            adapter,
            command,
            provenance=provenance("rejected-consequence"),
        )
    )
    assert consequence.status is WorldConsequenceStatus.FAILED
    assert consequence.dispatch_receipt is not None
    assert consequence.dispatch_receipt.result == "rejected"
    return binding_result, supervisor, issued, consequence


def disconnected_consequence():
    *_, binding_result, _, supervisor, issued = issued_chain()[-4:]
    command = build_mineflayer_command(issued, binding_result)
    adapter = FakeSession()
    adapter.fail_observe = True
    consequence = asyncio.run(
        execute_mineflayer_command(
            adapter,
            command,
            provenance=provenance("disconnected-consequence"),
        )
    )
    assert consequence.status is WorldConsequenceStatus.FAILED
    assert consequence.dispatch_receipt is None
    return binding_result, supervisor, issued, consequence


def undetermined_consequence():
    *_, binding_result, _, supervisor, issued = issued_chain()[-4:]
    command = build_mineflayer_command(issued, binding_result)
    adapter = FakeSession(
        (
            observation(1, 0.0, 0.0),
            effect(2, command.action_id, "set_control"),
            effect(3, command.cleanup_action_id, "clear_controls"),
            observation(4, 0.0, 0.0),
        )
    )
    consequence = asyncio.run(
        execute_mineflayer_command(
            adapter,
            command,
            provenance=provenance("undetermined-consequence"),
        )
    )
    assert consequence.status is WorldConsequenceStatus.UNDETERMINED
    return binding_result, supervisor, issued, consequence


def test_action_outcome_descriptor_is_integration_only_contract_guard() -> None:
    assert S16_ACTION_OUTCOME_CAPABILITY_SPEC.capability_id == "ACTION_OUTCOME"
    assert S16_ACTION_OUTCOME_CAPABILITY_SPEC.state_scopes == ()
    assert S16_ACTION_OUTCOME_CAPABILITY_SPEC.dependencies == ("WORLD_EXEC",)
    assert (
        S16_ACTION_OUTCOME_TRANSLATE_OPERATOR_DESCRIPTOR.effect
        is OperatorEffect.READ_ONLY
    )
    assert (
        S16_ACTION_OUTCOME_RECORD_OPERATOR_DESCRIPTOR.effect
        is OperatorEffect.OWNER_TRANSITION
    )
    assert (
        S16_ACTION_OUTCOME_CRITERION_DESCRIPTOR.kind
        is CriterionKind.CONTRACT_GUARD
    )


def test_executed_consequence_records_existing_outcome_state() -> None:
    binding_result, supervisor, issued, consequence = executed_consequence()
    interpretation = interpret_world_consequence(
        issued,
        binding_result,
        consequence,
        provenance=provenance("interpret-executed"),
    )
    assert interpretation.disposition is ActionOutcomeDisposition.OUTCOME
    assert interpretation.reason_code == "observed_execution"

    closed = record_interpreted_action_outcome(
        supervisor,
        interpretation,
        at_ns=20,
    )

    assert closed.state is ActionState.OUTCOME
    assert closed.events[-1].provenance == consequence.provenance
    assert supervisor.get(issued.action_id) is closed
    assert supervisor.open_actions == ()


def test_failed_rejected_dispatch_is_known_outcome_not_action_success() -> None:
    binding_result, supervisor, issued, consequence = rejected_consequence()
    interpretation = interpret_world_consequence(
        issued,
        binding_result,
        consequence,
        provenance=provenance("interpret-rejection"),
    )

    assert interpretation.source_status == "failed"
    assert interpretation.disposition is ActionOutcomeDisposition.OUTCOME
    assert interpretation.reason_code == "known_adapter_rejection"

    closed = record_interpreted_action_outcome(
        supervisor,
        interpretation,
        at_ns=20,
    )
    assert closed.state is ActionState.OUTCOME
    assert closed.events[-1].provenance == consequence.provenance


def test_failed_without_known_target_result_closes_existing_unknown() -> None:
    binding_result, supervisor, issued, consequence = disconnected_consequence()
    interpretation = interpret_world_consequence(
        issued,
        binding_result,
        consequence,
        provenance=provenance("interpret-disconnected"),
    )

    assert interpretation.disposition is ActionOutcomeDisposition.UNKNOWN
    assert interpretation.reason_code == "adapter_failure_consequence_unknown"

    closed = record_interpreted_action_outcome(
        supervisor,
        interpretation,
        at_ns=20,
    )
    assert closed.state is ActionState.UNKNOWN
    assert closed.events[-1].provenance == consequence.provenance


def test_undetermined_consequence_does_not_fabricate_terminal_result() -> None:
    binding_result, supervisor, issued, consequence = undetermined_consequence()
    interpretation = interpret_world_consequence(
        issued,
        binding_result,
        consequence,
        provenance=provenance("interpret-undetermined"),
    )

    assert interpretation.disposition is ActionOutcomeDisposition.UNAVAILABLE
    with pytest.raises(
        InvalidActionOutcomeData,
        match="cannot close Action",
    ):
        record_interpreted_action_outcome(
            supervisor,
            interpretation,
            at_ns=20,
        )

    assert supervisor.get(issued.action_id).state is ActionState.ISSUED
    (timeout,) = supervisor.advance(
        at_ns=100,
        provenance=provenance("timeout-after-undetermined"),
    )
    assert timeout.state is ActionState.TIMEOUT


@pytest.mark.parametrize("authorized", [False, True])
def test_non_issued_action_cannot_interpret_world_consequence(
    authorized: bool,
) -> None:
    *_, proposed, binding_result = s14_chain()[-3:]
    assert proposed is not None
    assert binding_result is not None
    lifecycle = proposed
    if authorized:
        lifecycle = proposed.authorize(
            at_ns=11,
            provenance=provenance("authorized-only"),
            authority="explicit-authority",
        )

    _, _, issued, consequence = executed_consequence()
    assert issued.state is ActionState.ISSUED
    with pytest.raises(Exception, match="ISSUED"):
        interpret_world_consequence(
            lifecycle,
            binding_result,
            consequence,
            provenance=provenance("non-issued-interpretation"),
        )


def test_exact_consequence_and_binding_identity_are_required() -> None:
    binding_result, _, issued, consequence = executed_consequence()

    with pytest.raises(InvalidActionOutcomeData, match="action_id"):
        interpret_world_consequence(
            issued,
            binding_result,
            replace(consequence, action_id="other-action"),
            provenance=provenance("wrong-action"),
        )

    with pytest.raises(InvalidActionOutcomeData, match="binding_id"):
        interpret_world_consequence(
            issued,
            binding_result,
            replace(consequence, binding_id="other-binding"),
            provenance=provenance("wrong-binding"),
        )

    with pytest.raises(InvalidActionOutcomeData, match="action_ref"):
        interpret_world_consequence(
            issued,
            binding_result,
            replace(consequence, action_ref="WAIT"),
            provenance=provenance("wrong-action-ref"),
        )

    with pytest.raises(Exception, match="skill_execution_id"):
        interpret_world_consequence(
            issued,
            replace(binding_result, skill_execution_id="other-skill"),
            consequence,
            provenance=provenance("wrong-skill"),
        )

    with pytest.raises(Exception, match="intent_id"):
        interpret_world_consequence(
            issued,
            replace(binding_result, intent_id="other-intent"),
            consequence,
            provenance=provenance("wrong-intent"),
        )


def test_structured_consequence_session_lineage_is_checked() -> None:
    binding_result, _, issued, consequence = executed_consequence()
    assert consequence.before_observation is not None
    wrong_before = replace(
        consequence.before_observation,
        session_id="other-session",
    )
    mismatched = replace(
        consequence,
        before_observation=wrong_before,
    )

    with pytest.raises(
        InvalidActionOutcomeData,
        match="session_id mismatch",
    ):
        interpret_world_consequence(
            issued,
            binding_result,
            mismatched,
            provenance=provenance("session-mismatch"),
        )


def test_missing_supervised_action_rejects_owner_transition() -> None:
    binding_result, _, issued, consequence = executed_consequence()
    interpretation = interpret_world_consequence(
        issued,
        binding_result,
        consequence,
        provenance=provenance("missing-supervisor-interpretation"),
    )
    empty_supervisor = ActionSupervisor()

    with pytest.raises(
        UnknownSupervisedAction,
        match="unknown supervised action",
    ):
        record_interpreted_action_outcome(
            empty_supervisor,
            interpretation,
            at_ns=20,
        )


def test_duplicate_outcome_replay_fails_closed_via_existing_owner() -> None:
    binding_result, supervisor, issued, consequence = executed_consequence()
    interpretation = interpret_world_consequence(
        issued,
        binding_result,
        consequence,
        provenance=provenance("replay-interpretation"),
    )
    first = record_interpreted_action_outcome(
        supervisor,
        interpretation,
        at_ns=20,
    )
    assert first.state is ActionState.OUTCOME

    with pytest.raises(InvalidTransition, match="outcome to outcome"):
        record_interpreted_action_outcome(
            supervisor,
            interpretation,
            at_ns=21,
        )
    assert supervisor.get(issued.action_id) is first


def test_timeout_first_rejects_late_world_consequence_closure() -> None:
    binding_result, supervisor, issued, consequence = executed_consequence()
    interpretation = interpret_world_consequence(
        issued,
        binding_result,
        consequence,
        provenance=provenance("late-interpretation"),
    )
    (timed_out,) = supervisor.advance(
        at_ns=100,
        provenance=provenance("timeout-first"),
    )
    assert timed_out.state is ActionState.TIMEOUT

    with pytest.raises(InvalidTransition, match="timeout to outcome"):
        record_interpreted_action_outcome(
            supervisor,
            interpretation,
            at_ns=100,
        )
    assert supervisor.get(issued.action_id) is timed_out


def test_outcome_first_prevents_later_timeout_rewrite() -> None:
    binding_result, supervisor, issued, consequence = executed_consequence()
    interpretation = interpret_world_consequence(
        issued,
        binding_result,
        consequence,
        provenance=provenance("outcome-first"),
    )
    outcome = record_interpreted_action_outcome(
        supervisor,
        interpretation,
        at_ns=20,
    )
    timed_out = supervisor.advance(
        at_ns=100,
        provenance=provenance("deadline-after-outcome"),
    )

    assert outcome.state is ActionState.OUTCOME
    assert timed_out == ()
    assert supervisor.get(issued.action_id) is outcome


def test_provider_expression_cannot_become_consequence_or_interpretation() -> None:
    binding_result, supervisor, issued, consequence = executed_consequence()
    expression = ProviderExpression(
        text="The action succeeded.",
        provenance=provenance("provider-success"),
    )

    with pytest.raises(
        InvalidActionOutcomeData,
        match="WorldConsequence",
    ):
        interpret_world_consequence(
            issued,
            binding_result,
            expression,  # type: ignore[arg-type]
            provenance=provenance("provider-not-consequence"),
        )

    interpretation = interpret_world_consequence(
        issued,
        binding_result,
        consequence,
        provenance=provenance("valid-interpretation"),
    )
    with pytest.raises(
        InvalidActionOutcomeData,
        match="ActionOutcomeInterpretation",
    ):
        record_interpreted_action_outcome(
            supervisor,
            ProviderExpression(
                text="The action failed.",
                provenance=provenance("provider-failure"),
            ),  # type: ignore[arg-type]
            at_ns=20,
        )
    assert interpretation.disposition is ActionOutcomeDisposition.OUTCOME
    assert supervisor.get(issued.action_id).state is ActionState.ISSUED


def test_action_outcome_off_preserves_world_consequence_and_issued_action() -> None:
    binding_result, supervisor, issued, consequence = executed_consequence()
    box: dict[str, object] = {}

    plan = s16_capability_plan(
        enabled_ids=frozenset(
            {"CTL", "SKL", "ADMISSION", "EXEC_BIND", "WORLD_EXEC"}
        )
    )
    due = (
        EpochWorkItem(
            "outcome-interpret-1",
            "action.interpret_world_consequence",
            "consequence-ready",
        ),
        EpochWorkItem(
            "outcome-record-1",
            "action.record_interpreted_outcome",
            "consequence-ready",
        ),
    )
    epoch = compile_epoch_plan(
        plan,
        S16_DESCRIPTOR_SET,
        due_items=due,
        bindings=(),
    )
    result = coordinate_planned_epoch(
        supervisor,
        epoch,
        bindings=(),
        at_ns=20,
        provenance=provenance("outcome-off"),
    )

    assert result.suppressed_work_ids == (
        "outcome-interpret-1",
        "outcome-record-1",
    )
    assert supervisor.get(issued.action_id).state is ActionState.ISSUED
    assert consequence.status is WorldConsequenceStatus.EXECUTED
    assert binding_result.action_id == issued.action_id
    assert box == {}


def test_action_closure_does_not_mutate_skill_learning_memory_or_belief() -> None:
    (
        attention,
        belief,
        concept,
        wait_prediction,
        move_prediction,
        plan,
        repertoire,
        habit,
        route,
        control,
        owner,
        criterion,
        admission,
        skill,
        proposed,
        binding_result,
        authorized,
        supervisor,
        issued,
    ) = issued_chain()
    assert skill is not None
    command = build_mineflayer_command(issued, binding_result)
    consequence = asyncio.run(
        execute_mineflayer_command(
            successful_session(command),
            command,
            provenance=provenance("closure-consequence"),
        )
    )
    interpretation = interpret_world_consequence(
        issued,
        binding_result,
        consequence,
        provenance=provenance("closure-interpretation"),
    )

    cognition = PersistentCognition(
        identity=IdentitySpecification(
            self_id="s16-self",
            directives=("do not auto-learn Action outcomes",),
            provenance=provenance("identity"),
        ),
        memories=(
            Memory(
                memory_id="existing",
                content="existing",
                source_provenance=provenance("memory-source"),
                integration_provenance=provenance("memory-integration"),
            ),
        ),
    )
    learned = LearningPreferenceState(
        target_id="risk_weight",
        value=3,
        minimum=0,
        maximum=10,
        revision=0,
        origin_provenance=provenance("learning"),
    )

    before = (
        cognition.memories,
        owner.events,
        skill,
        attention,
        belief,
        concept,
        wait_prediction,
        move_prediction,
        plan,
        repertoire,
        habit,
        route,
        control,
        admission,
        proposed,
        authorized,
    )
    closed = record_interpreted_action_outcome(
        supervisor,
        interpretation,
        at_ns=20,
    )

    assert closed.state is ActionState.OUTCOME
    assert cognition.memories == before[0]
    assert owner.events == before[1]
    assert skill == before[2]
    assert skill.state is SkillState.STARTED
    assert attention == before[3]
    assert belief == before[4]
    assert concept == before[5]
    assert wait_prediction == before[6]
    assert move_prediction == before[7]
    assert plan == before[8]
    assert repertoire == before[9]
    assert habit == before[10]
    assert route == before[11]
    assert control == before[12]
    assert admission == before[13]
    assert proposed == before[14]
    assert authorized == before[15]
    assert learned.value == 3
    assert learned.revision == 0

    with pytest.raises(InvalidLearningData, match="LearningFeedback"):
        propose_learning_update(
            learned,
            interpretation,  # type: ignore[arg-type]
            LearningUpdateRule(
                rule_id="bounded-step",
                version=1,
                step=1,
            ),
        )


def test_full_deterministic_evidence_to_action_outcome_uses_zero_provider_calls() -> None:
    (
        attention,
        belief,
        concept,
        wait_prediction,
        move_prediction,
        plan,
        repertoire,
        habit,
        route,
        control,
        owner,
        criterion,
        admission,
        skill,
        proposed,
        binding_result,
        authorized,
        supervisor,
        issued,
    ) = issued_chain()

    assert attention is not None
    assert belief is not None
    assert concept is not None
    assert wait_prediction is not None
    assert move_prediction is not None
    assert plan.selected is not None
    assert plan.selected.candidate_id == "MOVE_AWAY"
    assert habit.selected_candidate_ref == "MOVE_AWAY"
    assert route.status is RouteDecisionStatus.AGREED
    assert control is not None
    assert admission is not None
    assert admission.status is AdmissionDecisionStatus.ADMITTED
    assert skill is not None
    assert skill.state is SkillState.STARTED
    assert proposed is not None
    assert proposed.state is ActionState.PROPOSED
    assert authorized.state is ActionState.AUTHORIZED
    assert issued.state is ActionState.ISSUED

    command = build_mineflayer_command(issued, binding_result)
    consequence = asyncio.run(
        execute_mineflayer_command(
            successful_session(command),
            command,
            provenance=provenance("full-consequence"),
        )
    )
    interpretation = interpret_world_consequence(
        issued,
        binding_result,
        consequence,
        provenance=provenance("full-interpretation"),
    )
    closed = record_interpreted_action_outcome(
        supervisor,
        interpretation,
        at_ns=20,
    )

    assert closed.state is ActionState.OUTCOME
    assert closed.events[-1].provenance == consequence.provenance
    assert skill.state is SkillState.STARTED
    assert owner.current_intent is not None
    assert owner.current_intent.intent_id == "escape-threat"
    assert repertoire.rules[0].candidate_ref == "MOVE_AWAY"
    assert criterion.allowed_candidate_refs == ("MOVE_AWAY",)
    provider_calls: list[object] = []
    assert provider_calls == []
