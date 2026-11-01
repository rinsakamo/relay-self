"""MP8 Paper-owned NORMAL/ICE source verification and fixed disposable seed.

This does not attest a matched causal pair by itself. An independent postrun
review must compare both full original logs and actual physical state values.
"""
from __future__ import annotations

import hashlib
import math
import re
from pathlib import Path

from adapters.mineflayer.self_body_s50_l1_paper_dispatch import ForecastDispatchRejected

SEED = "RelaySelf-MP8-Matched-Surface-20261101"
MP9_SEED = "RelaySelf-MP9-Heldout-20261101"
MP10_SEED = "RelaySelf-MP10-Typed-Correction-20261101"
SHA = re.compile(r"[0-9a-f]{64}\Z")
TOKEN = re.compile(r"[A-Za-z0-9_-]{1,128}\Z")


def set_fixed_seed(root: Path, *, seed: str = SEED) -> dict[str, str]:
    """Pre-server exclusive config modification in a throwaway owned World."""
    if seed not in (SEED, MP9_SEED, MP10_SEED):
        raise ForecastDispatchRejected("unregistered MP8/MP9/MP10 seed")
    config = root / "server.properties"
    if (not isinstance(root, Path) or not root.is_absolute()
            or root.is_symlink() or not config.is_file() or config.is_symlink()):
        raise ForecastDispatchRejected("MP8 requires an owned fresh Paper config")
    raw = config.read_text(encoding="utf-8")
    if (raw.count("level-type=minecraft:flat\n") != 1
            or "level-seed=" in raw
            or "server-ip=127.0.0.1\n" not in raw):
        raise ForecastDispatchRejected("MP8 fixed-seed setup source differs")
    raw += "level-seed=" + seed + "\n"
    config.write_text(raw, encoding="utf-8")
    return {"declared_seed": seed, "server_properties_sha256": hashlib.sha256(
        config.read_bytes()).hexdigest()}


def surface_command(marker: str, mode: str) -> str:
    if (type(marker) is not str or TOKEN.fullmatch(marker) is None
            or mode not in ("NORMAL", "ICE")):
        raise ForecastDispatchRejected("MP8 invalid surface command scope")
    return ("relaydevicefloor " + marker + " " + (
        "GRASS_BLOCK_5X5_READONLY" if mode == "NORMAL" else "PACKED_ICE_5X5"
    ))


def attest_surface_lock(raw: bytes, *, marker: str, world: str,
                        subject_uuid: str, mode: str) -> dict[str, str]:
    """Read ONE actual Paper console source line; reject echoes and foreign IDs."""
    if (type(raw) is not bytes or len(raw) > 8_000_000
            or any(type(v) is not str or TOKEN.fullmatch(v) is None
                   for v in (marker, world, subject_uuid))
            or mode not in ("NORMAL", "ICE")):
        raise ForecastDispatchRejected("MP8 invalid original/identity")
    found = []
    for source in raw.splitlines():
        if b"S50_DEV_SURFACE_LOCK marker_id=" not in source:
            continue
        row = dict(item.split("=", 1) for item in source.decode("utf-8").split()
                   if item.count("=") == 1)
        if row.get("marker_id") == marker:
            found.append(row)
    if len(found) != 1:
        raise ForecastDispatchRejected("MP8 missing unique original surface lock")
    row = found[0]
    expected = {
        "world": world, "subject_uuid": subject_uuid,
        "mode": ("GRASS_BLOCK_5X5_READONLY" if mode == "NORMAL"
                 else "PACKED_ICE_5X5"),
        "original_material": "GRASS_BLOCK",
        "target_material": "GRASS_BLOCK" if mode == "NORMAL" else "PACKED_ICE",
        "blocks_verified": "25", "on_ground": "true",
        "game_mode": "CREATIVE",
        "status": "REAL_PAPER_PRE_ACTION_SURFACE_LOCK",
    }
    if any(row.get(k) != v for k, v in expected.items()):
        raise ForecastDispatchRejected("MP8 wrong actual surface/body binding")
    for k in ("full_time", "seed", "food", "floor_x", "floor_y", "floor_z"):
        try:
            int(row[k])
        except (KeyError, ValueError) as exc:
            raise ForecastDispatchRejected("MP8 missing integer Paper state") from exc
    for k in ("x", "y", "z", "yaw", "pitch", "vx", "vy", "vz", "health"):
        try:
            f = float(row[k])
        except (KeyError, ValueError) as exc:
            raise ForecastDispatchRejected("MP8 missing physical pose") from exc
        if not math.isfinite(f):
            raise ForecastDispatchRejected("MP8 nonfinite original physical pose")
    return row
