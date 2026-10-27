"""Offline DEV negative controls for original S49 first Action Node hold readback."""
from __future__ import annotations

from copy import deepcopy

import pytest

from adapters.mineflayer.s49_p1_native_hold_pair_dev import (
    P1NativeHoldRejected,
    compare_first_native_hold_dev,
)


def fixture_pair(*, hold_ms=610, ticks=12):
    pair = {
        "classification":
            "P1_TWO_INDEPENDENT_WORLDS_MATCHED_SEVEN_BONUS_TICKS_DEV_ONLY",
        "same_number_of_positive_paper_boost_ticks": True,
        "world_clock_phase_matched": False,
        "original_s49_first_action_duration_matched_by_world_tick": False,
        "model_preload_not_actual_longitudinal_p1_recovery": True,
        "native_displacement_causally_attributed_only_to_p1": False,
        "native_original_s16_displacement_gain_m": 0.478,
        "qualification_go": False, "science_go": False,
        "arms": {},
    }
    traces, witnesses = {}, {}
    for i, case in enumerate(("CARRY", "WAIT_ASSUMED")):
        sid, action = f"sid-{i}", f"action-{i}"
        pair["arms"][case] = {
            "action_id": action, "session_id": sid,
            "exact_paper_positive_bonus_ticks": 7,
            "paper_total_gait_ticks": 13,
            "paper_action_owner_issued": False,
            "qualification_go": False,
        }
        rows = [{"kind": "FIRST_ORIGINAL_SET", "ordinal": 1,
                 "monotonic_ms": 100}]
        for j in range(1, ticks + 1):
            rows.append({
                "kind": "ACTIVE_PHYSICS", "ordinal": j + 1,
                "monotonic_ms": 100 + 30 * j,
                "physics_ordinal": j, "forward": True, "sprint": True,
            })
        rows.append({"kind": "FIRST_ORIGINAL_CLEAR", "ordinal": len(rows) + 1,
                     "monotonic_ms": 100 + hold_ms})
        traces[case] = {
            "version": "S49_SPEED_ATTR_NATIVE_BOUNDARY_DEV_V1",
            "session_id": sid, "action_id": action,
            "source_attested": False, "paper_clock_synchronized": False,
            "added_issuers": 0, "added_readers": 0, "complete": True,
            "physics_ticks": ticks, "rows": rows,
        }
        witnesses[case] = {
            "classification":
                "S49_NODE_PAPER_ATTRIBUTE_TO_PHYSICS_KEY_DIAGNOSTIC_DEV_ONLY",
            "session_id": sid, "action_id": action,
            "no_additional_packet_reader": True,
            "paper_native_clock_same_epoch": False,
            "node_physics_ticks_sampled": ticks,
            "node_active_physics_key_dash_seen_count": 6,
            "qualification_go": False, "science_go": False,
        }
    return pair, traces, witnesses


def test_native_and_paper_window_match_is_observation_not_tick_control():
    pair, traces, witnesses = fixture_pair()
    original = deepcopy((pair, traces, witnesses))
    result = compare_first_native_hold_dev(pair, traces, witnesses)
    assert original == (pair, traces, witnesses)
    assert result["classification"] == (
        "P1_FIRST_ACTION_OBSERVED_NODE_HOLD_AND_TICKS_MATCH_DEV_ONLY"
    )
    assert result["node_active_physics_tick_counts_equal"] is True
    assert result["paper_action_gait_tick_counts_equal"] is True
    assert result["node_boost_attribute_physics_tick_counts_equal"] is True
    assert result["node_local_hold_delta_ms"] == 0
    assert result["paper_and_node_phase_aligned"] is False
    assert result["original_action_duration_tick_controlled_by_node"] is False
    assert result["original_action_tick_controlled_by_paper"] is False
    assert result["qualification_go"] is False
    assert result["science_go"] is False


@pytest.mark.parametrize("mismatch", [
    "hold_ms", "physics_count", "paper_count", "boost_count",
])
def test_native_hold_nonmatches_are_data_not_physical_claims(mismatch):
    pair, traces, witnesses = fixture_pair()
    if mismatch == "hold_ms":
        traces["WAIT_ASSUMED"]["rows"][-1]["monotonic_ms"] += 75
    elif mismatch == "physics_count":
        trace = traces["WAIT_ASSUMED"]
        trace["rows"].pop(-2)
        trace["physics_ticks"] -= 1
        trace["rows"][-1]["ordinal"] -= 1
        witnesses["WAIT_ASSUMED"]["node_physics_ticks_sampled"] -= 1
    elif mismatch == "paper_count":
        pair["arms"]["WAIT_ASSUMED"]["paper_total_gait_ticks"] += 1
    else:
        witnesses["WAIT_ASSUMED"]["node_active_physics_key_dash_seen_count"] -= 1
    result = compare_first_native_hold_dev(pair, traces, witnesses)
    assert result["classification"] == (
        "P1_FIRST_ACTION_NODE_HOLD_MATCH_NOT_ESTABLISHED_DEV_ONLY"
    )
    assert result["qualification_go"] is False


@pytest.mark.parametrize("fault", [
    "fake_phase", "fake_qualified", "foreign_session", "same_session",
    "duplicate_set", "duplicate_ordinal", "reverse_clock", "bad_controls",
    "bad_tick_counter", "fake_attestation", "foreign_witness", "short_hold",
    "unexpected_reader", "foreign_action", "fake_recovery",
])
def test_native_first_action_source_fails_closed_on_integrity_fault(fault):
    pair, traces, witnesses = fixture_pair()
    arm = pair["arms"]["CARRY"]
    trace = traces["CARRY"]
    if fault == "fake_phase":
        pair["world_clock_phase_matched"] = True
    elif fault == "fake_qualified":
        pair["qualification_go"] = True
    elif fault == "foreign_session":
        trace["session_id"] = "alien"
    elif fault == "same_session":
        pair["arms"]["WAIT_ASSUMED"]["session_id"] = arm["session_id"]
        traces["WAIT_ASSUMED"]["session_id"] = arm["session_id"]
        witnesses["WAIT_ASSUMED"]["session_id"] = arm["session_id"]
    elif fault == "duplicate_set":
        trace["rows"][1]["kind"] = "FIRST_ORIGINAL_SET"
    elif fault == "duplicate_ordinal":
        trace["rows"][2]["ordinal"] = 2
    elif fault == "reverse_clock":
        trace["rows"][2]["monotonic_ms"] = 50
    elif fault == "bad_controls":
        trace["rows"][2]["sprint"] = False
    elif fault == "bad_tick_counter":
        trace["physics_ticks"] += 1
    elif fault == "fake_attestation":
        trace["paper_clock_synchronized"] = True
    elif fault == "foreign_witness":
        witnesses["CARRY"]["action_id"] = "alien"
    elif fault == "short_hold":
        trace["rows"][-1]["monotonic_ms"] = 300
    elif fault == "unexpected_reader":
        trace["added_readers"] = 1
    elif fault == "foreign_action":
        trace["action_id"] = "alien"
    else:
        pair["model_preload_not_actual_longitudinal_p1_recovery"] = False
    with pytest.raises(P1NativeHoldRejected):
        compare_first_native_hold_dev(pair, traces, witnesses)
