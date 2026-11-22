"""Schema3 original producer byte crosscheck (synthetic Original/Native/Paper).

The separate process proves internal consistency of supplied bytes only.
It does NOT establish external producer authenticity, real clock or Gemma.
"""
from __future__ import annotations

import asyncio
import hashlib
import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

from relay_self.bd1b_schema3_prelogin_source_dev import prepare_original_schema3_prelogin
from relay_self.bd1b_schema3_source_readback_dev import (
    BD1bSchema3ReadbackHold,
    audit_schema3_original_source_bytes,
)
from relay_self.cognitive_minimal_dev import initial_patterns_with_relative_move
from relay_self.exploration_schema_record_dev import canonical_exploration_snapshot
from relay_self.innate_schema import SchemaMode
from relay_self.resident_cognitive_work_owner_dev import ResidentCognitiveWorkOwner
from relay_self.self_owner_checkpoint_dev import verify_typed_generation
from relay_self.stage28b_retired_resident_typed_cut_dev import (
    capture_retired_resident_typed_world,
)
from test_stage28b_retired_typed_cut_dev import _setup


def _sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _write(path, value):
    path.write_text(json.dumps(value, sort_keys=True) + "\n")
    return {"path": str(path), "sha256": _sha(path)}


def _bundle(tmp_path, monkeypatch):
    bridge, paper, _, evidence = _setup(tmp_path, monkeypatch)
    for name in ("world_nether", "world_the_end"):
        sibling = tmp_path / name
        sibling.mkdir()
        (sibling / "region").mkdir()
        (sibling / "region" / "r.0.0.mca").write_bytes(b"dimension")
    for owner in bridge.owners.values():
        owner.files.cognition_file.unlink()
        owner.pattern_registry = initial_patterns_with_relative_move()
        assert owner.retained.pattern_registry is None
    resident = ResidentCognitiveWorkOwner(bridge.owners)
    bridge.cognitive_work = resident
    for sid in ("A", "B"):
        registry = bridge.owners[sid].pattern_registry
        snapshot = canonical_exploration_snapshot(
            self_id=sid, registry=registry, mode=SchemaMode.FULL,
        )
        resident.register_present_schema(sid, snapshot)
    prepare_original_schema3_prelogin(resident, evidence_dir=evidence)
    for sid, native in (("A", "original-A"), ("B", "original-B")):
        resident.bind_login(
            self_id=sid, native_session_id=native,
            world_epoch=0, world_tick=105,
        )
    resident.fence_self("A")
    retirement = asyncio.run(resident.retire_self("A"))
    resident.mark_offline(retirement)
    resident.bind_login(
        self_id="A", native_session_id="rejoined-A",
        world_epoch=0, world_tick=105,
    )
    for sid in ("A", "B"):
        resident.fence_self(sid)
        retirement = asyncio.run(resident.retire_self(sid))
        resident.mark_offline(retirement)
    store = evidence / "typed-world-self-generations"
    store.mkdir()
    generation = capture_retired_resident_typed_world(
        bridge=bridge, paper=paper, store=store, evidence_dir=evidence,
    ).generation
    assert all(c.schema_snapshot is not None for c in verify_typed_generation(generation))
    receipt_keys = (
        ("a_first_logout_receipt_file", "A-first-logout-original", "A", "original-A"),
        ("final_a_logout_receipt_file", "A-final-logout-original", "A", "rejoined-A"),
        ("final_b_logout_receipt_file", "B-final-logout-original", "B", "original-B"),
    )
    originals = {}
    for key, name, sid, native in receipt_keys:
        originals[key] = _write(evidence / (name + ".json"), {
            "self_id": sid, "native_session_id": native,
            "physical_issuer_revoked": True,
            "no_physical_inflight": True, "physical_wal_clear": True,
            "native_terminated": True, "stale_gpu_fenced": True,
            "peer_transport_drained": True,
        })
    def revision(fields):
        return "sha256:" + hashlib.sha256(json.dumps(
            fields, sort_keys=True, separators=(",", ":"),
        ).encode()).hexdigest()

    first_paper_raw = (
        b"P0D_TICK_READY boot=paper-boot-a source=PAPER_MAIN_THREAD\\n"
        b"P0D_RESIDENT boot=presence-boot-a actor=uuid-A status=JOIN\\n"
        b"P0D_RESIDENT boot=presence-boot-a actor=uuid-B status=JOIN\\n"
    )
    (evidence / "initial-native-paper-owned.log").write_bytes(first_paper_raw)
    first_paper_sha = hashlib.sha256(first_paper_raw).hexdigest()
    initial = []
    for sid, native in (("A", "original-A"), ("B", "original-B")):
        native_data = {
            "self_id": sid, "owner_identity": str(tmp_path / ("self-" + sid)),
            "resident_epoch": 1, "world_id": "world-1",
            "branch_id": "source", "world_epoch": 0,
            "native_session_id": native, "native_request_id": "probe-" + sid,
            "native_sequence": 2, "native_source_ref": "native-source-" + sid,
            "native_world_time": 105,
        }
        paper_data = {
            "paper_session_id": "paper-owned-original", "paper_pid": 1011,
            "paper_boot_id": "paper-boot-a", "presence_boot_id": "presence-boot-a",
            "paper_tick": 107,
            "paper_tick_ref": "paper-main-thread:p0d:paper-boot-a:nonce-1:sha256:"
            + "a" * 64,
            "paper_actor_uuid": "uuid-" + sid,
            "paper_log_sha256": first_paper_sha,
        }
        initial.append({
            **native_data, **paper_data,
            "native_revision": revision(native_data),
            "paper_revision": revision(paper_data),
        })
    (evidence / "initial-native-paper-source.json").write_text(
        json.dumps(initial, sort_keys=True) + "\n"
    )
    step = {
        "typed_world_self_generation": str(generation),
        "typed_world_self_saved_tick": 110,
        "initial_native_paper_source": initial,
        "paper_session_id": "paper-owned-original",
        "paper_boot": "presence-boot-a",
        "initial_paper_log_sha256": first_paper_sha,
        "a_actor_uuid": "uuid-A",
        "b_actor_uuid": "uuid-B",
        "a_original_native_session": "original-A",
        "b_original_native_session": "original-B",
        "a_relogin_evidence": {"native_session_id": "rejoined-A"},
        "real_l1_l2_gpu_executed": False,
        "b_actual_physical_action": False,
        "b_physical_wal_outcome": False,
        **originals,
    }
    report = {
        "classification": "REAL_PAPER_TWO_SELF_TYPED_STOPPED_WORLD_CUT_DEV",
        "world_uuid": "world-1",
        "schema3_prelogin_record": str(evidence / "stage28b-schema3-prelogin.json"),
        "schema3_original_typed_owner_qualified": True,
        "schema3_original_independent_audit": False,
        "typed_world_self_generation": str(generation),
        "typed_world_self_saved_tick": 110,
        "real_b_physical_action": False,
        "real_b_physical_wal_outcome": False,
        "real_gpu": False,
        "autonomous_l1_skill_selection": False,
        "real_60_second_autosave_attested": False,
        "steps": [step],
    }
    report_path = evidence / "resident-presence-result.json"
    _write(report_path, report)
    args = {
        "evidence_dir": evidence,
        "generation": generation,
        "expected_committed_sha256": _sha(generation / "COMMITTED.json"),
        "expected_producer_report_sha256": _sha(report_path),
        "expected_prelogin_manifest_sha256": _sha(
            evidence / "stage28b-schema3-prelogin.json"
        ),
        "expected_initial_source_sha256": _sha(
            evidence / "initial-native-paper-source.json"
        ),
    }
    return args


def test_cpu_original_schema3_source_crosscheck_and_separate_process(
    tmp_path, monkeypatch,
):
    args = _bundle(tmp_path, monkeypatch)
    root = args["evidence_dir"]
    before = {p.relative_to(root): p.read_bytes() for p in root.rglob("*") if p.is_file()}
    receipt = audit_schema3_original_source_bytes(**args)
    assert receipt.classification == "BD1B_SCHEMA3_SOURCE_BYTES_CROSSCHECK_CPU_ONLY"
    assert receipt.original_native_sessions == (
        ("A", "rejoined-A"), ("B", "original-B"),
    )
    assert receipt.original_paper_provenance_attested is False
    assert receipt.original_native_provenance_attested is False
    assert receipt.original_model_post_attested is False
    assert before == {p.relative_to(root): p.read_bytes()
                      for p in root.rglob("*") if p.is_file()}
    source_root = Path(__file__).resolve().parents[1]
    env = os.environ.copy()
    env["PYTHONPATH"] = (
        str(source_root / "src") + os.pathsep + str(source_root)
        + os.pathsep + env.get("PYTHONPATH", "")
    )
    result = subprocess.run([
        sys.executable, "-m", "experiments.bd1b_schema3_source_audit_dev",
        "--evidence-dir", str(args["evidence_dir"]),
        "--generation", str(args["generation"]),
        "--committed-sha256", args["expected_committed_sha256"],
        "--report-sha256", args["expected_producer_report_sha256"],
        "--prelogin-sha256", args["expected_prelogin_manifest_sha256"],
        "--initial-source-sha256", args["expected_initial_source_sha256"],
    ], capture_output=True, text=True, timeout=30, env=env)
    assert result.returncode == 0, result.stderr
    assert json.loads(result.stdout)["classification"] == receipt.classification
    assert before == {p.relative_to(root): p.read_bytes()
                      for p in root.rglob("*") if p.is_file()}


@pytest.mark.parametrize("variant", [
    "prelogin-cognition", "prelogin-wal", "inner-prelogin-mode",
    "model-post-false-claim", "report-native-replay", "report-foreign-world",
    "report-fake-physical", "quit-native-mismatch", "missing-initial",
    "typed-generation-drift", "report-unsafe-pin", "wrong-commit-pin",
])
def test_original_source_crosscheck_rejects_hostile_correlated_inputs(
    tmp_path, monkeypatch, variant,
):
    args = _bundle(tmp_path, monkeypatch)
    ev = args["evidence_dir"]
    report_path = ev / "resident-presence-result.json"
    if variant == "prelogin-cognition":
        (ev / "stage28b-schema3-A-prelogin-cognition.json").write_text("forged")
    elif variant == "prelogin-wal":
        (ev / "stage28b-schema3-B-prelogin-wal.json").write_text("forged")
    elif variant == "inner-prelogin-mode":
        path = ev / "stage28b-schema3-prelogin.json"
        value = json.loads(path.read_bytes())
        value["schema_modes"] = ["OFF", "FULL"]
        _write(path, value)
        args["expected_prelogin_manifest_sha256"] = _sha(path)
    elif variant == "model-post-false-claim":
        value = json.loads(report_path.read_bytes())
        value["real_gpu"] = True
        _write(report_path, value)
        args["expected_producer_report_sha256"] = _sha(report_path)
    elif variant == "report-native-replay":
        value = json.loads(report_path.read_bytes())
        value["steps"][0]["a_relogin_evidence"]["native_session_id"] = "original-A"
        _write(report_path, value)
        args["expected_producer_report_sha256"] = _sha(report_path)
    elif variant == "report-foreign-world":
        value = json.loads(report_path.read_bytes())
        value["world_uuid"] = "foreign-world"
        _write(report_path, value)
        args["expected_producer_report_sha256"] = _sha(report_path)
    elif variant == "report-fake-physical":
        value = json.loads(report_path.read_bytes())
        value["steps"][0]["b_actual_physical_action"] = True
        _write(report_path, value)
        args["expected_producer_report_sha256"] = _sha(report_path)
    elif variant == "quit-native-mismatch":
        path = ev / "B-final-logout-original.json"
        content = json.loads(path.read_bytes())
        content["native_session_id"] = "forged-B"
        _write(path, content)
        ref = json.loads(report_path.read_bytes())
        ref["steps"][0]["final_b_logout_receipt_file"]["sha256"] = _sha(path)
        _write(report_path, ref)
        args["expected_producer_report_sha256"] = _sha(report_path)
    elif variant == "missing-initial":
        (ev / "initial-native-paper-source.json").unlink()
    elif variant == "typed-generation-drift":
        (args["generation"] / "selves" / "A" / "owner-state.json").write_bytes(b"forged")
    elif variant == "report-unsafe-pin":
        args["expected_producer_report_sha256"] = "f" * 64
    else:
        args["expected_committed_sha256"] = "f" * 64
    with pytest.raises((BD1bSchema3ReadbackHold, ValueError, RuntimeError)):
        audit_schema3_original_source_bytes(**args)

@pytest.mark.parametrize("variant", [
    "native-foreign-session", "native-foreign-owner", "native-rejoin-epoch",
    "native-foreign-world", "native-sequence-boolean",
    "native-bad-revision", "native-duplicate-self",
    "paper-other-boot", "paper-boot-mismatch", "paper-other-pid",
    "paper-boolean-pid", "paper-other-actor", "paper-other-log",
    "paper-other-tick", "paper-nonce-source", "paper-bad-revision",
    "paper-extra-field", "report-other-actor", "initial-wrong-independent-pin",
    "raw-paper-source-tampered", "raw-paper-reported-hash-tampered",
])
def test_original_initial_receipt_recomputed_revisions_and_cross_source_fence(
    tmp_path, monkeypatch, variant,
):
    """A fresh SHA/JSON checksum by the same mutable producer grants no trust."""
    args = _bundle(tmp_path, monkeypatch)
    evidence = args["evidence_dir"]
    source = evidence / "initial-native-paper-source.json"
    report = evidence / "resident-presence-result.json"
    rows = json.loads(source.read_bytes())
    manifest = json.loads(report.read_bytes())

    native_fields = (
        "self_id", "owner_identity", "resident_epoch", "world_id",
        "branch_id", "world_epoch", "native_session_id", "native_request_id",
        "native_sequence", "native_source_ref", "native_world_time",
    )
    paper_fields = (
        "paper_session_id", "paper_pid", "paper_boot_id", "presence_boot_id",
        "paper_tick", "paper_tick_ref", "paper_actor_uuid", "paper_log_sha256",
    )

    if variant == "native-foreign-session":
        rows[0]["native_session_id"] = "post-reJOIN-A"
    elif variant == "native-foreign-owner":
        rows[0]["owner_identity"] = "/unowned/Self-A"
    elif variant == "native-rejoin-epoch":
        rows[0]["resident_epoch"] = 2
    elif variant == "native-foreign-world":
        rows[0]["world_id"] = "other-world"
    elif variant == "native-sequence-boolean":
        rows[0]["native_sequence"] = True
    elif variant == "native-bad-revision":
        rows[0]["native_revision"] = "sha256:" + "0" * 64
    elif variant == "native-duplicate-self":
        rows[1]["self_id"] = "A"
    elif variant == "paper-other-boot":
        rows[0]["paper_boot_id"] = "other-boot"
    elif variant == "paper-boot-mismatch":
        rows[0]["presence_boot_id"] = "other-boot"
    elif variant == "paper-other-pid":
        rows[1]["paper_pid"] = 2222
    elif variant == "paper-boolean-pid":
        rows[0]["paper_pid"] = True
    elif variant == "paper-other-actor":
        rows[1]["paper_actor_uuid"] = "uuid-A"
    elif variant == "paper-other-log":
        rows[0]["paper_log_sha256"] = "f" * 64
    elif variant == "paper-other-tick":
        rows[1]["paper_tick"] = 1008
    elif variant == "paper-nonce-source":
        rows[0]["paper_tick_ref"] = (
            "paper-main-thread:p0d:other-boot:nonce-1:sha256:" + "a" * 64
        )
    elif variant == "paper-bad-revision":
        rows[0]["paper_revision"] = "sha256:" + "0" * 64
    elif variant == "paper-extra-field":
        rows[0]["extra-model-permission"] = True
    elif variant == "report-other-actor":
        manifest["steps"][0]["a_actor_uuid"] = "other-actor"
    elif variant == "raw-paper-source-tampered":
        (evidence / "initial-native-paper-owned.log").write_bytes(
            b"forged-Paper-log"
        )
    elif variant == "raw-paper-reported-hash-tampered":
        manifest["steps"][0]["initial_paper_log_sha256"] = "f" * 64
    else:
        args["expected_initial_source_sha256"] = "f" * 64

    def revision(fields):
        return "sha256:" + hashlib.sha256(
            json.dumps(fields, sort_keys=True, separators=(",", ":")).encode()
        ).hexdigest()

    # Recalculate model-supplied inner revisions, source body and all
    # dependent report SHA values. They still cannot bypass source fences.
    if variant not in ("native-bad-revision", "native-duplicate-self"):
        rows[0]["native_revision"] = revision({
            key: rows[0][key] for key in native_fields
        })
    if variant not in ("paper-bad-revision", "paper-extra-field"):
        for row in rows:
            row["paper_revision"] = revision({
                key: row[key] for key in paper_fields
            })
    if variant not in ("initial-wrong-independent-pin", "report-other-actor"):
        _write(source, rows)
        manifest["steps"][0]["initial_native_paper_source"] = rows
        args["expected_initial_source_sha256"] = _sha(source)
    _write(report, manifest)
    args["expected_producer_report_sha256"] = _sha(report)

    with pytest.raises((BD1bSchema3ReadbackHold, ValueError, RuntimeError)):
        audit_schema3_original_source_bytes(**args)
