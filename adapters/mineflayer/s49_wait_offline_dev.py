"""Offline DEV-only S49 owner/S50 Paper source projection, not R attestation.

Caller supplies the existing sole S49 DEV Executor and captured source streams.
No new Action issuer, Paper clock, World access or P1 recovery is introduced.
"""
from __future__ import annotations

import asyncio
import hashlib
import json
import os
from pathlib import Path

from adapters.mineflayer.m02_paper_dev.s50_boundary import BoundaryRejected
from adapters.mineflayer.m02_paper_dev.s50_p1_wait_joint_dev import review_joint_wait_sources
from adapters.mineflayer.s49_wait_fenced_executor_dev import S49WaitFencedExecutorDev

SCHEMA = "S49_S50_OFFLINE_PROJECTION_DEV_V1"


def _digest(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def _paper_rows(raw: str, *, marker: str, world: str, first: int) -> tuple:
    """Project exactly eight original-line hashes; never claim tick completeness."""
    samples = []
    for line in raw.splitlines():
        if not line.startswith("S50_DEV_WAIT_TICK "):
            continue
        data = {}
        for part in line.split()[1:]:
            if "=" not in part:
                raise BoundaryRejected("malformed Paper tick line")
            k, v = part.split("=", 1)
            if not k or not v or k in data:
                raise BoundaryRejected("duplicate/empty Paper tick field")
            data[k] = v
        if data.get("marker_id") != marker or data.get("world") != world:
            raise BoundaryRejected("foreign Paper tick source")
        try:
            tick = int(data["tick"])
            index = int(data["index"])
        except (KeyError, ValueError) as exc:
            raise BoundaryRejected("missing Paper tick identity") from exc
        if (index != len(samples) + 1
                or tick != first + len(samples) or index > 8):
            raise BoundaryRejected("missing/reordered/extra Paper tick")
        samples.append((tick, "paper-line-sha256:" + _digest(line)))
    if len(samples) != 8:
        raise BoundaryRejected("eight Paper callback samples required")
    return tuple(samples)


def _write_once(path: Path, report: dict) -> None:
    if (not isinstance(path, Path) or not path.is_absolute()
            or not path.parent.is_dir() or path.parent.is_symlink()
            or os.path.lexists(path)):
        raise BoundaryRejected("fresh absolute DEV report path required")
    raw = (json.dumps(report, sort_keys=True, allow_nan=False, indent=2)
           + "\n").encode()
    fd = os.open(
        path, os.O_WRONLY | os.O_CREAT | os.O_EXCL
        | getattr(os, "O_NOFOLLOW", 0), 0o600,
    )
    try:
        with os.fdopen(fd, "wb") as f:
            f.write(raw)
            f.flush()
            os.fsync(f.fileno())
    except BaseException:
        path.unlink(missing_ok=True)
        raise


async def run_s49_s50_offline_dev(
    executor: S49WaitFencedExecutorDev, sources: tuple, *,
    prior_action_id: str, output_path: Path,
) -> dict:
    """Cross-screen one provided Action and eight raw Paper lines; save once.

    Source bytes are caller input, so even PASS cannot attest real World ticks.
    """
    if (not isinstance(executor, S49WaitFencedExecutorDev)
            or not isinstance(sources, tuple) or len(sources) != 5
            or not isinstance(output_path, Path) or not output_path.is_absolute()
            or output_path.is_symlink() or os.path.lexists(output_path)
            or executor.wait_phase != "NEW"):
        raise BoundaryRejected("isolated fresh S49 DEV owner/input required")
    report = {
        "schema": SCHEMA, "status": "FAIL_CLOSED",
        "source_authentication": "UNATTESTED_CALLER_INPUT",
        "physical_clock_alignment": "NOT_ATTESTED",
        "qualification_go": False, "science_go": False,
        "wait_interval_ref": None, "source_bound_tick": None,
        "wait_ticks_admitted": 0, "p1_fatigue_recovered": 0.0,
        "input_hashes": None, "joint_screen": None, "owner_rows": [],
    }
    try:
        cross = review_joint_wait_sources(*sources)
        if (cross["session_id"] != executor.session_id
                or cross["action_id"] != prior_action_id):
            raise BoundaryRejected("S49 owner and S50 source mismatch")
        paper, native, commands, journal, movement = sources
        originals = _paper_rows(
            paper, marker=cross["marker_id"], world=cross["paper_world"],
            first=cross["first_world_tick"],
        )
        hashes = {
            "paper": _digest(paper),
            "native": _digest(json.dumps(native, sort_keys=True)),
            "commands": _digest(json.dumps(commands, sort_keys=True)),
            "journal": _digest(json.dumps(journal, sort_keys=True)),
            "movement": _digest(json.dumps(movement, sort_keys=True)),
        }
        executor.arm_after_original_outcome(
            closed_action_id=prior_action_id,
            terminal_outcome_ref="derived-dev-action:" + hashes["journal"],
            controls_clear_ref="derived-dev-command:" + hashes["native"],
        )

        async def samples():
            for tick, line_hash in originals:
                await asyncio.sleep(0)  # cancellation point, not World time
                yield tick, line_hash

        rows = await executor.screen_wait_samples(
            samples(), seal_source_ref="derived-dev-seal:" + hashes["paper"],
        )
        if any(rows[i + 1]["source_ref"] != pair[1]
               for i, pair in enumerate(originals)):
            raise BoundaryRejected("Paper source bytes did not match owner rows")
        final = review_joint_wait_sources(
            *sources, s49_owner_fence_rows=rows,
        )
        if final["wait_ticks_admitted"] or final["source_bound_tick"] is not None:
            raise BoundaryRejected("offline projection cannot admit WAIT")
        report["input_hashes"] = hashes
        report["joint_screen"] = final
        report["status"] = "OFFLINE_PROJECTION_ONLY"
    except BaseException as exc:
        report["status"] = ("CANCELLED_NOT_QUALIFIED" if isinstance(
            exc, asyncio.CancelledError,
        ) else "REJECTED_NOT_QUALIFIED")
        report["failure_type"] = type(exc).__name__
        if executor.wait_phase in {"ARMED", "SAMPLING", "ABORTED"}:
            executor.abort_wait(reason_source_ref="S49_OFFLINE_ABORT")
        report["owner_rows"] = list(executor.wait_original_rows)
        _write_once(output_path, report)
        raise
    report["owner_rows"] = list(executor.wait_original_rows)
    _write_once(output_path, report)
    return report
