"""Independent V6 review of R three-clock capability, source-only NO-GO.

R candidate matching delta of self-reported world age does not establish
authenticated Minecraft world-age or original command execution time.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

R_HEAD = "94c68a97bd25de9e170d067c61894fc21783c5bf"
CLOCK_GAPS = (
    "INDEPENDENT_MONOTONE_WORLD_AGE_NATIVE_PRODUCER",
    "ORIGINAL_COMMAND_EFFECT_WORLD_TICK",
    "SAME_GOLDEN_LIVE_WORLD_START",
    "REAL_ELAPSED_WORLD_TICK_PARITY",
    "ORIGINAL_RAW_SESSION_AND_EXCLUSIVE_ISSUER",
)


class V6ClockRejected(ValueError):
    """R clock source unavailable or projected claims falsely promoted."""


def _require(ok: bool, message: str) -> None:
    if not ok:
        raise V6ClockRejected(message)


def review_r_plan(data: dict[str, Any]) -> dict[str, Any]:
    _require(type(data) is dict and set(data) == {
        "classification", "golden_head", "golden_world_manifest_sha256",
        "world_start_bytes", "actual_host_monotonic_time",
        "native_time_of_day", "minecraft_world_age_tick", "m0_tick",
        "cross_arm_native_world_elapsed_parity", "science_g3",
        "physical_execution_authorized", "side_effects",
    }, "unqualified R plan shape")
    _require(
        data["classification"] == "RSEE_V6_WORLD_TIME_PRE_ADMISSION_PLAN"
        and data["golden_head"] == "34820f6bf391c77f325d7c29d3b779a33e3ca835"
        and data["golden_world_manifest_sha256"]
        == "5b1876db6a97fc8b9c4331938ca47727037c5626a241213d871b2073665996f8"
        and data["world_start_bytes"] == "NOT_READ"
        and data["actual_host_monotonic_time"] == "NOT_READ"
        and data["native_time_of_day"] == "NOT_READ"
        and data["minecraft_world_age_tick"] == "NOT_IN_FROZEN_MINEFLAYER_SOURCE"
        and data["m0_tick"] == "NOT_WORLD_TICK"
        and data["cross_arm_native_world_elapsed_parity"] == "NOT_ATTESTED"
        and data["physical_execution_authorized"] is False
        and data["science_g3"] == "NO_GO"
        and data["side_effects"] == "NONE",
        "unearned R World age or provenance claim",
    )
    return {
        "classification": "V6_R_THREE_CLOCK_PRODUCER_GAP_CONFIRMED_G0",
        "r_pinned_head": R_HEAD,
        "separate_clock_axes": [
            "HOST_MONOTONIC_NS", "MINECRAFT_DISPLAY_DAY_TIME", "M0_DECISION_TICK",
        ],
        "required_missing_originals": list(CLOCK_GAPS),
        "real_world_age_authenticated": False,
        "paired_native_elapsed_world_ticks_attested": False,
        "physical_session_admitted": False,
        "new_world_trials": 0, "science_g3": "NO_GO",
    }


def review_r_paired_candidate(data: dict[str, Any]) -> dict[str, Any]:
    _require(type(data) is dict and set(data) == {
        "classification", "world_start_slot", "planned_arms",
        "host_elapsed_ns_by_arm", "m0_tick_per_arm",
        "claimed_world_age_delta_parity_possible",
        "native_world_age_authenticity_verified",
        "independent_golden_clone_bytes_verified",
        "source_original_sha256_verified",
        "matched_native_world_elapsed_tick_attested",
        "actual_world_starts", "physical_execution_authorized", "science_g3",
    }, "unqualified R paired candidate schema")
    _require(
        data["classification"] == "RSEE_V6_PAIRED_CLOCK_REVIEW_ONLY_NOT_ADMITTED"
        and data["world_start_slot"] in (
            "WORLD_START_A", "WORLD_START_B", "WORLD_START_C", "WORLD_START_D",
        )
        and type(data["planned_arms"]) is int and data["planned_arms"] == 12
        and type(data["m0_tick_per_arm"]) is int and data["m0_tick_per_arm"] == 11
        and type(data["host_elapsed_ns_by_arm"]) is dict
        and len(data["host_elapsed_ns_by_arm"]) == 12
        and all(type(x) is str and bool(x) for x in data["host_elapsed_ns_by_arm"])
        and all(type(x) is int and x >= 0 for x in data["host_elapsed_ns_by_arm"].values())
        and type(data["claimed_world_age_delta_parity_possible"]) is bool
        and data["native_world_age_authenticity_verified"] is False
        and data["independent_golden_clone_bytes_verified"] is False
        and data["source_original_sha256_verified"] is False
        and data["matched_native_world_elapsed_tick_attested"] is False
        and type(data["actual_world_starts"]) is int and data["actual_world_starts"] == 0
        and data["physical_execution_authorized"] is False
        and data["science_g3"] == "NO_GO",
        "unbound projected age treated as genuine World original",
    )
    return {
        "classification": "V6_R_PAIRED_WORLD_CLOCK_CANDIDATE_ONLY",
        "candidate_equal_age_deltas": data["claimed_world_age_delta_parity_possible"],
        "native_age_producer_qualified": False,
        "original_world_time_matched": False,
        "physical_session_admitted": False,
        "new_world_trials": 0, "science_g3": "NO_GO",
    }


def _unique_pairs(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        _require(key not in result, "duplicate JSON clock source key")
        result[key] = value
    return result


def main() -> int:
    """Plan-only V-owned gate, no host/R/World work or receipt generation."""
    from experiments.standard_env.v6_world_timing import plan
    # Only for use in an explicitly pinned R checkout during CI.
    x = review_r_plan(plan())
    print(json.dumps(x, sort_keys=True))
    return 0


def review_json_file(path: Path) -> dict[str, Any]:
    _require(path.is_file() and 0 < path.stat().st_size <= 65536,
             "bounded existing R projection required")
    result = json.loads(path.read_text(encoding="utf-8"),
                        object_pairs_hook=_unique_pairs)
    _require(type(result) is dict, "R projection must be a JSON object")
    return review_r_plan(result)


if __name__ == "__main__":
    raise SystemExit(main())
