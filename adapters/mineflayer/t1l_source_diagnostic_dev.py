"""T1l offline/DEV source freshness diagnosis using ONLY the Node clock.

The causal-age upper bound includes challenge delivery, Paper callback, return
transport, Node queue and evaluation. It is NOT a one-way network latency.
No source refusal is repaired, replayed or promoted to admitted.
"""
from __future__ import annotations

import argparse
import json
from collections import Counter
from pathlib import Path

AGE_LIMIT_NS = 150_000_000
CHALLENGE_CAP = 2400


class ContinuityRejected(ValueError):
    """Corrupt, foreign or non-monotone original Paper source."""


def _integer(value, name, *, allow_none=False):
    if allow_none and value is None:
        return None
    if type(value) is not str or not value.isascii() or not value.isdecimal():
        raise ContinuityRejected(f"invalid {name}")
    return int(value)


def analyze_paper_records(records, *, session_id=None):
    """Describe the source, including rejected frames; never certify it.

    Input is original Node-originated JSONL objects, NOT reconstructed ticks.
    The first Paper sample can be a startup NONE, but cannot become ADMITTED.
    Other native effect frames may occur between Paper sequences.
    """
    count = 0
    statuses = Counter()
    reasons = Counter()
    violations = []
    maxima = {"causal_upper_ms": None, "challenge_to_receive_ms": None,
              "receive_to_complete_ms": None, "node_queue_ms": None,
              "node_evaluation_ms": None}
    samples = []
    prev = None
    native_previous_seq = None
    native_sequenced_records = 0
    observed_session = session_id
    for record in records:
        if not isinstance(record, dict):
            raise ContinuityRejected("native journal record not an object")
        native_seq = record.get("seq")
        if type(native_seq) is int:
            native_sequenced_records += 1
            if native_previous_seq is not None:
                if native_seq <= native_previous_seq:
                    violations.append("native_stream_seq_reordered_or_duplicate")
                elif native_seq != native_previous_seq + 1:
                    violations.append("native_stream_seq_gap")
            native_previous_seq = native_seq
        if record.get("type") != "paper_snapshot":
            continue
        count += 1
        if type(record.get("seq")) is not int or record["seq"] < 0:
            raise ContinuityRejected("invalid native source seq")
        if type(record.get("session_id")) is not str:
            raise ContinuityRejected("missing native session")
        if observed_session is None:
            observed_session = record["session_id"]
        if record["session_id"] != observed_session:
            violations.append("foreign_session")
        d = record.get("data")
        if not isinstance(d, dict) or not isinstance(d.get("snapshot"), dict):
            raise ContinuityRejected("Paper payload absent")
        snap = d["snapshot"]
        if (type(snap.get("index")) is not int or type(snap.get("tick")) is not int
                or type(snap.get("world_tick")) is not int):
            raise ContinuityRejected("malformed Paper index or tick")
        if snap["index"] < 1 or snap["index"] > CHALLENGE_CAP:
            violations.append("challenge_index_out_of_bounds")
        if prev:
            if record["seq"] <= prev[0]:
                violations.append("source_seq_reordered_or_duplicate")
            if (snap["index"] != prev[1] + 1
                    or snap["tick"] != prev[2] + 1
                    or snap["world_tick"] != prev[3] + 1):
                violations.append("paper_index_or_worldtick_gap")
            if (snap.get("boot"), snap.get("world"), snap.get("player")) != prev[4]:
                violations.append("paper_identity_changed")
        prev = (record["seq"], snap["index"], snap["tick"], snap["world_tick"],
                (snap.get("boot"), snap.get("world"), snap.get("player")))
        status = d.get("status")
        statuses[str(status)] += 1
        reasons[str(d.get("reason"))] += 1
        try:
            sent = _integer(d.get("challenge_sent_ns"), "challenge", allow_none=True)
            received = _integer(d.get("received_ns"), "received")
            started = _integer(d.get("evaluation_start_ns"), "evaluation start")
            completed = _integer(d.get("evaluation_completed_ns"), "completed")
            upper = _integer(d.get("age_upper_ns"), "age upper", allow_none=True)
            lower = _integer(d.get("age_lower_ns"), "age lower")
        except ContinuityRejected:
            violations.append("invalid_node_clock_fields")
            continue
        if not 0 <= received <= started <= completed or lower != completed - received:
            violations.append("node_clock_order_or_lower_bound")
            continue
        elapsed = {
            "receive_to_complete_ms": (completed - received) / 1e6,
            "node_queue_ms": (started - received) / 1e6,
            "node_evaluation_ms": (completed - started) / 1e6,
        }
        if sent is not None:
            if sent > received:
                violations.append("challenge_after_receive")
                continue
            elapsed["challenge_to_receive_ms"] = (received - sent) / 1e6
            elapsed["causal_upper_ms"] = (completed - sent) / 1e6
            if upper is not None and upper != completed - sent:
                violations.append("causal_age_bound_inconsistent")
        if status == "ADMITTED":
            if upper is None or sent is None or upper >= AGE_LIMIT_NS:
                violations.append("false_admitted_over_age_limit")
        for key, value in elapsed.items():
            maxima[key] = value if maxima[key] is None else max(maxima[key], value)
        if upper is not None and upper >= AGE_LIMIT_NS:
            samples.append({
                "seq": record["seq"], "index": snap["index"],
                "server_tick": snap["tick"], "world_tick": snap["world_tick"],
                "status": status, "reason": d.get("reason"),
                **{k: round(v, 6) for k, v in elapsed.items()},
            })
    return {
        "classification": "T1L_BOUNDED_NODE_CLOCK_SOURCE_DIAGNOSTIC_DEV",
        "qualification": False, "source_independently_authenticated": False,
        "age_limit_ms_unchanged": 150, "challenge_limit_unchanged": CHALLENGE_CAP,
        "source_session": observed_session, "paper_frames": count,
        "native_sequenced_records": native_sequenced_records,
        "native_last_seq": native_previous_seq,
        "statuses": dict(statuses), "reasons": dict(reasons),
        "maxima_ms": {k: round(v, 6) if v is not None else None
                      for k, v in maxima.items()},
        "over_150ms": samples,
        "source_violations": sorted(set(violations)),
        "source_continuous": bool(count) and not violations,
        "normal_20tps_claim": False, "one_way_latency_known": False,
        "p1_wait_qualified": False,
    }


def read_jsonl(path: Path):
    with path.open(encoding="utf-8") as stream:
        for line in stream:
            if line.strip():
                yield json.loads(line)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--native-jsonl", type=Path, required=True)
    parser.add_argument("--session-id")
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    result = analyze_paper_records(read_jsonl(args.native_jsonl),
                                   session_id=args.session_id)
    output = json.dumps(result, indent=2, sort_keys=True) + "\n"
    if args.output:
        if args.output.exists():
            parser.error("do not overwrite previous diagnostic originals")
        args.output.write_text(output, encoding="utf-8")
    else:
        print(output, end="")
    return int(not result["source_continuous"])


if __name__ == "__main__":
    raise SystemExit(main())
