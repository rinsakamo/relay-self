"""V7 original-derived DEV roster after R readback; NEVER physical V7 science.

Five real S disposable DEV sessions exist, R independently reviewed source
bytes, but observed path inequality violates predeclared matched-arm tolerance.
This readout is fixed descriptive prescience metadata, not 20 SCIENCE trials.
"""
from __future__ import annotations

import json

from experiments.validation import v7_m02_physics as v7
from experiments.validation import v7_m02_trial_roster as roster

S_RUN = 38819265395
R_RUN = 38819700537
S_HEAD = "944a68ca36f90380ffa5481ba85a6f95ed08ba18"
R_HEAD = "f15d97b197a4fcfb9d6e124b2499590b7b150248"
R_ARTIFACT = 12012577361
SOURCE = {
    "BASE_ON": ("f759a9ff216c543118bfb1a9aca91dd694798b49349055c771da01fd783a557f",
                1.039090342887362, 0.010390903428873619),
    "SHAM_ON": ("75daf993b20794534be038981d8d7fbf1b7dc311ca4f338dc53bbec8dfe69d3e",
                1.2828913533098643, 0.012828913533098642),
    "BASAL_ZERO": ("d08a3900cdb1c8c56b92b8dae69f719448a6cb5eea28a82c09548816233fa1fa",
                    1.2828913533098634, 0.012828913533098634),
    "WALK_ZERO": ("3ad740fc7edaf9622e693d8d389d278fc0e0a177a947ae0e534439230501e7cc",
                   1.2828913533098634, 0.0),
    "BOTH_ZERO": ("90dd0977ba0d122fa1094e4d2b4d6b5706e1228a19752b6f8119b1bcb812f18e",
                   1.2828913533098643, 0.0),
}


def seed61021_prescience_roster() -> dict:
    """Add all five real DEV attempts without consuming one science slot."""
    p = roster.new_roster()
    for slot in p["slots"]:
        if slot["seed"] == 61021:
            arm = slot["arm"]
            digest, _, _ = SOURCE[arm]
            slot["prescience_attempts"].append({
                "attempt_id": f"dev{S_RUN}-{arm}",
                "mode": "DEV",
                "outcome": "PASS_CLAIMED",  # S's DEV owner outcome, not V efficacy.
                "original_bundle_sha256": digest,
                "r_review": "REVIEW_ONLY",
                "science_trial": False,
                "grant_reused": False,
            })
    return p


def review_real_dev_metadata() -> dict:
    v7.load_manifest()
    p = seed61021_prescience_roster()
    result = roster.review_roster(p)
    v7_path = v7.load_manifest()["design"]["matched_path_tolerance_blocks"]
    values = [SOURCE[arm][1] for arm in v7.ARMS]
    diff = max(values) - min(values)
    if not diff > v7_path:
        raise v7.V7Rejected("fixed R original shows a mismatch; unexpected drift")
    if not result["prescience_attempts_preserved"] == {"DEV": 5, "QUALIFICATION": 0}:
        raise v7.V7Rejected("prospective five-arm source metadata incomplete")
    observed_rates = {}
    for arm, (_, blocks, debit) in SOURCE.items():
        _, walk = v7.MULTIPLIERS[arm]
        if not (v7.finite(blocks) and blocks > 0 and v7.finite(debit)):
            raise v7.V7Rejected("invalid physical path/debit for WALK rate")
        rate = debit / blocks
        expected_rate = 0.01 * walk
        if (abs(debit - expected_rate * blocks) >= 1e-7
                or abs(rate - expected_rate) >= 1e-7):
            raise v7.V7Rejected("foreign R Paper original WALK rate")
        observed_rates[arm] = rate
    return {
        "classification": "V7_M02_REAL_DEV_FIVE_ARM_PRESCIENCE_UNMATCHED_PATHS",
        "S_original_run_id": S_RUN, "S_original_head": S_HEAD,
        "R_independent_run_id": R_RUN, "R_independent_head": R_HEAD,
        "R_archived_orig_artifact_id": R_ARTIFACT,
        "seed": 61021, "actual_dev_worlds": 5,
        "prospective_science_slots": result["prospective_science_slots"],
        "v7_science_trials": 0, "v7_science_go": False,
        "r_original_review_type": "DEV_ORIGINALS_REVIEW_ONLY",
        "r_changed_profile_qualification": False,
        "match_path_tolerance_blocks": v7_path,
        "observed_path_max_minus_min_blocks": diff,
        "paired_paths_eligible": False,
        # Independent descriptive source accounting, NOT a prereg amendment.
        "walk_rate_source_accounting": "CONSISTENT_R_REVIEWED_DEV_ONLY",
        "walk_rate_requires_paired_path_match": False,
        "walk_rate_is_scientific_effect": False,
        "basal_physical_charge_independently_measured": False,
        "mechanism_source_cost_recomputed": True,
        "scientific_effect_estimated": False,
        "causal_comparisons_allowed": False,
        "ecological_calibration_go": False, "production_go": False,
        "originals_by_arm": {
            arm: {
                "S_artifact_zip_sha256": v[0],
                "source_observed_path_blocks": v[1],
                "source_observed_walk_exhaustion": v[2],
                "observed_walk_exhaustion_per_block": observed_rates[arm],
                "expected_walk_exhaustion_per_block":
                    v7.WALK_RATE * v7.MULTIPLIERS[arm][1],
            } for arm, v in SOURCE.items()
        },
    }


def main() -> None:
    print(json.dumps(review_real_dev_metadata(), sort_keys=True))


if __name__ == "__main__":
    main()
