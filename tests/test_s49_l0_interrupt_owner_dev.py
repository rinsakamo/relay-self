"""#150 DEV-only S49 opt-in L0 abort: sole native receiver, no extra issuer."""
from __future__ import annotations

import asyncio

import pytest

import test_mineflayer_execution_qualification as base
from adapters.mineflayer.execution import (
    MineflayerCommand,
    WorldConsequenceStatus,
    _watch_l0_during_motor,
    execute_mineflayer_command,
)
from adapters.mineflayer.python_protocol import MineflayerPaperL0Shadow


WORLD = "11111111-1111-4111-8111-111111111111"
PLAYER = "22222222-2222-4222-8222-222222222222"


def shadow(seq: int, assessment: str = "KNOWN_NEAR_HOSTILE") -> MineflayerPaperL0Shadow:
    return MineflayerPaperL0Shadow(
        session_id="s15-session", seq=seq,
        source="MINEFLAYER_CACHE_SHADOW_L0_DEV",
        observation_precision="CLIENT_CACHE_POST_PAPER_MESSAGE_NOT_EPOCH_FRESH",
        paper_sample_index=1, paper_server_tick="123",
        paper_world=WORLD, paper_player=PLAYER,
        evaluation_duration_ns="50",
        assessment=assessment,
        cached_body_observed=assessment != "UNKNOWN",
        l0_shadow_evaluated=True,
        l0_fresh_world_tick_attested=False,
        authorized_action_issued=False,
        tps_admission_granted=False,
    )


def command() -> MineflayerCommand:
    return MineflayerCommand(
        action_id="interrupt-test-move", binding_id="s14-binding",
        action_ref="MOVE_BACKWARD", effect="set_control",
        control="back", state=True, duration_s=0.02,
        cleanup_action_id="interrupt-test-clear",
    )


@pytest.mark.parametrize("signal", [
    "UNKNOWN", "LOW_HEALTH", "LOW_FOOD", "KNOWN_NEAR_HOSTILE",
])
def test_danger_during_issued_motor_preempts_original_executor_and_reads_clear_ack(signal):
    cmd = command()
    session = base.FakeSession([
        base.observation(1, 0, 0),
        base.effect(2, cmd.action_id, "set_control"),
        shadow(3, signal),
        base.effect(4, cmd.cleanup_action_id, "clear_controls"),
    ])
    result = asyncio.run(execute_mineflayer_command(
        session, cmd, timeout_s=0.1,
        provenance=base.provenance("l0-interrupt"),
        l0_interrupt_dev=True,
    ))
    assert result.status is WorldConsequenceStatus.FAILED
    assert "L0 DEV abort request" in result.error
    assert result.cleanup_attempted
    assert result.cleanup_receipt is not None
    assert result.cleanup_receipt.result == "applied"
    assert session.sent.count(("clear_controls", cmd.cleanup_action_id)) == 1
    assert sum(1 for x in session.sent if x[0] == "set_control") == 1
    assert sum(1 for x in session.sent if x[0] == "observe") == 1


def test_danger_before_dispatch_never_starts_motor():
    cmd = command()
    session = base.FakeSession([shadow(1), base.observation(2, 0, 0)])
    result = asyncio.run(execute_mineflayer_command(
        session, cmd, timeout_s=0.1,
        provenance=base.provenance("before-dispatch"),
        l0_interrupt_dev=True,
    ))
    assert result.status is WorldConsequenceStatus.FAILED
    assert not result.cleanup_attempted
    assert all(x[0] != "set_control" for x in session.sent)


def test_opted_in_missing_l0_during_motor_fails_closed_with_one_cleanup_attempt():
    cmd = command()
    session = base.FakeSession([
        base.observation(1, 0, 0),
        base.effect(2, cmd.action_id, "set_control"),
    ])
    result = asyncio.run(execute_mineflayer_command(
        session, cmd, timeout_s=0.01,
        provenance=base.provenance("no-l0-during-motor"),
        l0_interrupt_dev=True,
    ))
    assert result.status is WorldConsequenceStatus.FAILED
    assert result.cleanup_attempted
    assert session.sent.count(("clear_controls", cmd.cleanup_action_id)) == 1


def test_noninterrupting_cache_shadow_never_grants_safe_world_claim():
    class DeferredSession(base.FakeSession):
        async def receive(self):
            if self._messages:
                return self._messages.popleft()
            await asyncio.sleep(10)
    session = DeferredSession([shadow(1, "NO_KNOWN_URGENT_SIGNAL")])
    asyncio.run(_watch_l0_during_motor(
        session, duration_s=0.01, session_id="s15-session",
    ))
    assert session.sent == []


def test_default_action_execution_remains_unchanged():
    cmd = command()
    session = base.FakeSession([
        base.observation(1, 0, 0),
        base.effect(2, cmd.action_id, "set_control"),
        base.effect(3, cmd.cleanup_action_id, "clear_controls"),
        base.observation(4, 0, 0.15),
    ])
    result = asyncio.run(execute_mineflayer_command(
        session, cmd, timeout_s=0.1,
        provenance=base.provenance("default-no-new-l0"),
    ))
    assert result.status is WorldConsequenceStatus.EXECUTED
    assert result.cleanup_attempted
    assert result.cleanup_receipt is not None


def test_missing_clear_ack_never_reissues_duplicate_action_id():
    cmd = command()
    session = base.FakeSession([
        base.observation(1, 0, 0),
        base.effect(2, cmd.action_id, "set_control"),
        shadow(3, "LOW_HEALTH"),
        # Original owner clear send succeeds locally, but client ACK is absent.
    ])
    result = asyncio.run(execute_mineflayer_command(
        session, cmd, timeout_s=0.01,
        provenance=base.provenance("clear-ack-lost"),
        l0_interrupt_dev=True,
    ))
    assert result.status is WorldConsequenceStatus.FAILED
    assert result.cleanup_attempted
    assert result.cleanup_receipt is None
    assert session.sent.count(("clear_controls", cmd.cleanup_action_id)) == 1
