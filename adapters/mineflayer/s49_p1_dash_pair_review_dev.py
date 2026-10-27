"""DEV two fresh World Paper P1 preload arms: validate real motor sensitivity.

An earlier Paper World supplied two *hypothetical* F values. Each NEW
independent World uses one preloaded value; this is not a longitudinal WAIT
recovery study, P1 sensor, randomized experiment or R source attestation.
"""
from __future__ import annotations

import json
import math
from pathlib import Path

from adapters.mineflayer.s49_paper_forward_dash_dev import (
    PAIR_FATIGUE,
    PAIR_SOURCE_DIGEST,
    audit_native_paper_p1_dev,
)
from adapters.mineflayer.self_action_evidence import verify_native_action_evidence


class P1DashPairRejected(ValueError):
    """Source or actuator conditions are not comparable DEV records."""


def _finite(v: object) -> float:
    if type(v) not in (float, int) or not math.isfinite(v):
        raise P1DashPairRejected("missing finite physical motor measurement")
    return float(v)


def _case(directory: Path, case: str) -> dict:
    if directory.is_symlink() or not directory.is_dir():
        raise P1DashPairRejected("missing real World trial directory")
    try:
        report = json.loads((directory / "paper_forward_dash_dev_report.json").read_text())
        original = json.loads((directory / "original_s49_report.json").read_text())
        raw = (directory / "paper_server.log").read_text(encoding="utf-8")
    except (OSError, ValueError) as exc:
        raise P1DashPairRejected("incomplete original World reports") from exc
    if (
        report.get("status") not in (
            "DEV_FORWARD_SPRINT_POSITIVE_PAPER_DASH_OBSERVED",
            "DEV_FORWARD_SPRINT_MOTION_GATED_PAPER_DASH_OBSERVED",
            "DEV_PAIR_PAPER_OUTPUT_REAL_WORLD_NO_NATIVE_GAIN",
        )
        or original.get("status") != "PASS"
        or original.get("node_exit") != 0 or original.get("server_exit") != 0
        or original.get("runtime") != "PAPER_1_21_8_DISPOSABLE_DEV"
        or original.get("dev_sprint_motor") is not True
        or original.get("dev_m0_dash_owner") is not True
        or original.get("dev_m0_action_move_step") is not True
        or original.get("real_model_calls") != 0
        or not isinstance(original.get("actual_native_actions"), list)
        or len(original["actual_native_actions"]) != 2
        or report.get("qualification_go") is not False
        or report.get("science_go") is not False
        or report.get("p1_pair_preloaded_model_dev") != {
            "case": case,
            "input_fatigue": PAIR_FATIGUE[case],
            "frozen_candidate_source_sha256": PAIR_SOURCE_DIGEST,
            "model_preloaded_in_new_disposable_world": True,
            "actual_same_self_wait_recovery_attested": False,
            "production_p1_state_updated": False,
            "additional_action_issuers": 0,
            "qualification_go": False,
            "science_go": False,
        }
    ):
        raise P1DashPairRejected("DEV preload source not a successful original World")
    if report["status"] == "DEV_PAIR_PAPER_OUTPUT_REAL_WORLD_NO_NATIVE_GAIN":
        if (report.get("physical_gain_dev", "missing") is not None
                or report.get("native_gain_unobserved_reason")
                   != "Paper attribute on, but native DASH gain absent"):
            raise P1DashPairRejected("negative native response misclassified")
    else:
        if not isinstance(report.get("physical_gain_dev"), dict):
            raise P1DashPairRejected("positive native response lacked evidence")
    actions = original["actual_native_actions"]
    sid = original["session_id"]
    for action in actions:
        if action.get("terminal") != "outcome" or action.get("source") != sid:
            raise P1DashPairRejected("native S16 original terminal absent")
        verify_native_action_evidence(
            action["execution_evidence"], session_id=sid, action_id=action["action"],
            movement_m=action["movement_m"], allow_dev_forward=True,
            allow_dev_sprint=True,
        )
    first, second = actions
    if (
        first["execution_evidence"]["action_ref"] != "MOVE_FORWARD_SPRINT_DEV"
        or second["execution_evidence"]["action_ref"] != "MOVE_FORWARD_SPRINT_DEV"
        or original.get("dev_m0_dash_unboosted_actions") != [second["action"]]
        or report.get("p1_paper_motor_dev", {}).get("fatigue_initial")
            != PAIR_FATIGUE[case]
        or report.get("m0_debit_classification")
           != "S49_NATIVE_OUTCOME_TWO_M0_MOVE_STEPS_PAPER_BRACKET_DEV_ONLY"
    ):
        raise P1DashPairRejected("DEV pair arms or unboosted control mismatch")
    replay = audit_native_paper_p1_dev(
        raw, action_id=first["action"], session_id=sid,
        model_initial=PAIR_FATIGUE[case],
    )
    if replay != report["p1_paper_motor_dev"]:
        raise P1DashPairRejected("Paper P1 model replay not source reproducible")
    paper = report.get("paper")
    if (
        not isinstance(paper, dict)
        or paper.get("paper_forward_boost_ticks", 0) < 3
        or paper.get("m0_posted") is not False
        or paper.get("p1_native_updated") is not False
    ):
        raise P1DashPairRejected("original forward-only Paper modifier not proven")
    rows = []
    for line in raw.splitlines():
        mark = "S49_DASH_DEV_TICK "
        if mark not in line:
            continue
        fields = dict(
            token.split("=", 1) for token in line.split(mark, 1)[1].split()
            if token.count("=") == 1
        )
        if fields.get("action_id") != first["action"]:
            continue
        if (
            fields.get("session_id") != sid
            or fields.get("world") != report["paper_action_bracket"]["world_uuid"]
            or fields.get("player_uuid") != report["paper_action_bracket"]["player_uuid"]
        ):
            raise P1DashPairRejected("source Paper actor changed")
        if fields.get("modifier_applied") == "true":
            rows.append(fields)
    if len(rows) != paper["paper_forward_boost_ticks"] or len(rows) < 3:
        raise P1DashPairRejected("lost actual Paper positive boost ticks")
    powers = [_finite(float(row["p1_current_applied_power"])) for row in rows]
    speeds = [_finite(float(row["sampled_speed_mps"])) for row in rows]
    for power in powers:
        if not 0 < power <= 1:
            raise P1DashPairRejected("invalid measured Paper applied output")
    if (
        any(speed < 0 or speed > 100 for speed in speeds)
        or not all(0 < float(row["sampled_speed_mps"]) < 100 for row in rows)
    ):
        raise P1DashPairRejected("invalid actual Paper movement speeds")
    before = first["execution_evidence"]["before_observation"]["snapshot"]
    choices = original.get("decisions")
    if (
        not isinstance(choices, list) or len(choices) != 3
        or [c.get("selected") for c in choices] != ["WAIT", "MOVE_AWAY", "MOVE_AWAY"]
        or any(x.get("issued") is not True for x in choices[1:])
        or choices[1].get("event_seq") != first.get("event_seq")
        or choices[1].get("probe_seq") != first.get("probe_seq")
        or _finite(choices[1].get("distance_m")) >= 4
    ):
        raise P1DashPairRejected("foreign original L0 stimulus")
    return {
        "case": case, "session_id": sid,
        "first_action_id": first["action"],
        "first_native_distance_m": _finite(first["movement_m"]),
        "second_unboosted_distance_m": _finite(second["movement_m"]),
        "first_before_y": _finite(before["position"]["y"]),
        "first_threat_distance_m": _finite(choices[1]["distance_m"]),
        "first_native_health": _finite(before["health"]),
        "first_native_food": _finite(before["food"]),
        "paper_world_uuid": report["paper_action_bracket"]["world_uuid"],
        "paper_boost_count": len(rows),
        "paper_first_applied_power": powers[0],
        "paper_mean_applied_power": sum(powers) / len(powers),
        "paper_peak_sampled_speed_mps": max(speeds),
        "paper_mean_boost_sampled_speed_mps": sum(speeds) / len(speeds),
        "preloaded_hypothetical_fatigue": PAIR_FATIGUE[case],
        "actual_source_frames_verified": True,
        "model_replay_verified": True,
        "native_boost_relative_gain_gate_passed": (
            report["status"] != "DEV_PAIR_PAPER_OUTPUT_REAL_WORLD_NO_NATIVE_GAIN"
        ),
    }


def compare_p1_pair_dev(base: dict, post: dict) -> dict:
    if (
        type(base) is not dict or type(post) is not dict
        or base.get("case") != "CARRY" or post.get("case") != "WAIT_ASSUMED"
        or base.get("session_id") == post.get("session_id")
        or base.get("paper_world_uuid") == post.get("paper_world_uuid")
        or not all(x.get("actual_source_frames_verified") is True
                   and x.get("model_replay_verified") is True
                   for x in (base, post))
        or base.get("preloaded_hypothetical_fatigue") != PAIR_FATIGUE["CARRY"]
        or post.get("preloaded_hypothetical_fatigue") != PAIR_FATIGUE["WAIT_ASSUMED"]
        or any(abs(_finite(base[field]) - _finite(post[field])) > tol
               for field, tol in (
                   ("first_before_y", 0.01),
                   ("first_threat_distance_m", 0.05),
                   ("first_native_health", 0.01),
                   ("first_native_food", 0.01),
               ))
    ):
        raise P1DashPairRejected("original native preconditions not comparable")
    low, high = (_finite(base["paper_first_applied_power"]),
                 _finite(post["paper_first_applied_power"]))
    if not (0 < low < high <= 1.0 and high - low > .1):
        raise P1DashPairRejected("preloaded single P1 failed to separate applied power")
    distance_delta = _finite(post["first_native_distance_m"]) - _finite(
        base["first_native_distance_m"]
    )
    speed_delta = _finite(post["paper_mean_boost_sampled_speed_mps"]) - _finite(
        base["paper_mean_boost_sampled_speed_mps"]
    )
    return {
        "classification": "P1_TWO_FRESH_WORLD_PRELOADED_MODEL_MOTOR_SENSITIVITY_DEV_ONLY",
        "prior_p1_model_source_sha256": PAIR_SOURCE_DIGEST,
        "carry_world": base,
        "wait_assumed_world": post,
        "paper_applied_power_gain": high - low,
        "measured_first_native_distance_delta_m": distance_delta,
        "measured_paper_boost_speed_delta_mps": speed_delta,
        "physical_output_difference_observed": (
            distance_delta > .15 and speed_delta > .2
        ),
        "physical_output_if_no_clear_separation": "NOT_ESTABLISHED",
        "same_scripted_stimulus": True,
        "world_ticks_phase_matched": False,
        "same_self_longitudinal_wait_recovery": False,
        "actual_p1_fatigue_observed": False,
        "model_initial_value_was_preloaded_not_lived": True,
        "distance_causally_attributed_to_wait_recovery": False,
        "physically_qualified_l0_power_admission": None,
        "new_action_issuers": 0,
        "r_qualified_wait_ticks": 0,
        "qualification_go": False,
        "science_go": False,
    }


def review_p1_world_pair_dev(root: Path) -> dict:
    carry = _case(root / "CARRY", "CARRY")
    post = _case(root / "WAIT_ASSUMED", "WAIT_ASSUMED")
    result = compare_p1_pair_dev(carry, post)
    (root / "p1_dash_two_world_sensitivity_review_dev.json").write_text(
        json.dumps(result, sort_keys=True, indent=2) + "\n",
        encoding="utf-8",
    )
    return result


def main() -> int:
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, required=True)
    args = parser.parse_args()
    print(json.dumps(review_p1_world_pair_dev(args.root), sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
