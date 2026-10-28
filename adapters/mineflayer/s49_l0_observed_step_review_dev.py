"""Four independent original S49 Worlds: fixed vs S16-observed next input.

This DEV reviewer checks genuine original S14/S15/S16 action ownership and
the exact physical second native Action. Separate Worlds do not prove a
population-level motor advantage; no absolute destination or tick sync claimed.
"""
from __future__ import annotations

import json
import math
from pathlib import Path

from adapters.mineflayer.s49_p1_dash_pair_review_dev import _case
from adapters.mineflayer.s49_p1_matched_boost_review_dev import matched_boost_rows_dev

CASES = ("CARRY", "WAIT_ASSUMED")
MODES = ("FIXED", "FEEDBACK")
TARGET_M = 1.0


class S49ObservedFeedbackRejected(ValueError):
    pass


def _load(root: Path, mode: str, case: str) -> dict:
    directory = root / f"{mode}_{case}"
    if directory.is_symlink() or not directory.is_dir():
        raise S49ObservedFeedbackRejected("no independent real World")
    native = _case(directory, case)  # Real typed S16 and full native Paper replay.
    files = [
        directory / "original_s49_report.json",
        directory / "paper_server.log",
    ]
    if any(p.is_symlink() or not p.is_file() or p.stat().st_size > 3_000_000
           for p in files):
        raise S49ObservedFeedbackRejected("missing bounded producer source")
    raw = json.loads(files[0].read_text(encoding="utf-8"))
    actions = raw.get("actual_native_actions", [])
    if not isinstance(actions, list) or len(actions) != 2:
        raise S49ObservedFeedbackRejected("not two original S49 outcomes")
    paper = matched_boost_rows_dev(
        files[1].read_text(encoding="utf-8"),
        session_id=raw["session_id"],
        action_id=actions[0]["action"],
    )
    feedback = raw.get("dev_l0_observed_feedback")
    duration = 0.60
    plan_reason = "FIXED_INPUT_NO_FEEDBACK"
    if mode == "FEEDBACK":
        if (
            type(feedback) is not dict
            or feedback.get("session_id") != raw["session_id"]
            or feedback.get("first_action_id") != actions[0]["action"]
            or feedback.get("second_action_id") != actions[1]["action"]
            or feedback.get("previous_observed_m") != actions[0]["movement_m"]
            or feedback.get("previous_input_s") != 0.60
            or feedback.get("requested_next_step_m") != TARGET_M
            or feedback.get("same_original_S49_issuer") is not True
            or feedback.get("new_native_reader") is not False
            or feedback.get("native_tick_phase_attested") is not False
            or feedback.get("actual_target_reached_attested") is not False
            or feedback.get("qualification_go") is not False
            or feedback.get("science_go") is not False
            or feedback.get("second_actual_outcome") != "outcome"
            or feedback.get("second_actual_s16_m") != actions[1]["movement_m"]
            or feedback.get("goal_reached_attested") is not False
            or feedback.get("world_tick_phase_matched") is not False
        ):
            raise S49ObservedFeedbackRejected("fake, stale or promoted S16 feedback")
        duration = feedback.get("requested_duration_s")
        plan_reason = feedback.get("reason")
        if duration is None:
            if (plan_reason != "DANGER_ORIGINAL_L0_ESCAPE_PRIORITY"
                    or feedback.get("second_input_duration_s") != 0.60):
                raise S49ObservedFeedbackRejected("danger did not preserve escape")
            duration = 0.60
        elif (
            plan_reason != "OBSERVED_SPEED_INPUT_CORRECTION"
            or type(duration) is not float
            or not 0.10 <= duration <= 0.60
            or feedback.get("second_input_duration_s") != duration
            or not math.isclose(
                duration,
                min(0.60, max(0.10, 0.60 * TARGET_M / actions[0]["movement_m"])),
                rel_tol=1e-12,
            )
        ):
            raise S49ObservedFeedbackRejected("second physical input not S16-derived")
        if not math.isclose(
            feedback.get("absolute_second_step_error_m", -1),
            abs(actions[1]["movement_m"] - TARGET_M),
            abs_tol=1e-10,
        ):
            raise S49ObservedFeedbackRejected("S16 feedback result not source-consistent")
    elif (feedback is not None or raw.get("dev_l0_observed_next_step_m") is not None):
        raise S49ObservedFeedbackRejected("fixed baseline contaminated by feedback")
    if (
        raw.get("status") != "PASS"
        or paper.get("exact_paper_positive_bonus_ticks") != 7
        or paper.get("paper_total_gait_ticks") != 13
        or native["first_native_distance_m"] != actions[0]["movement_m"]
        or native["second_unboosted_distance_m"] != actions[1]["movement_m"]
    ):
        raise S49ObservedFeedbackRejected("original native or Paper source mismatch")
    return {
        "mode": mode, "model_case": case,
        "session_id": raw["session_id"],
        "world_uuid": native["paper_world_uuid"],
        "first_action_id": actions[0]["action"],
        "second_action_id": actions[1]["action"],
        "first_s16_m": actions[0]["movement_m"],
        "second_s16_m": actions[1]["movement_m"],
        "requested_second_step_m": TARGET_M,
        "second_input_duration_s": duration,
        "second_error_m": abs(actions[1]["movement_m"] - TARGET_M),
        "feedback_reason": plan_reason,
        "paper_first_positive_boost_ticks": 7,
        "paper_first_gait_ticks": 13,
        "original_action_issuer_added": 0,
        "native_reader_added": 0,
        "qualification_go": False,
        "science_go": False,
    }


def review_worlds(root: Path) -> dict:
    if not isinstance(root, Path) or root.is_symlink() or not root.is_dir():
        raise S49ObservedFeedbackRejected("invalid World source root")
    arms = {
        f"{mode}_{case}": _load(root, mode, case)
        for mode in MODES for case in CASES
    }
    if (
        len({x["session_id"] for x in arms.values()}) != 4
        or len({x["world_uuid"] for x in arms.values()}) != 4
    ):
        raise S49ObservedFeedbackRejected("duplicate native session or World")
    comparisons = {}
    for case in CASES:
        fixed = arms[f"FIXED_{case}"]
        feedback = arms[f"FEEDBACK_{case}"]
        comparisons[case] = {
            "feedback_minus_fixed_second_s16_m":
                feedback["second_s16_m"] - fixed["second_s16_m"],
            "feedback_minus_fixed_absolute_target_error_m":
                feedback["second_error_m"] - fixed["second_error_m"],
            "fixed_second_duration_s": fixed["second_input_duration_s"],
            "feedback_second_duration_s": feedback["second_input_duration_s"],
            "closer_to_target_in_this_world_pair":
                feedback["second_error_m"] < fixed["second_error_m"],
            "both_worlds_independent": True,
        }
    result = {
        "classification": "S49_L0_S16_OBSERVED_NEXT_INPUT_FOUR_WORLD_DEV_ONLY",
        "arms": arms, "per_model_comparisons": comparisons,
        "native_feedback_from_prior_original_S16": True,
        "original_L0_and_S14_S15_S16_retained": True,
        "observed_tick_count_matched": False,
        "new_action_issuers": 0,
        "new_packet_readers": 0,
        "target_is_relative_next_step_not_global_destination": True,
        "feedback_causally_better_proven": False,
        "real_wait_recovery_attested": False,
        "qualification_go": False, "science_go": False,
    }
    (root / "s49_l0_observed_step_comparison_dev.json").write_text(
        json.dumps(result, sort_keys=True, indent=2) + "\n", encoding="utf8"
    )
    return result


if __name__ == "__main__":
    import argparse
    p = argparse.ArgumentParser()
    p.add_argument("--root", type=Path, required=True)
    args = p.parse_args()
    print("S49_L0_FEEDBACK_FOUR_WORLD_DEV", json.dumps(
        review_worlds(args.root), sort_keys=True,
    ))
