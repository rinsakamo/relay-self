"""#860 DEV: real original physical issuer + owned per-Self native lifecycle.

Scope is deliberately NO GPU/LLM work and NO peer transport. The exact
Mineflayer child is owned by the original process adapter; user code must
not bypass its final physical admission hook. No dynamic cognition/LLM task
scheduler or model backend is attested by the inert boundary.
"""
from __future__ import annotations

from collections.abc import Awaitable, Callable
from pathlib import Path

from adapters.mineflayer.process_session import MineflayerProcessSession
from adapters.mineflayer.python_protocol import MineflayerLaunchConfig
from relay_self.checkpointed_cognitive_runtime_dev import CheckpointedCognitiveOwner
from relay_self.owned_native_rejoin_cohort_dev import verify_native_spawn_probe
from relay_self.owned_paper_world_dev import OwnedPaperWorld
from relay_self.persistent_cognition import (
    load_persistent_cognition,
    save_persistent_cognition,
)
from relay_self.physical_action_journal import PhysicalActionJournal
from relay_self.physical_issue_admission_dev import (
    PhysicalIssueAdmission,
    ResidentIssuerRetired,
)
from relay_self.world_resident_lifecycle_dev import (
    LoginTicket,
    LogoutFenceEvidence,
    NativeLoginEvidence,
    Presence,
    WorldOnlyQuiescenceEvidence,
    WorldResidentLifecycle,
)


class OwnedResidentBridgeError(RuntimeError):
    """No owner proof, stale session, unretired Action or unsupported work."""


class InertResidentWorkBoundary:
    """Proof scope is LIMITED to the explicitly owned no-compute/no-peer path.

    Attempted external work through this owner taints it permanently until an
    operator builds a genuinely different retirement proof. It does not claim
    to inspect all GPU activity, other native bridges or message producers.
    """

    def __init__(self, self_ids: tuple[str, ...]) -> None:
        self._ids = frozenset(self_ids)
        self._tainted: set[str] = set()

    def reject_gpu_task(self, self_id: str, task_id: str) -> None:
        if self_id not in self._ids or not task_id:
            raise OwnedResidentBridgeError("foreign or unnamed GPU task")
        self._tainted.add(self_id)
        raise OwnedResidentBridgeError("GPU tasks forbidden in inert resident DEV")

    def reject_peer_send(self, self_id: str, message_id: str) -> None:
        if self_id not in self._ids or not message_id:
            raise OwnedResidentBridgeError("foreign or unnamed peer message")
        self._tainted.add(self_id)
        raise OwnedResidentBridgeError("peer messages forbidden in inert resident DEV")

    def require_clean(self, self_id: str) -> None:
        if self_id not in self._ids or self_id in self._tainted:
            raise OwnedResidentBridgeError("resident compute/transport scope not clean")


class OwnedResidentPhysicalBridge:
    """Calls the EXISTING original issuer, never issues physical Action itself.

    Does not automatically change Minecraft playerdata or copy bodies between
    Worlds. Any actual native Action must still use original guarded entrypoint.
    """

    def __init__(
        self, *, lifecycle: WorldResidentLifecycle,
        physical: PhysicalIssueAdmission,
        paper: OwnedPaperWorld,
        configs: dict[str, MineflayerLaunchConfig],
        owners: dict[str, CheckpointedCognitiveOwner],
        launch: Callable[
            [MineflayerLaunchConfig], Awaitable[MineflayerProcessSession]
        ] = MineflayerProcessSession.launch,
        probe_timeout_s: float = 12.0,
    ) -> None:
        if (
            not isinstance(lifecycle, WorldResidentLifecycle)
            or not isinstance(physical, PhysicalIssueAdmission)
            or not physical.resident_mode
            or not isinstance(paper, OwnedPaperWorld)
            or not physical.all_residents_offline
            or tuple(sorted(configs)) != lifecycle.self_roster
            or tuple(sorted(owners)) != lifecycle.self_roster
            or physical.self_roster != lifecycle.self_roster
            or len({config.username for config in configs.values()})
            != len(configs)
            or any(
                not isinstance(c, MineflayerLaunchConfig)
                or c.version != "1.21.8" or c.host != "127.0.0.1"
                for c in configs.values()
            )
            or any(
                not isinstance(o, CheckpointedCognitiveOwner)
                or o.self_id != sid or o.cohort is not None
                or o.native_session_id != physical.current_native_sessions[sid]
                or o.supervisor.open_actions
                for sid, o in owners.items()
            )
            or not callable(launch)
            or type(probe_timeout_s) not in (float, int)
            or not 0 < probe_timeout_s <= 60
        ):
            raise OwnedResidentBridgeError(
                "single unbound owned native/physical/retained cognition roster required"
            )
        self.lifecycle = lifecycle
        self.physical = physical
        self.paper = paper
        self.configs = dict(configs)
        self.owners = dict(owners)
        self.launch = launch
        self.probe_timeout_s = float(probe_timeout_s)
        self.work = InertResidentWorkBoundary(lifecycle.self_roster)
        self.sessions: dict[str, MineflayerProcessSession] = {}
        self.retired: dict[str, ResidentIssuerRetired] = {}
        self._pending_login: set[str] = set()

    def _check_world(self) -> None:
        world = self.lifecycle.world
        if (
            self.paper.owned_session_id != world.paper_session_id
            or self.paper.world_id != world.world_id
            or self.paper.branch_id != world.branch_id
            or self.paper.held_uncertain
        ):
            raise OwnedResidentBridgeError("old/foreign Paper World owner")

    async def login(self, self_id: str) -> LoginTicket:
        self._check_world()
        self.work.require_clean(self_id)
        ticket = self.lifecycle.begin_login(self_id)
        prior = self.physical.current_native_sessions[self_id]
        launched = None
        self._pending_login.add(self_id)
        try:
            config = self.configs[self_id]
            launched = await self.launch(config)
            if (
                launched.process_returncode is not None
                or launched.started.config != config
                or launched.started.session_id == prior
                or launched.started.session_id in {
                    other.started.session_id for other in self.sessions.values()
                }
            ):
                raise OwnedResidentBridgeError("native spawn session not fresh")
            # Install final stdin capability guard BEFORE any sensor probe or
            # possible new Skill. The original issuer still says OFFLINE.
            def effect(native_id: str, effect_kind: str, action_id: str) -> None:
                self.physical.require_native_effect(
                    self_id=self_id,
                    native_session_id=native_id,
                    effect=effect_kind,
                    action_id=action_id,
                )

            launched.install_effect_admission(effect)
            _, _, request_id, observed_tick = await verify_native_spawn_probe(
                launched, timeout_s=self.probe_timeout_s,
            )
            self._check_world()
            if self.lifecycle.world.epoch != ticket.world.epoch:
                raise OwnedResidentBridgeError("World changed during native login")
            if launched.process_returncode is not None:
                raise OwnedResidentBridgeError("new native process exited after probe")
            owner = self.owners[self_id]
            if owner.supervisor.open_actions:
                raise OwnedResidentBridgeError("original Action supervisor still active")
            PhysicalActionJournal.restore(
                owner.files.physical_wal_file, self_id=self_id,
            ).require_clear()
            self.work.require_clean(self_id)
            evidence = NativeLoginEvidence(
                self_id, ticket.login_seq, ticket.world.world_id,
                ticket.world.branch_id, ticket.world.paper_session_id,
                ticket.world.epoch, launched.started.session_id,
                observed_tick, request_id, True, True, True, True, True,
            )
            self.lifecycle.complete_login(ticket, evidence)
            if self.lifecycle.world.epoch != ticket.world.epoch:
                raise OwnedResidentBridgeError("World epoch changed before issue rebind")
            # Original issuer is the ONLY path that now admits new effects.
            self.physical.admit_resident_login(
                self_id=self_id,
                former_native_session_id=prior,
                fresh_native_session_id=launched.started.session_id,
                physical_wal_file=owner.files.physical_wal_file,
                source_world_epoch_validated=True,
            )
            owner.native_session_id = launched.started.session_id
            owner.last_observed_tick = observed_tick
            owner.fresh_native_observation_required = False
            self.sessions[self_id] = launched
            self.retired.pop(self_id, None)
            return ticket
        except BaseException:
            # If source verification fails, NEVER grant a new issuer lease.
            # If admit succeeded before an unexpected failure, quarantine it.
            current = self.physical.current_native_sessions[self_id]
            if launched is not None and current == launched.started.session_id:
                self.physical.quarantine_resident(
                    self_id=self_id, native_session_id=current,
                )
            if self.lifecycle.view(self_id).status is not Presence.QUARANTINED:
                self.lifecycle.fail_self(self_id)
            if launched is not None:
                try:
                    await launched.terminate()
                except BaseException:
                    pass
            raise
        finally:
            self._pending_login.discard(self_id)

    def quarantine(self, self_id: str) -> None:
        """Synchronous, per-Self immediate issue block before any async wait."""
        if self_id not in self.sessions:
            raise OwnedResidentBridgeError("no currently owned Self session")
        current = self.sessions[self_id].started.session_id
        self.physical.quarantine_resident(
            self_id=self_id, native_session_id=current,
        )
        self.lifecycle.fail_self(self_id)

    async def logout(self, self_id: str) -> LogoutFenceEvidence:
        """Independent physical, journal, native process and cognition checks."""
        self._check_world()
        session = self.sessions.get(self_id)
        if session is None:
            raise OwnedResidentBridgeError("logout without owned native session")
        native_id = session.started.session_id
        view = self.lifecycle.view(self_id)
        if view.native_session_id != native_id or view.status not in (
            Presence.ONLINE, Presence.QUARANTINED,
        ):
            raise OwnedResidentBridgeError("wrong Self physical session at logout")
        # Close final physical effect admission synchronously before awaits.
        fence = self.physical.quarantine_resident(
            self_id=self_id, native_session_id=native_id,
        )
        if view.status is Presence.ONLINE:
            self.lifecycle.begin_logout(self_id)
        self.work.require_clean(self_id)
        owner = self.owners[self_id]
        try:
            if fence.active_action_ids or owner.supervisor.open_actions:
                raise OwnedResidentBridgeError("in-flight native Action; quarantine")
            result = await session.terminate()
            if session.process_returncode is None or result is None:
                raise OwnedResidentBridgeError("original owned native not terminated")
            # Validate durable cognition via original persistent owner.
            save_persistent_cognition(owner.files.cognition_file, owner.retained)
            if load_persistent_cognition(owner.files.cognition_file) != owner.retained:
                raise OwnedResidentBridgeError("canonical cognition persistence mismatch")
            retirement = self.physical.retire_resident(
                self_id=self_id, native_session_id=native_id,
                fence_ref=fence.fence_ref,
                physical_wal_file=owner.files.physical_wal_file,
            )
            self.work.require_clean(self_id)
            persisted_ref = f"cognition-file:{owner.files.cognition_file}"
            proof = LogoutFenceEvidence(
                self_id=self_id,
                world_epoch=self.lifecycle.world.epoch,
                native_session_id=native_id,
                source_ref=f"original-issuer:{retirement.fence_ref}:{retirement.physical_wal_digest}",
                persisted_cognition_ref=persisted_ref,
                physical_issuer_revoked=retirement.physical_issuer_revoked,
                no_physical_inflight=retirement.no_physical_inflight,
                physical_wal_clear=retirement.physical_wal_clear,
                native_terminated=session.process_returncode is not None,
                stale_gpu_fenced=True, peer_transport_drained=True,
            )
            self.lifecycle.finish_logout(self_id, proof)
            self.retired[self_id] = retirement
            del self.sessions[self_id]
            return proof
        except BaseException:
            if self.lifecycle.view(self_id).status is not Presence.QUARANTINED:
                self.lifecycle.fail_self(self_id)
            raise

    def world_only_quiescence(self) -> WorldOnlyQuiescenceEvidence:
        """Only a scoped NO-COMPUTE/NO-PEER qualification, not arbitrary L1/L2."""
        if (
            self.sessions or self._pending_login or not self.physical.all_residents_offline
            or not self.lifecycle.can_world_only_checkpoint()
        ):
            raise OwnedResidentBridgeError(
                "World-only requires all original Self issue sessions retired"
            )
        for sid in self.lifecycle.self_roster:
            self.work.require_clean(sid)
            if self.lifecycle.view(sid).status is not Presence.OFFLINE:
                raise OwnedResidentBridgeError("Self presence not really retired")
            owner = self.owners[sid]
            if owner.supervisor.open_actions:
                raise OwnedResidentBridgeError("original Action supervisor not drained")
            PhysicalActionJournal.restore(
                owner.files.physical_wal_file, self_id=sid,
            ).require_clear()
            if self.lifecycle.view(sid).persisted_cognition_ref != (
                f"cognition-file:{owner.files.cognition_file}"
            ):
                # Initial boot may be offline but did not pass real owner
                # retirement; do not claim source verified for those actors.
                raise OwnedResidentBridgeError(
                    "Self has not completed original issuer native retirement"
                )
            if sid not in self.retired:
                raise OwnedResidentBridgeError("no original owner retirement receipt")
        return WorldOnlyQuiescenceEvidence(
            world_epoch=self.lifecycle.world.epoch,
            checked_self_ids=self.lifecycle.self_roster,
            source_ref="owned-inert-physical:" + str(self.lifecycle.world.epoch),
            original_physical_issuer_closed=True,
            native_sessions_absent=True,
            no_unresolved_physical_actions=True,
            all_gpu_epochs_retired=True,
            pending_peer_messages_empty=True,
        )
