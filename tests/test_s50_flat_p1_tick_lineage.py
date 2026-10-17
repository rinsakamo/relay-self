"""FLAT native movement tick lineage: gaps never become free P1 WAIT."""
from __future__ import annotations

from dataclasses import dataclass
from types import SimpleNamespace

import pytest

from adapters.mineflayer.m02_paper_dev import s50_flat_p1_tick_lineage as subject
from adapters.mineflayer.m02_paper_dev.s50_boundary import BoundaryRejected
from adapters.mineflayer.m02_paper_dev.s50_flat_p1_pure_preview import (
    replay_p1_motion_only_preview,
)
from test_s50_flat_p1_motion import source
from adapters.mineflayer.m02_paper_dev.s50_flat_p1_motion import screen_motion


def fixture(arm="SHAM_ON"):
    console, report = source(arm)
    return screen_motion(console, report, arm=arm)


def test_lineage_preserves_unknown_ticks_and_positive_distance():
    ledger = subject.movement_tick_ledger(fixture())
    assert ledger["start_full_time"] == 16
    assert ledger["terminal_full_time"] == 100
    assert ledger["move_observed_ticks"] == 2
    assert ledger["unclassified_ticks"] == 82
    assert len(ledger["ticks"]) == 84
    assert ledger["ticks"][0]["activity"] == "UNKNOWN_NOT_WAIT"
    assert ledger["ticks"][3]["world_full_time"] == 20
    assert ledger["ticks"][3]["activity"].startswith("MOVE_EVENT")
    assert ledger["SourceBoundTick_WAIT_issued"] == 0
    assert ledger["P1_wait_recovery"] == 0.0
    assert not ledger["P1_state_advanced"]
    windows = subject.contiguous_motion_windows(ledger)
    assert len(windows) == 1
    assert windows[0]["consecutive_positive_motion_ticks"] == 2
    assert windows[0]["first_world_tick"] == 20
    assert windows[0]["last_world_tick"] == 21
    assert windows[0]["cross_unknown_gap_state_continuation_allowed"] is False


@pytest.mark.parametrize("arm", [
    "BASE_ON", "SHAM_ON", "BASAL_ZERO", "WALK_ZERO", "BOTH_ZERO",
])
def test_all_m02_arms_never_issue_body_recovery(arm):
    ledger = subject.movement_tick_ledger(fixture(arm))
    assert ledger["unclassified_ticks"] == 82
    assert ledger["P1_hypothetical_total_move_gain_unadmitted"] > 0
    assert ledger["SourceBoundTick_MOVE_issued"] == 0
    assert ledger["SourceBoundTick_WAIT_issued"] == 0


@pytest.mark.parametrize("mutation", [
    lambda r: r.update(flat_world_seed=62101),
    lambda r: r.update(P1_state_advanced=True),
    lambda r: r.update(p1_fatigue_recovered=0.1),
    lambda r: r.update(R_independent_review="PASS"),
    lambda r: r.update(start_full_time=21),
    lambda r: r.update(terminal_full_time=2600),
    lambda r: r.update(native_moving_tick_count=4),
    lambda r: r.update(native_motion_events=3),
    lambda r: r.update(native_observed_horizontal_blocks=200),
    lambda r: r["tick_event_groups"][0].update(world_full_time=16),
    lambda r: r["tick_event_groups"][1].update(world_full_time=20),
    lambda r: r["tick_event_groups"][1].update(event_blocks=-0.1),
    lambda r: r["tick_event_groups"][0].update(event_count=0),
])
def test_tampered_move_ledger_source_fails_closed(mutation):
    r = fixture()
    mutation(r)
    with pytest.raises(BoundaryRejected):
        subject.movement_tick_ledger(r)


@pytest.mark.parametrize("corrupt", [
    lambda x: x["ticks"][0].update(activity="WAIT"),
    lambda x: x["ticks"][0].update(P1_frame_issued=True),
    lambda x: x["ticks"][0].update(native_horizontal_blocks=0.0),
    lambda x: x["ticks"][0].update(event_count=1),
    lambda x: x["ticks"][3].update(P1_hypothetical_gain_not_admitted=0.0),
    lambda x: x["ticks"][3].update(world_full_time=18),
    lambda x: x.update(P1_wait_recovery=0.1),
    lambda x: x.update(R_independent_source_admission="PASS"),
])
def test_no_stolen_wait_or_fabricated_body_frame(corrupt):
    ledger = subject.movement_tick_ledger(fixture())
    corrupt(ledger)
    with pytest.raises(BoundaryRejected):
        subject.contiguous_motion_windows(ledger)


@dataclass(frozen=True)
class SpyState:
    session_id: str
    profile_sha256: str
    world_tick: int
    fatigue: float


class SpyP1:
    """Tests caller wiring only. Actual P1 runs in separately pinned checkout."""

    class FatigueProfile:
        def __init__(self, enabled):
            assert enabled
            self.sha256 = "test-profile-only"
            self.move_per_block = SimpleNamespace(value=0.04)
            self.wait_recovery_per_world_tick = SimpleNamespace(value=0.10)

    class FatigueFrame:
        def __init__(self, *, session_id, world_tick, activity, observed_blocks):
            self.session_id = session_id
            self.world_tick = world_tick
            self.activity = activity
            self.observed_blocks = observed_blocks

    @staticmethod
    def initial_state(profile, session, *, world_tick):
        return SpyState(session, profile.sha256, world_tick, 0.0)

    @staticmethod
    def capability(profile, state):
        return SimpleNamespace(max_move_blocks_per_world_tick=1.0)

    @staticmethod
    def advance(profile, state, frame):
        assert frame.world_tick == state.world_tick + 1
        after = SpyState(state.session_id, state.profile_sha256,
                         frame.world_tick, state.fatigue + frame.observed_blocks * .04)
        return SimpleNamespace(before=state, after=after, frame=frame,
                               recovered=0, accumulated=frame.observed_blocks * .04)


def test_preview_can_only_run_contiguous_positive_motion_without_wait():
    ledger = subject.movement_tick_ledger(fixture())
    result = replay_p1_motion_only_preview(ledger, p1=SpyP1)
    assert len(result["windows"]) == 1
    assert result["windows"][0]["candidate_ticks_replayed"] == 2
    assert result["windows"][0]["hypothetical_window_end_fatigue"] == pytest.approx(.028)
    assert not result["P1_authoritative_state_advanced"]
    assert result["P1_wait_recovery"] == 0.0
    assert result["R_new_original_review"] == "PENDING"


def test_unknown_tick_breaks_lineage_without_silent_recovery():
    report = fixture()
    report["tick_event_groups"][1]["world_full_time"] = 23
    ledger = subject.movement_tick_ledger(report)
    windows = subject.contiguous_motion_windows(ledger)
    assert len(windows) == 2
    result = replay_p1_motion_only_preview(ledger, p1=SpyP1)
    assert len(result["windows"]) == 2
    assert [x["candidate_ticks_replayed"] for x in result["windows"]] == [1, 1]
    assert all(x["lineage_reset_at_unknown_gap"] for x in result["windows"])
    assert result["P1_wait_recovery"] == 0


def test_source_above_p1_cap_is_recorded_not_clipped():
    report = fixture()
    report["tick_event_groups"] = [{
        "world_full_time": 20, "event_count": 2, "event_blocks": 1.3,
    }]
    report.update(native_moving_tick_count=1, native_motion_events=2,
                  native_observed_horizontal_blocks=1.3)
    ledger = subject.movement_tick_ledger(report)
    result = replay_p1_motion_only_preview(ledger, p1=SpyP1)
    assert result["cap_conflicts"] == 1
    assert result["windows"][0]["candidate_ticks_replayed"] == 0
    assert result["windows"][0]["conflict"]["observed_blocks"] == 1.3
    assert not result["P1_authoritative_state_advanced"]
