"""U16 Q4 raw Native/Paper/WAL source manifest — never World PASS.

These tests use fixture bytes, not a real Minecraft or Node process.
"""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path

import pytest

from experiments.i_unified_q4_raw_evidence_manifest_dev import (
    Q4RawManifestHold,
    seal_q4_original_raw_manifest,
)

ROLES = (
    "native_stdout", "native_stdin", "paper_ticks", "owner_wal",
    "owner_cognition", "host_monotonic", "process_exit",
)


def _fixture(tmp_path: Path, *, mode: str = "two_moves"):
    root = tmp_path / "isolated-q4"
    root.mkdir(mode=0o700)
    evidence = {}
    for name in ROLES:
        p = root / (name + ".jsonl")
        p.write_bytes((json.dumps({"original": name}) + "\n").encode())
        evidence[name] = p
    return root, evidence, root / (mode + "-manifest.json")


@pytest.mark.parametrize("mode", ["two_moves", "stop_failure"])
def test_sealed_manifest_preserves_all_seven_exact_originals_without_world_pass(
    tmp_path, mode,
):
    root, evidence, output = _fixture(tmp_path, mode=mode)
    originals = {role: p.read_bytes() for role, p in evidence.items()}
    report = seal_q4_original_raw_manifest(
        root=root, evidence=evidence, output=output, mode=mode,
    )
    assert report == json.loads(output.read_text())
    assert report["schema"] == "q4-original-raw-evidence-dev-v1"
    assert report["status"] == "RAW_EVIDENCE_MANIFEST_SEALED_NOT_VERIFIED"
    assert report["real_world_dev_pass"] is False
    assert report["independent_paper_source_audited"] is False
    assert report["independent_q_audited"] is False
    assert report["qual_go"] is False and report["science_run"] is False
    assert output.stat().st_mode & 0o777 == 0o600
    for role, original in originals.items():
        assert evidence[role].read_bytes() == original
        assert report["evidence"][role]["sha256"] == hashlib.sha256(
            original,
        ).hexdigest()
        assert report["evidence"][role]["size_bytes"] == len(original)
        assert report["evidence"][role]["path"] == role + ".jsonl"
    with pytest.raises(Q4RawManifestHold, match="fresh isolated"):
        seal_q4_original_raw_manifest(
            root=root, evidence=evidence, output=output, mode=mode,
        )
    assert output.read_bytes()


@pytest.mark.parametrize("fault", [
    "missing", "empty", "alias", "hardlink", "symlink", "out_of_root",
    "parent_symlink", "missing_role", "extra_role", "invalid_mode",
])
def test_manifest_rejects_untrusted_source_shapes_before_output(
    tmp_path, fault,
):
    root, evidence, output = _fixture(tmp_path)
    if fault == "missing":
        evidence["native_stdout"].unlink()
    elif fault == "empty":
        evidence["native_stdout"].write_bytes(b"")
    elif fault == "alias":
        evidence["native_stdin"] = evidence["native_stdout"]
    elif fault == "hardlink":
        evidence["native_stdin"].unlink()
        os.link(evidence["native_stdout"], evidence["native_stdin"])
    elif fault == "symlink":
        source = evidence["native_stdout"]
        source.unlink()
        source.symlink_to(evidence["paper_ticks"])
    elif fault == "out_of_root":
        source = tmp_path / "foreign.jsonl"
        source.write_text("{}\n")
        evidence["native_stdout"] = source
    elif fault == "parent_symlink":
        fake_dir = root / "alias"
        fake_dir.symlink_to(root, target_is_directory=True)
        evidence["native_stdout"] = fake_dir / "native_stdout.jsonl"
    elif fault == "missing_role":
        evidence.pop("process_exit")
    elif fault == "extra_role":
        evidence["forged_success"] = root / "host_monotonic.jsonl"
    elif fault == "invalid_mode":
        pass
    with pytest.raises(Q4RawManifestHold):
        seal_q4_original_raw_manifest(
            root=root, evidence=evidence, output=output,
            mode="claim_world_pass" if fault == "invalid_mode" else "two_moves",
        )
    assert not output.exists()


def test_manifest_refuses_altered_native_bytes_mid_read(tmp_path, monkeypatch):
    root, evidence, output = _fixture(tmp_path)
    original_read = os.read
    touched = False

    def adversarial_read(fd, size):
        nonlocal touched
        chunk = original_read(fd, size)
        if not touched and chunk:
            touched = True
            evidence["native_stdout"].write_bytes(b'{"tampered":true}\n')
        return chunk

    monkeypatch.setattr(os, "read", adversarial_read)
    with pytest.raises(Q4RawManifestHold, match="changed during readback"):
        seal_q4_original_raw_manifest(
            root=root, evidence=evidence, output=output, mode="two_moves",
        )
    assert not output.exists()


def test_manifest_refuses_unsafe_output_and_root(tmp_path):
    root, evidence, output = _fixture(tmp_path)
    outside = tmp_path / "outside.json"
    with pytest.raises(Q4RawManifestHold):
        seal_q4_original_raw_manifest(
            root=root, evidence=evidence, output=outside,
            mode="two_moves",
        )
    parent = tmp_path / "symlinked-root"
    parent.symlink_to(root, target_is_directory=True)
    with pytest.raises(Q4RawManifestHold):
        seal_q4_original_raw_manifest(
            root=parent, evidence=evidence,
            output=parent / "manifest.json", mode="two_moves",
        )
    assert not output.exists()
