"""S50 in-session Paper-only eight-tick witness, not complete Node source."""
from __future__ import annotations

from dataclasses import FrozenInstanceError

import pytest

from adapters.mineflayer.m02_paper_dev.s50_live_paper_window import (
    S50LivePaperWindowRejected,
    capture_s50_live_paper_window,
    verify_s50_live_window_against_final_paper,
)
from test_s50_selfbody_motion_source import ACTION, MARKER, SID, UUID, WORLD, paper


def captured() -> bytes:
    phases = (
        f"[INFO] M02_DEV_S50_PHASE marker_id={MARKER} world={WORLD} "
        "phase=PRE_FORWARD world_full_time=248\n"
        f"[INFO] M02_DEV_S50_PHASE marker_id={MARKER} world={WORLD} "
        "phase=POST_CLEAR world_full_time=249\n"
        f"[INFO] S50_DEV_WAIT_BEGIN marker_id={MARKER} world={WORLD} "
        "tick=250 x=-0.5 y=-60 z=1.7070768816725144\n"
    )
    return phases.encode() + paper()


def capture(raw=None):
    return capture_s50_live_paper_window(
        captured() if raw is None else raw,
        session_id=SID, action_id=ACTION, world=WORLD, subject_uuid=UUID,
    )


def test_live_paper_source_is_bounded_provisional_and_final_auditable():
    raw = captured()
    window = capture(raw)
    assert window.marker_id == MARKER
    assert window.paper_world_uuid == WORLD
    assert window.paper_prefix_bytes == len(raw)
    assert len(window.ticks) == 8
    assert tuple(t.world_tick for t in window.ticks) == tuple(range(251, 259))
    assert window.prior_motion_summary()["motion_with_last_reported_input_off_ticks"] == (
        251, 252,
    )
    assert window.input_event_count_at_window_end == 0
    assert window.provisional
    assert not window.final_source_verified
    assert not window.node_trace_complete
    assert not window.client_packet_writes_attested
    assert not window.full_tick_input_idle
    assert not window.physical_stability_attested
    assert not window.goal_admitted
    assert window.p1_wait_granted == 0
    with pytest.raises(FrozenInstanceError):
        window.provisional = False
    assert verify_s50_live_window_against_final_paper(
        window, raw + b"[INFO] Paper World ending normally\n",
    )


@pytest.mark.parametrize("fault", [
    "not_bytes", "no_newline", "too_long", "missing_first_tick",
    "missing_second_phase", "missing_wait", "foreign_world",
    "foreign_subject", "input_gap", "discontinuous", "nan_pose",
    "duplicate_tick", "extra_sample", "negative_tick",
])
def test_bad_in_session_prefix_not_qualified(fault):
    raw = captured()
    if fault == "not_bytes":
        raw = "not bytes"
    elif fault == "no_newline":
        raw = raw[:-1]
    elif fault == "too_long":
        raw += b"x" * 2_000_000
    elif fault == "missing_first_tick":
        raw = raw.replace(b"tick=250 x=-0.5", b"tick=NONE x=-0.5")
    elif fault == "missing_second_phase":
        raw = b"\n".join(line for line in raw.splitlines()
            if b"phase=POST_CLEAR" not in line) + b"\n"
    elif fault == "missing_wait":
        raw = b"\n".join(line for line in raw.splitlines()
            if b"S50_DEV_WAIT_TICK " not in line or b"index=5" not in line) + b"\n"
    elif fault == "foreign_world":
        raw = raw.replace(WORLD.encode(), b"foreign-world", 1)
    elif fault == "foreign_subject":
        raw = raw.replace(UUID.encode(), b"foreign-player", 1)
    elif fault == "input_gap":
        raw = b"\n".join(line for line in raw.splitlines()
            if b"S50_DEV_INPUT_TICK " not in line or b"index=5" not in line) + b"\n"
    elif fault == "discontinuous":
        raw = raw.replace(b"from_z=1.6480410884503386", b"from_z=99", 1)
        # Some float renderings may differ: replace at the stable second row.
        if raw == captured():
            raw = raw.replace(b"from_x=-0.5", b"from_x=99", 1)
    elif fault == "nan_pose":
        raw = raw.replace(b"from_x=-0.5", b"from_x=NaN", 1)
    elif fault == "duplicate_tick":
        raw = raw.replace(b"tick=254 index=4", b"tick=253 index=4", 1)
    elif fault == "extra_sample":
        raw += paper().splitlines()[0] + b"\n"
    elif fault == "negative_tick":
        raw = raw.replace(b"tick=251 index=1", b"tick=-1 index=1", 1)
    with pytest.raises((S50LivePaperWindowRejected, ValueError)):
        capture(raw)


def test_final_paper_mutation_or_truncation_fails_closed():
    raw = captured()
    window = capture(raw)
    for final in (
        raw[:-1],
        b"prefix\n" + raw,
        raw.replace(b"tick=251", b"tick=260", 1),
        raw + b"extra" * 4_000_000,
    ):
        with pytest.raises(S50LivePaperWindowRejected):
            verify_s50_live_window_against_final_paper(window, final)
