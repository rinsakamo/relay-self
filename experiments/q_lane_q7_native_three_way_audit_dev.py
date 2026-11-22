"""Q7 independent three-way raw stdin ↔ stdout ↔ original WAL Q4 checker.

Read-only: verifies exact two WALK PLACE command attempts, their Native ACK
identities and correlated probes. Does NOT prove stdin delivery, Paper
position, 800ms elapsed motor time, Node exit or real World qualification.
"""
from __future__ import annotations

import argparse
import json
import math
from pathlib import Path

from experiments.q_lane_q4_raw_native_wal_audit_dev import (
    Q4EvidenceHold,
    _parse,
    _source,
    audit_two_nominal_moves,
)


class Q7ThreeWayHold(Q4EvidenceHold):
    """Actual raw attempted effects do not match Native and original WAL."""


def _check(condition: bool, why: str) -> None:
    if not condition:
        raise Q7ThreeWayHold(why)


def _stdin_commands(path: Path) -> list[dict]:
    _check(path.is_file() and 0 < path.stat().st_size <= 32_000_000,
           "original Native stdin missing or oversized")
    raw = path.read_bytes()
    _check(raw.endswith(b"\n"), "incomplete native stdin final frame")
    result = []
    for frame in raw.split(b"\n")[:-1]:
        _check(bool(frame), "empty or partial native stdin frame")
        obj = _parse(frame)
        _check(type(obj) is dict, "invalid native stdin JSON object")
        kind = obj.get("type")
        if kind == "effect":
            _check(type(obj.get("action_id")) is str
                   and type(obj.get("effect")) is str,
                   "untyped Native physical effect")
        elif kind == "observe":
            _check(set(obj) in ({"type"}, {"type", "request_id"}),
                   "unrecognized probe command fields")
            if "request_id" in obj:
                _check(type(obj["request_id"]) is str and bool(obj["request_id"]),
                       "invalid correlated Native probe request")
        elif kind == "shutdown":
            _check(set(obj) == {"type"}, "noncanonical shutdown command")
        else:
            raise Q7ThreeWayHold("unrecognized native input command")
        result.append(obj)
    return result


def audit_two_moves_three_way(
    *, wal: Path, native_stdout: Path, native_stdin: Path,
) -> list[dict]:
    """No effects issued: consume three already-frozen unmodified sources."""
    moves = audit_two_nominal_moves(wal, native_stdout)
    rows, out = _source(wal, native_stdout)
    session = rows[0]["session_id"]
    _check(0 in out and out[0].get("type") == "adapter_started"
           and out[0].get("session_id") == session,
           "original Native startup seq=0 absent")
    _check(all(x.get("session_id") == session for x in out.values()),
           "mixed native session in source transcript")
    commands = _stdin_commands(native_stdin)
    effects = [(i, obj) for i, obj in enumerate(commands)
               if obj["type"] == "effect"]
    _check(len(effects) == 6, "two MOVE_PLACE parents require six raw effects")
    expected = [(row["action_id"] + suffix, effect)
                for row in rows
                for suffix, effect in (
                    ("-look", "look"), ("-start", "set_control"),
                    ("-stop", "clear_controls"),
                )]
    _check([(x["action_id"], x["effect"]) for _, x in effects] == expected,
           "original Native effect input order or identity mismatch")
    for _, command in effects:
        effect = command["effect"]
        if effect == "look":
            _check(set(command) == {
                "type", "action_id", "effect", "yaw", "pitch",
            }, "noncanonical original LOOK")
            _check(
                all(type(command[x]) in (float, int)
                    and math.isfinite(command[x])
                    for x in ("yaw", "pitch"))
                and command["pitch"] == 0.0,
                "unsafe or nonfinite Q4 LOOK",
            )
        elif effect == "set_control":
            _check(set(command) == {
                "type", "action_id", "effect", "control", "state",
            } and command["control"] == "forward"
                and command["state"] is True,
                "only bounded forward WALK can START",
            )
        else:
            _check(set(command) == {"type", "action_id", "effect"},
                   "STOP must be original clear-all-controls")
    native_acks = [x for x in out.values() if x.get("type") == "effect_result"]
    _check(len(native_acks) == 6,
           "extra or missing original Native physical effect ACK")
    for (_, command), ack in zip(effects, native_acks, strict=True):
        _check((ack.get("action_id"), ack.get("effect"),
                ack.get("result"), ack.get("error"))
               == (command["action_id"], command["effect"], "applied", None),
               "ACK cannot be matched to original stdin command")

    seen_request_ids: set[str] = set()
    observe_index: dict[str, int] = {}
    for index, command in enumerate(commands):
        if command["type"] == "observe" and "request_id" in command:
            rid = command["request_id"]
            _check(rid not in seen_request_ids,
                   "duplicate original stdin observe request")
            seen_request_ids.add(rid)
            observe_index[rid] = index
    for j, row in enumerate(rows):
        before_request = row["probe_request_id"]
        look_index = effects[j * 3][0]
        stop_index = effects[j * 3 + 2][0]
        next_look_index = (
            effects[(j + 1) * 3][0] if j + 1 < len(rows)
            else len(commands)
        )
        _check(before_request in observe_index
               and observe_index[before_request] < look_index,
               "original S1/S2 pre-LOOK source probe not sent")
        for seq in (
            row["initial_stop_seq"], row["first_stable_seq"],
            row["after_seq"],
        ):
            response = out[seq]
            rid = response["request_id"]
            _check(
                rid in observe_index
                and stop_index < observe_index[rid] < next_look_index,
                "original STOP settling probe not requested after STOP",
            )
    return moves


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--wal", required=True, type=Path)
    parser.add_argument("--native-stdout", required=True, type=Path)
    parser.add_argument("--native-stdin", required=True, type=Path)
    args = parser.parse_args()
    try:
        moves = audit_two_moves_three_way(
            wal=args.wal, native_stdout=args.native_stdout,
            native_stdin=args.native_stdin,
        )
    except (Q7ThreeWayHold, Q4EvidenceHold, OSError, ValueError, KeyError,
            TypeError, IndexError) as exc:
        print("Q7_THREE_WAY_SOURCE_HOLD: " + str(exc))
        return 2
    print(json.dumps({
        "status": "Q7_STDIN_STDOUT_WAL_CPU_STRUCTURE_PASS",
        "moves": moves, "real_world_dev_pass": False,
        "unverified": [
            "real Node delivery", "Paper tick/actor/position",
            "host 800ms motor timeline", "separate post-START STOP-fault exit",
        ],
    }, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
