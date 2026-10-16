"""V #619 V4: pre-run information-identifiability feasibility, not efficacy.

Do not confuse a constructed ON/OFF choice difference with a benefit from
retained cognition. The cheap same-information threshold is source-equivalent.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

MANIFEST = Path(__file__).with_name("v4_identifiability_manifest.json")
PARENT = "063c6581f00c7247346dd4b4bb38c989a65b4dcb"
S_HEAD = "28cb0f588192ecfe5d03b12b818508352d1a40a8"
SCHEMA = "RELAYSELF_V4_IDENTIFIABILITY_GATE_1"
PHASES = ("V3_FIXED_FIRST_ITEM", "LOW_ENERGY", "HIGH_ENERGY")


class V4Rejected(ValueError):
    """V4 identity, source changes, or fabricated qualification."""


def require(ok: bool, label: str) -> None:
    if not ok:
        raise V4Rejected(label)


def validate_manifest(d: dict[str, Any]) -> dict[str, Any]:
    require(type(d) is dict and set(d) == {
        "schema", "issue", "parent_v3_head", "s_source_head", "status",
        "baseline_assumptions", "factorial_source_shaped_states",
        "prospective_study_requirements", "boundaries",
    }, "unexpected V4 manifest fields")
    require(d["schema"] == SCHEMA and d["issue"] == 619
            and d["parent_v3_head"] == PARENT
            and d["s_source_head"] == S_HEAD
            and d["status"] == "OFFLINE_PREREQUISITE_NOT_A_WORLD_TRIAL",
            "V4 source/prereg identity")
    require(d["baseline_assumptions"] == {
        "energy_initial_v3": 12, "basal_per_tick": 0.5,
        "seek_sensor_quantum": 1, "seek_threshold": 8,
        "mask_gain": 0, "mask_bias": 12, "food_native_below": 14,
    }, "S policy/energy assumptions changed")
    require(d["factorial_source_shaped_states"] == [
        {"id": "V3_FIXED_FIRST_ITEM", "start_energy": 12,
         "prefixture_wait_ticks": 11, "expected_e": 6.5,
         "source_mode": "S_GROUNDV2_AVAILABLE"},
        {"id": "LOW_ENERGY", "start_energy": 4, "prefixture_wait_ticks": 1,
         "expected_e": 3.5, "source_mode": "NOT_S_PRODUCT_MODE"},
        {"id": "HIGH_ENERGY", "start_energy": 20, "prefixture_wait_ticks": 1,
         "expected_e": 19.5, "source_mode": "NOT_S_PRODUCT_MODE"},
    ], "source-shaped energy phase changed")
    require(d["prospective_study_requirements"] == {
        "cheap_equal_information": "SAME_QUANTIZED_SENSOR_THRESHOLD_CHEAP",
        "cheap_native_original": "NATIVE_ONLY",
        "sham": "UNCHANGED_SENSOR_ON_WITH_SWITCH_PATH",
        "masked": "GAIN_ZERO_BIAS_TWELVE",
        "required_conditions": ["LOW_ENERGY", "HIGH_ENERGY"],
        "reject_if_any_heldout_condition_or_supplementary_outcome_chosen_after_results": True,
        "must_show_positive_and_negative_net_effect_without_fixed_policy_scripted_success": True,
        "learned_policy_required_for_advanced_cognitive_claim": True,
        "train_holdout_disjoint_world_starts": True,
        "training_selection_not_observed_by_v_evaluator": True,
        "freeze_parameters_and_cheap_threshold_tuning_before_holdout": True,
        "original_native_elapsed_world_time_matched_by_r": True,
        "real_s_implementation_exists": False,
        "external_food_hazard_cost_and_opportunity_precommitted": False,
        "original_bytes_attested": False,
        "user_fresh_per_world_run_permission": False,
        "scientific_g3": "NO_GO",
    }, "scientific comparator/admission change")
    require(d["boundaries"] == {
        "actual_world_trials": 0, "actual_llm_calls": 0,
        "permission_granted": False, "v2_v3_preserved": True,
        "science_go": False, "production_go": False,
    }, "V4 forbidden elevation to science/live")
    return d


def load_manifest() -> dict[str, Any]:
    return validate_manifest(json.loads(MANIFEST.read_text(encoding="utf-8")))


def policy_choices(d: dict[str, Any] | None = None) -> dict[str, Any]:
    """Pinned-S-conditional *policy* oracle; no physical World state."""
    m = validate_manifest(d if d is not None else load_manifest())
    b = m["baseline_assumptions"]
    states = {}
    for case in m["factorial_source_shaped_states"]:
        e = case["start_energy"] - (
            case["prefixture_wait_ticks"] * b["basal_per_tick"]
        )
        require(e == case["expected_e"] and e > 0, "bad phase energy")
        sensor = round(e / b["seek_sensor_quantum"]) * b["seek_sensor_quantum"]
        gate = "SEEK" if sensor <= b["seek_threshold"] else "WAIT"
        states[case["id"]] = {
            "body_energy": e, "sensor_reading": sensor,
            "on": gate, "sham": gate,
            "masked": "WAIT", "cheap_native": "SEEK",
            "cheap_equal_information": gate,
            "s_product_mode": case["source_mode"],
        }
    require(tuple(states) == PHASES, "missing phase")
    require(
        states["V3_FIXED_FIRST_ITEM"]["on"]
        == states["V3_FIXED_FIRST_ITEM"]["cheap_native"] == "SEEK"
        and states["V3_FIXED_FIRST_ITEM"]["masked"] == "WAIT",
        "V3 first food policy witness drift",
    )
    require(
        states["LOW_ENERGY"]["on"] == "SEEK"
        and states["LOW_ENERGY"]["masked"] == "WAIT"
        and states["HIGH_ENERGY"]["on"] == "WAIT"
        and states["HIGH_ENERGY"]["cheap_native"] == "SEEK",
        "missing double dissociation",
    )
    require(all(x["on"] == x["cheap_equal_information"]
                for x in states.values()), "cheap equal-information parity drift")
    return {
        "classification": "V4_G0_EQUAL_INFORMATION_CHEAP_REPLICATION_BLOCK",
        "source": "PINNED_S_OWNER_CONDITIONAL_SOURCE_SHAPED",
        "phases": states,
        "on_vs_mask_low_energy_choice_discriminable": True,
        "on_vs_native_cheap_high_energy_choice_discriminable": True,
        "on_vs_equal_information_cheap_choices_discriminable": False,
        "v3_first_opportunity_on_cheap_divergence": False,
        "v4_real_s_product_mode_eligible": False,
        "net_energy_or_survival_benefit_established": False,
        "learning_or_retained_adaptation_established": False,
        "matched_native_world_time": "NOT_ATTESTED",
        "original_world_actions": 0,
        "science_go": False,
    }


def main() -> int:
    a = policy_choices()
    print(json.dumps(a, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
