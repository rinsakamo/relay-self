"""Coordinate-grounded Paper WALK review adversarial synthetic original logs."""
from __future__ import annotations

import pytest

from experiments.standard_env import v7_m02_motion_trace_audit as trace


def original():
    return (
        "M02_DEV_BASAL_WRITE id=1 world_full_time=17 before=0.0 requested=0.001 "
        "write_target=0.001 observed_after=0.001 cumulative_requested=0.001 "
        "x=0.5 y=65 z=0.5 yaw=0 pitch=0\n"
        "M02_DEV_MOTION id=1 reason=WALK blocks=0.5 billed=0.005 "
        "cumulative_blocks=0.5 cumulative_billed=0.005 "
        "from_x=0.5 from_y=65.0 from_z=0.5 "
        "to_x=1.0 to_y=65.0 to_z=0.5 world_full_time=21\n"
        "M02_DEV_MOTION id=2 reason=WALK blocks=0.25 billed=0.0025 "
        "cumulative_blocks=0.75 cumulative_billed=0.0075 "
        "from_x=1.0 from_y=65.0 from_z=0.5 "
        "to_x=1.25 to_y=65.0 to_z=0.5 world_full_time=22\n"
    ).encode()


def test_actual_pose_and_world_tick_are_source_diagnostics_only():
    x=trace.review(original())
    assert x["packet_count"]==2
    assert x["motion_path_blocks"]==pytest.approx(.75)
    assert x["net_horizontal_displacement_blocks"]==pytest.approx(.75)
    assert x["observed_charge_per_actual_block"]==pytest.approx(.01)
    assert x["first_native_motion_from_xyz"]==[.5,65,.5]
    assert x["last_native_motion_to_xyz"]==[1.25,65,.5]
    assert x["motion_time_span_world_ticks"]==1
    assert x["first_motion_time_relative_to_first_basal"]==4
    assert not x["collision_cause_attested"]
    assert not x["engineering_qualification"]
    assert not x["scientific_comparison_admitted"]


@pytest.mark.parametrize(("old","new","why"),[
    ("blocks=0.5","blocks=0.8","reconstruct"),
    ("cumulative_blocks=0.75","cumulative_blocks=0.7","cumulative"),
    ("id=2 reason=WALK","id=1 reason=WALK","movement ID"),
    ("to_x=1.25","to_x=nan","coordinate-complete"),
    ("reason=WALK","reason=SPRINT","non-WALK"),
    ("world_full_time=22","world_full_time=abc","coordinate-complete"),
])
def test_corrupted_paper_source_is_not_admitted(old,new,why):
    raw=original().replace(old.encode(),new.encode())
    with pytest.raises(trace.InvalidMotion,match=why):
        trace.review(raw)


def test_no_motion_does_not_get_invented_zero_block_rate():
    with pytest.raises(trace.InvalidMotion,match="no bounded"):
        trace.review(b"Paper plugin enabled\n")
