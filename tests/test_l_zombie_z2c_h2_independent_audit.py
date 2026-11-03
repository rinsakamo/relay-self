"""Z2c independent H2 postflight with real archived Z2b sources, FAKE HTTP."""
from __future__ import annotations

import io
import json
import shutil
import subprocess
import sys

import pytest

from adapters.mineflayer.l_zombie_z2b_policy_contract import ZombiePolicyRejected
from test_l_zombie_z2c_feedback_contract import (
    SOURCE_ROOT,
    answer,
    reply,
)
from tools import l_zombie_z2c_h2_independent_audit as auditor
from tools import l_zombie_z2c_h2_original_feedback as runner

REAL_OLD_ROOT = SOURCE_ROOT.resolve()
ENDPOINT = "http://127.0.0.1:8080/v1/chat/completions"
ALIAS = "relay-self-gemma4-12b-q4km"


def attempt(tmp_path, monkeypatch, *, response: bytes):
    monkeypatch.setenv("L_ZOMBIE_Z2C_REAL_H2_DEV", "1")
    calls = []
    class FakeResponse(io.BytesIO):
        pass
    def fake_urlopen(req, timeout):
        calls.append((req, timeout))
        return FakeResponse(response)
    monkeypatch.setattr(runner.urllib.request, "urlopen", fake_urlopen)
    fresh = tmp_path / "one-h2-attempt"
    try:
        runner.real_h2_once(
            original_root=REAL_OLD_ROOT, output_root=fresh,
            endpoint=ENDPOINT, model=ALIAS,
        )
    except ZombiePolicyRejected:
        pass
    assert len(calls) == 1
    assert (fresh / "h2-request-1.raw.json").exists()
    assert (fresh / "h2-response-1.raw.json").read_bytes() == response
    return fresh


def test_68_real_original_files_and_synthetic_h2_full_valid_readback(tmp_path, monkeypatch):
    root = attempt(tmp_path, monkeypatch, response=reply())
    report = auditor.audit_saved_h2(REAL_OLD_ROOT, root)
    assert report["classification"] == (
        "H2_FULL_CONTRACT_SOURCE_REPLAY_PASS_SEMANTIC_REVIEW_PENDING"
    )
    assert report["source_files_sha_replayed"] >= 68
    assert report["h2_wire_stopped_and_thinking_off"]
    assert report["numeric_h2_self_report_matches_original_paper"]
    assert report["numeric_H2_limited_evidence_only"]
    assert report["full_h2_contract_verified"]
    assert report["independent_qualitative_semantic_review"] == "NOT_PERFORMED"
    assert report["B1_Q"] == "NOT_INDEPENDENTLY_ESTABLISHED"
    assert not report["learning_authorized"]
    assert not report["action_authorized"]
    assert not report["qualification_go"]
    assert not report["science_run"]
    out = tmp_path / "independent-report.json"
    # CLI cannot share local monkeypatch state; it runs its own source replay.
    cp = subprocess.run(
        [sys.executable, "-m", "tools.l_zombie_z2c_h2_independent_audit",
         "--original-root", str(REAL_OLD_ROOT),
         "--h2-root", str(root), "--report", str(out)],
        check=False, capture_output=True, text=True,
    )
    assert cp.returncode == 0, cp.stderr
    assert json.loads(out.read_text())["full_h2_contract_verified"]
    cp2 = subprocess.run(
        [sys.executable, "-m", "tools.l_zombie_z2c_h2_independent_audit",
         "--original-root", str(REAL_OLD_ROOT),
         "--h2-root", str(root), "--report", str(out)],
        check=False, capture_output=True, text=True,
    )
    assert cp2.returncode == 2
    assert json.loads(out.read_text()) == report


def test_numeric_success_qualitative_failure_kept_separate(tmp_path, monkeypatch):
    invalid = answer(diagnosed_issues=["CHASE_CAUSALITY_UNATTESTED"])
    root = attempt(tmp_path, monkeypatch, response=reply(invalid))
    report = auditor.audit_saved_h2(REAL_OLD_ROOT, root)
    assert report["classification"] == (
        "H2_NUMERIC_WIRE_MATCH_QUALITATIVE_OR_SCHEMA_REJECTED"
    )
    assert report["numeric_h2_self_report_matches_original_paper"]
    assert not report["full_h2_contract_verified"]
    assert report["B1_Q"] == "NOT_INDEPENDENTLY_ESTABLISHED"
    assert not (root / "h2-revision-proposal-v1.json").exists()
    assert json.loads((root / "h2-status.json").read_text())["status"] == (
        "H2_NOT_ESTABLISHED"
    )


@pytest.mark.parametrize("response,classification", [
    (reply(answer(observed_horizontal_error_m=0.0)), "H2_WIRE_OR_NUMERIC_UNESTABLISHED"),
    (reply(finish="length"), "H2_WIRE_OR_NUMERIC_UNESTABLISHED"),
    (reply(reasoning="not thinking off"), "H2_WIRE_OR_NUMERIC_UNESTABLISHED"),
    (b"{broken json", "H2_WIRE_OR_NUMERIC_UNESTABLISHED"),
])
def test_wrong_numeric_incomplete_or_reasoning_response_never_passes(
    tmp_path, monkeypatch, response, classification,
):
    root = attempt(tmp_path, monkeypatch, response=response)
    result = auditor.audit_saved_h2(REAL_OLD_ROOT, root)
    assert result["classification"] == classification
    assert not result["numeric_h2_self_report_matches_original_paper"]
    assert not result["full_h2_contract_verified"]
    assert not result["learning_authorized"]


def test_saved_request_tampering_refused(tmp_path, monkeypatch):
    root = attempt(tmp_path, monkeypatch, response=reply())
    path = root / "h2-request-1.raw.json"
    path.write_bytes(path.read_bytes() + b" ")
    with pytest.raises(ZombiePolicyRejected, match="request"):
        auditor.audit_saved_h2(REAL_OLD_ROOT, root)


def test_saved_success_revision_tampering_refused(tmp_path, monkeypatch):
    root = attempt(tmp_path, monkeypatch, response=reply())
    path = root / "h2-revision-proposal-v1.json"
    assert path.exists()
    path.write_bytes(path.read_bytes() + b" ")
    with pytest.raises(ZombiePolicyRejected, match="proposal/status mismatch"):
        auditor.audit_saved_h2(REAL_OLD_ROOT, root)


def test_saved_status_claiming_success_for_bad_response_refused(tmp_path, monkeypatch):
    root = attempt(
        tmp_path, monkeypatch, response=reply(answer(observed_horizontal_error_m=0.0)),
    )
    status_file = root / "h2-status.json"
    status = json.loads(status_file.read_text())
    status["status"] = "H2_CONTRACT_DEV_PASS_UNADMITTED"
    status_file.write_text(json.dumps(status))
    with pytest.raises(ZombiePolicyRejected, match="cannot have a PASS"):
        auditor.audit_saved_h2(REAL_OLD_ROOT, root)


def test_original_68_file_mutation_refused_before_h2_interpretation(tmp_path, monkeypatch):
    root = attempt(tmp_path, monkeypatch, response=reply())
    original = tmp_path / "copied-z2b"
    shutil.copytree(REAL_OLD_ROOT, original)
    h1 = original / "gemma-preparation/llama-response-1.raw.json"
    h1.write_bytes(h1.read_bytes() + b"\n")
    with pytest.raises(ValueError):
        auditor.audit_saved_h2(original, root)


def test_broken_symlink_or_missing_response_status_cannot_claim_success(tmp_path, monkeypatch):
    root = attempt(tmp_path, monkeypatch, response=reply())
    p = root / "h2-response-1.raw.json"
    p.unlink()
    p.symlink_to("/does/not/exist")
    with pytest.raises(ZombiePolicyRejected, match="unsafe"):
        auditor.audit_saved_h2(REAL_OLD_ROOT, root)
