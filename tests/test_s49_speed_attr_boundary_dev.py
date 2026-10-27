"""Fail-closed Node-source-local attribute packet / physics witness tests."""
from __future__ import annotations

import json
from copy import deepcopy

import pytest

from adapters.mineflayer.s49_speed_attr_boundary_dev import (
    SpeedAttrBoundaryRejected,
    review_speed_attr_boundary_dev,
)
from adapters.mineflayer.s49_speed_attr_onoff_pair_dev import (
    AttributePairRejected,
    compare_attr_pair_dev,
)


def trace(sync=True):
    bonus = {"uuid": "relays49dashdev:forward_dash_only", "amount": .38, "operation": 2}
    sprint = {"uuid": "minecraft:sprinting", "amount": .3, "operation": 2}
    source = {"value": .1, "modifiers": [sprint, bonus]}
    target = {"value": .1, "modifiers": [bonus]}
    def row(kind, n, **data):
        return {
            "kind": kind, "ordinal": n, "monotonic_ms": 100 + n,
            "raw_generic_scale": source,
            "physics_movement_speed": target if sync else None,
            **data,
        }
    return {
        "version": "S49_SPEED_ATTR_NATIVE_BOUNDARY_DEV_V1",
        "session_id": "sid-one", "action_id": "action-one",
        "sync_enabled": sync, "source_attested": False,
        "paper_clock_synchronized": False,
        "added_issuers": 0, "added_readers": 0,
        "physics_ticks": 3, "complete": True,
        "rows": [
            row("FIRST_ORIGINAL_SET", 1),
            row("RAW_PACKET", 2, packet_properties=[
                {"key": "generic.scale", **source},
            ]),
            row("DECODED_ATTR", 3),
            row("ACTIVE_PHYSICS", 4, physics_ordinal=1,
                forward=True, sprint=True, x=1., z=2., vx=0., vz=.1),
            row("ACTIVE_PHYSICS", 5, physics_ordinal=2,
                forward=True, sprint=True, x=1., z=2.2, vx=0., vz=.2),
            row("ACTIVE_PHYSICS", 6, physics_ordinal=3,
                forward=True, sprint=True, x=1., z=2.5, vx=0., vz=.3),
            row("FIRST_ORIGINAL_CLEAR", 7),
        ],
    }


def write(tmp_path, payload):
    p = tmp_path / "native_boundary.json"
    p.write_text(json.dumps(payload), encoding="utf-8")
    return p


@pytest.mark.parametrize("sync", [False, True])
def test_source_local_packet_and_physics_key_compared_without_new_reader(tmp_path, sync):
    p = write(tmp_path, trace(sync))
    v = review_speed_attr_boundary_dev(
        p, session_id="sid-one", action_id="action-one",
        sync_expected=sync,
    )
    assert v["node_packet_paper_dash_seen_count"] == 1
    assert v["node_decoded_generic_dash_seen_count"] > 0
    assert (v["node_active_physics_key_dash_seen_count"] > 0) is sync
    assert v["node_physics_ticks_sampled"] == 3
    assert v["node_local_active_displacement_m"] == pytest.approx(.5)
    assert v["no_additional_packet_reader"] is True
    assert v["physics_speed_attribute_consumed_proven"] is False
    assert v["qualification_go"] is False


@pytest.mark.parametrize("fault", [
    "session", "action", "mode", "owner", "reader", "clock", "duplicate",
    "time", "kind", "not_complete", "miss_source", "fake_power", "foreign_packet",
    "bad_physics", "missing_phase", "bad_ordinal", "extra_ticks",
])
def test_reject_forged_or_nonlocal_native_trace(tmp_path, fault):
    a = trace()
    if fault == "session":
        a["session_id"] = "foreign"
    elif fault == "action":
        a["action_id"] = "other"
    elif fault == "mode":
        a["sync_enabled"] = False
    elif fault == "owner":
        a["added_issuers"] = 1
    elif fault == "reader":
        a["added_readers"] = 1
    elif fault == "clock":
        a["paper_clock_synchronized"] = True
    elif fault == "duplicate":
        a["rows"].append(deepcopy(a["rows"][-1]))
    elif fault == "time":
        a["rows"][3]["monotonic_ms"] = 0
    elif fault == "kind":
        a["rows"][3]["kind"] = "ACTION_GRANTED"
    elif fault == "not_complete":
        a["complete"] = False
    elif fault == "miss_source":
        del a["rows"][1]["packet_properties"]
    elif fault == "fake_power":
        a["rows"][3]["physics_movement_speed"]["modifiers"] = [
            {"uuid": "relays49dashdev:forward_dash_only", "amount": 1., "operation": 2}
        ]
    elif fault == "foreign_packet":
        a["rows"][1]["packet_properties"][0]["key"] = "foreign:attr"
    elif fault == "bad_physics":
        a["rows"][4]["vx"] = float("nan")
    elif fault == "missing_phase":
        a["rows"][-1]["kind"] = "ACTIVE_PHYSICS"
    elif fault == "bad_ordinal":
        a["rows"][5]["physics_ordinal"] = 15
    else:
        a["physics_ticks"] += 1
    with pytest.raises(SpeedAttrBoundaryRejected):
        review_speed_attr_boundary_dev(
            write(tmp_path, a), session_id="sid-one", action_id="action-one",
            sync_expected=True,
        )


def pair():
    base = {
        "sync_on": False, "session_id": "sid-off",
        "first_health": 20., "first_food": 20., "first_y": -60.,
        "first_threat_distance_m": 2.,
        "first_native_distance_m": 3.,
        "paper_first_applied_power": .766,
        "paper_boosted_ticks": 11,
        "paper_sampled_peak_speed_mps": 5.6,
        "first_node_boundary": {
            "native_sync_enabled": False,
            "node_active_physics_key_dash_seen_count": 0,
            "node_packet_paper_dash_seen_count": 5,
        },
        "m0_posted_by_original_s49_only": True,
        "original_native_sources_verified": True,
    }
    on = deepcopy(base)
    on["sync_on"] = True
    on["session_id"] = "sid-on"
    on["first_native_distance_m"] = 4.
    on["paper_sampled_peak_speed_mps"] = 8.
    on["first_node_boundary"]["native_sync_enabled"] = True
    on["first_node_boundary"]["node_active_physics_key_dash_seen_count"] = 10
    return base, on


def test_same_f_physics_key_on_off_measured_but_not_wait_recovery():
    off, on = pair()
    before = deepcopy((off, on))
    v = compare_attr_pair_dev(off, on)
    assert (off, on) == before
    assert v["client_paper_packet_witness_seen"] is True
    assert v["client_speed_attribute_physicsticked"] is True
    assert v["native_positive_gain_observed"] is True
    assert v["actual_longitudinal_p1_recovery_measured"] is False
    assert v["qualified_l0_power_admission"] is None


@pytest.mark.parametrize("fault", [
    "same_session", "wrong_mode", "changed_p1", "stale_health",
    "missing_source", "foreign_stimulus", "no_paper_ticks",
])
def test_invalid_same_f_pair_rejected(fault):
    off, on = pair()
    if fault == "same_session":
        on["session_id"] = off["session_id"]
    elif fault == "wrong_mode":
        on["first_node_boundary"]["native_sync_enabled"] = False
    elif fault == "changed_p1":
        on["paper_first_applied_power"] = 1.
    elif fault == "stale_health":
        on["first_health"] = 18.
    elif fault == "missing_source":
        on["original_native_sources_verified"] = False
    elif fault == "foreign_stimulus":
        on["first_threat_distance_m"] = 10.
    else:
        on["paper_boosted_ticks"] = 0
    with pytest.raises(AttributePairRejected):
        compare_attr_pair_dev(off, on)
