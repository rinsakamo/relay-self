"""Node-local physicsTick control flags are not Paper time or WAIT authority."""
from __future__ import annotations

import copy
import json

import pytest

from adapters.mineflayer.s49_node_physics_postclear_dev import (
    NativePhysicsTraceRejected,
    audit_node_physics_postclear_dev,
)
from test_s49_paper_action_bracket_dev import ACTION, SESSION


def fixture():
    rows = []
    for i in range(0, 14):
        rows.append({
            "phase": "SET" if i == 0 else "ACTIVE",
            "index": i, "monotonic_ms": 900 + i * 50,
            "forward": True, "sprint": True,
            "back": False, "left": False, "right": False,
            "x": 1.0, "z": float(i) * .15, "vx": 0.0, "vz": .10,
            "client_time_of_day_cached": 248,
        })
    rows.append({
        "phase": "CLEAR", "index": 13, "monotonic_ms": 1560,
        "forward": False, "sprint": False,
        "back": False, "left": False, "right": False,
        "x": 1.0, "z": 2.0, "vx": 0.0, "vz": .09,
        "client_time_of_day_cached": 248,
    })
    for i, step in enumerate([.08, .04, .02, .01, 0], 1):
        rows.append({
            "phase": "POST_CLEAR", "index": 13 + i,
            "monotonic_ms": 1560 + 50 * i,
            "forward": False, "sprint": False,
            "back": False, "left": False, "right": False,
            "x": 1.0, "z": 2 + sum([.08, .04, .02, .01, 0][:i]),
            "vx": 0, "vz": step,
            "client_time_of_day_cached": 248,
        })
    raw = {
        "version": "S49_NODE_PHYSICS_POST_CLEAR_DEV_V1",
        "action_id": ACTION, "session_id": SESSION,
        "clear_seen": True, "complete": True,
        "source_attested": False, "post_clear_ticks": 5, "rows": rows,
    }
    paper = {
        "action_id": ACTION, "session_id": SESSION,
        "paper_callbacks": 5, "post_release_positive_translation_ticks": 3,
        "WAIT_sourcebound_admitted": False, "M0_posted": False,
        "P1_posted": False,
    }
    return raw, paper


def audit(tmp_path, raw, paper):
    path = tmp_path / "trace.json"
    path.write_text(json.dumps(raw), encoding="utf-8")
    return audit_node_physics_postclear_dev(
        path, session_id=SESSION, action_id=ACTION,
        paper_post_release=paper,
    )


def test_node_after_clear_control_true_false_and_no_world_clock_claim(tmp_path):
    raw, paper = fixture()
    a = audit(tmp_path, raw, paper)
    assert a["node_active_physics_ticks"] == 13
    assert a["node_postclear_physics_ticks"] == 5
    assert a["node_postclear_forward_sprint_all_false"] is True
    assert a["node_postclear_translation_ticks"] == 4
    assert a["paper_postrelease_positive_translation_ticks"] == 3
    assert a["node_paper_tick_join_attested"] is False
    assert a["WAIT_sourcebound_admitted"] is False
    assert a["M0_posted"] is False and a["P1_posted"] is False


@pytest.mark.parametrize("fault", [
    "foreign_action", "foreign_session", "replay_physics", "missing_physics",
    "overlong", "forged_clear_state", "forged_active_state",
    "last_control_on", "negative_index", "rollback_clock",
    "nonfinite_x", "teleport", "bad_version", "fake_qual",
    "missing_clear", "duplicate_clear", "short_post", "bad_index",
    "paper_wait", "paper_foreign", "post_not_complete",
])
def test_invalid_node_local_physics_trace_denied(tmp_path, fault):
    raw, paper = fixture()
    r = raw["rows"]
    if fault == "foreign_action":
        raw["action_id"] = "alien"
    elif fault == "foreign_session":
        raw["session_id"] = "alien"
    elif fault == "replay_physics":
        r.insert(3, copy.deepcopy(r[2]))
    elif fault == "missing_physics":
        r.pop(5)
    elif fault == "overlong":
        r[3:3] = [copy.deepcopy(r[2]) for _ in range(100)]
    elif fault == "forged_clear_state":
        r[14]["forward"] = True
    elif fault == "forged_active_state":
        r[3]["forward"] = False
    elif fault == "last_control_on":
        r[-1]["sprint"] = True
    elif fault == "negative_index":
        r[6]["index"] = -1
    elif fault == "rollback_clock":
        r[8]["monotonic_ms"] = 0
    elif fault == "nonfinite_x":
        r[-1]["x"] = float("nan")
    elif fault == "teleport":
        r[16]["z"] = 900
    elif fault == "bad_version":
        raw["version"] = "QUALIFIED"
    elif fault == "fake_qual":
        raw["source_attested"] = True
    elif fault == "missing_clear":
        r.pop(14)
    elif fault == "duplicate_clear":
        r.insert(15, copy.deepcopy(r[14]))
    elif fault == "short_post":
        r.pop()
    elif fault == "bad_index":
        r[16]["index"] = 200
    elif fault == "paper_wait":
        paper["WAIT_sourcebound_admitted"] = True
    elif fault == "paper_foreign":
        paper["session_id"] = "alien"
    else:
        raw["complete"] = False
    with pytest.raises(NativePhysicsTraceRejected):
        audit(tmp_path, raw, paper)
