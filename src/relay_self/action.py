from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from relay_self.intent import IntentCommitment
    from relay_self.skill import SkillExecution


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

    def __post_init__(self) -> None:
        if not isinstance(self.state, ActionState):
            raise InvalidActionData("action event state must be an ActionState")
        if not isinstance(self.provenance, Provenance):
            raise InvalidActionData("action event provenance must be Provenance")
        _require_at_ns(self.at_ns)
        if self.authority is not None:
            _require_text("authorization authority", self.authority)
        if self.deadline_ns is not None:
            _require_at_ns(self.deadline_ns)


@dataclass(slots=True)
class _ActionLineage:
    current_revision: int = 0


@dataclass(frozen=True, slots=True)
class ActionLifecycle:
    """Immutable snapshot of one provenance-bearing Action lifecycle."""

    action_id: str
    skill_execution_id: str
    intent_id: str
    _events: tuple[ActionEvent, ...] = field(repr=False)
    _lineage: _ActionLineage = field(
        default_factory=_ActionLineage,
        repr=False,
        compare=False,
    )
    _revision: int = field(default=0, repr=False, compare=False)

    def __post_init__(self) -> None:
        _require_text("action_id", self.action_id)
        _require_text("skill_execution_id", self.skill_execution_id)
        _require_text("intent_id", self.intent_id)
        if not isinstance(self._events, tuple):
            raise InvalidActionData("action event history must be an immutable tuple")
        if not all(isinstance(event, ActionEvent) for event in self._events):
            raise InvalidActionData("action event history must contain only ActionEvent values")
        if not isinstance(self._lineage, _ActionLineage):
            raise InvalidActionData("action lineage must be internal Action lineage state")
        if (
            not isinstance(self._revision, int)
            or isinstance(self._revision, bool)
            or self._revision < 0
        ):
            raise InvalidActionData("action revision must be a non-negative integer")
        if self._revision != len(self._events) - 1:
            raise InvalidActionData("action revision must match event history")
        self._validate_history()

    @classmethod
    def propose(
        cls,
        action_id: str,
        *,
        skill_execution: SkillExecution,
        intent_commitment: IntentCommitment,
        at_ns: int,
        provenance: Provenance,
    ) -> ActionLifecycle:
        event = ActionEvent(
            state=ActionState.PROPOSED,
            at_ns=at_ns,
            provenance=provenance,
        )
        skill_execution = _require_skill_execution(skill_execution)
        intent_commitment = _require_intent_commitment(intent_commitment)

        from relay_self.skill import SkillState

        if not skill_execution.is_current_snapshot:
            raise InvalidTransition(
                "action proposal requires the current Skill execution snapshot"
            )
        if skill_execution.state is not SkillState.STARTED:
            raise InvalidTransition("action proposal skill execution must be started")

        current_intent = intent_commitment.current_intent
        if current_intent is None:
            raise InvalidTransition("action proposal requires a current intent")
        if skill_execution.intent_id != current_intent.intent_id:
            raise InvalidTransition(
                "action proposal skill intent does not match current intent"
            )

        return cls(
            action_id=action_id,
            skill_execution_id=skill_execution.execution_id,
            intent_id=current_intent.intent_id,
            _events=(event,),
        )

    @property
    def state(self) -> ActionState:
        return self._events[-1].state

    @property
    def events(self) -> tuple[ActionEvent, ...]:
        return self._events

    @property
    def is_terminal(self) -> bool:
        return self.state in TERMINAL_STATES

    @property
    def is_current_snapshot(self) -> bool:
        return self._revision == self._lineage.current_revision

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

    def _prepare_timeout(
        self,
        *,
        at_ns: int,
        provenance: Provenance,
    ) -> ActionLifecycle:
        """Prepare a timeout snapshot without advancing lineage currentness."""
        return self._prepare_transition(
            ActionEvent(
                state=ActionState.TIMEOUT,
                at_ns=at_ns,
                provenance=provenance,
            )
        )

    def _transition(self, event: ActionEvent) -> ActionLifecycle:
        next_lifecycle = self._prepare_transition(event)
        return self._commit_prepared(next_lifecycle)

    def _prepare_transition(self, event: ActionEvent) -> ActionLifecycle:
        if not self.is_current_snapshot:
            raise InvalidTransition("cannot transition a stale Action lifecycle snapshot")
        allowed = _ALLOWED_TRANSITIONS[self.state]
        if event.state not in allowed:
            raise InvalidTransition(
                f"cannot transition from {self.state.value} to {event.state.value}"
            )

        return ActionLifecycle(
            action_id=self.action_id,
            skill_execution_id=self.skill_execution_id,
            intent_id=self.intent_id,
            _events=(*self._events, event),
            _lineage=self._lineage,
            _revision=self._revision + 1,
        )

    def _commit_prepared(self, next_lifecycle: ActionLifecycle) -> ActionLifecycle:
        if not self.is_current_snapshot:
            raise InvalidTransition("cannot transition a stale Action lifecycle snapshot")
        if next_lifecycle._lineage is not self._lineage:
            raise InvalidActionData("prepared Action snapshot has a different lineage")
        if next_lifecycle._revision != self._revision + 1:
            raise InvalidActionData("prepared Action snapshot has an invalid revision")
        if next_lifecycle._events[:-1] != self._events:
            raise InvalidActionData("prepared Action snapshot does not extend current history")

        self._lineage.current_revision = next_lifecycle._revision
        return next_lifecycle

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
                    raise InvalidTransition(
                        "cannot timeout an issued action before its deadline"
                    )

            previous = event


def _require_text(name: str, value: object) -> None:
    if not isinstance(value, str) or not value.strip():
        raise InvalidActionData(f"{name} must be a non-empty string")


def _require_at_ns(value: object) -> None:
    if not isinstance(value, int) or isinstance(value, bool) or value < 0:
        raise InvalidActionData("monotonic time values must be non-negative integers")


def _require_skill_execution(value: object) -> SkillExecution:
    from relay_self.skill import SkillExecution

    if not isinstance(value, SkillExecution):
        raise InvalidActionData("action proposal skill execution must be SkillExecution")
    return value


def _require_intent_commitment(value: object) -> IntentCommitment:
    from relay_self.intent import IntentCommitment

    if not isinstance(value, IntentCommitment):
        raise InvalidActionData("action proposal intent commitment must be IntentCommitment")
    return value
