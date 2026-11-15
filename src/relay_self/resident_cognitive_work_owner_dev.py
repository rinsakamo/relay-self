"""#860 Stage20: original Self cognition write gate and scoped CPU-work retirement.

No inference GPU backend or external peer send is owned here. Cancelled
asyncio Tasks attest only Python coroutine termination; they DO NOT attest
llama.cpp/server generation STOP, GPU resource release, VRAM or foreign
out-of-process tasks. External work is forbidden by Stage19's inert bridge.
"""
from __future__ import annotations

import asyncio
import threading
from collections.abc import Coroutine
from dataclasses import dataclass
from typing import Any

from relay_self.checkpointed_cognitive_runtime_dev import (
    CheckpointedCognitiveOwner,
    LiveCognitionCheckpointError,
)
from relay_self.persistent_cognition import Memory


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
        self._discarded: dict[str, list[LocalPeerDiscard]] = {
            sid: [] for sid in owners
        }
        for owner in owners.values():
            owner.cohort = self  # use original owner's existing mutation path

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
            owner.fresh_native_observation_required = False

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
