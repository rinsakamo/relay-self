"""Read-only S49 Paper static-body candidate vs Node input-off interval DEV.

Two producer-local time axes are intentionally NEVER identified with one
another. No P1 recovery, physical WAIT admission or M0 debit permitted.
"""
from __future__ import annotations

import json
import math
from pathlib import Path

from adapters.mineflayer.s49_two_action_world_timeline_dev import _fields


class InterActionStillnessRejected(ValueError):
    pass


CONTROLS = ("forward", "sprint", "back", "left", "right", "jump", "sneak")


def review_inter_action_stillness_dev(
    raw: str, path: Path, *, timeline: dict, first_action_id: str,
    second_action_id: str, session_id: str, min_still_ticks: int = 8,
) -> dict:
    """Require genuine Paper stillness and original Node control-off custody.

    Exact Paper movement zero does not exclude latent packet effects,
    observation gaps outside this window or unknown L0 ownership.
    """
    if (
        type(raw) is not str or len(raw) > 10_000_000
        or type(timeline) is not dict
        or timeline.get("classification") !=
            "M0_TWO_NATIVE_ACTIONS_CONTIGUOUS_WORLD_TIMELINE_SHADOW_DEV_ONLY"
        or timeline.get("action_ids") != [first_action_id, second_action_id]
        or timeline.get("session_id") != session_id
        or timeline.get("tick_gaps_or_replay") is not False
        or timeline.get("double_counted_world_ticks") is not False
        or timeline.get("world_tick_m0_debits_posted") is not False
        or timeline.get("WAIT_sourcebound_admitted") is not False
        or type(min_still_ticks) is not int or not 8 <= min_still_ticks <= 40
        or not isinstance(path, Path) or path.is_symlink() or not path.is_file()
        or not 0 < path.stat().st_size <= 250_000
    ):
        raise InterActionStillnessRejected("bounded, source-joined passive inputs required")
    try:
        node = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        raise InterActionStillnessRejected("original Node trace missing") from exc
    if (type(node) is not dict
        or node.get("version") != "S49_NODE_INTER_ACTION_INPUT_OFF_DEV_V1"
        or node.get("session_id") != session_id
        or node.get("first_action_id") != first_action_id
        or node.get("first_cleanup_action_id") != first_action_id + "-s15-clear"
        or node.get("second_action_id") != second_action_id
        or node.get("source_attested") is not False
        or node.get("clock_synchronized") is not False
        or node.get("overflow") is not False
        or node.get("complete") is not True):
        raise InterActionStillnessRejected("original Node handoff not sealed")
    for controls in [node.get("start_controls"), node.get("before_second_set_controls")]:
        if (type(controls) is not dict
                or set(controls) != set(CONTROLS)
                or any(controls[c] is not False for c in CONTROLS)):
            raise InterActionStillnessRejected("Node handoff control was active")
    nodes = node.get("rows")
    if type(nodes) is not list or not 20 <= len(nodes) <= 1200:
        raise InterActionStillnessRejected("missing or oversized Node physics interval")
    prev_clock = -1
    for i, sample in enumerate(nodes, 1):
        if type(sample) is not dict:
            raise InterActionStillnessRejected("invalid Node physics row")
        clock = sample.get("monotonic_ms")
        if (type(sample.get("ordinal")) is not int
                or sample["ordinal"] != i
                or type(clock) is not int or clock < prev_clock or clock < 0
                or type(sample.get("controls")) is not dict
                or set(sample["controls"]) != set(CONTROLS)
                or any(sample["controls"][c] is not False for c in CONTROLS)
                or any(type(sample.get(k)) not in (float, int)
                       or not math.isfinite(sample[k]) for k in ("x", "z"))):
            raise InterActionStillnessRejected("Node input-off interval has control/gap/replay")
        prev_clock = clock
    arm = timeline.get("first_sample_tick")
    applied = timeline.get("second_ack_delivery_applied_tick")
    ticks_count = timeline.get("observed_contiguous_paper_ticks")
    end = timeline.get("last_sample_tick")
    first_count = timeline.get("first_action_paper_tick_count")
    if any(type(v) is not int for v in (arm, applied, ticks_count, end, first_count)):
        raise InterActionStillnessRejected("Paper timeline clock missing")
    if end - arm + 1 != ticks_count or applied <= arm + first_count + 12:
        raise InterActionStillnessRejected("Paper bridge interval missing")
    world, player = timeline.get("world_uuid"), timeline.get("player_uuid")
    samples = []
    marker = "S49_DASH_DEV_TRAIL_TICK "
    for line in raw.splitlines():
        if marker not in line:
            continue
        row = _fields(line, marker)
        if row.get("action_id") != first_action_id:
            continue
        samples.append(row)
    if len(samples) != ticks_count:
        raise InterActionStillnessRejected("Paper timeline missing or duplicated")
    paper = {}
    for i, row in enumerate(samples):
        try:
            t, index = int(row["tick"]), int(row["index"])
            x, z = float(row["x"]), float(row["z"])
        except (ValueError, KeyError) as exc:
            raise InterActionStillnessRejected("bad Paper position data") from exc
        if (index != i + 1 or t != arm + i
            or row.get("session_id") != session_id
            or row.get("world") != world or row.get("player_uuid") != player
            or not math.isfinite(x) or not math.isfinite(z)
            or any(row.get(k) != "false" for k in
                   ("motor_write", "M0_POSTED", "P1_APPLIED", "WAIT_ATTESTED"))
            or (t > arm + first_count
                and row.get("first_dash_modifier_present") != "false")):
            raise InterActionStillnessRejected("Paper actor clock/control spoofed")
        paper[t] = (x, z)
    # Conservative crop: 6 ticks after first original release/tail;
    # stop at least 6 ticks before Paper receives the second APPLIED ACK.
    # The second native SET may already precede that Paper marker.
    # Therefore even the candidate is NOT proof of no physical Action.
    low = arm + first_count + 7
    high = applied - 6
    streaks = []
    current = None
    for tick in range(low, high + 1):
        if tick not in paper or tick - 1 not in paper:
            raise InterActionStillnessRejected("candidate missing Paper predecessor")
        x, z = paper[t]
        px, pz = paper[t-1]
        delta = math.hypot(x-px, z-pz)
        if delta <= .002:
            if current is None:
                current = [tick, tick]
            else:
                current[1] = tick
        elif current is not None:
            streaks.append(current)
            current = None
    if current is not None:
        streaks.append(current)
    viable = [v for v in streaks if v[1]-v[0]+1 >= min_still_ticks]
    if not viable:
        return {
            "classification": "S49_INTER_ACTION_STILLNESS_CANDIDATE_ABSENT_DEV_ONLY",
            "action_ids": [first_action_id, second_action_id],
            "session_id": session_id,
            "paper_valid_stillness_found": False,
            "node_all_controls_off_until_second_set": True,
            "node_physics_samples": len(nodes),
            "physical_WAIT_admitted": False,
            "P1_recovery_posted": False,
            "M0_posted": False,
            "independent_source_attested": False,
            "node_paper_tick_join_attested": False,
        }
    best = max(viable, key=lambda v: (v[1]-v[0], -v[0]))
    return {
        "classification": "S49_INTER_ACTION_STILLNESS_CANDIDATE_DEV_ONLY",
        "action_ids": [first_action_id, second_action_id],
        "session_id": session_id, "world_uuid": world,
        "paper_first_candidate_tick": best[0],
        "paper_last_candidate_tick": best[1],
        "paper_consecutive_low_motion_ticks": best[1]-best[0]+1,
        "paper_threshold_horizontal_delta_m": .002,
        "paper_all_long_streaks_count": len(viable),
        "node_physics_samples": len(nodes),
        "node_all_controls_off_until_second_set": True,
        "node_first_clear_local_monotonic_ms": nodes[0]["monotonic_ms"],
        "node_last_before_second_set_monotonic_ms": nodes[-1]["monotonic_ms"],
        "paper_observer_motor_write": False,
        "node_paper_tick_join_attested": False,
        "second_native_effect_tick_attested": False,
        "physical_WAIT_admitted": False,
        "P1_recovery_posted": False, "M0_posted": False,
        "independent_source_attested": False,
        "qualification_go": False, "science_go": False,
    }
