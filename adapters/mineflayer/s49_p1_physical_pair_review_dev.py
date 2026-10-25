"""DEV only: compare two independently recorded original S49 motor World runs.

Matches *observed* control preconditions. Different fresh Minecraft Worlds
can never prove identical initial tick histories or causal fatigue. The
original S49 runner must have closed six L0 epochs and four Actions.
"""
from __future__ import annotations

import json
import math
from pathlib import Path

from adapters.mineflayer.m02_paper_dev.s50_boundary import BoundaryRejected
from adapters.mineflayer.s49_p1_physical_pair_dev import BASELINE, STRESS
from adapters.mineflayer.self_action_evidence import verify_native_action_evidence

DECISIONS = ["WAIT", "MOVE_AWAY", "MOVE_AWAY", "MOVE_AWAY", "WAIT", "MOVE_AWAY"]


def _extract(report: dict, source: dict, scenario: str) -> dict:
    if (not isinstance(report, dict) or not isinstance(source, dict)
            or report.get("status") != "PASS" or source.get("status") != "PASS"
            or report.get("classification")
            != "DEV_WORLD_SIXTH_ORIGINAL_S49_P1_MOTOR_TIMING_APPLIED"
            or source.get("classification")
            != "DEV_ONLY_S49_SIXTH_MOTOR_DEV_AFTER_FIFTH_WAIT"
            or report.get("motor_scenario") != scenario
            or source.get("node_exit") != 0 or source.get("server_exit") != 0
            or report.get("qualification_go") is not False
            or report.get("science_go") is not False):
        raise BoundaryRejected("original S49/pair World DEV source not PASS")
    decisions = source.get("decisions")
    actions = source.get("actual_native_actions")
    trace = source.get("source_pair_trace")
    if (not isinstance(decisions, list) or not isinstance(actions, list)
            or not isinstance(trace, list) or len(actions) != 4
            or len(trace) != 6 or len(decisions) != 6
            or [d["selected"] for d in decisions] != DECISIONS
            or [d["issued"] for d in decisions]
            != [False, True, True, True, False, True]
            or len({d["entity_id"] for d in decisions}) != 6
            or source.get("session_id") != report.get("original_s49_session_id")
            or source.get("minecraft_version") != "1.21.8"
            or source.get("runtime") != "PAPER_1_21_8_DISPOSABLE_DEV"):
        raise BoundaryRejected("sixth owner/session geometry or Action list invalid")
    for i, action in enumerate(actions):
        if (action.get("terminal") != "outcome"
                or action.get("source") != source["session_id"]
                or action.get("event_seq")
                != decisions[(1, 2, 3, 5)[i]]["event_seq"]
                or action.get("probe_seq")
                != decisions[(1, 2, 3, 5)[i]]["probe_seq"]
                or not isinstance(action.get("movement_m"), float)
                or not math.isfinite(action["movement_m"])
                or action["movement_m"] < 0.05):
            raise BoundaryRejected("original native Action OUTCOME failed")
        verify_native_action_evidence(
            action["execution_evidence"],
            session_id=source["session_id"],
            action_id=action["action"],
            movement_m=action["movement_m"],
        )
    sixth = actions[-1]
    view = report.get("sixth_motor_action_dev")
    sensitivity = report.get("sixth_motor_sensitivity_dev")
    gait = report.get("fifth_l0_p1_gait_compare_dev")
    if (not isinstance(view, dict) or not isinstance(sensitivity, dict)
            or not isinstance(gait, dict)
            or sensitivity.get("scenario") != scenario
            or view.get("dev_motor_sensitivity_scenario") != scenario
            or view.get("action_id") != sixth["action"]
            or view.get("observed_distance_m") != sixth["movement_m"]
            or view.get("same_original_native_probe_seq")
            != decisions[5]["probe_seq"]
            or view.get("p1_model_source_fifth_seq")
            != decisions[4]["probe_seq"]
            or sensitivity.get("fifth_native_seq")
            != decisions[4]["probe_seq"]
            or sensitivity.get("third_action_id") != actions[2]["action"]
            or sensitivity.get("third_observed_move_m") != actions[2]["movement_m"]
            or sensitivity.get("duration_s")
            != view.get("dev_model_conditioned_duration_s")
            or sensitivity.get("hypothetical_profile_sha256")
            != view.get("dev_motor_sensitivity_profile_sha256")
            or gait.get("original_p1_model_sha256")
            != report["third_move_p1_self_body_dev"]["p1_profile_sha256"]
            or view.get("unmodified_original_action_duration_s") != 0.2
            or view.get("command_duration_modified") is not True
            or view.get("observed_distance_causal_change_attested") is not False
            or view.get("new_action_issuer") is not False
            or view.get("new_grant") is not False
            or sensitivity.get("native_fatigue_measured") is not False
            or sensitivity.get("action_permission") is not False):
        raise BoundaryRejected("scoped original sixth motor sensitivity mismatch")
    evidence = sixth["execution_evidence"]
    before = evidence["before_observation"]
    snapshot = before["snapshot"]
    coverage = snapshot["nearby_entities_coverage"]
    zombies = [e for e in snapshot["nearby_entities"] if e["name"] == "zombie"]
    if (before["session_id"] != source["session_id"]
            or coverage["truncated"] is not False
            or len(zombies) != 1
            or not math.isfinite(zombies[0]["distance"])
            or abs(zombies[0]["distance"] - 2.0) > 0.05
            or snapshot["health"] <= 0 or snapshot["food"] <= 0):
        raise BoundaryRejected("source shows unmatched/unsafe sixth physical precondition")
    return {
        "scenario": scenario,
        "session_id": source["session_id"],
        "sixth_action_id": sixth["action"],
        "pre_move_zombie_distance_m": zombies[0]["distance"],
        "pre_move_health": snapshot["health"],
        "pre_move_food": snapshot["food"],
        "pre_move_y": snapshot["position"]["y"],
        "third_move_m": actions[2]["movement_m"],
        "actual_duration_s": view["dev_model_conditioned_duration_s"],
        "measured_sixth_displacement_m": sixth["movement_m"],
        "hypothetical_model_fatigue": sensitivity["hypothetical_fatigue"],
        "hypothetical_model_efficiency": sensitivity["hypothetical_efficiency"],
        "hypothetical_move_rate": sensitivity["hypothetical_move_rate_per_block"],
        "exact_source_native_action": True,
        "s16_terminal_outcome": True,
    }


def compare_pair_dev(base_report: dict, base_source: dict,
                     stress_report: dict, stress_source: dict) -> dict:
    base = _extract(base_report, base_source, BASELINE)
    stress = _extract(stress_report, stress_source, STRESS)
    if (base["session_id"] == stress["session_id"]
            or base_source["paper_asset_sha256"]
            != stress_source["paper_asset_sha256"]
            or not base["actual_duration_s"] > stress["actual_duration_s"]
            or not stress["hypothetical_model_fatigue"]
            > base["hypothetical_model_fatigue"]
            or abs(base["pre_move_zombie_distance_m"]
                   - stress["pre_move_zombie_distance_m"]) > 0.05
            or abs(base["pre_move_health"] - stress["pre_move_health"]) > 1e-9
            or abs(base["pre_move_food"] - stress["pre_move_food"]) > 1e-9
            or abs(base["pre_move_y"] - stress["pre_move_y"]) > 1e-9
            or abs(base["third_move_m"] - stress["third_move_m"]) > 0.10):
        raise BoundaryRejected("scripted World preconditions not matched or distinct")
    delta = stress["measured_sixth_displacement_m"] - base[
        "measured_sixth_displacement_m"
    ]
    # Difference is descriptive only: two fresh processes, one trial each.
    return {
        "status": "DEV_PAIRED_SCRIPTED_WORLD_MEASUREMENT",
        "classification": "DEV_ONLY_PHYSICAL_MOTOR_DISTANCE_COMPARISON",
        "base": base, "stress": stress,
        "duration_delta_s": (
            stress["actual_duration_s"] - base["actual_duration_s"]
        ),
        "observed_distance_delta_m": delta,
        "absolute_distance_delta_m": abs(delta),
        "physical_distance_difference_observed": abs(delta) >= 0.05,
        "observed_preconditions_matched": True,
        "world_tick_histories_identical": False,
        "physical_fatigue_measured": False,
        "p1_rate_stress_is_calibrated": False,
        "pair_count": 1,
        "distance_difference_causally_attributed_to_fatigue": False,
        "source_bound_tick": None,
        "r_admitted_wait_ticks": 0,
        "s10_updates": 0,
        "qualification_go": False,
        "science_go": False,
    }


def main() -> int:
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, required=True)
    args = parser.parse_args()
    root = args.root.resolve()
    try:
        inputs = []
        for scenario in (BASELINE, STRESS):
            p = root / scenario
            inputs.extend([
                json.loads((p / "world_first_dev_report.json").read_text()),
                json.loads((p / "original_s49_report.json").read_text()),
            ])
        result = compare_pair_dev(*inputs)
        out = root / "paired_world_review_dev.json"
        out.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n")
        print("S49_P1_SCRIPTED_TWO_WORLD_MOTOR_DEV_PASS", json.dumps(result, sort_keys=True))
        return 0
    except (BoundaryRejected, KeyError, TypeError, ValueError, OSError) as exc:
        print("S49_P1_SCRIPTED_TWO_WORLD_MOTOR_DEV_BLOCKED", type(exc).__name__, str(exc))
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
