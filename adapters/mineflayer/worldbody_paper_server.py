"""One World-owned, fixed-law Minecraft Paper WorldBody DEV staging.

Separate from the virtual P1 profile. The Java plugin **actually changes**
the server Player walk speed, but it exposes neither true fatigue nor World
recovery coefficients to the Self/Python host. Server logs are a separate
operator-only audit artifact, never input to the L0 REST decision.
"""
from __future__ import annotations

import hashlib
import os
import shutil
from pathlib import Path

from adapters.mineflayer.s31a_real_server_ci import S31ABlocked
from adapters.mineflayer.s49_p1_paper_server import PAPER_1218_SHA256, PAPER_1218_SIZE

PLUGIN_JAR = "relay-worldbody-physics-dev-0.1.0-dev.jar"
CONFIG = (
    "# Exclusive disposable World-owned physics DEV World\n"
    "dev-enabled: true\n"
    "target-player: RelaySelf\n"
)


class WorldBodyStagingRejected(S31ABlocked):
    pass


def stage_fixed_worldbody(
    root: Path, *, source_bridge_dev: bool = False,
    p1_physics_dev: bool = False,
) -> dict:
    if (
        os.environ.get("S49_REAL_SERVER_CI") != "1"
        or os.environ.get("S49_WORLDBODY_DEV_ONLY") != "1"
        or not isinstance(root, Path) or not root.is_absolute()
        or not root.is_dir() or root.is_symlink()
    ):
        raise WorldBodyStagingRejected("fresh exclusive WorldBody DEV grant required")

    def require(name: str) -> Path:
        value = os.environ.get(name)
        if not value:
            raise WorldBodyStagingRejected(f"{name} missing")
        path = Path(value)
        if (
            not path.is_absolute() or not path.is_file() or path.is_symlink()
            or any(parent.is_symlink() for parent in path.parents)
        ):
            raise WorldBodyStagingRejected("only immutable regular absolute artifacts")
        return path

    if type(source_bridge_dev) is not bool or (source_bridge_dev and (
        os.environ.get("S49_WB_P1_SOURCE_DEV_ONLY") != "1"
    )):
        raise WorldBodyStagingRejected("explicit same-World P1 source DEV gate required")

    if (
        type(p1_physics_dev) is not bool
        or (p1_physics_dev and (
            not source_bridge_dev
            or os.environ.get("S49_WB_P1_PHYSICAL_DEV_ONLY") != "1"
        ))
    ):
        raise WorldBodyStagingRejected(
            "P1 physical DEV needs distinct owner grant and same-World source"
        )

    paper = require("S49_WB_PAPER_JAR")
    plugin = require("S49_WB_PLUGIN_JAR")
    expect = os.environ.get("S49_WB_PLUGIN_SHA256", "")
    if (
        paper.stat().st_size != PAPER_1218_SIZE
        or hashlib.sha256(paper.read_bytes()).hexdigest() != PAPER_1218_SHA256
        or plugin.name != PLUGIN_JAR
        or plugin.stat().st_size < 1000
        or len(expect) != 64
        or any(ch not in "0123456789abcdef" for ch in expect)
        or hashlib.sha256(plugin.read_bytes()).hexdigest() != expect
        or paper == plugin
    ):
        raise WorldBodyStagingRejected("wrong Paper/plugin bytes or unpinned build")

    # Validate the existing #734 collector as a *second read-only plugin*.
    # A missing/wrong plugin fails before altering disposable World files.
    source_plugin = None
    source_sha = None
    if source_bridge_dev:
        source_plugin = require("S49_WB_P1_SOURCE_PLUGIN_JAR")
        source_sha = os.environ.get("S49_WB_P1_SOURCE_PLUGIN_SHA256", "")
        from adapters.mineflayer.s49_p1_paper_server import PLUGIN_JAR as SOURCE_JAR
        if (
            source_plugin.name != SOURCE_JAR
            or source_plugin == paper or source_plugin == plugin
            or source_plugin.stat().st_size < 1000
            or len(source_sha) != 64
            or any(ch not in "0123456789abcdef" for ch in source_sha)
            or hashlib.sha256(source_plugin.read_bytes()).hexdigest() != source_sha
        ):
            raise WorldBodyStagingRejected("wrong reused #734 read-only source plugin")
    shutil.copyfile(paper, root / "minecraft.jar")
    folder = root / "plugins"
    folder.mkdir(mode=0o700)
    shutil.copyfile(plugin, folder / PLUGIN_JAR)
    cfg = folder / "RelayWorldBodyDev"
    cfg.mkdir(mode=0o700)
    # Preserve the legacy #738 config and physical coefficients verbatim.
    # The new DEV mode is opt-in and mutually exclusive at Paper onEnable.
    physics_config = CONFIG
    if p1_physics_dev:
        physics_config += (
            "# Original P1 #626 standard law, server-owned and immutable\\n"
            "p1-law-dev-enabled: true\\n"
        )
    (cfg / "config.yml").write_text(physics_config, encoding="utf-8")
    if source_plugin is not None:
        shutil.copyfile(source_plugin, folder / source_plugin.name)
        source_cfg = folder / "S49P1Dev"
        source_cfg.mkdir(mode=0o700)
        (source_cfg / "config.yml").write_text(
            "# Reused #734 read-only Paper callback recorder; no P1 state or Action\n"
            "dev-enabled: true\n"
            "target-player: RelaySelf\n"
            "max-ticks: 2400\n",
            encoding="utf-8",
        )
    return {
        "s49_dev_server": "PINNED_PAPER_1_21_8",
        "s49_worldbody_plugin_sha256": expect,
        "worldbody_profile": (
            "PINNED_ORIGINAL_P1_PER_WORLD_TICK_CAP_DEV"
            if p1_physics_dev else "SERVER_FIXED_WALK_SPEED_UNOBSERVED_FATIGUE"
        ),
        "worldbody_p1_physics_dev": p1_physics_dev,
        "worldbody_truth_exported_to_self": False,
        "worldbody_rule_mutation_surface": False,
        "original_s49_issuer_unchanged": True,
        "worldbody_p1_same_world_source_dev": source_bridge_dev,
        "worldbody_p1_source_plugin_sha256": source_sha,
        "worldbody_p1_source_is_not_full_tick_wait_attestation": True,
    }
