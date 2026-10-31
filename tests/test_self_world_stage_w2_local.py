"""W2 offline rehearsal: real subprocess replay; Linux preflight BLOCKED in CI.

The sample fixture deliberately self-mints ephemeral signing keys and archive
pins. Results MUST NOT qualify genuine external issuer or Minecraft raw stream.
"""
from __future__ import annotations

import hashlib
import json
import os
import sqlite3
import subprocess
import sys
from dataclasses import asdict
from pathlib import Path

import pytest

from adapters.mineflayer.self_world_stage_v_attestation import (
    fingerprint_for_public_pem,
)
from adapters.mineflayer.self_world_stage_w2_local_preflight import (
    inspect_w2_local_environment,
)
from adapters.mineflayer.self_world_stage_w_gate import StageWPersistentGrantLedger

pytest_plugins = ("test_self_world_stage_w_gate",)


def _args(sample, tmp_path: Path, *, archive_sha: str | None = None):
    public = tmp_path / "operator-public.pem"
    public.write_bytes(sample["public"])
    envelope = tmp_path / "signed.json"
    envelope.write_text(json.dumps(sample["envelope"]))
    request = tmp_path / "expected.json"
    request.write_text(json.dumps(asdict(sample["request"])))
    database = tmp_path / "spent.sqlite3"
    StageWPersistentGrantLedger.provision_new(database.resolve())
    command = [
        sys.executable, "-m",
        "adapters.mineflayer.self_world_stage_w2_ledger_worker",
        "--envelope", str(envelope.resolve()),
        "--expected-request", str(request.resolve()),
        "--public-pem", str(public.resolve()),
        "--public-sha256", fingerprint_for_public_pem(sample["public"]),
        "--run-id", sample["request"].run_id,
        "--archive", str(sample["archive_path"].resolve()),
        "--archive-sha256", archive_sha or sample["archive_sha"],
        "--ledger", str(database.resolve()),
    ]
    return command, database, public


def test_w2_two_actual_os_processes_only_one_succeeds_and_restart_fails(
    sample, tmp_path,
):
    command, database, _ = _args(sample, tmp_path)
    workers = []
    for i in range(2):
        workers.append(subprocess.Popen(
            [*command, "--receipt", str((tmp_path/f"w2-{i}.json").resolve())],
            stdout=subprocess.PIPE, stderr=subprocess.PIPE,
        ))
    results = [p.communicate(timeout=30) for p in workers]
    assert sorted(p.returncode for p in workers) == [0, 2]
    assert sum("W2_OFFLINE_RESERVED_READONLY" in out.decode()
               for out, _ in results) == 1
    with sqlite3.connect(database) as db:
        assert db.execute("SELECT COUNT(*) FROM grant_spent").fetchone() == (1,)
    # Fresh subprocess, no shared in-memory Stage V verifier set.
    again = subprocess.run(
        [*command, "--receipt", str((tmp_path/"w2-restarted.json").resolve())],
        capture_output=True, timeout=30, check=False,
    )
    assert again.returncode == 2
    assert b"W2_OFFLINE_DENIED" in again.stderr
    assert not (tmp_path/"w2-restarted.json").exists()
    receipts = list(tmp_path.glob("w2-[01].json"))
    assert len(receipts) == 1
    row = json.loads(receipts[0].read_text())
    assert row["persistent_grant_reserved"]
    assert row["independent_source_recomputed"]
    for field in (
        "external_issuer_identity_qualified",
        "raw_world_stream_qualified", "real_s10_commit_permitted",
        "physical_wait_permitted", "science_qualified",
    ):
        assert row[field] is False


@pytest.mark.parametrize("case", ("wrong_source_pin", "wrong_signer_pin"))
def test_w2_external_pin_mismatch_leaves_ledger_unused(sample, tmp_path, case):
    command, database, _ = _args(sample, tmp_path)
    flag = "--archive-sha256" if case == "wrong_source_pin" else "--public-sha256"
    i = command.index(flag)
    command[i+1] = "0" * 64
    proc = subprocess.run(
        [*command, "--receipt", str((tmp_path/"denied.json").resolve())],
        capture_output=True, timeout=30, check=False,
    )
    assert proc.returncode == 2
    assert not (tmp_path/"denied.json").exists()
    with sqlite3.connect(database) as db:
        assert db.execute("SELECT COUNT(*) FROM grant_spent").fetchone() == (0,)


def test_w2_local_preflight_sees_digest_and_sqlite_but_denies_same_user_key(
    sample, tmp_path,
):
    _, database, public = _args(sample, tmp_path)
    key = tmp_path/"issuer-private-test-only.pem"
    key.write_text("THIS IS NOT A PRIVATE KEY")
    key.chmod(0o600)
    uid = os.geteuid() if hasattr(os, "geteuid") else -1
    raw = sample["archive_path"]  # SYNTHETIC extraction, not native raw
    report = inspect_w2_local_environment(
        public_pem_path=public.resolve(),
        expected_public_sha256=fingerprint_for_public_pem(sample["public"]),
        raw_source_path=raw.resolve(),
        expected_raw_sha256=hashlib.sha256(raw.read_bytes()).hexdigest(),
        existing_ledger_path=database.resolve(),
        issuer_private_key_path=key.resolve(),
        issuer_uid=uid + 1, consumer_uid=uid,
    )
    assert report.checks["pinned_public_key_digest_matches"]
    assert report.checks["externally_pinned_raw_digest_matches"]
    assert report.checks["sqlite_ledger_readonly_integrity"]
    assert report.checks["sqlite_ledger_owner_mode_0600"]
    assert not report.checks["issuer_private_key_unreadable_to_consumer"]
    assert report.classification == "W2_LOCAL_PREFLIGHT_BLOCKED"
    assert not report.distinct_os_identity_qualified
    assert not report.raw_native_stream_qualified
    assert not report.physical_s10_commit_permitted


def test_w2_local_preflight_denies_modified_raw_and_bad_ledger(sample, tmp_path):
    _, database, public = _args(sample, tmp_path)
    raw = tmp_path/"tampered-original.json"
    raw.write_bytes(sample["archive_path"].read_bytes() + b"\n")
    private = tmp_path/"test-only-private.pem"
    private.write_text("not real private")
    private.chmod(0o600)
    uid = os.geteuid() if hasattr(os, "geteuid") else -1
    with sqlite3.connect(database) as db:
        db.execute("DROP TABLE grant_spent")
    result = inspect_w2_local_environment(
        public_pem_path=public.resolve(),
        expected_public_sha256=fingerprint_for_public_pem(sample["public"]),
        raw_source_path=raw.resolve(),
        expected_raw_sha256=sample["archive_sha"],
        existing_ledger_path=database.resolve(),
        issuer_private_key_path=private.resolve(),
        issuer_uid=uid+1, consumer_uid=uid,
    )
    assert not result.checks["externally_pinned_raw_digest_matches"]
    assert not result.checks["sqlite_ledger_readonly_integrity"]
    assert result.classification == "W2_LOCAL_PREFLIGHT_BLOCKED"


def test_w2_local_preflight_report_is_unique_and_non_authorizing(sample, tmp_path):
    _, database, public = _args(sample, tmp_path)
    private = tmp_path/"private-must-be-denied.pem"
    private.write_text("not a real private key")
    raw = sample["archive_path"]
    uid = os.geteuid() if hasattr(os, "geteuid") else -1
    output = (tmp_path/"w2-preflight.json").resolve()
    cmd = [
        sys.executable, "-m",
        "adapters.mineflayer.self_world_stage_w2_local_preflight",
        "--public-pem", str(public.resolve()),
        "--public-sha256", fingerprint_for_public_pem(sample["public"]),
        "--raw-source", str(raw.resolve()),
        "--raw-sha256", sample["archive_sha"],
        "--ledger", str(database.resolve()),
        "--issuer-private-key", str(private.resolve()),
        "--issuer-uid", str(uid+1), "--consumer-uid", str(uid),
        "--report", str(output),
    ]
    p = subprocess.run(cmd, capture_output=True, timeout=30, check=False)
    assert p.returncode == 2
    assert output.exists()
    result = json.loads(output.read_text())
    assert result["classification"] == "W2_LOCAL_PREFLIGHT_BLOCKED"
    assert result["blockers"]
    assert result["raw_native_stream_qualified"] is False
    assert result["physical_s10_commit_permitted"] is False
    assert result["science_qualified"] is False
    # Frozen first witness cannot be overwritten.
    again = subprocess.run(cmd, capture_output=True, timeout=30, check=False)
    assert again.returncode != 0
    assert json.loads(output.read_text()) == result
