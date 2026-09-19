from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Generic, TypeVar

from relay_self.action import ActionLifecycle
from relay_self.action_supervision import ActionSupervisor
from relay_self.provenance import Provenance

RequestT = TypeVar("RequestT")
ResponseT = TypeVar("ResponseT")


class RuntimeCoordinationError(RuntimeError):
    """Base error for the minimum admitted decision-epoch coordinator."""


class CognitionUnavailable(RuntimeCoordinationError):
    """Raised when caller-owned decision work requests cognition with no engine."""


@dataclass(frozen=True, slots=True)
class DecisionEpochResult(Generic[ResponseT]):
    """Traceable result of one already-admitted runtime decision epoch."""

    timed_out_actions: tuple[ActionLifecycle, ...]
    cognition_requested: bool
    cognition_result: ResponseT | None
    next_action_deadline_ns: int | None


def coordinate_decision_epoch(
    supervisor: ActionSupervisor,
    *,
    at_ns: int,
    provenance: Provenance,
    decision_step: Callable[[], RequestT | None] | None = None,
    relay_engine: Callable[[RequestT], ResponseT] | None = None,
) -> DecisionEpochResult[ResponseT]:
    """Coordinate one admitted epoch without becoming a semantic state owner.

    Action supervision is serviced first because its deadline and lifecycle are
    already owned by ActionSupervisor. The optional decision_step is
    caller-owned deterministic/reprojection work. Returning None means that
    work is adequate without model cognition; any other return value is an
    opaque cognition request passed unchanged to the supplied relay_engine
    exactly once.

    The function does not classify raw events, own a clock, project Present,
    select Skills, mutate Current Intent, define a cognition request schema, or
    retry/fallback when cognition is unavailable.
    """

    timed_out_actions = supervisor.advance(
        at_ns=at_ns,
        provenance=provenance,
    )

    cognition_request = decision_step() if decision_step is not None else None
    if cognition_request is None:
        return DecisionEpochResult(
            timed_out_actions=timed_out_actions,
            cognition_requested=False,
            cognition_result=None,
            next_action_deadline_ns=supervisor.next_deadline_ns,
        )

    if relay_engine is None:
        raise CognitionUnavailable(
            "decision step requested cognition but no RelayEngine seam was supplied"
        )

    cognition_result = relay_engine(cognition_request)
    return DecisionEpochResult(
        timed_out_actions=timed_out_actions,
        cognition_requested=True,
        cognition_result=cognition_result,
        next_action_deadline_ns=supervisor.next_deadline_ns,
    )
