"""Original resident-owned periodic A/B CPU Present schedule (DEV).

The existing ResidentCognitiveWorkOwner owns BOTH asyncio tasks, their
per-Self epochs and logout cancellation. This scheduler only holds an
ephemeral observation cache. It cannot issue physical Actions, GPU requests,
peer messages, or write cognition. Every read revalidates the original sources.
"""
from __future__ import annotations

import asyncio
from dataclasses import dataclass
from typing import TYPE_CHECKING

from relay_self.b_np1b_normal_present_poll_dev import NormalPresentCpuPoll
from relay_self.resident_cognitive_work_owner_dev import (
    ResidentCognitiveWorkOwner,
    ResidentWorkToken,
)

if TYPE_CHECKING:
    from relay_self.owned_resident_physical_bridge_dev import OwnedResidentPhysicalBridge


class NormalCpuScheduleHold(RuntimeError):
    """No current, original Owner-authorized CPU schedule source is available."""


@dataclass(frozen=True, slots=True)
class ScheduledPresentCpu:
    """Ephemeral qualified result; never a persistent cognition adoption ticket."""

    self_id: str
    token: ResidentWorkToken
    iteration: int
    source_pair_revision: str
    poll: NormalPresentCpuPoll


class NormalResidentPresentCpuScheduler:
    """Two independent original-Owner tasks sampling the same verified source cut."""

    _TASK_REFS = {"A": "normal-present-cpu:A", "B": "normal-present-cpu:B"}
    _SECOND_TASK_REFS = {
        "A": "normal-present-cpu:g2:A",
        "B": "normal-present-cpu:g2:B",
    }

    def __init__(
        self, *, bridge: OwnedResidentPhysicalBridge,
        resident: ResidentCognitiveWorkOwner,
        interval_s: float,
        task_refs: dict[str, str] | None = None,
    ) -> None:
        # Unique generation task identities prevent a stale old-B work token
        # from matching a new task when B's original native epoch is unchanged.
        self._TASK_REFS = dict(
            type(self)._TASK_REFS if task_refs is None else task_refs
        )
        self.bridge = bridge
        self.resident = resident
        self.interval_s = interval_s
        self._tokens: dict[str, ResidentWorkToken] = {}
        self._tasks: dict[str, asyncio.Task[None]] = {}
        self._iterations = {"A": 0, "B": 0}
        self._current: dict[str, ScheduledPresentCpu] = {}
        self._held: dict[str, str] = {}
        self._stopped = False

    def _require_owned_task(self, self_id: str) -> ResidentWorkToken:
        if (
            self._stopped
            or type(self_id) is not str
            or self_id not in self._TASK_REFS
            or getattr(self.resident, "_normal_present_scheduler", None) is not self
        ):
            raise NormalCpuScheduleHold("original CPU scheduler not running")
        token = self._tokens.get(self_id)
        task = self._tasks.get(self_id)
        if (
            type(token) is not ResidentWorkToken
            or task is None
            or task.done()
            or task.cancelled()
            or token.self_id != self_id
            or token.task_ref != self._TASK_REFS[self_id]
        ):
            raise NormalCpuScheduleHold("original scheduled CPU task not active")
        state = self.resident._state(self_id)
        if (
            state.mode != "ONLINE"
            or (state.epoch, state.native, state.world_epoch)
            != (token.epoch, token.native_session_id, token.world_epoch)
            or (state.tasks or {}).get(token.task_ref) is not task
        ):
            raise NormalCpuScheduleHold("original Self epoch or CPU task was fenced")
        return token

    async def _run(self, self_id: str) -> None:
        """Each iteration either publishes a rechecked current CPU result or HOLD."""
        while True:
            with self.resident.lock:
                try:
                    token = self._require_owned_task(self_id)
                    if asyncio.current_task() is not self._tasks[self_id]:
                        raise NormalCpuScheduleHold("unowned scheduler coroutine")
                    result = self.bridge.poll_normal_present_cpu()
                    # The external Paper source may change while being read;
                    # Bridge itself requalifies it. Check Owner epoch *again*
                    # before making a result visible.
                    if self._require_owned_task(self_id) != token:
                        raise NormalCpuScheduleHold("original CPU epoch moved")
                    self._iterations[self_id] += 1
                    self._current[self_id] = ScheduledPresentCpu(
                        self_id, token, self._iterations[self_id],
                        result.source_pair_revision, result,
                    )
                    self._held.pop(self_id, None)
                except (RuntimeError, ValueError, TypeError, KeyError, AttributeError, OSError) as exc:
                    self._current.pop(self_id, None)
                    self._held[self_id] = type(exc).__name__
                    # Once this Self was fenced, stop attempting to serve it.
                    try:
                        self._require_owned_task(self_id)
                    except NormalCpuScheduleHold:
                        return
            await asyncio.sleep(self.interval_s)

    def require_current(self, self_id: str) -> ScheduledPresentCpu:
        """Do not expose a cached source unless it is *still* current now."""
        with self.resident.lock:
            try:
                token = self._require_owned_task(self_id)
                sample = self._current.get(self_id)
                if (
                    type(sample) is not ScheduledPresentCpu
                    or sample.token != token
                    or sample.iteration <= 0
                ):
                    raise NormalCpuScheduleHold("no qualified scheduled result yet")
                # Cached snapshots never become authority. The original bridge
                # must verify the entire A/B Native/Paper/Schema set again.
                current = self.bridge.poll_normal_present_cpu()
                if current != sample.poll or current.source_pair_revision != sample.source_pair_revision:
                    raise NormalCpuScheduleHold("scheduled result was superseded")
                self._require_owned_task(self_id)
                return sample
            except NormalCpuScheduleHold:
                raise
            except (RuntimeError, ValueError, TypeError, KeyError, AttributeError, OSError) as exc:
                raise NormalCpuScheduleHold("original CPU source no longer current") from exc

    def status(self, self_id: str) -> tuple[str, int]:
        """Diagnostic count only. It is not a permission to use an old result."""
        with self.resident.lock:
            if self_id not in self._TASK_REFS:
                raise NormalCpuScheduleHold("foreign Self")
            try:
                self._require_owned_task(self_id)
            except NormalCpuScheduleHold:
                return ("STOPPED", self._iterations[self_id])
            return (
                "HOLD" if self_id in self._held else
                "CURRENT" if self_id in self._current else "PENDING",
                self._iterations[self_id],
            )

    async def stop(self) -> None:
        """Stop scheduling; keep original Owner task records for retirement audit."""
        with self.resident.lock:
            self._stopped = True
            self._current.clear()
            tasks = tuple(self._tasks.values())
            for task in tasks:
                if not task.done():
                    task.cancel()
        if tasks:
            await asyncio.gather(*tasks, return_exceptions=True)


def start_normal_resident_present_cpu(
    *, bridge: OwnedResidentPhysicalBridge, interval_s: float = 0.05,
    task_refs: dict[str, str] | None = None,
) -> NormalResidentPresentCpuScheduler:
    """Install *original* A/B CPU owner tasks after source qualification.

    Must be invoked in a running asyncio loop. Startup is all-or-nothing;
    neither a new cognition owner nor a timer outside the original Owner
    is installed. Logout uses the original Owner's task cancellation path.
    """
    from relay_self.owned_resident_physical_bridge_dev import OwnedResidentPhysicalBridge

    if (
        not isinstance(bridge, OwnedResidentPhysicalBridge)
        or not isinstance(bridge.cognitive_work, ResidentCognitiveWorkOwner)
        or type(interval_s) not in (float, int)
        or not 0.01 <= interval_s <= 30.0
    ):
        raise NormalCpuScheduleHold("original Bridge and bounded CPU interval required")
    resident = bridge.cognitive_work
    try:
        asyncio.get_running_loop()
        with resident.lock:
            second = getattr(resident, "_normal_second_rejoin_cut", None)
            if task_refs is None:
                if second is not None:
                    raise NormalCpuScheduleHold(
                        "second reJOIN requires a distinct generation task reference"
                    )
                refs = dict(NormalResidentPresentCpuScheduler._TASK_REFS)
            else:
                if (
                    type(task_refs) is not dict
                    or task_refs != NormalResidentPresentCpuScheduler._SECOND_TASK_REFS
                    or second is None
                    or getattr(second, "bridge", None) is not bridge
                ):
                    raise NormalCpuScheduleHold("unowned CPU task-generation selector")
                refs = dict(task_refs)
            if getattr(resident, "_normal_present_scheduler", None) is not None:
                raise NormalCpuScheduleHold("original CPU schedule already installed")
            bridge.poll_normal_present_cpu()
            for sid, task_ref in refs.items():
                state = resident._state(sid)
                if (
                    state.mode != "ONLINE"
                    or state.native is None
                    or state.world_epoch is None
                    or state.tasks is None
                    or task_ref in state.tasks
                ):
                    raise NormalCpuScheduleHold("A/B original CPU task admission unavailable")
            scheduler = NormalResidentPresentCpuScheduler(
                bridge=bridge, resident=resident, interval_s=float(interval_s),
                task_refs=refs,
            )
            try:
                for sid, task_ref in scheduler._TASK_REFS.items():
                    token, task = resident.start_cpu_task(
                        sid, task_ref=task_ref, work=scheduler._run(sid),
                    )
                    scheduler._tokens[sid] = token
                    scheduler._tasks[sid] = task
            except BaseException:
                # No coroutine can run until we yield the currently held event
                # loop. Roll back all partial registrations and cancel tasks.
                scheduler._stopped = True
                for sid, task in scheduler._tasks.items():
                    task.cancel()
                    state = resident._state(sid)
                    if (state.tasks or {}).get(scheduler._TASK_REFS[sid]) is task:
                        del state.tasks[scheduler._TASK_REFS[sid]]
                raise
            resident._normal_present_scheduler = scheduler
            return scheduler
    except NormalCpuScheduleHold:
        raise
    except (RuntimeError, ValueError, TypeError, KeyError, AttributeError, OSError) as exc:
        raise NormalCpuScheduleHold("original CPU scheduler admission unavailable") from exc
