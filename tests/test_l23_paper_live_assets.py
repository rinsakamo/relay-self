"""L23 Paper asset/console opt-in regression; no Java, Paper or GPU."""
from __future__ import annotations

import asyncio
import hashlib
import json
from pathlib import Path

import pytest

from adapters.mineflayer.l23_paper_live_assets import (
    L23PaperAssets,
    L23PaperBlocked,
    paper_marker,
    stage_paper_assets,
    verify_paper_assets,
    wait_paper_line,
)

# Synthetic test config with the exact S-owned 16-key M0.2 action roster.
# This file does not claim an executable Java plugin or calibrated ecology.
ACTION_NAMES = (
    "BASAL", "WALK", "CROUCH", "SPRINT", "SWIM",
    "WALK_ON_WATER", "WALK_UNDERWATER", "JUMP", "JUMP_SPRINT",
    "ATTACK", "DAMAGED", "BLOCK_MINED", "REGEN", "HUNGER_EFFECT",
    "UNKNOWN", "COGNITION",
)
CONFIG = (
    "dev-enabled: true\n"
    "s50-tick-meter-dev: true\n"
    "target-player: RelaySelf\n"
    "minecraft-version: 1.21.8\n"
    "version: M0.2\n"
    "calibration-status: candidate_uncalibrated\n"
    "standard-food: cooked_beef\n"
    "actions:\n"
    + "".join(
        f"  {name}: {{unit: event, standard: 0.0, multiplier: 1.0, "
        "additional: 0.0, enabled: true}\n"
        for name in ACTION_NAMES
    )
)


def make_assets(tmp_path, *, config=CONFIG):
    inputs = tmp_path / "assets"
    inputs.mkdir()
    jar = inputs / "paper.jar"
    plugin = inputs / "plugin.jar"
    cfg = inputs / "config.yml"
    jar.write_bytes(b"test-only Paper jar, not executable")
    plugin.write_bytes(b"test-only plugin jar, not executable")
    cfg.write_text(config)
    def sha(file):
        return hashlib.sha256(file.read_bytes()).hexdigest()
    return L23PaperAssets(
        jar, sha(jar), plugin, sha(plugin), cfg, sha(cfg),
    )


def test_paper_assets_are_pinned_and_staged_only_in_fresh_world(tmp_path):
    assets = make_assets(tmp_path)
    verified = verify_paper_assets(assets)
    assert verified["qualification"] == "DEV_ONLY"
    assert verified["paper_profile"] == "ACTIVE_METABOLISM_INTERVENTION_NOT_PASSIVE"
    root = tmp_path / "fresh-world"
    root.mkdir()
    staged = stage_paper_assets(assets, root)
    assert staged == verified
    assert (root / "minecraft.jar").read_bytes() == assets.server_jar.read_bytes()
    assert (root / "plugins/RelayMetabolismDev/config.yml").read_bytes() == (
        assets.plugin_config.read_bytes()
    )
    with pytest.raises(L23PaperBlocked):
        stage_paper_assets(assets, root)


@pytest.mark.parametrize("fault", [
    "disabled", "wrong_target", "tick_disabled",
    "duplicate_config", "modified_sha", "relative",
    "wrong_version", "missing_food", "missing_calibration",
    "missing_action", "duplicate_action", "missing_actions_section",
])
def test_paper_bad_profile_rejected_before_world(tmp_path, fault):
    overrides = {
        "disabled": CONFIG.replace("dev-enabled: true", "dev-enabled: false"),
        "wrong_target": CONFIG.replace("RelaySelf", "SomeOtherPlayer"),
        "tick_disabled": CONFIG.replace(
            "s50-tick-meter-dev: true", "s50-tick-meter-dev: false",
        ),
        "duplicate_config": CONFIG + "dev-enabled: true\n",
        "wrong_version": CONFIG.replace("version: M0.2", "version: bad"),
        "missing_food": CONFIG.replace("standard-food: cooked_beef\n", ""),
        "missing_calibration": CONFIG.replace(
            "calibration-status: candidate_uncalibrated\n", "",
        ),
        "missing_action": CONFIG.replace("  BASAL: {", "  OMITTED: {"),
        "duplicate_action": CONFIG + "  BASAL: {unit: tick}\n",
        "missing_actions_section": CONFIG.replace("actions:\n", ""),
    }
    assets = make_assets(tmp_path, config=overrides.get(fault, CONFIG))
    if fault == "modified_sha":
        assets.plugin_jar.write_bytes(b"modified content")
    if fault == "relative":
        assets = L23PaperAssets(
            Path("relative.jar"), assets.server_sha256,
            assets.plugin_jar, assets.plugin_sha256,
            assets.plugin_config, assets.config_sha256,
        )
    with pytest.raises(L23PaperBlocked):
        verify_paper_assets(assets)


def test_marker_matches_native_action_session_and_disallows_injection():
    assert paper_marker("s49-native-move-24", "a-b") == "s49-native-move-24-a-b"
    for action, session in (
        ("bad:action", "sid"), ("s49", "../bad"),
        ("s49", "session\nstop"), ("a" * 128, "session"),
    ):
        with pytest.raises(L23PaperBlocked):
            paper_marker(action, session)


def test_paper_ack_gate_accepts_only_plugin_emitted_row(tmp_path):
    log = tmp_path / "server.log"
    marker = "s49-native-move-24-session"
    log.write_text(
        "[INFO] M02_DEV_S50_PHASE marker_id=s49-native-move-24-session "
        "phase=PRE_FORWARD world_full_time=290 world=abc\n"
        "[INFO] S50_DEV_WAIT_BEGIN marker_id=s49-native-move-24-session "
        "world=abc tick=300\n"
    )
    asyncio.run(wait_paper_line(
        log, marker=marker, kind="M02_DEV_S50_PHASE", phase="PRE_FORWARD",
    ))
    asyncio.run(wait_paper_line(
        log, marker=marker, kind="S50_DEV_WAIT_BEGIN",
    ))
    with pytest.raises(L23PaperBlocked):
        asyncio.run(wait_paper_line(
            log, marker=marker, kind="M02_DEV_S50_PHASE",
            phase="POST_CLEAR", timeout_s=0.01,
        ))


def test_s49_preflight_rejects_l23_without_l22_before_java(tmp_path, monkeypatch):
    from adapters.mineflayer import self_body_s50_world_dev as s49

    monkeypatch.setenv("S49_REAL_SERVER_CI", "1")
    monkeypatch.delenv("NODE_OPTIONS", raising=False)
    def fail_java(*_args, **_kwargs):
        pytest.fail("preflight must not reach Java or World")
    monkeypatch.setattr(s49, "_fetch_official_server", fail_java)
    root = tmp_path / "report.json"
    status = asyncio.run(s49.qualify(
        root, tmp_path / "server.log",
        l23_paper_assets=make_assets(tmp_path),
    ))
    report = json.loads(root.read_text())
    assert status == 2
    assert report["status"] == "BLOCKED"
    assert not (tmp_path / "server.log").exists()


def test_paper_eighth_callback_required_before_session_shutdown(tmp_path):
    log = tmp_path / "server.log"
    marker = "s49-native-move-24-session"
    prefix = f"[INFO] S50_DEV_WAIT_TICK marker_id={marker} "
    log.write_text("".join(
        f"{prefix}tick={300 + i} index={i}\n" for i in range(1, 8)
    ))
    with pytest.raises(L23PaperBlocked):
        asyncio.run(wait_paper_line(
            log, marker=marker, kind="S50_DEV_WAIT_TICK", timeout_s=0.01,
        ))

    async def delayed_eighth():
        waiter = asyncio.create_task(wait_paper_line(
            log, marker=marker, kind="S50_DEV_WAIT_TICK", timeout_s=1,
        ))
        await asyncio.sleep(0.02)
        assert not waiter.done()
        with log.open("a") as out:
            out.write(f"{prefix}tick=308 index=8\n")
        await waiter

    asyncio.run(delayed_eighth())
