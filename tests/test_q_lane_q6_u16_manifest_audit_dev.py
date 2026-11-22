"""Q6 hostile checks: real U16 manifest layout, fully synthetic source bytes.

Never treats these fixtures as real Native/Paper or a World DEV result.
"""
from __future__ import annotations

import hashlib
import json
import os

import pytest

from experiments.q_lane_q6_u16_manifest_audit_dev import (
    Q6ManifestHold,
    audit_u16_manifest,
)

ROLES = (
    "native_stdout", "native_stdin", "paper_ticks", "owner_wal",
    "owner_cognition", "host_monotonic", "process_exit",
)


def _file(root, role):
    return root / (role + ".jsonl")


def _seal(root, mode="two_moves"):
    evidence = {}
    for role in ROLES:
        p = _file(root, role)
        p.write_bytes(("{\"source\":\"" + role + "\"}\n").encode())
        s = p.stat()
        evidence[role] = {
            "path": p.name,
            "sha256": hashlib.sha256(p.read_bytes()).hexdigest(),
            "size_bytes": s.st_size,
            "device": s.st_dev,
            "inode": s.st_ino,
            "mtime_ns": s.st_mtime_ns,
        }
    manifest = {
        "schema": "q4-original-raw-evidence-dev-v1",
        "trial": mode,
        "status": "RAW_EVIDENCE_MANIFEST_SEALED_NOT_VERIFIED",
        "real_world_dev_pass": False,
        "qual_go": False,
        "science_run": False,
        "independent_paper_source_audited": False,
        "independent_q_audited": False,
        "evidence": evidence,
    }
    path = root / "raw-manifest.json"
    path.write_text(json.dumps(manifest) + "\n", encoding="utf-8")
    return manifest, path


def test_seven_original_raw_files_and_manifest_hashes_match(tmp_path):
    _, path = _seal(tmp_path)
    value = audit_u16_manifest(
        root=tmp_path, manifest_path=path, trial="two_moves",
    )
    assert value["roles"] == 7
    assert value["world_dev_pass"] is False
    assert "moves" not in value


def test_stop_fault_trial_separate_mode_cannot_claim_two_move_result(tmp_path):
    _, path = _seal(tmp_path, "stop_failure")
    audit_u16_manifest(root=tmp_path, manifest_path=path, trial="stop_failure")
    with pytest.raises(Q6ManifestHold):
        audit_u16_manifest(
            root=tmp_path, manifest_path=path, trial="stop_failure",
            inspect_two_moves=True,
        )
    with pytest.raises(Q6ManifestHold):
        audit_u16_manifest(root=tmp_path, manifest_path=path, trial="two_moves")


@pytest.mark.parametrize("mutate", [
    "changed_source", "same_size_same_mtime", "missing_source",
    "symlink", "foreign_source", "alias", "digest",
    "false_world_pass", "false_independent_q", "missing_role",
    "duplicate_json_key", "wrong_version", "zero_size", "hardlink",
])
def test_hostile_u16_raw_manifest_is_refused(tmp_path, mutate):
    payload, manifest = _seal(tmp_path)
    target = _file(tmp_path, "native_stdout")
    if mutate == "changed_source":
        target.write_bytes(b"changed original file\n")
    elif mutate == "same_size_same_mtime":
        before = target.stat()
        target.write_bytes(b"x" * before.st_size)
        os.utime(target, ns=(before.st_atime_ns, before.st_mtime_ns))
    elif mutate == "missing_source":
        target.unlink()
    elif mutate == "symlink":
        target.unlink()
        other = tmp_path / "other.jsonl"
        other.write_bytes(b"foreign\n")
        target.symlink_to(other)
    elif mutate == "foreign_source":
        payload["evidence"]["native_stdout"]["path"] = "../external.jsonl"
    elif mutate == "alias":
        payload["evidence"]["native_stdout"] = dict(
            payload["evidence"]["native_stdin"],
        )
    elif mutate == "digest":
        payload["evidence"]["native_stdout"]["sha256"] = "0" * 64
    elif mutate == "false_world_pass":
        payload["real_world_dev_pass"] = True
    elif mutate == "false_independent_q":
        payload["independent_q_audited"] = True
    elif mutate == "missing_role":
        del payload["evidence"]["process_exit"]
    elif mutate == "duplicate_json_key":
        manifest.write_bytes(
            manifest.read_bytes().rstrip()[:-1]
            + b', "trial": "two_moves"}\n'
        )
    elif mutate == "wrong_version":
        payload["schema"] = "unrecognized"
    elif mutate == "zero_size":
        target.write_bytes(b"")
    else:
        target.unlink()
        original = _file(tmp_path, "native_stdin")
        os.link(original, target)
    if mutate not in (
        "changed_source", "same_size_same_mtime", "missing_source",
        "symlink", "zero_size", "hardlink", "duplicate_json_key",
    ):
        manifest.write_text(json.dumps(payload) + "\n", encoding="utf-8")
    with pytest.raises((Q6ManifestHold, ValueError)):
        audit_u16_manifest(
            root=tmp_path, manifest_path=manifest, trial="two_moves",
        )


def test_synthetic_files_never_fake_native_wal_two_moves(tmp_path):
    _, path = _seal(tmp_path)
    with pytest.raises(Q6ManifestHold, match="Native/WAL"):
        audit_u16_manifest(
            root=tmp_path, manifest_path=path,
            trial="two_moves", inspect_two_moves=True,
        )
