from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

from relay_self.action import Provenance


class IntentCommitmentError(ValueError):
    """Base error for invalid Current Intent commitment operations."""


class InvalidIntentData(IntentCommitmentError):
    """Raised when intent data violates the commitment contract."""


class InvalidIntentTransition(IntentCommitmentError):
    """Raised when a requested commitment transition is not allowed."""


class DuplicateIntentIdentity(IntentCommitmentError):
    """Raised when an intent identity is reused inside one owner lifetime."""


class InvalidIntentTime(IntentCommitmentError):
    """Raised when intent event time is malformed or moves backward."""


class IntentEventKind(str, Enum):
    COMMITTED = "committed"
    RECONSIDERED_CONTINUE = "reconsidered_continue"
    RECONSIDERED_RELEASE = "reconsidered_release"
    COMPLETED = "completed"
    FAILED = "failed"
    INVALIDATED = "invalidated"


class ReconsiderationDecision(str, Enum):
    CONTINUE = "continue"
    RELEASE = "release"


_RELEASE_KINDS = frozenset(
    {
        IntentEventKind.RECONSIDERED_RELEASE,
        IntentEventKind.COMPLETED,
        IntentEventKind.FAILED,
        IntentEventKind.INVALIDATED,
    }
)


@dataclass(frozen=True, slots=True)
class IntentEvent:
    kind: IntentEventKind
    intent_id: str
    at_ns: int
    provenance: Provenance
    objective: str | None = None
    reason: str | None = None

    def __post_init__(self) -> None:
        if not isinstance(self.kind, IntentEventKind):
            raise InvalidIntentData("intent event kind must be an IntentEventKind")
        _require_text("intent_id", self.intent_id)
        _require_at_ns(self.at_ns)
        _require_provenance(self.provenance)

        if self.kind is IntentEventKind.COMMITTED:
            _require_text("intent objective", self.objective)
            if self.reason is not None:
                raise InvalidIntentData("commit event cannot record a release reason")
        else:
            if self.objective is not None:
                raise InvalidIntentData("intent objective is recorded only on commit")
            _require_text("intent transition reason", self.reason)


@dataclass(frozen=True, slots=True)
class CurrentIntent:
    intent_id: str
    objective: str
    committed_at_ns: int
    provenance: Provenance

    def __post_init__(self) -> None:
        _require_text("intent_id", self.intent_id)
        _require_text("intent objective", self.objective)
        _require_at_ns(self.committed_at_ns)
        _require_provenance(self.provenance)


class IntentCommitment:
    """Runtime owner that retains one Current Intent until explicit release."""

    def __init__(self) -> None:
        self._events: tuple[IntentEvent, ...] = ()

    @property
    def events(self) -> tuple[IntentEvent, ...]:
        return self._events

    @property
    def last_at_ns(self) -> int | None:
        if not self._events:
            return None
        return self._events[-1].at_ns

    @property
    def current_intent(self) -> CurrentIntent | None:
        if not self._events or self._events[-1].kind in _RELEASE_KINDS:
            return None
        for event in reversed(self._events):
            if event.kind is IntentEventKind.COMMITTED:
                assert event.objective is not None
                return CurrentIntent(
                    intent_id=event.intent_id,
                    objective=event.objective,
                    committed_at_ns=event.at_ns,
                    provenance=event.provenance,
                )
        raise IntentCommitmentError("active intent history has no commit event")

    def commit(
        self,
        intent_id: str,
        *,
        objective: str,
        at_ns: int,
        provenance: Provenance,
    ) -> CurrentIntent:
        self._require_time(at_ns)
        _require_text("intent_id", intent_id)
        _require_text("intent objective", objective)
        _require_provenance(provenance)

        current = self.current_intent
        if current is not None:
            raise InvalidIntentTransition(
                f"cannot commit {intent_id} while {current.intent_id} is current"
            )
        if intent_id in self._committed_intent_ids():
            raise DuplicateIntentIdentity(f"intent_id was already committed: {intent_id}")

        self._append(
            IntentEvent(
                kind=IntentEventKind.COMMITTED,
                intent_id=intent_id,
                at_ns=at_ns,
                provenance=provenance,
                objective=objective,
            )
        )
        current = self.current_intent
        assert current is not None
        return current

    def reconsider(
        self,
        intent_id: str,
        *,
        decision: ReconsiderationDecision,
        reason: str,
        at_ns: int,
        provenance: Provenance,
    ) -> CurrentIntent | None:
        self._require_time(at_ns)
        current = self._require_current(intent_id)
        if not isinstance(decision, ReconsiderationDecision):
            raise InvalidIntentData(
                "reconsideration decision must be a ReconsiderationDecision"
            )
        _require_text("reconsideration reason", reason)
        _require_provenance(provenance)

        kind = (
            IntentEventKind.RECONSIDERED_CONTINUE
            if decision is ReconsiderationDecision.CONTINUE
            else IntentEventKind.RECONSIDERED_RELEASE
        )
        self._append(
            IntentEvent(
                kind=kind,
                intent_id=current.intent_id,
                at_ns=at_ns,
                provenance=provenance,
                reason=reason,
            )
        )
        return self.current_intent

    def complete(
        self,
        intent_id: str,
        *,
        reason: str,
        at_ns: int,
        provenance: Provenance,
    ) -> IntentEvent:
        return self._close(
            IntentEventKind.COMPLETED,
            intent_id,
            reason=reason,
            at_ns=at_ns,
            provenance=provenance,
        )

    def fail(
        self,
        intent_id: str,
        *,
        reason: str,
        at_ns: int,
        provenance: Provenance,
    ) -> IntentEvent:
        return self._close(
            IntentEventKind.FAILED,
            intent_id,
            reason=reason,
            at_ns=at_ns,
            provenance=provenance,
        )

    def invalidate(
        self,
        intent_id: str,
        *,
        reason: str,
        at_ns: int,
        provenance: Provenance,
    ) -> IntentEvent:
        return self._close(
            IntentEventKind.INVALIDATED,
            intent_id,
            reason=reason,
            at_ns=at_ns,
            provenance=provenance,
        )

    def _close(
        self,
        kind: IntentEventKind,
        intent_id: str,
        *,
        reason: str,
        at_ns: int,
        provenance: Provenance,
    ) -> IntentEvent:
        self._require_time(at_ns)
        current = self._require_current(intent_id)
        _require_text("intent transition reason", reason)
        _require_provenance(provenance)
        event = IntentEvent(
            kind=kind,
            intent_id=current.intent_id,
            at_ns=at_ns,
            provenance=provenance,
            reason=reason,
        )
        self._append(event)
        return event

    def _require_current(self, intent_id: str) -> CurrentIntent:
        _require_text("intent_id", intent_id)
        current = self.current_intent
        if current is None:
            raise InvalidIntentTransition("no current intent is committed")
        if current.intent_id != intent_id:
            raise InvalidIntentTransition(
                f"intent {intent_id} is not current; current intent is {current.intent_id}"
            )
        return current

    def _require_time(self, at_ns: object) -> None:
        if not isinstance(at_ns, int) or isinstance(at_ns, bool) or at_ns < 0:
            raise InvalidIntentTime("intent time values must be non-negative integers")
        if self.last_at_ns is not None and at_ns < self.last_at_ns:
            raise InvalidIntentTime("intent event time must be monotonic")

    def _committed_intent_ids(self) -> frozenset[str]:
        return frozenset(
            event.intent_id
            for event in self._events
            if event.kind is IntentEventKind.COMMITTED
        )

    def _append(self, event: IntentEvent) -> None:
        self._events = (*self._events, event)


def _require_text(name: str, value: object) -> None:
    if not isinstance(value, str) or not value.strip():
        raise InvalidIntentData(f"{name} must be a non-empty string")


def _require_at_ns(value: object) -> None:
    if not isinstance(value, int) or isinstance(value, bool) or value < 0:
        raise InvalidIntentData("intent event time must be a non-negative integer")


def _require_provenance(value: object) -> None:
    if not isinstance(value, Provenance):
        raise InvalidIntentData("intent provenance must be Provenance")
