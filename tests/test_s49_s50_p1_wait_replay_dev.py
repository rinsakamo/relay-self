"""Focused DEV P1 replay: real-world claims remain disabled for fixtures."""
from __future__ import annotations

import pytest

from adapters.mineflayer.m02_paper_dev.s50_boundary import BoundaryRejected
from adapters.mineflayer.s49_s50_p1_wait_replay_dev import replay_wait_fatigue_dev
from experiments.fatigue_p1 import FatigueProfile, initial_state
from test_s49_paper_preaction_dev import pre_transcript
from test_s49_paper_transcript_dev import PLAYER, typed_owner


def setup_replay(monkeypatch, *, initial=0.5):
    capture = typed_owner(monkeypatch)
    profile = FatigueProfile(enabled=True, initial=initial)
    state = initial_state(profile, capture.projection.session_id, world_tick=70)
    paper = pre_transcript(capture)
    return capture, profile, state, paper


def evaluate(capture, profile, state, paper):
    return replay_wait_fatigue_dev(
        capture, paper, expected_player_uuid=PLAYER,
        profile=profile, state_before_wait=state,
    )


def test_s49_original_clear_paper_idle_to_existing_p1_model(monkeypatch):
    capture, profile, state, paper = setup_replay(monkeypatch)
    report = evaluate(capture, profile, state, paper)
    assert report["status"] == "OFFLINE_WAIT_MODEL_REPLAY"
    assert report["dev_wait_tick_count"] == 8
    assert [row["world_tick"] for row in report["dev_wait_ticks"]] == list(range(71, 79))
    assert report["excluded_release_boundary_tick"] == 70
    assert report["dev_fatigue_before"] == 0.5
    assert report["dev_fatigue_after"] == pytest.approx(0.0)
    assert report["dev_fatigue_recovered"] == pytest.approx(0.5)
    assert report["dev_fatigue_recovery_positive"]
    assert report["source_bound_tick"] is None
    assert report["wait_interval_ref"] is None
    assert report["wait_ticks_admitted"] == 0
    assert report["p1_fatigue_recovered"] == 0.0
    assert not report["world_run_verified"]
    assert not report["p1_world_state_updated"]
    assert not report["qualification_go"]
    assert not report["science_go"]
    assert capture._executor.wait_phase == "NEW"


def test_zero_fatigue_still_idle_but_no_recovery(monkeypatch):
    capture, profile, state, paper = setup_replay(monkeypatch, initial=0.0)
    report = evaluate(capture, profile, state, paper)
    assert report["dev_wait_tick_count"] == 8
    assert report["dev_fatigue_recovered"] == 0.0
    assert not report["dev_fatigue_recovery_positive"]


@pytest.mark.parametrize("mutation", [
    "active_input", "self_movement", "missing_tick", "foreign_session",
    "missing_back_off", "stale_action", "wrong_action", "replayed_log",
    "reported_abort",
])
def test_unsafe_paper_or_s16_does_not_recover(monkeypatch, mutation):
    capture, profile, state, paper = setup_replay(monkeypatch)
    if mutation == "active_input":
        paper = "".join(line.replace("input_idle=true", "input_idle=false")
                        if "index=4 " in line else line
                        for line in paper.splitlines(keepends=True))
    elif mutation == "self_movement":
        paper += "S49_DEV_BACK_WAIT_ABORT reason=SELF_MOVEMENT_EVENT_DURING_OBSERVATION\n"
    elif mutation == "missing_tick":
        paper = "".join(line for line in paper.splitlines(keepends=True)
                        if "index=5 " not in line)
    elif mutation == "foreign_session":
        paper = paper.replace("session_id=" + capture.projection.session_id,
                              "session_id=foreign", 1)
    elif mutation == "missing_back_off":
        paper = "".join(line for line in paper.splitlines(keepends=True)
                        if "S49_OBSERVER_BACK_FALSE" not in line)
    elif mutation == "stale_action":
        capture._state = "FAILED"
    elif mutation == "wrong_action":
        capture.projection.decoded_evidence["action_ref"] = "MOVE_FORWARD"
    elif mutation == "replayed_log":
        paper += paper
    else:
        paper += "S49_DEV_BACK_WAIT_ABORT reason=SERVER_INPUT_RESUMED\n"
    with pytest.raises(BoundaryRejected):
        evaluate(capture, profile, state, paper)


@pytest.mark.parametrize("kind", [
    "wrong_session", "wrong_tick", "disabled_profile", "wrong_profile",
])
def test_p1_state_not_silently_aligned(monkeypatch, kind):
    capture, profile, state, paper = setup_replay(monkeypatch)
    if kind == "wrong_session":
        state = initial_state(profile, "different-session", world_tick=70)
    elif kind == "wrong_tick":
        state = initial_state(profile, capture.projection.session_id, world_tick=69)
    elif kind == "disabled_profile":
        profile = FatigueProfile()
        state = initial_state(profile, capture.projection.session_id, world_tick=70)
    else:
        profile = FatigueProfile(enabled=True, initial=0.3)
    with pytest.raises(BoundaryRejected):
        evaluate(capture, profile, state, paper)
