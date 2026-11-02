"""S2-B offline row audit regression; generated owner rows are SYNTHETIC.

S49/S2A source sample is an already archived prior S2-A World. Constructed
S2-B owner witnesses are NOT a real owner readback from that historical World.
"""
from __future__ import annotations

import copy
import json
import sys
from pathlib import Path

import pytest

from tools.s537_s2b_original_owner_audit import (
    OwnerAuditRejected,
    audit_original_rows,
    main,
)

_FIXTURE = (
    Path(__file__).resolve().parents[1] / "docs" / "evidence"
    / "s537-s2a-world-20261102"
)


def _source():
    s49 = json.loads((_FIXTURE / "s49.json").read_text(encoding="utf-8"))
    s2a = json.loads((_FIXTURE / "s2a.json").read_text(encoding="utf-8"))
    entries = s2a["s2a"]["inputs"]
    # SYNTHETIC owner rows are fabricated solely as a negative-test fixture.
    rows = [{
        "native_probe_seq": entry["probe_seq"],
        "request_id": entry["request_id"],
        "intent_id": "escape-threat",
        "intent_generation": 1,
        "retained_revision": 1,
        "preceding_action_id": entry["preceding_action_id"],
    } for entry in entries]
    s2b = {
        "status": "RECORDED", "s2a_status": "RECORDED",
        "model_calls": 0, "s60_submissions": 0, "source_attested": False,
        "s2a": s2a,
        "owner_epoch": {
            "status": "RECORDED", "epoch_contexts": rows,
            "source_attested": False,
            "original_owner": {
                "status": "RECORDED", "session_id": s49["session_id"],
                "epochs": [{
                    "native_probe_seq": row["native_probe_seq"],
                    "intent_generation": 1, "retained_revision": 1,
                    "intent_id": "escape-threat",
                } for row in rows],
            },
        },
    }
    return s49, s2b


def test_original_rows_consistent_with_synthetic_owner_witness():
    s49, report = _source()
    result = audit_original_rows(s49, report)
    assert result["status"] == "PASS"
    assert result["native_input_count"] == 3
    assert result["original_closed_actions"] == 2
    assert result["previous_s16_bound"] == 1
    assert result["source_attested"] is False
    assert result["model_calls"] == 0


@pytest.mark.parametrize("fault", [
    "foreign_session", "future_s16", "injected_previous_s16",
    "replayed_probe", "wrong_owner_rev", "wrong_wb_source",
    "missing_s16", "wrong_action_after", "swapped_action",
    "model_call", "fake_source_attestation",
])
def test_audit_rejects_tampered_original_source_rows(fault):
    s49, report = _source()
    s49, report = copy.deepcopy((s49, report))
    rows = report["owner_epoch"]["epoch_contexts"]
    input_rows = report["s2a"]["s2a"]["inputs"]
    host_events = report["s2a"]["s2a"]["host_events"]
    if fault == "foreign_session":
        rows[0]["request_id"] = "foreign"
    elif fault == "future_s16":
        input_rows[2]["preceding_s16_after_seq"] = 1000
    elif fault == "injected_previous_s16":
        input_rows[0]["preceding_action_id"] = "s49-native-move-20"
    elif fault == "replayed_probe":
        rows[1]["native_probe_seq"] = rows[0]["native_probe_seq"]
    elif fault == "wrong_owner_rev":
        rows[1]["retained_revision"] = 4
    elif fault == "wrong_wb_source":
        report["s2a"]["s1"]["typed_join"]["wb_rows"][1]["world_source_ref"] = "fake"
    elif fault == "missing_s16":
        host_events.pop(2)
    elif fault == "wrong_action_after":
        host_events[2]["s16_after_seq"] = 222
    elif fault == "swapped_action":
        s49["actual_native_actions"][0]["action"] = "other"
    elif fault == "model_call":
        report["model_calls"] = 1
    elif fault == "fake_source_attestation":
        report["source_attested"] = True
    with pytest.raises(OwnerAuditRejected):
        audit_original_rows(s49, report)


def test_cli_is_fresh_only_and_never_certifies_independent_source(
    tmp_path, monkeypatch, capsys,
):
    s49, report = _source()
    p49 = tmp_path / "s49.json"
    p2b = tmp_path / "s2b.json"
    output = tmp_path / "audit.json"
    p49.write_text(json.dumps(s49))
    p2b.write_text(json.dumps(report))
    monkeypatch.setattr(sys, "argv", [
        "audit", "--s49", str(p49), "--s2b", str(p2b), "--output", str(output),
    ])
    assert main() == 0
    assert json.loads(output.read_text())["source_attested"] is False
    assert main() == 2
    assert '"BLOCKED"' in capsys.readouterr().out
