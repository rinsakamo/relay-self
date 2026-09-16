from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum

from relay_self.action import Provenance


class SkillExecutionError(ValueError):
    """Base error for invalid Skill Execution data or transitions."""


class InvalidSkillData(SkillExecutionError):
    """Raised when Skill Execution data violates the contract."""


class InvalidSkillTransition(SkillExecutionError):
    """Raised when a requested Skill Execution transition is not allowed."""


class SkillState(str, Enum):
    STARTED = "started"
    SUCCEEDED = "succeeded"
    FAILED = "failed"


SKILL_TERMINAL_STATES = frozenset({SkillState.SUCCEEDED, SkillState.FAILED})

_ALLOWED_TRANSITIONS = {
    SkillState.STARTED: frozenset({SkillState.SUCCEEDED, SkillState.FAILED}),
    SkillState.SUCCEEDED: frozenset(),
    SkillState.FAILED: frozenset(),
}


@dataclass(frozen=True, slots=True)
class SkillEvent:
    state: SkillState
    at_ns: int
    provenance: Provenance
    reason: str | None = None

    def __post_init__(self) -> None:
        if not isinstance(self.state, SkillState):
            raise InvalidSkillData("skill event state must be a SkillState")
        _require_at_ns(self.at_ns)
        _require_provenance(self.provenance)

        if self.state is SkillState.STARTED:
            if self.reason is not None:
                raise InvalidSkillData("skill start event cannot record a terminal reason")
        else:
            _require_text("skill terminal reason", self.reason)


@dataclass(frozen=True, slots=True)
class SkillExecution:
    """Immutable lifecycle for one runtime execution of one Skill capability."""

    execution_id: str
    skill_id: str
    intent_id: str
    _events: tuple[SkillEvent, ...] = field(repr=False)

    def __post_init__(self) -> None:
        _require_text("execution_id", self.execution_id)
        _require_text("skill_id", self.skill_id)
        _require_text("intent_id", self.intent_id)
        if not isinstance(self._events, tuple):
            raise InvalidSkillData("skill event history must be an immutable tuple")
        if not all(isinstance(event, SkillEvent) for event in self._events):
            raise InvalidSkillData("skill event history must contain only SkillEvent values")
        self._validate_history()

    @classmethod
    def start(
        cls,
        execution_id: str,
        *,
        skill_id: str,
        intent_id: str,
        at_ns: int,
        provenance: Provenance,
    ) -> SkillExecution:
        event = SkillEvent(
            state=SkillState.STARTED,
            at_ns=at_ns,
            provenance=provenance,
        )
        return cls(
            execution_id=execution_id,
            skill_id=skill_id,
            intent_id=intent_id,
            _events=(event,),
        )

    @property
    def state(self) -> SkillState:
        return self._events[-1].state

    @property
    def events(self) -> tuple[SkillEvent, ...]:
        return self._events

    @property
    def is_terminal(self) -> bool:
        return self.state in SKILL_TERMINAL_STATES

    def succeed(
        self,
        *,
        reason: str,
        at_ns: int,
        provenance: Provenance,
    ) -> SkillExecution:
        return self._transition(
            SkillEvent(
                state=SkillState.SUCCEEDED,
                at_ns=at_ns,
                provenance=provenance,
                reason=reason,
            )
        )

    def fail(
        self,
        *,
        reason: str,
        at_ns: int,
        provenance: Provenance,
    ) -> SkillExecution:
        return self._transition(
            SkillEvent(
                state=SkillState.FAILED,
                at_ns=at_ns,
                provenance=provenance,
                reason=reason,
            )
        )

    def _transition(self, event: SkillEvent) -> SkillExecution:
        if event.state not in _ALLOWED_TRANSITIONS[self.state]:
            raise InvalidSkillTransition(
                f"cannot transition from {self.state.value} to {event.state.value}"
            )
        return SkillExecution(
            execution_id=self.execution_id,
            skill_id=self.skill_id,
            intent_id=self.intent_id,
            _events=(*self._events, event),
        )

    def _validate_history(self) -> None:
        if not self._events:
            raise InvalidSkillData("a skill execution requires at least one event")
        if self._events[0].state is not SkillState.STARTED:
            raise InvalidSkillData("the first skill event must be started")

        previous: SkillEvent | None = None
        for event in self._events:
            _require_at_ns(event.at_ns)

            if previous is not None:
                if event.at_ns < previous.at_ns:
                    raise InvalidSkillData("skill event time must be monotonic")
                if event.state not in _ALLOWED_TRANSITIONS[previous.state]:
                    raise InvalidSkillData(
                        f"invalid recorded transition from {previous.state.value} "
                        f"to {event.state.value}"
                    )

            previous = event


def _require_text(name: str, value: object) -> None:
    if not isinstance(value, str) or not value.strip():
        raise InvalidSkillData(f"{name} must be a non-empty string")


def _require_at_ns(value: object) -> None:
    if not isinstance(value, int) or isinstance(value, bool) or value < 0:
        raise InvalidSkillData("skill event time must be a non-negative integer")


def _require_provenance(value: object) -> None:
    if not isinstance(value, Provenance):
        raise InvalidSkillData("skill event provenance must be Provenance")
