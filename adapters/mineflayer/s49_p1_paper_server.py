"""Exact-source, DEV-only Paper 1.21.8 launcher staging for S49 P1.

Separate mode only: default S49 still downloads the original Mojang server.
The caller retains its original single server/process/stdout collector.
"""
from __future__ import annotations

import hashlib
import os
import shutil
from pathlib import Path

from adapters.mineflayer.s31a_real_server_ci import S31ABlocked

PAPER_1218_SHA256 = "8de7c52c3b02403503d16fac58003f1efef7dd7a0256786843927fa92ee57f1e"
PAPER_1218_SIZE = 52811717
PLUGIN_JAR = "relay-s49-p1-source-dev-0.1.0-dev.jar"
CONFIG = (
    "# Disposable Paper DEV only; S49 owns single original session\n"
    "dev-enabled: true\n"
    "target-player: RelaySelf\n"
    "max-ticks: 480\n"
)


class S49P1PaperBlocked(S31ABlocked):
    """Pinned Paper/plugin bytes or sole-World startup gate absent."""


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _require_file(value: str | None) -> Path:
    if not value:
        raise S49P1PaperBlocked("explicit absolute input file required")
    path = Path(value)
    if (
        not path.is_absolute() or path.is_symlink()
        or not path.is_file()
        or any(p.is_symlink() for p in path.parents)
    ):
        raise S49P1PaperBlocked("source file must be an absolute regular file")
    return path


def stage_paper_dev(root: Path) -> dict:
    if (
        os.environ.get("S49_REAL_SERVER_CI") != "1"
        or os.environ.get("S49_BUG0_P1_PAPER_DEV_ONLY") != "1"
        or not isinstance(root, Path) or not root.is_absolute()
        or not root.is_dir()
    ):
        raise S49P1PaperBlocked("single original S49 P1 DEV gate required")
    paper = _require_file(os.environ.get("S49_P1_PAPER_JAR"))
    plugin = _require_file(os.environ.get("S49_P1_PLUGIN_JAR"))
    plugin_expected = os.environ.get("S49_P1_PLUGIN_SHA256", "")
    if (
        paper.stat().st_size != PAPER_1218_SIZE
        or _sha(paper) != PAPER_1218_SHA256
        or plugin.name != PLUGIN_JAR
        or not len(plugin_expected) == 64
        or any(x not in "0123456789abcdef" for x in plugin_expected)
        or plugin.stat().st_size < 1000
        or _sha(plugin) != plugin_expected
        or paper == plugin
    ):
        raise S49P1PaperBlocked("wrong pinned Paper or plugin bytes")
    shutil.copyfile(paper, root / "minecraft.jar")
    plugin_dir = root / "plugins"
    plugin_dir.mkdir(mode=0o700)
    shutil.copyfile(plugin, plugin_dir / PLUGIN_JAR)
    config_dir = plugin_dir / "S49P1Dev"
    config_dir.mkdir(mode=0o700)
    (config_dir / "config.yml").write_text(CONFIG, encoding="utf-8")
    return {
        "s49_dev_server": "PINNED_PAPER_1_21_8",
        "s49_paper_server_sha256": PAPER_1218_SHA256,
        "s49_p1_plugin_sha256": plugin_expected,
        "s49_p1_plugin_config": "DEV_ENABLED_ONE_WORLD",
        "original_server_collector_unchanged": True,
        "other_s49_modes_unchanged": True,
    }
