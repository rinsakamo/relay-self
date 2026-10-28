"""Fail-closed DEV source/control contract for Node attribute trace ON/OFF."""
from __future__ import annotations

from copy import deepcopy

import pytest

from adapters.mineflayer.s49_p1_attr_trace_ab_review_dev import (
    P1AttributeTraceABRejected,
    summarize_trace_ab_dev,
)


def fixture():
    records = {}
    for mode in ("ON", "OFF"):
        for case in ("CARRY", "WAIT_ASSUMED"):
            name = f"{mode}_{case}"
            present = mode == "ON"
            records[name] = {
                "mode": mode, "case": case,
                "first_action_id": f"action-{name}",
                "session_id": f"session-{name}",
                "world_uuid": f"world-{name}",
                "native_action_count": 2,
                "original_s49_source_verified": True,
                "speed_attribute_projection_enabled": True,
                "original_s49_action_owner_unchanged": True,
                "paper_positive_boost_ticks": 7,
                "paper_original_owner_release": True,
                "node_attribute_observer_enabled": present,
                "node_attribute_trace_file_exists": present,
                "node_active_physics_ticks": 12 if present else None,
                "node_visible_dash_ticks": 6 if present else None,
                "first_native_distance_m": 3.4 if case == "CARRY" else 4.0,
                "paper_mean_positive_speed_mps": (
                    6.7 if case == "CARRY" else 7.5
                ),
                "qualification_go": False,
                "science_go": False,
            }
    return records


def test_all_four_real_source_shaped_arms_compared_without_faking_off_ticks():
    f = fixture()
    copy = deepcopy(f)
    r = summarize_trace_ab_dev(f)
    assert f == copy
    assert r["classification"] == (
        "P1_NODE_ATTRIBUTE_OBSERVER_ON_OFF_FOUR_WORLD_DEV_ONLY"
    )
    assert r["velocity_projection_identical_and_enabled_in_all_arms"] is True
    assert r["node_trace_off_has_no_node_tick_attestation"] is True
    assert r["observer_causally_responsible_for_delta_proven"] is False
    assert r["paper_node_phase_synchronized"] is False
    assert r["qualification_go"] is False
    assert r["science_go"] is False
    assert r["per_model_on_off_observations"]["CARRY"][
        "off_node_visible_dash_ticks"
    ] is None


def test_genuine_negative_or_zero_motor_response_is_data():
    arms = fixture()
    arms["OFF_CARRY"]["first_native_distance_m"] = 2.5
    arms["OFF_WAIT_ASSUMED"]["first_native_distance_m"] = 4.0
    result = summarize_trace_ab_dev(arms)
    assert result["per_model_on_off_observations"]["CARRY"][
        "off_minus_on_first_s16_distance_m"
    ] < 0
    assert result["per_model_on_off_observations"]["WAIT_ASSUMED"][
        "off_minus_on_first_s16_distance_m"
    ] == 0


@pytest.mark.parametrize("fault", [
    "absent", "extra", "mode", "case", "session", "world",
    "foreign_owner", "no_projection", "lost_paper", "bad_release",
    "observer_off_but_exists", "observer_on_but_missing",
    "invented_off_node", "invented_off_dash", "missing_on_node",
    "invalid_on_dash", "fake_qualified", "fake_science",
    "nonfinite_distance", "foreign_action_count",
])
def test_source_identity_and_observer_isolation_fails_closed(fault):
    f = fixture()
    arm = f["OFF_CARRY"]
    if fault == "absent":
        f.pop("OFF_CARRY")
    elif fault == "extra":
        f["other"] = deepcopy(arm)
    elif fault == "mode":
        arm["mode"] = "ON"
    elif fault == "case":
        arm["case"] = "WAIT_ASSUMED"
    elif fault == "session":
        arm["session_id"] = f["ON_CARRY"]["session_id"]
    elif fault == "world":
        arm["world_uuid"] = f["ON_CARRY"]["world_uuid"]
    elif fault == "foreign_owner":
        arm["original_s49_action_owner_unchanged"] = False
    elif fault == "no_projection":
        arm["speed_attribute_projection_enabled"] = False
    elif fault == "lost_paper":
        arm["paper_positive_boost_ticks"] = 6
    elif fault == "bad_release":
        arm["paper_original_owner_release"] = False
    elif fault == "observer_off_but_exists":
        arm["node_attribute_trace_file_exists"] = True
    elif fault == "observer_on_but_missing":
        f["ON_CARRY"]["node_attribute_trace_file_exists"] = False
    elif fault == "invented_off_node":
        arm["node_active_physics_ticks"] = 12
    elif fault == "invented_off_dash":
        arm["node_visible_dash_ticks"] = 6
    elif fault == "missing_on_node":
        f["ON_CARRY"]["node_active_physics_ticks"] = None
    elif fault == "invalid_on_dash":
        f["ON_CARRY"]["node_visible_dash_ticks"] = 99
    elif fault == "fake_qualified":
        arm["qualification_go"] = True
    elif fault == "fake_science":
        arm["science_go"] = True
    elif fault == "nonfinite_distance":
        arm["first_native_distance_m"] = float("nan")
    else:
        arm["native_action_count"] = 1
    with pytest.raises(P1AttributeTraceABRejected):
        summarize_trace_ab_dev(f)
