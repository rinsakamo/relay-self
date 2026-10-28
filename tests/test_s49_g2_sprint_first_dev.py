"""G2 alternate motor request is *only* the original S49 issuer, DEV gated."""
import asyncio

import pytest

from adapters.mineflayer.normal_action import NormalActionRejected
from adapters.mineflayer.s49_goal_executor_dev import S49GoalExecutorDev


def test_g2_sprint_cannot_issue_without_all_explicit_gates(monkeypatch):
    monkeypatch.delenv("S49_GOAL_G2_SPRINT_FIRST_DEV_ONLY", raising=False)
    executor=object.__new__(S49GoalExecutorDev)
    executor._count=0
    with pytest.raises(NormalActionRejected,match="G2 sprint requires"):
        asyncio.run(executor.execute_goal_step(
            None,directive=None,decision=None,probe=None,propose=None,
            issue=None,g2_sprint_first_dev=True,
        ))


def test_g2_sprint_is_refused_after_any_prior_original_action(monkeypatch):
    monkeypatch.setenv("S49_GOAL_G2_SPRINT_FIRST_DEV_ONLY","1")
    monkeypatch.setenv("S49_SPRINT_MOTOR_DEV_ONLY","1")
    monkeypatch.setenv("S49_L1_G1_OBSERVATION_DEV_ONLY","1")
    executor=object.__new__(S49GoalExecutorDev)
    executor._count=1
    with pytest.raises(NormalActionRejected,match="G2 sprint requires"):
        asyncio.run(executor.execute_goal_step(
            None,directive=None,decision=None,probe=None,propose=None,
            issue=None,g2_sprint_first_dev=True,
        ))


def test_g2_sprint_rejects_unproven_live_hazard_or_turn(monkeypatch):
    monkeypatch.setenv("S49_GOAL_G2_SPRINT_FIRST_DEV_ONLY","1")
    monkeypatch.setenv("S49_SPRINT_MOTOR_DEV_ONLY","1")
    monkeypatch.setenv("S49_L1_G1_OBSERVATION_DEV_ONLY","1")
    executor=object.__new__(S49GoalExecutorDev)
    executor._count=0
    with pytest.raises(NormalActionRejected,match="G2 sprint requires"):
        asyncio.run(executor.execute_goal_step(
            None,directive=None,decision=None,probe=None,propose=None,
            issue=None,g2_sprint_first_dev=True,look_yaw_dev=0.0,
        ))


def test_existing_mineflayer_command_requires_exact_sprint_action_ref():
    from adapters.mineflayer.execution import (
        MOVE_FORWARD_ACTION_REF,
        MOVE_FORWARD_SPRINT_DEV_REF,
        MineflayerCommand,
    )
    with pytest.raises(ValueError):
        MineflayerCommand(
            action_id="g2",binding_id="g2-binding",
            action_ref=MOVE_FORWARD_ACTION_REF,
            effect="set_forward_sprint_dev",control="forward",state=True,
            duration_s=0.35,cleanup_action_id="g2-clear",
        )
    original=MineflayerCommand(
        action_id="g2",binding_id="g2-binding",
        action_ref=MOVE_FORWARD_SPRINT_DEV_REF,
        effect="set_forward_sprint_dev",control="forward",state=True,
        duration_s=0.35,cleanup_action_id="g2-clear",
    )
    assert original.effect=="set_forward_sprint_dev"


def test_g2_sneak_requires_owner_and_explicit_gate(monkeypatch):
    monkeypatch.delenv("S49_GOAL_G2_SNEAK_DEV_ONLY", raising=False)
    executor=object.__new__(S49GoalExecutorDev)
    executor._count=0
    with pytest.raises(NormalActionRejected,match="G2 sneak requires"):
        asyncio.run(executor.execute_goal_step(
            None,directive=None,decision=None,probe=None,propose=None,
            issue=None,g2_sneak_prefix_dev=True,
        ))


def test_g2_sneak_refused_after_three_original_actions(monkeypatch):
    monkeypatch.setenv("S49_GOAL_G2_SNEAK_DEV_ONLY","1")
    monkeypatch.setenv("S49_L1_G1_OBSERVATION_DEV_ONLY","1")
    executor=object.__new__(S49GoalExecutorDev)
    executor._count=3
    with pytest.raises(NormalActionRejected,match="G2 sneak requires"):
        asyncio.run(executor.execute_goal_step(
            None,directive=None,decision=None,probe=None,propose=None,
            issue=None,g2_sneak_prefix_dev=True,
        ))


def test_g2_sneak_no_unowned_live_probe_or_rotation(monkeypatch):
    monkeypatch.setenv("S49_GOAL_G2_SNEAK_DEV_ONLY","1")
    monkeypatch.setenv("S49_L1_G1_OBSERVATION_DEV_ONLY","1")
    executor=object.__new__(S49GoalExecutorDev)
    executor._count=0
    with pytest.raises(NormalActionRejected,match="G2 sneak requires"):
        asyncio.run(executor.execute_goal_step(
            None,directive=None,decision=None,probe=None,propose=None,
            issue=None,g2_sneak_prefix_dev=True,look_yaw_dev=0.0,
        ))


def test_g2_sneak_cannot_masquerade_as_normal_control():
    from adapters.mineflayer.execution import (
        MOVE_FORWARD_ACTION_REF,
        MOVE_FORWARD_SNEAK_DEV_REF,
        MineflayerCommand,
    )
    with pytest.raises(ValueError):
        MineflayerCommand(
            action_id="g2",binding_id="g2-binding",
            action_ref=MOVE_FORWARD_ACTION_REF,effect="set_forward_sneak_dev",
            control="forward",state=True,
            duration_s=0.35,cleanup_action_id="g2-clear",
        )
    command=MineflayerCommand(
        action_id="g2",binding_id="g2-binding",
        action_ref=MOVE_FORWARD_SNEAK_DEV_REF,effect="set_forward_sneak_dev",
        control="forward",state=True,
        duration_s=0.35,cleanup_action_id="g2-clear",
    )
    assert command.effect=="set_forward_sneak_dev"


def test_g2_sneak_wire_command_is_exact_pair():
    import json

    from adapters.mineflayer.python_protocol import encode_forward_sneak_dev
    value=json.loads(encode_forward_sneak_dev("g2-sneak"))
    assert value == {
        "type":"effect", "action_id":"g2-sneak",
        "effect":"set_forward_sneak_dev","forward":True,"sneak":True,
    }
