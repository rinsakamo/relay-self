"""Original S49 DEV two-World native speed attribute OFF vs ON review.

Both arms preload the SAME P1 model (CARRY). Only the existing,
explicitly DEV-scoped client attribute projection changes. Distinct
disposable World clocks are not synchronized and no true P1 is measured.
"""
from __future__ import annotations

import json
import math
from pathlib import Path

from adapters.mineflayer.s49_paper_forward_dash_dev import PAIR_FATIGUE
from adapters.mineflayer.s49_speed_attr_boundary_dev import review_speed_attr_boundary_dev
from adapters.mineflayer.self_action_evidence import verify_native_action_evidence


class AttributePairRejected(ValueError):
    pass


def _number(x: object) -> float:
    if type(x) not in (int, float) or not math.isfinite(x):
        raise AttributePairRejected("unverified native physical quantity")
    return float(x)


def _one(directory: Path, sync: bool) -> dict:
    if directory.is_symlink() or not directory.is_dir():
        raise AttributePairRejected("missing or redirected disposable World")
    try:
        outer = json.loads((directory / "paper_forward_dash_dev_report.json").read_text())
        original = json.loads((directory / "original_s49_report.json").read_text())
    except (ValueError, OSError) as exc:
        raise AttributePairRejected("missing actual S49 World source") from exc
    if (
        type(outer) is not dict or type(original) is not dict
        or outer.get("status") not in (
            "DEV_PAIR_PAPER_OUTPUT_REAL_WORLD_NO_NATIVE_GAIN",
            "DEV_FORWARD_SPRINT_MOTION_GATED_PAPER_DASH_OBSERVED",
            "DEV_FORWARD_SPRINT_POSITIVE_PAPER_DASH_OBSERVED",
        )
        or outer.get("original_s49_status") != "PASS"
        or original.get("status") != "PASS"
        or original.get("node_exit") != 0 or original.get("server_exit") != 0
        or original.get("runtime") != "PAPER_1_21_8_DISPOSABLE_DEV"
        or original.get("dev_m0_dash_owner") is not True
        or original.get("dev_m0_action_move_step") is not True
        or original.get("real_model_calls") != 0
        or not isinstance(original.get("actual_native_actions"), list)
        or len(original["actual_native_actions"]) != 2
        or outer.get("p1_pair_preloaded_model_dev", {}).get("case") != "CARRY"
        or outer.get("p1_pair_preloaded_model_dev", {}).get("input_fatigue")
           != PAIR_FATIGUE["CARRY"]
        or outer.get("p1_paper_motor_dev", {}).get("fatigue_initial")
           != PAIR_FATIGUE["CARRY"]
        or outer.get("qualification_go") is not False
        or outer.get("science_go") is not False
    ):
        raise AttributePairRejected("model-F or original-S49 World mismatch")
    sid = original["session_id"]
    first, second = original["actual_native_actions"]
    for action in (first, second):
        if action.get("source") != sid or action.get("terminal") != "outcome":
            raise AttributePairRejected("S16 terminal from alien session")
        verify_native_action_evidence(
            action["execution_evidence"], session_id=sid,
            action_id=action["action"], movement_m=action["movement_m"],
            allow_dev_forward=True, allow_dev_sprint=True,
        )
    if (
        original.get("dev_m0_dash_unboosted_actions") != [second["action"]]
        or first["execution_evidence"]["action_ref"] != "MOVE_FORWARD_SPRINT_DEV"
        or second["execution_evidence"]["action_ref"] != "MOVE_FORWARD_SPRINT_DEV"
        or type(original.get("decisions")) is not list
        or len(original["decisions"]) != 3
        or [d.get("selected") for d in original["decisions"]]
           != ["WAIT", "MOVE_AWAY", "MOVE_AWAY"]
        or first["event_seq"] != original["decisions"][1]["event_seq"]
        or first["probe_seq"] != original["decisions"][1]["probe_seq"]
    ):
        raise AttributePairRejected("original L0 or second control mismatch")
    boundary = review_speed_attr_boundary_dev(
        directory / "node_speed_attr_boundary_dev.json",
        session_id=sid, action_id=first["action"], sync_expected=sync,
    )
    if boundary != outer.get("node_speed_attribute_boundary_dev"):
        raise AttributePairRejected("Node attribute boundary report forged")
    obs = first["execution_evidence"]["before_observation"]["snapshot"]
    paper = outer.get("paper", {})
    if (
        not isinstance(paper, dict)
        or paper.get("paper_forward_boost_ticks", 0) < 3
        or outer.get("original_action_distances_m")
           != [first["movement_m"], second["movement_m"]]
    ):
        raise AttributePairRejected("Paper motor did not run")
    return {
        "sync_on": sync, "session_id": sid,
        "first_action_id": first["action"], "first_native_distance_m": _number(first["movement_m"]),
        "second_native_distance_m": _number(second["movement_m"]),
        "first_health": _number(obs["health"]), "first_food": _number(obs["food"]),
        "first_y": _number(obs["position"]["y"]),
        "first_threat_distance_m": _number(original["decisions"][1]["distance_m"]),
        "paper_first_applied_power": _number(outer["p1_paper_motor_dev"]["initial_boost_power"]),
        "paper_boosted_ticks": paper["paper_forward_boost_ticks"],
        "paper_sampled_peak_speed_mps": _number(paper["sampled_peak_server_horizontal_speed_m_s"]),
        "first_node_boundary": boundary,
        "physical_native_gain_in_own_world": (
            outer["status"] != "DEV_PAIR_PAPER_OUTPUT_REAL_WORLD_NO_NATIVE_GAIN"
        ),
        "m0_posted_by_original_s49_only": True,
        "original_native_sources_verified": True,
    }


def compare_attr_pair_dev(off: dict, on: dict) -> dict:
    if (
        type(off) is not dict or type(on) is not dict
        or off.get("sync_on") is not False or on.get("sync_on") is not True
        or off.get("session_id") == on.get("session_id")
        or off.get("first_node_boundary", {}).get("native_sync_enabled") is not False
        or on.get("first_node_boundary", {}).get("native_sync_enabled") is not True
        or not all(x.get("original_native_sources_verified") is True
                   and x.get("m0_posted_by_original_s49_only") is True
                   for x in (off, on))
        or any(abs(_number(off[key]) - _number(on[key])) > epsilon
               for key, epsilon in (
                   ("first_health", .01), ("first_food", .01),
                   ("first_y", .01), ("first_threat_distance_m", .05),
                   ("paper_first_applied_power", .02),
               ))
        or off.get("paper_boosted_ticks", 0) < 3
        or on.get("paper_boosted_ticks", 0) < 3
    ):
        raise AttributePairRejected("cannot isolate same-F speed projection DEV arms")
    on_boundary = on["first_node_boundary"]
    projected_in_client = on_boundary["node_active_physics_key_dash_seen_count"] > 0
    native_delta = _number(on["first_native_distance_m"]) - _number(
        off["first_native_distance_m"]
    )
    peak_delta = _number(on["paper_sampled_peak_speed_mps"]) - _number(
        off["paper_sampled_peak_speed_mps"]
    )
    return {
        "classification": "S49_SAME_P1_F_NATIVE_SPEED_ATTRIBUTE_ON_OFF_WORLD_DIAGNOSTIC_DEV_ONLY",
        "off": off, "on": on,
        "same_explicit_model_initial_fatigue": PAIR_FATIGUE["CARRY"],
        "client_speed_attribute_physicsticked": projected_in_client,
        "client_paper_packet_witness_seen": on_boundary["node_packet_paper_dash_seen_count"] > 0,
        "native_displacement_gain_m": native_delta,
        "paper_measured_peak_speed_gain_mps": peak_delta,
        "native_positive_gain_observed": native_delta > .4 and peak_delta > .5,
        "identifiable_client_attribute_to_physics_failure": (
            not projected_in_client
        ),
        "physical_motor_gain_if_not_separated": "NOT_ESTABLISHED",
        "two_fresh_world_clocks_synchronized": False,
        "actual_longitudinal_p1_recovery_measured": False,
        "real_p1_fatigue_sensor": False,
        "qualified_l0_power_admission": None,
        "extra_native_issuers": 0, "extra_native_readers": 0,
        "qual_go": False, "science_go": False,
    }


def review_attr_world_pair_dev(root: Path) -> dict:
    a = _one(root / "OFF", False)
    b = _one(root / "ON", True)
    result = compare_attr_pair_dev(a, b)
    (root / "attr_projection_world_compare_dev.json").write_text(
        json.dumps(result, sort_keys=True, indent=2) + "\n", encoding="utf-8",
    )
    return result


def main() -> int:
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, required=True)
    args = parser.parse_args()
    print(json.dumps(review_attr_world_pair_dev(args.root), sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
