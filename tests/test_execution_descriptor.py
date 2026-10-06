import importlib

import pytest

import relay_self
from relay_self.capability import (
    CapabilityPlan,
    CapabilitySpec,
    UnsatisfiedCapabilityDependency,
)
from relay_self.execution_descriptor import (
    S2_CAPABILITY_SPECS,
    S2_DESCRIPTOR_SET,
    CapabilityDescriptorSet,
    CriterionDescriptor,
    CriterionKind,
    CrossCapabilityDescriptor,
    InvalidExecutionDescriptor,
    MissingExecutionDescriptor,
    OperatorDescriptor,
    OperatorEffect,
    s2_capability_plan,
)


def resolve_ref(reference: str) -> object:
    parts = reference.split(".")
    for split in range(len(parts), 0, -1):
        module_name = ".".join(parts[:split])
        try:
            value: object = importlib.import_module(module_name)
        except ModuleNotFoundError:
            continue
        for attribute in parts[split:]:
            value = getattr(value, attribute)
        return value
    raise AssertionError(f"cannot resolve descriptor reference: {reference}")


def test_package_exports_s2_descriptor_types() -> None:
    assert relay_self.OperatorDescriptor is OperatorDescriptor
    assert relay_self.CriterionDescriptor is CriterionDescriptor
    assert relay_self.CapabilityDescriptorSet is CapabilityDescriptorSet
    assert relay_self.s2_capability_plan is s2_capability_plan


def test_s2_scope_is_exactly_existing_mem_ctl_skl_talk_slice() -> None:
    assert [spec.capability_id for spec in S2_CAPABILITY_SPECS] == [
        "MEM",
        "CTL",
        "SKL",
        "TALK",
    ]
    skill = next(
        spec for spec in S2_CAPABILITY_SPECS
        if spec.capability_id == "SKL"
    )
    assert skill.dependencies == ("CTL",)


def test_s2_enables_nothing_implicitly() -> None:
    plan = s2_capability_plan()

    assert plan.enabled_ids == frozenset()
    assert plan.enabled_specs == ()


def test_s2_skill_still_requires_control_capability() -> None:
    with pytest.raises(
        UnsatisfiedCapabilityDependency,
        match="SKL has disabled dependency: CTL",
    ):
        s2_capability_plan(enabled_ids=frozenset({"SKL"}))

    plan = s2_capability_plan(enabled_ids=frozenset({"CTL", "SKL"}))
    assert plan.enabled_ids == frozenset({"CTL", "SKL"})


def test_every_s2_descriptor_points_to_a_real_existing_python_seam() -> None:
    for descriptor in S2_DESCRIPTOR_SET.operators:
        assert resolve_ref(descriptor.implementation_ref) is not None
    for descriptor in S2_DESCRIPTOR_SET.criteria:
        assert resolve_ref(descriptor.implementation_ref) is not None


def test_s2_descriptors_do_not_admit_hidden_persistent_operator_state() -> None:
    assert all(
        descriptor.hidden_persistent_state is False
        for descriptor in S2_DESCRIPTOR_SET.operators
    )

    with pytest.raises(
        InvalidExecutionDescriptor,
        match="hidden persistent state",
    ):
        OperatorDescriptor(
            operator_id="bad",
            capability_id="MEM",
            implementation_ref=(
                "relay_self.persistent_cognition."
                "PersistentCognition.retain_memory"
            ),
            reads=(),
            writes=(),
            effect=OperatorEffect.OWNER_TRANSITION,
            hidden_persistent_state=True,
        )


def test_s2_criteria_are_contract_guards_not_invented_cognitive_objectives() -> None:
    assert S2_DESCRIPTOR_SET.criteria
    assert all(
        descriptor.kind is CriterionKind.CONTRACT_GUARD
        for descriptor in S2_DESCRIPTOR_SET.criteria
    )
    assert all(
        descriptor.mutates_state is False
        for descriptor in S2_DESCRIPTOR_SET.criteria
    )


def test_criterion_descriptor_cannot_acquire_state_mutation() -> None:
    with pytest.raises(
        InvalidExecutionDescriptor,
        match="cannot mutate state",
    ):
        CriterionDescriptor(
            criterion_id="bad",
            capability_id="CTL",
            implementation_ref=(
                "relay_self.runtime_coordination.coordinate_decision_epoch"
            ),
            reads=("present",),
            kind=CriterionKind.CONTRACT_GUARD,
            semantics="bad criterion",
            mutates_state=True,
        )


def test_descriptor_set_detects_missing_operator_reference() -> None:
    descriptor_set = CapabilityDescriptorSet()
    spec = CapabilitySpec(
        capability_id="MEM",
        operator_ids=("mem.missing",),
    )

    with pytest.raises(
        MissingExecutionDescriptor,
        match="mem.missing",
    ):
        descriptor_set.validate_spec(spec)


def test_descriptor_set_detects_cross_capability_operator_reference() -> None:
    descriptor_set = CapabilityDescriptorSet(
        operators=(
            OperatorDescriptor(
                operator_id="shared-looking",
                capability_id="MEM",
                implementation_ref=(
                    "relay_self.persistent_cognition."
                    "PersistentCognition.retain_memory"
                ),
                reads=("durable.memory",),
                writes=("durable.memory",),
                effect=OperatorEffect.OWNER_TRANSITION,
            ),
        )
    )
    control_spec = CapabilitySpec(
        capability_id="CTL",
        operator_ids=("shared-looking",),
    )

    with pytest.raises(
        CrossCapabilityDescriptor,
        match="owned by capability MEM",
    ):
        descriptor_set.validate_spec(control_spec)


def test_descriptor_validation_is_metadata_only_and_does_not_run_seams(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls: list[object] = []

    def forbidden(*args: object, **kwargs: object) -> None:
        calls.append((args, kwargs))
        raise AssertionError("runtime seam must not execute")

    monkeypatch.setattr(
        "relay_self.runtime_coordination.coordinate_decision_epoch",
        forbidden,
    )
    monkeypatch.setattr(
        "relay_self.persistent_cognition.PersistentCognition.retain_memory",
        forbidden,
    )

    plan = CapabilityPlan(
        specs=S2_CAPABILITY_SPECS,
        enabled_ids=frozenset({"MEM", "CTL"}),
    )
    S2_DESCRIPTOR_SET.validate_plan(plan)

    assert calls == []


def test_operator_effects_record_existing_seam_class_without_dispatch() -> None:
    effects = {
        descriptor.operator_id: descriptor.effect
        for descriptor in S2_DESCRIPTOR_SET.operators
    }

    assert effects["mem.retain"] is OperatorEffect.OWNER_TRANSITION
    assert effects["ctl.coordinate_decision_epoch"] is OperatorEffect.COORDINATION
    assert effects["ctl.bounded_cognition"] is OperatorEffect.COGNITION_CALL
    assert effects["skl.start_execution"] is OperatorEffect.OWNER_TRANSITION
    assert effects["skl.propose_action"] is OperatorEffect.OWNER_TRANSITION
    assert effects["talk.open_cognition"] is OperatorEffect.COGNITION_CALL
