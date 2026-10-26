"""#150 T1h STOP owner/independent Paper logger DEV negative controls."""
from __future__ import annotations

import pytest

from adapters.mineflayer.python_protocol import MineflayerEffectResult
from adapters.mineflayer.t1h_stop_owner_dev import (
    S49DevStopOwner,
    StopDevRejected,
    paper_stopped_after_marker,
)

W = "11111111-1111-4111-8111-111111111111"
P = "22222222-2222-4222-8222-222222222222"
SID = "test-s49-owner"
MARK = "T1H-STOP"


def log(*, count=10, active_at=None, gap_at=None, move_at=None,
        world=W, player=P, marker_tick=100):
    lines = [
        "INFO S_V8_DEV_SNAPSHOT marker_id=" + MARK
        + f" server_tick={marker_tick} world={W} x=0 y=64 z=0",
    ]
    for i in range(1, count + 1):
        tick = marker_tick + i + (1 if gap_at is not None and i >= gap_at else 0)
        pos = "0.1" if move_at == i else "0"
        active = "true" if active_at == i else "false"
        lines.append(
            "INFO PAPER_DEV_MOTOR_SAMPLE"
            + f" index={i} server_tick={tick} world={world} player={player}"
            + f" x={pos} y=64 z=0 forward={active} backward=false"
            + " left=false right=false jump=false sneak=false sprint=false"
        )
    return "\n".join(lines)


def receipt(*, action_id="t1h-clear", session_id=SID, effect="clear_controls",
            result="applied", seq=22):
    return MineflayerEffectResult(
        session_id=session_id, seq=seq,
        action_id=action_id, effect=effect, result=result,
        error=None if result == "applied" else "rejected",
    )


def requested():
    o = S49DevStopOwner(SID)
    o.request("t1h-stop-1", active_action_id="t1h-move", expected_clear_action_id="t1h-clear")
    return o


def test_stopped_paper_window_requires_eight_actual_stationary_transitions():
    first, last = paper_stopped_after_marker(log(), marker_id=MARK, world=W, player=P)
    assert (first, last) == (102, 109)


def test_stop_owner_latches_and_ack_is_distinct_from_shutdown_and_qualification():
    o = requested()
    assert o.requested and not o.allows_action
    assert o.ack is None
    o.accept_clear(receipt(), clear_action_id="t1h-clear")
    ack = o.finalize(log(), marker_id=MARK, world=W, player=P)
    assert ack.clear_ack_seq == 22
    assert ack.high_level_dev_stop_ack
    assert ack.classification == "S49_DEV_STOP_ACK_PAPER_IDLE_WINDOW"
    assert not ack.full_tick_stillness_qualified
    assert not ack.native_source_independently_authenticated
    assert not ack.p1_qualified_wait
    with pytest.raises(StopDevRejected):
        o.finalize(log(), marker_id=MARK, world=W, player=P)
    with pytest.raises(StopDevRejected):
        o.request("t1h-stop-2")


@pytest.mark.parametrize("field,value", [
    ("action_id", "foreign"),
    ("session_id", "another-session"),
    ("effect", "set_control"),
    ("result", "rejected"),
])
def test_no_dev_stop_ack_for_missing_or_false_client_clear(field, value):
    o = requested()
    with pytest.raises(StopDevRejected):
        o.accept_clear(receipt(**{field: value}), clear_action_id="t1h-clear")
    assert o.failed and o.ack is None


@pytest.mark.parametrize("change", [
    {"count": 8},
    {"count": 10, "gap_at": 5},
    {"count": 10, "world": "foreign"},
    {"count": 10, "player": "foreign"},
    {"count": 10, "move_at": 7},
    {"count": 10, "active_at": 6},
])
def test_partial_or_foreign_paper_never_ack_stop(change):
    o = requested()
    o.accept_clear(receipt(), clear_action_id="t1h-clear")
    with pytest.raises(StopDevRejected):
        o.finalize(log(**change), marker_id=MARK, world=W, player=P)
    assert o.failed and o.ack is None


def test_no_request_or_no_ack_never_promotes_bridge_shutdown_to_stop():
    o = S49DevStopOwner(SID)
    assert o.allows_action
    with pytest.raises(StopDevRejected):
        o.finalize(log(), marker_id=MARK, world=W, player=P)
    o.request("stop-1")
    with pytest.raises(StopDevRejected):
        o.finalize(log(), marker_id=MARK, world=W, player=P)
    assert not o.allows_action


def test_unrelated_log_marker_cannot_be_reused_for_dev_stop():
    o = requested()
    o.accept_clear(receipt(), clear_action_id="t1h-clear")
    with pytest.raises(StopDevRejected):
        o.finalize(log(), marker_id="other-marker", world=W, player=P)
    assert not o.allows_action


def test_caller_cannot_rename_an_old_action_clear_as_current_evidence():
    owner = requested()
    with pytest.raises(StopDevRejected, match="matching"):
        owner.accept_clear(receipt(action_id="old-clear"), clear_action_id="old-clear")
    assert owner.failed and owner.ack is None


def test_unissued_stop_never_accepts_any_motor_ack():
    owner = S49DevStopOwner(SID)
    owner.request("stop-unissued")
    with pytest.raises(StopDevRejected):
        owner.accept_clear(receipt(), clear_action_id="t1h-clear")
    assert owner.ack is None


def test_invalid_request_does_not_partially_latch_stop():
    owner = S49DevStopOwner(SID)
    with pytest.raises(StopDevRejected):
        owner.request("valid", active_action_id="bad action")
    assert not owner.requested and owner.allows_action


def test_duplicate_clear_is_consumed_once():
    owner = requested()
    owner.accept_clear(receipt(), clear_action_id="t1h-clear")
    with pytest.raises(StopDevRejected):
        owner.accept_clear(receipt(), clear_action_id="t1h-clear")
    assert owner.clear_ack_seq == 22


@pytest.mark.parametrize("change", [{"count": 20, "active_at": 19},
                                     {"count": 20, "move_at": 19},
                                     {"count": 20, "gap_at": 19},
                                     {"count": 20, "gap_at": 1}])
def test_later_fault_cannot_hide_behind_an_earlier_good_window(change):
    owner = requested()
    owner.accept_clear(receipt(), clear_action_id="t1h-clear")
    with pytest.raises(StopDevRejected):
        owner.finalize(log(**change), marker_id=MARK, world=W, player=P)
    assert owner.ack is None
