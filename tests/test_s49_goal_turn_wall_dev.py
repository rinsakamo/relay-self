"""L2/L1 bounded target bearing, original S15 yaw and wall fail-closed."""
from __future__ import annotations

import asyncio
import math
from pathlib import Path

import pytest

from adapters.mineflayer.execution import (
    InvalidMineflayerExecutionData,
    MineflayerCommand,
    execute_mineflayer_command,
)
from relay_self.goal_navigation import (
    GoalControlRejected,
    GoalPurpose,
    L2GoalProposal,
    compile_l1_goal_dev,
    compute_goal_bearing_dev,
)
from relay_self.provenance import Provenance


def directive(dx=1.4,dz=2.6):
    goal=L2GoalProposal(
        goal_id="turn-goal",intent_id="turn-intent",session_id="session",
        target_x=dx,target_z=dz,purpose=GoalPurpose.APPROACH,
        minimum_tolerance_m=0.30,maximum_tolerance_m=0.55,
        danger_interrupt_m=1.5,provenance=Provenance("l2-dev","target"),
    )
    return compile_l1_goal_dev(
        goal,current_x=0.0,current_z=0.0,
        provenance=Provenance("l1-dev","precision"),
    )


def command():
    return MineflayerCommand(
        action_id="native-goal-step-1",
        binding_id="goal-binding-1",
        action_ref="MOVE_FORWARD",effect="set_control",
        control="forward",state=True,duration_s=0.35,
        cleanup_action_id="native-goal-step-1-s15-clear",
    )


def test_target_bearing_calculated_from_l2_l1_immutable_xz():
    fx,fz,yaw=compute_goal_bearing_dev(
        directive(),current_x=0.0,current_z=0.0,
    )
    assert math.hypot(fx,fz)==pytest.approx(1)
    assert fx==pytest.approx(1.4/math.hypot(1.4,2.6))
    assert fz==pytest.approx(2.6/math.hypot(1.4,2.6))
    assert yaw==pytest.approx(math.atan2(-1.4,-2.6))
    assert fx>0 and fz>0


@pytest.mark.parametrize("x,z",[
    (float("nan"),0.0),(1.0,float("inf")),
    (1.4,2.6),
])
def test_rejects_nonfinite_or_zero_target_bearing(x,z):
    with pytest.raises(GoalControlRejected):
        compute_goal_bearing_dev(directive(),current_x=x,current_z=z)


def test_straight_goal_yaw_is_minecraft_positive_z():
    fx,fz,yaw=compute_goal_bearing_dev(
        directive(0.0,2.6),current_x=0.0,current_z=0.0,
    )
    assert fx==0.0 and fz==1.0
    assert abs(yaw)==pytest.approx(math.pi)


def test_look_requires_independent_goal_dev_gate(monkeypatch):
    monkeypatch.setenv("S49_L0_GOAL_LOOP_DEV_ONLY","1")
    monkeypatch.delenv("S49_L0_TURN_DEV_ONLY",raising=False)
    with pytest.raises(InvalidMineflayerExecutionData):
        asyncio.run(execute_mineflayer_command(
            object(),command(),provenance=Provenance("dev","invalid"),
            look_yaw_dev=1.0,on_look_ack_dev=lambda _:None,
        ))


def test_unbound_look_ack_rejected(monkeypatch):
    monkeypatch.setenv("S49_L0_GOAL_LOOP_DEV_ONLY","1")
    monkeypatch.setenv("S49_L0_TURN_DEV_ONLY","1")
    with pytest.raises(InvalidMineflayerExecutionData):
        asyncio.run(execute_mineflayer_command(
            object(),command(),provenance=Provenance("dev","invalid"),
            look_yaw_dev=None,on_look_ack_dev=lambda _:None,
        ))


def test_single_s15_reader_retains_look_and_original_motor_receipts():
    src=Path("adapters/mineflayer/execution.py").read_text()
    goal=Path("adapters/mineflayer/s49_goal_loop_real_dev.py").read_text()
    assert "await adapter.send_look(look_id" in src
    assert 'msg.action_id == look_id and msg.effect == "look"' in src
    assert "on_look_ack_dev(look_ack)" in src
    assert '"look_yaw_dev":float(yaw)' in goal
    assert "native_alignment_to_goal" in goal
    assert "wall_world_stimulus_requested" in goal
    assert "MOTOR_CONSEQUENCE_UNDETERMINED" in goal
    assert '"no_additional_action_issued":True' in goal
