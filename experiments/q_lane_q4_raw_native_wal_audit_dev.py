"""Q4 independent read-only raw Native + original WAL two-trial checker.

It does NOT attest Paper, host monotonic timing, source custody, actual bot
stopping or real World DEV PASS. Never issues effects or modifies evidence.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
from pathlib import Path


class Q4EvidenceHold(ValueError):
    """The supplied raw records do not support even a bounded structural claim."""


def _pairs(items: list[tuple[str, object]]) -> dict:
    result = {}
    for key, value in items:
        if key in result:
            raise Q4EvidenceHold(f"duplicate JSON key: {key}")
        result[key] = value
    return result


def _nonfinite(value: str) -> object:
    raise Q4EvidenceHold(f"nonfinite JSON: {value}")


def _parse(data: bytes) -> object:
    try:
        return json.loads(
            data.decode("utf-8"),
            object_pairs_hook=_pairs,
            parse_constant=_nonfinite,
        )
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise Q4EvidenceHold("malformed source JSON") from exc


def _position(value: object) -> tuple[float, float, float]:
    if not isinstance(value, dict) or set(value) != {"x", "y", "z"}:
        raise Q4EvidenceHold("position missing exact x/y/z")
    v = tuple(value[k] for k in ("x", "y", "z"))
    if any(type(x) not in (float, int) or not math.isfinite(x) for x in v):
        raise Q4EvidenceHold("nonfinite position")
    return v


def _time(snapshot: dict) -> int:
    clock = snapshot.get("time")
    if not isinstance(clock, dict):
        raise Q4EvidenceHold("Native World clock missing")
    keys = set(clock)
    if keys not in (
        {"day", "time_of_day"},  # historical Q4 fixture contract
        {"day", "time_of_day", "is_day"},
        {"day", "time_of_day", "is_day", "world_age_ticks"},
    ):
        raise Q4EvidenceHold("Native World clock has unrecognized fields")
    day, tod = clock.get("day"), clock.get("time_of_day")
    if (type(day) is not int or type(tod) is not int
            or ("is_day" in clock and type(clock["is_day"]) is not bool)
            or day < 0 or not 0 <= tod < 24000):
        raise Q4EvidenceHold("invalid Native daylight time")
    if "world_age_ticks" in clock:
        age = clock["world_age_ticks"]
        if type(age) is not int or not 0 <= age <= 2**53 - 1:
            raise Q4EvidenceHold("invalid independent Native world-age tick")
        return age
    return day * 24000 + tod


def _source(wal: Path, native: Path) -> tuple[list[dict], dict[int, dict]]:
    envelope = _parse(wal.read_bytes())
    if not isinstance(envelope, dict) or set(envelope) != {"body", "sha256"}:
        raise Q4EvidenceHold("original WAL envelope required")
    body = envelope["body"]
    if not isinstance(body, dict) or body.get("schema") != 2 or not body.get("self_id"):
        raise Q4EvidenceHold("original Self v2 WAL required")
    actions = body.get("actions")
    if not isinstance(actions, list) or len(actions) != 2:
        raise Q4EvidenceHold("two terminal original PLACE rows required")
    digest = hashlib.sha256(json.dumps(
        body, ensure_ascii=False, sort_keys=True, separators=(",", ":"),
        allow_nan=False,
    ).encode("utf-8")).hexdigest()
    if digest != envelope["sha256"]:
        raise Q4EvidenceHold("original WAL checksum mismatch")
    if native.stat().st_size > 32_000_000:
        raise Q4EvidenceHold("Native raw log exceeds Q4 audit size")
    records: dict[int, dict] = {}
    previous_seq = -1
    for data in native.read_bytes().splitlines():
        item = _parse(data)
        if not isinstance(item, dict) or type(item.get("seq")) is not int:
            raise Q4EvidenceHold("Native raw envelope malformed")
        seq = item["seq"]
        if seq <= previous_seq:
            raise Q4EvidenceHold("duplicate/out-of-order Native seq")
        records[seq] = item
        previous_seq = seq
    if not records:
        raise Q4EvidenceHold("missing raw Native source")
    return actions, records


def audit_two_nominal_moves(wal: Path, native: Path) -> list[dict]:
    """Check exactly two same-session actions against unmodified Native JSONL."""
    actions, records = _source(wal, native)
    seen_action_ids: set[str] = set()
    seen_probe_requests: set[str] = set()
    session: str | None = None
    previous_last_seq = -1
    output = []
    for row in actions:
        if not isinstance(row, dict) or row.get("capability") != "MOVE_PLACE":
            raise Q4EvidenceHold("only original MOVE_PLACE rows admitted")
        if row.get("status") != "NATIVE_PLACE_MOVE_SETTLED":
            raise Q4EvidenceHold("unresolved or nonterminal original WAL")
        parent = row.get("action_id")
        sid = row.get("session_id")
        if not isinstance(parent, str) or not parent or parent in seen_action_ids:
            raise Q4EvidenceHold("duplicate/missing parent Action identity")
        if not isinstance(sid, str) or not sid or (session is not None and sid != session):
            raise Q4EvidenceHold("foreign/rejoined Native session")
        session = sid
        seen_action_ids.add(parent)

        effect_seqs = row.get("effect_seqs")
        probe_seqs = [
            row.get("initial_stop_seq"),
            row.get("first_stable_seq"),
            row.get("after_seq"),
        ]
        if (
            not isinstance(effect_seqs, list) or len(effect_seqs) != 3
            or any(type(x) is not int for x in effect_seqs + probe_seqs)
            or len(set(effect_seqs + probe_seqs)) != 6
            or not (
                previous_last_seq < row.get("probe_seq", -1)
                < effect_seqs[0] < effect_seqs[1] < effect_seqs[2]
                < probe_seqs[0] < probe_seqs[1] < probe_seqs[2]
            )
        ):
            raise Q4EvidenceHold("original Native Action/ACK/probe sequence invalid")
        for seq, suffix, effect in zip(
            effect_seqs, ("-look", "-start", "-stop"),
            ("look", "set_control", "clear_controls"), strict=True,
        ):
            message = records.get(seq)
            if (
                message is None or message.get("session_id") != sid
                or message.get("type") != "effect_result"
                or message.get("action_id") != parent + suffix
                or message.get("effect") != effect
                or message.get("result") != "applied"
                or message.get("error") is not None
            ):
                raise Q4EvidenceHold("missing/foreign/rejected raw Native effect ACK")
        probes = []
        for seq in probe_seqs:
            m = records.get(seq)
            if (
                m is None or m.get("session_id") != sid
                or m.get("type") != "observation" or m.get("kind") != "probe"
                or not isinstance(m.get("request_id"), str)
                or not isinstance(m.get("snapshot"), dict)
                or m["request_id"] in seen_probe_requests
            ):
                raise Q4EvidenceHold("missing/foreign/duplicate original Native probe")
            seen_probe_requests.add(m["request_id"])
            probes.append(m["snapshot"])
        clocks = [p.get("time") for p in probes]
        if len({isinstance(c, dict) and "world_age_ticks" in c for c in clocks}) != 1:
            raise Q4EvidenceHold("mixed native STOP clock sources")
        ticks = [_time(p) for p in probes]
        if ticks != [
            row.get("initial_stop_tick"),
            row.get("first_stable_tick"),
            row.get("settled_tick"),
        ] or not (8 <= ticks[1] - ticks[0] <= 200 and 8 <= ticks[2] - ticks[1] <= 200):
            raise Q4EvidenceHold("8+8 post-STOP tick witness missing")

        before = _position(row.get("started_position"))
        after = _position(row.get("settled_position"))
        native_after = _position(probes[2].get("position"))
        native_first = _position(probes[1].get("position"))
        displacement = math.dist(before, after)
        if (
            after != native_after or math.dist(native_first, native_after) > 0.06
            or not 0.1 <= displacement <= 1.0
            or type(row.get("displacement_m")) not in (int, float)
            or not math.isclose(row["displacement_m"], displacement, abs_tol=1e-6)
        ):
            raise Q4EvidenceHold("World displacement overshoot/no movement/not settled")
        previous_last_seq = probe_seqs[-1]
        output.append({
            "action_id": parent,
            "native_session_id": sid,
            "displacement_m": round(displacement, 6),
            "stop_to_first_ticks": ticks[1] - ticks[0],
            "first_to_settled_ticks": ticks[2] - ticks[1],
        })
    return output


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--wal", required=True, type=Path)
    parser.add_argument("--native-jsonl", required=True, type=Path)
    args = parser.parse_args()
    try:
        result = audit_two_nominal_moves(args.wal, args.native_jsonl)
    except (Q4EvidenceHold, OSError, TypeError, KeyError, ValueError) as exc:
        print(f"Q4_RAW_NATIVE_WAL_STRUCTURE_HOLD: {exc}")
        return 2
    print(json.dumps({
        "status": "Q4_RAW_NATIVE_WAL_TWO_MOVES_CPU_STRUCTURE_PASS",
        "trials": result,
        "real_world_dev_pass": False,
        "unverified": [
            "independent Paper tick/position", "800ms original host motor timing",
            "real controlled abort + owned process exit", "original producer custody",
        ],
    }, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
