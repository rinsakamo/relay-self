"""G4.2 strictly joined native brake and following-position windows."""
import pytest

from adapters.mineflayer.g42_native_brake_timing_dev import (
    qualify_g42_native_window_dev,
)


def window(**changes):
    payload={
        "action_id":"goal-approach-demo-step-2",
        "session_id":"g42-session",
        "brake_seq":52,"brake_host_ns":1_500_000_000,
        "clear_seq":53,"clear_host_ns":1_517_000_000,
        "after_seq":55,"after_x":3.0,"after_z":2.0,
        "after_host_ns":1_535_000_000,
        "next_seq":58,"next_x":3.0,"next_z":2.1,
        "next_host_ns":1_750_000_000,
    }
    payload.update(changes)
    return qualify_g42_native_window_dev(**payload)


def test_g42_ordered_same_action_host_time_and_native_drift():
    item=window()
    assert item.brake_to_clear_ack_host_ms==pytest.approx(17.)
    assert item.after_s16_to_next_probe_host_ms==pytest.approx(215.)
    assert item.postclear_drift_candidate_m==pytest.approx(.1)
    assert not item.inertia_causality_attested
    assert not item.paper_tick_latency_attested
    assert not item.motor_speed_change_attested


def test_g42_no_brake_still_measures_interaction_gap():
    item=window(brake_seq=None,brake_host_ns=None)
    assert item.brake_to_clear_ack_host_ms is None
    assert item.postclear_drift_candidate_m>0


@pytest.mark.parametrize("bad",[
    {"brake_seq":54},{"brake_host_ns":1_517_000_000},
    {"clear_seq":55},{"after_seq":53},{"next_seq":55},
    {"next_host_ns":1_535_000_000},{"after_host_ns":1_518_000_000,
                                     "clear_host_ns":1_520_000_000},
    {"brake_seq":None},{"brake_host_ns":None},
    {"after_z":float("nan")},{"action_id":"unbound"},
    {"clear_seq":True},{"next_host_ns":True},
])
def test_g42_fails_closed_for_forged_or_unordered_window(bad):
    with pytest.raises(ValueError,match="G4.2"):
        window(**bad)
