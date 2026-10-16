"""Synthetic S/P1 WAIT source gates. NEVER R independent physical attestation."""
from __future__ import annotations

import pytest

from adapters.mineflayer.m02_paper_dev.s50_boundary import BoundaryRejected
from adapters.mineflayer.m02_paper_dev.s50_p1_wait import candidate_wait_ticks


def fixture() -> str:
    records = [
        "S50_DEV_WAIT_BEGIN marker_id=action-session world=world tick=40 "
        "packets=11 blocks=1.7 tick_meter_blocks=1.71 "
        "combat_events=0 swing_events=0 basal_ticks=41 x=2 y=-60 z=0.5"
    ]
    for i in range(1, 9):
        records.append(
            f"S50_DEV_WAIT_TICK marker_id=action-session world=world "
            f"tick={40+i} index={i} "
            "from_x=2 from_y=-60 from_z=0.5 x=2 y=-60 z=0.5 "
            "motion_packets=11 motion_blocks=1.7 tick_meter_blocks=1.71 "
            "combat_events=0 swing_events=0 sprint=false sneak=false swimming=false "
            f"basal_ticks={41+i}"
        )
    return "\n".join(records)


def check(source: str, *, status: str = "outcome") -> dict:
    return candidate_wait_ticks(
        source, marker_id="action-session", expected_world="world",
        source_action_terminal=status,
    )


def test_wait_source_candidate_has_zero_recovery_even_with_eight_quiet_snapshots():
    receipt = check(fixture())
    assert receipt["source_stationary_8_of_8"] is True
    assert receipt["first_world_tick"] == 41
    assert receipt["last_world_tick"] == 48
    assert receipt["wait_ticks_admitted"] == 0
    assert receipt["p1_fatigue_recovered"] == 0
    assert receipt["r_full_tick_activity_witness"] == "NOT_ATTESTED"
    assert not receipt["source_original_authenticated_by_r"]
    assert receipt["m02_basal_continues"]
    assert len(receipt["samples"]) == 8
    assert all(not x["p1_wait_recovery_admitted"] for x in receipt["samples"])


@pytest.mark.parametrize("before,after", [
    ("tick=43 index=3", "tick=44 index=3"),  # missing World tick
    ("tick=43 index=3", "tick=42 index=3"),  # regressed tick
    ("tick=43 index=3", "tick=43 index=2"),  # duplicate row id
    ("marker_id=action-session", "marker_id=foreign"),
    ("world=world", "world=foreign"),
    ("basal_ticks=44", "basal_ticks=43"),  # no basal progression
    ("from_x=2", "from_x=1.8"),  # teleport gap
    ("index=8", "index=9"),  # out of range
])
def test_missing_or_foreign_tick_never_grants_wait(before, after):
    original = fixture()
    assert before in original
    with pytest.raises(BoundaryRejected):
        check(original.replace(before, after, 1))


@pytest.mark.parametrize("bad", [
    "S50_DEV_WAIT_BEGIN ", "S50_DEV_WAIT_TICK ", "tick=48 index=8",
])
def test_missing_original_prevents_wait(bad):
    lines = fixture().splitlines()
    with pytest.raises(BoundaryRejected):
        check("\n".join(x for x in lines if bad not in x))


@pytest.mark.parametrize("field,replacement", [
    ("x=2 y=-60", "x=2.01 y=-60"),
    ("motion_packets=11", "motion_packets=12"),
    ("motion_blocks=1.7", "motion_blocks=1.8"),
    ("tick_meter_blocks=1.71", "tick_meter_blocks=1.8"),
    ("combat_events=0", "combat_events=1"),
    ("swing_events=0", "swing_events=1"),
    ("sprint=false", "sprint=true"),
    ("sneak=false", "sneak=true"),
    ("swimming=false", "swimming=true"),
])
def test_nonidle_tick_reported_but_not_recovered(field, replacement):
    lines = fixture().splitlines()
    lines[4] = lines[4].replace(field, replacement, 1)
    r = check("\n".join(lines))
    assert r["source_stationary_8_of_8"] is False
    assert 44 in r["source_activity_ticks"]
    assert r["p1_fatigue_recovered"] == 0.0
    assert r["wait_ticks_admitted"] == 0


@pytest.mark.parametrize("status", ["issued", "unknown", "aborted", ""])
def test_uncleared_or_unknown_action_cannot_be_wait(status):
    with pytest.raises(BoundaryRejected):
        check(fixture(), status=status)


def test_no_wait_window_in_qualified_old_jar():
    """Old frozen 2026-10-16 BASE_ON original cannot be retrofitted."""
    with pytest.raises(BoundaryRejected):
        check("M02_DEV_S50_PHASE marker_id=action-session phase=POST_CLEAR")
