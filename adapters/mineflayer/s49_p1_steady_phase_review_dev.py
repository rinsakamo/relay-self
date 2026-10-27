"""DEV phase-sensitive posterior of original S49 seven-bonus-tick Worlds.

Paper first-positive sample often includes the pre-attribute velocity.
Use Paper bonus ordinals 2..7 and Node-local successive positive physics
samples; DO NOT claim these ordinal windows share a clock.
"""
from __future__ import annotations

import hashlib
import json
import math
import statistics
from pathlib import Path

from adapters.mineflayer.s49_p1_matched_boost_review_dev import (
    review_p1_matched_boost_worlds_dev,
)
from adapters.mineflayer.s49_speed_attr_boundary_dev import (
    review_speed_attr_boundary_dev,
)


class SteadyPhaseRejected(ValueError):
    """Previously admitted producer boundary or local phase was violated."""


def _measured(v: object) -> float:
    if type(v) not in (float, int) or not math.isfinite(v):
        raise SteadyPhaseRejected("missing finite speed or position")
    return float(v)


def node_positive_transitions_dev(raw: dict, *, sid: str, aid: str) -> dict:
    """Only adjacent positive Node physics ticks, never interpolated frames."""
    if (
        type(raw) is not dict
        or raw.get("version") != "S49_SPEED_ATTR_NATIVE_BOUNDARY_DEV_V1"
        or raw.get("session_id") != sid or raw.get("action_id") != aid
        or raw.get("sync_enabled") is not True
        or raw.get("complete") is not True
        or raw.get("added_issuers") != 0
        or raw.get("added_readers") != 0
        or raw.get("paper_clock_synchronized") is not False
        or raw.get("source_attested") is not False
        or type(raw.get("rows")) is not list
    ):
        raise SteadyPhaseRejected("foreign or promoted Node timing trace")
    physics = [row for row in raw["rows"]
               if type(row) is dict and row.get("kind") == "ACTIVE_PHYSICS"]
    if len(physics) < 4 or len(physics) > 32:
        raise SteadyPhaseRejected("insufficient first native physics ticks")
    previous_ordinal, prev_boosted = None, False
    previous, transitions = None, []
    for row in physics:
        ordinal = row.get("physics_ordinal")
        if type(ordinal) is not int or (
            previous_ordinal is not None and ordinal != previous_ordinal + 1
        ):
            raise SteadyPhaseRejected("lost continuous local Node physics clock")
        previous_ordinal = ordinal
        if row.get("forward") is not True or row.get("sprint") is not True:
            raise SteadyPhaseRejected("non-sprint control phase")
        attrs = row.get("physics_movement_speed")
        if attrs is not None and (
            type(attrs) is not dict or type(attrs.get("modifiers")) is not list
        ):
            raise SteadyPhaseRejected("invalid active physics speed attribute")
        mods = [m for m in (attrs["modifiers"] if attrs else []) if type(m) is dict
                and m.get("uuid") == "relays49dashdev:forward_dash_only"]
        if len(mods) > 1:
            raise SteadyPhaseRejected("duplicate Paper modifier")
        boosted = len(mods) == 1
        if boosted and (
            mods[0].get("operation") != 2
            or not 0 < _measured(mods[0].get("amount")) <= .5
        ):
            raise SteadyPhaseRejected("invalid effective Paper boost")
        x, z = _measured(row.get("x")), _measured(row.get("z"))
        _measured(row.get("vx"))
        _measured(row.get("vz"))
        if previous is not None and boosted and prev_boosted:
            dx, dz = x - previous[0], z - previous[1]
            distance = math.hypot(dx, dz)
            if not 0 <= distance < 1.0:
                raise SteadyPhaseRejected("impossible local Node physics displacement")
            transitions.append({
                "node_physics_tick_ordinal": ordinal,
                "node_local_delta_m": distance,
                "node_local_speed_proxy_mps": distance * 20.0,
            })
        prev_boosted, previous = boosted, (x, z)
    if len(transitions) < 2:
        raise SteadyPhaseRejected("no stable consecutive boosted Node interval")
    speeds = [x["node_local_speed_proxy_mps"] for x in transitions]
    return {
        "node_active_physics_ticks": len(physics),
        "node_consecutive_boosted_intervals": len(transitions),
        "node_stable_speed_proxy_mps": speeds,
        "node_stable_speed_proxy_mean_mps": statistics.fmean(speeds),
        "node_time_axis": "NODE_LOCAL_PHYSICSTICK_20HZ_ASSUMED",
        "node_paper_tick_join": False,
        "native_motor_owner_modified": False,
    }


def compare_steady_phase_dev(paired: dict, traces: dict[str, dict]) -> dict:
    if (
        type(paired) is not dict or type(traces) is not dict
        or set(traces) != {"CARRY", "WAIT_ASSUMED"}
        or paired.get("classification") != (
            "P1_TWO_INDEPENDENT_WORLDS_MATCHED_SEVEN_BONUS_TICKS_DEV_ONLY"
        )
        or paired.get("same_number_of_positive_paper_boost_ticks") is not True
        or paired.get("world_clock_phase_matched") is not False
        or paired.get("original_s49_first_action_duration_matched_by_world_tick") is not False
        or paired.get("model_preload_not_actual_longitudinal_p1_recovery") is not True
        or paired.get("native_displacement_causally_attributed_only_to_p1") is not False
        or paired.get("physical_l0_dash_power_admission") is not None
        or paired.get("new_action_issuers") != 0
        or paired.get("r_qualified_wait_ticks") != 0
        or paired.get("qualification_go") is not False
        or paired.get("science_go") is not False
    ):
        raise SteadyPhaseRejected("historical seven-tick source qualified by accident")
    arms = paired.get("arms")
    if type(arms) is not dict or set(arms) != set(traces):
        raise SteadyPhaseRejected("missing Paper source arms")
    node = {}
    paper_stable = {}
    for case in ("CARRY", "WAIT_ASSUMED"):
        arm = arms[case]
        tr = traces[case]
        if (
            type(arm) is not dict
            or type(tr) is not dict
            or arm.get("exact_paper_positive_bonus_ticks") != 7
            or arm.get("qualification_go") is not False
            or arm.get("science_go") is not False
            or arm.get("same_world_tick_clock_as_other_world") is not False
        ):
            raise SteadyPhaseRejected("unverified Paper motor cap")
        node[case] = node_positive_transitions_dev(
            tr, sid=arm["session_id"], aid=arm["action_id"]
        )
        speeds = arm.get("matched_positive_speed_by_ordinal_mps")
        powers = arm.get("matched_positive_power_by_ordinal")
        if (
            type(speeds) is not list or len(speeds) != 7
            or type(powers) is not list or len(powers) != 7
        ):
            raise SteadyPhaseRejected("missing original Paper bonus ordinal samples")
        paper_stable[case] = {
            "paper_positive_ordinals": [2, 3, 4, 5, 6, 7],
            "paper_stable_speed_mps": [_measured(v) for v in speeds[1:]],
            "paper_stable_mean_speed_mps":
                statistics.fmean(_measured(v) for v in speeds[1:]),
            "paper_stable_model_powers": [_measured(v) for v in powers[1:]],
            "paper_first_sample_excluded_due_to_lag": True,
            "paper_first_sample_was_zero_allowed": True,
        }
        if any(v <= 0 or v > 1 for v in paper_stable[case]["paper_stable_model_powers"]):
            raise SteadyPhaseRejected("Paper motor power not bounded")
    a, b = paper_stable["CARRY"], paper_stable["WAIT_ASSUMED"]
    aa, bb = node["CARRY"], node["WAIT_ASSUMED"]
    paper_deltas = [vb - va for va, vb in zip(
        a["paper_stable_speed_mps"], b["paper_stable_speed_mps"]
    )]
    shared_node_intervals = min(
        aa["node_consecutive_boosted_intervals"],
        bb["node_consecutive_boosted_intervals"],
    )
    # Never equate Node tick ordinal to Paper tick or one World to the other.
    node_deltas = [
        vb - va for va, vb in zip(
            aa["node_stable_speed_proxy_mps"][:shared_node_intervals],
            bb["node_stable_speed_proxy_mps"][:shared_node_intervals],
        )
    ]
    if shared_node_intervals < 2:
        raise SteadyPhaseRejected("Node stable motor sources not comparable")
    return {
        "classification": "P1_SEVEN_BONUS_TICKS_PAPER_NODE_STABLE_PHASE_DESCRIPTIVE_DEV_ONLY",
        "paper": paper_stable,
        "node": node,
        "paper_stable_speed_delta_by_ordinal_mps": paper_deltas,
        "paper_stable_mean_speed_gain_mps": statistics.fmean(paper_deltas),
        "node_common_stable_intervals": shared_node_intervals,
        "node_speed_proxy_delta_by_ordinal_mps": node_deltas,
        "node_common_stable_mean_speed_proxy_gain_mps": statistics.fmean(node_deltas),
        "raw_original_first_s16_native_displacement_gain_m":
            paired["native_original_s16_displacement_gain_m"],
        "paper_stable_speed_gain_positive": statistics.fmean(paper_deltas) > .1,
        "node_common_speed_gain_positive": statistics.fmean(node_deltas) > .1,
        "paper_first_bonus_sample_excluded": True,
        "node_first_positive_bonus_sample_excluded": True,
        "paper_bonus_count_per_world": 7,
        "original_s49_action_duration_matched": False,
        "world_tick_phase_synchronized": False,
        "native_paper_effect_tick_correspondence_proven": False,
        "node_physics_20hz_nominal_not_attested": True,
        "model_preload_not_true_same_self_recovery": True,
        "causal_fatigue_effect_size_identified": False,
        "physical_l0_dash_capability_admitted": None,
        "new_native_action_issuers": 0,
        "new_native_packet_readers": 0,
        "qualified_r_wait_ticks": 0,
        "qualification_go": False,
        "science_go": False,
    }


def review_p1_steady_phase_worlds_dev(root: Path) -> dict:
    if not isinstance(root, Path) or root.is_symlink() or not root.is_dir():
        raise SteadyPhaseRejected("untrusted source root")
    paired = review_p1_matched_boost_worlds_dev(root)
    node_sources = {}
    for case in ("CARRY", "WAIT_ASSUMED"):
        arm = paired["arms"][case]
        node_path = root / case / "node_speed_attr_boundary_dev.json"
        if node_path.is_symlink() or not node_path.is_file():
            raise SteadyPhaseRejected("Node first native source not found")
        check = review_speed_attr_boundary_dev(
            node_path, session_id=arm["session_id"],
            action_id=arm["action_id"], sync_expected=True,
        )
        if (
            check.get("qualification_go") is not False
            or check.get("node_active_physics_key_dash_seen_count", 0) < 3
            or check.get("native_action_changed") is not False
        ):
            raise SteadyPhaseRejected("Node source-local motor witness invalid")
        try:
            source = node_path.read_bytes()
            node_sources[case] = json.loads(source)
        except (ValueError, OSError) as exc:
            raise SteadyPhaseRejected("source Node witness unreadable") from exc
        node_sources[case]["_local_sha256"] = hashlib.sha256(source).hexdigest()
    result = compare_steady_phase_dev(paired, node_sources)
    result["node_raw_sha256_by_case"] = {
        case: node_sources[case]["_local_sha256"] for case in node_sources
    }
    (root / "p1_stable_phase_motor_review_dev.json").write_text(
        json.dumps(result, sort_keys=True, indent=2) + "\n",
        encoding="utf-8",
    )
    return result


def main() -> int:
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, required=True)
    args = parser.parse_args()
    print(json.dumps(review_p1_steady_phase_worlds_dev(args.root), sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
