"""R one-shot M0.2 qualification: adversarial synthetic evidence envelopes only."""
from __future__ import annotations

import gzip
import hashlib
import json

import pytest

from experiments.standard_env import m02_paper_preworld as profile
from experiments.standard_env import m02_paper_qualification_audit as q
from test_rsee_m02_paper_dev_audit import dump, specimen


def synthetic(tmp_path, monkeypatch):
    log, native, commands, dev = specimen()
    root = tmp_path / "qualification-originals"
    root.mkdir()
    (root / "owned-worlds").mkdir()
    assets = tmp_path / "assets"
    assets.mkdir()
    props = b"server-ip=127.0.0.1\\nonline-mode=false\\n"
    (assets / "server.properties").write_bytes(props)
    initial_nbt = gzip.compress(b"\\x0a\\x00\\x00\\x00", mtime=0)
    initial_digest = hashlib.sha256(initial_nbt).hexdigest()
    witness = tmp_path / "independent-host-witness.json"
    pins = profile.load_manifest()["expected_assets_sha256"]
    report = {
        "owner": "S", "mode": "QUALIFICATION",
        "grant_id": q.QUAL_GRANT,
        "authorization_consumed": True,
        "classification": q.CLASSIFIED,
        "source_mode": "PAPER_CANDIDATE",
        "qual_engineering": False, "science_success": False,
        "production_go": False, "v_trials": 0,
        "virtual_m0_ledger_used": False,
        "retry_count": 0, "java_launch_count": 1, "node_session_count": 1,
        "new_world": "NEW_ISOLATED_PAPER",
        "seed": q.SEED, "paper_version": "1.21.8",
        "owned_world_cleaned": True, "port_released": True,
        "owned_java_pid_absent": True, "owned_node_pid_absent": True,
        "java_exit": 0, "node_exit": 0,
        "run_id": "a" * 32, "source_session_id": dev["source_session_id"],
        "java_pid": 10001, "node_pid": 10002,
        "world_seeded_properties_sha256": hashlib.sha256(
            props + f"level-seed={q.SEED}\\n".encode("ascii")).hexdigest(),
        "initial_level_dat_sha256": initial_digest,
        "initial_world_receipt": {
            "sha256": initial_digest,
            "size_bytes": len(initial_nbt),
            "snapshot_phase": "AFTER_SERVER_READY_SAVE_FLUSH_BEFORE_ACTION",
            "source_world_path": "s31a-ephemeral/level.dat",
        },
        "source_asset_hashes": pins,
        "native_stop_ack_seq": 8, "native_connection_end_seq": 9,
        "native_rows": 10,
        "movement": dev["movement"], "eating": dev["eating"],
    }
    originals = {
        "paper_server.log": log.encode(),
        "original_native.jsonl": b"".join(map(dump, native)),
        "owner_commands.jsonl": b"".join(map(dump, commands)),
        "qualification_producer.json": dump(report),
        "initial_world_level.dat": initial_nbt,
    }
    for k, v in originals.items():
        (root / k).write_bytes(v)
    (root / "SHA256SUMS").write_text("".join(
        hashlib.sha256(v).hexdigest() + "  " + k + "\n"
        for k, v in sorted(originals.items())))
    witness.write_bytes(dump({
        "github_run_id": "12345678", "github_run_attempt": 1,
        "java_pid": 10001, "node_pid": 10002,
        "java_absent": True, "node_absent": True,
        "loopback_port_released": True,
    }))
    monkeypatch.setattr(profile, "inspect", lambda _: {
        "classification": "M02_PAPER_ASSETS_PINNED_PREWORLD_REVIEW_ONLY",
        "physical_world_launches_by_review": 0,
    })
    return root, assets, witness, report


def verify(root, assets, witness):
    return q.review(root, expected_workflow_run="12345678",
                    witness_path=witness, admitted_assets=assets)


def rewrite(root, report):
    (root / "qualification_producer.json").write_bytes(dump(report))
    originals = [p for p in root.iterdir() if p.is_file() and p.name != "SHA256SUMS"]
    (root / "SHA256SUMS").write_text("".join(
        hashlib.sha256(p.read_bytes()).hexdigest() + "  " + p.name + "\n"
        for p in sorted(originals)))


def test_source_qualified_not_science(tmp_path, monkeypatch):
    root, assets, witness, report = synthetic(tmp_path, monkeypatch)
    result = verify(root, assets, witness)
    assert result["classification"] == q.PASS
    assert result["java_launches"] == 1 and result["grant_consumed"]
    assert result["independent_process_port_exit"]
    assert not result["science_go"] and not result["production_go"]


@pytest.mark.parametrize("key,value", [
    ("grant_id", "B0_SPENT"),
    ("mode", "DEV"), ("classification", "DEV_ONLY"),
    ("authorization_consumed", False), ("java_launch_count", 2),
    ("node_session_count", 2), ("retry_count", 1),
    ("science_success", True), ("production_go", True),
    ("virtual_m0_ledger_used", True), ("seed", "WRONG"),
    ("owned_java_pid_absent", False),
    ("new_world", "REUSED_GOLDEN"), ("initial_level_dat_sha256", "UNKNOWN"),
])
def test_fake_or_reused_qual_receipt_rejected(tmp_path, monkeypatch, key, value):
    root, assets, witness, report = synthetic(tmp_path, monkeypatch)
    report[key] = value
    rewrite(root, report)
    with pytest.raises(q.NotQualified):
        verify(root, assets, witness)


def test_native_bytes_and_host_witness_fail_closed(tmp_path, monkeypatch):
    root, assets, witness, _ = synthetic(tmp_path, monkeypatch)
    original = (root / "original_native.jsonl").read_bytes()
    (root / "original_native.jsonl").write_bytes(b"tampered\n")
    with pytest.raises(q.NotQualified, match="source original changed"):
        verify(root, assets, witness)
    (root / "original_native.jsonl").write_bytes(original)
    # Host witness is independently required, even when source digest exists.
    raw = json.loads(witness.read_text())
    raw["java_absent"] = False
    witness.write_bytes(dump(raw))
    with pytest.raises(q.NotQualified):
        verify(root, assets, witness)


def test_world_seed_and_saved_initial_bytes_are_independently_required(tmp_path, monkeypatch):
    root, assets, witness, report = synthetic(tmp_path, monkeypatch)
    (assets / "server.properties").write_bytes(b"altered World config")
    with pytest.raises(q.NotQualified, match="seed/properties hash"):
        verify(root, assets, witness)

    (assets / "server.properties").write_bytes(
        b"server-ip=127.0.0.1\\nonline-mode=false\\n")
    (root / "initial_world_level.dat").write_bytes(b"wrong original")
    rewrite(root, report)
    with pytest.raises(q.NotQualified, match="source bytes"):
        verify(root, assets, witness)
