import pytest

import relay_self
from relay_self.capability import (
    CapabilityDependencyCycle,
    CapabilityPlan,
    CapabilitySpec,
    InvalidCapabilityData,
    UnknownCapability,
    UnsatisfiedCapabilityDependency,
)


def spec(
    capability_id: str,
    *,
    dependencies: tuple[str, ...] = (),
) -> CapabilitySpec:
    return CapabilitySpec(
        capability_id=capability_id,
        state_scopes=("present",),
        operator_ids=(f"{capability_id.lower()}-operator",),
        criterion_ids=(f"{capability_id.lower()}-criterion",),
        port_ids=(f"{capability_id.lower()}-port",),
        dependencies=dependencies,
    )


def test_package_exports_declarative_capability_types() -> None:
    assert relay_self.CapabilitySpec is CapabilitySpec
    assert relay_self.CapabilityPlan is CapabilityPlan


def test_capability_spec_is_pure_declarative_metadata() -> None:
    value = CapabilitySpec(
        capability_id="MEM",
        state_scopes=("durable.memory", "present"),
        operator_ids=("memory-retrieve",),
        criterion_ids=("retrieval-relevance",),
        port_ids=("retrieval-out",),
    )

    assert value.capability_id == "MEM"
    assert value.state_scopes == ("durable.memory", "present")
    assert value.operator_ids == ("memory-retrieve",)
    assert value.dependencies == ()


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("state_scopes", ("present", "present")),
        ("operator_ids", ("op", "op")),
        ("criterion_ids", ("criterion", "criterion")),
        ("port_ids", ("port", "port")),
        ("dependencies", ("MEM", "MEM")),
    ],
)
def test_capability_spec_rejects_duplicate_metadata(
    field: str,
    value: tuple[str, ...],
) -> None:
    kwargs = {
        "capability_id": "SKL",
        "state_scopes": (),
        "operator_ids": (),
        "criterion_ids": (),
        "port_ids": (),
        "dependencies": (),
    }
    kwargs[field] = value

    with pytest.raises(InvalidCapabilityData, match="duplicates"):
        CapabilitySpec(**kwargs)


def test_capability_spec_rejects_self_dependency() -> None:
    with pytest.raises(InvalidCapabilityData, match="depend on itself"):
        spec("SKL", dependencies=("SKL",))


def test_plan_requires_unique_declared_capability_ids() -> None:
    with pytest.raises(InvalidCapabilityData, match="duplicate capability_id"):
        CapabilityPlan(specs=(spec("MEM"), spec("MEM")))


def test_plan_rejects_undeclared_dependency() -> None:
    with pytest.raises(UnknownCapability, match="undeclared capability"):
        CapabilityPlan(specs=(spec("SKL", dependencies=("CTL",)),))


def test_plan_rejects_unknown_enabled_capability() -> None:
    with pytest.raises(UnknownCapability, match="enabled capability"):
        CapabilityPlan(
            specs=(spec("MEM"),),
            enabled_ids=frozenset({"MEM", "UNKNOWN"}),
        )


def test_plan_rejects_dependency_cycle_even_when_capabilities_are_disabled() -> None:
    with pytest.raises(CapabilityDependencyCycle):
        CapabilityPlan(
            specs=(
                spec("CTL", dependencies=("SKL",)),
                spec("SKL", dependencies=("CTL",)),
            )
        )


def test_enabled_capability_requires_enabled_dependencies() -> None:
    plan_specs = (
        spec("CTL"),
        spec("SKL", dependencies=("CTL",)),
    )

    with pytest.raises(
        UnsatisfiedCapabilityDependency,
        match="SKL has disabled dependency: CTL",
    ):
        CapabilityPlan(
            specs=plan_specs,
            enabled_ids=frozenset({"SKL"}),
        )


def test_enabled_specs_preserve_declaration_order_without_execution() -> None:
    plan = CapabilityPlan(
        specs=(
            spec("MEM"),
            spec("CTL"),
            spec("SKL", dependencies=("CTL",)),
            spec("TALK"),
        ),
        enabled_ids=frozenset({"MEM", "CTL", "SKL"}),
    )

    assert [value.capability_id for value in plan.enabled_specs] == [
        "MEM",
        "CTL",
        "SKL",
    ]


def test_with_enabled_returns_new_plan_without_mutating_original() -> None:
    original = CapabilityPlan(
        specs=(spec("MEM"), spec("TALK")),
        enabled_ids=frozenset({"MEM"}),
    )

    updated = original.with_enabled("TALK")

    assert original.enabled_ids == frozenset({"MEM"})
    assert updated.enabled_ids == frozenset({"MEM", "TALK"})
    assert original.specs is updated.specs


def test_disabling_required_dependency_fails_closed() -> None:
    plan = CapabilityPlan(
        specs=(
            spec("CTL"),
            spec("SKL", dependencies=("CTL",)),
        ),
        enabled_ids=frozenset({"CTL", "SKL"}),
    )

    with pytest.raises(
        UnsatisfiedCapabilityDependency,
        match="SKL has disabled dependency: CTL",
    ):
        plan.with_enabled("CTL", enabled=False)


def test_plan_lookup_fails_closed_for_unknown_capability() -> None:
    plan = CapabilityPlan(specs=(spec("MEM"),))

    with pytest.raises(UnknownCapability, match="not declared"):
        plan.spec("PRD")


def test_enabled_flag_must_be_boolean() -> None:
    plan = CapabilityPlan(specs=(spec("MEM"),))

    with pytest.raises(InvalidCapabilityData, match="enabled must be bool"):
        plan.with_enabled("MEM", enabled=1)  # type: ignore[arg-type]
