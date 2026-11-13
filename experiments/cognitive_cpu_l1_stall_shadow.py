"""DEV-only read-only CPU Schema shadow while one L1 task is still running.

This is a bounded *simulation probe* of event-loop progress, NOT a new
persistent Scheduler, native S49 Action owner, real-time L0 guarantee or GPU
preemption. It only consumes caller-supplied, source-qualified WorldPercept.
"""
from __future__ import annotations

import asyncio
import statistics
import time
from dataclasses import dataclass
from typing import Callable

from relay_self.cognitive_minimal_dev import (
    MinimalCognitionError,
    PatternRegistry,
    WorldPercept,
    cpu_schema_epoch,
)

@dataclass(frozen=True, slots=True)
class CpuShadowSample:
    epoch: int
    percept_seq: int
    world_session_id: str
    schema_elapsed_ns: int
    pattern_checks: int
    fast_cues: tuple[str, ...]
    goal_ids: tuple[str, ...]
    l1_pending_at_sample: bool
    schedule_lateness_ns: int


@dataclass(frozen=True, slots=True)
class CpuShadowTrace:
    evidence_class: str
    samples: tuple[CpuShadowSample, ...]
    l1_was_running_at_entry: bool
    l1_still_pending_at_exit: bool
    max_schema_elapsed_ns: int
    p50_schema_elapsed_ns: int
    p95_schema_elapsed_ns: int
    deadline_misses: int
    session_changes: int


def _percentile(values: tuple[int, ...], fraction: float) -> int:
    if not values:
        return 0
    ordered = sorted(values)
    index = max(0, min(len(ordered) - 1, int((len(ordered) - 1) * fraction + 0.999999)))
    return ordered[index]


async def simulate_cpu_schema_during_l1(
    *,
    l1_task: asyncio.Task[object],
    percept_at_epoch: Callable[[int], WorldPercept],
    registry: PatternRegistry,
    allowed_skills: frozenset[tuple[str, int]],
    epochs: int,
    period_s: float = 0.002,
    hunger_threshold: float = 17,
) -> CpuShadowTrace:
    """Sample bounded independent Schema epochs until completion or cap.

    Never reads the Mineflayer session from this routine: the caller must
    supply frames from one existing observation gateway. No L1 call, no
    retries, no physical Action and no mutation of Intent/Skill ownership.
    `deadline_misses` compares *simulation* wall clock to requested tick
    cadence; its value is not a measured WorldBody FAST deadline.
    """
    if not isinstance(l1_task, asyncio.Task):
        raise MinimalCognitionError("one existing L1 asyncio Task required")
    if not callable(percept_at_epoch):
        raise MinimalCognitionError("source Percept supplier required")
    if type(epochs) is not int or not 1 <= epochs <= 2048:
        raise MinimalCognitionError("bounded positive CPU epoch count required")
    if (
        isinstance(period_s, bool)
        or not isinstance(period_s, (int, float))
        or not 0 < period_s <= 1
    ):
        raise MinimalCognitionError("period_s must be (0,1] seconds")
    if not isinstance(registry, PatternRegistry):
        raise MinimalCognitionError("typed CPU PatternRegistry required")
    if not isinstance(allowed_skills, frozenset):
        raise MinimalCognitionError("physical Skill catalog must be immutable")

    pending_at_entry = not l1_task.done()
    if not pending_at_entry:
        raise MinimalCognitionError("L1 must still be in flight")
    started_ns = time.perf_counter_ns()
    step_ns = int(period_s * 1_000_000_000)
    samples: list[CpuShadowSample] = []
    misses = 0
    session_changes = 0
    previous_session: str | None = None
    for i in range(epochs):
        if l1_task.done():
            break
        now_ns = time.perf_counter_ns()
        expected_ns = started_ns + i * step_ns
        lateness_ns = max(0, now_ns - expected_ns)
        if lateness_ns > step_ns:
            misses += 1
        percept = percept_at_epoch(i + 1)
        if not isinstance(percept, WorldPercept):
            raise MinimalCognitionError("shadow input must be native-scoped WorldPercept")
        if previous_session is not None and percept.scope.world_session_id != previous_session:
            session_changes += 1
        previous_session = percept.scope.world_session_id
        frame = cpu_schema_epoch(
            percept, registry, allowed_skills=allowed_skills,
            epoch=i + 1, hunger_threshold=hunger_threshold,
        )
        samples.append(CpuShadowSample(
            epoch=i + 1,
            percept_seq=percept.sequence,
            world_session_id=percept.scope.world_session_id or "",
            schema_elapsed_ns=frame.elapsed_ns,
            pattern_checks=frame.pattern_checks,
            fast_cues=frame.fast_cues,
            goal_ids=tuple(goal.goal_id for goal in frame.goals),
            l1_pending_at_sample=not l1_task.done(),
            schedule_lateness_ns=lateness_ns,
        ))
        await asyncio.sleep(period_s)

    durations = tuple(x.schema_elapsed_ns for x in samples)
    return CpuShadowTrace(
        evidence_class="OFFLINE_SHADOW_CPU_WHILE_L1_PENDING",
        samples=tuple(samples),
        l1_was_running_at_entry=pending_at_entry,
        l1_still_pending_at_exit=not l1_task.done(),
        max_schema_elapsed_ns=max(durations, default=0),
        p50_schema_elapsed_ns=int(statistics.median(durations)) if durations else 0,
        p95_schema_elapsed_ns=_percentile(durations, 0.95),
        deadline_misses=misses,
        session_changes=session_changes,
    )
