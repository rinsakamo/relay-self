"""DEV-only readback of first original S49 Action Node-local hold windows.

The original S49 controls and Paper speed cap are NOT changed. This reviewer
separates coincidence of observed tick counts from command-level tick matching.
It never equates Node monotonic clock with Paper World ticks.
"""
from __future__ import annotations

import json
from pathlib import Path

from adapters.mineflayer.s49_p1_matched_boost_review_dev import (
    review_p1_matched_boost_worlds_dev,
)
from adapters.mineflayer.s49_speed_attr_boundary_dev import (
    review_speed_attr_boundary_dev,
)


class P1NativeHoldRejected(ValueError):
    pass


CASES = ("CARRY", "WAIT_ASSUMED")
HOLD_TOLERANCE_MS = 50


def _node_window(trace: dict, *, action_id: str, session_id: str) -> dict:
    """Audit the producer-local SET -> physicsTick -> CLEAR chronology."""
    if (
        type(trace) is not dict
        or trace.get("version") != "S49_SPEED_ATTR_NATIVE_BOUNDARY_DEV_V1"
        or trace.get("session_id") != session_id
        or trace.get("action_id") != action_id
        or trace.get("complete") is not True
        or trace.get("source_attested") is not False
        or trace.get("paper_clock_synchronized") is not False
        or trace.get("added_issuers") != 0 or trace.get("added_readers") != 0
        or type(trace.get("rows")) is not list
        or type(trace.get("physics_ticks")) is not int
    ):
        raise P1NativeHoldRejected("non-original local source or forged clock")
    rows = trace["rows"]
    if not 5 <= len(rows) <= 120:
        raise P1NativeHoldRejected("missing or unbounded original Node events")
    if (
        rows[0].get("kind") != "FIRST_ORIGINAL_SET"
        or rows[-1].get("kind") != "FIRST_ORIGINAL_CLEAR"
        or sum(r.get("kind") == "FIRST_ORIGINAL_SET" for r in rows) != 1
        or sum(r.get("kind") == "FIRST_ORIGINAL_CLEAR" for r in rows) != 1
    ):
        raise P1NativeHoldRejected("ambiguous original SET/CLEAR controls")
    times = [r.get("monotonic_ms") for r in rows]
    if (
        any(type(t) is not int or t < 0 for t in times)
        or times != sorted(times)
        or any(r.get("ordinal") != i for i, r in enumerate(rows, 1))
    ):
        raise P1NativeHoldRejected("non-monotonic or duplicated Node event order")
    physics = [r for r in rows if r.get("kind") == "ACTIVE_PHYSICS"]
    if (
        len(physics) != trace["physics_ticks"]
        or len(physics) < 3
        or [r.get("physics_ordinal") for r in physics]
           != list(range(1, len(physics) + 1))
        or any(r.get("forward") is not True or r.get("sprint") is not True
               for r in physics)
    ):
        raise P1NativeHoldRejected("native active physics tick continuity violated")
    duration = times[-1] - times[0]
    if not 250 <= duration <= 1600:
        raise P1NativeHoldRejected("original physical SET/CLEAR window out of bounds")
    return {
        "session_id": session_id,
        "first_action_id": action_id,
        "first_set_monotonic_ms": times[0],
        "first_clear_monotonic_ms": times[-1],
        "first_action_node_local_hold_ms": duration,
        "node_active_physics_ticks": len(physics),
        "first_active_physics_delay_ms": physics[0]["monotonic_ms"] - times[0],
        "last_active_physics_to_clear_ms": times[-1] - physics[-1]["monotonic_ms"],
        "node_source_clock": "LOCAL_MONOTONIC_MS_NOT_PAPER_WORLD_TICK",
        "no_new_control_or_reader": True,
    }


def compare_first_native_hold_dev(matched: dict, traces: dict[str, dict],
                                  witnesses: dict[str, dict]) -> dict:
    if (
        type(matched) is not dict
        or matched.get("classification")
           != "P1_TWO_INDEPENDENT_WORLDS_MATCHED_SEVEN_BONUS_TICKS_DEV_ONLY"
        or set(matched.get("arms", {})) != set(CASES)
        or matched.get("same_number_of_positive_paper_boost_ticks") is not True
        or matched.get("world_clock_phase_matched") is not False
        or matched.get("original_s49_first_action_duration_matched_by_world_tick")
           is not False
        or matched.get("model_preload_not_actual_longitudinal_p1_recovery") is not True
        or matched.get("native_displacement_causally_attributed_only_to_p1") is not False
        or matched.get("qualification_go") is not False
        or matched.get("science_go") is not False
        or type(traces) is not dict or set(traces) != set(CASES)
        or type(witnesses) is not dict or set(witnesses) != set(CASES)
    ):
        raise P1NativeHoldRejected("prior matched Paper/source contract changed")
    arms = {}
    for case in CASES:
        arm = matched["arms"][case]
        witness = witnesses[case]
        if (
            type(arm) is not dict or type(witness) is not dict
            or arm.get("exact_paper_positive_bonus_ticks") != 7
            or arm.get("paper_action_owner_issued") is not False
            or arm.get("qualification_go") is not False
            or witness.get("classification")
               != "S49_NODE_PAPER_ATTRIBUTE_TO_PHYSICS_KEY_DIAGNOSTIC_DEV_ONLY"
            or witness.get("session_id") != arm.get("session_id")
            or witness.get("action_id") != arm.get("action_id")
            or witness.get("no_additional_packet_reader") is not True
            or witness.get("paper_native_clock_same_epoch") is not False
            or witness.get("qualification_go") is not False
            or witness.get("science_go") is not False
        ):
            raise P1NativeHoldRejected(f"{case} producer source join failed")
        node = _node_window(
            traces[case], action_id=arm["action_id"],
            session_id=arm["session_id"],
        )
        if (
            node["node_active_physics_ticks"]
               != witness.get("node_physics_ticks_sampled")
            or type(arm.get("paper_total_gait_ticks")) is not int
        ):
            raise P1NativeHoldRejected(f"{case} original tick counters disagree")
        arms[case] = {
            **node,
            "paper_total_gait_ticks": arm["paper_total_gait_ticks"],
            "paper_positive_bonus_ticks": arm["exact_paper_positive_bonus_ticks"],
            "node_attribute_active_boost_ticks":
                witness["node_active_physics_key_dash_seen_count"],
            "node_only_and_paper_only_clocks": True,
        }
    a, b = arms["CARRY"], arms["WAIT_ASSUMED"]
    if a["session_id"] == b["session_id"]:
        raise P1NativeHoldRejected("independent World sessions collapsed")
    hold_delta_ms = b["first_action_node_local_hold_ms"] - a[
        "first_action_node_local_hold_ms"
    ]
    equal_physics = (
        a["node_active_physics_ticks"] == b["node_active_physics_ticks"]
    )
    equal_paper = a["paper_total_gait_ticks"] == b["paper_total_gait_ticks"]
    equal_active_boost = (
        a["node_attribute_active_boost_ticks"]
        == b["node_attribute_active_boost_ticks"]
    )
    duration_within_tolerance = abs(hold_delta_ms) <= HOLD_TOLERANCE_MS
    observational_match = (
        equal_physics and equal_paper and equal_active_boost
        and duration_within_tolerance
    )
    return {
        "classification": (
            "P1_FIRST_ACTION_OBSERVED_NODE_HOLD_AND_TICKS_MATCH_DEV_ONLY"
            if observational_match
            else "P1_FIRST_ACTION_NODE_HOLD_MATCH_NOT_ESTABLISHED_DEV_ONLY"
        ),
        "arms": arms,
        "node_local_hold_delta_ms": hold_delta_ms,
        "node_hold_tolerance_ms": HOLD_TOLERANCE_MS,
        "node_hold_within_tolerance": duration_within_tolerance,
        "node_active_physics_tick_counts_equal": equal_physics,
        "paper_action_gait_tick_counts_equal": equal_paper,
        "node_boost_attribute_physics_tick_counts_equal": equal_active_boost,
        "original_action_tick_controlled_by_paper": False,
        "original_action_duration_tick_controlled_by_node": False,
        "paper_and_node_phase_aligned": False,
        "separate_world_monotonic_epoch_comparable": False,
        "physical_output_difference_observed_m":
            matched["native_original_s16_displacement_gain_m"],
        "hypothetical_preload_not_measured_recovery": True,
        "native_hold_observation_not_r_or_science_qualification": True,
        "additional_action_issuers": 0,
        "additional_native_readers": 0,
        "p1_or_m0_extra_postings": 0,
        "qualification_go": False,
        "science_go": False,
    }


def review_first_native_hold_pair_dev(root: Path) -> dict:
    if not isinstance(root, Path) or root.is_symlink() or not root.is_dir():
        raise P1NativeHoldRejected("untrusted World pair root")
    matched = review_p1_matched_boost_worlds_dev(root)
    traces, witnesses = {}, {}
    for case in CASES:
        arm = matched["arms"][case]
        path = root / case / "node_speed_attr_boundary_dev.json"
        if path.is_symlink() or not path.is_file() or not 200 <= path.stat().st_size <= 170_000:
            raise P1NativeHoldRejected(f"{case} raw Node producer source absent")
        traces[case] = json.loads(path.read_text(encoding="utf-8"))
        witnesses[case] = review_speed_attr_boundary_dev(
            path, session_id=arm["session_id"],
            action_id=arm["action_id"], sync_expected=True,
        )
    result = compare_first_native_hold_dev(matched, traces, witnesses)
    (root / "p1_first_native_hold_pair_dev.json").write_text(
        json.dumps(result, sort_keys=True, indent=2) + "\n", encoding="utf-8",
    )
    return result


def main() -> int:
    import argparse

    p = argparse.ArgumentParser()
    p.add_argument("--root", type=Path, required=True)
    args = p.parse_args()
    print(json.dumps(review_first_native_hold_pair_dev(args.root), sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
