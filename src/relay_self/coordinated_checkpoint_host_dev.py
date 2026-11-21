"""#860: explicitly polled full-cohort STOP -> 60s World+Self checkpoint host.

Not an unattended daemon. Hooks/owned Paper callbacks are external contracts,
not proofs of real Minecraft, genuine GPU task cancellation, or native ownership.
"""
from __future__ import annotations

import asyncio
import math
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Awaitable, Callable

from relay_self.checkpoint_stop_neutralization_dev import (
    StopCohortReady,
    StopParticipant,
    prepare_stop_before_autosave,
)
from relay_self.checkpointed_cognitive_runtime_dev import CognitionOwnerCohort
from relay_self.cohort_parallel_barrier_dev import require_bounded_workers
from relay_self.coordinated_autosave_runtime_dev import (
    AutosaveCycleResult,
    CoordinatedAutosaveRuntime,
)
from relay_self.coordinated_checkpoint_dev import verify_generation
from relay_self.owned_paper_world_dev import OwnedPaperWorld
from relay_self.physical_issue_admission_dev import PhysicalIssueAdmission


class CheckpointHostError(RuntimeError):
    """Host fails closed instead of continuing a split or unknown generation."""


@dataclass(frozen=True, slots=True)
class HostCheckpointCycle:
    stop: StopCohortReady
    saved: AutosaveCycleResult
    previous_paper_session: str | None
    next_paper_session: str | None
    duration_s: float
    historical_replay_performed: bool = False


class CoordinatedCheckpointHost:
    """Owns one explicit STOP→save pulse, with a fixed N-Self native owner roster.

    The same PhysicalIssueAdmission must be passed to CognitionOwnerCohort
    external physical close/rebind/release callbacks; this host does not install
    that callback or introduce new authority.
    """

    def __init__(
        self, *, runtime: CoordinatedAutosaveRuntime,
        physical: PhysicalIssueAdmission,
        cognitive_cohort: CognitionOwnerCohort,
        participants_now: Callable[[], tuple[StopParticipant, ...]],
        stop_audit_dir: Path,
        owned_paper: OwnedPaperWorld | None = None,
        prepare_native_rejoin: Callable[[str, str, str], Awaitable[str]] | None = None,
        stop_timeout_s: float = 8.0,
        stop_parallel_workers: int = 1,
        rejoin_parallel_workers: int = 1,
        monotonic_clock: Callable[[], float] = time.monotonic,
        sleep: Callable[[float], Awaitable[None]] = asyncio.sleep,
    ) -> None:
        if not isinstance(runtime, CoordinatedAutosaveRuntime):
            raise CheckpointHostError("coordinated autosave runtime required")
        if (
            not isinstance(physical, PhysicalIssueAdmission)
            or not physical.requires_neutral_stop
            or not runtime.strict_typed_owner_cut
        ):
            raise CheckpointHostError("strict typed owner and STOP required")
        if (
            not isinstance(cognitive_cohort, CognitionOwnerCohort)
            or cognitive_cohort.world_id != runtime.world_id
            or cognitive_cohort.branch_id != runtime.branch_id
            or getattr(runtime.admission.close, "__self__", None) is not cognitive_cohort
            or getattr(runtime.admission.release, "__self__", None) is not cognitive_cohort
        ):
            raise CheckpointHostError("one actual cognition owner cohort required")
        if (
            tuple(p.self_id for p in runtime.participants) != physical.self_roster
            or tuple(o.self_id for o in cognitive_cohort.owners)
            != physical.self_roster
            or not callable(participants_now) or not callable(monotonic_clock)
            or not callable(sleep)
        ):
            raise CheckpointHostError("full shared physical/Self roster required")
        if owned_paper is not None and (
            not isinstance(owned_paper, OwnedPaperWorld)
            or owned_paper.world_id != runtime.world_id
            or owned_paper.branch_id != runtime.branch_id
            or owned_paper.world_dir != runtime.source_world
            or not runtime.paper_layout
        ):
            raise CheckpointHostError("owned Paper and runtime World identity mismatch")
        if (
            type(stop_timeout_s) not in (float, int)
            or not math.isfinite(stop_timeout_s)
            or not 0 < stop_timeout_s <= 60
        ):
            raise CheckpointHostError("bounded STOP timeout required")
        stop_audit_dir = Path(stop_audit_dir)
        if stop_audit_dir.is_symlink() or not stop_audit_dir.is_dir():
            raise CheckpointHostError("preexisting STOP evidence directory required")
        self.runtime = runtime
        self.physical = physical
        self.cognitive_cohort = cognitive_cohort
        self.participants_now = participants_now
        self.stop_audit_dir = stop_audit_dir
        self.owned_paper = owned_paper
        self.prepare_native_rejoin = prepare_native_rejoin
        self.stop_timeout_s = float(stop_timeout_s)
        self.stop_parallel_workers = require_bounded_workers(stop_parallel_workers)
        self.rejoin_parallel_workers = require_bounded_workers(rejoin_parallel_workers)
        self.clock = monotonic_clock
        self.sleep = sleep
        self._cycle_active = False
        self._held = False
        self._last_poll: float | None = None

    @property
    def held_after_failure(self) -> bool:
        return self._held or self.runtime.held_after_failure

    def _participants(self) -> tuple[StopParticipant, ...]:
        members = self.participants_now()
        if (
            type(members) is not tuple
            or any(not isinstance(p, StopParticipant) for p in members)
            or tuple(p.self_id for p in sorted(members, key=lambda x: x.self_id))
            != self.physical.self_roster
        ):
            raise CheckpointHostError("native participant roster is incomplete")
        sessions: dict[str, str] = {}
        instance_ids: set[int] = set()
        for member in members:
            if id(member.session) in instance_ids:
                raise CheckpointHostError("duplicate native process handle")
            instance_ids.add(id(member.session))
            try:
                session_id = member.session.started.session_id
            except (AttributeError, ValueError) as exc:
                raise CheckpointHostError("native Self process has not started") from exc
            if type(session_id) is not str or not session_id.strip():
                raise CheckpointHostError("invalid native session receipt")
            sessions[member.self_id] = session_id
        if sessions != self.physical.current_native_sessions:
            raise CheckpointHostError("stale native session after Paper restart")
        for owner in self.cognitive_cohort.owners:
            if (
                owner.native_session_id != sessions[owner.self_id]
                or owner.fresh_native_observation_required
            ):
                raise CheckpointHostError(
                    "cognitive Self not ready in the current WorldBody session"
                )
        return tuple(sorted(members, key=lambda x: x.self_id))

    async def cycle_if_due(self, now_monotonic: float) -> HostCheckpointCycle | None:
        """First call saves immediately, subsequent successful cuts every 60s."""
        if self.held_after_failure or self._cycle_active:
            raise CheckpointHostError("host held or overlapping checkpoint pulse")
        if (
            type(now_monotonic) not in (int, float)
            or not math.isfinite(now_monotonic) or now_monotonic < 0
            or (self._last_poll is not None and now_monotonic < self._last_poll)
        ):
            raise CheckpointHostError("monotonic host clock invalid or regressed")
        self._last_poll = float(now_monotonic)
        if not self.runtime.timer.due(now_monotonic):
            return None
        self._cycle_active = True
        start = self.clock()
        try:
            if self.physical.closed:
                raise CheckpointHostError("physical admission already fenced")
            participants = self._participants()
            old_paper = None
            if self.owned_paper is not None:
                old_paper = self.owned_paper.owned_session_id
                if old_paper is None or self.owned_paper.held_uncertain:
                    raise CheckpointHostError("no healthy owned Paper process")
            stopped = await prepare_stop_before_autosave(
                self.physical, participants=participants,
                audit_dir=self.stop_audit_dir, timeout_s=self.stop_timeout_s,
                parallel_workers=self.stop_parallel_workers,
            )
            # Deliberately no await between full STOP and synchronous cognition/
            # world close/capture/restart. Other-process issuers still require
            # their own global gates and independent qualification.
            if self.prepare_native_rejoin is None:
                saved = self.runtime.run_if_due(now_monotonic)
            else:
                saved = await self.runtime.run_if_due_async(
                    now_monotonic, prepare_rejoin=self.prepare_native_rejoin,
                    rejoin_workers=self.rejoin_parallel_workers,
                )
            if (
                saved is None or not saved.typed_owner_cut_validated
                or saved.saved_self_ids != self.physical.self_roster
                or self.runtime.held_after_failure or self.physical.closed
                or saved.historical_replay_performed
                or saved.physical_action_issue_authorized
            ):
                raise CheckpointHostError("incomplete shared World/Self generation")
            verify_generation(saved.generation)
            new_paper = None
            if self.owned_paper is not None:
                new_paper = self.owned_paper.owned_session_id
                if (
                    new_paper is None or new_paper == old_paper
                    or self.owned_paper.held_uncertain
                ):
                    raise CheckpointHostError("fresh owned Paper session absent")
            return HostCheckpointCycle(
                stopped, saved, old_paper, new_paper, self.clock() - start,
            )
        except BaseException:
            self._held = True
            self.physical.hold_for_operator()
            raise
        finally:
            self._cycle_active = False

    async def run_bounded(
        self, *, max_cycles: int, max_polls: int = 100000,
        poll_seconds: float = 1.0,
    ) -> tuple[HostCheckpointCycle, ...]:
        """Explicitly awaited, bounded host runner. No background task."""
        if (
            type(max_cycles) is not int or not 1 <= max_cycles <= 1000
            or type(max_polls) is not int or not max_cycles <= max_polls <= 100000
            or type(poll_seconds) not in (int, float)
            or not math.isfinite(poll_seconds) or not 0 < poll_seconds <= 60
        ):
            raise CheckpointHostError("bounded explicit driver arguments required")
        done: list[HostCheckpointCycle] = []
        try:
            for _ in range(max_polls):
                cycle = await self.cycle_if_due(self.clock())
                if cycle is not None:
                    done.append(cycle)
                    if len(done) == max_cycles:
                        return tuple(done)
                await self.sleep(poll_seconds)
        except BaseException:
            self._held = True
            self.physical.hold_for_operator()
            raise
        self._held = True
        self.physical.hold_for_operator()
        raise CheckpointHostError("host poll budget exhausted without completed cuts")
