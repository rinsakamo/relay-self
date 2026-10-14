"""V6 source-only R clock checks: never accept display or projected age."""
from __future__ import annotations

import copy
import pytest

from experiments.validation import v6_r_clock_source_review as v6


def _plan():
    return {
        "classification": "RSEE_V6_WORLD_TIME_PRE_ADMISSION_PLAN",
        "golden_head": "34820f6bf391c77f325d7c29d3b779a33e3ca835",
        "golden_world_manifest_sha256": (
            "5b1876db6a97fc8b9c4331938ca47727037c5626a241213d871b2073665996f8"
        ),
        "world_start_bytes": "NOT_READ",
        "actual_host_monotonic_time": "NOT_READ",
        "native_time_of_day": "NOT_READ",
        "minecraft_world_age_tick": "NOT_IN_FROZEN_MINEFLAYER_SOURCE",
        "m0_tick": "NOT_WORLD_TICK",
        "cross_arm_native_world_elapsed_parity": "NOT_ATTESTED",
        "science_g3": "NO_GO", "physical_execution_authorized": False,
        "side_effects": "NONE",
    }


def _paired():
    return {
        "classification": "RSEE_V6_PAIRED_CLOCK_REVIEW_ONLY_NOT_ADMITTED",
        "world_start_slot": "WORLD_START_A", "planned_arms": 12,
        "host_elapsed_ns_by_arm": {f"LOW:control-{i}": 1000 + i for i in range(12)},
        "m0_tick_per_arm": 11, "claimed_world_age_delta_parity_possible": True,
        "native_world_age_authenticity_verified": False,
        "independent_golden_clone_bytes_verified": False,
        "source_original_sha256_verified": False,
        "matched_native_world_elapsed_tick_attested": False,
        "actual_world_starts": 0, "physical_execution_authorized": False,
        "science_g3": "NO_GO",
    }


def test_real_r_no_age_producer_reports_science_no_go():
    x = v6.review_r_plan(_plan())
    assert x["classification"] == "V6_R_THREE_CLOCK_PRODUCER_GAP_CONFIRMED_G0"
    assert x["separate_clock_axes"] == [
        "HOST_MONOTONIC_NS", "MINECRAFT_DISPLAY_DAY_TIME", "M0_DECISION_TICK",
    ]
    assert not x["paired_native_elapsed_world_ticks_attested"]
    assert not x["physical_session_admitted"] and x["new_world_trials"] == 0
    assert x["science_g3"] == "NO_GO"


@pytest.mark.parametrize(("key", "bad"), [
    ("minecraft_world_age_tick", "QUALIFIED"),
    ("native_time_of_day", "REAL_NATIVE_AGE"),
    ("m0_tick", "MINECRAFT_ELAPSED"),
    ("cross_arm_native_world_elapsed_parity", "MATCH"),
    ("world_start_bytes", "PASSED"),
    ("physical_execution_authorized", True),
    ("science_g3", "GO"),
    ("golden_head", "0" * 40),
])
def test_r_plan_promotion_blocked(key, bad):
    d = _plan()
    d[key] = bad
    with pytest.raises(v6.V6ClockRejected):
        v6.review_r_plan(d)


def test_r_paired_matching_candidate_still_cannot_authenticate_world_age():
    x = v6.review_r_paired_candidate(_paired())
    assert x["candidate_equal_age_deltas"] is True
    assert not x["original_world_time_matched"]
    assert not x["native_age_producer_qualified"]
    mismatch = _paired()
    mismatch["claimed_world_age_delta_parity_possible"] = False
    assert v6.review_r_paired_candidate(mismatch)["candidate_equal_age_deltas"] is False


@pytest.mark.parametrize(("field", "bad"), [
    ("native_world_age_authenticity_verified", True),
    ("independent_golden_clone_bytes_verified", True),
    ("source_original_sha256_verified", True),
    ("matched_native_world_elapsed_tick_attested", True),
    ("actual_world_starts", 1),
    ("physical_execution_authorized", True),
    ("science_g3", "GO"),
    ("claimed_world_age_delta_parity_possible", 1),
    ("planned_arms", 11),
])
def test_r_paired_candidate_cannot_become_real_receipt(field, bad):
    p = _paired()
    p[field] = bad
    with pytest.raises(v6.V6ClockRejected):
        v6.review_r_paired_candidate(p)


def test_pure_r_plan_and_duplicate_json_keys_rejected(tmp_path):
    import json

    d = _plan()
    before = copy.deepcopy(d)
    assert v6.review_r_plan(d)["r_pinned_head"] == v6.R_HEAD
    assert d == before
    p = tmp_path / "r-plan.json"
    p.write_text(json.dumps(d), encoding="utf-8")
    assert not v6.review_json_file(p)["physical_session_admitted"]
    p.write_text('{"classification":"A","classification":"B"}', encoding="utf-8")
    with pytest.raises(v6.V6ClockRejected, match="duplicate"):
        v6.review_json_file(p)
