"""MP7: one Paper-owned packed-ice 5x5 floor change in disposable World.

Not a Self action, not passive measurement, not a learned model. Every World
block intervention is authenticated from real Paper console before S49 MOVE.
"""
from __future__ import annotations

import hashlib
import re
from pathlib import Path

from adapters.mineflayer.self_body_s50_l1_paper_dispatch import ForecastDispatchRejected
from adapters.mineflayer.self_body_s50_l1_paper_local import check_local_paper_config

_TOKEN = re.compile(r"[A-Za-z0-9_-]{1,128}\\Z")
_SHA = re.compile(r"[0-9a-f]{64}\\Z")


def verify_ice_config(path: Path, sha: str) -> None:
    check_local_paper_config(path, sha)
    if not path.is_absolute() or path.is_symlink() or not _SHA.fullmatch(sha):
        raise ForecastDispatchRejected("MP7 needs absolute SHA-pinned Paper config")
    data = path.read_bytes()
    if len(data) > 1_000_000 or hashlib.sha256(data).hexdigest() != sha:
        raise ForecastDispatchRejected("MP7 physical config source mismatch")
    text = data.decode("utf-8")
    for key, expected in (
        ("s50-ice-floor-dev", "true"),
        ("s50-changed-body-condition-dev", "false"),
    ):
        values = re.findall(rf"^{re.escape(key)}:\\s*([^#\\r\\n]+)", text, re.M)
        if len(values) != 1 or values[0].strip() != expected:
            raise ForecastDispatchRejected("MP7 exclusive real World surface flag invalid")


def ice_command(marker: str, mode: str) -> str:
    if (type(marker) is not str or not _TOKEN.fullmatch(marker)
            or mode != "PACKED_ICE_5X5"):
        raise ForecastDispatchRejected("MP7 invalid console-only ice floor request")
    return f"relaydevicefloor {marker} PACKED_ICE_5X5"


def attest_ice_original(raw: bytes, *, marker: str, world: str,
                        subject_uuid: str) -> dict[str, str]:
    if type(raw) is not bytes or len(raw) > 8_000_000 or any(
        type(value) is not str or not _TOKEN.fullmatch(value)
        for value in (marker, world, subject_uuid)
    ):
        raise ForecastDispatchRejected("MP7 original source/identity invalid")
    candidates = []
    for line in raw.splitlines():
        if b"S50_DEV_ICE_FLOOR_APPLIED marker_id=" not in line:
            continue
        row = dict(part.split("=", 1) for part in line.decode("utf-8").split()
                   if part.count("=") == 1)
        if row.get("marker_id") == marker:
            candidates.append(row)
    if len(candidates) != 1:
        raise ForecastDispatchRejected("MP7 no single Paper physical floor receipt")
    row = candidates[0]
    for key, expected in (
        ("world", world), ("subject_uuid", subject_uuid),
        ("mode", "PACKED_ICE_5X5"),
        ("target_material", "PACKED_ICE"),
        ("blocks_verified", "25"),
        ("status", "REAL_PAPER_WORLD_BLOCK_INTERVENTION_PRE_S49_ACTION"),
    ):
        if row.get(key) != expected:
            raise ForecastDispatchRejected("MP7 foreign or incomplete floor intervention")
    if row.get("original_material") in (None, "AIR", "PACKED_ICE"):
        raise ForecastDispatchRejected("MP7 did not change original physical surface")
    for k in ("before_action_world_tick", "center_x", "floor_y", "center_z"):
        try:
            int(row[k])
        except (KeyError, ValueError) as exc:
            raise ForecastDispatchRejected("MP7 incomplete floor geometry") from exc
    return row
