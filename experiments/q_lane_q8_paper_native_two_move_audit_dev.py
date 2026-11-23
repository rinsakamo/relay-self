"""Q8 independent read-only Paper movement corroboration for Q4 two-MOVE DEV.

Requires *original* Paper process log + the Q7 Native stdin/stdout/WAL
triangle. Paper main-thread ticks and Native world day ticks are never
numerically compared; only within-source order, geometry and independent
8+8 tick windows are corroborated. This is NOT action causality.
"""
from __future__ import annotations

import argparse
import json
import math
import re
import uuid
from dataclasses import dataclass
from pathlib import Path

from experiments.q_lane_q4_raw_native_wal_audit_dev import _position, _source
from experiments.q_lane_q7_native_three_way_audit_dev import audit_two_moves_three_way


class Q8PaperHold(ValueError):
    """Paper source cannot independently corroborate the two original moves."""


_READY = re.compile(
    r"P0D_RESIDENT_READY boot=([0-9a-f-]{36}) "
    r"source=PAPER_MAIN_THREAD version=1"
)
_TOKEN = "P0D_RESIDENT event="
_FIELDS = {"event", "boot", "tick", "world", "actor", "name", "x", "y", "z", "source"}


def _check(ok: bool, why: str) -> None:
    if not ok:
        raise Q8PaperHold(why)


def _uuid(value: object) -> str:
    _check(type(value) is str, "Paper identity not string")
    try:
        canonical = str(uuid.UUID(value))
    except ValueError as exc:
        raise Q8PaperHold("invalid Paper UUID") from exc
    _check(value == canonical, "noncanonical Paper UUID")
    return canonical


@dataclass(frozen=True)
class PaperPoint:
    event: str
    boot: str
    world: str
    actor: str
    name: str
    tick: int
    line: int
    position: tuple[float, float, float]


def _read_paper(path: Path) -> list[PaperPoint]:
    _check(path.is_file() and 0 < path.stat().st_size <= 32_000_000,
           "missing or oversized original Paper log")
    raw = path.read_bytes()
    _check(raw.endswith(b"\n"), "Paper log contains an incomplete final line")
    try:
        source = raw.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise Q8PaperHold("Paper process log is not UTF-8") from exc
    boot: list[str] = []
    points: list[PaperPoint] = []
    for lineno, line in enumerate(source.splitlines(), start=1):
        match = _READY.search(line)
        if match is not None:
            boot.append(_uuid(match.group(1)))
        if _TOKEN not in line:
            continue
        tokens = line[line.index(_TOKEN):].split()
        fields: dict[str, str] = {}
        for token in tokens[1:]:
            _check(token.count("=") == 1, "malformed Paper main-thread field")
            key, val = token.split("=", 1)
            _check(key not in fields, "duplicate Paper main-thread field")
            fields[key] = val
        _check(set(fields) == _FIELDS and fields["source"] == "PAPER_MAIN_THREAD"
               and fields["event"] in {"JOIN", "QUIT", "MOVE", "PRESENT"},
               "unexpected Paper event fields")
        try:
            tick = int(fields["tick"])
            pos = tuple(float(fields[k]) for k in ("x", "y", "z"))
        except (ValueError, OverflowError) as exc:
            raise Q8PaperHold("invalid Paper number") from exc
        _check(str(tick) == fields["tick"] and tick >= 0
               and all(math.isfinite(x) for x in pos),
               "Paper tick or position noncanonical/nonfinite")
        _check(re.fullmatch(r"[A-Za-z0-9_]{3,16}", fields["name"]) is not None,
               "invalid Paper actor name")
        points.append(PaperPoint(
            fields["event"], _uuid(fields["boot"]), _uuid(fields["world"]),
            _uuid(fields["actor"]), fields["name"], tick, lineno, pos,
        ))
    _check(len(boot) == 1 and bool(points),
           "exactly one Paper boot marker and actor stream required")
    _check(all(p.boot == boot[0] for p in points),
           "Paper event not from one original boot")
    _check(all(b.tick >= a.tick and b.line > a.line
               for a, b in zip(points, points[1:])),
           "Paper tick/line ordering inconsistent")
    _check(len({p.world for p in points}) == 1,
           "Paper event world changed mid-session")
    joins = [p for p in points if p.event == "JOIN"]
    _check(len(joins) == 1
           and len({p.actor for p in points}) == 1
           and len({p.name for p in points}) == 1
           and joins[0] == points[0]
           and all(p.event not in {"QUIT", "JOIN"} for p in points[1:]),
           "single Paper actor must remain online for both MOVE actions")
    return points


def _match_window(
    people: list[PaperPoint], start_index: int,
    baseline: tuple[float, float, float],
    native: tuple[tuple[float, float, float], ...],
) -> tuple[int, tuple[PaperPoint, PaperPoint, PaperPoint]]:
    last = len(people)
    for i in range(start_index, last):
        stop = people[i]
        if stop.event not in {"MOVE", "PRESENT"}:
            continue
        distance = math.dist(baseline, stop.position)
        if not 0.1 <= distance <= 1.0 or math.dist(stop.position, native[0]) > 0.25:
            continue
        # Require a real independently observed Paper MOVE in this action
        # region, not just three stale PRESENT echoes.
        if not any(e.event == "MOVE" for e in people[start_index:i + 1]):
            continue
        for j in range(i + 1, last):
            first = people[j]
            if (
                first.event not in {"MOVE", "PRESENT"}
                or not 8 <= first.tick - stop.tick <= 200
                or math.dist(first.position, native[1]) > 0.16
            ):
                continue
            for k in range(j + 1, last):
                settled = people[k]
                if (
                    settled.event in {"MOVE", "PRESENT"}
                    and 8 <= settled.tick - first.tick <= 200
                    and math.dist(settled.position, native[2]) <= 0.12
                    and math.dist(first.position, settled.position) <= 0.06
                ):
                    return k, (stop, first, settled)
    raise Q8PaperHold("fresh stable Paper 8+8 move window unavailable")


def audit_two_moves_paper(
    *, wal: Path, native_stdout: Path, native_stdin: Path,
    paper_log: Path,
) -> list[dict]:
    """Require Paper geometries for exactly two distinct live original Actions."""
    moves = audit_two_moves_three_way(
        wal=wal, native_stdout=native_stdout, native_stdin=native_stdin,
    )
    rows, native = _source(wal, native_stdout)
    people = _read_paper(paper_log)
    baseline = people[0].position
    cursor = 1
    previous_tick = -1
    output = []
    for index, row in enumerate(rows):
        probes = tuple(
            _position(native[seq]["snapshot"]["position"])
            for seq in (
                row["initial_stop_seq"], row["first_stable_seq"],
                row["after_seq"],
            )
        )
        cursor, window = _match_window(people, cursor, baseline, probes)
        _check(window[0].tick > previous_tick,
               "Paper second action reuses or precedes first settled window")
        previous_tick = window[-1].tick
        output.append({
            "action_id": row["action_id"],
            "paper_boot": window[0].boot,
            "paper_actor_uuid": window[0].actor,
            "paper_world_uuid": window[0].world,
            "paper_ticks": [x.tick for x in window],
            "paper_lines": [x.line for x in window],
            "paper_displacement_m": round(
                math.dist(baseline, window[-1].position), 6,
            ),
            "native_displacement_m": moves[index]["displacement_m"],
        })
        baseline = window[-1].position
        cursor += 1
    return output


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--wal", type=Path, required=True)
    parser.add_argument("--native-stdout", type=Path, required=True)
    parser.add_argument("--native-stdin", type=Path, required=True)
    parser.add_argument("--paper-log", type=Path, required=True)
    args = parser.parse_args()
    try:
        windows = audit_two_moves_paper(
            wal=args.wal, native_stdout=args.native_stdout,
            native_stdin=args.native_stdin, paper_log=args.paper_log,
        )
    except (Q8PaperHold, ValueError, OSError, KeyError, TypeError,
            IndexError) as exc:
        print(f"Q8_ORIGINAL_PAPER_NATIVE_HOLD: {exc}")
        return 2
    print(json.dumps({
        "status": "Q8_PAPER_NATIVE_TWO_MOVES_CPU_CORRELATED",
        "paper_windows": windows,
        "real_world_dev_pass": False,
        "causal_native_to_paper": False,
        "host_motor_time_audited": False,
        "stop_fault_node_exit_audited": False,
    }, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
