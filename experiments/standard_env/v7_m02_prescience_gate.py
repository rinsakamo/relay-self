"""R V7: independent pre-science admission from read-only five-arm DEV receipt.

Classify source-shape validity separately from paired-world comparability.
Do not infer BASAL writes from configured rates, do not normalize unequal paths.
No Java/Node/Minecraft use. No SCIENCE/QUALIFICATION authorization.
"""
from __future__ import annotations

import json
import math
from typing import Any

ARMS = ("BASE_ON", "SHAM_ON", "BASAL_ZERO", "WALK_ZERO", "BOTH_ZERO")
TOLERANCE_BLOCKS = 0.005
CLASS = "RSEE_V7_M02_PRESCIENCE_MEASUREMENT_NOT_ADMITTED"


class NotAdmitted(ValueError):
    pass


def check(ok: bool, reason: str) -> None:
    if not ok:
        raise NotAdmitted(reason)


def finite(v: Any) -> float:
    check(type(v) in (int, float) and math.isfinite(v), "nonfinite numeric source")
    return float(v)


def review(paper_receipt: dict[str, Any]) -> dict[str, Any]:
    check(type(paper_receipt) is dict
          and paper_receipt.get("classification") ==
          "RSEE_V7_M02_FIVE_ARM_DEV_SOURCE_REVIEW_ONLY"
          and paper_receipt.get("producer_run") == 38819265395
          and paper_receipt.get("s_original_head") ==
          "944a68ca36f90380ffa5481ba85a6f95ed08ba18"
          and paper_receipt.get("all_five_originals_readonly_pass") is True
          and paper_receipt.get("five_arms_readback") == 5
          and paper_receipt.get("v7_science_trials") == 0
          and paper_receipt.get("v7_science_go") is False
          and paper_receipt.get("r_changed_config_engineering_qualified") is False
          and paper_receipt.get("basal_per_tick_cost_directly_attested") is False,
          "not the pinned historic read-only DEV original")
    arms = paper_receipt.get("arms")
    check(type(arms) is dict and set(arms) == set(ARMS),
          "missing/foreign original factor")
    summaries = {}
    for name in ARMS:
        a = arms[name]
        check(type(a) is dict and a.get("arm") == name
              and a.get("classification") ==
              "RSEE_V7_M02_CHANGED_CONFIG_DEV_ORIGINAL_REVIEW_ONLY"
              and a.get("actual_v7_science_trials") == 0
              and a.get("v_science_go") is False
              and a.get("real_s50_move_attested") is True
              and a.get("real_s51_eat_tested") is False
              and a.get("source_basal_physical_debit_independently_attested") is False,
              "foreign source arm or promoted claim")
        ticks, packets = a.get("min_player_ticks_reached"), a.get("real_motion_packets")
        check(type(ticks) is int and ticks >= 200
              and type(packets) is int and packets > 0,
              "no native Paper player ticks/path")
        path, debit = map(finite,
                          (a.get("real_motion_path_blocks"), a.get("observed_walk_debit")))
        multiplier = 0 if name in ("WALK_ZERO", "BOTH_ZERO") else 1
        check(.5 < path < 2
              and abs(debit - multiplier * .01 * path) < 1e-7,
              "actual packet WALK debit not independently recomputable")
        summaries[name] = {"blocks": path, "walk_debit": debit,
                           "player_ticks_min": ticks, "packet_count": packets}
    paths = [summaries[a]["blocks"] for a in ARMS]
    delta = max(paths) - min(paths)
    reported_delta = finite(paper_receipt.get("path_max_minus_min_blocks"))
    check(abs(delta - reported_delta) < 1e-9
          and paper_receipt.get("paired_path_tolerance_met") is
          (delta <= TOLERANCE_BLOCKS), "producer R pair-difference mismatch")
    path_valid = delta <= TOLERANCE_BLOCKS
    direct_basal = all(
        arms[a].get("source_basal_physical_debit_independently_attested") is True
        for a in ARMS
    )
    check(not direct_basal, "historical instrumentation did not produce direct BASAL")
    return {
        "classification": CLASS,
        "source": "R_EXACT_HISTORIC_FIVE_DEV_ORIGINALS_NOT_PROSPECTIVE_SCIENCE",
        "arms_reviewed": 5,
        "seed": 61021,
        "observed_path_max_minus_min_blocks": delta,
        "predeclared_tolerance_blocks": TOLERANCE_BLOCKS,
        "actual_paths_comparable": path_valid,
        "native_source_basal_written_cumulative": "NOT_IN_ORIGINALS",
        "direct_basal_source_authenticated": False,
        "all_actual_source_ticks_bounded_to_exact_experiment_interval": False,
        "strict_identical_initial_world_by_source": False,
        "independent_changed_config_qualification": False,
        "science_trials_credited": 0,
        "science_admitted": False,
        "production_go": False,
        "next_gate": [
            "S_NEW_DISPOSABLE_DEV_BASAL_SOURCE_WRITE_TELEMETRY",
            "S_RECORD_CONTROLLED_EXACT_WORLD_TICK_INTERVAL",
            "S_MATCH_PHYSICAL_PATHS_BY_PREDECLARED_CONTROL_NOT_POSTHOC_FILTERING",
            "R_INDEPENDENT_NEW_PLUGIN_BINARY_CONFIG_SOURCE_ADMISSION",
        ],
        "arms": summaries,
    }


def main() -> None:
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--review-json", required=True)
    args = parser.parse_args()
    with open(args.review_json, "r", encoding="utf-8") as stream:
        obj = json.load(stream)
    print(json.dumps(review(obj), sort_keys=True))


if __name__ == "__main__":
    main()
