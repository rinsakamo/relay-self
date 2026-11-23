"""Q10: independent U24 Paper main-thread tick vs Native STOP clock diagnostic.

Read-only. Run on the ORIGINAL same-inode seven-source U24 archive. Reports
distinct clock progress for two independent producer streams without assuming
absolute tick equality or causation. Never grants a World/QUAL/SCIENCE PASS.
"""
from __future__ import annotations

import argparse
import json
import math
import re
import uuid
from pathlib import Path

from experiments.q_lane_q4_raw_native_wal_audit_dev import _parse
from experiments.q_lane_q9_u24_s1_stop_diagnostic_dev import audit_u24_failed_s1

_READY = re.compile(
    r"P0D_RESIDENT_READY boot=([0-9a-f-]{36}) "
    r"source=PAPER_MAIN_THREAD version=1"
)
_TAG = "P0D_RESIDENT event="
_FIELDS = {"event", "boot", "tick", "world", "actor", "name", "x", "y", "z", "source"}


class Q10ClockHold(ValueError):
    """Paper main-thread or local custody evidence is not valid for comparison."""


def _require(condition: bool, reason: str) -> None:
    if not condition:
        raise Q10ClockHold(reason)


def _uuid(value: str) -> str:
    try:
        canonical = str(uuid.UUID(value))
    except (ValueError, AttributeError, TypeError) as exc:
        raise Q10ClockHold("Paper UUID malformed") from exc
    _require(canonical == value, "Paper UUID noncanonical")
    return canonical


def _paper_timeline(path: Path) -> dict:
    raw = path.read_bytes()
    # Paper’s console may redraw its prompt after the last complete log line.
    _require(0 < len(raw) <= 32 * 1024 * 1024
             and raw.endswith((b"\n", b"\n> ")),
             "original Paper stream empty, truncated or oversized")
    try:
        source = raw.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise Q10ClockHold("Paper stream not UTF-8") from exc
    boot_markers: list[str] = []
    records: list[dict] = []
    for line_no, line in enumerate(source.splitlines(), 1):
        match = _READY.search(line)
        if match:
            boot_markers.append(_uuid(match.group(1)))
        if _TAG not in line:
            continue
        fields: dict[str, str] = {}
        for token in line[line.index(_TAG):].split()[1:]:
            _require(token.count("=") == 1, "Paper field malformed")
            key, val = token.split("=", 1)
            _require(key not in fields, "Paper duplicate field")
            fields[key] = val
        _require(set(fields) == _FIELDS and fields["source"] == "PAPER_MAIN_THREAD"
                 and fields["event"] in {"JOIN", "QUIT", "MOVE", "PRESENT"},
                 "Paper main-thread event unrecognized")
        try:
            tick = int(fields["tick"])
            pos = tuple(float(fields[x]) for x in ("x", "y", "z"))
        except (ValueError, OverflowError) as exc:
            raise Q10ClockHold("Paper tick/position malformed") from exc
        _require(str(tick) == fields["tick"] and tick >= 0
                 and all(math.isfinite(p) for p in pos),
                 "Paper tick or coordinates invalid")
        records.append({
            "event": fields["event"],
            "tick": tick,
            "line": line_no,
            "boot": _uuid(fields["boot"]),
            "world": _uuid(fields["world"]),
            "actor": _uuid(fields["actor"]),
            "name": fields["name"],
            "position": pos,
        })
    _require(len(boot_markers) == 1 and bool(records)
             and records[0]["event"] == "JOIN",
             "one actual Paper boot and initial player JOIN required")
    _require(all(x["boot"] == boot_markers[0] for x in records)
             and len({x["world"] for x in records}) == 1
             and len({x["actor"] for x in records}) == 1
             and len({x["name"] for x in records}) == 1,
             "Paper boot/world/player replaced")
    _require(len([x for x in records if x["event"] == "JOIN"]) == 1
             and len([x for x in records if x["event"] == "QUIT"]) <= 1,
             "Paper player reJOIN or duplicate QUIT")
    _require(all(b["tick"] >= a["tick"] and b["line"] > a["line"]
                 for a, b in zip(records, records[1:])),
             "Paper tick regression or line reordering")
    quits = [i for i, x in enumerate(records) if x["event"] == "QUIT"]
    _require(not quits or quits[0] == len(records) - 1,
             "Paper player emitted positions after terminal QUIT")
    observations = [x for x in records if x["event"] in {"PRESENT", "MOVE"}]
    _require(bool(observations), "no independently sampled Paper tick")
    coords = [x["position"] for x in observations]
    return {
        "paper_actor_uuid": records[0]["actor"],
        "paper_world_uuid": records[0]["world"],
        "paper_boot_uuid": boot_markers[0],
        "paper_join_tick": records[0]["tick"],
        "paper_last_position_tick": observations[-1]["tick"],
        "paper_observed_tick_span": observations[-1]["tick"] - records[0]["tick"],
        "paper_distinct_sample_ticks": len({x["tick"] for x in observations}),
        "paper_move_events": sum(x["event"] == "MOVE" for x in records),
        "paper_position_endpoint_span_m": round(math.dist(
            coords[0], coords[-1],
        ), 6),
        "paper_player_quit_recorded": bool(quits),
    }


def audit_u24_two_source_clock_progress(
    *, root: Path, manifest_path: Path, trial: str = "two_moves",
    expected_stop_probes: int = 24,
) -> dict:
    """Combine independent Q9 STOP finding and read-only Paper timeline."""
    _require(trial in {"two_moves", "stop_failure"}, "trial mode not supported")
    q9 = audit_u24_failed_s1(
        root=root, manifest_path=manifest_path, trial=trial,
        expected_stop_probes=expected_stop_probes,
    )
    envelope = _parse(manifest_path.read_bytes())
    paper = _paper_timeline(root / envelope["evidence"]["paper_ticks"]["path"])
    result = {
        "status": "Q10_INDEPENDENT_NATIVE_PAPER_CLOCK_PROGRESS_CPU_DIAGNOSTIC",
        "trial": trial,
        "q9_original_s1_status": q9["status"],
        "paper": paper,
        "real_world_dev_pass": False,
        "world_stop_settled": False,
        "cross_clock_absolute_tick_equivalence": False,
        "paper_progress_during_exact_stop_probes_attested": False,
    }
    if trial == "two_moves":
        native_span = q9["native_world_tick_span"]
        paper_span = paper["paper_observed_tick_span"]
        if native_span < 16 and paper_span >= 16:
            classification = "NATIVE_STOP_CLOCK_SHORT_WITH_PAPER_RUN_PROGRESS"
        elif native_span < 16:
            classification = "NATIVE_STOP_CLOCK_SHORT_PAPER_PROGRESS_INCONCLUSIVE"
        else:
            classification = "NATIVE_ADVANCED_BUT_NO_SETTLED_8_PLUS_8"
        result["native"] = {
            "stop_clock_basis": q9["native_clock_basis"],
            "stop_probe_count": q9["probes"],
            "native_stop_tick_span": native_span,
            "native_distinct_stop_ticks": q9["distinct_native_world_ticks"],
            "native_stop_endpoint_displacement_m": q9["position_span_m"],
        }
        result["classification"] = classification
        result["next_action"] = (
            "Check source clock/gamerule and exact Native STOP samples; "
            "do not expand probe quota without original measurement"
            if native_span < 16 else
            "Review per-probe position drift and tick-stable candidates; "
            "do not infer STOP success from applied ACK"
        )
    else:
        result["classification"] = "STOP_FAILURE_CAPTURE_REQUIRES_OS_EXIT_REVIEW"
        result["original_node_exit_report_present"] = True
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, required=True)
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--trial", choices=("two_moves", "stop_failure"),
                        default="two_moves")
    parser.add_argument("--expected-stop-probes", type=int, default=24)
    args = parser.parse_args()
    try:
        result = audit_u24_two_source_clock_progress(
            root=args.root, manifest_path=args.manifest,
            trial=args.trial, expected_stop_probes=args.expected_stop_probes,
        )
    except (Q10ClockHold, ValueError, TypeError, OSError, KeyError,
            IndexError) as exc:
        print(f"Q10_U24_CLOCK_PROGRESS_HOLD: {exc}")
        return 2
    print(json.dumps(result, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
