"""Paper yaw source before S50 FORWARD: original-log ordering negative controls."""
from __future__ import annotations

import math

import pytest

from adapters.mineflayer.m02_paper_dev.s50_boundary import BoundaryRejected
from adapters.mineflayer.m02_paper_dev.s50_p1_flat_look_bracket import (
    screen_paper_look_forward_bracket,
)

MARKER = "m02-paper-walk-1-be9aa263-afac-4b17-945b-09eef6c47126"
WORLD = "bba420a8-7943-465f-997e-e857e7587b93"


def frame(n, yaw, *, world=WORLD, tick=23):
    return (
        "[Server thread/INFO]: S_V8_DEV_SNAPSHOT "
        f"marker_id={MARKER}-P1LOOK-{n:02d} world={world} seed=63101 "
        f"full_time={tick} player_tick=7 "
        f"x=0.5 y=-60.0 z=0.5 yaw={yaw} pitch=0.0 "
        "food=20 saturation=5 health=20 exhaustion=0.0"
    )


def phase(name, tick=24, *, world=WORLD):
    return (
        "[Server thread/INFO]: M02_DEV_S50_PHASE "
        f"marker_id={MARKER} phase={name} world_full_time={tick} "
        f"world={world} packets=0 blocks=0 billed=0 x=0.5 y=-60 z=0.5"
    )


def original(*, extra="", first_yaw="0", last_yaw="-90", omit_last=False):
    lines = [frame(1, first_yaw, tick=22)]
    if not omit_last:
        lines.append(frame(2, last_yaw, tick=23))
    lines += [
        phase("PRE_FORWARD", 24),
        phase("POST_FORWARD", 25),
        phase("PRE_CLEAR", 30),
        phase("POST_CLEAR", 31),
    ]
    if extra:
        lines.append(extra)
    return "\n".join(lines)+"\n"


def screen(text=None, *, witness=None):
    return screen_paper_look_forward_bracket(
        original() if text is None else text,
        marker=MARKER, requested_yaw_rad=-math.pi/2,
        producer_look_witness=witness,
    )


def test_factual_paper_yaw_must_precede_real_forward_phase():
    out = screen()
    assert out["final_yaw_matches"] is True
    assert out["last_yaw_paper_world_tick"] == 23
    assert out["pre_forward_paper_world_tick"] == 24
    assert out["paper_snapshots_before_forward"] == 2
    assert out["P1_wait_ticks_admitted"] == 0
    assert out["P1_fatigue_recovered"] == 0.0
    assert out["forward_motor_action_receipt"] == "SEPARATE_S15_S16_SOURCE_REQUIRED"


@pytest.mark.parametrize("mutate", [
    lambda x: x.replace("yaw=-90 ", "yaw=0 "),
    lambda x: x.replace("seed=63101", "seed=62101"),
    lambda x: x.replace("yaw=-90 ", "yaw=NaN "),
    lambda x: x.replace(f"{MARKER}-P1LOOK-02", f"{MARKER}-P1LOOK-03"),
    lambda x: x.replace("full_time=23", "full_time=26"),
    lambda x: x.replace("full_time=23", "full_time=21"),
    lambda x: x.replace("phase=PRE_FORWARD world_full_time=24",
                        "phase=PRE_FORWARD world_full_time=22"),
    lambda x: x.replace("phase=POST_FORWARD", "phase=PRE_FORWARD"),
    lambda x: x.replace("phase=PRE_FORWARD", "phase=POST_FORWARD"),
    lambda x: x.replace("x=0.5 y=-60.0 z=0.5 yaw=-90",
                        "x=0.5 y=-60.0 z=1.7 yaw=-90"),
    lambda x: x.replace("yaw=-90", "yaw=-90 yaw=-90"),
    lambda x: x.replace("yaw=-90", "yaw=90"),
    lambda x: x.replace("yaw=-90", "yaw=-90 pitch=11"),
])
def test_stale_or_forged_physical_snapshot_rejected(mutate):
    with pytest.raises(BoundaryRejected):
        screen(mutate(original()))


def test_snapshot_after_pre_forward_forbidden():
    raw = original()
    rows = raw.splitlines()
    rows.remove(frame(2, "-90", tick=23))
    rows.append(frame(2, "-90", tick=23))
    with pytest.raises(BoundaryRejected, match="after PRE_FORWARD"):
        screen("\n".join(rows))


def test_consistent_single_real_look_witness():
    raw = original(omit_last=True, first_yaw="-90")
    out = screen(raw)
    assert out["paper_snapshots_before_forward"] == 1


def test_no_snapshots_after_look_match():
    raw = original(first_yaw="-90", last_yaw="-90")
    with pytest.raises(BoundaryRejected, match="continued yaw polling"):
        screen(raw)


def test_mismatched_producer_receipt_cannot_authenticate_source():
    with pytest.raises(BoundaryRejected, match="producer yaw witness"):
        screen(witness={"orientation_matches": True, "paper_yaw_degrees": 0})


def test_misordered_or_unmatched_phase_world_fails():
    with pytest.raises(BoundaryRejected):
        screen(original().replace("phase=PRE_CLEAR", "phase=POST_CLEAR"))


def test_missing_phase_fails():
    with pytest.raises(BoundaryRejected):
        screen("\n".join(row for row in original().splitlines()
                         if "phase=POST_CLEAR" not in row))
