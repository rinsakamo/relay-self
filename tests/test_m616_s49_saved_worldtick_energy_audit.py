"""Saved original S49/B0 World evidence must remain unchanged and unbilled."""
from __future__ import annotations

import hashlib
import json
from copy import deepcopy

import pytest

import test_m616_s49_worldtick_energy_gate as raw_source
from tools.m616_s49_saved_worldtick_energy_audit import (
    M616OriginalEnergyAuditRejected,
    audit_preserved_b0_evidence,
)


def _prepare(tmp_path):
    directory = tmp_path / "m616-b0-evidence"
    directory.mkdir()
    s49, m = raw_source._saved()
    files = {
        "s49-report.json": json.dumps(s49),
        "m-original-b0.json": json.dumps(m),
        "exit.json": json.dumps({
            "process_exit": 0, "world_attempts": 1, "retries": 0,
        }),
        "minecraft.log": "offline synthetic log, no real server",
        "preflight.log": "offline synthetic import",
        "stderr.log": "",
        "stdout.log": "offline synthetic output",
    }
    for name, body in files.items():
        (directory / name).write_text(body, encoding="utf-8")
    _manifest(directory)
    return directory


def _manifest(directory):
    names = [
        "exit.json", "m-original-b0.json", "minecraft.log",
        "preflight.log", "s49-report.json", "stderr.log", "stdout.log",
    ]
    lines = []
    for name in names:
        sha = hashlib.sha256((directory / name).read_bytes()).hexdigest()
        lines.append(f"{sha}  m616-b0-evidence/{name}")
    (directory / "SHA256SUMS").write_text(
        "\n".join(lines) + "\n", encoding="utf-8",
    )


def test_untampered_source_sha_matched_and_no_energy_debit(tmp_path):
    original = _prepare(tmp_path)
    saved = audit_preserved_b0_evidence(original)
    assert saved["original_evidence_files_sha_matched"] == 7
    assert saved["status"] == "DEFERRED"
    assert saved["original_world_attempts"] == 1
    assert saved["energy_debits"] == 0
    assert saved["consecutive_world_ticks"] is None
    assert saved["native_full_tick_coverage"] == "NOT_SUPPLIED"
    assert not saved["original_artifact_sha_list_authenticated_by_independent_custodian"]


@pytest.mark.parametrize("fault", [
    "delete", "corrupt", "bad_manifest", "duplicate", "symlink",
    "wrong_world_count", "wrong_s49_status", "fake_debit",
])
def test_original_archive_violations_reject_without_repair(tmp_path, fault):
    root = _prepare(tmp_path)
    if fault == "delete":
        (root / "s49-report.json").unlink()
    elif fault == "corrupt":
        (root / "m-original-b0.json").write_text("{}", encoding="utf-8")
    elif fault == "bad_manifest":
        (root / "SHA256SUMS").write_text(
            "0" * 64 + "  m616-b0-evidence/exit.json\n", encoding="utf-8",
        )
    elif fault == "duplicate":
        file = root / "SHA256SUMS"
        file.write_text(file.read_text() + file.read_text().splitlines()[0] + "\n")
    elif fault == "symlink":
        p = root / "stdout.log"
        p.unlink()
        p.symlink_to(root / "stderr.log")
    elif fault == "wrong_world_count":
        (root / "exit.json").write_text(json.dumps({
            "process_exit": 0, "world_attempts": 2, "retries": 0,
        }))
        _manifest(root)
    elif fault == "wrong_s49_status":
        doc = json.loads((root / "s49-report.json").read_text())
        doc["status"] = "FAIL"
        (root / "s49-report.json").write_text(json.dumps(doc))
        _manifest(root)
    elif fault == "fake_debit":
        doc = json.loads((root / "m-original-b0.json").read_text())
        doc["energy_debits"] = 1
        (root / "m-original-b0.json").write_text(json.dumps(doc))
        _manifest(root)
    with pytest.raises(M616OriginalEnergyAuditRejected):
        audit_preserved_b0_evidence(root)


def test_additional_untrusted_time_fields_do_not_mint_tick_cost(tmp_path):
    root = _prepare(tmp_path)
    s = json.loads((root / "s49-report.json").read_text())
    s["world_age_ticks"] = "9000"
    s["full_tick_coverage_attested"] = True
    s["b0_worldtick_energy_debit"] = 18
    (root / "s49-report.json").write_text(json.dumps(s))
    _manifest(root)
    result = audit_preserved_b0_evidence(root)
    assert result["status"] == "DEFERRED"
    assert result["energy_debits"] == 0
    assert result["consecutive_world_ticks"] is None
