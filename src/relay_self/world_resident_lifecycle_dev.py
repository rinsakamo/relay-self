"""#860/#851 DEV: World-resident, independently fallible Self login/logout.

This is a typed state/fencing contract, NOT a new Action issuer, actual native
login client, L1/L2 cancellation engine, Paper owner or durable Self store.
Real receipt producers must be independently connected and qualified. In
particular changing a Presence state never authorizes a physical Action.
"""
from __future__ import annotations

import re
import threading
from dataclasses import dataclass
from enum import Enum


class ResidentLifecycleError(ValueError):
    """Invalid source, unquiesced actor, ambiguous World branch, or stale epoch."""


def _ref(name: str, value: object) -> str:
    if type(value) is not str or not value.strip() or "\n" in value:
        raise ResidentLifecycleError(f"{name} must be nonempty single-line text")
    return value


def _identity(value: object) -> str:
    if type(value) is not str or re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_-]{0,79}", value) is None:
        raise ResidentLifecycleError("invalid individual Self identity")
    return value


def _natural(name: str, value: object) -> int:
    if type(value) is not int or value < 0:
        raise ResidentLifecycleError(f"{name} must be nonnegative integer")
    return value


@dataclass(frozen=True, slots=True)
class WorldLifetime:
    """World/branch + host epoch + Paper process source (not only a tick)."""

    world_id: str
    branch_id: str
    paper_session_id: str
    epoch: int
    world_tick: int

    def __post_init__(self) -> None:
        for name in ("world_id", "branch_id", "paper_session_id"):
            _ref(name, getattr(self, name))
        _natural("World epoch", self.epoch)
        _natural("World tick", self.world_tick)


class Presence(str, Enum):
    OFFLINE = "OFFLINE"
    LOGIN_PENDING = "LOGIN_PENDING"
    ONLINE = "ONLINE"
    LOGOUT_PENDING = "LOGOUT_PENDING"
    QUARANTINED = "QUARANTINED"


@dataclass(frozen=True, slots=True)
class LoginTicket:
    self_id: str
    login_seq: int
    world: WorldLifetime
    persisted_cognition_ref: str
    worldbody_reobservation_required: bool = True
    action_issue_authorized: bool = False


@dataclass(frozen=True, slots=True)
class NativeLoginEvidence:
    """Claim supplied by the existing native+WAL owner, not this module."""

    self_id: str
    login_seq: int
    world_id: str
    branch_id: str
    paper_session_id: str
    world_epoch: int
    native_session_id: str
    observed_world_tick: int
    observation_ref: str
    old_native_invalidated: bool
    physical_wal_clear: bool
    stale_gpu_fenced: bool
    stale_transport_fenced: bool
    new_native_source_verified: bool
    action_issue_authorized: bool = False


@dataclass(frozen=True, slots=True)
class LogoutFenceEvidence:
    """Existing original issuer + canonical WAL owner jointly attest this."""

    self_id: str
    world_epoch: int
    native_session_id: str
    source_ref: str
    persisted_cognition_ref: str
    physical_issuer_revoked: bool
    no_physical_inflight: bool
    physical_wal_clear: bool
    native_terminated: bool
    stale_gpu_fenced: bool
    peer_transport_drained: bool
    action_issue_authorized: bool = False


@dataclass(frozen=True, slots=True)
class WorldInstallationEvidence:
    """Must come from an owned Paper/external World source, not a Self belief."""

    previous_world: WorldLifetime
    installed_world: WorldLifetime
    source_ref: str
    former_paper_terminated: bool
    fresh_paper_owned: bool
    world_file_integrity_verified: bool
    old_world_actions_fenced: bool
    fresh_worldbody_required: bool = True
    historical_replay_performed: bool = False
    portable_body_state_imported: bool = False
    action_issue_authorized: bool = False


@dataclass(frozen=True, slots=True)
class WorldOnlyQuiescenceEvidence:
    """Original physical/GPU/peer owners, not a local presence flag, assert idle.

    Deliberately cannot be generated from a SelfPresenceView. The caller
    must provide a source-qualified retired-issuer audit independently.
    """

    world_epoch: int
    checked_self_ids: tuple[str, ...]
    source_ref: str
    original_physical_issuer_closed: bool
    native_sessions_absent: bool
    no_unresolved_physical_actions: bool
    all_gpu_epochs_retired: bool
    pending_peer_messages_empty: bool
    action_issue_authorized: bool = False


@dataclass(frozen=True, slots=True)
class PresenceView:
    self_id: str
    status: Presence
    native_session_id: str | None
    world_epoch: int | None
    persisted_cognition_ref: str
    last_observed_world: WorldLifetime | None
    worldbody_reobservation_required: bool
    action_issue_authorized: bool = False


@dataclass(slots=True)
class _Resident:
    self_id: str
    status: Presence
    persisted_cognition_ref: str
    last_observed_world: WorldLifetime | None = None
    native_session_id: str | None = None
    bound_world_epoch: int | None = None
    pending_ticket: LoginTicket | None = None
    worldbody_reobservation_required: bool = True


class WorldResidentLifecycle:
    """World can tick while individual Self sessions are absent/failed.

    A QUARANTINED Self cannot log back in or participate in World replacement
    until the original external physical/WAL owner proves it safe to retire.
    Other Self remain ONLINE and are not implicitly frozen. World replacement
    (including a same-World restart) requires *all* Self safely OFFLINE.
    """

    def __init__(
        self, *, world: WorldLifetime,
        persisted_self_refs: dict[str, str],
        independent_native_world_clock: bool = False,
    ) -> None:
        if (
            not isinstance(world, WorldLifetime)
            or type(persisted_self_refs) is not dict
            or type(independent_native_world_clock) is not bool
            or (independent_native_world_clock and (
                world.epoch < 1
                or not world.paper_session_id.startswith("paper-owned-")
            ))
        ):
            raise ResidentLifecycleError("one World and explicit Self registry required")
        for sid, ref in persisted_self_refs.items():
            _identity(sid)
            _ref("persisted cognition source", ref)
        self._lock = threading.RLock()
        self._world = world
        # Native full-day World time and Paper process-local tick are distinct clocks.
        self._independent_native_world_clock = independent_native_world_clock
        self._self = {
            sid: _Resident(sid, Presence.OFFLINE, ref)
            for sid, ref in persisted_self_refs.items()
        }
        self._login_seq = 0
        self._world_held = False
        self._world_transition = False

    @property
    def world(self) -> WorldLifetime:
        with self._lock:
            return self._world

    @property
    def world_held(self) -> bool:
        with self._lock:
            return self._world_held

    @property
    def self_roster(self) -> tuple[str, ...]:
        with self._lock:
            return tuple(sorted(self._self))

    def view(self, self_id: str) -> PresenceView:
        with self._lock:
            try:
                actor = self._self[self_id]
            except (KeyError, TypeError) as exc:
                raise ResidentLifecycleError("unknown Self") from exc
            return PresenceView(
                actor.self_id, actor.status, actor.native_session_id,
                actor.bound_world_epoch, actor.persisted_cognition_ref,
                actor.last_observed_world,
                actor.worldbody_reobservation_required,
            )

    def can_world_only_checkpoint(self) -> bool:
        with self._lock:
            return (
                not self._world_held and not self._world_transition
                and all(a.status is Presence.OFFLINE for a in self._self.values())
            )

    def require_world_only_quiescence(
        self, evidence: WorldOnlyQuiescenceEvidence,
    ) -> None:
        """External original issuer proof, not simply an empty ONLINE list."""
        with self._lock:
            if (
                not self.can_world_only_checkpoint()
                or not isinstance(evidence, WorldOnlyQuiescenceEvidence)
                or evidence.world_epoch != self._world.epoch
                or evidence.checked_self_ids != self.self_roster
                or type(evidence.source_ref) is not str
                or not evidence.source_ref.strip()
                or evidence.original_physical_issuer_closed is not True
                or evidence.native_sessions_absent is not True
                or evidence.no_unresolved_physical_actions is not True
                or evidence.all_gpu_epochs_retired is not True
                or evidence.pending_peer_messages_empty is not True
                or evidence.action_issue_authorized is not False
            ):
                raise ResidentLifecycleError(
                    "World-only transition lacks original issuer retirement proof"
                )

    def world_tick(self, *, paper_session_id: str, tick: int,
                   source_ref: str) -> WorldLifetime:
        """The external Paper source progresses independently of cognition."""
        with self._lock:
            _ref("tick source", source_ref)
            _natural("World tick", tick)
            if self._world_held or self._world_transition:
                raise ResidentLifecycleError("World fenced while transitioning")
            if (
                self._world.paper_session_id != paper_session_id
                or tick < self._world.world_tick
            ):
                raise ResidentLifecycleError("foreign or regressed Paper tick")
            current = self._world
            self._world = WorldLifetime(
                current.world_id, current.branch_id, current.paper_session_id,
                current.epoch, tick,
            )
            return self._world

    def begin_login(self, self_id: str) -> LoginTicket:
        with self._lock:
            actor = self._actor(self_id)
            if (
                self._world_held or self._world_transition
                or actor.status is not Presence.OFFLINE
            ):
                raise ResidentLifecycleError("Self is not offline/World unavailable")
            self._login_seq += 1
            ticket = LoginTicket(
                self_id, self._login_seq, self._world,
                actor.persisted_cognition_ref,
            )
            actor.status = Presence.LOGIN_PENDING
            actor.pending_ticket = ticket
            return ticket

    def complete_login(
        self, ticket: LoginTicket, evidence: NativeLoginEvidence,
    ) -> PresenceView:
        with self._lock:
            if (
                not isinstance(ticket, LoginTicket)
                or not isinstance(evidence, NativeLoginEvidence)
            ):
                raise ResidentLifecycleError("typed native login evidence required")
            actor = self._actor(ticket.self_id)
            if (
                actor.status is not Presence.LOGIN_PENDING
                or actor.pending_ticket != ticket
                or ticket.world.epoch != self._world.epoch
                or ticket.world.paper_session_id != self._world.paper_session_id
                or ticket.world.world_id != self._world.world_id
                or ticket.world.branch_id != self._world.branch_id
                or self._world_transition or self._world_held
                or evidence.self_id != ticket.self_id
                or evidence.login_seq != ticket.login_seq
                or evidence.world_id != self._world.world_id
                or evidence.branch_id != self._world.branch_id
                or evidence.paper_session_id != self._world.paper_session_id
                or evidence.world_epoch != self._world.epoch
                or type(evidence.observed_world_tick) is not int
                or (
                    not self._independent_native_world_clock
                    and evidence.observed_world_tick < self._world.world_tick
                )
                or evidence.native_session_id in {
                    a.native_session_id for a in self._self.values()
                    if a.status is Presence.ONLINE
                }
                or not evidence.old_native_invalidated
                or not evidence.physical_wal_clear
                or not evidence.stale_gpu_fenced
                or not evidence.stale_transport_fenced
                or not evidence.new_native_source_verified
                or evidence.action_issue_authorized is not False
            ):
                raise ResidentLifecycleError("login source/epoch/fence not qualified")
            _ref("fresh native session", evidence.native_session_id)
            _ref("new WorldBody observation", evidence.observation_ref)
            actor.native_session_id = evidence.native_session_id
            actor.bound_world_epoch = self._world.epoch
            actor.status = Presence.ONLINE
            actor.pending_ticket = None
            actor.worldbody_reobservation_required = False
            actor.last_observed_world = WorldLifetime(
                self._world.world_id, self._world.branch_id,
                self._world.paper_session_id, self._world.epoch,
                self._world.world_tick if self._independent_native_world_clock
                else evidence.observed_world_tick,
            )
            return self.view(ticket.self_id)

    def begin_logout(self, self_id: str) -> PresenceView:
        with self._lock:
            actor = self._actor(self_id)
            if actor.status is not Presence.ONLINE or self._world_transition:
                raise ResidentLifecycleError("Self is not online")
            actor.status = Presence.LOGOUT_PENDING
            return self.view(self_id)

    def finish_logout(
        self, self_id: str, proof: LogoutFenceEvidence,
    ) -> PresenceView:
        with self._lock:
            actor = self._actor(self_id)
            if actor.status not in (Presence.LOGOUT_PENDING, Presence.QUARANTINED):
                raise ResidentLifecycleError("logout must follow session isolation")
            if not self._retired(actor, proof):
                actor.status = Presence.QUARANTINED
                raise ResidentLifecycleError("Self retirement unverified; quarantine")
            actor.status = Presence.OFFLINE
            actor.persisted_cognition_ref = proof.persisted_cognition_ref
            actor.native_session_id = None
            actor.bound_world_epoch = None
            actor.pending_ticket = None
            actor.worldbody_reobservation_required = True
            return self.view(self_id)

    def fail_self(
        self, self_id: str, *,
        terminal_proof: LogoutFenceEvidence | None = None,
    ) -> PresenceView:
        """One failed Self becomes isolated, not a global N-Self barrier.

        No proof means QUARANTINED; World may still produce new observations
        and other registered Self retain their ONLINE state. This is NOT proof
        an outstanding physical effect has been canceled. World switch and
        this Self's re-login remain forbidden until positive retirement.
        """
        with self._lock:
            actor = self._actor(self_id)
            if actor.status not in (
                Presence.ONLINE, Presence.LOGIN_PENDING,
                Presence.LOGOUT_PENDING, Presence.QUARANTINED,
            ):
                raise ResidentLifecycleError("cannot fail an offline Self")
            actor.status = Presence.QUARANTINED
            if terminal_proof is not None and self._retired(actor, terminal_proof):
                return self.finish_logout(self_id, terminal_proof)
            return self.view(self_id)

    def begin_world_transition(self) -> WorldLifetime:
        """No Self session or unresolved QUARANTINE can cross this barrier."""
        with self._lock:
            if not self.can_world_only_checkpoint():
                raise ResidentLifecycleError(
                    "World switch requires every Self safely offline"
                )
            self._world_transition = True
            return self._world

    def abort_world_transition(self) -> None:
        """Unknown stop/restart is terminal; never resume old Action epochs."""
        with self._lock:
            self._world_held = True
            self._world_transition = False

    def install_world(
        self, evidence: WorldInstallationEvidence,
    ) -> WorldLifetime:
        with self._lock:
            if not isinstance(evidence, WorldInstallationEvidence):
                raise ResidentLifecycleError("owned World source receipt required")
            if (
                not self._world_transition or self._world_held
                or not all(a.status is Presence.OFFLINE for a in self._self.values())
                or evidence.previous_world != self._world
                or evidence.installed_world.epoch != self._world.epoch + 1
                or evidence.installed_world.paper_session_id == self._world.paper_session_id
                or not evidence.former_paper_terminated
                or not evidence.fresh_paper_owned
                or not evidence.world_file_integrity_verified
                or not evidence.old_world_actions_fenced
                or evidence.fresh_worldbody_required is not True
                or evidence.historical_replay_performed is not False
                or evidence.portable_body_state_imported is not False
                or evidence.action_issue_authorized is not False
            ):
                # A failed source-qualified World swap cannot be retried by
                # interpreting the old Paper state as if still current.
                self.abort_world_transition()
                raise ResidentLifecycleError("World installation source/epoch invalid; HOLD")
            _ref("owned new World evidence", evidence.source_ref)
            self._world = evidence.installed_world
            self._world_transition = False
            # Identity and historical cognition remain; old Body/Present
            # targets and every previous native session are permanently stale.
            for actor in self._self.values():
                actor.worldbody_reobservation_required = True
                actor.native_session_id = None
                actor.bound_world_epoch = None
            return self._world

    def _actor(self, self_id: str) -> _Resident:
        try:
            return self._self[_identity(self_id)]
        except KeyError as exc:
            raise ResidentLifecycleError("Self not enrolled") from exc

    def _retired(
        self, actor: _Resident, proof: LogoutFenceEvidence | None,
    ) -> bool:
        if not isinstance(proof, LogoutFenceEvidence):
            return False
        return (
            actor.native_session_id is not None
            and proof.self_id == actor.self_id
            and proof.native_session_id == actor.native_session_id
            and proof.world_epoch == actor.bound_world_epoch
            and type(proof.source_ref) is str and bool(proof.source_ref.strip())
            and type(proof.persisted_cognition_ref) is str
            and bool(proof.persisted_cognition_ref.strip())
            and proof.physical_issuer_revoked is True
            and proof.no_physical_inflight is True
            and proof.physical_wal_clear is True
            and proof.native_terminated is True
            and proof.stale_gpu_fenced is True
            and proof.peer_transport_drained is True
            and proof.action_issue_authorized is False
        )
