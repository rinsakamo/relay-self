"""Stage28c2b: original native-session denylist comes from hashed Stage28b."""
from __future__ import annotations

import hashlib
import json
import shutil

import pytest

from relay_self.stage28c2b_historical_native_sessions_dev import (
    HistoricalSessionHold,
    inspect_original_stage28b_native_sessions,
)
from test_stage28c1_inert_restore_dev import _source


def _make_evidence(tmp_path):
    root = tmp_path / "stage28b-evidence"
    root.mkdir()
    trial = {
        "a_original_native_session": "native-first-A",
        "b_original_native_session": "native-retired-B",
        "a_relogin_evidence": {"native_session_id": "native-retired-A"},
    }
    report = {
        "classification": "REAL_PAPER_TWO_SELF_TYPED_STOPPED_WORLD_CUT_DEV",
        "steps": [trial],
    }
    path = root / "resident-presence-result.json"
    path.write_text(json.dumps(report), encoding="utf-8")
    other = root / "audit.log"
    other.write_text("synthetic native/Paper log")
    return root, report


def _pin(root):
    names = ["resident-presence-result.json", "audit.log"]
    checksum = "".join(
        hashlib.sha256((root / name).read_bytes()).hexdigest()
        + "  " + name + "\n"
        for name in sorted(names)
    )
    (root / "SHA256SUMS").write_text(checksum)
    return hashlib.sha256(checksum.encode()).hexdigest()


def _validate(root, generation, sha):
    return inspect_original_stage28b_native_sessions(
        root, generation, expected_manifest_sha256=sha, expected_files=2,
    )


def test_stage28c2b_native_history_source_is_immutable_hashed_trial(tmp_path, monkeypatch):
    generation = _source(tmp_path, monkeypatch)
    root, _ = _make_evidence(tmp_path)
    sha = _pin(root)
    result = _validate(root, generation, sha)
    assert result.manifest_files == 2
    assert result.original_a_initial == "native-first-A"
    assert result.original_a_rejoined == "native-retired-A"
    assert result.original_b_initial == "native-retired-B"
    assert set(result.historical_native_sessions) == {
        "native-first-A", "native-retired-A", "native-retired-B",
    }
    assert result.source_verified
    assert result.new_native_session_authorized is False
    assert result.source_manifest_sha256 == sha


def test_nested_generation_checksums_are_verified_even_when_outer_manifest_omits_them(
    tmp_path, monkeypatch,
):
    source = _source(tmp_path, monkeypatch)
    root, _ = _make_evidence(tmp_path)
    generation = root / source.name
    shutil.copytree(source, generation)
    files = sorted(p for p in root.rglob("*") if p.is_file() and p.name != "SHA256SUMS")
    checksum = "".join(
        hashlib.sha256(p.read_bytes()).hexdigest() + "  "
        + p.relative_to(root).as_posix() + "\n" for p in files
    )
    (root / "SHA256SUMS").write_text(checksum)
    sha = hashlib.sha256(checksum.encode()).hexdigest()
    inspect_original_stage28b_native_sessions(
        root, generation, expected_manifest_sha256=sha, expected_files=len(files),
    )
    (generation / "world" / "SHA256SUMS").write_text("altered")
    with pytest.raises(HistoricalSessionHold):
        inspect_original_stage28b_native_sessions(
            root, generation, expected_manifest_sha256=sha, expected_files=len(files),
        )


@pytest.mark.parametrize("failure", [
    "wrong-pin", "changed-bytes", "untracked-file", "wrong-final-a",
    "missing-b", "duplicate-entries", "missing-report",
])
def test_stage28c2b_session_history_rejects_unverified_source(
    tmp_path, monkeypatch, failure,
):
    generation = _source(tmp_path, monkeypatch)
    root, report = _make_evidence(tmp_path)
    sha = _pin(root)
    if failure == "wrong-pin":
        sha = "0" * 64
    elif failure == "changed-bytes":
        (root / "audit.log").write_text("modified")
    elif failure == "untracked-file":
        (root / "extra").write_text("not in manifest")
    elif failure == "wrong-final-a":
        report["steps"][0]["a_relogin_evidence"]["native_session_id"] = "foreign"
        (root / "resident-presence-result.json").write_text(json.dumps(report))
        sha = _pin(root)
    elif failure == "missing-b":
        del report["steps"][0]["b_original_native_session"]
        (root / "resident-presence-result.json").write_text(json.dumps(report))
        sha = _pin(root)
    elif failure == "duplicate-entries":
        manifest = root / "SHA256SUMS"
        manifest.write_bytes(manifest.read_bytes() + manifest.read_bytes().splitlines(keepends=True)[0])
        sha = hashlib.sha256(manifest.read_bytes()).hexdigest()
    else:
        (root / "resident-presence-result.json").unlink()
    with pytest.raises(HistoricalSessionHold):
        _validate(root, generation, sha)
