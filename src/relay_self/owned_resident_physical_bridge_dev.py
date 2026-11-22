"""#860 DEV: real original physical issuer + owned per-Self native lifecycle.

Scope is deliberately NO GPU/LLM work and NO peer transport. The exact
Mineflayer child is owned by the original process adapter; user code must
not bypass its final physical admission hook. No dynamic cognition/LLM task
scheduler or model backend is attested by the inert boundary.
"""
from __future__ import annotations

import re
import time
import uuid
from collections.abc import Awaitable, Callable

from adapters.mineflayer.process_session import MineflayerProcessSession
from adapters.mineflayer.python_protocol import MineflayerLaunchConfig, MineflayerObservation
from adapters.mineflayer.sense_projection import (
    SenseFrame,
    SenseRefusal,
    sense_for_self_world,
    sense_from_native,
)
from relay_self.checkpointed_cognitive_runtime_dev import CheckpointedCognitiveOwner
from relay_self.common_io import ScopeRef
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
    ResidentCognitiveWorkError,
    ResidentCognitiveWorkOwner,
)
from relay_self.resident_llama_inference_lane_dev import (
    ResidentLlamaInferenceLane,
)
from relay_self.three_self_present import project_three_self
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
        enable_sense: bool = False,
    ) -> None:
        if (
            not isinstance(lifecycle, WorldResidentLifecycle)
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
            or type(enable_sense) is not bool
            or (enable_sense and cognitive_work is None)
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
        self.inference_lane = inference_lane
        self.enable_sense = enable_sense
        # Passive SENSE is ephemeral; original native/Paper sources remain authoritative.
        self._sense: dict[str, SenseFrame] = {}
        self._sense_received_at: dict[str, float] = {}
        self._sense_refreshing: set[str] = set()
        # Exactly matched I1 observe replies; separate from the normal
        # passive Native SENSE stream. Both live under the same original
        # resident lock and Native process, not a second owner.
        self._i1_correlated_sense: dict[str, SenseFrame] = {}
        self._i1_correlated_received_at: dict[str, float] = {}
        # A restored Self may have joined/quit more than once in the old
        # boot. All historical native IDs, not just last_owner_session,
        # must be refused BEFORE rebind/admission.
        self.forbidden_native_sessions = forbidden_native_sessions
        self.sessions: dict[str, MineflayerProcessSession] = {}
        self.retired: dict[str, ResidentIssuerRetired] = {}
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
            if self.cognitive_work is not None:
                self.cognitive_work.bind_login(
                    self_id=self_id,
                    native_session_id=launched.started.session_id,
                    world_epoch=ticket.world.epoch, world_tick=observed_tick,
                )
                if self.inference_lane is not None:
                    self.inference_lane.bind_login(self_id)
            else:
                owner.native_session_id = launched.started.session_id
                owner.last_observed_tick = observed_tick
                owner.fresh_native_observation_required = False
            self.sessions[self_id] = launched
            self.last_login_evidence[self_id] = evidence
            if len(observations) != 1:
                raise OwnedResidentBridgeError("original native probe body unavailable")
            self.last_login_observations[self_id] = observations[0]
            self.retired.pop(self_id, None)
            if self.enable_sense:
                self._start_sense(self_id, launched, ticket)
            return ticket
        except BaseException:
            self._sense.pop(self_id, None)
            self._sense_received_at.pop(self_id, None)
            self._i1_correlated_sense.pop(self_id, None)
            self._i1_correlated_received_at.pop(self_id, None)
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

    def _start_sense(self, self_id: str, session: MineflayerProcessSession, ticket: LoginTicket) -> None:
        """Subscribe to the existing original native receive/decoder after login."""
        if self.cognitive_work is None:
            raise OwnedResidentBridgeError("SENSE requires original resident lock")
        scope = ScopeRef(self_id, ticket.world.paper_session_id)
        evidence = self.last_login_evidence[self_id]
        probe = self.last_login_observations[self_id]
        if (probe.kind != "probe" or probe.request_id != evidence.observation_ref
                or probe.session_id != session.started.session_id or probe.seq < 1
                or not self._sense_current(self_id, session, ticket)):
            raise OwnedResidentBridgeError("verified original seed probe required for SENSE")
        # Same original probe, NOT a second observation or an added Paper fact.
        seed = sense_from_native(
            probe, scope=scope, expected_native_session=session.started.session_id,
            expected_request_id=evidence.observation_ref, previous_seq=probe.seq - 1,
        )
        previous_seq = probe.seq
        self._sense[self_id] = seed
        self._sense_received_at[self_id] = time.monotonic()

        def observe(message: object) -> None:
            nonlocal previous_seq
            if not isinstance(message, MineflayerObservation) or message.kind == "probe":
                return
            # Same original lock as B Present projection. No extra perception owner.
            with self.cognitive_work.lock:
                if not self._sense_current(self_id, session, ticket):
                    self._sense.pop(self_id, None)
                    self._sense_received_at.pop(self_id, None)
                    return
                try:
                    frame = sense_from_native(
                        message, scope=scope, expected_native_session=session.started.session_id,
                        previous_seq=previous_seq,
                    )
                except SenseRefusal:
                    return
                previous_seq = message.seq
                self._sense[self_id] = frame
                self._sense_received_at[self_id] = session._observer_received_monotonic

        session.start_dispatcher(
            observe,
            compact_safe=lambda: (
                not self.physical.closed and not self.physical.active_action_ids
            ),
        )

    def _sense_current(self, self_id: str, session: MineflayerProcessSession, ticket: LoginTicket) -> bool:
        try:
            _, native, epoch = self.cognitive_work.current_scope(self_id)
        except ResidentCognitiveWorkError:
            return False
        view = self.lifecycle.view(self_id)
        return (
            native == session.started.session_id
            and epoch == ticket.world.epoch
            and self.sessions.get(self_id) is session
            and session.process_returncode is None
            and (self.lifecycle.world.world_id, self.lifecycle.world.branch_id,
                 self.lifecycle.world.paper_session_id, self.lifecycle.world.epoch)
            == (ticket.world.world_id, ticket.world.branch_id,
                ticket.world.paper_session_id, ticket.world.epoch)
            and view.status is Presence.ONLINE
            and view.native_session_id == session.started.session_id
            and self.owners[self_id].native_session_id == session.started.session_id
            and not self.owners[self_id].fresh_native_observation_required
            and self.physical.current_native_sessions[self_id] == session.started.session_id
            and self.paper.owned_session_id == ticket.world.paper_session_id
            and self.paper.world_id == ticket.world.world_id
            and self.paper.branch_id == ticket.world.branch_id
            and not self.paper.held_uncertain
        )

    def current_sense(self, self_id: str, *, max_age_s: float = 2.0) -> SenseFrame | None:
        """Read only a current passive frame; no Action or Paper qualification."""
        if self.cognitive_work is None or not getattr(self, "enable_sense", False):
            return None
        with self.cognitive_work.lock:
            try:
                _, resident_native, resident_world_epoch = (
                    self.cognitive_work.current_scope(self_id)
                )
            except ResidentCognitiveWorkError:
                self._sense.pop(self_id, None)
                self._sense_received_at.pop(self_id, None)
                return None
            frame = self._sense.get(self_id)
            session = self.sessions.get(self_id)
            evidence = self.last_login_evidence.get(self_id)
            received_at = self._sense_received_at.get(self_id, 0)
            if (frame is None or session is None or evidence is None
                    or not 0 < max_age_s <= 60
                    or not 0 <= time.monotonic() - received_at <= max_age_s):
                return None
            world = self.lifecycle.world
            view = self.lifecycle.view(self_id)
            if (resident_native != session.started.session_id
                    or resident_world_epoch != world.epoch
                    or view.status is not Presence.ONLINE
                    or session.process_returncode is not None
                    or session.observer_error is not None or session._dispatch_error is not None
                    or frame.scope != ScopeRef(self_id, world.paper_session_id)
                    or evidence.self_id != self_id
                    or evidence.native_session_id != session.started.session_id
                    or frame.observation.session_id != session.started.session_id
                    or frame.source_revision_ref != (f"mineflayer:{session.started.session_id}:"
                                                     f"{frame.observation.seq}")
                    or view.native_session_id != session.started.session_id
                    or self.owners[self_id].native_session_id != session.started.session_id
                    or self.owners[self_id].fresh_native_observation_required
                    or self.physical.current_native_sessions[self_id] != session.started.session_id
                    or (world.world_id, world.branch_id, world.paper_session_id, world.epoch)
                    != (evidence.world_id, evidence.branch_id,
                        evidence.paper_session_id, evidence.world_epoch)
                    or self.paper.owned_session_id != world.paper_session_id
                    or self.paper.world_id != world.world_id
                    or self.paper.branch_id != world.branch_id
                    or self.paper.held_uncertain):
                self._sense.pop(self_id, None)
                self._sense_received_at.pop(self_id, None)
                return None
            return frame

    def current_i1_correlated_sense(
        self, self_id: str, *, max_age_s: float = 2.0,
    ) -> SenseFrame | None:
        """Read the last exact matched observe reply from this original bridge.

        Passive move/entities may have higher Native seq and no request ID:
        they continue to update current_sense(), but must never replace the
        explicitly correlated I1 CPU snapshot. This I1-only projection is
        bounded by normal original Native/Paper/Owner currentness and TTL.
        """
        if self.cognitive_work is None or not self.enable_sense:
            return None
        with self.cognitive_work.lock:
            # Real original resident/Native/Paper fences are still mandatory.
            passive = self.current_sense(self_id, max_age_s=max_age_s)
            correlated = self._i1_correlated_sense.get(self_id)
            received = self._i1_correlated_received_at.get(self_id, 0)
            if (passive is None or correlated is None
                    or not 0 < max_age_s <= 60
                    or not 0 <= time.monotonic() - received <= max_age_s
                    or correlated.scope != passive.scope
                    or correlated.observation.session_id != passive.observation.session_id
                    or correlated.observation.seq > passive.observation.seq
                    or correlated.observation.kind != "probe"
                    or type(correlated.observation.request_id) is not str
                    or re.fullmatch(
                        r"i1-original-sense-[0-9a-f]{32}",
                        correlated.observation.request_id,
                    ) is None
                    or correlated.source_revision_ref != (
                        f"mineflayer:{correlated.observation.session_id}:"
                        f"{correlated.observation.seq}"
                    )):
                return None
            return correlated

    async def refresh_i1_read_only_sense(
        self, self_id: str, *, timeout_s: float = 2.0,
    ) -> SenseFrame:
        """Original single Native reader: request a fresh read-only Body probe.

        No second native subprocess, Physical Action, GPU task or Memory owner.
        The correlated result must be consumed through the original session
        and admitted under the resident lock after fresh owner/source checks.
        """
        from relay_self.checkpoint_stop_neutralization_dev import _receive_matched

        if (self.cognitive_work is None
                or not self.enable_sense
                or not self.physical.observation_only
                or self.physical.active_action_ids
                or type(timeout_s) not in (float, int)
                or not 0 < timeout_s <= 5):
            raise OwnedResidentBridgeError("I1 requires original observation-only native")
        with self.cognitive_work.lock:
            session = self.sessions.get(self_id)
            evidence = self.last_login_evidence.get(self_id)
            if (session is None or evidence is None
                    or self_id in self._sense_refreshing
                    or session.process_returncode is not None
                    or self.cognitive_work.current_scope(self_id)[1:]
                    != (evidence.native_session_id, evidence.world_epoch)
                    or self.physical.current_native_sessions[self_id]
                    != evidence.native_session_id
                    or session.started.session_id != evidence.native_session_id
                    or self.lifecycle.view(self_id).status is not Presence.ONLINE
                    or self.paper.held_uncertain
                    or self.lifecycle.world.paper_session_id
                    != evidence.paper_session_id):
                raise OwnedResidentBridgeError("I1 stale/foreign/parallel native observer")
            self._check_world()
            self._sense_refreshing.add(self_id)
        request_id = "i1-original-sense-" + uuid.uuid4().hex
        try:
            await session.send_observe(request_id)
            observation = await _receive_matched(
                session, session_id=evidence.native_session_id,
                kind="probe", identity=request_id, timeout_s=timeout_s,
            )
            with self.cognitive_work.lock:
                if (self.sessions.get(self_id) is not session
                        or self.cognitive_work.current_scope(self_id)[1:]
                        != (evidence.native_session_id, evidence.world_epoch)
                        or self.lifecycle.view(self_id).status is not Presence.ONLINE
                        or self.physical.current_native_sessions[self_id]
                        != evidence.native_session_id
                        or self.paper.held_uncertain
                        or self.lifecycle.world.paper_session_id
                        != evidence.paper_session_id):
                    raise OwnedResidentBridgeError("I1 source changed during observe")
                self._check_world()
                previous = self._sense.get(self_id)
                previous_seq = (
                    previous.observation.seq if previous is not None
                    else self.last_login_observations[self_id].seq
                )
                frame = sense_from_native(
                    observation,
                    scope=ScopeRef(self_id, evidence.paper_session_id),
                    expected_native_session=evidence.native_session_id,
                    previous_seq=previous_seq, expected_request_id=request_id,
                )
                self._sense[self_id] = frame
                now = time.monotonic()
                self._sense_received_at[self_id] = now
                self._i1_correlated_sense[self_id] = frame
                self._i1_correlated_received_at[self_id] = now
                return frame
        finally:
            with self.cognitive_work.lock:
                self._sense_refreshing.discard(self_id)

    def current_self_world(self, self_id: str):
        """Transient source-bound E SelfWorld view; not a separate store."""
        frame = self.current_sense(self_id)
        if frame is None:
            return None
        world = self.lifecycle.world
        return project_three_self(
            retained=self.owners[self_id].retained, scope=frame.scope,
            epoch_ref=f"{world.world_id}:{world.branch_id}:{world.paper_session_id}:{world.epoch}",
            source_revision_refs=(frame.source_revision_ref,),
            claims=sense_for_self_world(frame),
        ).self_world

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
        self._sense.pop(self_id, None)
        self._sense_received_at.pop(self_id, None)
        self._i1_correlated_sense.pop(self_id, None)
        self._i1_correlated_received_at.pop(self_id, None)
        current = self.sessions[self_id].started.session_id
        self.physical.quarantine_resident(
            self_id=self_id, native_session_id=current,
        )
        if self.cognitive_work is not None:
            self.cognitive_work.fence_self(self_id)
        if self.inference_lane is not None:
            self.inference_lane.fence_self(self_id)
        self.lifecycle.fail_self(self_id)

    async def logout(self, self_id: str) -> LogoutFenceEvidence:
        """Independent physical, journal, native process and cognition checks."""
        self._check_world()
        session = self.sessions.get(self_id)
        if session is None:
            raise OwnedResidentBridgeError("logout without owned native session")
        self._sense.pop(self_id, None)
        self._sense_received_at.pop(self_id, None)
        self._i1_correlated_sense.pop(self_id, None)
        self._i1_correlated_received_at.pop(self_id, None)
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
        if self.cognitive_work is not None:
            self.cognitive_work.fence_self(self_id)
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
            self.sessions or self._pending_login or getattr(self, "_sense_refreshing", None)
            or not self.physical.all_residents_offline
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
