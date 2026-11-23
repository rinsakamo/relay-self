"""Q7 read-only raw three-way checker hostile synthetic regressions.

All records constructed in tests are fixtures, not actual Minecraft evidence.
"""
from __future__ import annotations

import json

import pytest

from experiments.q_lane_q4_raw_native_wal_audit_dev import Q4EvidenceHold
from experiments.q_lane_q7_native_three_way_audit_dev import (
    Q7ThreeWayHold,
    audit_two_moves_three_way,
)
from test_q_lane_q4_raw_native_wal_audit_dev import _fixture, _write


def _prepare(tmp_path):
    rows, messages, wal, stdout = _fixture(tmp_path)
    sid = "native-A"
    commands = []
    for i, row in enumerate(rows):
        before_id = f"before-{i}"
        row["probe_request_id"] = before_id
        base = i * 10
        commands.extend([
            {"type": "observe", "request_id": before_id},
            {
                "type": "effect", "effect": "look",
                "action_id": row["action_id"] + "-look",
                "yaw": 1.25, "pitch": 0.0,
            },
            {
                "type": "effect", "effect": "set_control",
                "action_id": row["action_id"] + "-start",
                "control": "forward", "state": True,
            },
            {
                "type": "effect", "effect": "clear_controls",
                "action_id": row["action_id"] + "-stop",
            },
            *[
                {"type": "observe", "request_id": f"probe-{i}-{j}"}
                for j in range(3)
            ],
        ])
        messages.insert(
            0 if i == 0 else 7,
            {
                "type": "observation", "session_id": sid,
                "seq": base + 2, "kind": "probe",
                "request_id": before_id,
                "snapshot": {
                    "time": {"day": 0, "time_of_day": 95 + i * 100},
                    "position": {"x": i * 0.45, "y": 64, "z": 0},
                },
            },
        )
    messages.insert(0, {
        "type": "adapter_started", "session_id": sid, "seq": 0,
    })
    stdin = tmp_path / "original-native-stdin.jsonl"
    return rows, messages, wal, stdout, stdin, commands


def _save(rows, messages, wal, stdout, stdin, commands):
    _write(rows, messages, wal, stdout)
    stdin.write_bytes(b"".join(
        json.dumps(cmd, sort_keys=True, separators=(",", ":")).encode() + b"\n"
        for cmd in commands
    ))


def _audit(files):
    rows, messages, wal, stdout, stdin, commands = files
    _save(rows, messages, wal, stdout, stdin, commands)
    return audit_two_moves_three_way(
        wal=wal, native_stdout=stdout, native_stdin=stdin,
    )


def test_two_original_place_actions_correlate_three_sources(tmp_path):
    results = _audit(_prepare(tmp_path))
    assert [m["action_id"] for m in results] == ["q4-place-1", "q4-place-2"]
    assert all(m["displacement_m"] == 0.45 for m in results)


@pytest.mark.parametrize("fault", [
    "extra_attack", "start_wrong_control", "start_not_true",
    "look_wrong_pitch", "stop_wrong_id", "missing_stop",
    "swapped_start_stop", "before_probe_missing", "after_probe_early",
    "duplicate_observe", "source_startup_missing", "foreign_startup",
    "foreign_seq", "rejected_stop", "extra_native_ack",
    "wrong_action_echo", "changed_wal_action", "stdin_shutdown_effect",
    "duplicate_effect_input", "truncated_stdin", "nan_yaw",
])
def test_forged_or_incomplete_three_way_sources_hold(tmp_path, fault):
    files = _prepare(tmp_path)
    rows, messages, wal, stdout, stdin, commands = files
    if fault == "extra_attack":
        commands.append({
            "type": "effect", "effect": "attack_entity",
            "action_id": "foreign-attack", "entity_id": 7,
        })
    elif fault == "start_wrong_control":
        commands[2]["control"] = "back"
    elif fault == "start_not_true":
        commands[2]["state"] = False
    elif fault == "look_wrong_pitch":
        commands[1]["pitch"] = 0.2
    elif fault == "stop_wrong_id":
        commands[3]["action_id"] = "forged-stop"
    elif fault == "missing_stop":
        del commands[3]
    elif fault == "swapped_start_stop":
        commands[2], commands[3] = commands[3], commands[2]
    elif fault == "before_probe_missing":
        del commands[0]
    elif fault == "after_probe_early":
        commands[3], commands[4] = commands[4], commands[3]
    elif fault == "duplicate_observe":
        commands.append({"type": "observe", "request_id": "probe-1-2"})
    elif fault == "source_startup_missing":
        del messages[0]
    elif fault == "foreign_startup":
        messages[0]["session_id"] = "foreign-Node"
    elif fault == "foreign_seq":
        messages[-1]["session_id"] = "foreign-Node"
    elif fault == "rejected_stop":
        messages[4]["result"] = "rejected"
    elif fault == "extra_native_ack":
        messages.append({
            "type": "effect_result", "session_id": "native-A",
            "seq": 19, "action_id": "out-of-band-attack",
            "effect": "attack_entity", "result": "applied", "error": None,
        })
    elif fault == "wrong_action_echo":
        messages[3]["action_id"] = "forged-look"
    elif fault == "changed_wal_action":
        rows[1]["action_id"] = rows[0]["action_id"]
    elif fault == "stdin_shutdown_effect":
        commands.append({"type": "shutdown", "action_id": "fake"})
    elif fault == "duplicate_effect_input":
        commands.append(dict(commands[1]))
    elif fault == "nan_yaw":
        commands[1]["yaw"] = float("nan")
    _save(*files)
    if fault == "truncated_stdin":
        stdin.write_bytes(stdin.read_bytes().rstrip(b"\n"))
    with pytest.raises((Q7ThreeWayHold, Q4EvidenceHold, ValueError)):
        audit_two_moves_three_way(
            wal=wal, native_stdout=stdout, native_stdin=stdin,
        )


def test_no_real_world_claim_or_physical_side_effect(tmp_path):
    rows, messages, wal, stdout, stdin, commands = _prepare(tmp_path)
    _save(rows, messages, wal, stdout, stdin, commands)
    original = [p.read_bytes() for p in (wal, stdout, stdin)]
    audit_two_moves_three_way(
        wal=wal, native_stdout=stdout, native_stdin=stdin,
    )
    assert original == [p.read_bytes() for p in (wal, stdout, stdin)]
