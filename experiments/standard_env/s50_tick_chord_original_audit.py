"""Independent R original Paper S50 tick-chord billing inspection, DEV only.

Uses neither S-owned parsers nor S-reported totals. It measures *tick chords*
(lower bounds), never continuous paths, ecology, P1 WAIT or qualification.
"""
from __future__ import annotations

import hashlib
import json
import math
from pathlib import Path
from typing import Any

ARMS = {
    "BASE_ON": (0.001, 0.01), "SHAM_ON": (0.001, 0.01),
    "BASAL_ZERO": (0.0, 0.01), "WALK_ZERO": (0.001, 0.0),
    "BOTH_ZERO": (0.0, 0.0),
}
CLASS = "R_S50_TICK_CHORD_NEW_JAR_DEV_ORIGINAL_REVIEW_ONLY"


class InvalidSource(ValueError):
    pass


def need(test: bool, why: str) -> None:
    if not test:
        raise InvalidSource(why)


def kv(raw: str, prefix: str) -> list[dict[str, str]]:
    out = []
    for line in raw.splitlines():
        if prefix not in line:
            continue
        tokens = [x.split("=", 1) for x in line.split(prefix, 1)[1].split()]
        need(all(len(x) == 2 and x[0] for x in tokens), "bad source token")
        row = dict(tokens)
        need(len(row) == len(tokens), "duplicate source field")
        out.append(row)
    return out


def number(row: dict, name: str) -> float:
    try:
        n = float(row[name])
    except (KeyError, TypeError, ValueError) as exc:
        raise InvalidSource("missing numeric source: " + name) from exc
    need(math.isfinite(n), "nonfinite numeric source: " + name)
    return n


def integer(row: dict, name: str) -> int:
    n = number(row, name)
    need(n >= 0 and n == int(n), "invalid integer source: " + name)
    return int(n)


def position(row: dict, prefix: str = "") -> tuple[float, float, float]:
    return tuple(number(row, prefix + ax) for ax in ("x", "y", "z"))


def close(a: float, b: float, tol: float = 1e-7) -> bool:
    return abs(a - b) <= tol


def review_paper_source(raw: bytes, arm: str, marker: str) -> dict[str, Any]:
    """Review complete independent Paper source content for *one* Action."""
    need(type(raw) is bytes and 0 < len(raw) <= 12 * 1024 * 1024,
         "missing/oversized Paper original")
    need(arm in ARMS and type(marker) is str and 8 <= len(marker) <= 256
         and " " not in marker, "unregistered original arm/marker")
    try:
        content = raw.decode("utf-8")
    except UnicodeError as exc:
        raise InvalidSource("nonUTF8 Paper original") from exc
    phase = kv(content, "M02_DEV_S50_PHASE ")
    need(len(phase) == 4
         and [x.get("phase") for x in phase]
         == ["PRE_FORWARD", "POST_FORWARD", "PRE_CLEAR", "POST_CLEAR"],
         "missing/duplicate/order of source phase")
    world = phase[0].get("world")
    need(world and all(x.get("world") == world
                       and x.get("marker_id") == marker for x in phase),
         "foreign marker/world")
    times = [integer(x, "world_full_time") for x in phase]
    need(all(b >= a for a, b in zip(times, times[1:])),
         "regressing Paper phase time")
    arm_rows = kv(content, "S50_DEV_TICK_METER_ARM ")
    need(len(arm_rows) == 1 and arm_rows[0].get("marker_id") == marker
         and arm_rows[0].get("world") == world
         and integer(arm_rows[0], "world_full_time") == times[0],
         "no unique armed native meter/first phase")
    last_pose = position(arm_rows[0])
    need(math.dist(last_pose, position(phase[0])) <= 1e-8,
         "arming pose not at first phase")
    meter = kv(content, "S50_DEV_TICK_MOTION ")
    need(6 <= len(meter) <= 500, "absent/unbounded World tick chord evidence")
    expected_rate = ARMS[arm][1]
    full_time = times[0]
    total_distance = total_charge = 0.0
    unique_world_ticks: set[int] = set()
    by_tick: dict[int, tuple[tuple[float, float, float], float, float]] = {}
    moving = 0
    for idx, row in enumerate(meter, 1):
        tick = integer(row, "world_full_time")
        need(row.get("world") == world and row.get("marker_id") == marker
             and integer(row, "id") == idx
             and (tick in (full_time, full_time + 1) if idx == 1
                  else tick == full_time + 1)
             and tick not in unique_world_ticks,
             "missing/duplicate/foreign World tick writer")
        unique_world_ticks.add(tick)
        first, second = position(row, "from_"), position(row, "to_")
        need(math.dist(first, last_pose) <= 1e-8,
             "discontinuous real World pose")
        chord = math.hypot(second[0] - first[0], second[2] - first[2])
        charge = number(row, "billed")
        need(0 <= chord <= 1 and abs(first[1] - second[1]) <= .5
             and close(number(row, "blocks"), chord, 1e-8)
             and close(charge, chord * expected_rate, 1e-8),
             "source chord / billed walk mismatch")
        total_distance += chord
        total_charge += charge
        need(close(number(row, "cumulative_blocks"), total_distance)
             and close(number(row, "cumulative_billed"), total_charge)
             and close(number(row, "write_target"),
                       number(row, "write_before") + charge, 1e-6)
             and close(number(row, "write_after"),
                       number(row, "write_target"), 2e-6),
             "native setter input/readback or cumulative corrupted")
        last_pose, full_time = second, tick
        by_tick[tick] = (second, total_distance, total_charge)
        moving += chord > 0
    need(moving > 0, "zero observed physical movement")
    ticks = kv(content, "S50_DEV_TICK ")
    need(len(ticks) >= 6, "missing independent tick snapshots")
    tick_serial = []
    for sample in ticks:
        t = integer(sample, "tick")
        need(sample.get("world") == world
             and sample.get("marker_id") == marker
             and t in by_tick
             and (not tick_serial or t == tick_serial[-1] + 1),
             "foreign/gapped tick snapshot")
        tick_serial.append(t)
        to, walked, spent = by_tick[t]
        need(math.dist(position(sample), to) <= 1e-8
             and close(number(sample, "tick_meter_blocks"), walked)
             and close(number(sample, "tick_meter_billed"), spent),
             "tick snapshot/meter mismatch")
    quiet = [x for x in ticks if integer(x, "tick") > times[-1]]
    observed_quiet = False
    for end in range(5, len(quiet)):
        span = quiet[end-5:end+1]
        values = [(position(x), number(x, "packets"),
                   number(x, "blocks"), number(x, "billed")) for x in span]
        if len(set(values)) == 1:
            observed_quiet = True
            break
    need(observed_quiet, "no source-observed bounded quiet window")
    events = kv(content, "M02_DEV_MOTION ")
    need(len(events) >= 1
         and all(x.get("world") == world and x.get("marker_id") == marker
                 and integer(x, "id") == i
                 and close(number(x, "billed"), 0, 1e-12)
                 and close(number(x, "cumulative_billed"), 0, 1e-12)
                 for i, x in enumerate(events, 1)),
         "event double billing or foreign packet event")
    event_distance = sum(number(x, "blocks") for x in events)
    need(event_distance <= total_distance + 1e-7,
         "event path exceeds tick chord lower bound")
    return {
        "classification": CLASS,
        "arm": arm, "world": world, "marker_id": marker,
        "raw_paper_sha256": hashlib.sha256(raw).hexdigest(),
        "native_tick_rows": len(meter),
        "first_meter_tick": min(unique_world_ticks),
        "last_meter_tick": max(unique_world_ticks),
        "source_tick_chord_blocks_lower_bound": total_distance,
        "walk_native_exhaustion_setter_input": total_charge,
        "source_walk_exhaustion_per_chord_block": total_charge / total_distance,
        "event_observed_blocks_not_billed": event_distance,
        "event_native_double_billing": False,
        "bounded_quiet_window_observed": True,
        "continuous_subtick_path_attested": False,
        "world_action_control_effective_timing_attested": False,
        "native_hunger_net_cost_attested": False,
        "engineering_qualified": False, "science_go": False,
    }


def review_files(root: Path, arm: str) -> dict[str, Any]:
    """Cross-check S original file digests and independently computed source."""
    need(root.is_absolute() and root.is_dir() and not root.is_symlink()
         and all(not p.is_symlink() for p in root.parents),
         "unsafe evidence root")
    required = ("paper_server.log", "original_native.jsonl",
                "owner_commands.jsonl", "s50_action_original.jsonl",
                "initial_world_level.dat", "m02_report.json",
                "relay-metabolism-paper-dev.jar")
    originals: dict[str, bytes] = {}
    for name in required:
        files = [p for p in root.rglob(name) if p.is_file() and not p.is_symlink()
                 and all(not q.is_symlink() for q in p.parents)]
        need(len(files) == 1, "missing/ambiguous native original " + name)
        originals[name] = files[0].read_bytes()
        need(bool(originals[name]), "empty original " + name)
    report = json.loads(originals["m02_report.json"])
    need(type(report) is dict
         and report.get("classification") == "M02_PAPER_DEV_ONLY_PHYSICS_OBSERVED"
         and report.get("status") == "PASS"
         and report.get("owner_status") == "PASS"
         and report.get("v7_arm") == arm
         and report.get("v7_seed") == 61021
         and report.get("qualified") is False
         and report.get("science_go") is False
         and report.get("production_go") is False,
         "S DEV-only report identity/classification invalid")
    for key in required[:5]:
        expected = (report.get("evidence_hashes") or {}).get(key)
        if key == "initial_world_level.dat":
            expected = (report.get("initial_world_receipt") or {}).get("sha256")
        need(expected == hashlib.sha256(originals[key]).hexdigest(),
             "source report digest mismatch " + key)
    need(report.get("plugin_sha256")
         == hashlib.sha256(originals["relay-metabolism-paper-dev.jar"]).hexdigest(),
         "new JAR digest not proven")
    movement = report.get("movement")
    need(type(movement) is dict and movement.get("action_state") == "outcome",
         "missing genuine issued/closed Action")
    session, action = movement.get("source_session"), movement.get("action_id")
    need(type(session) is str and session
         and type(action) is str and action, "missing Action/session")
    marker = action + "-" + session
    need(movement.get("v7_phase_marker_id") == marker,
         "Action marker not source bound")
    native = [json.loads(row) for row in originals["original_native.jsonl"].splitlines()]
    commands = [json.loads(row) for row in originals["owner_commands.jsonl"].splitlines()]
    journal = [json.loads(row) for row in originals["s50_action_original.jsonl"].splitlines()]
    need(len(journal) == 2
         and [x.get("state") for x in journal] == ["issued", "outcome"]
         and all(x.get("action_id") == action
                 and x.get("session_id") == session for x in journal)
         and len(native) > 10
         and [x.get("seq") for x in native] == list(range(len(native)))
         and all(x.get("session_id") == session for x in native)
         and native[-2].get("type") == "shutdown_ack"
         and native[-1].get("type") == "connection_end"
         and len([x for x in commands if x.get("type") == "shutdown"]) == 1
         and report.get("node_exit") == 0 and report.get("java_exit") == 0
         and report.get("port_released_after_shutdown") is True,
         "raw Action journal/native STOP or host report fails")
    out = review_paper_source(originals["paper_server.log"], arm, marker)
    need(close(out["source_tick_chord_blocks_lower_bound"],
               (report.get("s50_tick_chord_source") or {}).get(
                   "native_horizontal_path_blocks", -99), 1e-7)
         if isinstance(report.get("s50_tick_chord_source"), dict)
         else True,
         "producer and independent motion source differ")
    out.update({
        "paper_plugin_source_sha256": report["plugin_sha256"],
        "java_node_reported_exit_zero": True,
        "port_release_report_only": True,
        "native_stop_ack": True,
        "source_action_outcome": True,
        "initial_world_source_sha256":
            hashlib.sha256(originals["initial_world_level.dat"]).hexdigest(),
        "independently_witnessed_pid_cleanup": False,
        "original_zip_bytes_independently_attested_here": False,
        "qualification_grant_consumed": False,
    })
    return out
