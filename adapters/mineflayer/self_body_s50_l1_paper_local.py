"""MP5 Paper-local one-shot pre-S49 shadow model binding; no World launches.

The MP3 frozen model from a previous World is the sole source. The Paper
main-thread accepted-model log is necessary before original S49 native Action.
No per-tick console RTT, no new physical Action/LLM/learning update.
"""
from __future__ import annotations

import hashlib
import math
import re
from pathlib import Path

from adapters.mineflayer.self_body_s50_l1_paper_dispatch import ForecastDispatchRejected

_TOKEN = re.compile(r"[A-Za-z0-9_-]{1,128}\Z")
_SHA = re.compile(r"[0-9a-f]{64}\Z")


def check_local_paper_config(path: Path, sha256: str) -> None:
    if (
        not isinstance(path, Path) or not path.is_absolute()
        or path.is_symlink() or not path.is_file()
        or not isinstance(sha256, str) or _SHA.fullmatch(sha256) is None
    ):
        raise ForecastDispatchRejected("MP5 requires a pinned, absolute real config")
    raw = path.read_bytes()
    if len(raw) > 1_000_000 or hashlib.sha256(raw).hexdigest() != sha256:
        raise ForecastDispatchRejected("Paper config SHA does not match original pin")
    try:
        source = raw.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise ForecastDispatchRejected("invalid UTF-8 config") from exc
    for key, required in (
        ("dev-enabled", "true"),
        ("s50-tick-meter-dev", "true"),
        ("s50-input-witness-dev", "true"),
        ("s50-paper-local-forecast-dev", "true"),
        ("s50-forecast-gate-dev", "false"),
    ):
        values = re.findall(rf"^{re.escape(key)}:\s*([^#\r\n]+)", source, re.M)
        if len(values) != 1 or values[0].strip() != required:
            raise ForecastDispatchRejected(f"MP5 rejected missing/duplicate {key}={required}")


def local_model_command(marker: str, slope: float, ticket_sha256: str) -> str:
    if (
        type(marker) is not str or _TOKEN.fullmatch(marker) is None
        or type(slope) is not float or not math.isfinite(slope)
        or slope < 0 or slope > 64
        or type(ticket_sha256) is not str or _SHA.fullmatch(ticket_sha256) is None
    ):
        raise ForecastDispatchRejected("MP5 malformed heldout model arm")
    return f"relaydevlocalmodel {marker} {slope!r} {ticket_sha256}"


def confirm_original_local_arm(
    console_bytes: bytes, *, marker: str, paper_world_uuid: str,
    subject_uuid: str, ticket_sha256: str, slope: float,
) -> None:
    """Check one full server console acceptance, NOT a console echo/host claim."""
    if not isinstance(console_bytes, bytes):
        raise ForecastDispatchRejected("MP5 requires original server stdout bytes")
    if any(_TOKEN.fullmatch(s or "") is None
           for s in (marker, paper_world_uuid, subject_uuid)):
        raise ForecastDispatchRejected("invalid MP5 target identity")
    if _SHA.fullmatch(ticket_sha256 or "") is None:
        raise ForecastDispatchRejected("MP5 missing original ticket digest")
    found = []
    for raw in console_bytes.splitlines():
        if b"S50_DEV_LOCAL_MODEL_ARM marker_id=" not in raw:
            continue
        decoded = raw.decode("utf-8", errors="strict")
        fields = dict(item.split("=", 1) for item in decoded.split()
                      if item.count("=") == 1)
        if fields.get("marker_id") == marker:
            found.append(fields)
    if len(found) != 1:
        raise ForecastDispatchRejected("MP5 no unique original Paper model arm")
    field = found[0]
    if (
        field.get("world") != paper_world_uuid
        or field.get("subject_uuid") != subject_uuid
        or field.get("ticket_sha256") != ticket_sha256
        or field.get("status") != "FROZEN_PRE_S49_ACTION"
    ):
        raise ForecastDispatchRejected("MP5 foreign or unauthenticated arm receipt")
    try:
        parsed_slope = float(field["slope"])
    except (KeyError, ValueError) as exc:
        raise ForecastDispatchRejected("MP5 missing Paper actual slope") from exc
    if not math.isfinite(parsed_slope) or parsed_slope != slope:
        raise ForecastDispatchRejected("MP5 Paper source slope not identical")
