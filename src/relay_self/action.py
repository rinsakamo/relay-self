from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum


class ActionState(str, Enum):
    PROPOSED = "proposed"
    AUTHORIZED = "authorized"
    DENIED = "denied"
    ISSUED = "issued"
    OUTCOME = "outcome"
    TIMEOUT = "timeout"
    UNKNOWN = "unknown"


TERMINAL_STATES = frozenset(
    {
        ActionState.DENIED,
        ActionState.OUTCOME,
        ActionState.TIMEOUT,
        ActionState.UNKNOWN,
    }
)

_ALLOWED_TRANSITIONS = {
    ActionState.PROPOSED: frozenset({ActionState.AUTHORIZED, ActionState.DENIED}),
    ActionState.AUTHORIZED: frozenset({ActionState.ISSUED}),
    ActionState.ISSUED: frozenset(
        {ActionState.OUTCOME, ActionState.TIMEOUT, ActionState.UNKNOWN}
    ),
    ActionState.DENIED: frozenset(),
    ActionState.OUTCOME: frozenset(),
    ActionState.TIMEOUT: frozenset(),
    ActionState.UNKNOWN: frozenset(),
}


class ActionLifecycleError(ValueError):
    """Base error for invalid Action Lifecycle data or transitions."""


class InvalidActionData(ActionLifecycleError):
    """Raised when lifecycle data violates the contract."""


class InvalidTransition(ActionLifecycleError):
    """Raised when a requested lifecycle transition is not allowed."""


@dataclass(frozen=True, slots=True)
class Provenance:
    source: str
    reference: str

    def __post_init__(self) -> None:
        _require_text("provenance source", self.source)
        _require_text("provenance reference", self.reference)


@dataclass(frozen=True, slots=True)
class ActionEvent:
    state: ActionState
    at_ns: int
    provenance: Provenance
    authority: str | None = None
    deadline_ns: int | None = None


@dataclass(frozen=True, slots=True)
class ActionLifecycle:
    """Immutable, provenance-bearing state machine for one action."""

    action_id: str
    _events: tuple[ActionEvent, ...] = field(repr=False)

    def __post_init__(self) -> None:
        _require_text("action_id", self.action_id)
        self._validate_history()

    @classmethod
    def propose(
        cls,
        action_id: str,
        *,
        at_ns: int,
        provenance: Provenance,
    ) -> ActionLifecycle:
        event = ActionEvent(
            state=ActionState.PROPOSED,
            at_ns=at_ns,
            provenance=provenance,
        )
        return cls(action_id=action_id, _events=(event,))

    @property
    def state(self) -> ActionState:
        return self._events[-1].state

    @property
    def events(self) -> tuple[ActionEvent, ...]:
        return self._events

    @property
    def is_terminal(self) -> bool:
        return self.state in TERMINAL_STATES

    def authorize(
        self,
        *,
        at_ns: int,
        provenance: Provenance,
        authority: str,
    ) -> ActionLifecycle:
        _require_text("authorization authority", authority)
        return self._transition(
            ActionEvent(
                state=ActionState.AUTHORIZED,
                at_ns=at_ns,
                provenance=provenance,
                authority=authority,
            )
        )

    def deny(
        self,
        *,
        at_ns: int,
        provenance: Provenance,
        authority: str,
    ) -> ActionLifecycle:
        _require_text("authorization authority", authority)
        return self._transition(
            ActionEvent(
                state=ActionState.DENIED,
                at_ns=at_ns,
                provenance=provenance,
                authority=authority,
            )
        )

    def issue(
        self,
        *,
        at_ns: int,
        deadline_ns: int,
        provenance: Provenance,
    ) -> ActionLifecycle:
        return self._transition(
            ActionEvent(
                state=ActionState.ISSUED,
                at_ns=at_ns,
                provenance=provenance,
                deadline_ns=deadline_ns,
            )
        )

    def record_outcome(
        self,
        *,
        at_ns: int,
        provenance: Provenance,
    ) -> ActionLifecycle:
        return self._transition(
            ActionEvent(
                state=ActionState.OUTCOME,
                at_ns=at_ns,
                provenance=provenance,
            )
        )

    def timeout(
        self,
        *,
        at_ns: int,
        provenance: Provenance,
    ) -> ActionLifecycle:
        return self._transition(
            ActionEvent(
                state=ActionState.TIMEOUT,
                at_ns=at_ns,
                provenance=provenance,
            )
        )

    def mark_unknown(
        self,
        *,
        at_ns: int,
        provenance: Provenance,
    ) -> ActionLifecycle:
        return self._transition(
            ActionEvent(
                state=ActionState.UNKNOWN,
                at_ns=at_ns,
                provenance=provenance,
            )
        )

    def _transition(self, event: ActionEvent) -> ActionLifecycle:
        allowed = _ALLOWED_TRANSITIONS[self.state]
        if event.state not in allowed:
            raise InvalidTransition(f"cannot transition from {self.state.value} to {event.state.value}")
        return ActionLifecycle(action_id=self.action_id, _events=(*self._events, event))

    def _validate_history(self) -> None:
        if not self._events:
            raise InvalidActionData("an action lifecycle requires at least one event")
        if self._events[0].state is not ActionState.PROPOSED:
            raise InvalidActionData("the first action event must be proposed")

        previous: ActionEvent | None = None
        issued_deadline_ns: int | None = None

        for event in self._events:
            _require_at_ns(event.at_ns)

            if previous is not None:
                if event.at_ns < previous.at_ns:
                    raise InvalidActionData("action event time must be monotonic")
                if event.state not in _ALLOWED_TRANSITIONS[previous.state]:
                    raise InvalidActionData(
                        f"invalid recorded transition from {previous.state.value} "
                        f"to {event.state.value}"
                    )

            if event.state in {ActionState.AUTHORIZED, ActionState.DENIED}:
                _require_text("authorization authority", event.authority)
            elif event.authority is not None:
                raise InvalidActionData("authority is recorded only on authorization decisions")

            if event.state is ActionState.ISSUED:
                _require_at_ns(event.deadline_ns)
                if event.deadline_ns <= event.at_ns:
                    raise InvalidActionData("issued action deadline must be after issue time")
                issued_deadline_ns = event.deadline_ns
            elif event.deadline_ns is not None:
                raise InvalidActionData("deadline is recorded only on the issued event")

            if event.state is ActionState.TIMEOUT:
                if issued_deadline_ns is None:
                    raise InvalidActionData("timeout requires a prior issued deadline")
                if event.at_ns < issued_deadline_ns:
                    raise InvalidTransition("cannot timeout an issued action before its deadline")

            previous = event


def _require_text(name: str, value: str | None) -> None:
    if value is None or not value.strip():
        raise InvalidActionData(f"{name} must be a non-empty string")


def _require_at_ns(value: int | None) -> None:
    if not isinstance(value, int) or isinstance(value, bool) or value < 0:
        raise InvalidActionData("monotonic time values must be non-negative integers")
