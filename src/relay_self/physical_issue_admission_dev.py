"""#860 P0-D: physical EAT/ATTACK issue leases for coordinated autosave.

The lease spans the *entire* existing native EAT/ATTACK await chain, not merely
the durable WAL PREPARED step. It is a wrapper for the existing physical owner:
NO new selector, grant, native sender, WAL or ActionSupervisor is introduced.

Only callers using these guarded entrypoints are fenced. Legacy direct calls to
issue_selected_eat_dev / issue_selected_attack_dev remain outside this owner
until migrated; therefore this alone does NOT attest a global real-world fence.
"""
from __future__ import annotations

import math
import threading
from contextlib import contextmanager
from dataclasses import dataclass
from typing import Any, Callable, Iterator

from adapters.mineflayer.python_protocol import MineflayerEffectResult, MineflayerObservation
from relay_self.checkpointed_cognitive_runtime_dev import ExternalPhysicalFence


class PhysicalIssueFenceError(RuntimeError):
    """Action issuer is busy, stopped, foreign or holds an old native session."""


@dataclass(frozen=True, slots=True)
class IssueLease:
    self_id: str
    native_session_id: str
    action_id: str
    epoch: int
    effect_family: str = "NONE"


@dataclass(frozen=True, slots=True)
class NeutralStopProof:
    """Two same-session native probes after the ACK, with World clock spacing."""

    stop_action_id: str
    ack: MineflayerEffectResult
    initial_probe: MineflayerObservation
    first_probe: MineflayerObservation
    settled_probe: MineflayerObservation


_EFFECT_FAMILIES: dict[str, frozenset[str]] = {
    "NONE": frozenset(),
    "EAT": frozenset({"equip_item", "consume_held"}),
    "ATTACK": frozenset({"attack_entity"}),
}


class PhysicalIssueAdmission:
    """Single in-process admission owner for a fixed multi-Self cohort.

    close() fences new leases BEFORE inspecting active physical actions. If an
    existing native call is active, close REJECTS and leaves the gate held,
    rather than falsely reporting a clean World/Self checkpoint.
    """

    def __init__(
        self, current_sessions: dict[str, str], *,
        require_neutral_stop: bool = False,
    ) -> None:
        if type(require_neutral_stop) is not bool:
            raise PhysicalIssueFenceError("neutral STOP policy must be bool")
        self._require_neutral_stop = require_neutral_stop
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
        self._poisoned = False
        self._fence_token: str | None = None
        self._generation = 0
        self._rotated: set[str] = set()
        self._neutralizing = False
        self._stop_required: set[str] = set()
        self._stop_active: dict[str, tuple[str, str]] = {}
        self._stop_proofs: dict[str, NeutralStopProof] = {}

    @property
    def requires_neutral_stop(self) -> bool:
        return self._require_neutral_stop

    @property
    def self_roster(self) -> tuple[str, ...]:
        with self._lock:
            return tuple(sorted(self._sessions))

    @property
    def closed(self) -> bool:
        with self._lock:
            return self._closed

    @property
    def neutralization_complete(self) -> bool:
        with self._lock:
            return (
                self._closed and self._neutralizing and not self._poisoned
                and self._stop_required == set(self._stop_proofs)
                and not self._stop_active
            )

    @property
    def active_action_ids(self) -> tuple[str, ...]:
        with self._lock:
            return tuple(sorted(x.action_id for x in self._active.values()))

    @contextmanager
    def lease(
        self, *, self_id: str, native_session_id: str, action_id: str,
        effect_family: str = "NONE",
    ) -> Iterator[IssueLease]:
        """Synchronous acquire before async await; finally releases on cancel."""
        with self._lock:
            if self._closed:
                raise PhysicalIssueFenceError("checkpoint fence closed physical admission")
            if self_id not in self._sessions or self._sessions[self_id] != native_session_id:
                raise PhysicalIssueFenceError("stale or foreign physical native session")
            if type(action_id) is not str or not action_id.strip():
                raise PhysicalIssueFenceError("physical Action ID required")
            if effect_family not in _EFFECT_FAMILIES:
                raise PhysicalIssueFenceError("unsupported physical effect family")
            if self_id in self._active or any(
                x.action_id == action_id for x in self._active.values()
            ):
                raise PhysicalIssueFenceError("physical Action already in flight")
            record = IssueLease(
                self_id, native_session_id, action_id, self._generation,
                effect_family,
            )
            self._active[self_id] = record
        try:
            yield record
        finally:
            with self._lock:
                if self._active.get(self_id) == record:
                    del self._active[self_id]

    def require_native_effect(
        self, *, self_id: str, native_session_id: str,
        effect: str, action_id: str | None = None,
    ) -> None:
        """Actual Mineflayer stdin gate: require an active typed EAT/ATTACK lease.

        L0 MOVE/LOOK/CLEAR controls remain *unsupported* in coordinated mode.
        The caller must ensure controls were already neutral before this mode
        is installed; an emergency STOP has its own separately supervised path.
        """
        with self._lock:
            if self._poisoned:
                raise PhysicalIssueFenceError("native physical effect blocked by checkpoint")
            if self._sessions.get(self_id) != native_session_id:
                raise PhysicalIssueFenceError("stale/foreign native effect session")
            if self._closed:
                authorized_stop = self._stop_active.get(self_id)
                if (
                    self._neutralizing and effect == "clear_controls"
                    and authorized_stop is not None
                    and authorized_stop[0] == native_session_id
                    and authorized_stop[1] == action_id
                ):
                    return
                raise PhysicalIssueFenceError("native physical effect blocked by checkpoint")
            lease = self._active.get(self_id)
            if (
                lease is None or lease.native_session_id != native_session_id
                or effect not in _EFFECT_FAMILIES[lease.effect_family]
            ):
                raise PhysicalIssueFenceError(
                    "native effect requires active capability-scoped issuer lease"
                )

    def begin_neutralization(self) -> str:
        """Lock normal physical effects before one supervised STOP per Self.

        An in-flight EAT/ATTACK is a fatal dirty cut; never attempt STOP over
        an unresolved physical issue. This is a PRE-checkpoint phase; the
        cognition/World cut starts only after stop readback is verified.
        """
        with self._lock:
            if self._closed or self._poisoned:
                raise PhysicalIssueFenceError("physical neutralization already held")
            self._closed = True
            self._generation += 1
            self._rotated.clear()
            self._fence_token = f"physical-cohort-{self._generation}"
            self._stop_required = set(self._sessions)
            self._stop_active.clear()
            self._stop_proofs.clear()
            self._neutralizing = True
            if self._active:
                self._poisoned = True
                raise PhysicalIssueFenceError(
                    "in-flight physical Action prevents STOP; admission held"
                )
            return self._fence_token

    def abort_neutralization(self) -> None:
        """A failed pre-save STOP must never become a later valid COMMIT."""
        with self._lock:
            if self._closed and self._neutralizing:
                self._poisoned = True

    @contextmanager
    def stop_lease(
        self, *, fence_ref: str, self_id: str,
        native_session_id: str, stop_action_id: str,
    ) -> Iterator[None]:
        """Single-use STOP capability while normal effects are globally closed."""
        with self._lock:
            if (
                self._poisoned or not self._closed or not self._neutralizing
                or fence_ref != self._fence_token
                or self._sessions.get(self_id) != native_session_id
                or type(stop_action_id) is not str or not stop_action_id.strip()
                or self_id in self._stop_active or self_id in self._stop_proofs
                or self._active or any(
                    item[1] == stop_action_id for item in self._stop_active.values()
                )
            ):
                raise PhysicalIssueFenceError("STOP requires unique current closed cohort lease")
            self._stop_active[self_id] = (native_session_id, stop_action_id)
        try:
            yield
        finally:
            with self._lock:
                self._stop_active.pop(self_id, None)
                if self_id not in self._stop_proofs:
                    # STOP may have reached native before the callback failed.
                    self._poisoned = True

    def confirm_neutral_stop(
        self, *, fence_ref: str, self_id: str, proof: NeutralStopProof,
    ) -> None:
        """Verify native ACK + same source + two clock-separated 3D positions."""
        with self._lock:
            active = self._stop_active.get(self_id)
            if (
                self._poisoned or not self._closed or not self._neutralizing
                or fence_ref != self._fence_token or active is None
                or not isinstance(proof, NeutralStopProof)
                or active[1] != proof.stop_action_id
            ):
                raise PhysicalIssueFenceError("STOP proof has no active generation lease")
            sid = active[0]
            ack = proof.ack
            initial, first, last = (
                proof.initial_probe, proof.first_probe, proof.settled_probe
            )
            if (
                not isinstance(ack, MineflayerEffectResult)
                or any(not isinstance(p, MineflayerObservation)
                       for p in (initial, first, last))
                or any(e.session_id != sid for e in (ack, initial, first, last))
                or ack.action_id != proof.stop_action_id
                or ack.effect != "clear_controls" or ack.result != "applied"
                or not ack.seq < initial.seq < first.seq < last.seq
                or any(p.kind != "probe" or not p.request_id
                       or p.snapshot.time is None or p.snapshot.health <= 0
                       for p in (initial, first, last))
                or len({p.request_id for p in (initial, first, last)}) != 3
            ):
                raise PhysicalIssueFenceError("STOP ACK and correlated probe lineage absent")
            pre_time = initial.snapshot.time
            before_time = first.snapshot.time
            after_time = last.snapshot.time
            pre_tick = pre_time.day * 24000 + pre_time.time_of_day
            before_tick = before_time.day * 24000 + before_time.time_of_day
            after_tick = after_time.day * 24000 + after_time.time_of_day
            if not (
                8 <= before_tick - pre_tick <= 200
                and 8 <= after_tick - before_tick <= 200
            ):
                raise PhysicalIssueFenceError(
                    "STOP lacks initial 8-tick settle and subsequent 8-tick stable windows"
                )
            pos0, pos1 = first.snapshot.position, last.snapshot.position
            displacement = math.dist(
                (pos0.x, pos0.y, pos0.z), (pos1.x, pos1.y, pos1.z),
            )
            if not math.isfinite(displacement) or displacement > 0.06:
                raise PhysicalIssueFenceError("STOP body not settled within 0.06m in 3D")
            self._stop_proofs[self_id] = proof

    def close(self) -> ExternalPhysicalFence:
        """Fences new issues; rejects if an in-flight async action has not drained."""
        with self._lock:
            if not self._closed and self._require_neutral_stop:
                self._closed = True
                self._poisoned = True
                raise PhysicalIssueFenceError(
                    "full-cohort STOP required before physical checkpoint"
                )
            if self._closed:
                if self._neutralizing:
                    if self._poisoned or not self.neutralization_complete:
                        self._poisoned = True
                        raise PhysicalIssueFenceError(
                            "not all Self bodies settled; checkpoint HOLD"
                        )
                    self._neutralizing = False
                    return ExternalPhysicalFence(
                        self._fence_token, physically_blocked=True,
                        physical_inflight_action_ids=(),
                    )
                raise PhysicalIssueFenceError("physical admission already held")
            self._closed = True
            self._generation += 1
            self._rotated.clear()
            self._fence_token = f"physical-cohort-{self._generation}"
            if self._active:
                # This generation cannot recover from an unsettled native effect.
                # A later lease completion does NOT transform a failed cut into a success.
                self._poisoned = True
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
            if self._poisoned or self._neutralizing:
                raise PhysicalIssueFenceError("failed/unsettled physical checkpoint requires operator recovery")
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
                self._poisoned or self._neutralizing or not self._closed
                or self._fence_token != fence_ref
                or self._active or self._rotated != set(self._sessions)
            ):
                raise PhysicalIssueFenceError(
                    "cannot release without complete native session rebind"
                )
            self._closed = False
            self._fence_token = None
            self._stop_required.clear()
            self._stop_proofs.clear()

    async def issue_eat(self, session: Any, **kwargs: Any) -> Any:
        """Wrap existing native issuer, WAL and async ACK+consequence readback."""
        from experiments.cognitive_physical_eat_issue_dev import issue_selected_eat_dev

        proposal = kwargs["proposal"]
        with self.lease(
            self_id=proposal.binding.scope.self_id,
            native_session_id=session.started.session_id,
            action_id=proposal.binding.action_id,
            effect_family="EAT",
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
            effect_family="ATTACK",
        ):
            return await issue_selected_attack_dev(session, **kwargs)

    async def run_l1_eat(
        self, session: Any, receipt: Any, *, admission_ref: str, **kwargs: Any,
    ) -> Any:
        """Fenced existing L1 EAT runner, including Intent/Skill setup and native IO.

        admission_ref is a coordinator call identity, NOT a physical Action ID,
        and cannot substitute for the Action/WAL receipts inside the runner.
        """
        from experiments.cognitive_physical_eat_runner import issue_eat_from_selected_l1_dev

        with self.lease(
            self_id=kwargs["self_id"],
            native_session_id=session.started.session_id,
            action_id=admission_ref,
            effect_family="EAT",
        ):
            return await issue_eat_from_selected_l1_dev(session, receipt, **kwargs)

    async def run_l1_attack(
        self, session: Any, receipt: Any, *, admission_ref: str, **kwargs: Any,
    ) -> Any:
        """Fenced existing L1 ATTACK runner from selected Intent through readback."""
        from experiments.cognitive_physical_attack_runner import issue_attack_from_selected_l1_dev

        with self.lease(
            self_id=kwargs["self_id"],
            native_session_id=session.started.session_id,
            action_id=admission_ref,
            effect_family="ATTACK",
        ):
            return await issue_attack_from_selected_l1_dev(session, receipt, **kwargs)

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
