"""T1h DEV: real S49 executor consumes an owner-local STOP predicate."""
from __future__ import annotations

import asyncio

import pytest

import test_mineflayer_execution_qualification as base
from adapters.mineflayer.execution import (
    MineflayerCommand,
    WorldConsequenceStatus,
    execute_mineflayer_command,
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
    owner.request("stop-before", active_action_id="t1h-move", expected_clear_action_id="t1h-clear")
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
                owner.request("stop-during", active_action_id="t1h-move", expected_clear_action_id="t1h-clear")
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
                owner.request("stop-lost-clear",active_action_id="t1h-move", expected_clear_action_id="t1h-clear")
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


@pytest.mark.parametrize("boundary", ["set_send", "dispatch_wait", "clear_wait", "after_clear"])
def test_stop_at_send_ack_and_cleanup_boundaries_clears_at_most_once(boundary):
    from dataclasses import replace

    from test_s49_l0_interrupt_owner_dev import shadow

    owner = S49DevStopOwner(SID)

    def request():
        owner.request("stop-boundary", active_action_id="t1h-move",
                      expected_clear_action_id="t1h-clear")

    class BoundarySession(base.FakeSession):
        async def send_set_control(self, *args, **kwargs):
            await super().send_set_control(*args, **kwargs)
            if boundary == "set_send":
                request()

        async def send_clear_controls(self, *args, **kwargs):
            await super().send_clear_controls(*args, **kwargs)
            if boundary == "clear_wait":
                request()

        async def receive(self):
            if (self._messages and isinstance(self._messages[0], MineflayerEffectResult)
                    and self._messages[0].effect == "clear_controls"
                    and ("clear_controls", "t1h-clear") not in self.sent):
                await asyncio.sleep(.1)
            m = await super().receive()
            if isinstance(m, MineflayerEffectResult):
                if boundary == "dispatch_wait" and m.effect == "set_control":
                    request()
                if boundary == "after_clear" and m.effect == "clear_controls":
                    request()
            return m

    # Keep cleanup ACK queued until original executor sends clear. A benign
    # tick is consumed by the same reader during the normal motor interval.
    session = BoundarySession([
        base.observation(1, 0, 0), base.effect(2, "t1h-move", "set_control"),
        shadow(3, "NO_KNOWN_URGENT_SIGNAL"),
        base.effect(4, "t1h-clear", "clear_controls"), base.observation(5, 0, 1),
    ])
    result = asyncio.run(execute_mineflayer_command(
        session, replace(command(), duration_s=.02), timeout_s=.1,
        provenance=base.provenance("boundary"), l0_interrupt_dev=True,
        stop_requested_dev=lambda: owner.requested,
    ))
    # Both normal cleanup and early interruption use the one clear path.
    if boundary in ("clear_wait", "after_clear"):
        assert owner.requested
    assert result.status is WorldConsequenceStatus.FAILED
    assert session.sent.count(("clear_controls", "t1h-clear")) == 1
    assert result.cleanup_receipt is not None
    assert not owner.allows_action


def test_stop_during_stalled_set_send_joins_write_before_single_clear():
    async def scenario():
        owner = S49DevStopOwner(SID)
        writing = False

        class StalledSend(base.FakeSession):
            async def send_set_control(self, *args, **kwargs):
                nonlocal writing
                writing = True
                await super().send_set_control(*args, **kwargs)
                try:
                    owner.request("stop-stalled-send", active_action_id="t1h-move",
                                  expected_clear_action_id="t1h-clear")
                    await asyncio.sleep(60)
                finally:
                    writing = False

            async def send_clear_controls(self, *args, **kwargs):
                assert not writing
                await super().send_clear_controls(*args, **kwargs)

        session = StalledSend([base.observation(1, 0, 0),
                               base.effect(2, "t1h-clear", "clear_controls")])
        async with asyncio.timeout(.2):
            result = await execute_mineflayer_command(
                session, command(), timeout_s=.1, provenance=base.provenance("stalled"),
                l0_interrupt_dev=True, stop_requested_dev=lambda: owner.requested,
            )
        assert result.status is WorldConsequenceStatus.FAILED
        assert "T1h high-level STOP" in result.error
        assert result.cleanup_receipt is not None
        assert session.sent.count(("clear_controls", "t1h-clear")) == 1
        assert not writing
    asyncio.run(scenario())
