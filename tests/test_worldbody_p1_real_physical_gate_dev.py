"""Pinned original P1 physical Paper-mode negative contract; World NOT run.

The pure gate receives DEV input/frame candidates; no independent R source
authenticity or original full-tick WAIT qualification is claimed.
"""
from __future__ import annotations

import asyncio
import re
from pathlib import Path

import pytest

from adapters.mineflayer.worldbody_paper_server import (
    WorldBodyStagingRejected,
    stage_fixed_worldbody,
)

pytest_plugins = ("test_worldbody_p1_existing_law_parity_dev",)

ROOT = Path(
    "adapters/mineflayer/worldbody_physics_dev/src/main/java/"
    "io/github/rinsakamo/worldbody"
)


def test_original_enabled_p1_profile_sha_pinned_to_exact_source(original_p1):
    owner = original_p1.FatigueProfile(enabled=True)
    source = (ROOT / "P1WorldTickGateDev.java").read_text(encoding="utf-8")
    assert owner.sha256 in source
    assert owner.move_per_block.value == 0.04
    assert owner.wait_recovery_per_world_tick.value == 0.1
    assert owner.impairment_per_fraction.value == 0.7
    assert original_p1.FatigueProfile().enabled is False


def test_law_paper_path_is_exclusive_and_only_dev_activated():
    plugin = (ROOT / "RelayWorldBodyDev.java").read_text(encoding="utf-8")
    original = (ROOT / "P1PaperPhysicalRuntimeDev.java").read_text(
        encoding="utf-8"
    )
    assert 'getConfig().getBoolean("p1-law-dev-enabled", false)' in plugin
    early = plugin[plugin.index("if (getConfig().getBoolean("):]
    assert early.index("return;") < early.index("enabledForDev = true;")
    assert "P1WorldTickGateDev" in original
    assert "getCurrentInput()" in original
    assert "PlayerInputEvent" in original
    assert "PlayerMoveEvent" in original
    assert "p.isOnGround()" in original
    assert "MAX_EVENT_BLOCKS = 1.0" in original
    assert "world_authority=true" in original
    assert "independent_s_r_attestation=false" in original
    assert "0.35" not in original
    assert "MOVE_FATIGUE_PER_METRE = 2.0" not in original
    assert "getConfig().getDouble" not in original
    assert "onCommand(" not in original  # owner marker only, no Self command


def test_native_tick_gate_never_claims_r_authenticity_or_quiet_from_action_gap():
    gate = (ROOT / "P1WorldTickGateDev.java").read_text(encoding="utf-8")
    assert "P1_DEV_SOURCE_GAP_OR_WRONG_WORLD_TICK" in gate
    assert "P1_DEV_MIXED_FIGHT_MOTION_UNKNOWN" in gate
    assert "P1_DEV_FULL_TICK_IDLE_UNATTESTED" in gate
    assert "observation.ownerMoveOpen()" in gate
    assert "observation.acceptedMoveBlocks() == 0" in gate
    assert "new DevResult(activity, frame.blocked(), transition," in gate
    assert "false, false" in gate
    assert 'P1FatigueLaw.Activity.WAIT' in gate
    # Capability is a prospective physical limit, never a S49 grant.
    assert "maxMoveBlocksPerWorldTick()" in (
        ROOT / "P1PaperPhysicalRuntimeDev.java"
    ).read_text()


def test_staging_requires_distinct_owner_grant_and_read_only_same_world(
    tmp_path, monkeypatch,
):
    monkeypatch.setenv("S49_REAL_SERVER_CI", "1")
    monkeypatch.setenv("S49_WORLDBODY_DEV_ONLY", "1")
    monkeypatch.setenv("S49_WB_P1_SOURCE_DEV_ONLY", "1")
    monkeypatch.delenv("S49_WB_P1_PHYSICAL_DEV_ONLY", raising=False)
    monkeypatch.delenv("NODE_OPTIONS", raising=False)
    with pytest.raises(WorldBodyStagingRejected):
        stage_fixed_worldbody(
            tmp_path, source_bridge_dev=True, p1_physics_dev=True,
        )
    assert list(tmp_path.iterdir()) == []


def test_original_s49_refuses_unapproved_p1_world_before_creation(
    tmp_path, monkeypatch,
):
    from adapters.mineflayer import s49_normal_session_real_ci as s49

    monkeypatch.setenv("S49_REAL_SERVER_CI", "1")
    monkeypatch.setenv("S49_WORLDBODY_DEV_ONLY", "1")
    monkeypatch.setenv("S49_WB_P1_SOURCE_DEV_ONLY", "1")
    monkeypatch.delenv("S49_WB_P1_PHYSICAL_DEV_ONLY", raising=False)
    monkeypatch.delenv("NODE_OPTIONS", raising=False)
    out = tmp_path / "report.json"
    code = asyncio.run(s49.qualify(
        out, tmp_path / "world.log", worldbody_dev=True,
        worldbody_p1_source_dev=True, worldbody_p1_physics_dev=True,
    ))
    assert code == 2
    assert "P1 physical World needs distinct exclusive S49 DEV gate" in (
        out.read_text()
    )
    assert not (tmp_path / "world.log").exists()


def test_same_world_p1_marker_lifecycle_is_operator_source_only():
    runner = Path(
        "adapters/mineflayer/s49_normal_session_real_ci.py"
    ).read_text()
    plugin = (ROOT / "P1PaperPhysicalRuntimeDev.java").read_text()
    assert "p1bodyarm {p1_same_world_nonce}" in runner
    assert re.search(r"p1bodyaction.*begin", runner, flags=re.DOTALL)
    assert "p1bodystop {p1_same_world_nonce}" in runner
    assert "source_bridge_dev=worldbody_p1_source_dev" in runner
    assert "p1_physics_dev=worldbody_p1_physics_dev" in runner
    assert "not decision.rest_requested" in runner  # legacy still strict
    assert "rest_choice.selected != (" in runner  # P1 WAIT permissible
    assert 'cmd.equals("p1bodyaction")' not in plugin
    assert 'kind.equals("p1bodyaction")' in plugin
    assert "ConsoleCommandSender" in plugin
