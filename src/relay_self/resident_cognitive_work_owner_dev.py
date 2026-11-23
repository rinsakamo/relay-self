"""#860 Stage20: original Self cognition write gate and scoped CPU-work retirement.

No inference GPU backend or external peer send is owned here. Cancelled
asyncio Tasks attest only Python coroutine termination; they DO NOT attest
llama.cpp/server generation STOP, GPU resource release, VRAM or foreign
out-of-process tasks. External work is forbidden by Stage19's inert bridge.
"""
from __future__ import annotations

import asyncio
import threading
import weakref
from collections.abc import Coroutine
from dataclasses import dataclass
from typing import Any
from uuid import uuid4

from relay_self.checkpointed_cognitive_runtime_dev import (
    CheckpointedCognitiveOwner,
    LiveCognitionCheckpointError,
)
from relay_self.cognitive_minimal_dev import (
    PresetAcceptanceReceipt,
    accept_skill_parameter_preset,
    initial_move_pattern,
    initial_patterns_with_relative_move,
)
from relay_self.common_io import ScopeRef
from relay_self.innate_schema import SchemaMode, SchemaSnapshot, check_schema_eligibility
from relay_self.persistent_cognition import Memory
from relay_self.provenance import Provenance
from relay_self.skill_invocation import SkillBudget, SkillDefinition, SkillParameterPreset


class ResidentCognitiveWorkError(RuntimeError):
    """A Self's CPU work, memory write or in-memory peer queue is unretired."""


@dataclass(frozen=True, slots=True)
class ResidentWorkToken:
    self_id: str
    task_ref: str
    epoch: int
    native_session_id: str
    world_epoch: int


@dataclass(frozen=True, slots=True)
class LocalPeerDiscard:
    sender_self_id: str
    recipient_self_id: str
    message_ref: str
    sender_epoch: int
    externally_sent: bool = False
    recipient_delivery_authorized: bool = False


@dataclass(frozen=True, slots=True)
class ResidentCognitionRetirement:
    self_id: str
    former_native_session_id: str
    world_epoch: int
    retired_epoch: int
    cancelled_cpu_task_refs: tuple[str, ...]
    discarded_unsent_message_refs: tuple[str, ...]
    all_cpu_coroutines_terminated: bool
    cognition_mutation_fenced: bool
    no_external_gpu_work_scope: bool = True
    no_external_peer_transport_scope: bool = True
    action_issue_authorized: bool = False


@dataclass(slots=True)
class _ResidentState:
    mode: str = "OFFLINE"
    epoch: int = 0
    native: str | None = None
    world_epoch: int | None = None
    tasks: dict[str, asyncio.Task[Any]] | None = None
    staged_peer: dict[str, tuple[str, str]] | None = None
    retired: ResidentCognitionRetirement | None = None


class ResidentCognitiveWorkOwner:
    """Own the existing CheckpointedCognitiveOwner's per-Self mutation gates.

    This is mutually exclusive with CognitionOwnerCohort; no parallel second
    canonical cognition owner is created. The original owner methods still
    write the original retained memory/Intent/Skill fields, but now consult a
    per-Self presence gate instead of one global checkpoint gate.

    Task finish does not auto-write memory: only explicit owner-mediated
    commit_memory_from_work can install a result with a current token.
    """

    def __init__(self, owners: dict[str, CheckpointedCognitiveOwner]) -> None:
        if (
            type(owners) is not dict or not owners
            or any(
                type(sid) is not str or not sid
                or not isinstance(owner, CheckpointedCognitiveOwner)
                or owner.self_id != sid
                or owner.cohort is not None
                for sid, owner in owners.items()
            )
        ):
            raise ResidentCognitiveWorkError("unattached original Self cognitive owners required")
        roots = {owner.files.self_root.resolve() for owner in owners.values()}
        if (
            len(roots) != len(owners)
            or any(parent in roots for root in roots for parent in root.parents)
            or any(owner.files.self_root.is_symlink() for owner in owners.values())
        ):
            raise ResidentCognitiveWorkError("canonical Self roots must be disjoint")
        self.lock = threading.RLock()
        self.owners = dict(owners)
        self._states = {sid: _ResidentState() for sid in owners}
        # Run configuration only: it is deliberately not part of checkpoint data.
        self._present_schemas = {}
        self._coverage_adoption_turns = weakref.WeakValueDictionary()
        self._discarded: dict[str, list[LocalPeerDiscard]] = {
            sid: [] for sid in owners
        }
        for owner in owners.values():
            owner.cohort = self  # use original owner's existing mutation path

    def register_present_schema(self, self_id: str, snapshot: SchemaSnapshot) -> None:
        """Install once before the first login; restore requires explicit rebootstrap."""
        with self.lock:
            state = self._state(self_id)
            if state.mode != "OFFLINE" or state.epoch != 0 or self_id in self._present_schemas:
                raise ResidentCognitiveWorkError("schema registration closed")
            owner = self.owners[self_id]
            registry = owner.pattern_registry
            if not isinstance(snapshot, SchemaSnapshot) or snapshot.self_id != self_id or snapshot.revision != registry.revision:
                raise ResidentCognitiveWorkError("foreign or stale schema registration")
            activation = snapshot.get("exploratory")
            # Explicit mapping: D module exploratory v1 -> B exploration pattern v1.
            expected_pattern = initial_patterns_with_relative_move().patterns[-1]
            patterns = [p for p in registry.patterns if p.schema_id == "exploration"]
            allowed = ([expected_pattern],)
            if tuple(self.owners) == ("B",):
                allowed += ([initial_move_pattern()],)
            if (activation is None or activation.spec.version != 1
                or "QUESTION_CANDIDATE" not in activation.spec.signal_kinds
                or (activation.mode is not SchemaMode.OFF and (patterns not in allowed
                    or not check_schema_eligibility(snapshot, scope=ScopeRef(self_id, None),
                        schema_id="exploratory", requested_mode=activation.mode,
                        current_registry_revision=registry.revision).allowed))):
                raise ResidentCognitiveWorkError("exploration mapping or activation invalid")
            self._present_schemas[self_id] = (snapshot, registry)

    def decide_initial_move_preset(
        self, preset: SkillParameterPreset,
    ) -> PresetAcceptanceReceipt:
        """Apply B's initial exploration preset policy to its adopted live Body."""
        from relay_self.initial_skill_ir import initial_skill_definitions
        from relay_self.physical_action_journal import PhysicalActionJournal

        with self.lock:
            scope = self.current_scope("B")
            owner = self.owners["B"]
            owner._eligible()
            body = owner.current_worldbody_observation
            definition = next(d for d in initial_skill_definitions() if d.skill_id == "MOVE")
            if (
                tuple(self.owners) != ("B",) or scope[0] != 1
                or body is None or body.session_id != scope[1]
                or body.snapshot.health <= 0 or body.snapshot.time is None
                or body.snapshot.time.day * 24000 + body.snapshot.time.time_of_day
                != owner.last_observed_tick
                or owner.intent.events or owner.skills or owner.supervisor.recorded_actions
                or owner.pattern_registry.accepted_presets
                or not isinstance(preset, SkillParameterPreset)
                or preset.budget != SkillBudget(1, 1500, 2.0, 32)
                or preset.constraints.requirements or preset.arguments
                or preset.expected_cost is not None
                or PhysicalActionJournal.read_snapshot(
                    owner.files.physical_wal_file, self_id="B", require_clear=True,
                )
            ):
                raise ResidentCognitiveWorkError("initial B exploration policy declined MOVE preset")
            receipt = PresetAcceptanceReceipt(
                "B", "initial-move-" + uuid4().hex, preset.preset_ref,
                Provenance("original-b-initial-move-policy-v1", body.provenance.reference),
            )
            self.publish_accepted_move_preset(
                preset=preset, definition=definition, receipt=receipt, scope=scope,
                expected_revision=owner.pattern_registry.revision,
            )
            return receipt

    def publish_accepted_move_preset(
        self, *, preset: SkillParameterPreset, definition: SkillDefinition,
        receipt: PresetAcceptanceReceipt, scope: tuple[int, str, int],
        expected_revision: int,
    ) -> None:
        """Publish a decision already authenticated by the original Self caller."""
        from relay_self.exploration_schema_record_dev import (
            canonical_exploration_snapshot,
            require_recorded_schema,
        )
        from relay_self.initial_skill_ir import initial_skill_definitions

        with self.lock:
            if (
                tuple(self.owners) != ("B",)
                or not isinstance(receipt, PresetAcceptanceReceipt)
                or receipt.self_id != "B"
                or scope != self.current_scope("B")
                or not isinstance(preset, SkillParameterPreset)
                or preset.pattern_id != initial_move_pattern().pattern_id
                or definition != next(d for d in initial_skill_definitions() if d.skill_id == "MOVE")
            ):
                raise ResidentCognitiveWorkError("current original B MOVE acceptance required")
            owner = self.owners["B"]
            owner._eligible()
            snapshot = self.present_schema("B")
            if (
                snapshot.get("exploratory").mode is not SchemaMode.FULL
                or owner.retained.pattern_registry != owner.pattern_registry
            ):
                raise ResidentCognitiveWorkError("current retained exploration registry required")
            registry = accept_skill_parameter_preset(
                owner.pattern_registry, preset, definition=definition, receipt=receipt,
                accepted_by_self=True, expected_revision=expected_revision,
                available_skills=frozenset({("MOVE", 1)}),
            )
            retained = owner.retained.retain_schema_registry(
                registry, expected_revision=expected_revision,
            )
            revision = canonical_exploration_snapshot(
                self_id="B", registry=registry, mode=SchemaMode.FULL,
            )
            require_recorded_schema(revision, self_id="B", registry=registry)
            owner.retained = retained
            owner.pattern_registry = registry
            self._present_schemas["B"] = (revision, registry)

    def present_schema(self, self_id: str) -> SchemaSnapshot:
        """Return only a current registration, under the resident lock."""
        with self.lock:
            self.current_scope(self_id)
            registration = self._present_schemas.get(self_id)
            if registration is None or registration[1] != self.owners[self_id].pattern_registry:
                raise ResidentCognitiveWorkError("schema unregistered or registry changed")
            return registration[0]

    def read_present_cpu(
        self, *, bridge, self_id, boot=None, world=None, links=None,
        initial_receipts=None, historical_composite=None,
    ):
        """Read current original-owner Present, including a qualified reJOIN source.

        The historical Stage28 source keeps its original verifier. A reJOIN
        requires BOTH immutable historical receipts, but is qualified solely
        by re-reading the original current Native/Paper sources under this lock.
        Neither path grants a new capability or persists cognition.
        """
        from relay_self.b_np1b_rejoin_present_dev import build_rejoined_owner_present
        from relay_self.bd1b_owner_present_dev import build_bd1b_owner_present

        with self.lock:
            if bridge.cognitive_work is not self or bridge.owners.get(self_id) is not self.owners.get(self_id):
                raise ResidentCognitiveWorkError("foreign resident bridge")
            rejoin = initial_receipts is not None or historical_composite is not None
            if rejoin:
                if (initial_receipts is None or historical_composite is None
                        or any(value is not None for value in (boot, world, links))):
                    raise ResidentCognitiveWorkError("ambiguous mixed Stage28/reJOIN source")
                if getattr(self, "_normal_second_rejoin_cut", None) is not None:
                    from relay_self.b_np1b_second_rejoin_rearm_dev import (
                        build_second_rejoin_owner_present,
                    )

                    return build_second_rejoin_owner_present(
                        bridge=bridge, self_id=self_id,
                        initial_receipts=initial_receipts,
                        historical_composite=historical_composite,
                    )
                return build_rejoined_owner_present(
                    bridge=bridge, self_id=self_id,
                    initial_receipts=initial_receipts,
                    historical_composite=historical_composite,
                )
            if any(value is None for value in (boot, world, links)):
                raise ResidentCognitiveWorkError("Stage28 source witnesses required")
            return build_bd1b_owner_present(
                bridge=bridge, boot=boot, world=world, links=links, self_id=self_id,
            )

    def read_context_shadow_cpu(
        self, *, bridge, self_id: str, boot, world, links,
        memory_ids: tuple[str, ...] = (), recent_limit: int = 8,
    ):
        """Opt-in read-only R1 Context through the *existing* Original Owner.

        The original resident lock, persisted Owner, Stage28 source and
        read-only Shadow comparison remain the only providers. This is NOT
        a second Owner, reJOIN admission, L1 prompt input, GPU lease or
        Physical issuer. The result retains R1's original provenance and
        explicit freshness recheck contract; callers must revalidate it
        before later use, as Paper may advance outside this lock.
        """
        from relay_self.r1_owner_context_shadow_dev import (
            R1ShadowStatus,
            compare_original_owner_r1_shadow,
            r1_shadow_is_live,
        )

        with self.lock:
            if (
                getattr(bridge, "cognitive_work", None) is not self
                or not isinstance(getattr(bridge, "owners", None), dict)
                or self_id not in self.owners
                or bridge.owners.get(self_id) is not self.owners[self_id]
            ):
                raise ResidentCognitiveWorkError("foreign original Context reader")
            report = compare_original_owner_r1_shadow(
                bridge=bridge, boot=boot, world=world, links=links,
                self_id=self_id, memory_ids=memory_ids,
                recent_limit=recent_limit,
            )
            if (
                report.status is not R1ShadowStatus.MATCH
                or report.context is None
                or not r1_shadow_is_live(
                    report, bridge=bridge, boot=boot, world=world, links=links,
                )
            ):
                raise ResidentCognitiveWorkError(
                    "original read-only Context source unavailable or stale"
                )
            return report

    def read_rejoined_context_shadow_cpu(
        self, *, bridge, self_id: str, initial_receipts, historical_composite,
    ):
        """Opt-in first reJOIN Composite CURRENT through this original Owner.

        No Stage28 boot/link reuse, no second Owner or store, and no L1/physical
        admission. A later consumer must revalidate the returned diagnostic.
        """
        from relay_self.r2_3_rejoin_composite_context_dev import (
            read_r23_original_rejoin_context,
        )

        with self.lock:
            if (
                getattr(bridge, "cognitive_work", None) is not self
                or not isinstance(getattr(bridge, "owners", None), dict)
                or self_id not in self.owners
                or bridge.owners.get(self_id) is not self.owners[self_id]
            ):
                raise ResidentCognitiveWorkError("foreign original reJOIN Context reader")
            return read_r23_original_rejoin_context(
                bridge=bridge, self_id=self_id,
                initial_receipts=initial_receipts,
                historical_composite=historical_composite,
            )

    def read_rejoined_l1_source_compatibility_cpu(
        self, *, bridge, self_id: str,
    ):
        """R2-3b opt-in Inquiry/CURRENT comparison; no post-reJOIN L1 issuer.

        Only reads the already-bound original A/B CPU source cut. It neither
        registers a candidate nor changes L1 prompts, Memory, Intent or WAL.
        """
        from relay_self.r2_3b_original_rejoin_l1_source_compare_dev import (
            compare_r23b_original_rejoin_inquiry_context,
        )

        with self.lock:
            if (
                getattr(bridge, "cognitive_work", None) is not self
                or not isinstance(getattr(bridge, "owners", None), dict)
                or self_id not in self.owners
                or bridge.owners.get(self_id) is not self.owners[self_id]
            ):
                raise ResidentCognitiveWorkError("foreign original R2-3b Context reader")
            return compare_r23b_original_rejoin_inquiry_context(
                bridge=bridge, self_id=self_id,
            )

    def prepare_rejoined_original_l1_request_cpu(self, *, bridge, self_id: str):
        """CPU-only first-reJOIN Question request, registered on this Owner.

        Uses already-owned Source and existing B ADOPT/HOLD/DECLINE choices.
        This does NOT connect the GPU issuer, change input, or adopt a Question.
        """
        from relay_self.r2_3c_original_rejoin_frozen_l1_dev import (
            prepare_r23c_original_rejoin_l1_cpu,
        )

        with self.lock:
            if (
                getattr(bridge, "cognitive_work", None) is not self
                or self_id not in self.owners
                or getattr(bridge, "owners", {}).get(self_id) is not self.owners[self_id]
            ):
                raise ResidentCognitiveWorkError("foreign original reJOIN L1 request")
            return prepare_r23c_original_rejoin_l1_cpu(
                bridge=bridge, self_id=self_id,
            )

    def compare_rejoined_original_l1_request_cpu(self, *, bridge, turn):
        """Original Owner's registered frozen Request vs revalidated Context."""
        from relay_self.r2_3c_original_rejoin_frozen_l1_dev import (
            compare_r23c_registered_l1_context,
        )

        with self.lock:
            if getattr(bridge, "cognitive_work", None) is not self:
                raise ResidentCognitiveWorkError("foreign original L1 comparison")
            return compare_r23c_registered_l1_context(
                bridge=bridge, turn=turn,
            )

    async def issue_rejoined_original_question_once_dev(
        self, *, bridge, lane, turn, timeout_s: float = 60.0,
    ):
        """Opt-in original reJOIN Question L1 issuer, no Question adoption.

        The issuer checks original Source and ticket under this same Owner's
        lock; it never gains independent memory/intent/physical authority.
        """
        from relay_self.r2_3e_original_rejoin_question_issuer_dev import (
            issue_r23e_original_rejoin_question_once_dev,
        )

        if (
            getattr(bridge, "cognitive_work", None) is not self
            or getattr(lane, "cognitive_work", None) is not self
        ):
            raise ResidentCognitiveWorkError("foreign original reJOIN issuer")
        return await issue_r23e_original_rejoin_question_once_dev(
            bridge=bridge, lane=lane, turn=turn, timeout_s=timeout_s,
        )

    def read_coverage_inquiry_cpu(
        self, *, bridge, self_id, boot=None, world=None, links=None,
        initial_receipts=None, historical_composite=None,
    ):
        """Consume the same current Present through the original Inquiry contract."""
        from relay_self.bd1b_coverage_inquiry_dev import (
            _build_inquiry,
            build_coverage_inquiry,
        )

        with self.lock:
            readout = self.read_present_cpu(
                bridge=bridge, boot=boot, world=world, links=links, self_id=self_id,
                initial_receipts=initial_receipts,
                historical_composite=historical_composite,
            )
            if initial_receipts is not None:
                # The shared Inquiry consumer rebuilds, compares and validates
                # Need/coverage, now using the exact same reJOIN source path.
                def present_reader(**_ignored):
                    return self.read_present_cpu(
                        bridge=bridge, self_id=self_id,
                        initial_receipts=initial_receipts,
                        historical_composite=historical_composite,
                    )

                return _build_inquiry(
                    bridge=bridge, boot=None, world=None, links=None,
                    self_id=self_id, readout=readout, present_reader=present_reader,
                )
            return build_coverage_inquiry(
                bridge=bridge, boot=boot, world=world, links=links,
                self_id=self_id, readout=readout,
            )

    def bind_normal_rejoin_source_cpu(
        self, *, bridge, initial_receipts, historical_composite,
    ) -> None:
        """Once-only original history binding; full current A/B revalidation."""
        from relay_self.b_np1b_normal_present_poll_dev import bind_normal_rejoin_source_cpu

        return bind_normal_rejoin_source_cpu(
            resident=self, bridge=bridge, initial_receipts=initial_receipts,
            historical_composite=historical_composite,
        )

    def poll_normal_present_cpu(self, *, bridge):
        """Ordinary original resident CPU caller; no GPU or physical work."""
        from relay_self.b_np1b_normal_present_poll_dev import poll_normal_present_cpu

        return poll_normal_present_cpu(resident=self, bridge=bridge)

    def _state(self, self_id: str) -> _ResidentState:
        try:
            return self._states[self_id]
        except (KeyError, TypeError) as exc:
            raise ResidentCognitiveWorkError("unknown cognitive Self") from exc

    def _mutating(self, self_id: str | None = None) -> None:
        """Called ONLY by original owner under its existing shared lock."""
        if self_id is None:
            raise LiveCognitionCheckpointError("resident mutation requires Self scope")
        state = self._state(self_id)
        if state.mode != "ONLINE":
            raise LiveCognitionCheckpointError("individual cognition epoch fenced")

    def bind_login(
        self, *, self_id: str, native_session_id: str,
        world_epoch: int, world_tick: int,
    ) -> None:
        """Called after current native probe, before any new cognitive writes."""
        with self.lock:
            state = self._state(self_id)
            if (
                state.mode != "OFFLINE"
                or type(native_session_id) is not str or not native_session_id
                or type(world_epoch) is not int or world_epoch < 0
                or type(world_tick) is not int or world_tick < 0
                or any(
                    other.native == native_session_id
                    for other in self._states.values()
                    if other.mode == "ONLINE"
                )
            ):
                raise ResidentCognitiveWorkError("new native Self cognition bind invalid")
            state.mode = "ONLINE"
            state.epoch += 1
            state.native = native_session_id
            state.world_epoch = world_epoch
            state.tasks = {}
            state.staged_peer = {}
            state.retired = None
            owner = self.owners[self_id]
            owner.native_session_id = native_session_id
            owner.last_observed_tick = world_tick
            owner.current_worldbody_observation = None
            owner.fresh_native_observation_required = False

    def current_scope(self, self_id: str) -> tuple[int, str, int]:
        """Live original Self/native/World tuple for owned L1/L2 admission."""
        with self.lock:
            state = self._state(self_id)
            if (
                state.mode != "ONLINE" or state.native is None
                or state.world_epoch is None
            ):
                raise ResidentCognitiveWorkError("original Self cognition not online")
            return (state.epoch, state.native, state.world_epoch)

    def quarantined_scope(self, self_id: str) -> tuple[int, str, int]:
        """Only after original memory/Intent/Skill writer admission is closed."""
        with self.lock:
            state = self._state(self_id)
            if (
                state.mode != "QUARANTINED" or state.native is None
                or state.world_epoch is None
            ):
                raise ResidentCognitiveWorkError("original Self cognition not quarantined")
            return (state.epoch, state.native, state.world_epoch)

    def fence_self(self, self_id: str) -> int:
        """Sync: deny new original cognition writes BEFORE any await/cancel."""
        with self.lock:
            state = self._state(self_id)
            if state.mode == "ONLINE":
                state.mode = "QUARANTINED"
                state.epoch += 1
            elif state.mode != "QUARANTINED":
                raise ResidentCognitiveWorkError("cognitive actor not online")
            return state.epoch

    def start_cpu_task(
        self, self_id: str, *, task_ref: str,
        work: Coroutine[Any, Any, Any],
    ) -> tuple[ResidentWorkToken, asyncio.Task[Any]]:
        with self.lock:
            state = self._state(self_id)
            if state.mode != "ONLINE" or type(task_ref) is not str or not task_ref:
                work.close()
                raise ResidentCognitiveWorkError("resident CPU work not admitted")
            assert state.tasks is not None and state.native is not None
            assert state.world_epoch is not None
            if task_ref in state.tasks:
                work.close()
                raise ResidentCognitiveWorkError("duplicate CPU work identity")
            try:
                task = asyncio.create_task(work)
            except BaseException:
                work.close()
                raise
            token = ResidentWorkToken(
                self_id, task_ref, state.epoch,
                state.native, state.world_epoch,
            )
            state.tasks[task_ref] = task
            return token, task

    def commit_memory_from_work(
        self, token: ResidentWorkToken, memory: Memory,
    ) -> None:
        """Commit a completed result only at the original current Self epoch."""
        with self.lock:
            if not isinstance(token, ResidentWorkToken):
                raise ResidentCognitiveWorkError("typed cognitive work token required")
            state = self._state(token.self_id)
            task = (state.tasks or {}).get(token.task_ref)
            if (
                state.mode != "ONLINE"
                or state.epoch != token.epoch
                or state.native != token.native_session_id
                or state.world_epoch != token.world_epoch
                or task is None or not task.done()
                or task.cancelled() or task.exception() is not None
            ):
                raise ResidentCognitiveWorkError("late/unqualified CPU work result")
            # Existing owner has the only retained cognition owner API.
            self.owners[token.self_id].retain_memory(memory)
            del state.tasks[token.task_ref]

    def stage_unsent_peer_message(
        self, *, self_id: str, recipient_self_id: str,
        message_ref: str, payload_ref: str,
    ) -> None:
        """Never transmits a message. Unsent queues are discarded on logout."""
        with self.lock:
            state = self._state(self_id)
            if (
                state.mode != "ONLINE" or recipient_self_id not in self.owners
                or recipient_self_id == self_id
                or type(message_ref) is not str or not message_ref
                or type(payload_ref) is not str or not payload_ref
            ):
                raise ResidentCognitiveWorkError("invalid local-only peer staging")
            assert state.staged_peer is not None
            if message_ref in state.staged_peer:
                raise ResidentCognitiveWorkError("duplicate local peer identity")
            state.staged_peer[message_ref] = (recipient_self_id, payload_ref)

    async def retire_self(
        self, self_id: str, *, timeout_s: float = 5.0,
    ) -> ResidentCognitionRetirement:
        """Cancellation request -> awaited task STOP -> no external peer send.

        Must be called only AFTER the original physical issuer was revoked
        via quarantine_resident. This does not prove backend GPU release.
        """
        if (
            type(timeout_s) not in (float, int) or not 0 < timeout_s <= 30
        ):
            raise ResidentCognitiveWorkError("bounded CPU task retirement timeout")
        with self.lock:
            state = self._state(self_id)
            if state.mode != "QUARANTINED":
                raise ResidentCognitiveWorkError("cognition must be fenced before retirement")
            tasks = dict(state.tasks or {})
            epoch = state.epoch
            old_native = state.native
            old_world = state.world_epoch
            if old_native is None or old_world is None:
                raise ResidentCognitiveWorkError("missing former cognition epoch")
        for task in tasks.values():
            if not task.done():
                task.cancel()
        if tasks:
            completed, outstanding = await asyncio.wait(
                tasks.values(), timeout=float(timeout_s),
            )
            if outstanding:
                # Retain task handles so the actor cannot be logged back in.
                raise ResidentCognitiveWorkError(
                    "CPU coroutine not stopped; individual cognition HOLD"
                )
            if not all(task.done() for task in completed):
                raise ResidentCognitiveWorkError("CPU coroutine stop unverified")
        with self.lock:
            state = self._state(self_id)
            if state.mode != "QUARANTINED" or state.epoch != epoch:
                raise ResidentCognitiveWorkError("cognition changed during retire")
            if any(not t.done() for t in (state.tasks or {}).values()):
                raise ResidentCognitiveWorkError("active CPU task appeared during retire")
            cancelled = tuple(sorted(tasks))
            for task in (state.tasks or {}).values():
                if task.done() and not task.cancelled():
                    try:
                        task.exception()  # consume exception; never adopt stale result
                    except asyncio.CancelledError:
                        pass
            staged = state.staged_peer or {}
            discarded = tuple(sorted(staged))
            self._discarded[self_id].extend(
                LocalPeerDiscard(
                    self_id, staged[ref][0], ref, epoch - 1,
                )
                for ref in discarded
            )
            state.tasks = {}
            state.staged_peer = {}
            result = ResidentCognitionRetirement(
                self_id, old_native, old_world, epoch,
                cancelled, discarded, True, True,
            )
            state.retired = result
            return result

    def mark_offline(self, receipt: ResidentCognitionRetirement) -> None:
        with self.lock:
            state = self._state(receipt.self_id)
            if (
                state.mode != "QUARANTINED" or state.retired != receipt
                or state.tasks or state.staged_peer
                or not receipt.all_cpu_coroutines_terminated
                or not receipt.cognition_mutation_fenced
            ):
                raise ResidentCognitiveWorkError("unqualified cognitive work logout")
            state.mode = "OFFLINE"
            state.native = None
            state.world_epoch = None

    def retired_recorded_schemas(self) -> dict[str, SchemaSnapshot]:
        """Read original pre-login registrations ONLY after true A/B retirement.

        Registry presence does not establish activation. No inferred defaults
        are returned, and a partially registered cohort is a source HOLD.
        """
        from relay_self.exploration_schema_record_dev import require_recorded_schema

        with self.lock:
            if not self._present_schemas:
                return {}
            if set(self._present_schemas) != set(self.owners):
                raise ResidentCognitiveWorkError("partial original Schema registration")
            found = {}
            for sid, owner in self.owners.items():
                if not self.retired_clean(sid):
                    raise ResidentCognitiveWorkError("Schema cut requires retired original Self")
                snapshot, pinned_registry = self._present_schemas[sid]
                if pinned_registry != owner.pattern_registry:
                    raise ResidentCognitiveWorkError("original Schema registry changed after login")
                try:
                    found[sid] = require_recorded_schema(
                        snapshot, self_id=sid, registry=owner.pattern_registry,
                    )
                except ValueError as exc:
                    raise ResidentCognitiveWorkError("original Schema registration invalid") from exc
            return found

    def retired_clean(self, self_id: str) -> bool:
        with self.lock:
            state = self._state(self_id)
            return (
                state.mode == "OFFLINE" and state.retired is not None
                and not state.tasks and not state.staged_peer
            )

    def discarded_local_messages(self, self_id: str) -> tuple[LocalPeerDiscard, ...]:
        with self.lock:
            return tuple(self._discarded[self_id])
