"""S-owned DEV source reconciliation; correlation is not independent attestation.

No control, physiology writes, WAIT recovery or authorization lives here.
"""

from __future__ import annotations

import asyncio
import math
from pathlib import Path


class BoundaryRejected(ValueError):
    """Missing, foreign, duplicated or inconsistent original source."""


def rows(content: str, prefix: str) -> list[dict]:
    result = []
    for line in content.splitlines():
        if prefix not in line:
            continue
        pairs = [token.split("=", 1) for token in line.split(prefix, 1)[1].split()]
        if any(len(p) != 2 for p in pairs) or len(dict(pairs)) != len(pairs):
            raise BoundaryRejected("malformed or duplicate source fields")
        result.append(dict(pairs))
    return result


def number(row, key):
    try:
        value = float(row[key])
    except (KeyError, ValueError) as exc:
        raise BoundaryRejected("missing/invalid source number") from exc
    if not math.isfinite(value):
        raise BoundaryRejected("nonfinite source number")
    return value


def integer(row, key):
    value = number(row, key)
    if value < 0 or value != int(value):
        raise BoundaryRejected("invalid source counter")
    return int(value)


def pose(row, prefix=""):
    return tuple(number(row, prefix + a) for a in ("x", "y", "z"))


def phases(content, marker):
    found = rows(content, "M02_DEV_S50_PHASE ")
    if (
        len(found) != 4
        or [r.get("phase") for r in found]
        != ["PRE_FORWARD", "POST_FORWARD", "PRE_CLEAR", "POST_CLEAR"]
        or any(r.get("marker_id") != marker for r in found)
    ):
        raise BoundaryRejected("missing/foreign/duplicate phase source")
    if any(
        integer(b, "world_full_time") < integer(a, "world_full_time")
        for a, b in zip(found, found[1:])
    ):
        raise BoundaryRejected("regressed phase World time")
    return found


def quiet_window(content, marker):
    """Six native snapshots spanning five complete observed quiet intervals."""
    phase = phases(content, marker)
    world = phase[0].get("world")
    if not world or any(r.get("world") != world for r in phase):
        raise BoundaryRejected("foreign/missing World")
    ticks = rows(content, "S50_DEV_TICK ")
    for i, row in enumerate(ticks):
        if row.get("world") != world or row.get("marker_id") != marker:
            raise BoundaryRejected("foreign tick source")
        if i and integer(row, "tick") != integer(ticks[i - 1], "tick") + 1:
            raise BoundaryRejected("missing/duplicate/regressed World tick")
        pose(row)
        if i and (
            integer(row, "packets") < integer(ticks[i - 1], "packets")
            or number(row, "blocks") < number(ticks[i - 1], "blocks")
            or number(row, "billed") < number(ticks[i - 1], "billed")
        ):
            raise BoundaryRejected("regressed movement counters")
    after = [r for r in ticks if integer(r, "tick") > integer(phase[-1], "world_full_time")]
    for i in range(5, len(after)):
        window = after[i - 5 : i + 1]
        if all(
            (integer(r, "packets"), pose(r), number(r, "blocks"), number(r, "billed"))
            == (
                integer(window[0], "packets"),
                pose(window[0]),
                number(window[0], "blocks"),
                number(window[0], "billed"),
            )
            for r in window
        ):
            return phase, ticks, window
    return None


async def await_quiet(log: Path, marker: str):
    for _ in range(100):
        if not log.is_file():
            raise BoundaryRejected("World source disappeared")
        if quiet_window(log.read_text(), marker) is not None:
            return
        await asyncio.sleep(0.05)
    raise BoundaryRejected("no bounded native quiet interval; physical end NOT_ATTESTED")


def reconcile(content: str, movement: dict, *, walk_rate: float) -> dict:
    marker = movement["action_id"] + "-" + movement["source_session"]
    if movement["v7_phase_marker_id"] != marker:
        raise BoundaryRejected("Action/session mismatch")
    quiet = quiet_window(content, marker)
    if quiet is None:
        raise BoundaryRejected("quiet boundary NOT_ATTESTED")
    phase, ticks, window = quiet
    world = phase[0]["world"]
    packets = rows(content, "M02_DEV_MOTION ")
    start = pose(phase[0])
    previous = start
    distance = charge = 0.0
    last_tick = integer(phase[0], "world_full_time")
    post_clear = 0.0
    per_tick = {}
    for i, row in enumerate(packets, 1):
        tick = integer(row, "world_full_time")
        if (
            integer(row, "id") != i
            or row.get("marker_id") != marker
            or row.get("world") != world
            or row.get("reason") != "WALK"
            or not last_tick <= tick <= integer(window[-1], "tick")
        ):
            raise BoundaryRejected("foreign/late/duplicate/regressed motion")
        frm, to = pose(row, "from_"), pose(row, "to_")
        if math.dist(frm, previous) > 1e-7:
            raise BoundaryRejected("native coordinate discontinuity")
        blocks = math.hypot(to[0] - frm[0], to[2] - frm[2])
        billed = number(row, "billed")
        if (
            not 0 < blocks <= 1
            or abs(blocks - number(row, "blocks")) > 1e-8
            or abs(billed - blocks * walk_rate) > 1e-8
        ):
            raise BoundaryRejected("distance/billing mismatch")
        distance += blocks
        charge += billed
        if (
            abs(distance - number(row, "cumulative_blocks")) > 1e-7
            or abs(charge - number(row, "cumulative_billed")) > 1e-7
        ):
            raise BoundaryRejected("cumulative source mismatch")
        if tick > integer(phase[-1], "world_full_time"):
            post_clear += blocks
        per_tick[tick] = per_tick.get(tick, 0.0) + blocks
        previous, last_tick = to, tick
    if (
        math.dist(previous, pose(window[-1])) > 1e-7
        or integer(window[-1], "packets") != len(packets)
        or abs(number(window[-1], "blocks") - distance) > 1e-7
        or abs(number(window[-1], "billed") - charge) > 1e-7
    ):
        raise BoundaryRejected("missing motion or final pose mismatch")
    # Snapshot counters identify the already-observed event prefix even when
    # scheduler and movement callbacks share one World tick (ordering differs).
    for snap in phase + ticks:
        count = integer(snap, "packets")
        if count > len(packets):
            raise BoundaryRejected("snapshot refers to missing event")
        prefix = packets[:count]
        expected_pose = pose(prefix[-1], "to_") if prefix else start
        if (
            math.dist(pose(snap), expected_pose) > 1e-7
            or abs(number(snap, "blocks") - sum(number(p, "blocks") for p in prefix)) > 1e-7
            or abs(number(snap, "billed") - sum(number(p, "billed") for p in prefix)) > 1e-7
        ):
            raise BoundaryRejected("snapshot/event prefix mismatch")
    # All later observed ticks must remain quiet; a temporary pause is not an end.
    if any(
        (integer(r, "packets") != len(packets) or math.dist(pose(r), previous) > 1e-7)
        for r in ticks
        if integer(r, "tick") >= integer(window[-1], "tick")
    ):
        raise BoundaryRejected("motion resumed after quiet boundary")
    original_start = tuple(movement["native_start_position"][a] for a in ("x", "y", "z"))
    if math.dist(start, original_start) > 1e-6:
        raise BoundaryRejected("pre-Action drift")
    target = movement["native_target_position"]
    remaining = math.hypot(target["x"] - previous[0], target["z"] - previous[2])
    initial = math.hypot(target["x"] - start[0], target["z"] - start[2])
    progress = initial - remaining
    if abs(progress - movement["observed_progress_blocks"]) > 1e-5:
        raise BoundaryRejected("Action OUTCOME contradicts physical progress")
    return {
        "classification": "DEV_ONLY_SOURCE_RECONCILED_NOT_R_ATTESTED",
        "world": world,
        "marker_id": marker,
        "nominal_requested_blocks": 1.0,
        "native_horizontal_path_blocks": distance,
        "native_target_progress_blocks": progress,
        "native_walk_exhaustion": charge,
        "distance_after_post_clear_world_bracket_blocks": post_clear,
        "clear_ack_to_world_exact_tick": "NOT_ATTESTED",
        "quiet_observed_from_tick": integer(window[0], "tick"),
        "quiet_observed_through_tick": integer(ticks[-1], "tick"),
        "physical_permanent_stop": "NOT_ATTESTED",
        "hard_one_block_cap": "NOT_GUARANTEED",
        "tick_classes": [
            dict(
                world_tick=integer(r, "tick"),
                action_id=movement["action_id"],
                distance=per_tick.get(integer(r, "tick"), 0.0),
                kind=(
                    "MOVE_OBSERVATION_NO_WAIT_RECOVERY"
                    if integer(r, "tick") <= integer(window[-1], "tick")
                    else "NO_ACTION_UNKNOWN_NO_WAIT_RECOVERY"
                ),
            )
            for r in ticks
        ],
        "wait_recovery_eligible_ticks": 0,
    }



def tick_motion_source(content: str, phase: dict, walk_rate: float) -> dict:
    """Verify the prospective Paper tick-pose WALK writer, not event billing.

    A tick-to-tick chord is a lower bound on continuous movement. The server
    writes native player exhaustion for EACH observed chord; sub-tick turns
    remain NOT_ATTESTED. Old event-based profiles are not promoted.
    """
    if not isinstance(phase, dict) or not math.isfinite(walk_rate) or walk_rate < 0:
        raise BoundaryRejected("unregistered tick meter profile")
    marker = phase["marker_id"]
    phase_rows = phases(content, marker)
    if phase_rows[0].get("marker_id") != marker:
        raise BoundaryRejected("tick ledger phase marker mismatch")
    world = phase_rows[0].get("world")
    arm = rows(content, "S50_DEV_TICK_METER_ARM ")
    if (len(arm) != 1 or arm[0].get("marker_id") != marker
            or arm[0].get("world") != world
            or integer(arm[0], "world_full_time")
            != integer(phase_rows[0], "world_full_time")
            or math.dist(pose(arm[0]), pose(phase_rows[0])) > 1e-8):
        raise BoundaryRejected("native tick meter was not armed at PRE_FORWARD")
    ledger = rows(content, "S50_DEV_TICK_MOTION ")
    if len(ledger) < 6:
        raise BoundaryRejected("missing continuous native World-tick motion")
    previous = pose(arm[0])
    blocks_sum = charge_sum = 0.0
    last_tick = integer(arm[0], "world_full_time")
    by_tick = {}
    moving_rows = 0
    for idx, r in enumerate(ledger, 1):
        tick = integer(r, "world_full_time")
        if (r.get("marker_id") != marker or r.get("world") != world
                or integer(r, "id") != idx
                or tick not in ((last_tick, last_tick + 1) if idx == 1
                                else (last_tick + 1,))):
            raise BoundaryRejected("foreign/nonconsecutive native tick meter")
        start, end = pose(r, "from_"), pose(r, "to_")
        if math.dist(start, previous) > 1e-8:
            raise BoundaryRejected("tick meter source discontinuity")
        blocks = math.hypot(end[0]-start[0], end[2]-start[2])
        charge = number(r, "billed")
        if (blocks > 1 or abs(start[1] - end[1]) > 0.5
                or abs(blocks - number(r, "blocks")) > 1e-8
                or abs(charge - blocks * walk_rate) > 1e-8):
            raise BoundaryRejected("native tick ledger distance/debit mismatch")
        blocks_sum += blocks
        charge_sum += charge
        if (abs(number(r, "cumulative_blocks")-blocks_sum) > 1e-7
                or abs(number(r, "cumulative_billed")-charge_sum) > 1e-7
                or abs(number(r, "write_target")-
                       number(r, "write_before")-charge) > 1e-6
                or abs(number(r, "write_after")-
                       number(r, "write_target")) > 2e-6):
            raise BoundaryRejected("native tick exhaustion writer discrepancy")
        previous, last_tick = end, tick
        by_tick[tick] = (end, blocks_sum, charge_sum)
        moving_rows += blocks > 0
    if moving_rows == 0:
        raise BoundaryRejected("no physical MOVE progress in tick ledger")
    samples = rows(content, "S50_DEV_TICK ")
    if not samples:
        raise BoundaryRejected("no native tick snapshot with meter counters")
    for sample in samples:
        tick = integer(sample, "tick")
        if (sample.get("world") != world or sample.get("marker_id") != marker
                or tick not in by_tick):
            raise BoundaryRejected("snapshot without original tick writer")
        end, walked, spent = by_tick[tick]
        if (math.dist(pose(sample), end) > 1e-8
                or abs(number(sample, "tick_meter_blocks")-walked) > 1e-7
                or abs(number(sample, "tick_meter_billed")-spent) > 1e-7):
            raise BoundaryRejected("native tick snapshot/exhaustion drift")
    return {
        "source": "PAPER_PER_WORLD_TICK_NATIVE_POSE_AND_EXHAUSTION_WRITES_DEV",
        "marker_id": marker,
        "world": world,
        "source_rows": len(ledger),
        "first_tick": integer(ledger[0], "world_full_time"),
        "last_tick": last_tick,
        "moving_rows": moving_rows,
        "observed_tick_chord_blocks": blocks_sum,
        "walk_native_writer_input": charge_sum,
        "last_pose": dict(zip(("x", "y", "z"), previous)),
        "unobserved_subtick_path": "NOT_ATTESTED",
        "native_event_double_billing_prevented": True,
        "exact_continuous_distance_attested": False,
        "qualified": False,
        "science_go": False,
    }


def reconcile_tick_meter(content: str, movement: dict, *, walk_rate: float) -> dict:
    """S50 DEV-only action→accepted tick writer↔quiet endpoint, no fake OUTCOME."""
    marker = movement["action_id"] + "-" + movement["source_session"]
    if movement["v7_phase_marker_id"] != marker:
        raise BoundaryRejected("foreign tick metering Action/session")
    quiet = quiet_window(content, marker)
    if quiet is None:
        raise BoundaryRejected("tick-meter physical quiet not observed")
    phase_rows, _ticks, window = quiet
    source = {
        "marker_id": marker, "ordered_originals": [
            {"phase": r["phase"]} for r in phase_rows
        ]
    }
    meter = tick_motion_source(content, source, walk_rate)
    original = movement["native_start_position"]
    start = tuple(original[k] for k in ("x", "y", "z"))
    endpoint = pose(window[-1])
    if (math.dist(pose(phase_rows[0]), start) > 1e-6
            or math.dist(tuple(meter["last_pose"][a] for a in ("x", "y", "z")),
                         endpoint) > 1e-7):
        raise BoundaryRejected("tick writer/Action physical endpoints disagree")
    events = rows(content, "M02_DEV_MOTION ")
    if not events or any(
        r.get("world") != meter["world"] or r.get("marker_id") != marker
        or integer(r, "id") != i
        or abs(number(r, "billed")) > 1e-12
        or abs(number(r, "cumulative_billed")) > 1e-12
        for i, r in enumerate(events, 1)
    ):
        raise BoundaryRejected("legacy event billing still active / foreign")
    event_distance = sum(number(r, "blocks") for r in events)
    if event_distance > meter["observed_tick_chord_blocks"] + 1e-7:
        raise BoundaryRejected("tick lower bound falls short of event path")
    # Existing motion events remain native observations, not alternative
    # billable movements; add no after-the-fact debit/credit.
    target = movement["native_target_position"]
    remaining = math.hypot(target["x"] - endpoint[0], target["z"] - endpoint[2])
    initial = math.hypot(target["x"] - start[0], target["z"] - start[2])
    progress = initial - remaining
    if abs(progress - movement["observed_progress_blocks"]) > 1e-5:
        raise BoundaryRejected("physical progress contradicts Action OUTCOME")
    # The complete tick ledger is checked through its last original,
    # including its observations AFTER the bounded quiet terminal.
    # It cannot prove an infinite future absence of motion.
    return {
        "classification": "S50_DEV_TICK_CHORD_WALK_SOURCE_RECONCILED_NOT_QUALIFIED",
        "world": meter["world"],
        "marker_id": marker,
        "nominal_requested_blocks": 1.0,
        "native_horizontal_path_blocks": meter["observed_tick_chord_blocks"],
        "native_target_progress_blocks": progress,
        "native_walk_exhaustion": meter["walk_native_writer_input"],
        "native_event_observed_blocks_not_billed": event_distance,
        "observed_tick_motion_source": meter,
        "quiet_observed_from_tick": integer(window[0], "tick"),
        "quiet_observed_through_tick": integer(window[-1], "tick"),
        "physical_permanent_stop": "NOT_ATTESTED",
        "hard_one_block_cap": "NOT_GUARANTEED",
        "sub_tick_path": "NOT_ATTESTED",
        "wait_recovery_eligible_ticks": 0,
    }


def verify_native(native: list[dict], commands: list[dict], movement: dict):
    """Recheck original bridge command/ACK/probe identity, not host timestamps."""
    session = movement["source_session"]
    if (
        not native
        or any(r.get("session_id") != session for r in native)
        or [r.get("seq") for r in native] != list(range(len(native)))
    ):
        raise BoundaryRejected("missing/duplicate/foreign native stream")
    action = movement["action_id"]
    for key, aid, effect in [
        ("look_seq", action + "-look", "look"),
        ("forward_seq", action, "set_control"),
        ("clear_seq", action + "-clear", "clear_controls"),
    ]:
        index = movement[key]
        ack = native[index] if 0 <= index < len(native) else {}
        if (
            ack.get("type") != "effect_result"
            or ack.get("action_id") != aid
            or ack.get("effect") != effect
            or ack.get("result") != "applied"
        ):
            raise BoundaryRejected("native control ACK missing/foreign/rejected")
        acks = [r for r in native if r.get("type") == "effect_result" and r.get("action_id") == aid]
        if len(acks) != 1:
            raise BoundaryRejected("duplicate native control ACK")
        cmd = [r for r in commands if r.get("action_id") == aid]
        if len(cmd) != 1 or cmd[0].get("effect") != effect:
            raise BoundaryRejected("command missing/duplicated/foreign")
        if effect == "set_control" and (
            cmd[0].get("control") != "forward" or cmd[0].get("state") is not True
        ):
            raise BoundaryRejected("wrong control command")
    if (
        len([r for r in commands if r.get("type") == "effect"]) != 3
        or len([r for r in native if r.get("type") == "effect_result"]) != 3
    ):
        raise BoundaryRejected("extra uncontrolled effect in single-Action boundary")
    if len([r for r in native if r.get("request_id") == action + "-seek-after"]) != 1:
        raise BoundaryRejected("duplicate/missing final probe")
    seqs = [
        movement[k]
        for k in ("source_before_seq", "look_seq", "forward_seq", "clear_seq", "source_after_seq")
    ]
    if seqs != sorted(set(seqs)):
        raise BoundaryRejected("native ACK chronology")
    after = native[movement["source_after_seq"]]
    if after.get("request_id") != action + "-seek-after":
        raise BoundaryRejected("missing correlated final probe")
    if len([r for r in native if r.get("type") == "shutdown_ack"]) != 1:
        raise BoundaryRejected("STOP ACK NOT_ATTESTED")


def review_bundle(root: Path) -> dict:
    """Read-only replay of reconciliation against saved receipt byte hashes."""
    import hashlib
    import json

    report = json.loads((root / "m02_report.json").read_text())
    required = {
        "original_native.jsonl",
        "owner_commands.jsonl",
        "paper_server.log",
        "s50_action_original.jsonl",
    }
    for name in required:
        path = root / name
        expected = report.get("evidence_hashes", {}).get(name)
        if (
            path.is_symlink()
            or not path.is_file()
            or hashlib.sha256(path.read_bytes()).hexdigest() != expected
        ):
            raise BoundaryRejected("original byte hash mismatch/missing: " + name)
    movement = report["movement"]
    journal = [json.loads(x) for x in (root / "s50_action_original.jsonl").read_text().splitlines()]
    if (
        len(journal) != 2
        or [r.get("state") for r in journal] != ["issued", "outcome"]
        or any(
            r.get("action_id") != movement["action_id"]
            or r.get("session_id") != movement["source_session"]
            for r in journal
        )
        or [e["state"] for e in journal[0]["events"]] != ["proposed", "authorized", "issued"]
        or journal[1]["events"][:-1] != journal[0]["events"]
        or journal[1]["events"][-1]["state"] != "outcome"
    ):
        raise BoundaryRejected("formal issued/outcome journal mismatch")
    verify_native(
        [json.loads(x) for x in (root / "original_native.jsonl").read_text().splitlines()],
        [json.loads(x) for x in (root / "owner_commands.jsonl").read_text().splitlines()],
        movement,
    )
    from adapters.mineflayer.m02_paper_dev.v7_paired_config import ARMS

    result = reconcile(
        (root / "paper_server.log").read_text(),
        movement,
        walk_rate=0.01 * ARMS[report["v7_arm"]][1],
    )
    if report.get("java_exit") != 0 or report.get("node_exit") != 0:
        raise BoundaryRejected("session cleanup not confirmed")
    return result


def diagnose_motion(content: str, marker: str) -> dict:
    """Report native sources separately even when the physical boundary blocks.

    Tick chords are not invented PlayerMoveEvents or proven sub-tick paths.
    The endpoint is a lower bound on travel; no debit/credit is repaired here.
    """
    quiet = quiet_window(content, marker)
    if quiet is None:
        raise BoundaryRejected("native quiet interval NOT_ATTESTED")
    phase, ticks, window = quiet
    world = phase[0]["world"]
    packets = rows(content, "M02_DEV_MOTION ")
    if any(r.get("world") != world or r.get("marker_id") != marker for r in packets):
        raise BoundaryRejected("foreign motion diagnostics")
    first, last = pose(phase[0]), pose(window[-1])
    displacement = math.hypot(last[0] - first[0], last[2] - first[2])
    event_path = sum(number(r, "blocks") for r in packets)
    event_charge = sum(number(r, "billed") for r in packets)
    sampled = [first] + [pose(r) for r in ticks]
    chord_sum = sum(math.hypot(b[0] - a[0], b[2] - a[2]) for a, b in zip(sampled, sampled[1:]))
    after = pose(phase[-1])
    tail = math.hypot(last[0] - after[0], last[2] - after[2])
    gap = max(0.0, displacement - event_path)
    return {
        "classification": "DEV_ONLY_DIAGNOSTIC_NOT_ATTESTATION",
        "world": world,
        "marker_id": marker,
        "native_start_pose": dict(zip(("x", "y", "z"), first)),
        "native_quiet_pose": dict(zip(("x", "y", "z"), last)),
        "endpoint_displacement_blocks": displacement,
        "tick_sampled_horizontal_chords_blocks": chord_sum,
        "event_metered_horizontal_path_blocks": event_path,
        "event_billed_walk_exhaustion": event_charge,
        "unmetered_travel_lower_bound_blocks": gap,
        "post_clear_bracket_endpoint_displacement_blocks": tail,
        "post_clear_tick": integer(phase[-1], "world_full_time"),
        "quiet_interval_start_tick": integer(window[0], "tick"),
        "quiet_interval_end_tick": integer(window[-1], "tick"),
        "event_meter_covers_native_endpoint": gap <= 1e-7,
        "body_boundary": "BLOCKED" if gap > 1e-7 else "NOT_ATTESTED",
        "sub_tick_path": "NOT_ATTESTED",
        "wait_recovery_eligible_ticks": 0,
    }


def diagnose_bundle(root: Path) -> dict:
    """Read-only failed-attempt diagnosis, preserving the original terminal."""
    import hashlib
    import json

    report = json.loads((root / "m02_report.json").read_text())
    for name in (
        "paper_server.log",
        "s50_action_original.jsonl",
        "original_native.jsonl",
        "owner_commands.jsonl",
    ):
        path = root / name
        if (
            path.is_symlink()
            or not path.is_file()
            or hashlib.sha256(path.read_bytes()).hexdigest()
            != report.get("evidence_hashes", {}).get(name)
        ):
            raise BoundaryRejected("original byte hash mismatch: " + name)
    journal = [json.loads(x) for x in (root / "s50_action_original.jsonl").read_text().splitlines()]
    if (
        len(journal) != 2
        or journal[0].get("state") != "issued"
        or journal[1].get("state") != "unknown"
        or any(r.get("session_id") != report.get("source_session_id") for r in journal)
        or journal[1].get("action_id") != journal[0].get("action_id")
        or journal[1]["events"][:-1] != journal[0]["events"]
    ):
        raise BoundaryRejected("failed formal Action lineage missing")
    marker = journal[0]["action_id"] + "-" + journal[0]["session_id"]
    result = diagnose_motion((root / "paper_server.log").read_text(), marker)
    native = [json.loads(x) for x in (root / "original_native.jsonl").read_text().splitlines()]
    commands = [json.loads(x) for x in (root / "owner_commands.jsonl").read_text().splitlines()]
    action = journal[0]["action_id"]

    def one(predicate):
        found = [r for r in native if predicate(r)]
        if len(found) != 1:
            raise BoundaryRejected("native boundary ACK/probe missing/duplicate")
        return found[0]["seq"]

    movement = {
        "action_id": action,
        "source_session": report["source_session_id"],
        "source_before_seq": one(lambda r: r.get("request_id") == "m02-before-walk"),
        "source_after_seq": one(lambda r: r.get("request_id") == action + "-seek-after"),
        **{
            key: one(
                lambda r, aid=aid: r.get("type") == "effect_result" and r.get("action_id") == aid
            )
            for key, aid in (
                ("look_seq", action + "-look"),
                ("forward_seq", action),
                ("clear_seq", action + "-clear"),
            )
        },
    }
    verify_native(native, commands, movement)
    for key, expected in (
        ("source_before_seq", result["native_start_pose"]),
        ("source_after_seq", result["native_quiet_pose"]),
    ):
        actual = native[movement[key]].get("snapshot", {}).get("position", {})
        if any(abs(number(actual, axis) - expected[axis]) > 1e-6 for axis in ("x", "y", "z")):
            raise BoundaryRejected("native probe/World pose mismatch")
    result["native_boundary_seqs"] = movement
    from adapters.mineflayer.m02_paper_dev.v7_paired_config import ARMS, TEMPLATE, render_arm

    # Failed owner reports may stop before the arm label is assigned. Bind to
    # the saved physical config fingerprint, never infer from a directory name.
    candidates = [
        arm
        for arm in ARMS
        if hashlib.sha256(render_arm(TEMPLATE.read_bytes(), arm)).hexdigest()
        == report.get("plugin_config_sha256")
    ]
    rates = {0.01 * ARMS[arm][1] for arm in candidates}
    if len(rates) != 1:
        raise BoundaryRejected("configured WALK rate NOT_ATTESTED")
    rate = rates.pop()
    result.update(
        source_config_candidate_arms=candidates,
        configured_walk_rate=rate,
        walk_debit_shortfall_lower_bound=max(
            0.0,
            result["endpoint_displacement_blocks"] * rate - result["event_billed_walk_exhaustion"],
        ),
        original_terminal=journal[-1]["state"],
        original_error=report.get("error"),
        original_status=report.get("status"),
        native_clear_and_shutdown_ack=True,
        java_exit=report.get("java_exit"),
        node_exit=report.get("node_exit"),
    )
    return result


if __name__ == "__main__":
    import argparse
    import json

    parser = argparse.ArgumentParser(description="Read-only S50 DEV original-byte review")
    parser.add_argument("root", type=Path)
    parser.add_argument("--failed-attempt", action="store_true")
    args = parser.parse_args()
    print(
        json.dumps(
            diagnose_bundle(args.root) if args.failed_attempt else review_bundle(args.root),
            indent=2,
        )
    )
