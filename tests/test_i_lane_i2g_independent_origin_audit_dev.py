"""I2g independent original audit/seal is source-only, fail closed.

Offline fixtures are NOT real Paper/GPU/native source, so none may be
certified by the final I2g auditor; only its bounded file inventory helper
may accept synthetic sample hashes.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest

from experiments import i_lane_i2g_independent_origin_audit_dev as audit
from test_i_lane_i2e_future_original_preflight_dev import _future


def test_i2g_root_inventory_requires_three_original_typed_dimension_hashes(
    tmp_path,
):
    evidence = tmp_path / "evidence"
    evidence.mkdir()
    file = evidence / "resident-presence-result.json"
    file.write_bytes(b"synthetic-untrusted-content")
    with pytest.raises(audit.I2gIndependentOriginHold):
        audit._root_files(evidence, manifest_exists=False)
    for name in audit._NESTED_HASHES:
        path = evidence / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(b"synthetic-dimension-checksum")
    files = audit._root_files(evidence, manifest_exists=False)
    assert files == {
        "resident-presence-result.json": hashlib.sha256(file.read_bytes()).hexdigest()
    }
    (evidence / "untracked").write_bytes(b"tamper")
    assert len(audit._root_files(evidence, manifest_exists=False)) == 2
    (evidence / "untracked").unlink()
    (evidence / "SHA256SUMS").write_bytes(b"forged root manifest")
    with pytest.raises(audit.I2gIndependentOriginHold):
        audit._root_files(evidence, manifest_exists=False)
    assert audit._root_files(evidence, manifest_exists=True) == files


@pytest.mark.parametrize("fault", [
    "foreign-generation", "missing-report", "legacy-report",
    "synthetic-v3-no-real-paper", "foreign-native",
])
def test_i2g_new_origin_audit_refuses_synthetic_or_legacy_source(
    tmp_path, monkeypatch, fault,
):
    args = _future(tmp_path, monkeypatch)
    gen = args["generation"]
    evidence = tmp_path / "separate-original-real-evidence"
    evidence.mkdir()
    if fault == "foreign-generation":
        gen = tmp_path / "forged-generation"
        gen.mkdir()
    elif fault == "legacy-report":
        (evidence / "resident-presence-result.json").write_text(
            json.dumps({
                "classification": "REAL_PAPER_TWO_SELF_TYPED_STOPPED_WORLD_CUT_DEV",
                "i2g_original_v3_source": True,
            }),
        )
    elif fault == "synthetic-v3-no-real-paper":
        (evidence / "resident-presence-result.json").write_text(
            json.dumps({
                "classification": audit._I2G_CLASS,
                "i2g_original_v3_source": True,
                "i2g_initial_source_verified": True,
                "steps": [],
            }),
        )
    elif fault == "foreign-native":
        (evidence / "resident-presence-result.json").write_text(
            json.dumps({
                "classification": audit._I2G_CLASS,
                "i2g_original_v3_source": True,
                "i2g_initial_source_verified": True,
                "steps": [{"a_original_native_session": "forged"}],
            }),
        )
    with pytest.raises(audit.I2gIndependentOriginHold):
        audit.independently_read_i2g_original(evidence=evidence, generation=gen)
    assert not (evidence / "SHA256SUMS").exists()
    assert not (tmp_path / "fork").exists()


def test_i2g_seal_never_runs_on_synthetic_v3_without_native_paper(
    tmp_path, monkeypatch,
):
    args = _future(tmp_path, monkeypatch)
    evidence = tmp_path / "missing-raw-source"
    evidence.mkdir()
    with pytest.raises(audit.I2gIndependentOriginHold):
        audit.seal_i2g_original_manifest_once(
            evidence=evidence, generation=args["generation"],
        )
    assert not (evidence / "SHA256SUMS").exists()


def test_i2g_pins_fork_cannot_be_prepared_from_unsealed_source(
    tmp_path, monkeypatch,
):
    args = _future(tmp_path, monkeypatch)
    evidence = tmp_path / "missing-origin-source"
    evidence.mkdir()
    with pytest.raises((audit.I2gIndependentOriginHold, RuntimeError, OSError)):
        audit.prepare_i2g_inert_fork_and_pins_once(
            evidence=evidence, generation=args["generation"],
            sealed_manifest_sha256="0" * 64,
            manifest_files=285, destination=tmp_path / "fork",
            restore_id="independent-once",
            pins_output=tmp_path / "new-source-pins.json",
        )
    assert not (tmp_path / "fork").exists()
    assert not (tmp_path / "new-source-pins.json").exists()


@pytest.mark.parametrize("flags", [
    ["--inspect-unsealed", "--restored", "forged"],
    ["--seal-once", "--pins-output", "forged"],
    ["--prepare-fork-once"],
])
def test_i2g_cli_never_mutates_legacy_evidence_on_invalid_mode(
    tmp_path, monkeypatch, flags, capsys,
):
    evidence = tmp_path / "legacy"
    evidence.mkdir()
    monkeypatch.setattr(
        "sys.argv", [
            "i2g-audit",
            "--original-evidence", str(evidence),
            "--generation", str(tmp_path / "missing-generation"),
            *flags,
        ],
    )
    assert audit.main() == 2
    assert "I2G_INDEPENDENT_ORIGINAL_HOLD" in capsys.readouterr().err
    assert not list(evidence.iterdir())
