"""Historical new V7 source-reviewed DEV slots, not scientific outcomes."""
from __future__ import annotations

from experiments.validation import v7_m02_seed61021_dev as real
from experiments.validation import v7_m02_trial_roster as roster


def test_real_dev_arms_are_logged_without_promoting_science():
    packet = real.review_real_dev_metadata()
    assert packet["classification"] == "V7_M02_REAL_DEV_FIVE_ARM_PRESCIENCE_UNMATCHED_PATHS"
    assert packet["actual_dev_worlds"] == 5
    assert packet["prospective_science_slots"] == 20
    assert packet["v7_science_trials"] == 0
    assert packet["R_archived_orig_artifact_id"] == 12012577361
    assert not packet["v7_science_go"]
    assert not packet["paired_paths_eligible"]
    assert not packet["causal_comparisons_allowed"]
    assert packet["observed_path_max_minus_min_blocks"] > 0.24
    assert packet["match_path_tolerance_blocks"] == 0.005
    assert not packet["basal_physical_charge_independently_measured"]


def test_full_prescience_roster_keeps_all_20_empty_science_slots():
    p = real.seed61021_prescience_roster()
    checked = roster.review_roster(p)
    assert len(p["slots"]) == 20
    assert checked["prescience_attempts_preserved"] == {"DEV": 5, "QUALIFICATION": 0}
    assert checked["actual_v7_science_trials"] == 0
    assert p["science_trials_executed"] == 0
    assert not p["science_execution_authorized"]
    for row in p["slots"]:
        assert row["science_status"] == "NOT_RUN"
        attempts = row["prescience_attempts"]
        assert len(attempts) == (1 if row["seed"] == 61021 else 0)
        for x in attempts:
            assert x["mode"] == "DEV" and x["outcome"] == "PASS_CLAIMED"
            assert x["r_review"] == "REVIEW_ONLY"
            assert not x["science_trial"] and not x["grant_reused"]


def test_real_r_original_walk_arithmetic_not_matched_path_effect():
    x = real.review_real_dev_metadata()
    v = x["originals_by_arm"]
    assert v["BASE_ON"]["source_observed_path_blocks"] != v["SHAM_ON"]["source_observed_path_blocks"]
    assert v["SHAM_ON"]["source_observed_walk_exhaustion"] > 0
    assert v["WALK_ZERO"]["source_observed_walk_exhaustion"] == 0
    assert v["BOTH_ZERO"]["source_observed_walk_exhaustion"] == 0
    assert x["r_original_review_type"] == "DEV_ORIGINALS_REVIEW_ONLY"
    assert not x["r_changed_profile_qualification"]
    assert not x["scientific_effect_estimated"]
