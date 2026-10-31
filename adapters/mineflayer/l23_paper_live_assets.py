"""L23 opt-in disposable Paper asset and read-only phase marker gate.

Reuses S-owned Paper plugin strictly as an intervention in a fresh L DEV World.
It *changes metabolism* when enabled; never describe this as passive physics.
No Minecraft process is started by this module and no new motor owner exists.
"""
from __future__ import annotations

import asyncio
import hashlib
import re
import shutil
from dataclasses import dataclass
from pathlib import Path

MARKER_RE = re.compile(r"[A-Za-z0-9_-]{1,128}\Z")
SHA_RE = re.compile(r"[a-f0-9]{64}\Z")
SOURCE_BRANCH = "self/product-self-one-command-20261010"


class L23PaperBlocked(ValueError):
    """Invalid operator-owned Paper assets or missing console receipt."""


@dataclass(frozen=True, slots=True)
class L23PaperAssets:
    server_jar: Path
    server_sha256: str
    plugin_jar: Path
    plugin_sha256: str
    plugin_config: Path
    config_sha256: str


def _verified_file(path: Path, expected: str, label: str) -> bytes:
    if (
        not isinstance(path, Path)
        or not path.is_absolute()
        or path.is_symlink()
        or not path.is_file()
        or path.resolve(strict=True) != path
        or not isinstance(expected, str)
        or SHA_RE.fullmatch(expected) is None
    ):
        raise L23PaperBlocked(f"invalid absolute pinned Paper {label}")
    sha = hashlib.sha256()
    size = 0
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            size += len(chunk)
            max_bytes = 1_000_000 if label == "config" else 150_000_000
            if size > max_bytes:
                raise L23PaperBlocked(f"Paper {label} exceeds bounded bytes")
            sha.update(chunk)
    if size == 0 or sha.hexdigest() != expected:
        raise L23PaperBlocked(f"Paper {label} SHA256 mismatch")
    return path.read_bytes() if label == "config" else b""


def verify_paper_assets(assets: L23PaperAssets) -> dict[str, str]:
    if not isinstance(assets, L23PaperAssets):
        raise L23PaperBlocked("explicit Paper asset bundle required")
    _verified_file(assets.server_jar, assets.server_sha256, "server")
    _verified_file(assets.plugin_jar, assets.plugin_sha256, "plugin")
    config = _verified_file(assets.plugin_config, assets.config_sha256, "config")
    try:
        text = config.decode("utf-8")
    except UnicodeError as exc:
        raise L23PaperBlocked("invalid Paper config UTF-8") from exc
    for key, required in (
        ("dev-enabled", "true"),
        ("s50-tick-meter-dev", "true"),
        ("target-player", "RelaySelf"),
        ("minecraft-version", "1.21.8"),
    ):
        matches = re.findall(rf"^{re.escape(key)}:\s*(\S+)\s*$", text, re.M)
        if matches != [required]:
            raise L23PaperBlocked(f"missing/duplicate Paper {key}={required}")
    # The actual S-owned RelayMetabolismDev plugin refuses activation without
    # its M0.2 profile and exactly the native exhaustion + two synthetic rules.
    # Catch an incomplete operator config BEFORE consuming a disposable World.
    for key, required in (
        ("version", "M0.2"),
        ("calibration-status", "candidate_uncalibrated"),
        ("standard-food", "cooked_beef"),
    ):
        matches = re.findall(rf"^{re.escape(key)}:\s*(\S+)\s*$", text, re.M)
        if matches != [required]:
            raise L23PaperBlocked(f"invalid Paper profile {key}")
    if len(re.findall(r"^actions:\s*$", text, re.M)) != 1:
        raise L23PaperBlocked("missing/duplicate Paper actions section")
    expected_actions = {
        "BASAL", "WALK", "CROUCH", "SPRINT", "SWIM",
        "WALK_ON_WATER", "WALK_UNDERWATER", "JUMP", "JUMP_SPRINT",
        "ATTACK", "DAMAGED", "BLOCK_MINED", "REGEN", "HUNGER_EFFECT",
        "UNKNOWN", "COGNITION",
    }
    action_names = re.findall(r"^  ([A-Z_]+):\s*\{", text, re.M)
    if (
        len(action_names) != len(expected_actions)
        or set(action_names) != expected_actions
    ):
        raise L23PaperBlocked("incomplete/duplicate Paper M0.2 action roster")
    return {
        "paper_server_sha256": assets.server_sha256,
        "paper_plugin_sha256": assets.plugin_sha256,
        "paper_config_sha256": assets.config_sha256,
        "paper_profile": "ACTIVE_METABOLISM_INTERVENTION_NOT_PASSIVE",
        "qualification": "DEV_ONLY",
    }


def stage_paper_assets(assets: L23PaperAssets, root: Path) -> dict[str, str]:
    """Copy only after preflight and into a fresh disposable server root."""
    reviewed = verify_paper_assets(assets)
    if not isinstance(root, Path) or not root.is_dir() or root.is_symlink():
        raise L23PaperBlocked("fresh owned Paper World root required")
    jar = root / "minecraft.jar"
    plugin_dir = root / "plugins"
    cfg_dir = plugin_dir / "RelayMetabolismDev"
    if jar.exists() or plugin_dir.exists():
        raise L23PaperBlocked("non-fresh Paper World asset destination")
    plugin_dir.mkdir()
    cfg_dir.mkdir()
    shutil.copyfile(assets.server_jar, jar)
    shutil.copyfile(
        assets.plugin_jar, plugin_dir / "relay-metabolism-paper-dev.jar",
    )
    shutil.copyfile(assets.plugin_config, cfg_dir / "config.yml")
    return reviewed


def paper_marker(action_id: str, session_id: str) -> str:
    if not isinstance(action_id, str) or not isinstance(session_id, str):
        raise L23PaperBlocked("Paper marker requires actual native source identity")
    marker = f"{action_id}-{session_id}"
    if MARKER_RE.fullmatch(marker) is None:
        raise L23PaperBlocked("Paper marker incompatible with console command")
    return marker


async def wait_paper_line(
    path: Path, *, marker: str, kind: str, phase: str | None = None,
    timeout_s: float = 5.0,
) -> None:
    """Read only fresh plugin-emitted console lines, not an operator echo."""
    if kind not in ("M02_DEV_S50_PHASE", "S50_DEV_WAIT_BEGIN"):
        raise L23PaperBlocked("unapproved Paper observation marker")
    if kind == "M02_DEV_S50_PHASE" and phase not in (
        "PRE_FORWARD", "POST_CLEAR",
    ):
        raise L23PaperBlocked("unapproved Paper phase")
    if MARKER_RE.fullmatch(marker) is None:
        raise L23PaperBlocked("invalid Paper marker")
    loop = asyncio.get_running_loop()
    deadline = loop.time() + timeout_s
    needle = f"{kind} marker_id={marker}"
    while loop.time() < deadline:
        if path.is_file():
            # The log is an in-progress source here. Final audit uses the
            # sealed complete log after the server's normal exit.
            data = path.read_text(encoding="utf-8", errors="replace")
            for line in data.splitlines():
                if needle not in line:
                    continue
                after = line.split(needle, 1)[1]
                if (not after or after[0] != " " or
                    (phase is not None and
                     f"phase={phase}" not in after.split(" world_full_time=", 1)[0])):
                    continue
                return
        await asyncio.sleep(0.05)
    raise L23PaperBlocked(f"Paper callback marker did not arrive: {kind} {phase}")
