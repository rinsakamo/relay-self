"""Fail-closed two P1 model-F motor arms with both client speed maps enabled."""
from __future__ import annotations

from copy import deepcopy

import pytest

from adapters.mineflayer.s49_p1_dash_pair_review_dev import (
    compare_p1_pair_dev,
)
from adapters.mineflayer.s49_p1_synced_motor_pair_dev import (
    P1SyncedMotorPairRejected,
    validate_synced_pair_dev,
)
from test_s49_p1_dash_pair_review_dev import cases


def example():
    pair = compare_p1_pair_dev(*cases())
    witnesses = {}
    for case, key in (("CARRY", "carry_world"), ("WAIT_ASSUMED", "wait_assumed_world")):
        arm = pair[key]
        witnesses[case] = {
            "classification": "S49_NODE_PAPER_ATTRIBUTE_TO_PHYSICS_KEY_DIAGNOSTIC_DEV_ONLY",
            "session_id": arm["session_id"],
            "action_id": arm["first_action_id"],
            "native_sync_enabled": True,
            "node_packet_paper_dash_seen_count": 5,
            "node_decoded_generic_dash_seen_count": 20,
            "node_projected_physics_dash_seen_count": 16,
            "node_active_physics_key_dash_seen_count": 9,
            "node_physics_ticks_sampled": 12,
            "node_local_active_displacement_m": arm["first_native_distance_m"] - 0.1,
            "no_additional_packet_reader": True,
            "paper_native_clock_same_epoch": False,
            "physics_speed_attribute_consumed_proven": False,
            "physical_fatigue_attested": False,
            "actual_p1_state_updated": False,
            "native_action_changed": False,
            "qualification_go": False,
            "science_go": False,
        }
    return pair, witnesses


def test_two_original_s16_native_motor_outputs_and_node_physics_agree():
    pair, witnesses = example()
    saved = deepcopy((pair, witnesses))
    out = validate_synced_pair_dev(pair, witnesses)
    assert (pair, witnesses) == saved
    assert out["physical_movement_separation_observed"] is True
    assert out["actual_first_s16_displacement_gain_m"] == pytest.approx(.5)
    assert out["actual_paper_mean_boost_speed_gain_mps"] == pytest.approx(1.15)
    assert out["both_client_physicsticks_contain_paper_dash_bonus"] is True
    assert out["model_f_preloaded_not_lived"] is True
    assert out["same_self_longitudinal_wait_recovery_observed"] is False
    assert out["fatigue_recovery_causally_identified"] is False
    assert out["l0_physical_dash_power_admission"] is None
    assert out["new_native_action_issuers"] == 0
    assert out["new_native_packet_readers"] == 0
    assert out["qualification_go"] is False
    assert out["science_go"] is False


def test_not_observed_native_motor_gain_does_not_promote_l0():
    pair, witnesses = example()
    pair["wait_assumed_world"]["first_native_distance_m"] = (
        pair["carry_world"]["first_native_distance_m"]
    )
    pair["wait_assumed_world"]["paper_mean_boost_sampled_speed_mps"] = (
        pair["carry_world"]["paper_mean_boost_sampled_speed_mps"]
    )
    pair["measured_first_native_distance_delta_m"] = 0
    pair["measured_paper_boost_speed_delta_mps"] = 0
    pair["physical_output_difference_observed"] = False
    out = validate_synced_pair_dev(pair, witnesses)
    assert out["physical_movement_separation_observed"] is False
    assert out["physical_motor_gain_if_not_separated"] == "NOT_ESTABLISHED"
    assert out["l0_physical_dash_power_admission"] is None


@pytest.mark.parametrize("fault", [
    "wrong_source", "actual_fatigue", "actual_wait", "wrong_physical_delta",
    "fabricated_physical_gain", "same_world", "foreign_session",
    "wrong_action", "sync_off", "no_packet", "no_generic",
    "no_projected_key", "no_active_physics_key", "no_physics",
    "reader_added", "native_issued", "clock_conflation",
    "physics_consumption_claim", "fatigue_attested", "p1_updated",
    "posted_qualification", "model_f_changed", "no_source",
    "missing_arm", "fake_l0_grant", "not_original",
])
def test_p1_next_model_motor_source_negative_controls(fault):
    pair, witnesses = example()
    first = witnesses["CARRY"]
    rested = witnesses["WAIT_ASSUMED"]
    if fault == "wrong_source":
        pair["prior_p1_model_source_sha256"] = "f" * 64
    elif fault == "actual_fatigue":
        pair["actual_p1_fatigue_observed"] = True
    elif fault == "actual_wait":
        pair["same_self_longitudinal_wait_recovery"] = True
    elif fault == "wrong_physical_delta":
        pair["measured_first_native_distance_delta_m"] = 20.0
    elif fault == "fabricated_physical_gain":
        pair["physical_output_difference_observed"] = False
    elif fault == "same_world":
        pair["wait_assumed_world"]["paper_world_uuid"] = pair["carry_world"]["paper_world_uuid"]
    elif fault == "foreign_session":
        first["session_id"] = "other"
    elif fault == "wrong_action":
        rested["action_id"] = "unrelated"
    elif fault == "sync_off":
        first["native_sync_enabled"] = False
    elif fault == "no_packet":
        rested["node_packet_paper_dash_seen_count"] = 0
    elif fault == "no_generic":
        rested["node_decoded_generic_dash_seen_count"] = 0
    elif fault == "no_projected_key":
        rested["node_projected_physics_dash_seen_count"] = 0
    elif fault == "no_active_physics_key":
        first["node_active_physics_key_dash_seen_count"] = 0
    elif fault == "no_physics":
        first["node_physics_ticks_sampled"] = 0
    elif fault == "reader_added":
        rested["no_additional_packet_reader"] = False
    elif fault == "native_issued":
        rested["native_action_changed"] = True
    elif fault == "clock_conflation":
        first["paper_native_clock_same_epoch"] = True
    elif fault == "physics_consumption_claim":
        first["physics_speed_attribute_consumed_proven"] = True
    elif fault == "fatigue_attested":
        rested["physical_fatigue_attested"] = True
    elif fault == "p1_updated":
        rested["actual_p1_state_updated"] = True
    elif fault == "posted_qualification":
        rested["qualification_go"] = True
    elif fault == "model_f_changed":
        pair["carry_world"]["preloaded_hypothetical_fatigue"] = 0.1
    elif fault == "no_source":
        pair["carry_world"]["actual_source_frames_verified"] = False
    elif fault == "missing_arm":
        witnesses.pop("CARRY")
    elif fault == "fake_l0_grant":
        pair["physically_qualified_l0_power_admission"] = 1.0
    else:
        pair["new_action_issuers"] = 1
    with pytest.raises(P1SyncedMotorPairRejected):
        validate_synced_pair_dev(pair, witnesses)
