"""#860 DEV: real original physical issuer + owned per-Self native lifecycle.

Scope is deliberately NO GPU/LLM work and NO peer transport. The exact
Mineflayer child is owned by the original process adapter; user code must
not bypass its final physical admission hook. No dynamic cognition/LLM task
scheduler or model backend is attested by the inert boundary.
"""
from __future__ import annotations

from collections.abc import Awaitable, Callable

from adapters.mineflayer.process_session import MineflayerProcessSession
from adapters.mineflayer.python_protocol import MineflayerLaunchConfig, MineflayerObservation
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
from relay_self.resident_cognitive_work_owner_dev import (
    ResidentCognitiveWorkOwner,
)
from relay_self.resident_llama_inference_lane_dev import (
    ResidentLlamaInferenceLane,
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
        cognitive_work: ResidentCognitiveWorkOwner | None = None,
        inference_lane: ResidentLlamaInferenceLane | None = None,
        forbidden_native_sessions: frozenset[str] = frozenset(),
        adopt_login_worldbody_dev: bool = False,
    ) -> None:
        if (
            type(adopt_login_worldbody_dev) is not bool
            or (adopt_login_worldbody_dev and cognitive_work is None)
            or not isinstance(lifecycle, WorldResidentLifecycle)
            or not isinstance(physical, PhysicalIssueAdmission)
            or not physical.resident_mode
            or (
                inference_lane is not None
                and (
                    not isinstance(inference_lane, ResidentLlamaInferenceLane)
                    or cognitive_work is None
                    or inference_lane.cognitive_work is not cognitive_work
                )
            )
            or (
                cognitive_work is not None
                and (
                    not isinstance(cognitive_work, ResidentCognitiveWorkOwner)
                    or set(cognitive_work.owners) != set(owners)
                    or any(
                        cognitive_work.owners[sid] is not owner
                        for sid, owner in owners.items()
                    )
                )
            )
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
                or o.self_id != sid
                or o.cohort not in (None, cognitive_work)
                or o.native_session_id != physical.current_native_sessions[sid]
                or o.supervisor.open_actions
                for sid, o in owners.items()
            )
            or type(forbidden_native_sessions) is not frozenset
            or any(type(sid) is not str or not sid
                   for sid in forbidden_native_sessions)
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
        self.cognitive_work = cognitive_work
        self.adopt_login_worldbody_dev = adopt_login_worldbody_dev
        self.inference_lane = inference_lane
        # A restored Self may have joined/quit more than once in the old
        # boot. All historical native IDs, not just last_owner_session,
        # must be refused BEFORE rebind/admission.
        self.forbidden_native_sessions = forbidden_native_sessions
        self.sessions: dict[str, MineflayerProcessSession] = {}
        self.retired: dict[str, ResidentIssuerRetired] = {}
        # DEV-only owner-retained logout witness for post-reJOIN Paper correlation.
        self._b_np1b_retired_login: dict[str, tuple[
            LogoutFenceEvidence, tuple[int, str, int], CheckpointedCognitiveOwner,
            NativeLoginEvidence, MineflayerObservation,
        ]] = {}
        # Preserve the ORIGINAL verified native/Paper source claim so an
        # independent Paper log join can use it without inventing evidence.
        self.last_login_evidence: dict[str, NativeLoginEvidence] = {}
        self.last_login_observations: dict[str, MineflayerObservation] = {}
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
                or launched.started.session_id in self.forbidden_native_sessions
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
            # Only this actual adapter-owned child can submit the final effect
            # bytes. Synthetic injected Native fixtures keep their existing
            # observable gate; no extra issuer or sender is introduced.
            if isinstance(launched, MineflayerProcessSession):
                def submit_effect(
                    native_id: str, effect_kind: str, action_id: str,
                    write: Callable[[], None],
                ) -> None:
                    self.physical.submit_native_effect(
                        self_id=self_id, native_session_id=native_id,
                        effect=effect_kind, action_id=action_id, write=write,
                    )

                launched.install_atomic_effect_sender(submit_effect)
            observations: list[MineflayerObservation] = []
            _, _, request_id, observed_tick = await verify_native_spawn_probe(
                launched, timeout_s=self.probe_timeout_s, probe_sink=observations.append,
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
            if len(observations) != 1:
                raise OwnedResidentBridgeError("original native probe body unavailable")
            if self.cognitive_work is not None:
                with self.cognitive_work.lock:
                    self.cognitive_work.bind_login(
                        self_id=self_id,
                        native_session_id=launched.started.session_id,
                        world_epoch=ticket.world.epoch, world_tick=observed_tick,
                    )
                    scope = self.cognitive_work.current_scope(self_id)
                    self.sessions[self_id] = launched
                    self.last_login_evidence[self_id] = evidence
                    self.last_login_observations[self_id] = observations[0]
                    if self.adopt_login_worldbody_dev:
                        self._adopt_login_worldbody_dev(self_id, scope)
                if self.inference_lane is not None:
                    self.inference_lane.bind_login(self_id)
            else:
                owner.native_session_id = launched.started.session_id
                owner.last_observed_tick = observed_tick
                owner.fresh_native_observation_required = False
                self.sessions[self_id] = launched
                self.last_login_evidence[self_id] = evidence
                self.last_login_observations[self_id] = observations[0]
            self.retired.pop(self_id, None)
            return ticket
        except BaseException:
            if self.adopt_login_worldbody_dev and self.cognitive_work is not None:
                with self.cognitive_work.lock:
                    self.owners[self_id].current_worldbody_observation = None
            self.last_login_evidence.pop(self_id, None)
            self.last_login_observations.pop(self_id, None)
            # If source verification fails, NEVER grant a new issuer lease.
            # If admit succeeded before an unexpected failure, quarantine it.
            current = self.physical.current_native_sessions[self_id]
            if launched is not None and current == launched.started.session_id:
                self.physical.quarantine_resident(
                    self_id=self_id, native_session_id=current,
                )
                if self.cognitive_work is not None:
                    try:
                        self.cognitive_work.fence_self(self_id)
                    except Exception:
                        pass  # still HOLD; failed cognition admission cannot become ONLINE
                if self.inference_lane is not None:
                    self.inference_lane.fence_self(self_id)
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

    def _adopt_login_worldbody_dev(self, self_id: str, scope: tuple[int, str, int]) -> None:
        """Adopt the correlated login probe within the original resident epoch."""
        resident = self.cognitive_work
        if resident is None:
            raise OwnedResidentBridgeError("resident required")
        with resident.lock:
            owner = self.owners[self_id]
            probe = self.last_login_observations.get(self_id)
            evidence = self.last_login_evidence.get(self_id)
            session = self.sessions.get(self_id)
            world = self.lifecycle.world
            if (
                not self.adopt_login_worldbody_dev
                or self.lifecycle.view(self_id).status is not Presence.ONLINE
                or resident.current_scope(self_id) != scope
                or scope[2] != world.epoch or owner.cohort is not resident
                or session is None or session.process_returncode is not None
                or evidence is None or probe is None
                or evidence.self_id != self_id or evidence.world_epoch != world.epoch
                or evidence.world_id != world.world_id or evidence.branch_id != world.branch_id
                or evidence.paper_session_id != world.paper_session_id
                or session.started.session_id != scope[1]
                or self.physical.current_native_sessions[self_id] != scope[1]
                or evidence.native_session_id != scope[1] or owner.native_session_id != scope[1]
                or probe.session_id != scope[1] or probe.kind != "probe"
                or not evidence.observation_ref or probe.request_id != evidence.observation_ref
                or probe.snapshot.time is None
                or probe.snapshot.time.day * 24000 + probe.snapshot.time.time_of_day
                != evidence.observed_world_tick
                or evidence.observed_world_tick != owner.last_observed_tick
            ):
                raise OwnedResidentBridgeError("stale or foreign login WorldBody")
            self._check_world()
            owner.accept_rejoined_worldbody(probe, request_id=evidence.observation_ref)

    def attach_observation_only_bounded_l1(
        self, lane: ResidentLlamaInferenceLane,
    ) -> None:
        """Stage28c2c: attach one owned model lane AFTER fresh A/B Body proof.

        This never issues an Action. The same bridge must own the lane so its
        existing logout fences/waits for backend completion and slot readback.
        No hot replacement or attachment while native work is uncertain.
        """
        self._check_world()
        if (
            self.inference_lane is not None
            or not isinstance(lane, ResidentLlamaInferenceLane)
            or self.cognitive_work is None
            or lane.cognitive_work is not self.cognitive_work
            or lane.uncertain
            or not self.physical.observation_only
            or self.physical.active_action_ids
            or tuple(sorted(self.sessions)) != self.lifecycle.self_roster
            or tuple(sorted(self.last_login_observations))
            != self.lifecycle.self_roster
            or any(
                self.lifecycle.view(sid).status is not Presence.ONLINE
                or self.sessions[sid].process_returncode is not None
                or self.owners[sid].current_worldbody_observation
                is not self.last_login_observations[sid]
                or self.owners[sid].fresh_native_observation_required
                or self.owners[sid].supervisor.open_actions
                for sid in self.lifecycle.self_roster
            )
        ):
            raise OwnedResidentBridgeError(
                "only one fresh original A/B observer may adopt bounded GPU lane"
            )
        # Existing llama owner checks /slots n_parallel=1 idle. An external
        # inference client can race this probe; exclusive loopback ownership
        # remains a hard operator/runner prerequisite, not inferred here.
        lane.witness.require_idle()
        try:
            for sid in self.lifecycle.self_roster:
                lane.bind_login(sid)
        except BaseException:
            for sid in self.lifecycle.self_roster:
                lane.fence_self(sid)
            raise
        self.inference_lane = lane

    def quarantine(self, self_id: str) -> None:
        """Synchronous, per-Self immediate issue block before any async wait."""
        if self_id not in self.sessions:
            raise OwnedResidentBridgeError("no currently owned Self session")
        current = self.sessions[self_id].started.session_id
        self.physical.quarantine_resident(
            self_id=self_id, native_session_id=current,
        )
        if self.cognitive_work is not None:
            self.cognitive_work.fence_self(self_id)
        if self.inference_lane is not None:
            self.inference_lane.fence_self(self_id)
        self.lifecycle.fail_self(self_id)

    async def abort_place_after_start_dev(
        self, *, self_id: str, stop_action_id: str,
    ):
        """Q4 host-owned kill switch; independent of a canceled PLACE lease.

        The existing original physical issuer is revoked before first await,
        then the owned Native bot is disconnected if STOP/ACK is uncertain.
        Neither this method nor disconnection resolves a PREPARED WAL.
        """
        from relay_self.q4_place_abort_dev import abort_original_place_after_start

        return await abort_original_place_after_start(
            bridge=self, self_id=self_id, stop_action_id=stop_action_id,
        )

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
        # Original cognition writes must lose Self admission BEFORE the
        # first async await. A late CPU job cannot rewrite a frozen Self.
        retired_scope = None
        retired_native = None
        if self.cognitive_work is not None:
            with self.cognitive_work.lock:
                self._b_np1b_retired_login.pop(self_id, None)
                if self.adopt_login_worldbody_dev and view.status is Presence.ONLINE:
                    retired_scope = self.cognitive_work.current_scope(self_id)
                    prior_login = self.last_login_evidence.get(self_id)
                    prior_probe = self.last_login_observations.get(self_id)
                    if (prior_login is not None and prior_probe is not None
                            and prior_login.native_session_id == retired_scope[1]
                            and prior_probe.session_id == retired_scope[1]
                            and prior_probe.kind == "probe"
                            and prior_probe.request_id == prior_login.observation_ref):
                        retired_native = (prior_login, prior_probe)
                self.cognitive_work.fence_self(self_id)
                # Historical receipts remain immutable; only current admission is cleared.
                for name in ('_fresh_native_initial', '_fresh_native_current',
                             '_fresh_native_pending'):
                    getattr(self, name, {}).pop(self_id, None)
                self.last_login_evidence.pop(self_id, None)
                self.last_login_observations.pop(self_id, None)
        self.forbidden_native_sessions = self.forbidden_native_sessions | {native_id}
        if self.inference_lane is not None:
            self.inference_lane.fence_self(self_id)
        try:
            if view.status is Presence.ONLINE:
                self.lifecycle.begin_logout(self_id)
            self.work.require_clean(self_id)
            cognitive_retired = None
            if self.cognitive_work is not None:
                cognitive_retired = await self.cognitive_work.retire_self(self_id)
            if self.inference_lane is not None:
                await self.inference_lane.retire_self(self_id)
            owner = self.owners[self_id]
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
            if self.cognitive_work is not None:
                assert cognitive_retired is not None
                self.cognitive_work.mark_offline(cognitive_retired)
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
            if retired_scope is not None and retired_native is not None:
                assert self.cognitive_work is not None
                with self.cognitive_work.lock:
                    self._b_np1b_retired_login[self_id] = (
                        proof, retired_scope, owner, *retired_native,
                    )
            self.retired[self_id] = retirement
            del self.sessions[self_id]
            return proof
        except BaseException:
            if self.lifecycle.view(self_id).status is not Presence.QUARANTINED:
                self.lifecycle.fail_self(self_id)
            raise

    def bind_normal_rejoin_present_cpu(
        self, *, initial_receipts, historical_composite,
    ) -> None:
        """Bind the existing original Owner's history after full current qualification."""
        if self.cognitive_work is None:
            raise OwnedResidentBridgeError("original cognitive resident not attached")
        self.cognitive_work.bind_normal_rejoin_source_cpu(
            bridge=self, initial_receipts=initial_receipts,
            historical_composite=historical_composite,
        )

    def poll_normal_present_cpu(self):
        """Explicit read-only A/B CPU caller. No periodic scheduler is installed."""
        if self.cognitive_work is None:
            raise OwnedResidentBridgeError("original cognitive resident not attached")
        return self.cognitive_work.poll_normal_present_cpu(bridge=self)

    def start_normal_present_cpu_schedule(self, *, interval_s: float = 0.05):
        """Start periodic A/B Present using the original Resident CPU tasks.

        Bound source history, current Paper and both original Native sessions
        are prerequisites. No GPU, Action or persistent cognition mutation.
        """
        from relay_self.b_np1b_normal_present_scheduler_dev import (
            start_normal_resident_present_cpu,
        )

        return start_normal_resident_present_cpu(
            bridge=self, interval_s=interval_s,
        )

    def require_scheduled_present_cpu(self, self_id: str):
        """Read a scheduler result ONLY after a fresh original-source recheck."""
        from relay_self.b_np1b_normal_present_scheduler_dev import NormalCpuScheduleHold

        resident = self.cognitive_work
        if resident is None:
            raise NormalCpuScheduleHold("original cognitive resident missing")
        scheduler = getattr(resident, "_normal_present_scheduler", None)
        if scheduler is None or scheduler.bridge is not self:
            raise NormalCpuScheduleHold("original CPU schedule not installed")
        return scheduler.require_current(self_id)

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
            if (
                self.cognitive_work is not None
                and not self.cognitive_work.retired_clean(sid)
            ):
                raise OwnedResidentBridgeError(
                    "unretired original resident cognitive writers"
                )
            if (
                self.inference_lane is not None
                and not self.inference_lane.retired_clean(sid)
            ):
                raise OwnedResidentBridgeError(
                    "unretired actual shared inference slot work"
                )
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
        if self.inference_lane is not None:
            self.inference_lane.require_world_idle()
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
