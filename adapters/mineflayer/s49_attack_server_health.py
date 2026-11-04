"""Read-only Paper server-console health samples for a single tagged mob.

This is an operator-staged Minecraft DEV diagnostic, not part of S49 Action
authority or proof of damage attribution. The existing single stdout
collector writes the server log; this module NEVER reads process stdout.
"""
from __future__ import annotations

import asyncio
import re
from dataclasses import dataclass
from pathlib import Path

from adapters.mineflayer.s31a_real_server_ci import _command


class ServerHealthReadbackRejected(ValueError):
    """Native Paper health sample missing, ambiguous, or out of bounds."""


TARGET_TAG = "RelaySelfAttackTarget"
_HEALTH_LINE = re.compile(
    r"has the following entity data:\s*(-?\d+(?:\.\d+)?)(?:f|d)?(?:\s|$)",
    re.IGNORECASE,
)


@dataclass(frozen=True, slots=True)
class ServerHealthSample:
    stage: str
    target_tag: str
    source: str
    health: float
    marker_start: str
    marker_end: str
    native_line: str
    log_line_number: int
    source_independently_attested: bool = False


def parse_health_log(
    log: str, *, stage: str, nonce: str,
) -> ServerHealthSample | None:
    """Return only a uniquely bracketed single-health-command server result.

    None means the *end marker has not arrived yet*. Any other malformed
    response is an error, never an inferred zero or successful attack.
    """
    if stage not in ("before", "after") or not re.fullmatch(r"[a-z0-9]{12,32}", nonce):
        raise ServerHealthReadbackRejected("invalid single-World health sample identity")
    start = f"RSELF_HEALTH_{nonce}_{stage}_START"
    end = f"RSELF_HEALTH_{nonce}_{stage}_END"
    lines = log.splitlines()
    start_hits = [i for i, line in enumerate(lines) if f"[Server] {start}" in line]
    end_hits = [i for i, line in enumerate(lines) if f"[Server] {end}" in line]
    if not start_hits and not end_hits:
        return None  # The single stdout collector may not have flushed yet.
    if len(start_hits) != 1 or len(end_hits) > 1:
        raise ServerHealthReadbackRejected("missing or duplicated Paper health marker")
    if not end_hits:
        return None
    i, j = start_hits[0], end_hits[0]
    if j <= i:
        raise ServerHealthReadbackRejected("Paper health marker order reversed")
    excerpt = lines[i + 1:j]
    health_lines = [
        (i + k + 2, line, _HEALTH_LINE.search(line))
        for k, line in enumerate(excerpt)
        if "has the following entity data:" in line
    ]
    if len(health_lines) != 1 or health_lines[0][2] is None:
        raise ServerHealthReadbackRejected("missing or ambiguous target health in Paper source")
    number, line, match = health_lines[0]
    value = float(match.group(1))
    if not 0.0 < value <= 20.0:
        raise ServerHealthReadbackRejected("unexpected zombie health outside valid range")
    return ServerHealthSample(
        stage=stage, target_tag=TARGET_TAG,
        source="ORIGINAL_PAPER_SERVER_CONSOLE",
        health=value, marker_start=start, marker_end=end,
        native_line=line, log_line_number=number,
    )


async def sample_tagged_zombie_health(
    server: object, log_path: Path, *, stage: str, nonce: str,
) -> ServerHealthSample:
    """Query Minecraft's authoritative server NBT Health without an Action.

    The tag must be installed on the sole staged NoAI zombie. No new entity
    is spawned, no player input is changed, and no Action/grant is minted.
    """
    if not isinstance(log_path, Path) or not log_path.is_file():
        raise ServerHealthReadbackRejected("original Paper log not readable")
    if not hasattr(server, "stdin") or server.stdin is None:
        raise ServerHealthReadbackRejected("original Paper console not available")
    if stage not in ("before", "after") or not re.fullmatch(r"[a-z0-9]{12,32}", nonce):
        raise ServerHealthReadbackRejected("invalid Paper sample request")
    start = f"RSELF_HEALTH_{nonce}_{stage}_START"
    end = f"RSELF_HEALTH_{nonce}_{stage}_END"
    # Minecraft tag scopes precisely the zombie created by this DEV operator.
    # Its number must still be corroborated by complete native 1/1 coverage.
    for cmd in (
        f"say {start}",
        f"data get entity @e[type=minecraft:zombie,tag={TARGET_TAG},limit=1] Health",
        f"say {end}",
    ):
        _command(server, cmd)
    await server.stdin.drain()
    for _ in range(80):
        text = log_path.read_text(encoding="utf-8")
        result = parse_health_log(text, stage=stage, nonce=nonce)
        if result is not None:
            return result
        await asyncio.sleep(0.1)
    raise ServerHealthReadbackRejected("Paper health end marker did not complete")
