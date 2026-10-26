"""S49 native input-off and Paper stillness candidate: no false physical WAIT."""
from __future__ import annotations

import json
from copy import deepcopy

import pytest

from adapters.mineflayer.s49_inter_action_stillness_dev import (
    InterActionStillnessRejected,
    review_inter_action_stillness_dev,
)
from adapters.mineflayer.s49_two_action_world_timeline_dev import (
    review_two_action_world_timeline_dev,
)
from test_s49_two_action_world_timeline_dev import source


def fixture(tmp_path):
    args = source()
    first = args["action_id"]
    second = args["original_actions"][1]["action"]
    sid = args["session_id"]
    log = []
    x = 0.0
    for tick in range(101, 318):
        step = (.15 if tick <= 113 else
                .015 if tick <= 121 else
                0.0 if tick <= 289 else
                .01 if tick <= 300 else
                .12 if tick <= 312 else .025)
        x += step
        fields = dict(
            action_id=first, session_id=sid,
            world="world-s49", player_uuid="player-s49",
            tick=tick, index=tick - 100,
            second_applied_marker_seen=str(tick > 300).lower(),
            second_cleared_marker_seen=str(tick > 312).lower(),
            first_dash_modifier_present=str(tick < 114).lower(),
            x=round(x, 8), z=0.0,
            motor_write="false", M0_POSTED="false",
            P1_APPLIED="false", WAIT_ATTESTED="false",
        )
        log.append("S49_DASH_DEV_TRAIL_TICK " + " ".join(
            f"{key}={val}" for key, val in fields.items()
        ))
    for phase, seq, tick in (("APPLIED", 60, 300), ("CLEARED", 72, 312)):
        log.append("S49_DASH_DEV_TRAIL_EDGE " + " ".join(
            f"{key}={val}" for key, val in dict(
                action_id=second, session_id=sid,
                world="world-s49", player_uuid="player-s49",
                tick=tick, phase=phase, native_seq=seq,
                delivered_after_original_native_ack="true",
                exact_client_effect_tick_attested="false",
            ).items()
        ))
    log.append("S49_DASH_DEV_TRAIL_COMPLETE " + " ".join(
        f"{key}={val}" for key, val in dict(
            action_id=first, session_id=sid, second_action_id=second,
            world="world-s49", player_uuid="player-s49",
            tick=317, samples=217,
            reason="SECOND_NATIVE_ACK_MARKER_PLUS_FIVE",
            motor_write="false", M0_POSTED="false",
            P1_APPLIED="false", WAIT_ATTESTED="false",
        ).items()
    ))
    raw = "\n".join(log)
    args["raw"] = raw
    timeline = review_two_action_world_timeline_dev(**args)
    controls = dict.fromkeys(("forward", "sprint", "back", "left",
                              "right", "jump", "sneak"), False)
    node = {
        "version": "S49_NODE_INTER_ACTION_INPUT_OFF_DEV_V1",
        "session_id": sid,
        "first_action_id": first,
        "first_cleanup_action_id": first + "-s15-clear",
        "second_action_id": second,
        "source_attested": False,
        "clock_synchronized": False,
        "complete": True,
        "overflow": False,
        "start_controls": controls.copy(),
        "before_second_set_controls": controls.copy(),
        "rows": [{
            "ordinal": i,
            "monotonic_ms": 1000 + i * 50,
            "controls": controls.copy(),
            "x": 0.5, "z": 2.0,
        } for i in range(1, 155)],
    }
    path = tmp_path / "node_controls.json"
    path.write_text(json.dumps(node), encoding="utf-8")
    return raw, path, timeline, node, first, second, sid


def read(raw, path, timeline, first, second, sid):
    return review_inter_action_stillness_dev(
        raw, path, timeline=timeline,
        first_action_id=first, second_action_id=second,
        session_id=sid,
    )


def test_long_stillness_node_controls_off_but_not_wait(tmp_path):
    raw, path, timeline, node, first, second, sid = fixture(tmp_path)
    before = deepcopy(timeline)
    result = read(raw, path, timeline, first, second, sid)
    assert result["classification"] == "S49_INTER_ACTION_STILLNESS_CANDIDATE_DEV_ONLY", (result["paper_candidate_search_interval"], result["paper_max_low_motion_run_ticks"])
    assert result["paper_consecutive_low_motion_ticks"] >= 80
    assert result["node_physics_samples"] == 154
    assert result["node_all_controls_off_until_second_set"] is True
    assert result["node_paper_tick_join_attested"] is False
    assert result["second_native_effect_tick_attested"] is False
    assert result["physical_WAIT_admitted"] is False
    assert result["P1_recovery_posted"] is False
    assert result["M0_posted"] is False
    assert timeline == before
    assert node["complete"] is True


def test_no_long_stillness_returns_absent_not_fabricated_wait(tmp_path):
    raw, path, timeline, _, first, second, sid = fixture(tmp_path)
    lines = raw.splitlines()
    for index in range(13, 199):
        # No more than one low-motion tick after the first Action.
        line = lines[index]
        delta = 0.03 * (index - 13)
        lines[index] = " ".join(
            f"x={delta:.6f}" if part.startswith("x=") else part
            for part in line.split()
        )
    result = read("\n".join(lines), path, timeline, first, second, sid)
    assert result["classification"] == "S49_INTER_ACTION_STILLNESS_CANDIDATE_ABSENT_DEV_ONLY"
    assert result["physical_WAIT_admitted"] is False


@pytest.mark.parametrize("fault", [
    "bad_first_id", "bad_cleanup_id", "bad_second_id", "bad_session",
    "forged_attested", "forged_sync", "incomplete", "overflow",
    "active_first_controls", "active_last_controls", "active_middle_controls",
    "control_flag_missing", "skipped_node_tick", "node_clock_rollback",
    "nan_position", "short_node_trace", "duplicate_paper_tick",
    "missing_paper_tick", "foreign_paper_session", "foreign_paper_actor",
    "forged_paper_M0", "forged_paper_WAIT", "forged_paper_modifier",
    "fake_timeline_wait", "fake_gap", "fake_owner", "invalid_threshold",
])
def test_untrusted_input_or_missing_provenance_never_admits_stillness(tmp_path, fault):
    raw, path, timeline, node, first, second, sid = fixture(tmp_path)
    if fault == "bad_first_id":
        node["first_action_id"] = "foreign"
    elif fault == "bad_cleanup_id":
        node["first_cleanup_action_id"] = "foreign"
    elif fault == "bad_second_id":
        node["second_action_id"] = "foreign"
    elif fault == "bad_session":
        node["session_id"] = "foreign"
    elif fault == "forged_attested":
        node["source_attested"] = True
    elif fault == "forged_sync":
        node["clock_synchronized"] = True
    elif fault == "incomplete":
        node["complete"] = False
    elif fault == "overflow":
        node["overflow"] = True
    elif fault == "active_first_controls":
        node["start_controls"]["forward"] = True
    elif fault == "active_last_controls":
        node["before_second_set_controls"]["sprint"] = True
    elif fault == "active_middle_controls":
        node["rows"][12]["controls"]["jump"] = True
    elif fault == "control_flag_missing":
        del node["rows"][12]["controls"]["sneak"]
    elif fault == "skipped_node_tick":
        node["rows"][12]["ordinal"] += 1
    elif fault == "node_clock_rollback":
        node["rows"][12]["monotonic_ms"] = 0
    elif fault == "nan_position":
        node["rows"][12]["x"] = float("nan")
    elif fault == "short_node_trace":
        node["rows"] = node["rows"][:4]
    else:
        lines = raw.splitlines()
        if fault == "duplicate_paper_tick":
            lines.insert(30, lines[30])
        elif fault == "missing_paper_tick":
            lines.pop(30)
        elif fault == "foreign_paper_session":
            lines[30] = lines[30].replace("session_id=native-session-dev", "session_id=wrong")
        elif fault == "foreign_paper_actor":
            lines[30] = lines[30].replace("player_uuid=player-s49", "player_uuid=wrong")
        elif fault == "forged_paper_M0":
            lines[30] = lines[30].replace("M0_POSTED=false", "M0_POSTED=true")
        elif fault == "forged_paper_WAIT":
            lines[30] = lines[30].replace("WAIT_ATTESTED=false", "WAIT_ATTESTED=true")
        elif fault == "forged_paper_modifier":
            lines[30] = lines[30].replace(
                "first_dash_modifier_present=false",
                "first_dash_modifier_present=true",
            )
        elif fault == "fake_timeline_wait":
            timeline["WAIT_sourcebound_admitted"] = True
        elif fault == "fake_gap":
            timeline["tick_gaps_or_replay"] = True
        elif fault == "fake_owner":
            timeline["action_ids"][0] = "foreign"
        elif fault == "invalid_threshold":
            pass
        raw = "\n".join(lines)
    path.write_text(json.dumps(node), encoding="utf-8")
    with pytest.raises(InterActionStillnessRejected):
        review_inter_action_stillness_dev(
            raw, path, timeline=timeline,
            first_action_id=first, second_action_id=second, session_id=sid,
            min_still_ticks=1 if fault == "invalid_threshold" else 8,
        )
