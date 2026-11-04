"""Post-World original P1 default vs frozen slow recovery DEV comparison.

Both evaluations consume the SAME immutable original Paper log + original S49
report; retrospective results never enter the preceding online L0 decision.
"""
from __future__ import annotations

import argparse
import json
import math
from pathlib import Path

from tools.bug0_s49_p1_paper_model_eval import evaluate_source

EXPECTED_CLASSIFICATION = "DEV_ONLY_S49_P1_EXPERIMENTAL_SENSOR_PROSPECTIVE_REST"


def compare(report: dict, paper_log: str, *, p1_checkout: Path) -> dict:
    if report.get("status") != "PASS" or report.get("classification") != EXPECTED_CLASSIFICATION:
        raise ValueError("one exact original DEV World required")
    sensor = report.get("prospective_p1_sensor")
    join = report.get("prospective_p1_s49_join")
    if not isinstance(sensor, dict) or not isinstance(join, dict):
        raise ValueError("no prospective original L0 P1 sensor/REST evidence")
    if (
        sensor.get("source_kind")
            != "PAPER_PRE_DECISION_CALLBACK_P1_VIRTUAL_SENSOR_DEV"
        or sensor.get("request_rest") is not True
        or sensor.get("source_post_rest_lookahead_used") is not False
        or sensor.get("experimental_wait_recovery_per_tick") != 0.002
        or sensor.get("original_default_wait_recovery_per_tick") != 0.1
        or sensor.get("original_P1_runtime_state_installed") is not False
        or join.get("status") != "DEV_NONDEFAULT_PROFILE_MODEL_SENSOR_REST_CHOSEN"
        or join.get("source_future_read_for_decision") is not False
        or join.get("independent_physical_fatigue_recovery") is not False
        or report.get("rest_choice", {}).get("selected") != "REST"
        or report.get("rest_choice", {}).get("reason")
            != "REST_INTENT_ONLY_P1_WAIT_UNATTESTED"
    ):
        raise ValueError("prospective P1 sensor cannot be silently substituted")
    standard = evaluate_source(
        report, paper_log, p1_checkout=p1_checkout,
    )
    experimental = evaluate_source(
        report, paper_log, p1_checkout=p1_checkout,
        experimental_wait_rate=0.002,
    )
    if (
        standard["model_profile_kind"] != "ORIGINAL_P1_DEFAULT"
        or experimental["model_profile_kind"]
            != "FROZEN_NONDEFAULT_P1_DEV_HYPOTHESIS"
        or standard["original_p1_commit"] != experimental["original_p1_commit"]
        or standard["source_world_uuid"] != experimental["source_world_uuid"]
        or sensor["paper_source_uuid"] != standard["source_world_uuid"]
        or standard["original_s49_action_id"] != experimental["original_s49_action_id"]
        or sensor["original_p1_default_profile_sha256"]
            != standard["original_p1_profile_sha256"]
        or sensor["experimental_p1_profile_sha256"]
            != experimental["original_p1_profile_sha256"]
        or standard["model_stop_reason"] is not None
        or experimental["model_stop_reason"] is not None
        or standard["model_fight_steps"] != 1
        or experimental["model_fight_steps"] != 1
        or not experimental["model_wait_steps"] >= 8
        or standard["model_fatigue_at_rest_intent"] != 0
        or not experimental["model_fatigue_at_rest_intent"] > 0
        or not experimental["model_recovery_after_rest_intent"] > 0
        or experimental["source_full_tick_activity_independently_attested"] is not False
        or experimental["P1_real_physical_recovery_independently_attested"] is not False
    ):
        raise ValueError("real Paper dual-profile counterfactual conditions not satisfied")
    as_of = sensor["source_as_of_tick"]
    if not (
        type(as_of) is int
        and experimental["source_fight_callback_world_tick"] < as_of
        < experimental["source_rest_intent_world_tick"]
    ):
        raise ValueError("pre-decision source includes future/post-REST ticks")
    def state_at(rows: list[dict]) -> float:
        matches = [
            row["P1_model_after"]
            for row in rows if row["source_world_tick"] == as_of
        ]
        if len(matches) != 1:
            raise ValueError("missing/ambiguous pre-decision model tick")
        return matches[0]
    original_at_decision = state_at(standard["model_steps"])
    alternate_at_decision = state_at(experimental["model_steps"])
    if (
        not math.isclose(original_at_decision, sensor["model_default_fatigue_pre_decision"],
                         abs_tol=1e-12)
        or not math.isclose(alternate_at_decision,
                            sensor["model_experimental_fatigue_pre_decision"],
                            abs_tol=1e-12)
        or original_at_decision != 0
        or not alternate_at_decision > 0
    ):
        raise ValueError("prospective P1 state disagrees with retrospective replay")
    return {
        "classification": "S49_P1_PROSPECTIVE_MODEL_FATIGUE_REST_DEV_ONLY",
        "source_world_uuid": standard["source_world_uuid"],
        "s49_original_session_id": report["session_id"],
        "s49_original_action_id": standard["original_s49_action_id"],
        "source_fight_world_tick": standard["source_fight_event_world_tick"],
        "source_model_fight_callback_tick": standard["source_fight_callback_world_tick"],
        "source_as_of_predecision_tick": as_of,
        "source_rest_intent_world_tick": standard["source_rest_intent_world_tick"],
        "source_tick_callbacks": experimental["source_tick_callback_count"],
        "source_rest_candidate_quiet_samples": 8,
        "source_no_future_tick_used_for_decision": True,
        "original_p1_commit": standard["original_p1_commit"],
        "original_p1_module_sha256": standard["original_p1_module_sha256"],
        "default_profile_sha256": standard["original_p1_profile_sha256"],
        "experimental_profile_sha256": experimental["original_p1_profile_sha256"],
        "default_wait_recovery_rate_per_tick": 0.1,
        "experimental_wait_recovery_rate_per_tick": 0.002,
        "default_model_fatigue_at_decision": original_at_decision,
        "experimental_model_fatigue_at_decision": alternate_at_decision,
        "default_model_fatigue_at_rest": standard["model_fatigue_at_rest_intent"],
        "experimental_model_fatigue_at_rest": experimental["model_fatigue_at_rest_intent"],
        "experimental_model_recovery_after_rest":
            experimental["model_recovery_after_rest_intent"],
        "experimental_model_end_fatigue":
            experimental["model_fatigue_at_last_candidate_tick"],
        "model_sensor_reading_used_by_original_L0":
            sensor["model_experimental_sensor_reading"],
        "sensor_threshold": sensor["experimental_sensor_threshold"],
        "rest_request": sensor["request_rest"],
        "original_L0_choice": report["rest_choice"]["selected"],
        "original_self_actions_issued": len(report["actual_native_actions"]),
        "default_trace": standard["model_steps"],
        "experimental_trace": experimental["model_steps"],
        "p1_real_fatigue_physically_measured": False,
        "full_tick_activity_independently_attested": False,
        "p1_owner_live_state_installed": False,
        "m_basal_credit_or_waiver": False,
        "qualification_go": False,
        "science_run": False,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--report", type=Path, required=True)
    parser.add_argument("--paper-log", type=Path, required=True)
    parser.add_argument("--p1-checkout", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    report = json.loads(args.report.read_text(encoding="utf-8"))
    result = compare(
        report, args.paper_log.read_text(encoding="utf-8"),
        p1_checkout=args.p1_checkout,
    )
    args.out.write_text(
        json.dumps(result, sort_keys=True, indent=2) + "\n", encoding="utf-8",
    )
    print("S49_P1_PROSPECTIVE_MODEL_REST_PASS / PHYSICAL_FATIGUE_UNATTESTED")


if __name__ == "__main__":
    main()
