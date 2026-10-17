"""FLAT S50→P1 movement-only source bridge (strictly DEV candidate).

Read the ORIGINAL Paper PlayerMoveEvent distance witnesses against the
archived S50 Action/STOP report.  This bridge cannot classify unobserved
World ticks, cannot emit SourceBoundTick or mutate the P1 Body state.
P1 owner #626 retains the physics semantics, R #575 the independent audit.
"""
from __future__ import annotations

import hashlib
import json
import math
from pathlib import Path

from adapters.mineflayer.m02_paper_dev.s50_boundary import (
    BoundaryRejected, integer, number, rows,
)
from adapters.mineflayer.m02_paper_dev.v7_paired_config import (
    ARMS, TEMPLATE, render_arm,
)

MOTION_PREFIX = "M02_DEV_MOTION "
P1_DRAFT_MOVE_PER_BLOCK = 0.04  # Illustrative Draft #626 default only.
MAX_LOGGED_MOTION = 300
KNOWN_SEED = "63101"


def _close(a: float, b: float) -> bool:
    return math.isclose(a, b, abs_tol=1e-9, rel_tol=1e-8)


def screen_motion(original_console: str, report: dict, *, arm: str) -> dict:
    """Screen positive movement for later P1 owner admission; no recovery."""
    if (arm not in ARMS or not isinstance(report, dict)
            or report.get("arm") != arm
            or report.get("mode") != "FLAT_DEV_ONLY"
            or report.get("status") != "PASS"
            or report.get("cleanup_complete") is not True
            or report.get("original_unchanged") is not True
            or report.get("science_trials") != 0
            or report.get("engineering_qualified") is not False):
        raise BoundaryRejected("foreign/nonterminal FLAT DEV source")
    initial = report.get("initial_server_marker")
    terminal = report.get("terminal_server_marker")
    if not isinstance(initial, dict) or not isinstance(terminal, dict):
        raise BoundaryRejected("missing first/last native Paper marker")
    if (initial.get("seed") != KNOWN_SEED
            or terminal.get("seed") != KNOWN_SEED
            or not initial.get("world")
            or terminal.get("world") != initial["world"]
            or initial.get("x") != "0.5"
            or initial.get("y") != "-60.0"
            or initial.get("z") != "0.5"):
        raise BoundaryRejected("foreign Paper World, seed or start pose")
    start = integer(initial, "full_time")
    end = integer(terminal, "full_time")
    if end <= start or not _close(number(initial, "motion_blocks"), 0.0):
        raise BoundaryRejected("invalid initial native motion/time")
    config_sha = hashlib.sha256(render_arm(TEMPLATE.read_bytes(), arm)).hexdigest()
    if (report.get("config_sha256") != config_sha
            or report.get("basal_multiplier") != ARMS[arm][0]
            or report.get("walk_multiplier") != ARMS[arm][1]):
        raise BoundaryRejected("M0.2 arm profile not source-matched")
    trace = report.get("foraging")
    if (not isinstance(trace, dict)
            or trace.get("status") != "PICKUP_SOURCE_CONSISTENT"
            or not isinstance(trace.get("movement_outcomes"), list)
            or len(trace["movement_outcomes"]) != 2
            or [x.get("kind") for x in trace["movement_outcomes"]]
            != ["PROGRESSED", "ARRIVED"]
            or any(x.get("terminal") != "outcome"
                   for x in trace["movement_outcomes"])
            or report.get("eating") is None):
        raise BoundaryRejected("no existing S50/S51 Action closure")
    meter = report.get("metabolism_source")
    if not isinstance(meter, dict) or meter.get("motion_log_cap") != MAX_LOGGED_MOTION:
        raise BoundaryRejected("missing native Paper motion meter scope")
    entries = rows(original_console, MOTION_PREFIX)
    if (not entries or len(entries) > MAX_LOGGED_MOTION
            or len(entries) != meter.get("motion_logged_rows")):
        raise BoundaryRejected("native motion log truncated, absent or capped")
    total_blocks = 0.0
    total_billed = 0.0
    by_tick: dict[int, dict] = {}
    prev_tick = start
    for sequence, entry in enumerate(entries, 1):
        stamp = integer(entry, "world_full_time")
        if (integer(entry, "id") != sequence
                or stamp < prev_tick or stamp > end
                or entry.get("world") != initial["world"]
                or entry.get("reason") != "WALK"
                or entry.get("marker_id") is None):
            raise BoundaryRejected("duplicate/reordered/foreign native motion row")
        dx = number(entry, "to_x") - number(entry, "from_x")
        dz = number(entry, "to_z") - number(entry, "from_z")
        observed = math.hypot(dx, dz)
        blocks = number(entry, "blocks")
        billed = number(entry, "billed")
        if (blocks <= 0 or blocks > 1.0
                or billed < 0
                or not _close(observed, blocks)
                or not _close(billed, blocks * 0.01 * ARMS[arm][1])):
            raise BoundaryRejected("native horizontal motion or WALK bill inconsistent")
        total_blocks += blocks
        total_billed += billed
        if (not _close(total_blocks, number(entry, "cumulative_blocks"))
                or not _close(total_billed, number(entry, "cumulative_billed"))):
            raise BoundaryRejected("native motion cumulative counter disagrees")
        row = by_tick.setdefault(stamp, {"world_full_time": stamp,
                                          "event_count": 0, "event_blocks": 0.0})
        row["event_count"] += 1
        row["event_blocks"] += blocks
        prev_tick = stamp
    if (not _close(total_blocks, number(terminal, "motion_blocks"))
            or not _close(total_billed, number(terminal, "motion_billed"))
            or not _close(total_blocks, meter.get("motion_blocks"))
            or not _close(total_billed, meter.get("motion_billed"))):
        raise BoundaryRejected("native source aggregate not at terminal snapshot")
    # No source for other Paper ticks is supplied here. Treat silence as UNKNOWN,
    # never WAIT: a sparse callback list cannot create free P1 recovery.
    return {
        "classification": "S_FLAT_P1_MOTION_SOURCE_CANDIDATE_DEV_ONLY",
        "arm": arm,
        "flat_world_seed": 63101,
        "world": initial["world"],
        "start_full_time": start,
        "terminal_full_time": end,
        "native_motion_events": len(entries),
        "native_moving_tick_count": len(by_tick),
        "tick_event_groups": list(by_tick.values()),
        "native_observed_horizontal_blocks": total_blocks,
        "native_billed_walk_exhaustion": total_billed,
        "hypothetical_P1_draft_move_rate": P1_DRAFT_MOVE_PER_BLOCK,
        "hypothetical_P1_motion_gain_unadmitted": total_blocks * P1_DRAFT_MOVE_PER_BLOCK,
        "physical_full_tick_source_authenticated": False,
        "move_SourceBoundTick_issued": False,
        "P1_state_advanced": False,
        "unobserved_ticks": "UNKNOWN_NOT_WAIT",
        "wait_SourceBoundTick_issued": False,
        "p1_wait_ticks_admitted": 0,
        "p1_fatigue_recovered": 0.0,
        "R_independent_review": "PENDING",
        "science_trials": 0,
        "production_go": False,
    }


def read_archived_original(root: Path, *, arm: str) -> dict:
    """Bounded provenance check of an unmodified S ORIGINAL directory."""
    if not root.is_dir() or root.is_symlink():
        raise BoundaryRejected("source root not a real folder")
    manifest_path = root / "sha256.json"
    report_path = root / "report.json"
    console_path = root / "paper_server.log"
    if any(not p.is_file() or p.is_symlink()
           for p in (manifest_path, report_path, console_path)):
        raise BoundaryRejected("missing or symlinked source original")
    if (manifest_path.stat().st_size > 2_000_000
            or report_path.stat().st_size > 2_000_000
            or console_path.stat().st_size > 25_000_000):
        raise BoundaryRejected("source original exceeds bounded read")
    manifest = json.loads(manifest_path.read_text())
    if not isinstance(manifest, dict):
        raise BoundaryRejected("invalid original manifest")
    for file in (report_path, console_path):
        expected = manifest.get(file.name)
        if (not isinstance(expected, str) or len(expected) != 64
                or hashlib.sha256(file.read_bytes()).hexdigest() != expected):
            raise BoundaryRejected("original file SHA not matched")
    result = screen_motion(console_path.read_text(), json.loads(report_path.read_text()),
                           arm=arm)
    result["original_report_sha256"] = manifest["report.json"]
    result["original_console_sha256"] = manifest["paper_server.log"]
    return result
