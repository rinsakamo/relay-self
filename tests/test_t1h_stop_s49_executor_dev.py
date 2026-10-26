"""T1h DEV: real S49 executor consumes an owner-local STOP predicate."""
from __future__ import annotations

import asyncio

import pytest

import test_mineflayer_execution_qualification as base
from adapters.mineflayer.execution import (
    MineflayerCommand, WorldConsequenceStatus, execute_mineflayer_command,
)
from adapters.mineflayer.python_protocol import MineflayerEffectResult
from adapters.mineflayer.t1h_stop_owner_dev import S49DevStopOwner

SID = "s15-session"


def command():
    return MineflayerCommand(
        action_id="t1h-move", binding_id="t1h-binding", action_ref="MOVE_BACKWARD",
        effect="set_control", control="back", state=True, duration_s=0.3,
        cleanup_action_id="t1h-clear",
    )


def run(sess, owner):
    return asyncio.run(execute_mineflayer_command(
        sess, command(), timeout_s=.1, provenance=base.provenance("t1h-owner"),
        l0_interrupt_dev=True, stop_requested_dev=lambda: owner.requested,
    ))


def test_explicit_stop_before_dispatch_never_sets_motor():
    owner = S49DevStopOwner(SID)
    owner.request("stop-before", active_action_id="t1h-move")
    session = base.FakeSession([base.observation(1,0,0)])
    result = run(session, owner)
    assert result.status == WorldConsequenceStatus.FAILED
    assert "T1h high-level STOP" in result.error
    assert all(x[0] != "set_control" for x in session.sent)
    assert all(x[0] != "clear_controls" for x in session.sent)
    assert not owner.allows_action


def test_stop_after_dispatch_interrupts_once_through_s49_clear_path():
    owner = S49DevStopOwner(SID)

    class StopOnDispatch(base.FakeSession):
        async def receive(self):
            m = await super().receive()
            if isinstance(m, MineflayerEffectResult) and m.effect == "set_control":
                owner.request("stop-during", active_action_id="t1h-move")
            return m

    session = StopOnDispatch([
        base.observation(1, 0, 0),
        base.effect(2,"t1h-move","set_control"),
        base.effect(3,"t1h-clear","clear_controls"),
    ])
    result = run(session, owner)
    assert result.status == WorldConsequenceStatus.FAILED
    assert result.cleanup_attempted
    assert result.cleanup_receipt is not None
    assert result.cleanup_receipt.seq == 3
    assert session.sent.count(("clear_controls", "t1h-clear")) == 1
    assert session.sent.count(("set_control", "t1h-move", "back", True)) == 1
    assert "T1h high-level STOP" in result.error
    owner.accept_clear(result.cleanup_receipt, clear_action_id="t1h-clear")
    assert not owner.allows_action


def test_stop_clear_ack_lost_cannot_repeat_motor_or_claim_ack():
    owner = S49DevStopOwner(SID)

    class StopOnDispatch(base.FakeSession):
        async def receive(self):
            m = await super().receive()
            if isinstance(m, MineflayerEffectResult) and m.effect == "set_control":
                owner.request("stop-lost-clear",active_action_id="t1h-move")
            return m

    session = StopOnDispatch([
        base.observation(1,0,0),
        base.effect(2,"t1h-move","set_control"),
    ])
    result = run(session,owner)
    assert result.status == WorldConsequenceStatus.FAILED
    assert result.cleanup_attempted and result.cleanup_receipt is None
    assert session.sent.count(("clear_controls","t1h-clear")) == 1
    assert not owner.allows_action


def test_forged_stop_callback_needs_explicit_dev_owner():
    session = base.FakeSession()
    with pytest.raises(ValueError,match="requires explicit"):
        asyncio.run(execute_mineflayer_command(
            session,command(),provenance=base.provenance("no-dev"),
            stop_requested_dev=lambda: True,
        ))
