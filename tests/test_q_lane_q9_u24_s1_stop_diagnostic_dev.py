"""Q9 hostile CPU fixtures: no actual Minecraft/Node/llama or source authentication."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest

from experiments.q_lane_q9_u24_s1_stop_diagnostic_dev import (
    Q9U24Hold,
    audit_u24_failed_s1,
)


ACTION = "stage27c-B-7"
SESSION = "native-original-s1"
ROLES = {
    "native_stdout": "original-native-stdout.jsonl",
    "native_stdin": "original-native-stdin.jsonl",
    "paper_ticks": "original-paper-process.log",
    "owner_wal": "original-owner-wal.json",
    "owner_cognition": "original-owner-persistent-cognition.json",
    "host_monotonic": "original-host-monotonic.json",
    "process_exit": "original-node-process-exit.json",
}


def _write_json(path: Path, value: object) -> None:
    path.write_text(json.dumps(value, sort_keys=True) + "\n")


def _make_source(root: Path, trial: str, *, stop_ticks=None):
    """A same-inode original-style source set; not real World evidence."""
    original = [dict(type="adapter_started", seq=0, session_id=SESSION)]
    stdin = [dict(type="observe", request_id="pre-first")]
    original.append(dict(
        type="observation", kind="probe", seq=1, session_id=SESSION,
        request_id="pre-first", snapshot={
            "time": {"day": 0, "time_of_day": 100, "is_day": True},
            "position": {"x": 0.0, "y": 64.0, "z": 0.0},
        },
    ))
    effects = [
        dict(type="effect", action_id=ACTION + "-look",
             effect="look", yaw=0.0, pitch=0.0),
        dict(type="effect", action_id=ACTION + "-start",
             effect="set_control", control="forward", state=True),
    ]
    if trial == "two_moves":
        effects.append(dict(type="effect", action_id=ACTION + "-stop",
                            effect="clear_controls"))
    for index, row in enumerate(effects, start=2):
        stdin.append(row)
        original.append(dict(type="effect_result", seq=index, session_id=SESSION,
                             action_id=row["action_id"], effect=row["effect"],
                             result="applied", error=None))
    if trial == "two_moves":
        if stop_ticks is None:
            stop_ticks = [100] * 24
        for i, tick in enumerate(stop_ticks):
            request = "p0d-move-stop-" + str(i)
            stdin.append(dict(type="observe", request_id=request))
            original.append(dict(
                type="observation", kind="probe", seq=5 + i,
                session_id=SESSION, request_id=request, snapshot={
                    "time": {"day": 0, "time_of_day": tick, "is_day": True},
                    "position": {"x": 0.42, "y": 64.0, "z": 0.0},
                },
            ))
    (root / ROLES["native_stdin"]).write_bytes(
        b"".join((json.dumps(x) + "\n").encode() for x in stdin),
    )
    (root / ROLES["native_stdout"]).write_bytes(
        b"".join((json.dumps(x) + "\n").encode() for x in original),
    )
    body = {"schema": 2, "self_id": "B", "actions": [{
        "action_id": ACTION, "capability": "MOVE_PLACE", "status": "PREPARED_UNRESOLVED",
        "session_id": SESSION, "effect_seqs": None, "after_seq": None,
    }]}
    wal = {
        "body": body,
        "sha256": hashlib.sha256(json.dumps(
            body, sort_keys=True, ensure_ascii=False,
            separators=(",", ":"), allow_nan=False,
        ).encode()).hexdigest(),
    }
    _write_json(root / ROLES["owner_wal"], wal)
    _write_json(root / ROLES["owner_cognition"], {"retained": "test"})
    _write_json(root / ROLES["host_monotonic"], {
        "schema": 1,
        "s1_forward_ms": None, "s1_start_stop_host_ms": None,
        "s2_forward_ms": None, "s2_start_stop_host_ms": None,
        "s2_original_metrics_count": 0, "no_real_world_pass_claim": True,
    })
    _write_json(root / ROLES["process_exit"], {
        "schema": 1, "trial_mode": trial, "native_session": SESSION,
        "owned_pid": 311, "returncode": -15, "wal_unresolved": True,
        "s1_action_id": None, "s2_action_id": None, "s2_terminal": False,
        "real_world_dev_pass": False,
        "stop_fault_injection_consumed": trial == "stop_failure",
    })
    (root / ROLES["paper_ticks"]).write_text("Paper raw synthetic\n")
    return _seal(root, trial)


def _seal(root: Path, trial: str) -> Path:
    rows = {}
    for role, basename in ROLES.items():
        path = root / basename
        stat = path.stat()
        rows[role] = {
            "path": basename, "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
            "size_bytes": stat.st_size, "device": stat.st_dev, "inode": stat.st_ino,
            "mtime_ns": stat.st_mtime_ns,
        }
    manifest = root / "original-u17-manifest.json"
    _write_json(manifest, {
        "schema": "q4-original-raw-evidence-dev-v1", "trial": trial,
        "status": "RAW_EVIDENCE_MANIFEST_SEALED_NOT_VERIFIED",
        "real_world_dev_pass": False, "qual_go": False, "science_run": False,
        "independent_paper_source_audited": False,
        "independent_q_audited": False, "evidence": rows,
    })
    return manifest


def _modify(root, role, fn, trial):
    path = root / ROLES[role]
    value = json.loads(path.read_text()) if path.suffix != ".jsonl" else [
        json.loads(line) for line in path.read_text().splitlines()
    ]
    fn(value)
    if path.suffix == ".jsonl":
        path.write_text("".join(json.dumps(x) + "\n" for x in value))
    else:
        _write_json(path, value)
    return _seal(root, trial)


@pytest.mark.parametrize("trial", ["two_moves", "stop_failure"])
def test_failed_s1_original_source_structural_diagnosis(tmp_path, trial):
    manifest = _make_source(tmp_path, trial)
    result = audit_u24_failed_s1(
        root=tmp_path, manifest_path=manifest, trial=trial,
    )
    assert result["wal_unresolved"] is True
    assert result["s2_issued"] is False
    assert result["start_applied"] is True
    assert result["real_world_dev_pass"] is False
    assert result["independent_os_exit_attested"] is False
    if trial == "two_moves":
        assert result["stop_applied"] is True
        assert result["probes"] == 24
        assert result["native_world_tick_span"] == 0
        assert result["observation_classification"] == "INSUFFICIENT_NATIVE_TICK_ADVANCE"
    else:
        assert result["stop_sent"] is False
        assert result["stop_applied"] is False


@pytest.mark.parametrize("fault", [
    "missing-stop", "surplus-effect", "bad-start-ack", "old-stop-probe",
    "tick-regression", "duplicate-probe", "faked-terminal-wal",
    "missing-stop-response", "tampered-original",
])
def test_nominal_unresolved_adversarial_refusals(tmp_path, fault):
    trial = "two_moves"
    manifest = _make_source(tmp_path, trial)
    if fault == "missing-stop":
        manifest = _modify(tmp_path, "native_stdin", lambda x: x.remove(
            next(row for row in x if row.get("effect") == "clear_controls")), trial)
    elif fault == "surplus-effect":
        manifest = _modify(tmp_path, "native_stdin",
                           lambda x: x.append(dict(type="effect", action_id="second-start",
                                                   effect="set_control",
                                                   control="forward", state=True)), trial)
    elif fault == "bad-start-ack":
        manifest = _modify(tmp_path, "native_stdout",
                           lambda x: next(r for r in x if r.get("action_id") == ACTION + "-start")
                           .update(result="rejected"), trial)
    elif fault == "old-stop-probe":
        manifest = _modify(tmp_path, "native_stdout",
                           lambda x: next(r for r in x if r.get("request_id") == "p0d-move-stop-0")
                           .update(seq=3), trial)
    elif fault == "tick-regression":
        manifest = _modify(tmp_path, "native_stdout",
                           lambda x: next(r for r in x if r.get("request_id") == "p0d-move-stop-23")
                           ["snapshot"]["time"].update(time_of_day=99), trial)
    elif fault == "duplicate-probe":
        manifest = _modify(tmp_path, "native_stdin",
                           lambda x: next(r for r in x if r.get("request_id") == "p0d-move-stop-23")
                           .update(request_id="p0d-move-stop-0"), trial)
    elif fault == "faked-terminal-wal":
        manifest = _modify(tmp_path, "owner_wal",
                           lambda x: x["body"]["actions"][0].update(status="NATIVE_PLACE_MOVE_SETTLED"),
                           trial)
    elif fault == "missing-stop-response":
        manifest = _modify(tmp_path, "native_stdout",
                           lambda x: x.remove(next(
                               r for r in x if r.get("request_id") == "p0d-move-stop-23")), trial)
    else:
        (tmp_path / ROLES["native_stdout"]).write_text("forged bytes\n")
    with pytest.raises((Q9U24Hold, ValueError)):
        audit_u24_failed_s1(root=tmp_path, manifest_path=manifest, trial=trial)


def test_nominal_stable_window_contradicts_exhaustion(tmp_path):
    ticks = [100] * 7 + [111] * 9 + [123] * 8
    manifest = _make_source(tmp_path, "two_moves", stop_ticks=ticks)
    with pytest.raises(Q9U24Hold, match="already meets 8\\+8"):
        audit_u24_failed_s1(root=tmp_path, manifest_path=manifest, trial="two_moves")


@pytest.mark.parametrize("fault", [
    "sent-stop", "missing-start", "zero-return", "unused-fault", "s2-claim",
])
def test_fault_trial_adversarial_refusals(tmp_path, fault):
    trial = "stop_failure"
    manifest = _make_source(tmp_path, trial)
    if fault == "sent-stop":
        manifest = _modify(tmp_path, "native_stdin",
                           lambda x: x.append(dict(type="effect",
                                                   action_id=ACTION + "-stop",
                                                   effect="clear_controls")), trial)
    elif fault == "missing-start":
        manifest = _modify(tmp_path, "native_stdout",
                           lambda x: x.remove(next(
                               r for r in x if r.get("action_id") == ACTION + "-start")), trial)
    else:
        def patch(row):
            if fault == "zero-return":
                row["returncode"] = 0
            elif fault == "unused-fault":
                row["stop_fault_injection_consumed"] = False
            else:
                row["s2_terminal"] = True
        manifest = _modify(tmp_path, "process_exit", patch, trial)
    with pytest.raises((Q9U24Hold, ValueError)):
        audit_u24_failed_s1(root=tmp_path, manifest_path=manifest, trial=trial)
