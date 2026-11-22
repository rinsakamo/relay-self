"""Hostile synthetic fixtures for Q4 read-only two-MOVE Native/WAL auditor.

Synthetic success proves ONLY the local parsing/rejection logic, never World.
"""
from __future__ import annotations

import hashlib
import json

import pytest

from experiments.q_lane_q4_raw_native_wal_audit_dev import (
    Q4EvidenceHold,
    audit_two_nominal_moves,
)


def _canonical(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True,
                      separators=(",", ":"), allow_nan=False).encode()


def _fixture(tmp_path):
    rows = []
    messages = []
    for index, base in enumerate((0, 10)):
        action = f"q4-place-{index + 1}"
        start_x = index * 0.45
        after_x = start_x + 0.45
        rows.append({
            "capability": "MOVE_PLACE", "status": "NATIVE_PLACE_MOVE_SETTLED",
            "session_id": "native-A", "action_id": action,
            "probe_seq": base + 2,
            "effect_seqs": [base + 3, base + 4, base + 5],
            "initial_stop_seq": base + 6, "first_stable_seq": base + 7,
            "after_seq": base + 8,
            "initial_stop_tick": 100 + index * 100,
            "first_stable_tick": 108 + index * 100,
            "settled_tick": 116 + index * 100,
            "started_position": {"x": start_x, "y": 64, "z": 0},
            "settled_position": {"x": after_x, "y": 64, "z": 0},
            "displacement_m": 0.45,
        })
        for seq, suffix, effect in (
            (base + 3, "-look", "look"),
            (base + 4, "-start", "set_control"),
            (base + 5, "-stop", "clear_controls"),
        ):
            messages.append({
                "type": "effect_result", "session_id": "native-A", "seq": seq,
                "action_id": action + suffix, "effect": effect,
                "result": "applied", "error": None,
            })
        for j, seq in enumerate((base + 6, base + 7, base + 8)):
            messages.append({
                "type": "observation", "session_id": "native-A", "seq": seq,
                "kind": "probe", "request_id": f"probe-{index}-{j}",
                "snapshot": {
                    "time": {"day": 0, "time_of_day": 100 + index * 100 + 8*j},
                    "position": {
                        "x": after_x if j else after_x - 0.01,
                        "y": 64, "z": 0,
                    },
                },
            })
    wal_path = tmp_path / "original-physical-wal.json"
    native_path = tmp_path / "original-native-stdout.jsonl"
    return rows, messages, wal_path, native_path


def _write(rows, messages, wal_path, native_path):
    body = {"schema": 2, "self_id": "A", "actions": rows}
    wal_path.write_bytes(_canonical({
        "body": body,
        "sha256": hashlib.sha256(_canonical(body)).hexdigest(),
    }) + b"\n")
    native_path.write_bytes(b"".join(_canonical(x) + b"\n" for x in messages))


def test_two_nominal_same_native_session_structure_only(tmp_path):
    fixture = _fixture(tmp_path)
    _write(*fixture)
    result = audit_two_nominal_moves(fixture[2], fixture[3])
    assert len(result) == 2
    assert result[0]["displacement_m"] == 0.45
    assert [x["action_id"] for x in result] == ["q4-place-1", "q4-place-2"]


@pytest.mark.parametrize("tamper", [
    "old_session", "stop_rejected", "missing_stop", "duplicate_seq",
    "no_8tick", "overshoot", "late_drift", "unresolved", "replay_parent",
    "second_not_new", "foreign_probe", "bad_wal_digest",
])
def test_hostile_raw_native_and_wal_refuse(tmp_path, tamper):
    rows, messages, wal, native = _fixture(tmp_path)
    if tamper == "old_session":
        rows[1]["session_id"] = "old-native"
    elif tamper == "stop_rejected":
        messages[2]["result"] = "rejected"
    elif tamper == "missing_stop":
        del messages[2]
    elif tamper == "duplicate_seq":
        messages[3]["seq"] = messages[2]["seq"]
    elif tamper == "no_8tick":
        rows[0]["first_stable_tick"] = 105
        messages[4]["snapshot"]["time"]["time_of_day"] = 105
    elif tamper == "overshoot":
        rows[1]["settled_position"]["x"] = 1.65
        rows[1]["displacement_m"] = 1.2
        messages[-1]["snapshot"]["position"]["x"] = 1.65
    elif tamper == "late_drift":
        messages[4]["snapshot"]["position"]["x"] = -0.25
    elif tamper == "unresolved":
        rows[1]["status"] = "PREPARED_UNRESOLVED"
    elif tamper == "replay_parent":
        rows[1]["action_id"] = rows[0]["action_id"]
    elif tamper == "second_not_new":
        rows[1]["probe_seq"] = 7
    elif tamper == "foreign_probe":
        messages[-1]["session_id"] = "native-B"
    elif tamper == "bad_wal_digest":
        _write(rows, messages, wal, native)
        wal.write_bytes(wal.read_bytes().replace(b"q4-place-1", b"q4-forged-1"))
        with pytest.raises(Q4EvidenceHold):
            audit_two_nominal_moves(wal, native)
        return
    _write(rows, messages, wal, native)
    with pytest.raises(Q4EvidenceHold):
        audit_two_nominal_moves(wal, native)


def test_duplicate_keys_in_raw_ack_fail_even_when_wal_valid(tmp_path):
    rows, messages, wal, native = _fixture(tmp_path)
    _write(rows, messages, wal, native)
    records = native.read_bytes().splitlines()
    records[0] = records[0][:-1] + b',"seq":3}'
    native.write_bytes(b"\n".join(records) + b"\n")
    with pytest.raises(Q4EvidenceHold, match="duplicate JSON"):
        audit_two_nominal_moves(wal, native)


def test_duplicate_probe_request_refused(tmp_path):
    rows, messages, wal, native = _fixture(tmp_path)
    messages[-1]["request_id"] = messages[-2]["request_id"]
    _write(rows, messages, wal, native)
    with pytest.raises(Q4EvidenceHold):
        audit_two_nominal_moves(wal, native)
