"""Q9: independent read-only diagnosis of the two U24 failed-S1 originals.

Q6 first pins seven original files to the same local inode/mtime/hash manifest.
Q9 matches Native stdin, stdout, unresolved WAL and producer Node-exit record.
No Paper motion, actual OS kill, host motor deadline or World PASS is attested.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
from pathlib import Path

from experiments.q_lane_q4_raw_native_wal_audit_dev import _parse, _position, _time
from experiments.q_lane_q6_u16_manifest_audit_dev import audit_u16_manifest
from experiments.q_lane_q7_native_three_way_audit_dev import _stdin_commands


class Q9U24Hold(ValueError):
    """Original-source content cannot support the requested narrow diagnosis."""


def _check(ok: bool, reason: str) -> None:
    if not ok:
        raise Q9U24Hold(reason)


def _native(path: Path) -> list[dict]:
    data = path.read_bytes()
    _check(0 < len(data) <= 32 * 1024 * 1024 and data.endswith(b"\n"),
           "missing/truncated original Native stdout")
    rows = [_parse(line) for line in data.splitlines()]
    _check(all(type(row) is dict and type(row.get("seq")) is int
               and type(row.get("session_id")) is str for row in rows),
           "Native stdout sequence/session malformed")
    _check(rows[0].get("type") == "adapter_started" and rows[0]["seq"] == 0
           and all(b["seq"] > a["seq"] for a, b in zip(rows, rows[1:]))
           and len({row["session_id"] for row in rows}) == 1,
           "Native startup, ordering or single session missing")
    return rows


def _unresolved_wal(path: Path) -> dict:
    envelope = _parse(path.read_bytes())
    _check(type(envelope) is dict and set(envelope) == {"body", "sha256"},
           "canonical original WAL envelope missing")
    body = envelope["body"]
    _check(type(body) is dict and body.get("schema") == 2
           and body.get("self_id") == "B"
           and type(body.get("actions")) is list
           and len(body["actions"]) == 1, "exactly one Original B v2 WAL row required")
    digest = hashlib.sha256(json.dumps(
        body, sort_keys=True, ensure_ascii=False, separators=(",", ":"),
        allow_nan=False,
    ).encode()).hexdigest()
    _check(digest == envelope["sha256"], "WAL content checksum mismatch")
    row = body["actions"][0]
    _check(type(row) is dict and row.get("capability") == "MOVE_PLACE"
           and row.get("status") == "PREPARED_UNRESOLVED"
           and type(row.get("action_id")) is str
           and bool(row["action_id"])
           and type(row.get("session_id")) is str
           and row.get("effect_seqs") is None
           and row.get("after_seq") is None, "WAL cannot claim resolved S1")
    return row


def _stop_probe_diagnosis(
    commands: list[dict], native: list[dict], stop_seq: int,
    *, expected_probes: int,
) -> dict:
    requests = [x["request_id"] for x in commands
                if x["type"] == "observe" and "request_id" in x
                and x["request_id"].startswith("p0d-move-stop-")]
    _check(len(requests) == expected_probes and len(set(requests)) == len(requests),
           "original STOP observation reservation not fully accounted")
    by_request: dict[str, dict] = {}
    for row in native:
        if row.get("type") == "observation" and row.get("kind") == "probe":
            request_id = row.get("request_id")
            _check(type(request_id) is str and request_id not in by_request,
                   "Native probe request missing/duplicated")
            by_request[request_id] = row
    _check(all(req in by_request for req in requests),
           "STOP probe request missing original Native response")
    observations = [by_request[req] for req in requests]
    _check(all(p["seq"] > stop_seq and type(p.get("snapshot")) is dict
               for p in observations)
           and all(b["seq"] > a["seq"] for a, b in zip(observations, observations[1:])),
           "STOP samples not newer than actual STOP ACK")
    ticks = [_time(p["snapshot"]) for p in observations]
    positions = [_position(p["snapshot"].get("position")) for p in observations]
    _check(all(b >= a for a, b in zip(ticks, ticks[1:]))
           and ticks[-1] - ticks[0] <= 200,
           "Native World tick regressed or left STOP horizon")
    first = 0
    reached_first = False
    stable = False
    for idx in range(1, len(ticks)):
        if not reached_first:
            if ticks[idx] - ticks[0] >= 8:
                first = idx
                reached_first = True
            continue
        if ticks[idx] - ticks[first] < 8:
            continue
        if math.dist(positions[first], positions[idx]) <= 0.06:
            stable = True
            break
        first = idx
    _check(not stable, "source already meets 8+8 stability; failure needs separate diagnosis")
    span = ticks[-1] - ticks[0]
    return {
        "probes": len(observations),
        "first_seq": observations[0]["seq"],
        "last_seq": observations[-1]["seq"],
        "native_world_first_tick": ticks[0],
        "native_world_last_tick": ticks[-1],
        "native_world_tick_span": span,
        "distinct_native_world_ticks": len(set(ticks)),
        "position_span_m": round(math.dist(positions[0], positions[-1]), 6),
        "native_8_plus_8_stability_observed": False,
        "observation_classification": (
            "INSUFFICIENT_NATIVE_TICK_ADVANCE" if span < 16
            else "NO_STABLE_8_PLUS_8_WINDOW"
        ),
        "note": "Native World clock only; not equal to Paper main-thread tick",
    }


def audit_u24_failed_s1(
    *, root: Path, manifest_path: Path, trial: str,
    expected_stop_probes: int = 24,
) -> dict:
    """Check exact original sources without issuing action or modifying files."""
    _check(trial in {"two_moves", "stop_failure"}
           and type(expected_stop_probes) is int
           and 3 <= expected_stop_probes <= 256, "Q9 trial/probe budget invalid")
    census = audit_u16_manifest(root=root, manifest_path=manifest_path, trial=trial)
    evidence = _parse(manifest_path.read_bytes())["evidence"]

    def source(role: str) -> Path:
        return root / evidence[role]["path"]

    commands = _stdin_commands(source("native_stdin"))
    native = _native(source("native_stdout"))
    wal = _unresolved_wal(source("owner_wal"))
    node = _parse(source("process_exit").read_bytes())
    host = _parse(source("host_monotonic").read_bytes())
    _check(type(node) is dict and node.get("schema") == 1
           and node.get("trial_mode") == trial
           and node.get("native_session") == native[0]["session_id"]
           and wal["session_id"] == native[0]["session_id"]
           and node.get("wal_unresolved") is True
           and node.get("s1_action_id") is None
           and node.get("s2_action_id") is None
           and node.get("s2_terminal") is False
           and node.get("real_world_dev_pass") is False
           and type(node.get("owned_pid")) is int and node["owned_pid"] > 0
           and type(node.get("returncode")) is int,
           "Original Node-exit report conflicts with unresolved S1")
    _check(type(host) is dict and host.get("schema") == 1
           and host.get("s1_forward_ms") is None
           and host.get("s1_start_stop_host_ms") is None
           and host.get("s2_forward_ms") is None
           and host.get("s2_start_stop_host_ms") is None
           and host.get("s2_original_metrics_count") == 0
           and host.get("no_real_world_pass_claim") is True,
           "failed S1 cannot claim original terminal motor metrics")
    effects = [c for c in commands if c["type"] == "effect"]
    expected = [
        (wal["action_id"] + "-look", "look"),
        (wal["action_id"] + "-start", "set_control"),
    ]
    if trial == "two_moves":
        expected.append((wal["action_id"] + "-stop", "clear_controls"))
    _check([(c.get("action_id"), c.get("effect")) for c in effects] == expected,
           "original Native stdin effect order/absence differs")
    _check(effects[0].get("pitch") == 0.0
           and type(effects[0].get("yaw")) in (int, float)
           and math.isfinite(effects[0]["yaw"])
           and effects[1].get("control") == "forward"
           and effects[1].get("state") is True,
           "unexpected original LOOK or START controls")
    acks = [row for row in native if row.get("type") == "effect_result"]
    _check(len(acks) == len(expected)
           and [(a.get("action_id"), a.get("effect"), a.get("result"), a.get("error"))
                for a in acks] == [(a, b, "applied", None) for a, b in expected]
           and all(b["seq"] > a["seq"] for a, b in zip(acks, acks[1:])),
           "original ACK missing, reordered or surplus")
    _check(all(ack["session_id"] == wal["session_id"] for ack in acks),
           "foreign Native effect session")
    result = {
        "status": "Q9_U24_FAILED_S1_SOURCE_STRUCTURE_PASS_NOT_WORLD_PASS",
        "trial": trial,
        "q6_custody": census["status"],
        "s1_action_id": wal["action_id"],
        "native_session_id": wal["session_id"],
        "start_applied": True,
        "wal_unresolved": True,
        "s2_issued": False,
        "original_node_exit_report_present": True,
        "independent_os_exit_attested": False,
        "real_world_dev_pass": False,
        "qual_go": False,
        "science_run": False,
    }
    if trial == "two_moves":
        _check(node.get("stop_fault_injection_consumed") is False,
               "nominal trial cannot consume STOP failure")
        result["stop_applied"] = True
        result.update(_stop_probe_diagnosis(
            commands, native, acks[-1]["seq"],
            expected_probes=expected_stop_probes,
        ))
    else:
        _check(node.get("stop_fault_injection_consumed") is True
               and node.get("returncode") != 0,
               "STOP failure was not consumed with nonzero original Node exit")
        _check(not any(c.get("effect") == "clear_controls" for c in commands),
               "STOP was sent despite claimed pre-STOP failure")
        result.update(stop_sent=False, stop_applied=False,
                      fault_report_consistent=True)
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, required=True)
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--trial", choices=("two_moves", "stop_failure"), required=True)
    parser.add_argument("--expected-stop-probes", type=int, default=24)
    args = parser.parse_args()
    try:
        result = audit_u24_failed_s1(
            root=args.root, manifest_path=args.manifest, trial=args.trial,
            expected_stop_probes=args.expected_stop_probes,
        )
    except (ValueError, OSError, KeyError, TypeError, IndexError) as exc:
        print("Q9_U24_HOLD: " + str(exc))
        return 2
    print(json.dumps(result, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
