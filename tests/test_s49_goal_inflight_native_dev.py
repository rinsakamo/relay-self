"""S15 in-flight original-reader boundary and fail-closed physical semantics."""
from __future__ import annotations

from pathlib import Path

import pytest

from adapters.mineflayer.execution import (
    InvalidMineflayerExecutionData,
    MineflayerCommand,
    execute_mineflayer_command,
)
from adapters.mineflayer.s49_goal_inflight_review_dev import (
    InflightReviewRejected,
    review_inflight_two_worlds,
)
from relay_self.provenance import Provenance


def command():
    return MineflayerCommand(
        action_id="goal-original-step-1",
        binding_id="goal-binding-1",
        action_ref="MOVE_FORWARD",
        effect="set_control",control="forward",state=True,
        duration_s=0.35,cleanup_action_id="goal-original-step-1-s15-clear",
    )


@pytest.mark.asyncio
async def test_inflight_callback_rejected_without_separate_dev_gate(monkeypatch):
    monkeypatch.delenv("S49_L0_INFLIGHT_PREEMPT_DEV_ONLY",raising=False)
    monkeypatch.setenv("S49_L0_GOAL_LOOP_DEV_ONLY","1")
    with pytest.raises(InvalidMineflayerExecutionData):
        await execute_mineflayer_command(
            object(),command(),provenance=Provenance("test","negative-gate"),
            on_live_probe_dev=lambda probe:True,
        )


@pytest.mark.asyncio
async def test_inflight_callback_rejects_wrong_action_or_missing_callable(monkeypatch):
    monkeypatch.setenv("S49_L0_INFLIGHT_PREEMPT_DEV_ONLY","1")
    monkeypatch.setenv("S49_L0_GOAL_LOOP_DEV_ONLY","1")
    c=command()
    with pytest.raises(InvalidMineflayerExecutionData):
        await execute_mineflayer_command(
            object(),c,provenance=Provenance("test","bad-callback"),
            on_live_probe_dev=True,
        )
    from dataclasses import replace
    with pytest.raises(InvalidMineflayerExecutionData):
        await execute_mineflayer_command(
            object(),replace(c,action_ref="MOVE_BACKWARD",control="back"),
            provenance=Provenance("test","bad-action"),
            on_live_probe_dev=lambda probe:True,
        )


def test_missing_two_world_evidence_fails_closed(tmp_path):
    with pytest.raises(InflightReviewRejected):
        review_inflight_two_worlds(tmp_path)


def test_exclusive_s15_reader_no_second_issuer_and_unknown_on_stop():
    source=Path("adapters/mineflayer/execution.py").read_text()
    owner=Path("adapters/mineflayer/s49_goal_executor_dev.py").read_text()
    runner=Path("adapters/mineflayer/s49_goal_loop_real_dev.py").read_text()
    assert "on_live_probe_dev" in source
    assert "await adapter.send_observe(request_id)" in source
    assert "await _receive_until(" in source
    assert 'error=("DEV_L0_INFLIGHT_NATIVE_THREAT_PREEMPTED"' in source
    assert "on_live_probe_dev=on_live_probe_dev" in owner
    assert "interpretation.disposition is not ActionOutcomeDisposition.OUTCOME" in owner
    assert "on_effect_ack_dev" in runner
    assert '"injected_after_applied"' in runner
    assert "receipt.terminal.state is not ActionState.UNKNOWN" in runner
    assert "executor.supervisor.open_actions" in runner
