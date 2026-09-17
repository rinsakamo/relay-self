from __future__ import annotations

from relay_self.action import ActionLifecycle, ActionState, Provenance


class ActionSupervisionError(ValueError):
    """Base error for invalid Action Supervision operations."""


class InvalidSupervisionData(ActionSupervisionError):
    """Raised when supervision input data violates the contract."""


class DuplicateSupervisedAction(ActionSupervisionError):
    """Raised when an action identity is reused inside one supervisor."""


class UnknownSupervisedAction(ActionSupervisionError):
    """Raised when an action identity is not owned by the supervisor."""


class InvalidSupervisorTime(ActionSupervisionError):
    """Raised when supervisor processing time is malformed or moves backward."""


class ActionSupervisor:
    """Deterministic in-flight action owner for explicit runtime decision epochs."""

    def __init__(self) -> None:
        self._lifecycles: dict[str, ActionLifecycle] = {}
        self._last_at_ns: int | None = None

    @property
    def last_at_ns(self) -> int | None:
        return self._last_at_ns

    @property
    def open_actions(self) -> tuple[ActionLifecycle, ...]:
        return tuple(
            self._lifecycles[action_id]
            for action_id in sorted(self._lifecycles)
            if self._lifecycles[action_id].state is ActionState.ISSUED
        )

    @property
    def next_deadline_ns(self) -> int | None:
        deadlines = tuple(_issued_deadline_ns(lifecycle) for lifecycle in self.open_actions)
        return min(deadlines, default=None)

    def get(self, action_id: str) -> ActionLifecycle:
        _require_action_id(action_id)
        try:
            return self._lifecycles[action_id]
        except KeyError as exc:
            raise UnknownSupervisedAction(f"unknown supervised action: {action_id}") from exc

    def issue(
        self,
        lifecycle: ActionLifecycle,
        *,
        at_ns: int,
        deadline_ns: int,
        provenance: Provenance,
    ) -> ActionLifecycle:
        self._require_time(at_ns)
        if not isinstance(lifecycle, ActionLifecycle):
            raise InvalidSupervisionData("supervised issue requires an ActionLifecycle")
        if lifecycle.action_id in self._lifecycles:
            raise DuplicateSupervisedAction(
                f"action is already supervised: {lifecycle.action_id}"
            )

        issued = lifecycle.issue(
            at_ns=at_ns,
            deadline_ns=deadline_ns,
            provenance=provenance,
        )
        self._lifecycles[lifecycle.action_id] = issued
        self._last_at_ns = at_ns
        return issued

    def record_outcome(
        self,
        action_id: str,
        *,
        at_ns: int,
        provenance: Provenance,
    ) -> ActionLifecycle:
        self._require_time(at_ns)
        lifecycle = self.get(action_id)
        closed = lifecycle.record_outcome(at_ns=at_ns, provenance=provenance)
        self._lifecycles[action_id] = closed
        self._last_at_ns = at_ns
        return closed

    def mark_unknown(
        self,
        action_id: str,
        *,
        at_ns: int,
        provenance: Provenance,
    ) -> ActionLifecycle:
        self._require_time(at_ns)
        lifecycle = self.get(action_id)
        closed = lifecycle.mark_unknown(at_ns=at_ns, provenance=provenance)
        self._lifecycles[action_id] = closed
        self._last_at_ns = at_ns
        return closed

    def advance(
        self,
        *,
        at_ns: int,
        provenance: Provenance,
    ) -> tuple[ActionLifecycle, ...]:
        self._require_time(at_ns)
        _require_provenance(provenance)

        prepared: list[tuple[str, ActionLifecycle, ActionLifecycle]] = []
        for lifecycle in self.open_actions:
            deadline_ns = _issued_deadline_ns(lifecycle)
            if deadline_ns <= at_ns:
                prepared.append(
                    (
                        lifecycle.action_id,
                        lifecycle,
                        lifecycle._prepare_timeout(
                            at_ns=at_ns,
                            provenance=provenance,
                        ),
                    )
                )

        replacements: list[tuple[str, ActionLifecycle]] = []
        for action_id, current, replacement in prepared:
            replacements.append(
                (action_id, current._commit_prepared(replacement))
            )

        for action_id, lifecycle in replacements:
            self._lifecycles[action_id] = lifecycle
        self._last_at_ns = at_ns
        return tuple(lifecycle for _, lifecycle in replacements)

    def _require_time(self, at_ns: object) -> None:
        if not isinstance(at_ns, int) or isinstance(at_ns, bool) or at_ns < 0:
            raise InvalidSupervisorTime(
                "supervisor time values must be non-negative integers"
            )
        if self._last_at_ns is not None and at_ns < self._last_at_ns:
            raise InvalidSupervisorTime("supervisor time must be monotonic")


def _issued_deadline_ns(lifecycle: ActionLifecycle) -> int:
    deadline_ns = lifecycle.events[-1].deadline_ns
    if deadline_ns is None:
        raise ActionSupervisionError(
            f"supervised issued action has no deadline: {lifecycle.action_id}"
        )
    return deadline_ns


def _require_action_id(value: object) -> None:
    if not isinstance(value, str) or not value.strip():
        raise InvalidSupervisionData("supervised action_id must be a non-empty string")


def _require_provenance(value: object) -> None:
    if not isinstance(value, Provenance):
        raise InvalidSupervisionData("supervision provenance must be Provenance")
