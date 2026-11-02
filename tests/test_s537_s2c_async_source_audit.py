"""S2-C cross-audit using archived S2-B World rows + SYNTHETIC S60 receipts.

The archived World did not run S2-C or a model. The added S60 rows are fake
offline test fixtures only, not a physical model attempt.
"""
from __future__ import annotations

import copy
import json
import sys
from pathlib import Path

import pytest

from tools.s537_s2c_async_source_audit import (
    S2CSourceAuditRejected,
    audit_s2c_rows,
    main,
)

_SOURCE = (
    Path(__file__).resolve().parents[1] / "docs" / "evidence"
    / "s537-s2b-world-20261102"
)


def _synthetic_s2c():
    s49 = json.loads((_SOURCE / "s49.json").read_text())
    prev = json.loads((_SOURCE / "s2b.json").read_text())
    inputs = prev["s2a"]["s2a"]["inputs"]
    model_source = [row for row in inputs if row["preceding_action_id"]]
    assert len(model_source) == 1
    s60 = {
        "status": "EXPIRED_ORIGINAL_S16_WORLD_ADVANCED",
        "model_attempts": 1,
        "session_id": s49["session_id"],
        "input_source_seq": model_source[0]["probe_seq"],
        "latest_probe_seq": model_source[0]["probe_seq"],
        "original_s16_invalidations": 1,
        "l0_awaited_provider": False,
        "backend_stop_ack": False,
        "gpu_release_verified": False,
        "source_attested": False,
        "owner_events": [
            "NEW_REQUEST_STARTED", "DISPLACED", "HOST_CANCEL_REQUESTED",
        ],
        "transport_events": ["START_INVOKED", "SOCKET_POST_SENT"],
        "poll_errors": [],
        "original_source_callback_errors": [],
        "advisory_accepted_before_invalidation": [],
    }
    return s49, {
        "status": "RECORDED",
        "source_join_status": "RECORDED",
        "s49_s1": prev["s2a"]["s1"],
        "s2a": prev["s2a"]["s2a"],
        "owner_epoch": prev["owner_epoch"],
        "s60": s60,
        "s60_submissions": 1,
        "http_post_sent_observed": True,
        "http_completion_observed": False,
        "source_attested": False,
        "action_authority": False,
        "learning_authority": False,
        "new_native_reads": 0,
        "new_action_issues": 0,
        "learning_updates": 0,
        "energy_debits": 0,
    }


def test_synthetic_s2c_receipts_are_source_consistent_but_not_real_model():
    s49, report = _synthetic_s2c()
    result = audit_s2c_rows(s49, report)
    assert result["status"] == "PASS"
    assert result["native_input_count"] == 3
    assert result["original_closed_actions"] == 2
    assert result["previous_s16_bound"] == 1
    assert result["s60_model_attempts"] == 1
    assert not result["source_attested"]
    assert not result["backend_stop_ack"]
    assert not result["http_completion_observed"]


@pytest.mark.parametrize("kind", [
    "missing_http_post", "forged_completion", "no_original_s16_fence",
    "wrong_model_seq", "wrong_session", "double_model",
    "future_s16", "altered_wb", "fake_source_attestation",
    "action_authority", "l0_blocked", "backend_stop_ack",
])
def test_s2c_cross_audit_rejects_model_or_source_forgery(kind):
    s49, report = copy.deepcopy(_synthetic_s2c())
    s60 = report["s60"]
    if kind == "missing_http_post":
        s60["transport_events"].remove("SOCKET_POST_SENT")
    elif kind == "forged_completion":
        report["http_completion_observed"] = True
    elif kind == "no_original_s16_fence":
        s60["owner_events"].remove("DISPLACED")
    elif kind == "wrong_model_seq":
        s60["input_source_seq"] -= 1
    elif kind == "wrong_session":
        s60["session_id"] = "foreign"
    elif kind == "double_model":
        report["s60_submissions"] = 2
    elif kind == "future_s16":
        report["s2a"]["inputs"][2]["preceding_s16_after_seq"] = 999
    elif kind == "altered_wb":
        report["s49_s1"]["typed_join"]["wb_rows"][1]["request_id"] = "foreign"
    elif kind == "fake_source_attestation":
        report["source_attested"] = True
    elif kind == "action_authority":
        report["action_authority"] = True
    elif kind == "l0_blocked":
        s60["l0_awaited_provider"] = True
    elif kind == "backend_stop_ack":
        s60["backend_stop_ack"] = True
    with pytest.raises(S2CSourceAuditRejected):
        audit_s2c_rows(s49, report)


def test_model_enabled_audit_cli_is_fresh_only(tmp_path, monkeypatch):
    s49, report = _synthetic_s2c()
    original, sidecar, output = (
        tmp_path / "original.json", tmp_path / "sidecar.json",
        tmp_path / "audit.json",
    )
    original.write_text(json.dumps(s49))
    sidecar.write_text(json.dumps(report))
    monkeypatch.setattr(sys, "argv", [
        "audit", "--s49", str(original),
        "--s2c", str(sidecar), "--output", str(output),
    ])
    assert main() == 0
    assert json.loads(output.read_text())["source_attested"] is False
    assert main() == 2
