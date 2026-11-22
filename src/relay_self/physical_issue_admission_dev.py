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
from pathlib import Path
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


@dataclass(frozen=True, slots=True)
class ResidentIssuerFence:
    """Original physical owner isolated exactly one Self, not the cohort."""

    self_id: str
    former_native_session_id: str
    fence_ref: str
    active_action_ids: tuple[str, ...]
    physical_issuer_revoked: bool = True
    no_physical_inflight: bool = False
    physical_wal_clear: bool = False
    native_terminated: bool = False
    action_issue_authorized: bool = False


@dataclass(frozen=True, slots=True)
class ResidentIssuerRetired:
    """Original Action and durable WAL checked; native/GPU/peer are separate."""

    self_id: str
    former_native_session_id: str
    fence_ref: str
    physical_wal_digest: str
    physical_issuer_revoked: bool = True
    no_physical_inflight: bool = True
    physical_wal_clear: bool = True
    native_terminated: bool = False
    action_issue_authorized: bool = False


_EFFECT_FAMILIES: dict[str, frozenset[str]] = {
    "NONE": frozenset(),
    "EAT": frozenset({"equip_item", "consume_held"}),
    "ATTACK": frozenset({"attack_entity"}),
    # MOVE is only opted into resident mode with an original canonical WAL.
    "MOVE": frozenset({"set_control", "clear_controls"}),
    # I U4 explicit opt-in only; default restored B owner cannot acquire.
    "MOVE_PLACE": frozenset({"look", "set_control", "clear_controls"}),
}


def _native_children(family: str, parent_action_id: str) -> dict[str, str]:
    """ActionPort-selected parent -> exact primitive native child identities."""
    if family == "EAT":
        return {
            "equip_item": parent_action_id + "-equip",
            "consume_held": parent_action_id + "-consume",
        }
    if family == "ATTACK":
        return {"attack_entity": parent_action_id + "-attack"}
    if family == "MOVE":
        return {
            "set_control": parent_action_id + "-start",
            "clear_controls": parent_action_id + "-stop",
        }
    if family == "MOVE_PLACE":
        return {
            "look": parent_action_id + "-look",
            "set_control": parent_action_id + "-start",
            "clear_controls": parent_action_id + "-stop",
        }
    raise PhysicalIssueFenceError("no native children for unsupported Action")



class PhysicalIssueAdmission:
    """Single in-process admission owner for a fixed multi-Self cohort.

    close() fences new leases BEFORE inspecting active physical actions. If an
    existing native call is active, close REJECTS and leaves the gate held,
    rather than falsely reporting a clean World/Self checkpoint.
    """

    def __init__(
        self, current_sessions: dict[str, str], *,
        require_neutral_stop: bool = False,
        resident_mode: bool = False,
        initially_offline: bool = False,
        allow_resident_move: bool = False,
        allow_resident_place_move: bool = False,
        observation_only: bool = False,
    ) -> None:
        if type(observation_only) is not bool or (observation_only and not resident_mode):
            raise PhysicalIssueFenceError("observation-only requires explicit resident mode")
        if type(resident_mode) is not bool or type(initially_offline) is not bool:
            raise PhysicalIssueFenceError("resident ownership mode must be explicit")
        if initially_offline and not resident_mode:
            raise PhysicalIssueFenceError("initially offline requires resident mode")
        if type(allow_resident_move) is not bool or (allow_resident_move and not resident_mode):
            raise PhysicalIssueFenceError("resident MOVE requires explicit opt-in")
        if (
            type(allow_resident_place_move) is not bool
            or (allow_resident_place_move and not (
                resident_mode and allow_resident_move
            ))
        ):
            raise PhysicalIssueFenceError(
                "PLACE requires independent original resident MOVE opt-in"
            )
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
        self._resident_mode = resident_mode
        self._observation_only = observation_only
        self._allow_resident_move = allow_resident_move
        self._allow_resident_place_move = allow_resident_place_move
        # Ordinary all-N checkpoint remains unchanged unless opted in.
        # Offline session tokens are stale birth refs, NEVER issue grants.
        self._resident_states = {
            sid: ("OFFLINE" if initially_offline else "ONLINE")
            for sid in current_sessions
        }
        self._resident_epochs = {sid: 0 for sid in current_sessions}
        self._resident_fence_refs: dict[str, str] = {}
        self._active: dict[str, IssueLease] = {}
        # Admission is not a second Action owner: this map only gates exact
        # native child IDs belonging to the already-selected original Action.
        self._native_child_ids: dict[str, dict[str, str]] = {}
        self._used_native_children: dict[str, set[str]] = {}
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
    def resident_mode(self) -> bool:
        return self._resident_mode

    @property
    def observation_only(self) -> bool:
        return self._observation_only

    @property
    def resident_states(self) -> dict[str, str]:
        with self._lock:
            return dict(self._resident_states)

    @property
    def all_residents_offline(self) -> bool:
        with self._lock:
            return (
                self._resident_mode and not self._closed
                and not self._poisoned and not self._active
                and all(x == "OFFLINE" for x in self._resident_states.values())
            )

    def _require_resident_mode(self, self_id: str) -> None:
        if (
            not self._resident_mode or self._closed or self._poisoned
            or self_id not in self._sessions or self._neutralizing
        ):
            raise PhysicalIssueFenceError("individual resident issuer unavailable")

    @property
    def requires_neutral_stop(self) -> bool:
        return self._require_neutral_stop

    @property
    def self_roster(self) -> tuple[str, ...]:
        with self._lock:
            return tuple(sorted(self._sessions))

    @property
    def current_native_sessions(self) -> dict[str, str]:
        """Read-only snapshot for pre-save host roster/source verification."""
        with self._lock:
            return dict(self._sessions)

    def hold_for_operator(self) -> None:
        """Irreversibly deny new issues after host preflight or cycle failure.

        This is an admission fence, NOT proof that an in-flight native Action
        has already stopped. Operator must reconcile any unresolved WAL.
        """
        with self._lock:
            self._closed = True
            self._poisoned = True

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
        defer_selected_children: bool = False,
    ) -> Iterator[IssueLease]:
        """Synchronous acquire before async await; finally releases on cancel."""
        with self._lock:
            if self._observation_only:
                raise PhysicalIssueFenceError("observation-only blocks all physical leases")
            if self._closed:
                raise PhysicalIssueFenceError("checkpoint fence closed physical admission")
            if self._resident_states.get(self_id) != "ONLINE":
                raise PhysicalIssueFenceError("Self resident issuer is revoked or offline")
            if self_id not in self._sessions or self._sessions[self_id] != native_session_id:
                raise PhysicalIssueFenceError("stale or foreign physical native session")
            if type(action_id) is not str or not action_id.strip():
                raise PhysicalIssueFenceError("physical Action ID required")
            if effect_family not in _EFFECT_FAMILIES:
                raise PhysicalIssueFenceError("unsupported physical effect family")
            if effect_family == "MOVE" and not (
                self._resident_mode and self._allow_resident_move
            ):
                raise PhysicalIssueFenceError("MOVE requires original resident opt-in")
            if effect_family == "MOVE_PLACE" and not (
                self._resident_mode and self._allow_resident_move
                and self._allow_resident_place_move
            ):
                raise PhysicalIssueFenceError(
                    "PLACE requires explicit original resident opt-in"
                )
            if type(defer_selected_children) is not bool or (
                defer_selected_children and effect_family not in ("EAT", "ATTACK")
            ):
                raise PhysicalIssueFenceError("deferred child binding only for L1")

            if self_id in self._active or any(
                x.action_id == action_id for x in self._active.values()
            ):
                raise PhysicalIssueFenceError("physical Action already in flight")
            record = IssueLease(
                self_id, native_session_id, action_id, self._generation,
                effect_family,
            )
            self._active[self_id] = record
            # Generic original test/adapter leases allow only their declared
            # literal Action ID. Real selected issuers explicitly bind their
            # parent-child IDs after original PREPARED WAL reservation.
            self._native_child_ids[self_id] = (
                {} if defer_selected_children
                or effect_family in ("MOVE", "MOVE_PLACE")
                else _native_children(effect_family, action_id)
                if not self._resident_mode and effect_family in ("EAT", "ATTACK")
                else {effect: action_id for effect in _EFFECT_FAMILIES[effect_family]}
            )
            self._used_native_children[self_id] = set()
        try:
            yield record
        finally:
            with self._lock:
                if self._active.get(self_id) == record:
                    del self._active[self_id]
                    self._native_child_ids.pop(self_id, None)
                    self._used_native_children.pop(self_id, None)

    def bind_native_children(
        self, *, self_id: str, native_session_id: str,
        lease_action_id: str, parent_action_id: str, family: str,
        journal: Any,
    ) -> None:
        """Bind the selected original Action only AFTER canonical fsynced PREPARED.

        The original L1 root lease is acquired before L1 creates the Action.
        Hence final native stdin must be DENIED until the L1 runner installs
        actual EAT/ATTACK parent-child IDs from the original WAL.
        """
        from relay_self.physical_action_journal import PhysicalActionJournal

        if not isinstance(journal, PhysicalActionJournal):
            raise PhysicalIssueFenceError("original durable WAL required")
        readback = PhysicalActionJournal.restore(journal.path, self_id=self_id)
        rows = readback.records
        if (
            not rows or not readback.unresolved
            or rows[-1]["action_id"] != parent_action_id
            or rows[-1]["capability"] != family
            or rows[-1]["session_id"] != native_session_id
            or (family == "MOVE_PLACE" and (
                readback.schema_version != 2
                or rows[-1].get("gait_mode") == "SNEAK"
            ))
        ):
            raise PhysicalIssueFenceError("selected child does not match PREPARED WAL")
        with self._lock:
            lease = self._active.get(self_id)
            if (
                self._poisoned or self._closed
                or self._resident_states.get(self_id) != "ONLINE"
                or lease is None or lease.native_session_id != native_session_id
                or lease.action_id != lease_action_id
                or lease.effect_family != family
                or self._native_child_ids.get(self_id) is None
                or (
                    family in ("MOVE", "MOVE_PLACE")
                    and lease.action_id != parent_action_id
                )
            ):
                raise PhysicalIssueFenceError("original selected lease no longer current")
            if self._used_native_children.get(self_id):
                raise PhysicalIssueFenceError("cannot rebind already issued native effects")
            self._native_child_ids[self_id] = _native_children(family, parent_action_id)

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
            if self._observation_only:
                raise PhysicalIssueFenceError("observation-only blocks all native effects")
            if self._poisoned:
                raise PhysicalIssueFenceError("native physical effect blocked by checkpoint")
            resident_state = self._resident_states.get(self_id)
            # A quarantined MOVE may still need one *exact* STOP to prevent
            # continued walking. No other motion/effect can follow quarantine.
            active_motion = self._active.get(self_id)
            quarantine_stop = (
                resident_state == "QUARANTINED"
                and not self._closed and not self._poisoned
                and active_motion is not None
                and active_motion.effect_family == "MOVE"
                and effect == "clear_controls"
                and self._native_child_ids.get(self_id, {}).get(effect) == action_id
            )
            if resident_state != "ONLINE" and not quarantine_stop:
                raise PhysicalIssueFenceError("Self resident native effect blocked")
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
                or self._native_child_ids.get(self_id, {}).get(effect) != action_id
                or action_id in self._used_native_children.get(self_id, set())
            ):
                raise PhysicalIssueFenceError(
                    "native effect requires active capability-scoped issuer lease"
                )
            # One-shot final-stdin admission, consumed before native IO.
            # Write failures retain PREPARED WAL; no replay of the child.
            self._used_native_children[self_id].add(action_id)

    def begin_neutralization(self) -> str:
        """Lock normal physical effects before one supervised STOP per Self.

        An in-flight EAT/ATTACK is a fatal dirty cut; never attempt STOP over
        an unresolved physical issue. This is a PRE-checkpoint phase; the
        cognition/World cut starts only after stop readback is verified.
        """
        with self._lock:
            if self._observation_only:
                raise PhysicalIssueFenceError("observation-only blocks neutralization effects")
            if self._closed or self._poisoned:
                raise PhysicalIssueFenceError("physical neutralization already held")
            if self._resident_mode and any(
                x != "ONLINE" for x in self._resident_states.values()
            ):
                raise PhysicalIssueFenceError(
                    "mixed offline residents require World-only path, not all-N STOP"
                )
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
            if self._resident_mode and any(
                x != "ONLINE" for x in self._resident_states.values()
            ):
                raise PhysicalIssueFenceError(
                    "mixed resident presence cannot masquerade as all-N cut"
                )
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

    def quarantine_resident(
        self, *, self_id: str, native_session_id: str,
    ) -> ResidentIssuerFence:
        """Atomically remove ONE native Self's final-stdin issue permission.

        A running Action is not force-cancelled by this operation. Its
        unfinished lease is returned as evidence; retirement is forbidden
        until the original journal and native process have been reconciled.
        Other Self keep their leases and current native source IDs.
        """
        with self._lock:
            self._require_resident_mode(self_id)
            if self._sessions[self_id] != native_session_id:
                raise PhysicalIssueFenceError("foreign resident native session")
            if self._resident_states[self_id] == "OFFLINE":
                raise PhysicalIssueFenceError("already retired individual resident")
            if self._resident_states[self_id] == "ONLINE":
                self._resident_epochs[self_id] += 1
                self._resident_states[self_id] = "QUARANTINED"
                self._resident_fence_refs[self_id] = (
                    f"resident-{self_id}-{self._resident_epochs[self_id]}"
                )
            active = self._active.get(self_id)
            return ResidentIssuerFence(
                self_id=self_id,
                former_native_session_id=native_session_id,
                fence_ref=self._resident_fence_refs[self_id],
                active_action_ids=(active.action_id,) if active is not None else (),
                no_physical_inflight=active is None,
            )

    def retire_resident(
        self, *, self_id: str, native_session_id: str,
        fence_ref: str, physical_wal_file: Path,
    ) -> ResidentIssuerRetired:
        """Read ORIGINAL durable physical journal; only THIS issuer retires Self.

        All new effect writes were already blocked by quarantine. IO is done
        outside the issuer lock so other Self continue issuing Actions.
        Revalidate exact old owner fence and active work after disk readback.
        Does not assert that a native process/GPU/backend actually terminated.
        """
        from relay_self.physical_action_journal import PhysicalActionJournal

        with self._lock:
            self._require_resident_mode(self_id)
            if (
                self._resident_states[self_id] != "QUARANTINED"
                or self._sessions[self_id] != native_session_id
                or self._resident_fence_refs.get(self_id) != fence_ref
                or self_id in self._active
            ):
                raise PhysicalIssueFenceError(
                    "individual retirement requires closed, drained original issue"
                )
        journal = PhysicalActionJournal.restore(
            Path(physical_wal_file), self_id=self_id,
        )
        journal.require_clear()
        with self._lock:
            self._require_resident_mode(self_id)
            if (
                self._resident_states[self_id] != "QUARANTINED"
                or self._sessions[self_id] != native_session_id
                or self._resident_fence_refs.get(self_id) != fence_ref
                or self_id in self._active
            ):
                raise PhysicalIssueFenceError("resident issuer changed during retirement")
            self._resident_states[self_id] = "OFFLINE"
            return ResidentIssuerRetired(
                self_id, native_session_id, fence_ref, journal.digest,
            )

    def admit_resident_login(
        self, *, self_id: str, former_native_session_id: str,
        fresh_native_session_id: str, physical_wal_file: Path,
        source_world_epoch_validated: bool,
    ) -> None:
        """Rebind ONE resident only after source-verified WorldBody & WAL read.

        The host must independently verify Paper and native new-session proof,
        then complete the original cognitive login before calling this. A
        bool here is a precondition, never a replacement for source evidence.
        No other Self session is modified or silently accepted.
        """
        from relay_self.physical_action_journal import PhysicalActionJournal

        if source_world_epoch_validated is not True:
            raise PhysicalIssueFenceError("new World epoch source not validated")
        with self._lock:
            self._require_resident_mode(self_id)
            if (
                self._resident_states[self_id] != "OFFLINE"
                or self._sessions[self_id] != former_native_session_id
                or type(fresh_native_session_id) is not str
                or not fresh_native_session_id.strip()
                or fresh_native_session_id == former_native_session_id
                or fresh_native_session_id in self._sessions.values()
                or self_id in self._active
            ):
                raise PhysicalIssueFenceError(
                    "new resident session not fresh, source-scoped or safely retired"
                )
            expected_epoch = self._resident_epochs[self_id]
        PhysicalActionJournal.restore(
            Path(physical_wal_file), self_id=self_id,
        ).require_clear()
        with self._lock:
            self._require_resident_mode(self_id)
            if (
                self._resident_states[self_id] != "OFFLINE"
                or self._sessions[self_id] != former_native_session_id
                or expected_epoch != self._resident_epochs[self_id]
                or fresh_native_session_id in self._sessions.values()
            ):
                raise PhysicalIssueFenceError("individual issuer changed during login")
            self._sessions[self_id] = fresh_native_session_id
            self._resident_states[self_id] = "ONLINE"
            self._resident_epochs[self_id] += 1
            self._resident_fence_refs.pop(self_id, None)

    async def issue_move(self, session: Any, **kwargs: Any) -> Any:
        """Same original PhysicalIssueAdmission, WAL and actor lease as EAT.

        Only after a Self has selected its own existing PhysicalActionPort
        proposal. No new Skill/Goal chooser, source author or native sender.
        """
        from experiments.cognitive_physical_move_issue_dev import issue_selected_move_dev

        proposal = kwargs["proposal"]
        parent = proposal.binding.action_id
        with self.lease(
            self_id=proposal.binding.scope.self_id,
            native_session_id=session.started.session_id,
            action_id=parent,
            effect_family="MOVE",
        ):
            def register(selected: str) -> None:
                self.bind_native_children(
                    self_id=proposal.binding.scope.self_id,
                    native_session_id=session.started.session_id,
                    lease_action_id=parent, parent_action_id=selected,
                    family="MOVE", journal=kwargs["journal"],
                )
            return await issue_selected_move_dev(
                session, **kwargs, bind_native_children=register,
            )

    async def issue_eat(self, session: Any, **kwargs: Any) -> Any:
        """Wrap existing native issuer, WAL and async ACK+consequence readback."""
        from experiments.cognitive_physical_eat_issue_dev import issue_selected_eat_dev

        proposal = kwargs["proposal"]
        with self.lease(
            self_id=proposal.binding.scope.self_id,
            native_session_id=session.started.session_id,
            action_id=proposal.binding.action_id,
            effect_family="EAT", defer_selected_children=True,
        ):
            original = kwargs.get("journal")
            # The physical issuer performs the canonical PREPARED reservation;
            # it supplies the one-time callback before ANY effect is written.
            def register(parent: str) -> None:
                self.bind_native_children(
                    self_id=proposal.binding.scope.self_id,
                    native_session_id=session.started.session_id,
                    lease_action_id=proposal.binding.action_id,
                    parent_action_id=parent, family="EAT", journal=original,
                )
            return await issue_selected_eat_dev(
                session, **kwargs, bind_native_children=register,
            )

    async def issue_attack(self, session: Any, **kwargs: Any) -> Any:
        """Wrap existing ATTACK issuer including uncertain-outcome handling."""
        from experiments.cognitive_physical_attack_issue_dev import issue_selected_attack_dev

        proposal = kwargs["proposal"]
        with self.lease(
            self_id=proposal.binding.scope.self_id,
            native_session_id=session.started.session_id,
            action_id=proposal.binding.action_id,
            effect_family="ATTACK", defer_selected_children=True,
        ):
            def register(parent: str) -> None:
                self.bind_native_children(
                    self_id=proposal.binding.scope.self_id,
                    native_session_id=session.started.session_id,
                    lease_action_id=proposal.binding.action_id,
                    parent_action_id=parent, family="ATTACK",
                    journal=kwargs["journal"],
                )
            return await issue_selected_attack_dev(
                session, **kwargs, bind_native_children=register,
            )

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
            effect_family="EAT", defer_selected_children=True,
        ):
            def register(parent: str) -> None:
                self.bind_native_children(
                    self_id=kwargs["self_id"], native_session_id=session.started.session_id,
                    lease_action_id=admission_ref, parent_action_id=parent,
                    family="EAT", journal=kwargs["journal"],
                )
            return await issue_eat_from_selected_l1_dev(
                session, receipt, **kwargs, bind_native_children=register,
            )

    async def run_l1_attack(
        self, session: Any, receipt: Any, *, admission_ref: str, **kwargs: Any,
    ) -> Any:
        """Fenced existing L1 ATTACK runner from selected Intent through readback."""
        from experiments.cognitive_physical_attack_runner import issue_attack_from_selected_l1_dev

        with self.lease(
            self_id=kwargs["self_id"],
            native_session_id=session.started.session_id,
            action_id=admission_ref,
            effect_family="ATTACK", defer_selected_children=True,
        ):
            def register(parent: str) -> None:
                self.bind_native_children(
                    self_id=kwargs["self_id"], native_session_id=session.started.session_id,
                    lease_action_id=admission_ref, parent_action_id=parent,
                    family="ATTACK", journal=kwargs["journal"],
                )
            return await issue_attack_from_selected_l1_dev(
                session, receipt, **kwargs, bind_native_children=register,
            )

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
