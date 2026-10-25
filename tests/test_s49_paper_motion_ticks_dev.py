"""Source-specific Paper movement ticks do not pretend to attest BACK input."""
from __future__ import annotations

import asyncio
import hashlib

import pytest

from adapters.mineflayer.m02_paper_dev.s50_boundary import BoundaryRejected
from adapters.mineflayer.s49_motor_clock_review_dev import review_native_motor_clock_dev
from adapters.mineflayer.s49_paper_motion_ticks_dev import review_paper_motion_ticks_dev
from adapters.mineflayer.s49_paper_world_first_dev import CONFIRM, run
from test_s49_motor_clock_dev import _trial_data


def _sample(tmp_path):
    node, paper, original, feedback, _ = _trial_data(tmp_path)
    clock = review_native_motor_clock_dev(node, paper, original, feedback)
    aid = original["actual_native_actions"][1]["action"]
    sid = original["session_id"]
    header = (
        f"S49_MOTION_SERVER_ARM action_id={aid} session_id={sid} "
        "player_uuid=test-uuid world=world tick=440 authority=NONE "
        "input_edge_attested=false"
    )
    frames = [
        f"S49_MOTION_SERVER_POSITION action_id={aid} session_id={sid} world=world "
        f"tick={tick} index={i} from_x={x} from_z=0.0 to_x={x+.1} "
        "to_z=0.0 input_edge_attested=false"
        for i, (tick, x) in enumerate(
            [(441, 0.0), (442, 0.1), (443, 0.2), (444, 0.3)], 1,
        )
    ]
    end = (
        f"S49_MOTION_SERVER_COMPLETE action_id={aid} session_id={sid} "
        "player_uuid=test-uuid world=world movement_events=4 "
        "distinct_position_change_ticks=4 authority=NONE "
        "input_edge_attested=false"
    )
    paper.write_text("\n".join([header, *frames, end, paper.read_text()]))
    return paper, original, clock


def test_independent_server_movement_events_not_server_control_edges(tmp_path):
    paper, original, clock = _sample(tmp_path)
    actual = review_paper_motion_ticks_dev(paper, original, clock)
    assert actual["status"] == "DEV_PAPER_SERVER_POSITION_EVENT_TICKS_OBSERVED"
    assert actual["action_id"] == original["actual_native_actions"][1]["action"]
    assert actual["paper_distinct_position_change_ticks"] == 4
    assert actual["paper_position_change_event_count"] == 4
    assert actual["paper_edge_to_edge_displacement_m"] == pytest.approx(0.4)
    assert actual["paper_player_input_back_on_observed"] is False
    assert actual["paper_player_input_back_off_observed"] is False
    assert actual["server_input_effective_tick_count_attested"] is False
    assert actual["cross_process_clock_alignment_attested"] is False
    assert actual["qualification_go"] is False


@pytest.mark.parametrize("bad", [
    "foreign", "missing_arm", "wrong_count", "wrong_world", "bad_tick",
    "nan_position", "server_authority",
])
def test_server_position_source_rejects_invalid_trace(tmp_path, bad):
    paper, original, clock = _sample(tmp_path)
    s = paper.read_text()
    if bad == "foreign":
        s = s.replace("session_id=test-session", "session_id=other", 1)
    elif bad == "missing_arm":
        s = "\n".join(s.splitlines()[1:])
    elif bad == "wrong_count":
        s = s.replace("movement_events=4", "movement_events=5")
    elif bad == "wrong_world":
        s = s.replace("world=world", "world=other", 1)
    elif bad == "bad_tick":
        s = s.replace("tick=444 index=4", "tick=441 index=4")
    elif bad == "nan_position":
        s = s.replace("to_x=0.4", "to_x=NaN")
    else:
        s += "\nS49_MOTION_SERVER_DENIED invalid_source\n"
    paper.write_text(s)
    with pytest.raises(BoundaryRejected):
        review_paper_motion_ticks_dev(paper, original, clock)


def test_motion_observation_needs_native_clock_and_selfbody(tmp_path):
    p, o = tmp_path / "paper.jar", tmp_path / "observer.jar"
    p.write_bytes(b"f")
    o.write_bytes(b"o")
    out = tmp_path / "not-created"
    assert asyncio.run(run(
        out, p, hashlib.sha256(p.read_bytes()).hexdigest(),
        o, hashlib.sha256(o.read_bytes()).hexdigest(),
        confirmation=CONFIRM, paper_motion_ticks_dev=True,
    )) == 2
    assert not out.exists()
