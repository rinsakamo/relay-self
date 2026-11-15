"""#860 P0-D: physical EAT/ATTACK issue leases for coordinated autosave.

The lease spans the *entire* existing native EAT/ATTACK await chain, not merely
the durable WAL PREPARED step. It is a wrapper for the existing physical owner:
NO new selector, grant, native sender, WAL or ActionSupervisor is introduced.

Only callers using these guarded entrypoints are fenced. Legacy direct calls to
issue_selected_eat_dev / issue_selected_attack_dev remain outside this owner
until migrated; therefore this alone does NOT attest a global real-world fence.
"""
from __future__ import annotations

import threading
from contextlib import contextmanager
from dataclasses import dataclass
from typing import Any, Callable, Iterator

from relay_self.checkpointed_cognitive_runtime_dev import ExternalPhysicalFence


class PhysicalIssueFenceError(RuntimeError):
    """Action issuer is busy, stopped, foreign or holds an old native session."""


@dataclass(frozen=True, slots=True)
class IssueLease:
    self_id: str
    native_session_id: str
    action_id: str
    epoch: int


class PhysicalIssueAdmission:
    """Single in-process admission owner for a fixed multi-Self cohort.

    close() fences new leases BEFORE inspecting active physical actions. If an
    existing native call is active, close REJECTS and leaves the gate held,
    rather than falsely reporting a clean World/Self checkpoint.
    """

    def __init__(self, current_sessions: dict[str, str]) -> None:
        if (
            type(current_sessions) is not dict
            or not current_sessions
            or any(type(sid) is not str or not sid for sid in current_sessions)
            or any(type(sess) is not str or not sess for sess in current_sessions.values())
            or len(set(current_sessions.values())) != len(current_sessions)
        ):
            raise PhysicalIssueFenceError("one unique native session per Self required")
        self._lock = threading.RLock()
        self._sessions = dict(current_sessions)
        self._active: dict[str, IssueLease] = {}
        self._closed = False
        self._fence_token: str | None = None
        self._generation = 0
        self._rotated: set[str] = set()

    @property
    def closed(self) -> bool:
        with self._lock:
            return self._closed

    @property
    def active_action_ids(self) -> tuple[str, ...]:
        with self._lock:
            return tuple(sorted(x.action_id for x in self._active.values()))

    @contextmanager
    def lease(
        self, *, self_id: str, native_session_id: str, action_id: str,
    ) -> Iterator[IssueLease]:
        """Synchronous acquire before async await; finally releases on cancel."""
        with self._lock:
            if self._closed:
                raise PhysicalIssueFenceError("checkpoint fence closed physical admission")
            if self_id not in self._sessions or self._sessions[self_id] != native_session_id:
                raise PhysicalIssueFenceError("stale or foreign physical native session")
            if type(action_id) is not str or not action_id.strip():
                raise PhysicalIssueFenceError("physical Action ID required")
            if self_id in self._active or any(
                x.action_id == action_id for x in self._active.values()
            ):
                raise PhysicalIssueFenceError("physical Action already in flight")
            record = IssueLease(self_id, native_session_id, action_id, self._generation)
            self._active[self_id] = record
        try:
            yield record
        finally:
            with self._lock:
                if self._active.get(self_id) == record:
                    del self._active[self_id]

    def close(self) -> ExternalPhysicalFence:
        """Fences new issues; rejects if an in-flight async action has not drained."""
        with self._lock:
            if self._closed:
                raise PhysicalIssueFenceError("physical admission already held")
            self._closed = True
            self._generation += 1
            self._rotated.clear()
            self._fence_token = f"physical-cohort-{self._generation}"
            if self._active:
                raise PhysicalIssueFenceError(
                    "in-flight physical Action prevents checkpoint; gate held"
                )
            return ExternalPhysicalFence(
                self._fence_token, physically_blocked=True,
                physical_inflight_action_ids=(),
            )

    def rotate_native_session(
        self, *, fence_ref: str, self_id: str, old_session_id: str,
        new_session_id: str,
    ) -> None:
        """Record qualified rebind; external adapter must prove its authenticity."""
        with self._lock:
            if not self._closed or fence_ref != self._fence_token:
                raise PhysicalIssueFenceError("missing current physical fence")
            if self_id not in self._sessions or self._sessions[self_id] != old_session_id:
                raise PhysicalIssueFenceError("old physical session does not match owner")
            if (
                type(new_session_id) is not str or not new_session_id
                or new_session_id == old_session_id
                or new_session_id in self._sessions.values()
                or self_id in self._rotated
            ):
                raise PhysicalIssueFenceError("physical native session not fresh and unique")
            if self._active:
                raise PhysicalIssueFenceError("physical Action active during rebind")
            self._sessions[self_id] = new_session_id
            self._rotated.add(self_id)

    def release(self, fence_ref: str) -> None:
        """Only full A/B fresh session rejoin may reopen issuer admission."""
        with self._lock:
            if (
                not self._closed or self._fence_token != fence_ref
                or self._active or self._rotated != set(self._sessions)
            ):
                raise PhysicalIssueFenceError(
                    "cannot release without complete native session rebind"
                )
            self._closed = False
            self._fence_token = None

    async def issue_eat(self, session: Any, **kwargs: Any) -> Any:
        """Wrap existing native issuer, WAL and async ACK+consequence readback."""
        from experiments.cognitive_physical_eat_issue_dev import issue_selected_eat_dev

        proposal = kwargs["proposal"]
        with self.lease(
            self_id=proposal.binding.scope.self_id,
            native_session_id=session.started.session_id,
            action_id=proposal.binding.action_id,
        ):
            return await issue_selected_eat_dev(session, **kwargs)

    async def issue_attack(self, session: Any, **kwargs: Any) -> Any:
        """Wrap existing ATTACK issuer including uncertain-outcome handling."""
        from experiments.cognitive_physical_attack_issue_dev import issue_selected_attack_dev

        proposal = kwargs["proposal"]
        with self.lease(
            self_id=proposal.binding.scope.self_id,
            native_session_id=session.started.session_id,
            action_id=proposal.binding.action_id,
        ):
            return await issue_selected_attack_dev(session, **kwargs)

    async def run_guarded(
        self, *, self_id: str, native_session_id: str,
        action_id: str, perform: Callable[[], Any],
    ) -> Any:
        """Test/adapter hook using exactly the same lease as the native wrappers."""
        with self.lease(
            self_id=self_id, native_session_id=native_session_id,
            action_id=action_id,
        ):
            return await perform()
