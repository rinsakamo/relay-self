from __future__ import annotations

import asyncio
from collections import deque
from dataclasses import replace

import pytest

from adapters.mineflayer.execution import (
    MOVE_BACKWARD_ACTION_REF,
    MOVE_BACKWARD_CONTROL,
    InvalidMineflayerExecutionData,
    MineflayerCommand,
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
from relay_self.action import ActionLifecycle, ActionState, InvalidActionData
from relay_self.action_supervision import ActionSupervisor
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
    InvalidExecutionBindingData,
    resolve_execution_binding,
    start_and_propose_bound_execution,
)
from relay_self.execution_descriptor import (
    S15_DESCRIPTOR_SET,
    S15_WORLD_EXEC_CAPABILITY_SPEC,
    S15_WORLD_EXEC_COMMAND_OPERATOR_DESCRIPTOR,
    S15_WORLD_EXEC_CRITERION_DESCRIPTOR,
    S15_WORLD_EXEC_EXECUTE_OPERATOR_DESCRIPTOR,
    CriterionKind,
    OperatorEffect,
    s15_capability_plan,
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
        source="s15-mineflayer-execution-qualification",
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


def test_world_exec_descriptor_is_integration_only_contract_guard() -> None:
    assert S15_WORLD_EXEC_CAPABILITY_SPEC.capability_id == "WORLD_EXEC"
    assert S15_WORLD_EXEC_CAPABILITY_SPEC.state_scopes == ()
    assert S15_WORLD_EXEC_CAPABILITY_SPEC.dependencies == ("EXEC_BIND",)
    assert (
        S15_WORLD_EXEC_COMMAND_OPERATOR_DESCRIPTOR.effect
        is OperatorEffect.READ_ONLY
    )
    assert (
        S15_WORLD_EXEC_EXECUTE_OPERATOR_DESCRIPTOR.effect
        is OperatorEffect.COORDINATION
    )
    assert (
        S15_WORLD_EXEC_CRITERION_DESCRIPTOR.kind
        is CriterionKind.CONTRACT_GUARD
    )


def test_proposed_action_cannot_build_physical_command() -> None:
    *_, proposed, binding_result = s14_chain()[-3:]
    assert proposed is not None
    assert binding_result is not None
    assert proposed.state is ActionState.PROPOSED
    with pytest.raises(
        InvalidMineflayerExecutionData,
        match="ISSUED",
    ):
        build_mineflayer_command(proposed, binding_result)


def test_authorized_action_cannot_build_physical_command() -> None:
    *_, proposed, binding_result = s14_chain()[-3:]
    assert proposed is not None
    assert binding_result is not None
    authorized = proposed.authorize(
        at_ns=11,
        provenance=provenance("authorized"),
        authority="explicit-authority",
    )
    with pytest.raises(
        InvalidMineflayerExecutionData,
        match="ISSUED",
    ):
        build_mineflayer_command(authorized, binding_result)


def test_issued_action_requires_exact_binding_result() -> None:
    *_, binding_result, _, _, issued = issued_chain()[-4:]
    assert binding_result is not None
    with pytest.raises(
        InvalidMineflayerExecutionData,
        match="ExecutionBindingResult",
    ):
        build_mineflayer_command(issued, None)  # type: ignore[arg-type]

    wrong_action = replace(binding_result, action_id="other-action")
    with pytest.raises(InvalidMineflayerExecutionData, match="action_id"):
        build_mineflayer_command(issued, wrong_action)

    wrong_skill = replace(
        binding_result,
        skill_execution_id="other-skill",
    )
    with pytest.raises(
        InvalidMineflayerExecutionData,
        match="skill_execution_id",
    ):
        build_mineflayer_command(issued, wrong_skill)

    wrong_intent = replace(binding_result, intent_id="other-intent")
    with pytest.raises(InvalidMineflayerExecutionData, match="intent_id"):
        build_mineflayer_command(issued, wrong_intent)


def test_exact_issued_binding_builds_only_closed_move_backward_command() -> None:
    *_, binding_result, _, supervisor, issued = issued_chain()[-4:]
    command = build_mineflayer_command(issued, binding_result)
    assert command.action_id == issued.action_id
    assert command.binding_id == binding_result.binding_id
    assert command.action_ref == MOVE_BACKWARD_ACTION_REF
    assert command.effect == "set_control"
    assert command.control == MOVE_BACKWARD_CONTROL
    assert command.state is True
    assert command.duration_s == 0.20
    assert supervisor.get(issued.action_id) == issued
    assert issued.state is ActionState.ISSUED


def test_unsupported_or_malformed_action_ref_fails_closed() -> None:
    *_, binding_result, _, _, issued = issued_chain()[-4:]
    unsupported = replace(binding_result, action_ref="ATTACK")
    with pytest.raises(
        InvalidMineflayerExecutionData,
        match="unsupported S15 action_ref",
    ):
        build_mineflayer_command(issued, unsupported)

    with pytest.raises(InvalidExecutionBindingData, match="structured identifier"):
        replace(binding_result, action_ref="MOVE BACKWARD")


def test_successful_bounded_adapter_execution_requires_observed_movement() -> None:
    *_, binding_result, _, supervisor, issued = issued_chain()[-4:]
    command = build_mineflayer_command(issued, binding_result)
    adapter = successful_session(command)
    consequence = asyncio.run(
        execute_mineflayer_command(
            adapter,
            command,
            provenance=provenance("world-consequence"),
        )
    )
    assert consequence.status is WorldConsequenceStatus.EXECUTED
    assert consequence.movement_distance == pytest.approx(0.20)
    assert consequence.dispatch_receipt is not None
    assert consequence.dispatch_receipt.result == "applied"
    assert consequence.cleanup_receipt is not None
    assert consequence.cleanup_receipt.result == "applied"
    assert consequence.before_observation is not None
    assert consequence.after_observation is not None
    assert consequence.cleanup_attempted is True
    assert adapter.sent == [
        ("observe",),
        ("set_control", issued.action_id, "back", True),
        ("clear_controls", command.cleanup_action_id),
        ("observe",),
    ]
    assert supervisor.get(issued.action_id).state is ActionState.ISSUED


def test_applied_command_without_observed_movement_is_undetermined() -> None:
    *_, binding_result, _, _, issued = issued_chain()[-4:]
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
            provenance=provenance("undetermined"),
        )
    )
    assert consequence.status is WorldConsequenceStatus.UNDETERMINED
    assert consequence.movement_distance == 0.0
    assert consequence.error is None


def test_disconnected_adapter_returns_failed_without_fabricated_after_state() -> None:
    *_, binding_result, _, supervisor, issued = issued_chain()[-4:]
    command = build_mineflayer_command(issued, binding_result)
    adapter = FakeSession()
    adapter.fail_observe = True
    consequence = asyncio.run(
        execute_mineflayer_command(
            adapter,
            command,
            provenance=provenance("disconnected"),
        )
    )
    assert consequence.status is WorldConsequenceStatus.FAILED
    assert consequence.before_observation is None
    assert consequence.after_observation is None
    assert consequence.dispatch_receipt is None
    assert consequence.error is not None
    assert supervisor.get(issued.action_id).state is ActionState.ISSUED
    assert adapter.sent == [("observe",)]


def test_dispatch_error_has_no_retry_and_best_effort_cleanup_is_bounded() -> None:
    *_, binding_result, _, _, issued = issued_chain()[-4:]
    command = build_mineflayer_command(issued, binding_result)
    adapter = FakeSession((observation(1, 0.0, 0.0),))
    adapter.fail_set_control = True
    consequence = asyncio.run(
        execute_mineflayer_command(
            adapter,
            command,
            provenance=provenance("dispatch-error"),
        )
    )
    assert consequence.status is WorldConsequenceStatus.FAILED
    assert adapter.sent.count(
        ("set_control", issued.action_id, "back", True)
    ) == 1
    assert adapter.sent.count(
        ("clear_controls", command.cleanup_action_id)
    ) == 1


def test_provider_text_cannot_grant_authority_build_command_or_consequence() -> None:
    *_, proposed, binding_result = s14_chain()[-3:]
    assert proposed is not None
    assert binding_result is not None
    expression = ProviderExpression(
        text="authorized",
        provenance=provenance("provider-authorized"),
    )
    with pytest.raises(InvalidActionData, match="authorization authority"):
        proposed.authorize(
            at_ns=11,
            provenance=provenance("bad-provider-authority"),
            authority=expression,  # type: ignore[arg-type]
        )
    with pytest.raises(
        InvalidMineflayerExecutionData,
        match="ExecutionBindingResult",
    ):
        build_mineflayer_command(
            proposed,
            ProviderExpression(
                text="move backward",
                provenance=provenance("provider-command"),
            ),  # type: ignore[arg-type]
        )
    with pytest.raises(
        InvalidMineflayerExecutionData,
        match="adapter",
    ):
        asyncio.run(
            execute_mineflayer_command(
                ProviderExpression(
                    text="the move succeeded",
                    provenance=provenance("provider-success"),
                ),  # type: ignore[arg-type]
                MineflayerCommand(
                    action_id="a",
                    binding_id="b",
                    action_ref="MOVE_BACKWARD",
                    effect="set_control",
                    control="back",
                    state=True,
                    duration_s=0.20,
                    cleanup_action_id="a-clear",
                ),
                provenance=provenance("provider-not-world"),
            )
        )


def test_world_exec_off_leaves_issued_authority_without_adapter_work() -> None:
    *_, binding_result, _, supervisor, issued = issued_chain()[-4:]
    box: dict[str, object] = {}
    due = (
        EpochWorkItem(
            "world-build-1",
            "world.build_mineflayer_command",
            "world-exec-disabled",
        ),
        EpochWorkItem(
            "world-execute-1",
            "world.execute_mineflayer_command",
            "world-exec-disabled",
        ),
    )
    plan = s15_capability_plan(
        enabled_ids=frozenset({"CTL", "SKL", "ADMISSION", "EXEC_BIND"})
    )
    epoch = compile_epoch_plan(
        plan,
        S15_DESCRIPTOR_SET,
        due_items=due,
        bindings=(),
    )
    result = coordinate_planned_epoch(
        supervisor,
        epoch,
        bindings=(),
        at_ns=20,
        provenance=provenance("world-exec-off"),
    )
    assert result.suppressed_work_ids == (
        "world-build-1",
        "world-execute-1",
    )
    assert supervisor.get(issued.action_id).state is ActionState.ISSUED
    assert binding_result.action_ref == MOVE_BACKWARD_ACTION_REF
    assert box == {}


def test_action_supervisor_deadline_processing_precedes_world_exec_work() -> None:
    current = s14_chain()
    proposed = current[14]
    binding_result = current[15]
    assert proposed is not None
    assert binding_result is not None
    authorized = proposed.authorize(
        at_ns=11,
        provenance=provenance("current-authorization"),
        authority="current-authority",
    )
    supervisor = ActionSupervisor()

    prior_owner = intent_owner()
    from relay_self.skill import SkillExecution

    prior_skill = SkillExecution.start(
        "prior-skill",
        skill_id="WAIT",
        intent_commitment=prior_owner,
        at_ns=2,
        provenance=provenance("prior-skill"),
    )
    prior = ActionLifecycle.propose(
        "prior-action",
        skill_execution=prior_skill,
        intent_commitment=prior_owner,
        at_ns=3,
        provenance=provenance("prior-proposal"),
    ).authorize(
        at_ns=4,
        provenance=provenance("prior-authorization"),
        authority="prior-authority",
    )
    supervisor.issue(
        prior,
        at_ns=5,
        deadline_ns=13,
        provenance=provenance("prior-issue"),
    )
    issued = supervisor.issue(
        authorized,
        at_ns=12,
        deadline_ns=100,
        provenance=provenance("current-issue"),
    )

    seen: list[ActionState] = []
    from relay_self.epoch_plan import EpochBinding

    def build_work() -> None:
        seen.append(supervisor.get("prior-action").state)
        build_mineflayer_command(issued, binding_result)

    binding_work = EpochBinding(
        "world-build-1",
        "world.build_mineflayer_command",
        build_work,
    )
    plan = s15_capability_plan(
        enabled_ids=frozenset(
            {"CTL", "SKL", "ADMISSION", "EXEC_BIND", "WORLD_EXEC"}
        )
    )
    epoch = compile_epoch_plan(
        plan,
        S15_DESCRIPTOR_SET,
        due_items=(
            EpochWorkItem(
                "world-build-1",
                "world.build_mineflayer_command",
                "issued-ready",
            ),
        ),
        bindings=(binding_work,),
    )
    result = coordinate_planned_epoch(
        supervisor,
        epoch,
        bindings=(binding_work,),
        at_ns=13,
        provenance=provenance("supervision-first"),
    )
    assert seen == [ActionState.TIMEOUT]
    assert result.timed_out_actions[0].action_id == "prior-action"
    assert supervisor.get(issued.action_id).state is ActionState.ISSUED


def test_conflict_rejection_and_binding_failure_cannot_reach_s15() -> None:
    conflict = s14_chain(wait_score=1, move_score=5)
    assert conflict[8].status is RouteDecisionStatus.CONFLICT
    assert conflict[9] is None
    assert conflict[12] is None
    assert conflict[13] is None
    assert conflict[14] is None
    assert conflict[15] is None

    rejected = s14_chain(allowed=("WAIT",))
    assert rejected[12] is not None
    assert rejected[12].status is AdmissionDecisionStatus.REJECTED
    assert rejected[13] is None
    assert rejected[14] is None
    assert rejected[15] is None

    valid = s14_chain()
    control = valid[9]
    admission = valid[12]
    assert control is not None
    assert admission is not None
    with pytest.raises(InvalidExecutionBindingData, match="candidate_ref"):
        resolve_execution_binding(
            admission,
            control,
            valid[8],
            valid[10],
            valid[11],
            replace(binding(), candidate_ref="WAIT"),
            provenance=provenance("binding-failure"),
        )


def test_world_consequence_does_not_trigger_learning_memory_or_action_closure() -> None:
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
    assert control is not None
    assert admission is not None
    assert skill is not None
    command = build_mineflayer_command(issued, binding_result)
    consequence = asyncio.run(
        execute_mineflayer_command(
            successful_session(command),
            command,
            provenance=provenance("consequence"),
        )
    )
    cognition = PersistentCognition(
        identity=IdentitySpecification(
            self_id="s15-self",
            directives=("do not auto-learn world consequences",),
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
        skill,
        proposed,
        authorized,
        supervisor.get(issued.action_id),
    )
    with pytest.raises(InvalidLearningData, match="LearningFeedback"):
        propose_learning_update(
            learned,
            consequence,  # type: ignore[arg-type]
            LearningUpdateRule(
                rule_id="bounded-step",
                version=1,
                step=1,
            ),
        )
    assert cognition.memories == before[0]
    assert owner.events == before[1]
    assert attention == before[2]
    assert belief == before[3]
    assert concept == before[4]
    assert wait_prediction == before[5]
    assert move_prediction == before[6]
    assert plan == before[7]
    assert repertoire == before[8]
    assert habit == before[9]
    assert route == before[10]
    assert control == before[11]
    assert admission == before[12]
    assert skill == before[13]
    assert proposed == before[14]
    assert authorized == before[15]
    assert supervisor.get(issued.action_id) == before[16]
    assert learned.value == 3
    assert learned.revision == 0


def test_full_deterministic_evidence_to_issued_to_world_consequence_uses_no_model() -> None:
    invocations = {
        "ATT": 1,
        "BLF": 1,
        "CNC": 1,
        "PRD": 2,
        "PLAN": 1,
        "HABIT": 1,
        "ROUTE": 1,
        "ADMISSION": 1,
        "EXEC_BIND": 2,
        "ACTION_AUTHORITY": 2,
        "MINEFLAYER_ADAPTER": 1,
        "PROVIDER": 0,
    }
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
            provenance=provenance("full-world-consequence"),
        )
    )
    assert consequence.status is WorldConsequenceStatus.EXECUTED
    assert supervisor.get(issued.action_id).state is ActionState.ISSUED
    assert owner.current_intent is not None
    assert owner.current_intent.intent_id == "escape-threat"
    assert repertoire.rules[0].candidate_ref == "MOVE_AWAY"
    assert criterion.allowed_candidate_refs == ("MOVE_AWAY",)
    assert invocations["PROVIDER"] == 0
