"""S47 budgeted L0 -> bounded -> THINK/OPEN escalation over existing RelayEngine.

No second provider, LLM-per-tick loop, Action authority or state persistence.
Bounded and open answer topology remain distinct from execution depth.
"""
from __future__ import annotations

from dataclasses import dataclass, replace
from enum import Enum

from relay_self.reactive_l0 import L0Step
from relay_self.relay_engine import (
    BoundedChoiceRequest,
    DecisionStatus,
    OpenCognitionRequest,
    OpenCognitionResult,
    RelayEngine,
    RelayEngineResult,
)


class AllocationRejected(ValueError):
    """No cognition without an explicit bounded budget and valid request."""


class AllocationPath(str, Enum):
    L0 = "L0"
    BOUNDED = "BOUNDED"
    THINK = "THINK"
    OPEN = "OPEN"
    DEFER = "DEFER"


@dataclass(frozen=True, slots=True)
class CognitionBudget:
    max_model_calls: int = 1
    allow_think: bool = False
    allow_open: bool = False

    def __post_init__(self) -> None:
        if (
            type(self.max_model_calls) is not int
            or not 0 <= self.max_model_calls <= 3
            or type(self.allow_think) is not bool
            or type(self.allow_open) is not bool
        ):
            raise AllocationRejected("explicit bounded cognition budget required")


@dataclass(frozen=True, slots=True)
class AllocationResult:
    path: AllocationPath
    choice_id: str | None
    bounded_result: RelayEngineResult | None
    open_result: OpenCognitionResult | None
    model_calls: int
    unresolved: bool


def allocate_cognition(
    *,
    budget: CognitionBudget,
    l0: L0Step | None = None,
    bounded: BoundedChoiceRequest | None = None,
    open_request: OpenCognitionRequest | None = None,
    engine: RelayEngine | None = None,
) -> AllocationResult:
    if not isinstance(budget, CognitionBudget):
        raise AllocationRejected("typed budget required")
    if l0 is not None:
        if not isinstance(l0, L0Step):
            raise AllocationRejected("typed L0 decision required")
        # A deterministic decision does not silently become an Action grant.
        return AllocationResult(
            AllocationPath.L0, l0.choice.selection.value, None, None, 0, False,
        )
    if budget.max_model_calls == 0:
        return AllocationResult(AllocationPath.DEFER, None, None, None, 0, True)
    if not isinstance(bounded, BoundedChoiceRequest):
        raise AllocationRejected("explicit typed finite question required")
    if not isinstance(engine, RelayEngine):
        raise AllocationRejected("actual shared RelayEngine required")
    allow_think = budget.allow_think and budget.max_model_calls >= 2
    request = replace(bounded, think_allowed=allow_think)
    result = engine(request)
    count = result.provider_call_count
    if count < 1 or count > budget.max_model_calls:
        raise AllocationRejected("actual provider call count exceeds budget")
    if result.status is DecisionStatus.RESOLVED:
        return AllocationResult(
            AllocationPath.THINK if result.escalated else AllocationPath.BOUNDED,
            result.choice_id, result, None, count, False,
        )
    if (
        budget.allow_open and isinstance(open_request, OpenCognitionRequest)
        and count < budget.max_model_calls
    ):
        # Explicit OPEN generation is transient hypothesis/expression, not
        # accepted World truth, retained belief or Action commitment.
        opened = engine.open(open_request)
        return AllocationResult(
            AllocationPath.OPEN, None, result, opened, count + 1, True,
        )
    return AllocationResult(
        AllocationPath.THINK if result.escalated else AllocationPath.BOUNDED,
        None, result, None, count, True,
    )
