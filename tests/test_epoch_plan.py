import pytest

import relay_self
from relay_self.action import ActionLifecycle, ActionState
from relay_self.action_supervision import ActionSupervisor
from relay_self.epoch_plan import (
    CognitionInvocation,
    CognitionStepOrderingError,
    EpochBinding,
    EpochBindingMismatch,
    EpochWorkItem,
    InvalidEpochPlanData,
    MultipleCognitionSteps,
    NestedCoordinationOperator,
    UnexpectedEpochBinding,
    UnknownEpochOperator,
    compile_epoch_plan,
    coordinate_planned_epoch,
)
from relay_self.execution_descriptor import (
    S2_DESCRIPTOR_SET,
    s2_capability_plan,
)
from relay_self.intent import IntentCommitment
from relay_self.persistent_cognition import (
    IdentitySpecification,
    Memory,
    PersistentCognition,
)
from relay_self.provenance import Provenance
from relay_self.skill import SkillExecution


def provenance(reference: str) -> Provenance:
    return Provenance(source="epoch-plan-test", reference=reference)


def running_supervisor(
    *,
    deadline_ns: int = 50,
) -> ActionSupervisor:
    commitment = IntentCommitment()
    commitment.commit(
        "intent-1",
        objective="reach safety",
        at_ns=1,
        provenance=provenance("intent"),
    )
    skill = SkillExecution.start(
        "skill-1",
        skill_id="FLEE",
        intent_commitment=commitment,
        at_ns=2,
        provenance=provenance("skill"),
    )
    action = ActionLifecycle.propose(
        "action-1",
        skill_execution=skill,
        intent_commitment=commitment,
        at_ns=3,
        provenance=provenance("proposal"),
    ).authorize(
        at_ns=4,
        provenance=provenance("authorization"),
        authority="test-authority",
    )
    supervisor = ActionSupervisor()
    supervisor.issue(
        action,
        at_ns=5,
        deadline_ns=deadline_ns,
        provenance=provenance("issue"),
    )
    return supervisor


def test_package_exports_s3_epoch_plan_types() -> None:
    assert relay_self.EpochWorkItem is EpochWorkItem
    assert relay_self.EpochBinding is EpochBinding
    assert relay_self.CognitionInvocation is CognitionInvocation
    assert relay_self.compile_epoch_plan is compile_epoch_plan
    assert relay_self.coordinate_planned_epoch is coordinate_planned_epoch


def test_compile_is_metadata_only_and_does_not_invoke_binding() -> None:
    calls: list[str] = []
    plan = s2_capability_plan(enabled_ids=frozenset({"MEM"}))
    binding = EpochBinding(
        work_id="retain-1",
        operator_id="mem.retain",
        invoke=lambda: calls.append("ran"),
    )

    compiled = compile_epoch_plan(
        plan,
        S2_DESCRIPTOR_SET,
        due_items=(
            EpochWorkItem(
                work_id="retain-1",
                operator_id="mem.retain",
                trigger_ref="governed-retention-1",
            ),
        ),
        bindings=(binding,),
    )

    assert [step.work_id for step in compiled.steps] == ["retain-1"]
    assert compiled.suppressed == ()
    assert calls == []


def test_capability_off_suppresses_due_work_without_requiring_binding() -> None:
    plan = s2_capability_plan()

    compiled = compile_epoch_plan(
        plan,
        S2_DESCRIPTOR_SET,
        due_items=(
            EpochWorkItem(
                work_id="retain-1",
                operator_id="mem.retain",
                trigger_ref="governed-retention-1",
            ),
        ),
        bindings=(),
    )

    assert compiled.steps == ()
    assert [item.work_id for item in compiled.suppressed] == ["retain-1"]


def test_binding_for_suppressed_work_is_rejected_instead_of_hidden() -> None:
    plan = s2_capability_plan()
    binding = EpochBinding(
        work_id="retain-1",
        operator_id="mem.retain",
        invoke=lambda: None,
    )

    with pytest.raises(
        UnexpectedEpochBinding,
        match="retain-1",
    ):
        compile_epoch_plan(
            plan,
            S2_DESCRIPTOR_SET,
            due_items=(
                EpochWorkItem(
                    work_id="retain-1",
                    operator_id="mem.retain",
                    trigger_ref="retention",
                ),
            ),
            bindings=(binding,),
        )


def test_unknown_due_operator_fails_closed() -> None:
    plan = s2_capability_plan(enabled_ids=frozenset({"MEM"}))

    with pytest.raises(
        UnknownEpochOperator,
        match="unknown operator",
    ):
        compile_epoch_plan(
            plan,
            S2_DESCRIPTOR_SET,
            due_items=(
                EpochWorkItem(
                    work_id="unknown-1",
                    operator_id="mem.not-real",
                    trigger_ref="trigger",
                ),
            ),
            bindings=(),
        )


def test_binding_operator_must_match_due_operator() -> None:
    plan = s2_capability_plan(enabled_ids=frozenset({"MEM"}))

    with pytest.raises(
        EpochBindingMismatch,
        match="expects mem.retain",
    ):
        compile_epoch_plan(
            plan,
            S2_DESCRIPTOR_SET,
            due_items=(
                EpochWorkItem(
                    work_id="retain-1",
                    operator_id="mem.retain",
                    trigger_ref="retention",
                ),
            ),
            bindings=(
                EpochBinding(
                    work_id="retain-1",
                    operator_id="talk.open_cognition",
                    invoke=lambda: None,
                ),
            ),
        )


def test_outer_coordination_operator_cannot_be_nested_as_inner_work() -> None:
    plan = s2_capability_plan(enabled_ids=frozenset({"CTL"}))

    with pytest.raises(
        NestedCoordinationOperator,
        match="cannot be inner epoch work",
    ):
        compile_epoch_plan(
            plan,
            S2_DESCRIPTOR_SET,
            due_items=(
                EpochWorkItem(
                    work_id="nested-1",
                    operator_id="ctl.coordinate_decision_epoch",
                    trigger_ref="decision-epoch",
                ),
            ),
            bindings=(),
        )


def test_one_epoch_allows_at_most_one_cognition_call() -> None:
    plan = s2_capability_plan(
        enabled_ids=frozenset({"CTL", "TALK"})
    )
    items = (
        EpochWorkItem(
            work_id="bounded-1",
            operator_id="ctl.bounded_cognition",
            trigger_ref="bounded-request",
        ),
        EpochWorkItem(
            work_id="talk-1",
            operator_id="talk.open_cognition",
            trigger_ref="expression-request",
        ),
    )
    bindings = tuple(
        EpochBinding(
            work_id=item.work_id,
            operator_id=item.operator_id,
            invoke=lambda: CognitionInvocation(
                request={"request": "unused"},
                runner=lambda request: request,
            ),
        )
        for item in items
    )

    with pytest.raises(MultipleCognitionSteps):
        compile_epoch_plan(
            plan,
            S2_DESCRIPTOR_SET,
            due_items=items,
            bindings=bindings,
        )


def test_cognition_call_must_be_final_inner_step() -> None:
    plan = s2_capability_plan(
        enabled_ids=frozenset({"CTL", "MEM"})
    )
    items = (
        EpochWorkItem(
            work_id="bounded-1",
            operator_id="ctl.bounded_cognition",
            trigger_ref="bounded-request",
        ),
        EpochWorkItem(
            work_id="retain-1",
            operator_id="mem.retain",
            trigger_ref="retention",
        ),
    )
    bindings = (
        EpochBinding(
            work_id="bounded-1",
            operator_id="ctl.bounded_cognition",
            invoke=lambda: CognitionInvocation(
                request={"request": "unused"},
                runner=lambda request: request,
            ),
        ),
        EpochBinding(
            work_id="retain-1",
            operator_id="mem.retain",
            invoke=lambda: None,
        ),
    )

    with pytest.raises(CognitionStepOrderingError):
        compile_epoch_plan(
            plan,
            S2_DESCRIPTOR_SET,
            due_items=items,
            bindings=bindings,
        )


def test_planned_epoch_services_action_supervision_before_bound_work() -> None:
    supervisor = running_supervisor(deadline_ns=50)
    observed: list[ActionState] = []
    plan = s2_capability_plan(enabled_ids=frozenset({"MEM"}))
    binding = EpochBinding(
        work_id="retain-1",
        operator_id="mem.retain",
        invoke=lambda: observed.append(
            supervisor.get("action-1").state
        ),
    )
    compiled = compile_epoch_plan(
        plan,
        S2_DESCRIPTOR_SET,
        due_items=(
            EpochWorkItem(
                work_id="retain-1",
                operator_id="mem.retain",
                trigger_ref="retention",
            ),
        ),
        bindings=(binding,),
    )

    result = coordinate_planned_epoch(
        supervisor,
        compiled,
        bindings=(binding,),
        at_ns=50,
        provenance=provenance("epoch"),
    )

    assert observed == [ActionState.TIMEOUT]
    assert [action.action_id for action in result.timed_out_actions] == [
        "action-1"
    ]
    assert result.executed_work_ids == ("retain-1",)
    assert result.cognition_requested is False


def test_mem_binding_can_call_existing_owner_transition_explicitly() -> None:
    identity = IdentitySpecification(
        self_id="self-1",
        directives=("persist governed cognition",),
        provenance=provenance("identity"),
    )
    box = {"cognition": PersistentCognition(identity=identity)}
    memory = Memory(
        memory_id="memory-1",
        content="grounded consequence",
        source_provenance=provenance("source"),
        integration_provenance=provenance("integration"),
    )

    def retain() -> None:
        box["cognition"] = box["cognition"].retain_memory(memory)

    binding = EpochBinding(
        work_id="retain-1",
        operator_id="mem.retain",
        invoke=retain,
    )
    compiled = compile_epoch_plan(
        s2_capability_plan(enabled_ids=frozenset({"MEM"})),
        S2_DESCRIPTOR_SET,
        due_items=(
            EpochWorkItem(
                work_id="retain-1",
                operator_id="mem.retain",
                trigger_ref="governed-retention",
            ),
        ),
        bindings=(binding,),
    )

    result = coordinate_planned_epoch(
        ActionSupervisor(),
        compiled,
        bindings=(binding,),
        at_ns=10,
        provenance=provenance("epoch"),
    )

    assert [value.memory_id for value in box["cognition"].memories] == [
        "memory-1"
    ]
    assert result.executed_work_ids == ("retain-1",)


def test_cognition_invocation_runs_exactly_once_through_existing_coordinator() -> None:
    requests: list[object] = []
    request = {"kind": "bounded", "choices": ("wait", "flee")}

    def run_cognition(received: object) -> dict[str, str]:
        requests.append(received)
        return {"choice": "flee"}

    binding = EpochBinding(
        work_id="bounded-1",
        operator_id="ctl.bounded_cognition",
        invoke=lambda: CognitionInvocation(
            request=request,
            runner=run_cognition,
        ),
    )
    compiled = compile_epoch_plan(
        s2_capability_plan(enabled_ids=frozenset({"CTL"})),
        S2_DESCRIPTOR_SET,
        due_items=(
            EpochWorkItem(
                work_id="bounded-1",
                operator_id="ctl.bounded_cognition",
                trigger_ref="explicit-unresolved-control",
            ),
        ),
        bindings=(binding,),
    )

    result = coordinate_planned_epoch(
        ActionSupervisor(),
        compiled,
        bindings=(binding,),
        at_ns=20,
        provenance=provenance("epoch"),
    )

    assert requests == [request]
    assert result.executed_work_ids == ("bounded-1",)
    assert result.cognition_requested is True
    assert result.cognition_result == {"choice": "flee"}


def test_cognition_binding_must_return_explicit_invocation() -> None:
    binding = EpochBinding(
        work_id="bounded-1",
        operator_id="ctl.bounded_cognition",
        invoke=lambda: {"request": "raw"},
    )
    compiled = compile_epoch_plan(
        s2_capability_plan(enabled_ids=frozenset({"CTL"})),
        S2_DESCRIPTOR_SET,
        due_items=(
            EpochWorkItem(
                work_id="bounded-1",
                operator_id="ctl.bounded_cognition",
                trigger_ref="explicit-unresolved-control",
            ),
        ),
        bindings=(binding,),
    )

    with pytest.raises(
        InvalidEpochPlanData,
        match="must return CognitionInvocation",
    ):
        coordinate_planned_epoch(
            ActionSupervisor(),
            compiled,
            bindings=(binding,),
            at_ns=20,
            provenance=provenance("epoch"),
        )


def test_non_cognition_binding_cannot_smuggle_cognition_request() -> None:
    supervisor = running_supervisor(deadline_ns=50)
    binding = EpochBinding(
        work_id="retain-1",
        operator_id="mem.retain",
        invoke=lambda: {"need": "cognition"},
    )
    compiled = compile_epoch_plan(
        s2_capability_plan(enabled_ids=frozenset({"MEM"})),
        S2_DESCRIPTOR_SET,
        due_items=(
            EpochWorkItem(
                work_id="retain-1",
                operator_id="mem.retain",
                trigger_ref="retention",
            ),
        ),
        bindings=(binding,),
    )

    with pytest.raises(
        InvalidEpochPlanData,
        match="must return None",
    ):
        coordinate_planned_epoch(
            supervisor,
            compiled,
            bindings=(binding,),
            at_ns=50,
            provenance=provenance("epoch"),
        )

    assert supervisor.get("action-1").state is ActionState.TIMEOUT


def test_execution_bindings_must_exactly_match_compiled_steps() -> None:
    binding = EpochBinding(
        work_id="retain-1",
        operator_id="mem.retain",
        invoke=lambda: None,
    )
    compiled = compile_epoch_plan(
        s2_capability_plan(enabled_ids=frozenset({"MEM"})),
        S2_DESCRIPTOR_SET,
        due_items=(
            EpochWorkItem(
                work_id="retain-1",
                operator_id="mem.retain",
                trigger_ref="retention",
            ),
        ),
        bindings=(binding,),
    )

    with pytest.raises(
        InvalidEpochPlanData,
        match="exactly match plan steps",
    ):
        coordinate_planned_epoch(
            ActionSupervisor(),
            compiled,
            bindings=(),
            at_ns=20,
            provenance=provenance("epoch"),
        )
