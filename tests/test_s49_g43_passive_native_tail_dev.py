"""G4.3 native quiet-reference controls are strict, not causal claims."""
from dataclasses import replace

import pytest

from adapters.mineflayer.g43_passive_native_tail_dev import (
    G43PassiveNativeSampleDev,
    qualify_g43_passive_native_tail_dev,
)


def cases(**changes):
    samples=tuple(G43PassiveNativeSampleDev(
        label=label,session_id="session-x",source_seq=101+i,
        request_id=f"goal-demo-step-2-g43-off-{i}",source="mineflayer",
        x=0.0,z=z,host_ns=2_000_000_000+i*250_000_000,
        entities_truncated=False,
    ) for i,(label,z) in enumerate((
        ("EARLY_40",1.11),("EARLY_120",1.18),("MID_300",1.21),
        ("QUIET_550",1.22),("QUIET_800",1.221),
    )))
    payload={
        "action_id":"goal-demo-step-2","session_id":"session-x",
        "clear_seq":98,"s16_seq":100,"s16_x":0.0,"s16_z":1.0,
        "s16_host_ns":1_900_000_000,
        "samples":samples,"original_action_closed":True,
    }
    payload.update(changes)
    return qualify_g43_passive_native_tail_dev(**payload)


def test_g43_reports_host_bracketed_movement_with_noncausal_quiet_reference():
    v=cases()
    assert v.early_s16_to_120_m==pytest.approx(.18)
    assert v.mid_120_to_300_m==pytest.approx(.03)
    assert v.quiet_550_to_800_m==pytest.approx(.001)
    assert v.full_s16_to_800_m==pytest.approx(.221)
    assert v.no_new_s49_motor_during_samples
    assert not v.independently_randomized_control
    assert not v.physical_input_off_per_tick_attested
    assert not v.inertia_causality_attested


def test_g43_held_still_is_acceptable():
    old=cases()
    v=cases(samples=tuple(replace(p,z=1.0) for p in old.samples))
    assert v.early_s16_to_120_m==v.quiet_550_to_800_m==0.0


@pytest.mark.parametrize("broken",[
    {"clear_seq":100},{"s16_host_ns":2_100_000_000},
    {"original_action_closed":False},{"session_id":"wrong"},
    {"s16_z":float("nan")},{"samples":()},
])
def test_g43_refuses_invalid_source_or_open_action(broken):
    with pytest.raises(ValueError,match="G4.3"):
        cases(**broken)


@pytest.mark.parametrize("index,change",[
    (0,{"source":"fabricated"}),(1,{"session_id":"foreign"}),
    (2,{"source_seq":101}),(3,{"request_id":"old"}),
    (4,{"entities_truncated":True}),(0,{"host_ns":1}),
    (2,{"x":float("inf")}),
])
def test_g43_refuses_foreign_or_stale_sample(index,change):
    orig=cases().samples
    bad=tuple(replace(v,**change) if i==index else v for i,v in enumerate(orig))
    with pytest.raises(ValueError,match="G4.3"):
        cases(samples=bad)
