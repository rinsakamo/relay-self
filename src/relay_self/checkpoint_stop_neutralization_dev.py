"""#860 P0-D: supervised pre-save neutralization of ALL enrolled Self bodies.

This is an explicitly invoked async PRE-checkpoint phase. The existing
synchronous CoordinatedAutosaveRuntime subsequently calls the same physical
issuer's close() and will HOLD unless every Self has a qualified STOP proof.

It neither sends MOVE nor changes the default real Action/WAL authority.
It is not a substitute for Paper main-thread readback or world-wide fencing.
"""
from __future__ import annotations

import asyncio
import json
import math
import os
import re
import uuid
from dataclasses import dataclass
from pathlib import Path
from typing import Protocol

from adapters.mineflayer.python_protocol import (
    MineflayerEffectResult,
    MineflayerObservation,
)
from relay_self.cohort_parallel_barrier_dev import (
    require_bounded_workers,
    run_async_cohort_barrier,
)
from relay_self.physical_issue_admission_dev import (
    NeutralStopProof,
    PhysicalIssueAdmission,
    PhysicalIssueFenceError,
)


class StopNeutralizationError(RuntimeError):
    """STOP or its causal native readback was not independently established."""


class NeutralStopSession(Protocol):
    @property
    def started(self) -> object: ...

    async def send_clear_controls(self, action_id: str) -> None: ...

    async def send_observe(self, request_id: str | None = None) -> None: ...

    async def receive(self) -> object: ...


@dataclass(frozen=True, slots=True)
class StopParticipant:
    self_id: str
    session: NeutralStopSession


@dataclass(frozen=True, slots=True)
class StopCohortReady:
    fence_ref: str
    verified_self_ids: tuple[str, ...]
    receipt_files: tuple[Path, ...]
    physical_issue_blocked: bool = True
    checkpoint_committed: bool = False


def _exclusive_json(path: Path, value: dict[str, object]) -> None:
    """Durably reserve STOP evidence BEFORE ever writing a native effect."""
    if path.is_symlink() or path.parent.is_symlink() or not path.parent.is_dir():
        raise StopNeutralizationError("unsafe STOP audit path")
    data = (json.dumps(value, sort_keys=True, ensure_ascii=False, allow_nan=False)
            + "\n").encode()
    fd = os.open(path, os.O_CREAT | os.O_EXCL | os.O_WRONLY | os.O_NOFOLLOW, 0o600)
    try:
        buf = memoryview(data)
        while buf:
            n = os.write(fd, buf)
            if n <= 0:
                raise StopNeutralizationError("short STOP audit write")
            buf = buf[n:]
        os.fsync(fd)
    finally:
        os.close(fd)
    dfd = os.open(path.parent, os.O_DIRECTORY | os.O_RDONLY)
    try:
        os.fsync(dfd)
    finally:
        os.close(dfd)


async def _receive_matched(
    session: NeutralStopSession, *, session_id: str,
    kind: str, identity: str, timeout_s: float,
) -> MineflayerEffectResult | MineflayerObservation:
    deadline = asyncio.get_running_loop().time() + timeout_s
    for _ in range(512):
        left = deadline - asyncio.get_running_loop().time()
        if left <= 0:
            break
        try:
            entry = await asyncio.wait_for(session.receive(), timeout=left)
        except (TimeoutError, OSError, EOFError) as exc:
            raise StopNeutralizationError("native STOP evidence timed out or disconnected") from exc
        if not isinstance(entry, (MineflayerEffectResult, MineflayerObservation)):
            # Other native stream errors/connections must never look like STOP.
            raise StopNeutralizationError("unknown native message during STOP readback")
        if entry.session_id != session_id:
            raise StopNeutralizationError("foreign session native STOP observation")
        if isinstance(entry, MineflayerEffectResult):
            if (
                kind == "stop_ack" and entry.action_id == identity
                and entry.effect == "clear_controls"
            ):
                return entry
            raise StopNeutralizationError("unmatched native physical effect during STOP")
        if entry.kind == "probe":
            if kind == "probe" and entry.request_id == identity:
                return entry
            raise StopNeutralizationError("unmatched probe stream during STOP")
        # Passive move/health/time events may interleave with the single STOP
        # owner. They do not themselves establish stillness.
    raise StopNeutralizationError("STOP evidence horizon exhausted")


async def _stop_one(
    admission: PhysicalIssueAdmission,
    participant: StopParticipant,
    fence_ref: str,
    audit_dir: Path,
    timeout_s: float,
) -> Path:
    sid = participant.self_id
    session = participant.session
    native = session.started.session_id
    action_id = f"checkpoint-stop-{uuid.uuid4().hex}"
    audit_stem = f"stop-{sid}-{fence_ref}-{action_id}"
    prepared_path = audit_dir / (audit_stem + ".prepared.json")
    completed_path = audit_dir / (audit_stem + ".verified.json")
    try:
        with admission.stop_lease(
            fence_ref=fence_ref, self_id=sid,
            native_session_id=native, stop_action_id=action_id,
        ):
            _exclusive_json(prepared_path, {
                "schema": 1, "state": "PREPARED_UNRESOLVED",
                "self_id": sid, "fence_ref": fence_ref,
                "native_session_id": native, "stop_action_id": action_id,
            })
            await session.send_clear_controls(action_id)
            ack = await _receive_matched(
                session, session_id=native, kind="stop_ack",
                identity=action_id, timeout_s=timeout_s,
            )
            assert isinstance(ack, MineflayerEffectResult)
            if ack.result != "applied":
                raise StopNeutralizationError("clear_controls native ACK rejected")

            first_id = f"checkpoint-first-{uuid.uuid4().hex}"
            await session.send_observe(first_id)
            first = await _receive_matched(
                session, session_id=native, kind="probe",
                identity=first_id, timeout_s=timeout_s,
            )
            assert isinstance(first, MineflayerObservation)
            if first.snapshot.time is None:
                raise StopNeutralizationError("World clock missing from first STOP probe")

            # Allow real Minecraft residual displacement after STOP ACK.
            # Demand one additional stable >=8-tick interval after an initial
            # >=8-tick settling window. Shift the reference forward on drift;
            # a perpetually moving body may NEVER be checkpoint-committed.
            deadline = asyncio.get_running_loop().time() + timeout_s
            initial = first
            initial_time = (
                first.snapshot.time.day * 24000
                + first.snapshot.time.time_of_day
            )
            baseline = first
            baseline_tick = initial_time
            last: MineflayerObservation | None = None
            initial_window_elapsed = False
            while asyncio.get_running_loop().time() < deadline:
                await asyncio.sleep(0.05)
                later_id = f"checkpoint-settle-{uuid.uuid4().hex}"
                await session.send_observe(later_id)
                row = await _receive_matched(
                    session, session_id=native, kind="probe",
                    identity=later_id, timeout_s=max(
                        0.001, deadline - asyncio.get_running_loop().time(),
                    ),
                )
                assert isinstance(row, MineflayerObservation)
                if row.snapshot.time is None:
                    raise StopNeutralizationError("World clock missing during settling")
                now = row.snapshot.time.day * 24000 + row.snapshot.time.time_of_day
                if now < baseline_tick or now - initial_time > 200:
                    raise StopNeutralizationError("STOP World clock regressed/jumped")
                if not initial_window_elapsed:
                    if now - initial_time >= 8:
                        initial_window_elapsed = True
                        baseline = row
                        baseline_tick = now
                    continue
                if now - baseline_tick < 8:
                    continue
                p0, p1 = baseline.snapshot.position, row.snapshot.position
                displacement = math.dist(
                    (p0.x, p0.y, p0.z), (p1.x, p1.y, p1.z),
                )
                if math.isfinite(displacement) and displacement <= 0.06:
                    first = baseline
                    last = row
                    break
                baseline = row
                baseline_tick = now
            if last is None:
                raise StopNeutralizationError(
                    "STOP body never settled for 8 World ticks after initial wait"
                )
            then = (
                first.snapshot.time.day * 24000 + first.snapshot.time.time_of_day
            )
            proof = NeutralStopProof(action_id, ack, initial, first, last)
            admission.confirm_neutral_stop(
                fence_ref=fence_ref, self_id=sid, proof=proof,
            )
            _exclusive_json(completed_path, {
                "schema": 1, "state": "NEUTRAL_SETTLED_DEV",
                "self_id": sid, "fence_ref": fence_ref,
                "native_session_id": native, "stop_action_id": action_id,
                "ack_seq": ack.seq, "initial_probe_seq": initial.seq,
                "first_probe_seq": first.seq,
                "settled_probe_seq": last.seq,
                "initial_request_id": initial.request_id,
                "first_request_id": first.request_id,
                "settled_request_id": last.request_id,
                "initial_world_tick": initial_time,
                "first_world_tick": then, "settled_world_tick": now,
                "first_position": {
                    "x": first.snapshot.position.x,
                    "y": first.snapshot.position.y,
                    "z": first.snapshot.position.z,
                },
                "settled_position": {
                    "x": last.snapshot.position.x,
                    "y": last.snapshot.position.y,
                    "z": last.snapshot.position.z,
                },
            })
    except (OSError, ValueError, PhysicalIssueFenceError, asyncio.TimeoutError) as exc:
        raise StopNeutralizationError("STOP uncertain; global admission remains held") from exc
    return completed_path


async def prepare_stop_before_autosave(
    admission: PhysicalIssueAdmission, *,
    participants: tuple[StopParticipant, ...],
    audit_dir: Path, timeout_s: float = 8.0,
    parallel_workers: int = 1, total_timeout_s: float = 60.0,
) -> StopCohortReady:
    """Fence normal physical effects, then neutralize every fixed Self.

    The caller must invoke the SAME admission object's close() through the
    preexisting CognitionOwnerCohort as the next step; no physical issue may be
    admitted in between. On error: no release/retry/Checkpoint COMMIT.
    """
    if (
        not isinstance(admission, PhysicalIssueAdmission)
        or not admission.requires_neutral_stop
        or type(participants) is not tuple or not participants
        or type(timeout_s) not in (int, float) or not 0 < timeout_s <= 60
        or type(total_timeout_s) not in (int, float)
        or not math.isfinite(total_timeout_s)
        or not 0 < total_timeout_s <= 60
        or type(parallel_workers) is not int
        or not 1 <= parallel_workers <= 64
        or not Path(audit_dir).is_dir()
        or Path(audit_dir).is_symlink()
    ):
        raise StopNeutralizationError("invalid STOP cohort preflight")
    ordered = tuple(sorted(participants, key=lambda p: p.self_id))
    roster = tuple(p.self_id for p in ordered)
    if (
        len(set(roster)) != len(roster)
        or any(re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_-]{0,79}", sid) is None
               for sid in roster)
        or roster != admission.self_roster
    ):
        raise StopNeutralizationError("STOP roster must match full physical Self cohort")
    # No asynchronous wait before initial physical closure: no new user Action
    # can acquire a lease between roster validation and this closed transition.
    fence_ref = admission.begin_neutralization()
    try:
        # Crash-safe STOP audit check. Any earlier PREPARED without the
        # corresponding verified receipt can mean native STOP was applied
        # while the host lost its evidence. Never silently erase/retry it.
        for prepared in Path(audit_dir).glob("stop-*.prepared.json"):
            if (
                prepared.is_symlink()
                or not prepared.with_name(
                    prepared.name.removesuffix(".prepared.json") + ".verified.json"
                ).is_file()
            ):
                raise StopNeutralizationError(
                    "earlier STOP PREPARED_UNRESOLVED requires operator recovery"
                )
        # Workers share exactly one pre-closed physical epoch. STOP leases
        # remain disjoint per Self; no worker may save World or release.
        # The barrier joins *every* result before cognition/World cut.
        async def stop_member(participant: StopParticipant) -> Path:
            return await _stop_one(
                admission, participant, fence_ref, Path(audit_dir), timeout_s,
            )

        files = await run_async_cohort_barrier(
            ordered, stop_member, workers=require_bounded_workers(parallel_workers),
            total_timeout_s=total_timeout_s,
        )
        if not admission.neutralization_complete:
            raise StopNeutralizationError("not all Self STOP proofs verified")
    except BaseException:
        # Even a failed final evidence-file fsync after a valid ACK means HOLD.
        # Includes CancelledError / KeyboardInterrupt; never auto-resume.
        admission.abort_neutralization()
        raise
    return StopCohortReady(fence_ref, roster, tuple(files))
