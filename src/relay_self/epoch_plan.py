from __future__ import annotations

from dataclasses import dataclass
from typing import Callable

from relay_self.action import ActionLifecycle
from relay_self.action_supervision import ActionSupervisor
from relay_self.capability import CapabilityPlan, UnknownCapability
from relay_self.execution_descriptor import (
    CapabilityDescriptorSet,
    OperatorDescriptor,
    OperatorEffect,
)
from relay_self.provenance import Provenance
from relay_self.runtime_coordination import (
    DecisionEpochResult,
    coordinate_decision_epoch,
)


class EpochPlanError(ValueError):
    """Base error for stateless epoch-plan compilation or execution."""


class InvalidEpochPlanData(EpochPlanError):
    """Raised when epoch-plan inputs or binding results are malformed."""


class UnknownEpochOperator(EpochPlanError):
    """Raised when due work references an operator not in the descriptor set."""


class MissingEpochBinding(EpochPlanError):
    """Raised when enabled due work has no explicit concrete binding."""


class UnexpectedEpochBinding(EpochPlanError):
    """Raised when a binding does not correspond to enabled due work."""


class EpochBindingMismatch(EpochPlanError):
    """Raised when one work binding names a different operator."""


class NestedCoordinationOperator(EpochPlanError):
    """Raised when the outer decision coordinator is scheduled as inner work."""


class MultipleCognitionSteps(EpochPlanError):
    """Raised when one epoch would make more than one cognition call."""


class CognitionStepOrderingError(EpochPlanError):
    """Raised when cognition is not the final admitted inner step."""


@dataclass(frozen=True, slots=True)
class EpochWorkItem:
    """One caller/source-admitted due item before capability filtering."""

    work_id: str
    operator_id: str
    trigger_ref: str

    def __post_init__(self) -> None:
        _require_text("work_id", self.work_id)
        _require_text("operator_id", self.operator_id)
        _require_text("trigger_ref", self.trigger_ref)


@dataclass(frozen=True, slots=True)
class EpochStep:
    """One immutable enabled step in caller-supplied due order."""

    work_id: str
    operator_id: str
    capability_id: str
    trigger_ref: str
    effect: OperatorEffect

    def __post_init__(self) -> None:
        _require_text("work_id", self.work_id)
        _require_text("operator_id", self.operator_id)
        _require_text("capability_id", self.capability_id)
        _require_text("trigger_ref", self.trigger_ref)
        if not isinstance(self.effect, OperatorEffect):
            raise InvalidEpochPlanData("step effect must be OperatorEffect")


@dataclass(frozen=True, slots=True)
class EpochPlan:
    """Stateless plan compiled from current capability selection and due work."""

    steps: tuple[EpochStep, ...]
    suppressed: tuple[EpochWorkItem, ...]

    def __post_init__(self) -> None:
        if not isinstance(self.steps, tuple) or not all(
            isinstance(value, EpochStep)
            for value in self.steps
        ):
            raise InvalidEpochPlanData("steps must be a tuple of EpochStep values")
        if not isinstance(self.suppressed, tuple) or not all(
            isinstance(value, EpochWorkItem)
            for value in self.suppressed
        ):
            raise InvalidEpochPlanData(
                "suppressed must be a tuple of EpochWorkItem values"
            )

        _require_unique(
            "step work_id",
            tuple(step.work_id for step in self.steps),
        )
        _require_unique(
            "suppressed work_id",
            tuple(item.work_id for item in self.suppressed),
        )

        overlap = {
            step.work_id
            for step in self.steps
        }.intersection(item.work_id for item in self.suppressed)
        if overlap:
            raise InvalidEpochPlanData(
                "one work item cannot be both scheduled and suppressed: "
                + ", ".join(sorted(overlap))
            )

        if any(
            step.effect is OperatorEffect.COORDINATION
            for step in self.steps
        ):
            raise NestedCoordinationOperator(
                "EpochPlan cannot contain an inner coordination operator"
            )

        cognition_positions = [
            index
            for index, step in enumerate(self.steps)
            if step.effect is OperatorEffect.COGNITION_CALL
        ]
        if len(cognition_positions) > 1:
            raise MultipleCognitionSteps(
                "one epoch may contain at most one cognition-call step"
            )
        if cognition_positions and cognition_positions[0] != len(self.steps) - 1:
            raise CognitionStepOrderingError(
                "cognition-call step must be the final inner epoch step"
            )

    @property
    def cognition_step(self) -> EpochStep | None:
        values = tuple(
            step
            for step in self.steps
            if step.effect is OperatorEffect.COGNITION_CALL
        )
        if not values:
            return None
        if len(values) != 1:
            raise InvalidEpochPlanData(
                "compiled EpochPlan contains multiple cognition steps"
            )
        return values[0]


@dataclass(frozen=True, slots=True)
class CognitionInvocation:
    """Explicit request plus explicitly supplied execution runner.

    The runner is not discovered from descriptor metadata. It is supplied by
    the caller that owns the concrete runtime integration.
    """

    request: object
    runner: Callable[[object], object]

    def __post_init__(self) -> None:
        if self.request is None:
            raise InvalidEpochPlanData("cognition request cannot be None")
        if not callable(self.runner):
            raise InvalidEpochPlanData("cognition runner must be callable")


@dataclass(frozen=True, slots=True)
class EpochBinding:
    """Caller-owned concrete binding for exactly one due work item."""

    work_id: str
    operator_id: str
    invoke: Callable[[], object | None]

    def __post_init__(self) -> None:
        _require_text("work_id", self.work_id)
        _require_text("operator_id", self.operator_id)
        if not callable(self.invoke):
            raise InvalidEpochPlanData("epoch binding invoke must be callable")


@dataclass(frozen=True, slots=True)
class PlannedDecisionEpochResult:
    """Result of running one immutable plan through the admitted coordinator."""

    decision: DecisionEpochResult[object]
    executed_work_ids: tuple[str, ...]
    suppressed_work_ids: tuple[str, ...]

    @property
    def timed_out_actions(self) -> tuple[ActionLifecycle, ...]:
        return self.decision.timed_out_actions

    @property
    def cognition_requested(self) -> bool:
        return self.decision.cognition_requested

    @property
    def cognition_result(self) -> object | None:
        return self.decision.cognition_result

    @property
    def next_action_deadline_ns(self) -> int | None:
        return self.decision.next_action_deadline_ns


def compile_epoch_plan(
    capability_plan: CapabilityPlan,
    descriptor_set: CapabilityDescriptorSet,
    *,
    due_items: tuple[EpochWorkItem, ...],
    bindings: tuple[EpochBinding, ...],
) -> EpochPlan:
    """Compile due work into an immutable stateless plan.

    Caller-provided due_items define order. Disabled-capability work is
    explicitly suppressed. Enabled work requires an explicit matching binding.
    Descriptor implementation_ref strings are never imported or executed.
    """

    if not isinstance(capability_plan, CapabilityPlan):
        raise InvalidEpochPlanData("capability_plan must be CapabilityPlan")
    if not isinstance(descriptor_set, CapabilityDescriptorSet):
        raise InvalidEpochPlanData(
            "descriptor_set must be CapabilityDescriptorSet"
        )
    if not isinstance(due_items, tuple) or not all(
        isinstance(value, EpochWorkItem)
        for value in due_items
    ):
        raise InvalidEpochPlanData(
            "due_items must be a tuple of EpochWorkItem values"
        )
    if not isinstance(bindings, tuple) or not all(
        isinstance(value, EpochBinding)
        for value in bindings
    ):
        raise InvalidEpochPlanData(
            "bindings must be a tuple of EpochBinding values"
        )

    descriptor_set.validate_plan(capability_plan)
    _require_unique(
        "due work_id",
        tuple(item.work_id for item in due_items),
    )
    _require_unique(
        "binding work_id",
        tuple(binding.work_id for binding in bindings),
    )

    operators = {
        descriptor.operator_id: descriptor
        for descriptor in descriptor_set.operators
    }
    bindings_by_work = {
        binding.work_id: binding
        for binding in bindings
    }

    steps: list[EpochStep] = []
    suppressed: list[EpochWorkItem] = []
    scheduled_work_ids: set[str] = set()

    for item in due_items:
        descriptor = operators.get(item.operator_id)
        if descriptor is None:
            raise UnknownEpochOperator(
                f"due work references unknown operator: {item.operator_id}"
            )

        try:
            capability_plan.spec(descriptor.capability_id)
        except UnknownCapability as exc:
            raise UnknownEpochOperator(
                f"operator capability is not declared in plan: "
                f"{descriptor.capability_id}"
            ) from exc

        if not capability_plan.is_enabled(descriptor.capability_id):
            suppressed.append(item)
            continue

        if descriptor.effect is OperatorEffect.COORDINATION:
            raise NestedCoordinationOperator(
                f"coordination operator cannot be inner epoch work: "
                f"{descriptor.operator_id}"
            )

        binding = bindings_by_work.get(item.work_id)
        if binding is None:
            raise MissingEpochBinding(
                f"enabled due work has no binding: {item.work_id}"
            )
        if binding.operator_id != item.operator_id:
            raise EpochBindingMismatch(
                f"work {item.work_id} expects {item.operator_id} but binding "
                f"names {binding.operator_id}"
            )

        steps.append(
            _step_from(item, descriptor)
        )
        scheduled_work_ids.add(item.work_id)

    unexpected = set(bindings_by_work).difference(scheduled_work_ids)
    if unexpected:
        raise UnexpectedEpochBinding(
            "binding does not correspond to enabled due work: "
            + ", ".join(sorted(unexpected))
        )

    cognition_positions = [
        index
        for index, step in enumerate(steps)
        if step.effect is OperatorEffect.COGNITION_CALL
    ]
    if len(cognition_positions) > 1:
        raise MultipleCognitionSteps(
            "one epoch may contain at most one cognition-call step"
        )
    if cognition_positions and cognition_positions[0] != len(steps) - 1:
        raise CognitionStepOrderingError(
            "cognition-call step must be the final inner epoch step"
        )

    return EpochPlan(
        steps=tuple(steps),
        suppressed=tuple(suppressed),
    )


def coordinate_planned_epoch(
    supervisor: ActionSupervisor,
    plan: EpochPlan,
    *,
    bindings: tuple[EpochBinding, ...],
    at_ns: int,
    provenance: Provenance,
) -> PlannedDecisionEpochResult:
    """Run one plan through the existing deadline-first decision coordinator.

    ActionSupervisor is serviced by coordinate_decision_epoch before this
    function's decision work begins. Deterministic/owner-transition work then
    runs in plan order. At most one final cognition step may return a
    CognitionInvocation, which is executed exactly once by the existing
    coordinator's cognition seam.
    """

    if not isinstance(plan, EpochPlan):
        raise InvalidEpochPlanData("plan must be EpochPlan")
    if not isinstance(bindings, tuple) or not all(
        isinstance(value, EpochBinding)
        for value in bindings
    ):
        raise InvalidEpochPlanData(
            "bindings must be a tuple of EpochBinding values"
        )

    _require_unique(
        "binding work_id",
        tuple(binding.work_id for binding in bindings),
    )
    bindings_by_work = {
        binding.work_id: binding
        for binding in bindings
    }

    required = {step.work_id for step in plan.steps}
    if set(bindings_by_work) != required:
        missing = required.difference(bindings_by_work)
        extra = set(bindings_by_work).difference(required)
        details: list[str] = []
        if missing:
            details.append("missing=" + ",".join(sorted(missing)))
        if extra:
            details.append("extra=" + ",".join(sorted(extra)))
        raise InvalidEpochPlanData(
            "execution bindings must exactly match plan steps: "
            + " ".join(details)
        )

    for step in plan.steps:
        binding = bindings_by_work[step.work_id]
        if binding.operator_id != step.operator_id:
            raise EpochBindingMismatch(
                f"work {step.work_id} expects {step.operator_id} but binding "
                f"names {binding.operator_id}"
            )

    executed: list[str] = []

    def decision_step() -> CognitionInvocation | None:
        for step in plan.steps:
            binding = bindings_by_work[step.work_id]
            result = binding.invoke()

            if step.effect is OperatorEffect.COGNITION_CALL:
                if not isinstance(result, CognitionInvocation):
                    raise InvalidEpochPlanData(
                        f"cognition work {step.work_id} must return "
                        "CognitionInvocation"
                    )
                executed.append(step.work_id)
                return result

            if result is not None:
                raise InvalidEpochPlanData(
                    f"non-cognition work {step.work_id} must return None"
                )
            executed.append(step.work_id)

        return None

    def run_cognition(invocation: CognitionInvocation) -> object:
        if not isinstance(invocation, CognitionInvocation):
            raise InvalidEpochPlanData(
                "planned cognition request must be CognitionInvocation"
            )
        return invocation.runner(invocation.request)

    decision = coordinate_decision_epoch(
        supervisor,
        at_ns=at_ns,
        provenance=provenance,
        decision_step=decision_step if plan.steps else None,
        relay_engine=run_cognition,
    )

    return PlannedDecisionEpochResult(
        decision=decision,
        executed_work_ids=tuple(executed),
        suppressed_work_ids=tuple(
            item.work_id
            for item in plan.suppressed
        ),
    )


def _step_from(
    item: EpochWorkItem,
    descriptor: OperatorDescriptor,
) -> EpochStep:
    return EpochStep(
        work_id=item.work_id,
        operator_id=item.operator_id,
        capability_id=descriptor.capability_id,
        trigger_ref=item.trigger_ref,
        effect=descriptor.effect,
    )


def _require_unique(name: str, values: tuple[str, ...]) -> None:
    seen: set[str] = set()
    for value in values:
        if value in seen:
            raise InvalidEpochPlanData(f"duplicate {name}: {value}")
        seen.add(value)


def _require_text(name: str, value: object) -> None:
    if not isinstance(value, str) or not value.strip():
        raise InvalidEpochPlanData(f"{name} must be a non-empty string")
