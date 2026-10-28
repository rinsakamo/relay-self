"""Four disposable original-S49 Worlds: Node attribute observer ON/OFF DEV.

Only S49_SPEED_ATTR_BOUNDARY_DEV_ONLY is disabled for OFF cases. The native
movement-speed projection remains ON in all arms; the unmodified Paper plugin
still supplies exactly seven speed-modifier callbacks.  No Node tick or phase
equivalence is inferred from Paper logs when the Node observer is OFF.
"""
from __future__ import annotations

import hashlib
import json
import math
from pathlib import Path

from adapters.mineflayer.s49_p1_dash_pair_review_dev import _case, compare_p1_pair_dev
from adapters.mineflayer.s49_p1_matched_boost_review_dev import matched_boost_rows_dev
from adapters.mineflayer.s49_speed_attr_boundary_dev import (
    review_speed_attr_boundary_dev,
)

ARMS = ("ON_CARRY", "OFF_CARRY", "OFF_WAIT_ASSUMED", "ON_WAIT_ASSUMED")
CASES = ("CARRY", "WAIT_ASSUMED")


class P1AttributeTraceABRejected(ValueError):
    pass


def summarize_trace_ab_dev(arms: dict[str, dict]) -> dict:
    """Compare source-verified observations without fabricating OFF Node ticks."""
    if type(arms) is not dict or set(arms) != set(ARMS):
        raise P1AttributeTraceABRejected("four independent original Worlds required")
    sessions, worlds = set(), set()
    for name in ARMS:
        arm = arms[name]
        mode, case = name.split("_", 1)
        if (
            type(arm) is not dict
            or arm.get("mode") != mode or arm.get("case") != case
            or arm.get("first_action_id") is None
            or type(arm.get("session_id")) is not str
            or type(arm.get("world_uuid")) is not str
            or arm.get("native_action_count") != 2
            or arm.get("original_s49_source_verified") is not True
            or arm.get("speed_attribute_projection_enabled") is not True
            or arm.get("original_s49_action_owner_unchanged") is not True
            or arm.get("paper_positive_boost_ticks") != 7
            or arm.get("paper_original_owner_release") is not True
            or arm.get("node_attribute_observer_enabled") is not (mode == "ON")
            or arm.get("node_attribute_trace_file_exists") is not (mode == "ON")
            or arm.get("qualification_go") is not False
            or arm.get("science_go") is not False
        ):
            raise P1AttributeTraceABRejected(f"{name} source or control changed")
        if (
            type(arm.get("first_native_distance_m")) not in (int, float)
            or not math.isfinite(arm["first_native_distance_m"])
            or type(arm.get("paper_mean_positive_speed_mps")) not in (int, float)
            or not math.isfinite(arm["paper_mean_positive_speed_mps"])
        ):
            raise P1AttributeTraceABRejected("invalid real motor measurement")
        if mode == "OFF":
            if arm.get("node_active_physics_ticks") is not None:
                raise P1AttributeTraceABRejected("invented OFF Node physics ticks")
            if arm.get("node_visible_dash_ticks") is not None:
                raise P1AttributeTraceABRejected("invented OFF DASH visibility")
        elif (
            type(arm.get("node_active_physics_ticks")) is not int
            or arm["node_active_physics_ticks"] < 1
            or type(arm.get("node_visible_dash_ticks")) is not int
            or not 1 <= arm["node_visible_dash_ticks"] <= arm["node_active_physics_ticks"]
        ):
            raise P1AttributeTraceABRejected("missing ON native physics source")
        sessions.add(arm["session_id"])
        worlds.add(arm["world_uuid"])
    if len(sessions) != 4 or len(worlds) != 4:
        raise P1AttributeTraceABRejected("duplicate or replayed World identities")

    case_deltas = {}
    for case in CASES:
        on, off = arms["ON_" + case], arms["OFF_" + case]
        case_deltas[case] = {
            "off_minus_on_first_s16_distance_m": (
                off["first_native_distance_m"] - on["first_native_distance_m"]
            ),
            "off_minus_on_paper_positive_speed_mps": (
                off["paper_mean_positive_speed_mps"]
                - on["paper_mean_positive_speed_mps"]
            ),
            "on_node_active_physics_ticks": on["node_active_physics_ticks"],
            "on_node_visible_dash_ticks": on["node_visible_dash_ticks"],
            "off_node_physics_ticks": None,
            "off_node_visible_dash_ticks": None,
            "exact_phase_matched": False,
        }
    return {
        "classification": "P1_NODE_ATTRIBUTE_OBSERVER_ON_OFF_FOUR_WORLD_DEV_ONLY",
        "arms": arms,
        "per_model_on_off_observations": case_deltas,
        "node_trace_off_has_no_node_tick_attestation": True,
        "velocity_projection_identical_and_enabled_in_all_arms": True,
        "paper_seven_positive_modifier_callbacks_in_all_arms": True,
        "observed_difference_isolated_to_trace": False,
        "observer_causally_responsible_for_delta_proven": False,
        "worlds_are_independent_not_randomized": True,
        "model_preloads_not_actual_same_self_recovery": True,
        "paper_node_phase_synchronized": False,
        "native_action_tick_count_controlled": False,
        "new_action_issuers": 0,
        "new_native_readers": 0,
        "additional_p1_m0_posts": 0,
        "qualification_go": False,
        "science_go": False,
    }


def _load_arm(root: Path, name: str) -> dict:
    mode, case = name.split("_", 1)
    directory = root / name
    if directory.is_symlink() or not directory.is_dir():
        raise P1AttributeTraceABRejected("missing disposable World")
    native = _case(directory, case)  # Existing original S15/S16 & Paper replay.
    def read(name_: str) -> dict:
        f = directory / name_
        if f.is_symlink() or not f.is_file() or f.stat().st_size > 1_500_000:
            raise P1AttributeTraceABRejected("missing/bounded native evidence")
        return json.loads(f.read_text(encoding="utf-8"))
    report = read("paper_forward_dash_dev_report.json")
    original = read("original_s49_report.json")
    rawpath = directory / "paper_server.log"
    if rawpath.is_symlink() or not rawpath.is_file():
        raise P1AttributeTraceABRejected("Paper producer log absent")
    raw = rawpath.read_text(encoding="utf-8")
    first_action = original["actual_native_actions"][0]["action"]
    sid = original["session_id"]
    paper = matched_boost_rows_dev(raw, action_id=first_action, session_id=sid)
    flags = report.get("p1_trace_ab_dev")
    if (
        type(flags) is not dict
        or flags.get("speed_attribute_projection_enabled") is not True
        or flags.get("node_attribute_observer_enabled") is not (mode == "ON")
        or flags.get("node_attribute_trace_file_exists") is not (mode == "ON")
        or flags.get("sole_original_s49_action_owner_unchanged") is not True
        or flags.get("native_trace_write_during_first_action") is not False
        or flags.get("qualification_go") is not False
        or flags.get("science_go") is not False
        or paper.get("world") != native["paper_world_uuid"]
        or paper.get("exact_paper_positive_bonus_ticks") != 7
    ):
        raise P1AttributeTraceABRejected("source provenance or isolation changed")
    tracepath = directory / "node_speed_attr_boundary_dev.json"
    if tracepath.is_symlink() or tracepath.exists() != (mode == "ON"):
        raise P1AttributeTraceABRejected("Node trace presence disagrees with mode")
    node_ticks = dash_ticks = None
    if mode == "ON":
        result = review_speed_attr_boundary_dev(
            tracepath, session_id=sid, action_id=first_action,
            sync_expected=True,
        )
        if result.get("qualification_go") is not False:
            raise P1AttributeTraceABRejected("promoted Node boundary result")
        node_ticks = result["node_physics_ticks_sampled"]
        dash_ticks = result["node_active_physics_key_dash_seen_count"]
    return {
        "mode": mode, "case": case,
        "first_action_id": first_action,
        "session_id": sid,
        "world_uuid": native["paper_world_uuid"],
        "native_action_count": len(original["actual_native_actions"]),
        "original_s49_source_verified": True,
        "speed_attribute_projection_enabled": True,
        "original_s49_action_owner_unchanged": True,
        "paper_positive_boost_ticks": paper["exact_paper_positive_bonus_ticks"],
        "paper_total_gait_ticks": paper["paper_total_gait_ticks"],
        "paper_first_positive_index": paper["positive_first_index"],
        "paper_mean_positive_speed_mps": paper["matched_positive_speed_mean_mps"],
        "paper_mean_positive_power": sum(paper["matched_positive_power_by_ordinal"]) / 7,
        "paper_original_owner_release": True,
        "paper_log_sha256": hashlib.sha256(raw.encode("utf-8")).hexdigest(),
        "first_native_distance_m": native["first_native_distance_m"],
        "second_unboosted_distance_m": native["second_unboosted_distance_m"],
        "node_attribute_observer_enabled": mode == "ON",
        "node_attribute_trace_file_exists": mode == "ON",
        "node_active_physics_ticks": node_ticks,
        "node_visible_dash_ticks": dash_ticks,
        "qualification_go": False,
        "science_go": False,
    }


def review_trace_ab_worlds_dev(root: Path) -> dict:
    if not isinstance(root, Path) or root.is_symlink() or not root.is_dir():
        raise P1AttributeTraceABRejected("untrusted DEV experiment root")
    arms = {name: _load_arm(root, name) for name in ARMS}
    # Pure existing comparison still verifies both same-model stimulus
    # preconditions for each ON/OFF group and deliberately synthetic P1 input.
    for mode in ("ON", "OFF"):
        prefix = mode + "_"
        lhs = _case(root / (prefix + "CARRY"), "CARRY")
        rhs = _case(root / (prefix + "WAIT_ASSUMED"), "WAIT_ASSUMED")
        compare_p1_pair_dev(lhs, rhs)
    result = summarize_trace_ab_dev(arms)
    (root / "p1_speed_attr_trace_ab_comparison_dev.json").write_text(
        json.dumps(result, sort_keys=True, indent=2) + "\n", encoding="utf-8"
    )
    return result


def main() -> int:
    import argparse

    p = argparse.ArgumentParser()
    p.add_argument("--root", required=True, type=Path)
    args = p.parse_args()
    print("P1_ATTR_OBSERVER_TRACE_AB_DEV_RESULT", json.dumps(
        review_trace_ab_worlds_dev(args.root), sort_keys=True,
    ))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
