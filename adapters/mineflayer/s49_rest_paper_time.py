"""Read-only Minecraft server-game-time witness for a bounded S49 REST hold.

Paper console text is produced by the original Java collector and is NOT
authoritative per-tick idle/held controls or a P1 fatigue transition.
"""
from __future__ import annotations

import asyncio
import re
from dataclasses import dataclass
from pathlib import Path

from adapters.mineflayer.s31a_real_server_ci import _command


class RestTimeRejected(ValueError):
    """Paper clock readback missing, ambiguous, or inconsistent."""


_GAME_TIME = re.compile(r"The time is\s+(\d+)\s*$")


@dataclass(frozen=True, slots=True)
class ServerGameTime:
    phase: str
    tick: int
    source: str
    native_line: str
    log_line_number: int
    start_marker: str
    end_marker: str
    independent_world_tick_attestation: bool = False


def parse_game_time(
    paper_log: str, *, phase: str, nonce: str,
) -> ServerGameTime | None:
    if phase not in ("before", "after") or re.fullmatch(r"[a-z0-9]{12,32}", nonce) is None:
        raise RestTimeRejected("invalid REST time source identity")
    start = f"RSELF_REST_{nonce}_{phase}_START"
    end = f"RSELF_REST_{nonce}_{phase}_END"
    lines = paper_log.splitlines()
    s = [i for i, line in enumerate(lines) if f"[Server] {start}" in line]
    e = [i for i, line in enumerate(lines) if f"[Server] {end}" in line]
    if not s and not e:
        return None
    if len(s) != 1 or len(e) > 1:
        raise RestTimeRejected("ambiguous REST Paper time delimiters")
    if not e:
        return None
    if e[0] <= s[0]:
        raise RestTimeRejected("REST time source reversed")
    subset = [(s[0]+offset+2, line, _GAME_TIME.search(line)) for offset, line
              in enumerate(lines[s[0]+1:e[0]]) if "The time is" in line]
    if len(subset) != 1 or subset[0][2] is None:
        raise RestTimeRejected("one native Paper game-time value required")
    line_no, line, m = subset[0]
    tick = int(m.group(1))
    if tick < 0:
        raise RestTimeRejected("invalid negative Paper World tick")
    return ServerGameTime(
        phase=phase, tick=tick, source="ORIGINAL_PAPER_SERVER_CONSOLE",
        native_line=line, log_line_number=line_no,
        start_marker=start, end_marker=end,
    )


async def read_game_time(
    server: object, log_path: Path, *, phase: str, nonce: str,
) -> ServerGameTime:
    """Read Paper game-time only, without issuing any Minecraft player Action."""
    if not isinstance(log_path, Path) or not log_path.is_file():
        raise RestTimeRejected("original Paper collector log required")
    if getattr(server, "stdin", None) is None or getattr(server, "returncode", None) is not None:
        raise RestTimeRejected("Paper console not available")
    if phase not in ("before", "after") or re.fullmatch(r"[a-z0-9]{12,32}", nonce) is None:
        raise RestTimeRejected("invalid REST time query")
    for command in (
        f"say RSELF_REST_{nonce}_{phase}_START",
        "time query gametime",
        f"say RSELF_REST_{nonce}_{phase}_END",
    ):
        _command(server, command)
    await server.stdin.drain()
    for _ in range(80):
        result = parse_game_time(log_path.read_text(encoding="utf-8"),
                                 phase=phase, nonce=nonce)
        if result is not None:
            return result
        await asyncio.sleep(0.1)
    raise RestTimeRejected("REST Paper game-time sample incomplete")
