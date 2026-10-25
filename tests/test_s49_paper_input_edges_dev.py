"""Paper PlayerInputEvent clock is separate from Node time & physicsTick."""
from __future__ import annotations

import asyncio
import hashlib

import pytest

from adapters.mineflayer.m02_paper_dev.s50_boundary import BoundaryRejected
from adapters.mineflayer.s49_motor_clock_review_dev import review_native_motor_clock_dev
from adapters.mineflayer.s49_paper_input_edges_dev import review_paper_input_edges_dev
from adapters.mineflayer.s49_paper_world_first_dev import CONFIRM, run
from test_s49_motor_clock_dev import _trial_data


def _source(tmp_path):
    native, paper, original, feedback, _ = _trial_data(tmp_path)
    clock = review_native_motor_clock_dev(native, paper, original, feedback)
    aid, sid = original["actual_native_actions"][1]["action"], original["session_id"]
    marker = f"marker_id={aid}-{sid} action_id={aid} session_id={sid} world=world run_id=run"
    header = f"S49_OBSERVER_PRE_ARM {marker} tick=440 input_idle=true"
    on = f"S49_OBSERVER_BACK_TRUE {marker} tick=444 back=true x=0.0 z=0.0"
    off = f"S49_OBSERVER_BACK_FALSE {marker} tick=448 back=false x=0.6 z=0.0"
    paper.write_text("\n".join([header, on, off, paper.read_text()]))
    return paper, original, clock


def test_paper_server_edges_match_original_second_closed_action(tmp_path):
    paper, source, clock = _source(tmp_path)
    result = review_paper_input_edges_dev(paper, source, clock)
    assert result["status"] == "DEV_PAPER_SERVER_INPUT_EDGE_TICKS_OBSERVED"
    assert result["paper_arm_tick"] == 440
    assert result["paper_server_back_on_event_tick"] == 444
    assert result["paper_server_back_off_event_tick"] == 448
    assert result["paper_observed_input_edge_tick_span"] == 4
    assert result["paper_server_position_displacement_between_edge_events_m"] == .6
    assert result["post_release_consecutive_world_wait_ticks"] == 8
    assert result["source_action_id"] == source["actual_native_actions"][1]["action"]
    assert result["paper_full_effective_movement_ticks_attested"] is False
    assert result["cross_process_clock_alignment_attested"] is False
    assert result["new_paper_command_effect"] is False


@pytest.mark.parametrize("tamper", [
    "missing_arm", "no_off", "wrong_world", "wrong_session",
    "same_tick", "reversed", "wait_gap", "not_finite", "too_far",
])
def test_paper_events_fail_closed_on_mismatch(tmp_path, tamper):
    paper, source, clock = _source(tmp_path)
    contents = paper.read_text()
    if tamper == "missing_arm":
        contents = "\n".join(contents.splitlines()[1:])
    elif tamper == "no_off":
        contents = "\n".join(contents.splitlines()[:2] + contents.splitlines()[3:])
    elif tamper == "wrong_world":
        contents = contents.replace("world=world", "world=other", 1)
    elif tamper == "wrong_session":
        contents = contents.replace("session_id=test-session", "session_id=other", 1)
    elif tamper == "same_tick":
        contents = contents.replace("tick=448 back=false", "tick=444 back=false")
    elif tamper == "reversed":
        contents = contents.replace("tick=444 back=true", "tick=449 back=true")
    elif tamper == "wait_gap":
        contents = contents.replace("tick=451 index=1", "tick=452 index=1")
    elif tamper == "not_finite":
        contents = contents.replace("x=0.6", "x=NaN")
    elif tamper == "too_far":
        contents = contents.replace("x=0.6", "x=100.0")
    paper.write_text(contents)
    with pytest.raises(BoundaryRejected):
        review_paper_input_edges_dev(paper, source, clock)


def test_preobserver_requires_full_existing_dev_gate(tmp_path):
    paper, observer = tmp_path / "paper.jar", tmp_path / "observer.jar"
    paper.write_bytes(b"fixture")
    observer.write_bytes(b"fixture")
    result = asyncio.run(run(
        tmp_path / "not-created",
        paper, hashlib.sha256(paper.read_bytes()).hexdigest(),
        observer, hashlib.sha256(observer.read_bytes()).hexdigest(),
        confirmation=CONFIRM, paper_input_edges_dev=True,
    ))
    assert result == 2
    assert not (tmp_path / "not-created").exists()
