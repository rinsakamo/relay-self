"""V7 real DEV pre-science negative gates: no fake BASAL or path equivalence."""
from __future__ import annotations

import copy

import pytest

from experiments.standard_env import v7_m02_prescience_gate as gate


def _receipt() -> dict:
    paths = {"BASE_ON": 1.039090342887362,
             "SHAM_ON": 1.2828913533098643,
             "BASAL_ZERO": 1.2828913533098634,
             "WALK_ZERO": 1.2828913533098634,
             "BOTH_ZERO": 1.2828913533098643}
    arms = {}
    for name, blocks in paths.items():
        arms[name] = {
            "arm": name,
            "classification": "RSEE_V7_M02_CHANGED_CONFIG_DEV_ORIGINAL_REVIEW_ONLY",
            "actual_v7_science_trials": 0,
            "v_science_go": False,
            "real_s50_move_attested": True,
            "real_s51_eat_tested": False,
            "source_basal_physical_debit_independently_attested": False,
            "min_player_ticks_reached": 200,
            "real_motion_packets": 7 if name == "BASE_ON" else 9,
            "real_motion_path_blocks": blocks,
            "observed_walk_debit": blocks * .01 * (
                0 if name in ("WALK_ZERO", "BOTH_ZERO") else 1),
        }
    return {
        "classification": "RSEE_V7_M02_FIVE_ARM_DEV_SOURCE_REVIEW_ONLY",
        "producer_run": 38819265395,
        "s_original_head": "944a68ca36f90380ffa5481ba85a6f95ed08ba18",
        "all_five_originals_readonly_pass": True,
        "five_arms_readback": 5,
        "v7_science_trials": 0,
        "v7_science_go": False,
        "r_changed_config_engineering_qualified": False,
        "basal_per_tick_cost_directly_attested": False,
        "path_max_minus_min_blocks": max(paths.values()) - min(paths.values()),
        "paired_path_tolerance_met": False,
        "arms": arms,
    }


def test_physical_source_observed_does_not_admit_original():
    receipt = _receipt()
    original = copy.deepcopy(receipt)
    v = gate.review(receipt)
    assert v["classification"] == gate.CLASS
    assert v["arms_reviewed"] == 5
    assert v["science_trials_credited"] == 0
    assert not v["actual_paths_comparable"]
    assert not v["direct_basal_source_authenticated"]
    assert v["observed_path_max_minus_min_blocks"] > 0.24
    assert v["native_source_basal_written_cumulative"] == "NOT_IN_ORIGINALS"
    assert v["independent_changed_config_qualification"] is False
    assert receipt == original


@pytest.mark.parametrize(("field", "value"), [
    ("classification", "RSEE_V7_M02_SCIENCE_PASS"),
    ("producer_run", 38819265396),
    ("s_original_head", "0" * 40),
    ("all_five_originals_readonly_pass", False),
    ("five_arms_readback", 4),
    ("v7_science_trials", 5),
    ("v7_science_go", True),
    ("r_changed_config_engineering_qualified", True),
    ("basal_per_tick_cost_directly_attested", True),
    ("paired_path_tolerance_met", True),
    ("path_max_minus_min_blocks", 0.0),
])
def test_altered_source_level_claims_are_rejected(field, value):
    packet = _receipt()
    packet[field] = value
    with pytest.raises(gate.NotAdmitted):
        gate.review(packet)


@pytest.mark.parametrize(("field", "value"), [
    ("min_player_ticks_reached", 100),
    ("real_motion_packets", 0),
    ("real_motion_path_blocks", float("nan")),
    ("observed_walk_debit", 0),
    ("source_basal_physical_debit_independently_attested", True),
    ("real_s50_move_attested", False),
    ("actual_v7_science_trials", 1),
    ("real_s51_eat_tested", True),
])
def test_forged_arm_world_charge_and_promotion_rejected(field, value):
    packet = _receipt()
    packet["arms"]["BASE_ON"][field] = value
    with pytest.raises(gate.NotAdmitted):
        gate.review(packet)


def test_missing_duplicate_or_fake_sham_cannot_be_promoted():
    packet = _receipt()
    del packet["arms"]["BOTH_ZERO"]
    with pytest.raises(gate.NotAdmitted):
        gate.review(packet)


def test_matching_paths_by_editing_unqualified_original_is_rejected():
    packet = _receipt()
    packet["arms"]["BASE_ON"]["real_motion_path_blocks"] = 1.2828913533098643
    packet["arms"]["BASE_ON"]["observed_walk_debit"] = .012828913533098643
    with pytest.raises(gate.NotAdmitted, match="pair-difference"):
        gate.review(packet)
