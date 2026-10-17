"""Native getControlState readbacks are client-local snapshots, not WAIT."""
from __future__ import annotations

import copy
import json

import pytest

from adapters.mineflayer.m02_paper_dev.s50_boundary import BoundaryRejected
from adapters.mineflayer.m02_paper_dev.s50_p1_native_controls import (
    CONTROLS,
    review_native_controls,
)

SESSION = "11111111-2222-4333-8444-555555555555"
ACTION = "m02-paper-walk-1"


def fixture():
    movement = {
        "source_session": SESSION, "action_id": ACTION,
        "forward_seq": 2, "clear_seq": 3, "source_after_seq": 4,
    }
    native = [
        {"session_id": SESSION, "seq": 0, "type": "adapter_started"},
        {"session_id": SESSION, "seq": 1, "type": "effect_result",
         "effect": "look", "action_id": ACTION + "-look", "result": "applied"},
        {"session_id": SESSION, "seq": 2, "type": "effect_result",
         "effect": "set_control", "action_id": ACTION, "result": "applied"},
        {"session_id": SESSION, "seq": 3, "type": "effect_result",
         "effect": "clear_controls", "action_id": ACTION + "-clear",
         "result": "applied"},
        {"session_id": SESSION, "seq": 4, "type": "observation",
         "kind": "probe", "request_id": ACTION + "-seek-after"},
        {"session_id": SESSION, "seq": 5, "type": "shutdown_ack"},
    ]

    def row(kind, seq=None, tick=0, held=False, aid=None):
        value = {
            "source": "S50_DEV_NATIVE_READBACK_V1",
            "ordinal": 0, "session_id": SESSION,
            "client_physics_tick": tick,
            "kind": kind,
        }
        if seq is not None:
            value["native_seq"] = seq
        if aid is not None:
            value["native_action_id"] = aid
        if kind != "SESSION_START":
            value["controls"] = {key: key == "forward" and held
                                 for key in CONTROLS}
        return value

    rows = [
        row("SESSION_START", 0),
        row("EFFECT_ACK", 1, aid=ACTION + "-look"),
        row("EFFECT_ACK", 2, held=True, aid=ACTION),
        row("PHYSICS_TICK", tick=1, held=True),
        row("EFFECT_ACK", 3, tick=1, aid=ACTION + "-clear"),
        row("PHYSICS_TICK", tick=2),
        row("PROBE", 4, tick=2, aid=ACTION + "-seek-after"),
        row("PHYSICS_TICK", tick=3),
        row("SHUTDOWN_ACK", 5, tick=3),
    ]
    for i, item in enumerate(rows, 1):
        item["ordinal"] = i
    return rows, native, movement


def review(f):
    rows, native, movement = f
    return review_native_controls(
        "\n".join(json.dumps(item) for item in rows),
        native, movement,
    )


def test_seven_direct_controls_read_after_ack_and_over_later_physics_ticks():
    out = review(fixture())
    assert out["controls"] == list(CONTROLS)
    assert out["clear_readback_all_false"]
    assert out["after_probe_readback_all_false"]
    assert out["post_clear_sample_count"] == 4
    assert out["client_clock"] == "MINEFLAYER_PHYSICS_TICK_NOT_PAPER_WORLD_TICK"
    assert out["paper_effective_input_release_tick"] == "NOT_ATTESTED"
    assert out["continuous_held_controls_absence"] == "NOT_ATTESTED"
    assert out["all_S15_S16_issuers_absent"] == "NOT_ATTESTED"
    assert out["wait_ticks_admitted"] == 0
    assert out["p1_fatigue_recovered"] == 0
    assert not out["science_go"]


@pytest.mark.parametrize("change", [
    "wrong_session", "missing_key", "non_boolean", "forward_false",
    "clear_forward_true", "clear_other_held", "after_probe_true",
    "post_clear_reactivated", "missing_sample", "wrong_source",
    "duplicate_seq", "lost_ack", "foreign_native", "missing_stop",
    "missing_start", "over_cap", "clock_regression", "native_ack_rejected",
    "native_probe_wrong_action", "original_action_mismatch",
    "bad_ordinal", "extra_ack", "missing_physics_tick",
])
def test_all_untrusted_native_readback_shapes_fail_closed(change):
    f = list(copy.deepcopy(fixture()))
    rows, native, movement = f
    if change == "wrong_session":
        rows[3]["session_id"] = "foreign"
    elif change == "missing_key":
        del rows[4]["controls"]["back"]
    elif change == "non_boolean":
        rows[4]["controls"]["forward"] = 0
    elif change == "forward_false":
        rows[2]["controls"]["forward"] = False
    elif change == "clear_forward_true":
        rows[4]["controls"]["forward"] = True
    elif change == "clear_other_held":
        rows[4]["controls"]["sneak"] = True
    elif change == "after_probe_true":
        rows[6]["controls"]["forward"] = True
    elif change == "post_clear_reactivated":
        rows[7]["controls"]["back"] = True
    elif change == "missing_sample":
        rows.pop(5)
    elif change == "wrong_source":
        rows[2]["source"] = "fake"
    elif change == "duplicate_seq":
        rows[6]["native_seq"] = 3
    elif change == "lost_ack":
        rows.pop(4)
    elif change == "foreign_native":
        native[3]["session_id"] = "foreign"
    elif change == "missing_stop":
        rows.pop()
    elif change == "missing_start":
        rows.pop(0)
    elif change == "over_cap":
        rows.extend(copy.deepcopy(rows[7]) for _ in range(8194))
    elif change == "clock_regression":
        rows[6]["client_physics_tick"] = 0
    elif change == "native_ack_rejected":
        native[3]["result"] = "rejected"
    elif change == "native_probe_wrong_action":
        native[4]["request_id"] = "foreign"
    elif change == "original_action_mismatch":
        movement["action_id"] = "foreign"
    elif change == "bad_ordinal":
        rows[3]["ordinal"] = 100
    elif change == "extra_ack":
        rows.append(copy.deepcopy(rows[4]))
    elif change == "missing_physics_tick":
        rows[:] = [r for r in rows if r["kind"] != "PHYSICS_TICK"
                   or r["ordinal"] < 5]
    with pytest.raises(BoundaryRejected):
        review(f)


def test_bad_json_and_non_list_native_fail_closed():
    rows, native, movement = fixture()
    with pytest.raises(BoundaryRejected):
        review_native_controls("{broken", native, movement)
    with pytest.raises(BoundaryRejected):
        review_native_controls("\n".join(json.dumps(x) for x in rows),
                               "not-list", movement)
