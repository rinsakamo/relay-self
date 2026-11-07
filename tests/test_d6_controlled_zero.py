"""D6-D4: original S49 multi-generation DEV controlled-zero World gates.

The test explicitly disables normal Minecraft drops, so zero outcomes here
must NEVER be reported as independent vanilla RNG.
"""
from __future__ import annotations

import asyncio
import json

import pytest

from tools.bug0_d4_oneworld import run
from tools.bug0_d6_multigen_post import MultigenAuditRejected, audit
from tools.bug0_d6_multigen_world import continue_after_first_respawn
from tools.bug0_d6_natural_move_world import source_qualified_natural_move


def test_controlled_zero_scope_requires_separate_world_grant(monkeypatch, tmp_path):
    monkeypatch.setenv("S49_REAL_SERVER_CI", "1")
    monkeypatch.setenv("BUG0_S49_D4_ONE_WORLD_ONLY", "1")
    monkeypatch.setenv("D6_NATURAL_DROP_MOVE_WORLD_ONLY", "1")
    monkeypatch.setenv("D6_NATURAL_MULTIGEN_WORLD_ONLY", "1")
    monkeypatch.setenv("S49_D5_NONMOTION_FENCE_DEV_ONLY", "1")
    monkeypatch.delenv("D6_CONTROLLED_ZERO_WORLD_ONLY", raising=False)
    report=tmp_path/"report.json"
    exit_code=asyncio.run(run(
        report, tmp_path/"paper.log",
        nonmotion_fence_path=tmp_path/"nonmotion.json",
        motion_fence_path=tmp_path/"motion.json",
        post_death_loot_move_dev=source_qualified_natural_move,
        post_respawn_dev=continue_after_first_respawn,
        d6_multigen_dev=True, d6_controlled_zero_dev=True,
    ))
    assert exit_code != 0
    body=json.loads(report.read_text())
    assert not body.get("real_world_started", False)
    assert not (tmp_path/"nonmotion.json").exists()
    assert not (tmp_path/"motion.json").exists()
    assert not (tmp_path/"paper.log").exists()


@pytest.mark.parametrize("override", [
    {"d6_multigen_source_natural_drop_rng_unchanged": True},
    {"d6_multigen_operator_forced_zero": False},
    {"d6_controlled_zero_world_rule": "doMobLoot=true"},
    {"d6_controlled_zero_set_before_first_attack": False},
])
def test_independent_audit_never_accepts_forced_zero_as_natural(tmp_path, override):
    report={
        "status":"PASS_DEV", "real_world_started":True,
        "node_exit":0, "java_exit":0, "cleanup_done":True,
        "d6_operator_forced_zero":True,
        "d6_controlled_zero_not_vanilla_sample":True,
        "d6_controlled_zero_world_rule":"doMobLoot=false",
        "d6_controlled_zero_command":"gamerule doMobLoot false",
        "d6_controlled_zero_set_before_first_attack":True,
        "d6_multigen_self_policy_epoch_limit_imposed":False,
        "d6_multigen_source_natural_drop_rng_unchanged":False,
        "d6_multigen_operator_forced_zero":True,
        "d6_multigen_no_physical_reissue":True,
        "d6_multigen_no_eat":True,
        "d6_multigen_same_supervisor":True,
        "d6_multigen_eat_after_move":False,
        "self_eat":False, "self_goal_selected_autonomously":False,
        "real_model_calls":0, "learning_updated":False,
        "d6_multigen_dev_world_trial_limit":4,
    }
    report.update(override)
    with pytest.raises(MultigenAuditRejected):
        audit("", report, nonmotion_path=tmp_path/"a", motion_path=tmp_path/"m")
