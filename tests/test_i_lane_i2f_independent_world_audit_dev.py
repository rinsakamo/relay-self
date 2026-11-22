"""I2f independent model→Native/Paper correlation with synthetic raw witnesses.

This is intentionally a narrow helper fixture, NEVER evidence of real World.
The full independent auditor still requires original pinned v3 checkpoint,
owned Paper process/ack, actual model HTTP/GGUF source and clean retirement.
"""
from __future__ import annotations

import hashlib
import json

import pytest

from experiments.i_lane_i2f_independent_world_audit_dev import (
    I2fIndependentWorldHold,
    _model_native_correlation,
    independently_audit_i2f_original_world,
)
from relay_self.i_lane_i2f_future_source_pins_dev import I2fFutureSourcePins
from test_i_lane_i1_independent_cpu_audit_dev import (
    _SESSION,
    _SOURCE_WORLD,
    _fixture,
    _line,
    _native,
)


def _synthetic_model_world(tmp_path):
    report, evidence, executable, owners = _fixture(tmp_path)
    report["paper_boot"]["paper_session_id"] = _SESSION
    report["paper_boot"]["source_world_id"] = _SOURCE_WORLD
    ref = next(
        row for row in report["i1_cpu_epochs"]["epochs"]
        if row["self_id"] == "A" and row["native_seq"] == 3
    )
    native = "native-A"
    request = "i1-original-sense-" + "f" * 32
    raw = evidence / "native-RelayA-native-A.jsonl"
    output, _ = _native("A", 4, request)
    with raw.open("ab") as stream:
        stream.write(_line(output))
    report["raw_native_file_sha256"]["RelayA"] = hashlib.sha256(
        raw.read_bytes()
    ).hexdigest()
    command = evidence / "native-commands-RelayA-native-A.jsonl"
    with command.open("ab") as stream:
        stream.write(_line({"type": "observe", "request_id": request}))
    report["raw_native_command_file_sha256"]["RelayA"] = hashlib.sha256(
        command.read_bytes()
    ).hexdigest()
    raw_dir = evidence / "i2f-original-dual-model"
    raw_dir.mkdir()
    model = {
        "self_id": "A",
        "open_l2_ticket": {"self_epoch": 1},
        "handoff": {
            "self_id": "A",
            "paper_session_id": _SESSION,
            "native_session_id": native,
            "resident_epoch": 1,
            "paper_log_sha256": ref["paper_log_sha256"],
            "paper_tick_source_ref": ref["paper_tick_source_ref"],
            "model_invoked": False,
            "action_issue_authorized": False,
            "status": "NO_QUALIFIED_EXPLORATION_GOAL",
            "native_request_id": request,
            "native_seq": 4,
        },
    }
    (raw_dir / "i2e-dual-model-report.json").write_text(json.dumps(model))
    return report, evidence, executable, raw_dir, model


def test_i2f_qualified_synthetic_native_paper_correlation_only(
    tmp_path,
):
    report, evidence, executable, raw_dir, model = _synthetic_model_world(tmp_path)
    correlated = _model_native_correlation(
        report=report, evidence=evidence,
        executable=executable, raw_dir=raw_dir,
    )
    assert correlated["owner_self"] == "A"
    assert correlated["native_seq"] == 4
    assert correlated["original_paper_prefix_sha256"] == (
        model["handoff"]["paper_log_sha256"]
    )
    assert correlated["original_a_native_request_id"] == (
        model["handoff"]["native_request_id"]
    )
    # This helper success has no status field that could promote real-World.


@pytest.mark.parametrize("fault", [
    "foreign-self", "foreign-session", "stale-seq", "stale-req",
    "paper-digest", "paper-session", "paper-ack", "paper-stdout",
    "native-output", "native-command", "physical-b-command",
    "absent-l2-ticket", "false-mode",
])
def test_i2f_native_paper_attribution_rejects_forgery(
    tmp_path, fault,
):
    report, evidence, executable, raw_dir, model = _synthetic_model_world(tmp_path)
    if fault == "foreign-self":
        model["self_id"] = "B"
    elif fault == "foreign-session":
        model["handoff"]["native_session_id"] = "native-B"
    elif fault == "stale-seq":
        model["handoff"]["native_seq"] = 3
    elif fault == "stale-req":
        model["handoff"]["native_request_id"] = "i1-original-sense-" + "e" * 32
    elif fault == "paper-digest":
        model["handoff"]["paper_log_sha256"] = "0" * 64
    elif fault == "paper-session":
        model["handoff"]["paper_session_id"] = "paper-owned-foreign"
    elif fault == "paper-ack":
        ack_dir = executable / "plugins" / "P0BRecorder" / "p0d-ticks" / "acks"
        for f in ack_dir.iterdir():
            f.write_bytes(b"tampered ack")
    elif fault == "paper-stdout":
        (evidence / (_SESSION + ".log")).write_bytes(b"foreign Paper")
    elif fault == "native-output":
        with (evidence / "native-RelayA-native-A.jsonl").open("ab") as handle:
            handle.write(b"foreign\n")
    elif fault == "native-command":
        with (evidence / "native-commands-RelayA-native-A.jsonl").open("ab") as handle:
            handle.write(_line({"type": "observe", "request_id": "extra"}))
    elif fault == "physical-b-command":
        cmd = evidence / "native-commands-RelayB-native-B.jsonl"
        cmd.write_bytes(_line({"type": "move", "request_id": "attack"}))
        report["raw_native_command_file_sha256"]["RelayB"] = hashlib.sha256(
            cmd.read_bytes()
        ).hexdigest()
    elif fault == "absent-l2-ticket":
        model["open_l2_ticket"] = {}
    else:
        model["handoff"]["action_issue_authorized"] = True
    (raw_dir / "i2e-dual-model-report.json").write_text(json.dumps(model))
    with pytest.raises((I2fIndependentWorldHold, KeyError, ValueError)):
        _model_native_correlation(
            report=report, evidence=evidence,
            executable=executable, raw_dir=raw_dir,
        )


def test_i2f_full_world_audit_cannot_promote_synthetic_prefix_helper(
    tmp_path,
):
    report, evidence, executable, raw_dir, model = _synthetic_model_world(tmp_path)
    # Even a valid raw prefix match is insufficient to claim an original
    # real Model/GGUF or World. World auditor must reject source on entry.
    result = evidence / "stage28c2b-recovered-world-result.json"
    result.write_text(json.dumps(report))
    with pytest.raises((I2fIndependentWorldHold, RuntimeError, KeyError, ValueError)):
        independently_audit_i2f_original_world(
            result=result, generation=tmp_path / "missing-generation",
            restored=tmp_path / "missing-restored",
            original_evidence=tmp_path / "missing-original-evidence",
            executable=executable,
            pins=I2fFutureSourcePins(
                _SOURCE_WORLD, "source",
                "a" * 64, "new-fork", "b" * 64, 285,
            ),
        )
