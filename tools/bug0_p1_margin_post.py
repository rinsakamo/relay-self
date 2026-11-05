"""Same-World source-bound nominal vs guarded P1 REST/WAIT audit (DEV).

No post-choice state can influence the preceding S49 choice. Compare both
original pinned P1 model traces against the exact predecision sensor value.
"""
from __future__ import annotations

import argparse
import json
import math
from pathlib import Path

from tools.bug0_p1_sensor_threshold import sensitivity
from tools.bug0_s49_p1_paper_model_eval import evaluate_source


def compare_margin(report: dict, paper_log: str, *, p1_checkout: Path) -> dict:
    mode = report.get("classification")
    rates = {
        "DEV_ONLY_S49_P1_MARGIN_SENSOR_NATIVE_CHOICE": 0.002,
        "DEV_ONLY_S49_P1_HIGH_SENSOR_NATIVE_CHOICE": 0.001,
    }
    if report.get("status") != "PASS" or mode not in rates:
        raise ValueError("one original rate-bound margin DEV World required")
    expected_rate = rates[mode]
    sensor = report.get("prospective_p1_sensor")
    joined = report.get("prospective_p1_s49_join")
    actual = report.get("rest_choice", {}).get("selected")
    if (
        not isinstance(sensor, dict) or not isinstance(joined, dict)
        or actual not in ("WAIT", "REST")
        or sensor.get("sensor_decision_policy") != "margin"
        or sensor.get("source_post_rest_lookahead_used") is not False
        or sensor.get("source_kind") != "PAPER_PRE_DECISION_CALLBACK_P1_VIRTUAL_SENSOR_DEV"
        or sensor.get("original_P1_runtime_state_installed") is not False
        or sensor.get("p1_real_fatigue_attested") is not False
        or joined.get("status") != "DEV_THRESHOLD_MARGIN_MODEL_SENSOR_NATIVE_CHOICE"
        or joined.get("actual_original_l0_choice") != actual
        or joined.get("source_future_read_for_decision") is not False
        or joined.get("independent_physical_fatigue_recovery") is not False
        or sensor.get("experimental_wait_recovery_per_tick") != expected_rate
        or sensor.get("original_default_wait_recovery_per_tick") != 0.1
        or not isinstance(sensor.get("sensitivity"), dict)
    ):
        raise ValueError("stale/foreign/missing original L0 margin source")
    reading = sensor["model_experimental_sensor_reading"]
    table = sensitivity(float(reading))
    if (
        table.to_dict() != sensor["sensitivity"]
        or sensor["nominal_rest_shadow"] is not table.nominal_rest
        or sensor["uncertainty_guard_rest_shadow"] is not table.uncertainty_guard_rest
        or sensor["safety_margin_rest_shadow"] is not table.safety_margin_rest
        or sensor["request_rest"] is not table.safety_margin_rest
        or (actual == "REST") is not table.safety_margin_rest
    ):
        raise ValueError("L0 choice did not follow frozen margin sensor")
    standard = evaluate_source(report, paper_log, p1_checkout=p1_checkout)
    alternate = evaluate_source(
        report, paper_log, p1_checkout=p1_checkout,
        experimental_wait_rate=expected_rate,
    )
    if (
        standard["source_world_uuid"] != alternate["source_world_uuid"]
        or standard["original_s49_session_id"] != alternate["original_s49_session_id"]
        or standard["original_s49_action_id"] != alternate["original_s49_action_id"]
        or sensor["paper_source_uuid"] != standard["source_world_uuid"]
        or sensor["original_s49_session_id"] != report["session_id"]
        or standard["model_stop_reason"] is not None
        or alternate["model_stop_reason"] is not None
        or standard["model_fight_steps"] != 1
        or alternate["model_fight_steps"] != 1
        or alternate["model_wait_steps"] < 8
        or standard["source_original_l0_choice"] != actual
        or alternate["source_original_l0_choice"] != actual
        or standard["source_rest_intent_world_tick"] != (
            standard["source_choice_world_tick"] if actual == "REST" else None
        )
        or alternate["original_p1_profile_sha256"]
            != sensor["experimental_p1_profile_sha256"]
        or standard["original_p1_profile_sha256"]
            != sensor["original_p1_default_profile_sha256"]
    ):
        raise ValueError("original Paper and dual P1 trace mismatch")
    as_of = sensor["source_as_of_tick"]
    boundary = standard["source_choice_world_tick"]
    if not (
        type(as_of) is int and standard["source_fight_callback_world_tick"] < as_of
        < boundary and boundary <= standard["source_tick_callback_count"]
            + standard["source_world_tick_start"] + 1
    ):
        raise ValueError("model sensor contains post-decision source")
    def at_as_of(trace: dict) -> float:
        values = [
            x["P1_model_after"] for x in trace["model_steps"]
            if x["source_world_tick"] == as_of
        ]
        if len(values) != 1:
            raise ValueError("incomplete retrospective callback at decision")
        return values[0]
    default = at_as_of(standard)
    experimental = at_as_of(alternate)
    if (
        not math.isclose(default, sensor["model_default_fatigue_pre_decision"],
                         abs_tol=1e-12)
        or not math.isclose(experimental,
                            sensor["model_experimental_fatigue_pre_decision"],
                            abs_tol=1e-12)
        or sensor["source_as_of_tick"] != joined["source_as_of_server_tick"]
        or not (standard["source_full_tick_activity_independently_attested"] is False
                and alternate["P1_real_physical_recovery_independently_attested"] is False)
    ):
        raise ValueError("prospective/body model state drift")
    return {
        "classification": "DEV_P1_SENSOR_MARGIN_SOURCE_CAUSAL_COMPARISON",
        "original_s49_session_id": report["session_id"],
        "original_s49_action_id": standard["original_s49_action_id"],
        "original_p1_commit": standard["original_p1_commit"],
        "source_world_uuid": standard["source_world_uuid"],
        "source_fight_callback_tick": standard["source_fight_callback_world_tick"],
        "source_as_of_predecision_tick": as_of,
        "source_choice_marker_tick": boundary,
        "source_callback_tick_rows": standard["source_tick_callback_count"],
        "experimental_wait_recovery_per_tick": expected_rate,
        "experimental_profile_mode": mode,
        "sensor_quantum": table.quantum,
        "base_threshold": table.threshold,
        "uncertainty_lower_bound": table.admissible_lower,
        "safety_margin": table.margin,
        "nominal_rest_shadow": table.nominal_rest,
        "uncertainty_guard_rest_shadow": table.uncertainty_guard_rest,
        "safety_margin_rest": table.safety_margin_rest,
        "nominal_vs_margin_flip": table.nominal_rest != table.safety_margin_rest,
        "original_s49_l0_selected": actual,
        "one_native_attack_and_no_post_choice_action": (
            len(report["actual_native_actions"]) == 1
            and report.get("rest_action_issued") is False
        ),
        "default_P1_model_fatigue_predecision": default,
        "experimental_P1_model_fatigue_predecision": experimental,
        "experiment_model_fatigue_at_choice": alternate["model_fatigue_at_rest_intent"],
        "experiment_model_recovery_postchoice":
            alternate["model_recovery_after_rest_intent"],
        "source_future_tick_used_for_decision": False,
        "source_full_tick_independently_attested": False,
        "P1_real_fatigue_measured": False,
        "P1_runtime_body_state_installed": False,
        "m_energy_credit_or_waiver": False,
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
    result = compare_margin(
        report, args.paper_log.read_text(encoding="utf-8"),
        p1_checkout=args.p1_checkout,
    )
    args.out.write_text(json.dumps(result, sort_keys=True, indent=2) + "\n",
                        encoding="utf-8")
    print("DEV_P1_QUANTIZATION_MARGIN_L0_CHOICE_JOIN_PASS_NOT_PHYSICAL")


if __name__ == "__main__":
    main()
