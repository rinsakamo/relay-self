"""#860 P0-D: opt-in synchronous autosave barrier for real runtime adapters.

This adapter orchestrates existing owners; it cannot itself stop Paper, verify
native processes, serialize all cognition, issue Actions, or confer recovery
qualification. The supplied hooks must implement those capabilities and return
strict per-cycle receipts. Failure leaves admission closed (manual recovery).
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path
from typing import Callable

from relay_self.coordinated_checkpoint_dev import (
    AutosaveGate,
    SelfSnapshotSource,
    capture_generation,
    latest_verified_generation,
    verify_generation,
)


class AutosaveBarrierError(RuntimeError):
    """Refuse a partial, stale or uncertified autosave boundary."""


def _ref(value: str) -> str:
    if type(value) is not str or not value.strip():
        raise AutosaveBarrierError("missing runtime receipt reference")
    return value


@dataclass(frozen=True, slots=True)
class AdmissionCloseReceipt:
    """Externally asserted issue fence; still needs live adapter qualification."""

    token: str
    physical_admission_closed: bool
    cognitive_admission_closed: bool
    communication_admission_closed: bool


@dataclass(frozen=True, slots=True)
class SelfFrozenReceipt:
    self_id: str
    snapshot: SelfSnapshotSource
    old_native_session_id: str
    freeze_ref: str
    physical_inflight_action_ids: tuple[str, ...]
    undelivered_message_ids: tuple[str, ...]
    writers_quiesced: bool
    issue_admission_closed: bool
    communication_quiesced: bool


@dataclass(frozen=True, slots=True)
class StoppedWorldReceipt:
    world_id: str
    branch_id: str
    old_server_session_id: str
    logical_tick: int
    tick_source_ref: str
    stopped_server_ref: str
    process_exit_code: int
    all_dimensions_saved: bool


@dataclass(frozen=True, slots=True)
class RestartedWorldReceipt:
    world_id: str
    branch_id: str
    new_server_session_id: str
    server_started: bool


@dataclass(frozen=True, slots=True)
class ReboundSelfReceipt:
    self_id: str
    new_native_session_id: str
    world_id: str
    branch_id: str
    old_session_invalidated: bool
    obsolete_gpu_tasks_fenced: bool
    stale_messages_discarded: bool
    issue_admission_closed: bool


@dataclass(frozen=True, slots=True)
class SelfRuntimeHooks:
    """Adapter-provided methods, not a new cognition or Action owner."""

    self_id: str
    freeze_and_flush: Callable[[str], SelfFrozenReceipt]
    rebind_after_world_restart: Callable[[str], ReboundSelfReceipt]


@dataclass(frozen=True, slots=True)
class WorldRuntimeHooks:
    stop_and_save: Callable[[], StoppedWorldReceipt]
    restart_same_source_world: Callable[[], RestartedWorldReceipt]


@dataclass(frozen=True, slots=True)
class AdmissionHooks:
    close: Callable[[], AdmissionCloseReceipt]
    release: Callable[[str], None]


@dataclass(frozen=True, slots=True)
class AutosaveCycleResult:
    generation: Path
    sequence: int
    saved_self_ids: tuple[str, ...]
    world_id: str
    branch_id: str
    physical_action_issue_authorized: bool = False
    historical_replay_performed: bool = False
    live_owner_restoration_attested: bool = False
    typed_owner_cut_validated: bool = False


def next_generation_sequence(store: Path) -> int:
    """Advance past incomplete generations, without deleting or reusing them."""
    root = Path(store)
    if root.is_symlink() or not root.is_dir():
        raise AutosaveBarrierError("checkpoint generation store unavailable")
    nums: list[int] = []
    for entry in root.iterdir():
        if not re.fullmatch(r"g-[0-9]{12}", entry.name):
            if entry.name.startswith("g-"):
                raise AutosaveBarrierError("unexpected generation name")
            continue
        if entry.is_symlink() or not entry.is_dir():
            raise AutosaveBarrierError("unsafe generation path")
        nums.append(int(entry.name[2:]))
    return max(nums, default=-1) + 1


class CoordinatedAutosaveRuntime:
    """Synchronous, externally polled runtime cut, never an independent issuer.

    In a real adapter, all admission gates must be fenced by the SAME owner,
    so a late L0 result cannot escape after close. Stage-1 file verification
    does not prove this; hooks are contract tests only until live-qualified.
    """

    def __init__(
        self, *, source_world: Path, store: Path, world_id: str,
        branch_id: str, participants: tuple[SelfRuntimeHooks, ...],
        world: WorldRuntimeHooks, admission: AdmissionHooks,
        strict_typed_owner_cut: bool = False,
        paper_layout: bool = False,
    ) -> None:
        if type(strict_typed_owner_cut) is not bool:
            raise AutosaveBarrierError("typed owner checkpoint flag must be bool")
        if type(paper_layout) is not bool:
            raise AutosaveBarrierError("Paper layout flag must be bool")
        self.paper_layout = paper_layout
        self.strict_typed_owner_cut = strict_typed_owner_cut
        if not participants or len({p.self_id for p in participants}) != len(participants):
            raise AutosaveBarrierError("expected distinct nonempty Self roster")
        if any(
            type(p.self_id) is not str
            or re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_-]{0,79}", p.self_id) is None
            for p in participants
        ):
            raise AutosaveBarrierError("invalid Self identity")
        _ref(world_id)
        _ref(branch_id)
        self.source_world = Path(source_world)
        self.store = Path(store)
        self.world_id = world_id
        self.branch_id = branch_id
        self.participants = tuple(sorted(participants, key=lambda p: p.self_id))
        self.world = world
        self.admission = admission
        self.timer = AutosaveGate()
        self._cycle_active = False
        self._held_after_failure = False
        self._last_server_session_id: str | None = None
        self._last_native_sessions: dict[str, str] = {}

    @property
    def held_after_failure(self) -> bool:
        return self._held_after_failure

    def run_if_due(self, now_monotonic: float) -> AutosaveCycleResult | None:
        if self._held_after_failure or self._cycle_active:
            raise AutosaveBarrierError("autosave held or already in progress")
        if not self.timer.due(now_monotonic):
            return None
        self._cycle_active = True
        try:
            # Timer only advances on independently verified committed generation.
            result: AutosaveCycleResult | None = None

            def capture() -> Path:
                nonlocal result
                result = self._cycle()
                return result.generation

            verified = self.timer.run_if_due(now_monotonic, capture)
            assert verified is not None and result is not None
            return result
        except Exception as exc:
            # No automatic release or World restart on uncertain outcomes.
            self._held_after_failure = True
            if isinstance(exc, AutosaveBarrierError):
                raise
            raise AutosaveBarrierError(
                "checkpoint failed; admission must remain held for operator review"
            ) from exc
        finally:
            self._cycle_active = False

    def _cycle(self) -> AutosaveCycleResult:
        close = self.admission.close()
        if (
            not isinstance(close, AdmissionCloseReceipt)
            or not (close.physical_admission_closed
                    and close.cognitive_admission_closed
                    and close.communication_admission_closed)
        ):
            raise AutosaveBarrierError("admission gate not fully closed")
        token = _ref(close.token)
        sequence = next_generation_sequence(self.store)
        generation_id = f"g-{sequence:012d}"
        cohort: list[SelfFrozenReceipt] = []
        for participant in self.participants:
            frozen = participant.freeze_and_flush(generation_id)
            if (
                not isinstance(frozen, SelfFrozenReceipt)
                or frozen.self_id != participant.self_id
                or frozen.snapshot.self_id != participant.self_id
                or not (frozen.writers_quiesced and frozen.issue_admission_closed
                        and frozen.communication_quiesced)
                or frozen.physical_inflight_action_ids
                or frozen.undelivered_message_ids
                or frozen.snapshot.owner_state_file is None
            ):
                raise AutosaveBarrierError("Self not fully frozen at generation cut")
            _ref(frozen.freeze_ref)
            _ref(frozen.old_native_session_id)
            previous = self._last_native_sessions.get(participant.self_id)
            if previous is not None and frozen.old_native_session_id != previous:
                raise AutosaveBarrierError("Self session changed without owner fencing")
            cohort.append(frozen)

        stopped = self.world.stop_and_save()
        if (
            not isinstance(stopped, StoppedWorldReceipt)
            or stopped.world_id != self.world_id
            or stopped.branch_id != self.branch_id
            or type(stopped.logical_tick) is not int
            or stopped.logical_tick < 0
            or type(stopped.process_exit_code) is not int
            or stopped.process_exit_code != 0
            or stopped.all_dimensions_saved is not True
        ):
            raise AutosaveBarrierError("Paper stopped World receipt invalid")
        _ref(stopped.old_server_session_id)
        if (self._last_server_session_id is not None
                and stopped.old_server_session_id != self._last_server_session_id):
            raise AutosaveBarrierError("Paper source session changed between cuts")
        _ref(stopped.tick_source_ref)
        _ref(stopped.stopped_server_ref)

        if self.strict_typed_owner_cut:
            from relay_self.self_owner_checkpoint_dev import (
                capture_typed_generation,
                verify_typed_generation,
            )

            capture_fn = capture_typed_generation
        else:
            capture_fn = capture_generation

        generation = capture_fn(
            self.source_world, self.store, sequence=sequence,
            expected_self_ids=tuple(p.self_id for p in self.participants),
            selves=tuple(f.snapshot for f in cohort),
            world_id=self.world_id, branch_id=self.branch_id,
            logical_tick=stopped.logical_tick,
            tick_source_ref=stopped.tick_source_ref,
            stopped_server_ref=stopped.stopped_server_ref,
            quiesced_selves_ref="cohort:" + generation_id + ":" + token,
            paper_layout=self.paper_layout,
        )
        verify_generation(generation)
        if self.strict_typed_owner_cut:
            verify_typed_generation(generation)

        restarted = self.world.restart_same_source_world()
        if (
            not isinstance(restarted, RestartedWorldReceipt)
            or not restarted.server_started
            or restarted.world_id != self.world_id
            or restarted.branch_id != self.branch_id
            or restarted.new_server_session_id == stopped.old_server_session_id
        ):
            raise AutosaveBarrierError("World restart receipt does not match saved branch")
        _ref(restarted.new_server_session_id)

        sessions: set[str] = set()
        new_native_sessions: dict[str, str] = {}
        for participant, frozen in zip(self.participants, cohort, strict=True):
            rebound = participant.rebind_after_world_restart(restarted.new_server_session_id)
            if (
                not isinstance(rebound, ReboundSelfReceipt)
                or rebound.self_id != participant.self_id
                or rebound.world_id != self.world_id
                or rebound.branch_id != self.branch_id
                or rebound.new_native_session_id == frozen.old_native_session_id
                or rebound.new_native_session_id in sessions
                or not (rebound.old_session_invalidated
                        and rebound.obsolete_gpu_tasks_fenced
                        and rebound.stale_messages_discarded
                        and rebound.issue_admission_closed)
            ):
                raise AutosaveBarrierError("Self is not ready for new native session")
            sessions.add(_ref(rebound.new_native_session_id))
            new_native_sessions[participant.self_id] = rebound.new_native_session_id

        # Release only after every Self is rebound, and never grants a stale Action.
        self.admission.release(token)
        self._last_server_session_id = restarted.new_server_session_id
        self._last_native_sessions = new_native_sessions
        return AutosaveCycleResult(
            generation=generation, sequence=sequence,
            saved_self_ids=tuple(p.self_id for p in self.participants),
            world_id=self.world_id, branch_id=self.branch_id,
            typed_owner_cut_validated=self.strict_typed_owner_cut,
        )

    def last_verified(self) -> Path | None:
        return latest_verified_generation(self.store)
