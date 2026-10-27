"""Original S49 S15 Paper producer target readback stays DEV-only."""
from __future__ import annotations

from copy import deepcopy

import pytest

from adapters.mineflayer.s49_p1_original_owner_hold_review_dev import (
    S49OriginalOwnerHoldReviewRejected,
    join_original_owner_hold_dev,
)
from adapters.mineflayer.s49_p1_steady_phase_review_dev import (
    compare_steady_phase_dev,
)
from test_s49_p1_steady_phase_review_dev import example


def source():
    previous, traces = example()
    prior = compare_steady_phase_dev(previous, traces)
    arms = {}
    for case in ("CARRY", "WAIT_ASSUMED"):
        pap = previous["arms"][case]
        record = {
            "classification": "ORIGINAL_S49_S15_PAPER_PRODUCER_TICK_HOLD_DEV_ONLY",
            "action_id": pap["action_id"],
            "session_id": pap["session_id"],
            "world": pap["world"],
            "paper_hold_target_sample_index": 15,
            "paper_hold_target_world_tick": 264 if case == "CARRY" else 265,
            "paper_positive_boost_ticks_before_release": 7,
            "same_original_s15_clear_owner": True,
            "node_paper_host_clocks_synchronized": False,
            "native_action_duration_world_ticks_exact": False,
            "qualification_go": False,
            "science_go": False,
        }
        arms[case] = {
            "first_action_id": pap["action_id"],
            "session_id": pap["session_id"],
            "world": pap["world"],
            "first_native_displacement_m": 3.7 if case == "CARRY" else 4.1,
            "hold": record,
        }
    return prior, arms


def test_original_s15_hold_receipt_stays_source_local():
    prior, arms = source()
    saved = deepcopy((prior, arms))
    r = join_original_owner_hold_dev(prior, arms)
    assert (prior, arms) == saved
    assert r["same_paper_hold_target_both_worlds"] is True
    assert r["paper_owner_first_action_hold_target_index"] == 15
    assert r["native_first_s16_displacement_gain_m"] == pytest.approx(.4)
    assert r["same_native_action_elapsed_world_ticks_proven"] is False
    assert r["original_s49_sole_native_action_issuer"] is True
    assert r["physical_L0_DASH_admission"] is None
    assert r["source_bound_wait_admitted"] is False
    assert r["qualification_go"] is False


@pytest.mark.parametrize("fault", [
    "prior_promoted", "fake_world_sync", "native_grant", "other_issuer",
    "negative_fatigue_claim", "missing_case", "other_session",
    "wrong_world", "wrong_action", "bad_count", "bad_target",
    "foreign_clear", "claimed_native_clock", "claimed_full_duration",
    "qualified", "no_displacement", "same_world", "missing_receipt",
])
def test_reject_foreign_or_promoted_original_s15_hold(fault):
    prior, arms = source()
    rested = arms["WAIT_ASSUMED"]
    receipt = rested["hold"]
    if fault == "prior_promoted":
        prior["classification"] = "QUALIFIED_NATIVE"
    elif fault == "fake_world_sync":
        prior["world_tick_phase_synchronized"] = True
    elif fault == "native_grant":
        prior["physical_l0_dash_capability_admitted"] = 1.
    elif fault == "other_issuer":
        prior["new_native_action_issuers"] = 1
    elif fault == "negative_fatigue_claim":
        prior["model_preload_not_true_same_self_recovery"] = False
    elif fault == "missing_case":
        arms.pop("WAIT_ASSUMED")
    elif fault == "other_session":
        receipt["session_id"] = "foreign"
    elif fault == "wrong_world":
        receipt["world"] = "other"
    elif fault == "wrong_action":
        receipt["action_id"] = "other"
    elif fault == "bad_count":
        receipt["paper_positive_boost_ticks_before_release"] = 8
    elif fault == "bad_target":
        receipt["paper_hold_target_sample_index"] = 14
    elif fault == "foreign_clear":
        receipt["same_original_s15_clear_owner"] = False
    elif fault == "claimed_native_clock":
        receipt["node_paper_host_clocks_synchronized"] = True
    elif fault == "claimed_full_duration":
        receipt["native_action_duration_world_ticks_exact"] = True
    elif fault == "qualified":
        receipt["qualification_go"] = True
    elif fault == "no_displacement":
        rested["first_native_displacement_m"] = float("nan")
    elif fault == "same_world":
        rested["world"] = arms["CARRY"]["world"]
        receipt["world"] = arms["CARRY"]["world"]
    else:
        rested.pop("hold")
    with pytest.raises(S49OriginalOwnerHoldReviewRejected):
        join_original_owner_hold_dev(prior, arms)
