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
    # Derive candidate spans directly from eligible consecutive tick IDs.
    # Never interpolate missing ticks or accept one-frame stillness.
    static_tick_ids = []
    for tick in range(low, high + 1):
        if tick not in paper or tick - 1 not in paper:
            raise InterActionStillnessRejected("candidate missing Paper predecessor")
        x, z = paper[tick]
        px, pz = paper[tick - 1]
        if math.hypot(x - px, z - pz) <= .002:
            static_tick_ids.append(tick)
    streaks = []
    for tick in static_tick_ids:
        if streaks and streaks[-1][1] == tick - 1:
            streaks[-1][1] = tick
        else:
            streaks.append([tick, tick])
    viable = [v for v in streaks if v[1]-v[0]+1 >= min_still_ticks]
    if not viable:
        return {
            "classification": "S49_INTER_ACTION_STILLNESS_CANDIDATE_ABSENT_DEV_ONLY",
            "action_ids": [first_action_id, second_action_id],
            "session_id": session_id,
            "paper_valid_stillness_found": False,
            "paper_max_low_motion_run_ticks": max(
                (v[1] - v[0] + 1 for v in streaks), default=0,
            ),
            "paper_candidate_search_interval": [low, high],
            "paper_motion_probe": [
                [t, list(paper.get(t, ())),
                 math.hypot(paper[t][0] - paper[t-1][0],
                            paper[t][1] - paper[t-1][1])]
                for t in (low, low + 1, low + 10, low + 20, high)
                if t in paper and t - 1 in paper
            ],
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


def review_original_owner_no_issued_action_gap_dev(
    owner: dict, stillness: dict, *, first_action_id: str,
    second_action_id: str, session_id: str,
) -> dict:
    """Readback from SAME original S49 NormalSessionActionExecutor.

    There is no new Action owner or receiver. No assumed equality between
    Python monotonic_ns, Node process.hrtime and Paper fullTime clocks.
    """
    if (
        type(owner) is not dict or type(stillness) is not dict
        or owner.get("classification")
           != "S49_ORIGINAL_EXECUTOR_NO_ISSUE_GAP_DEV_ONLY"
        or owner.get("session_id") != session_id
        or stillness.get("session_id") != session_id
        or owner.get("first_terminal_action_id") != first_action_id
        or owner.get("second_requested_action_id") != second_action_id
        or stillness.get("action_ids") != [first_action_id, second_action_id]
        or stillness.get("classification")
           != "S49_INTER_ACTION_STILLNESS_CANDIDATE_DEV_ONLY"
        or stillness.get("node_all_controls_off_until_second_set") is not True
        or stillness.get("paper_consecutive_low_motion_ticks", 0) < 8
        or stillness.get("node_paper_tick_join_attested") is not False
        or stillness.get("physical_WAIT_admitted") is not False
        or owner.get("same_original_S49_executor") is not True
        or owner.get("first_terminal_outcome") is not True
        or owner.get("native_action_count_at_first_terminal") != 1
        or owner.get("native_open_actions_at_first_terminal") != 0
        or owner.get("native_action_count_at_next_request") != 1
        or owner.get("native_open_actions_at_next_request") != 0
        or owner.get("native_action_count_after_second_terminal") != 2
        or owner.get("native_open_actions_after_second_terminal") != 0
        or owner.get("native_dispatched_action_ids") != [first_action_id]
        or owner.get("all_actions_globally_absent_attested") is not False
        or owner.get("paper_world_tick_bound_attested") is not False
        or owner.get("node_control_epoch_aligned_attested") is not False
        or owner.get("WAIT_admitted") is not False
        or owner.get("P1_recovery_posted") is not False
        or owner.get("M0_posted") is not False
        or stillness.get("P1_recovery_posted") is not False
        or stillness.get("M0_posted") is not False
    ):
        raise InterActionStillnessRejected(
            "original sole S49 Action owner or static/control candidate not bound"
        )
    start = owner.get("host_first_outcome_monotonic_ns")
    end = owner.get("host_next_action_request_monotonic_ns")
    duration = owner.get("elapsed_owner_local_monotonic_ns")
    if (any(type(n) is not int or n < 0 for n in (start, end, duration))
            or not 0 < duration <= 120_000_000_000
            or end - start != duration):
        raise InterActionStillnessRejected("original S49 owner clock malformed")
    return {
        "classification": "S49_ORIGINAL_OWNER_NO_ACTION_ISSUE_PLUS_NODE_PAPER_STATIC_CANDIDATE_DEV_ONLY",
        "action_ids": [first_action_id, second_action_id],
        "session_id": session_id,
        "same_original_executor": True,
        "original_owner_no_new_issue_between_bookends": True,
        "first_terminal_count": 1,
        "at_next_action_request_count": 1,
        "after_second_terminal_count": 2,
        "open_actions_at_bookends": [0, 0, 0],
        "original_owner_gap_monotonic_ms": duration / 1_000_000,
        "paper_candidate_first_tick":
            stillness["paper_first_candidate_tick"],
        "paper_candidate_last_tick":
            stillness["paper_last_candidate_tick"],
        "paper_candidate_consecutive_still_ticks":
            stillness["paper_consecutive_low_motion_ticks"],
        "node_input_off_physics_callbacks": stillness["node_physics_samples"],
        "node_all_inputs_off_at_local_callbacks": True,
        "host_node_monotonic_clocks_calibrated": False,
        "host_paper_world_tick_clocks_calibrated": False,
        "physical_overlap_time_attested": False,
        "global_issuer_absence_attested": False,
        "physical_WAIT_admitted": False,
        "P1_recovery_posted": False,
        "M0_posted": False,
        "independent_source_attested": False,
        "qualification_go": False,
        "science_go": False,
    }
