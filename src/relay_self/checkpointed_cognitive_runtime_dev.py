"""#860 P0-D DEV: directly snapshot the existing mutable cognition owners.

This is a concrete boundary for the currently implemented owners, NOT an
authoritative mineflayer/Paper connector or physical Action issuer. The external
physical admission fence, real native rejoin and GPU cancellation remain separate
operator/adapter contracts and MUST be independently attested for real World.
"""
from __future__ import annotations

import hashlib
import re
import threading
from dataclasses import dataclass, replace
from pathlib import Path
from typing import Callable

from relay_self.action_supervision import ActionSupervisor
from relay_self.cognitive_minimal_dev import PatternRegistry, SchemaPattern, accept_learned_pattern
from relay_self.coordinated_autosave_runtime_dev import (
    AdmissionCloseReceipt,
    AdmissionHooks,
    ReboundSelfReceipt,
    SelfFrozenReceipt,
    SelfRuntimeHooks,
)
from relay_self.coordinated_checkpoint_dev import SelfSnapshotSource
from relay_self.intent import IntentCommitment
from relay_self.persistent_cognition import (
    Memory,
    PersistentCognition,
    load_persistent_cognition,
    save_persistent_cognition,
)
from relay_self.physical_action_journal import PhysicalActionJournal
from relay_self.provenance import Provenance
from relay_self.self_owner_checkpoint_dev import (
    PeerDelivery,
    RehydratedSelfOwner,
    SelfOwnerCut,
    prepare_typed_owner_restore,
    save_self_owner_cut,
)
from relay_self.skill import SkillExecution


class LiveCognitionCheckpointError(RuntimeError):
    """Owner mutation, freeze, or fresh-WorldBody handoff is not qualified."""


@dataclass(frozen=True, slots=True)
class ExternalPhysicalFence:
    """Input from the EXISTING physical issue owner, not a new grant."""

    fence_ref: str
    physically_blocked: bool
    physical_inflight_action_ids: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class ExternalRejoin:
    """Source-qualified native/cognition/GPU/transport adapter receipt."""

    new_native_session_id: str
    old_native_session_invalidated: bool
    obsolete_gpu_tasks_fenced: bool
    stale_messages_discarded: bool


@dataclass(frozen=True, slots=True)
class CognitiveOwnerFiles:
    """Existing Self-owned persistence, plus per-generation immutable cuts."""

    self_root: Path
    cognition_file: Path
    physical_wal_file: Path


@dataclass(frozen=True, slots=True)
class StagedRecoveredCognition:
    """Restored owner objects with old authorities explicitly absent."""

    self_id: str
    retained: PersistentCognition
    semantic: RehydratedSelfOwner
    physical_wal_path: Path
    fresh_worldbody_required: bool = True
    native_session_bound: bool = False
    issue_authorized: bool = False
    conversation_redelivery_authorized: bool = False


class CognitionOwnerCohort:
    """Single coarse mutation gate for the *participating* Self owners only.

    This gates all mutations through this facade and performs real WAL and
    ActionSupervisor checks. Existing action/native paths are NOT automatically
    fenced by this gate; the external physical adapter must fence their issuer.
    """

    def __init__(
        self, *, owners: tuple["CheckpointedCognitiveOwner", ...],
        world_id: str, branch_id: str,
        external_close_physical: Callable[[], ExternalPhysicalFence],
        external_release_physical: Callable[[str], None],
        external_native_rejoin: Callable[[str, str, str], ExternalRejoin],
    ) -> None:
        if not owners or len({o.self_id for o in owners}) != len(owners):
            raise LiveCognitionCheckpointError("full unique Self roster required")
        if any(o.cohort is not None for o in owners):
            raise LiveCognitionCheckpointError("Self is already attached to a cohort")
        # Parallel durable writes must never alias another enrolled Self's
        # canonical owner subtree, even if Self IDs are distinct.
        roots = {o.files.self_root.resolve() for o in owners}
        if (
            len(roots) != len(owners)
            or any(
                parent in roots
                for root in roots
                for parent in root.parents
            )
            or any(o.files.self_root.is_symlink() for o in owners)
        ):
            raise LiveCognitionCheckpointError(
                "parallel Self owner roots overlap or are symlinked"
            )
        if not world_id or not branch_id:
            raise LiveCognitionCheckpointError("World identity required")
        self.lock = threading.RLock()
        self.owners = tuple(sorted(owners, key=lambda o: o.self_id))
        self._owners_by_id = {owner.self_id: owner for owner in self.owners}
        self.world_id = world_id
        self.branch_id = branch_id
        self.external_close_physical = external_close_physical
        self.external_release_physical = external_release_physical
        self.external_native_rejoin = external_native_rejoin
        self.closed = False
        self.hold = False
        self.fence: ExternalPhysicalFence | None = None
        self._freeze_active: set[str] = set()
        self._freeze_completed: set[str] = set()
        self._freeze_generation: str | None = None
        self._freeze_failed = False
        self.token = 0
        for owner in self.owners:
            owner.cohort = self

    def _mutating(self, self_id: str | None = None) -> None:
        # Existing global cohort ignores optional Self scope; the alternative
        # resident gate requires the Self ID for per-actor write admission.
        if self.hold or self.closed:
            raise LiveCognitionCheckpointError("cognitive epoch fenced by checkpoint")

    def _owner(self, self_id: str) -> "CheckpointedCognitiveOwner":
        try:
            return self._owners_by_id[self_id]
        except (KeyError, TypeError) as exc:
            raise LiveCognitionCheckpointError(
                "unregistered Self identity"
            ) from exc

    def admission_hooks(self) -> AdmissionHooks:
        return AdmissionHooks(self.close, self.release)

    def participant_hooks(self) -> tuple[SelfRuntimeHooks, ...]:
        return tuple(SelfRuntimeHooks(
            o.self_id,
            lambda generation, owner=o: self.freeze(owner.self_id, generation),
            lambda server_session, owner=o: self.rebind(owner.self_id, server_session),
        ) for o in self.owners)

    def close(self) -> AdmissionCloseReceipt:
        with self.lock:
            if self.closed or self.hold:
                raise LiveCognitionCheckpointError("cohort already closed/held")
            # Close in-memory cognition/peer admission BEFORE external fence.
            self.closed = True
            self.hold = True
            self._freeze_active.clear()
            self._freeze_completed.clear()
            self._freeze_generation = None
            self._freeze_failed = False
            receipt = self.external_close_physical()
            if (not isinstance(receipt, ExternalPhysicalFence)
                    or not receipt.physically_blocked
                    or receipt.physical_inflight_action_ids
                    or not receipt.fence_ref):
                raise LiveCognitionCheckpointError("external physical issuer not quiesced")
            self.fence = receipt
            self.token += 1
            return AdmissionCloseReceipt(
                f"cognition-gate-{self.token}", True, True, True,
            )

    def freeze(self, self_id: str, generation_id: str) -> SelfFrozenReceipt:
        """Snapshot each disjoint owner under the already-closed N-Self epoch.

        The coarse lock protects the *immutable cut* and WAL check. Durable
        per-Self fsyncs then run outside that lock, so a bounded thread pool
        can actually overlap independent owner files without allowing any
        normal cognition mutation. Rebind/release reject active or failed
        freezes; the complete generation is still one global COMMIT.
        """
        with self.lock:
            if not (self.closed and self.hold and self.fence is not None):
                raise LiveCognitionCheckpointError("freeze requires external physical fence")
            if re.fullmatch(r"g-[0-9]{12}", generation_id) is None:
                raise LiveCognitionCheckpointError("invalid generation")
            if (
                self._freeze_failed
                or self_id in self._freeze_active
                or self_id in self._freeze_completed
                or (
                    self._freeze_generation is not None
                    and self._freeze_generation != generation_id
                )
            ):
                raise LiveCognitionCheckpointError("duplicate/failed/foreign freeze generation")
            owner = self._owner(self_id)
            self._freeze_active.add(self_id)
            self._freeze_generation = generation_id
            try:
                if owner.supervisor.open_actions:
                    raise LiveCognitionCheckpointError(
                        "in-flight original Action supervisor"
                    )
                journal = PhysicalActionJournal.restore(
                    owner.files.physical_wal_file, self_id=owner.self_id,
                )
                journal.require_clear()
                # These owner values are stable: close() blocked every facade
                # mutation and each Self has a different persistence directory.
                cut = SelfOwnerCut(
                    generation_id=generation_id, self_id=self_id,
                    world_id=self.world_id, branch_id=self.branch_id,
                    former_native_session_id=owner.native_session_id,
                    last_observed_world_tick=owner.last_observed_tick,
                    intent_events=owner.intent.events,
                    skill_executions=tuple(
                        owner.skills[k] for k in sorted(owner.skills)
                    ),
                    pattern_registry=owner.pattern_registry,
                    peer_deliveries=tuple(
                        owner.peer_deliveries[k]
                        for k in sorted(owner.peer_deliveries)
                    ),
                    pending_question_refs=tuple(sorted(owner.pending_questions)),
                )
                retained = owner.retained
                if retained.exploration_continuity is not None:
                    questions = {q.question_ref for q in retained.exploration_continuity.questions if q.open}
                    if not questions.issubset(owner.pending_questions):
                        raise LiveCognitionCheckpointError("open exploration Question missing from owner cut")
                if retained.pattern_registry is not None and retained.pattern_registry != cut.pattern_registry:
                    raise LiveCognitionCheckpointError("cognition/owner registry mismatch")
                retained = replace(retained, pattern_registry=cut.pattern_registry)
                fence_ref = self.fence.fence_ref
            except BaseException:
                self._freeze_failed = True
                self._freeze_active.remove(self_id)
                raise

        try:
            checkpoint_dir = owner.files.self_root / "checkpoint-cuts"
            checkpoint_dir.mkdir(mode=0o700, exist_ok=True)
            folder = checkpoint_dir / generation_id
            folder.mkdir(mode=0o700)
            owner_path = folder / "owner-state.json"
            # Canonical original owner persists, not a forked authority.
            save_persistent_cognition(owner.files.cognition_file, retained)
            if load_persistent_cognition(owner.files.cognition_file) != retained:
                raise LiveCognitionCheckpointError("cognition write/readback mismatch")
            if cut.pattern_registry.accepted_presets or retained.exploration_continuity is not None:
                cut = replace(cut, cognition_sha256=hashlib.sha256(
                    owner.files.cognition_file.read_bytes()).hexdigest())
            save_self_owner_cut(owner_path, cut)
            receipt = SelfFrozenReceipt(
                self_id=self_id,
                snapshot=SelfSnapshotSource(
                    self_id, owner.files.cognition_file,
                    owner.files.physical_wal_file, owner_path,
                ),
                old_native_session_id=owner.native_session_id,
                freeze_ref=fence_ref + ":" + generation_id + ":" + self_id,
                physical_inflight_action_ids=(),
                undelivered_message_ids=(),
                writers_quiesced=True, issue_admission_closed=True,
                communication_quiesced=True,
            )
        except BaseException:
            with self.lock:
                self._freeze_failed = True
                self._freeze_active.discard(self_id)
            raise
        with self.lock:
            self._freeze_active.remove(self_id)
            self._freeze_completed.add(self_id)
        return receipt

    def rebind(self, self_id: str, new_server_session_id: str) -> ReboundSelfReceipt:
        with self.lock:
            if not (self.closed and self.hold and self.fence is not None):
                raise LiveCognitionCheckpointError("no verified generation fence")
            if (
                self._freeze_failed or self._freeze_active
                or (
                    self._freeze_generation is not None
                    and self._freeze_completed
                    != {owner.self_id for owner in self.owners}
                )
            ):
                raise LiveCognitionCheckpointError(
                    "incomplete or failed owner freeze; rebind forbidden"
                )
            owner = self._owner(self_id)
            prior = owner.native_session_id
            evidence = self.external_native_rejoin(self_id, new_server_session_id, prior)
            if (
                not isinstance(evidence, ExternalRejoin)
                or not evidence.new_native_session_id
                or evidence.new_native_session_id == prior
                or not (evidence.old_native_session_invalidated
                        and evidence.obsolete_gpu_tasks_fenced
                        and evidence.stale_messages_discarded)
            ):
                raise LiveCognitionCheckpointError("native rejoin and stale work fence absent")
            owner.native_session_id = evidence.new_native_session_id
            owner.fresh_native_observation_required = True
            return ReboundSelfReceipt(
                self_id, owner.native_session_id, self.world_id, self.branch_id,
                True, True, True, True,
            )

    def observe_fenced_rejoin_world_tick(
        self, *, self_id: str, native_session_id: str, world_tick: int,
    ) -> None:
        """Accept a new-source WorldBody tick while checkpoint admission is HELD.

        This narrow operation is only for the *already rebound* native session
        before the existing external physical release. Ordinary cognition and
        physical Action mutations remain forbidden throughout this call.
        Callers must independently verify the real native probe source.
        """
        with self.lock:
            if not (self.closed and self.hold and self.fence is not None):
                raise LiveCognitionCheckpointError("fenced WorldBody handoff required")
            owner = self._owner(self_id)
            if (
                not owner.fresh_native_observation_required
                or native_session_id != owner.native_session_id
                or type(world_tick) is not int
                or world_tick < owner.last_observed_tick
            ):
                raise LiveCognitionCheckpointError(
                    "fenced native WorldBody clock stale or foreign"
                )
            owner.last_observed_tick = world_tick
            owner.fresh_native_observation_required = False

    def release(self, token: str) -> None:
        with self.lock:
            if (
                not self.closed or not self.hold or self.fence is None
                or token != f"cognition-gate-{self.token}"
                or self._freeze_failed or self._freeze_active
                or (
                    self._freeze_generation is not None
                    and self._freeze_completed
                    != {owner.self_id for owner in self.owners}
                )
            ):
                raise LiveCognitionCheckpointError(
                    "stale/foreign/incomplete owner cohort release"
                )
            # External physical owner must finish its own fenced release.
            self.external_release_physical(self.fence.fence_ref)
            self.fence = None
            self.closed = False
            self.hold = False

    def delivered(self, delivery: PeerDelivery) -> None:
        """Record a completed A→B receipt atomically in both existing owners."""
        with self.lock:
            self._mutating()
            sender = self._owner(delivery.sender_self_id)
            receiver = self._owner(delivery.recipient_self_id)
            if (sender.fresh_native_observation_required
                    or receiver.fresh_native_observation_required):
                raise LiveCognitionCheckpointError(
                    "fresh native WorldBody observation required for both peers"
                )
            if (delivery.message_id in sender.peer_deliveries
                    or delivery.message_id in receiver.peer_deliveries
                    or delivery.received_world_tick > sender.last_observed_tick
                    or delivery.received_world_tick > receiver.last_observed_tick):
                raise LiveCognitionCheckpointError("unqualified/duplicate peer delivery")
            sender.peer_deliveries[delivery.message_id] = delivery
            receiver.peer_deliveries[delivery.message_id] = delivery


class CheckpointedCognitiveOwner:
    """Small actually mutable runtime over existing owner types, not a new issuer."""

    def __init__(
        self, *, retained: PersistentCognition, intent: IntentCommitment,
        pattern_registry: PatternRegistry, native_session_id: str,
        last_observed_tick: int, files: CognitiveOwnerFiles,
        physical_supervisor: ActionSupervisor,
        skills: tuple[SkillExecution, ...] = (),
        peer_deliveries: tuple[PeerDelivery, ...] = (),
        pending_questions: tuple[str, ...] = (),
    ) -> None:
        if not isinstance(retained, PersistentCognition):
            raise LiveCognitionCheckpointError("real retained cognition required")
        if not isinstance(intent, IntentCommitment):
            raise LiveCognitionCheckpointError("actual Intent owner required")
        if not isinstance(pattern_registry, PatternRegistry):
            raise LiveCognitionCheckpointError("typed pattern registry required")
        if retained.pattern_registry is not None and retained.pattern_registry != pattern_registry:
            raise LiveCognitionCheckpointError("cognition/owner registry mismatch")
        if not isinstance(physical_supervisor, ActionSupervisor):
            raise LiveCognitionCheckpointError("actual physical Action supervisor required")
        if not native_session_id or type(last_observed_tick) is not int or last_observed_tick < 0:
            raise LiveCognitionCheckpointError("invalid native session/clock")
        if not files.self_root.is_dir() or not files.physical_wal_file.is_file():
            raise LiveCognitionCheckpointError("canonical Self file or WAL missing")
        PhysicalActionJournal.read_snapshot(
            files.physical_wal_file, self_id=retained.identity.self_id,
        )
        if len({x.execution_id for x in skills}) != len(skills):
            raise LiveCognitionCheckpointError("duplicate Skill histories")
        if len({x.message_id for x in peer_deliveries}) != len(peer_deliveries):
            raise LiveCognitionCheckpointError("duplicate peer delivery")
        if (type(pending_questions) is not tuple
                or any(type(q) is not str or not q.strip() for q in pending_questions)
                or len(set(pending_questions)) != len(pending_questions)):
            raise LiveCognitionCheckpointError("invalid or duplicate pending Question")
        self.retained = retained
        self.intent = intent
        self.pattern_registry = pattern_registry
        self.native_session_id = native_session_id
        self.last_observed_tick = last_observed_tick
        self.files = files
        self.supervisor = physical_supervisor
        self.skills = {x.execution_id: x for x in skills}
        self.peer_deliveries = {x.message_id: x for x in peer_deliveries}
        self.pending_questions = set(pending_questions)
        self.fresh_native_observation_required = False
        self.current_worldbody_observation = None
        self.cohort: CognitionOwnerCohort | None = None

    @property
    def self_id(self) -> str:
        return self.retained.identity.self_id

    def _mutating(self) -> threading.RLock:
        if self.cohort is None:
            raise LiveCognitionCheckpointError("Self must be part of a cohort")
        return self.cohort.lock

    def _eligible(self) -> None:
        assert self.cohort is not None
        self.cohort._mutating(self.self_id)
        if self.fresh_native_observation_required:
            raise LiveCognitionCheckpointError(
                "fresh native WorldBody observation required after rebind"
            )

    def observe_world_tick(self, *, session_id: str, world_tick: int) -> None:
        with self._mutating():
            assert self.cohort is not None
            self.cohort._mutating(self.self_id)
            if (session_id != self.native_session_id or type(world_tick) is not int
                    or world_tick < self.last_observed_tick):
                raise LiveCognitionCheckpointError("old session/future epoch observation")
            self.last_observed_tick = world_tick
            self.fresh_native_observation_required = False

    def accept_rejoined_worldbody(self, observation, *, request_id: str) -> None:
        """Attach the verified new native probe to this existing online owner."""
        from adapters.mineflayer.python_protocol import MineflayerObservation

        with self._mutating():
            self._eligible()
            if (
                not isinstance(observation, MineflayerObservation)
                or observation.kind != "probe"
                or observation.session_id != self.native_session_id
                or observation.request_id != request_id or not request_id
                or observation.snapshot.time is None
                or observation.snapshot.time.day * 24000
                + observation.snapshot.time.time_of_day != self.last_observed_tick
            ):
                raise LiveCognitionCheckpointError("foreign or stale native WorldBody probe")
            self.current_worldbody_observation = observation

    def retain_memory(self, memory: Memory) -> None:
        with self._mutating():
            self._eligible()
            self.retained = self.retained.retain_memory(memory)

    def commit_intent(self, intent_id: str, objective: str, at_ns: int, provenance: Provenance) -> None:
        with self._mutating():
            self._eligible()
            self.intent.commit(intent_id, objective=objective, at_ns=at_ns, provenance=provenance)

    def complete_intent(self, intent_id: str, reason: str, at_ns: int, provenance: Provenance) -> None:
        with self._mutating():
            self._eligible()
            self.intent.complete(intent_id, reason=reason, at_ns=at_ns, provenance=provenance)

    def start_skill(
        self, execution_id: str, skill_id: str, at_ns: int, provenance: Provenance,
    ) -> None:
        with self._mutating():
            self._eligible()
            if execution_id in self.skills:
                raise LiveCognitionCheckpointError("duplicate Skill execution")
            skill = SkillExecution.start(
                execution_id, skill_id=skill_id, intent_commitment=self.intent,
                at_ns=at_ns, provenance=provenance,
            )
            self.skills[execution_id] = skill

    def accept_pattern(self, pattern: SchemaPattern, allowed_skills: frozenset[tuple[str, int]]) -> None:
        with self._mutating():
            self._eligible()
            self.pattern_registry = accept_learned_pattern(
                self.pattern_registry, pattern,
                accepted_by_self=True, expected_revision=self.pattern_registry.revision,
                allowed_skills=allowed_skills,
            )
            if self.retained.pattern_registry is not None:
                self.retained = replace(self.retained, pattern_registry=self.pattern_registry)


def staged_recover_cognition_cohort(
    generation: Path, restored_directory: Path,
) -> tuple[StagedRecoveredCognition, ...]:
    """Stage all Self candidates only after exact typed World+Self restore.

    These are read-only/inert candidates, not automatically running Self.
    """
    restored = Path(restored_directory)
    semantic = prepare_typed_owner_restore(generation, restored)
    result = []
    for owner in semantic:
        sid = owner.cut.self_id
        files = restored / "selves" / sid
        retained = load_persistent_cognition(files / "cognition.json")
        if retained.identity.self_id != sid:
            raise LiveCognitionCheckpointError("foreign restored Self identity")
        journal_path = files / "physical-wal.json"
        PhysicalActionJournal.read_snapshot(journal_path, self_id=sid, require_clear=True)
        result.append(StagedRecoveredCognition(
            sid, retained, owner, journal_path,
        ))
    return tuple(result)
