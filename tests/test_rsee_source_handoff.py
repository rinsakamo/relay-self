"""RSEE R2 bounded source handoff tests; no host, GPU, JVM or Node run."""
from __future__ import annotations

import json

import pytest

from experiments.standard_env import shared_runtime as r1
from experiments.standard_env import source_handoff as r2


@pytest.fixture
def sample(tmp_path):
    root = tmp_path / "native-originals"
    root.mkdir()
    original = root / "native_report.json"
    original.write_bytes(b'{"kind":"probe","session":"native-s"}\n')
    outcome = root / "action_outcome.jsonl"
    outcome.write_bytes(b'{"kind":"outcome","session":"native-s"}\n')
    index = r1.read_only_receipt_index({"native": original, "action": outcome})
    record = {
        "schema": r1.SCHEMA,
        "lane": "S",
        "source_head": "a" * 40,
        "environment_profile_sha256": "b" * 64,
        "source_session": "native-s",
        "world_identity": {"world_manifest_sha256": "c" * 64},
        "model_identity": None,
        "original_receipt_refs": [{"path": str(original), "sha256": index[str(original)]}],
        "action_outcome_refs": [{"path": str(outcome), "sha256": index[str(outcome)]}],
        "cleanup_observations": {
            "host_cancellation": "UNKNOWN",
            "backend_stop_ack": "UNKNOWN",
            "slot_release": "UNKNOWN",
            "gpu_quiescence": "UNKNOWN",
            "vram_release": "UNKNOWN",
            "owned_process_exit": "REPORTED_NOT_REATTESTED",
        },
        "terminal_classification": "SOURCE_REPORTED_OUTCOME",
        "evidence_sha256_index": index,
        "physical_execution_authorized": False,
        "science_qualified": False,
        "timeline_is_physical_proof": False,
    }
    kw = {
        "producer_lane": "S",
        "consumer_lane": "V",
        "expected_head": "a" * 40,
        "expected_profile_sha256": "b" * 64,
        "expected_session": "native-s",
        "receipt_root": root,
        "require_action_outcome": True,
    }
    return record, kw, original, outcome


@pytest.mark.parametrize(("producer", "consumer"), [
    ("S", "L"), ("S", "V"), ("L", "S"), ("L", "V"), ("V", "S"), ("V", "L"),
])
def test_plan_is_pure_and_never_grants(monkeypatch, producer, consumer):
    def forbidden(*_a, **_kw):
        pytest.fail("R2 plan cannot read originals or Git")
    monkeypatch.setattr(r1, "validate_evidence", forbidden)
    report = r2.plan(producer, consumer)
    assert report["classification"] == "RSEE_R2_PLAN_ONLY"
    assert report["physical_execution_authorized"] is False
    assert report["original_receipts"] == "NOT_READ"


def test_bytes_match_but_not_physical_attestation(sample):
    record, kw, original, outcome = sample
    original_bytes, outcome_bytes = original.read_bytes(), outcome.read_bytes()
    report = r2.audit(record, **kw)
    assert report["classification"] == "RSEE_R2_RAW_BYTES_MATCH_REVIEW_ONLY"
    assert report["original_files_sha256_checked"] == 2
    assert report["action_outcome_original_files_declared"] == 1
    assert report["native_provenance_attested"] is False
    assert report["source_native_event_semantics_attested"] is False
    assert report["backend_stop_ack_attested"] is False
    assert report["lease_release_attested"] is False
    assert report["science_qualified"] is False
    assert report["physical_execution_authorized"] is False
    assert original.read_bytes() == original_bytes
    assert outcome.read_bytes() == outcome_bytes


@pytest.mark.parametrize(("key", "new", "error"), [
    ("expected_head", "c" * 40, "source HEAD mismatch"),
    ("expected_profile_sha256", "d" * 64, "profile SHA mismatch"),
    ("expected_session", "foreign-session", "native session mismatch"),
    ("producer_lane", "L", "producer lane mismatch"),
])
def test_independent_consumer_binding(sample, key, new, error):
    record, kw, _, _ = sample
    kw[key] = new
    with pytest.raises(r2.HandoffRejected, match=error):
        r2.audit(record, **kw)


def test_no_action_receipt_and_empty_index_cannot_pass(sample):
    record, kw, _, _ = sample
    record["action_outcome_refs"] = []
    with pytest.raises(r2.HandoffRejected, match="required original Action/OUTCOME"):
        r2.audit(record, **kw)
    kw["require_action_outcome"] = False
    record["original_receipt_refs"] = []
    record["evidence_sha256_index"] = {}
    with pytest.raises(r2.HandoffRejected, match="original native receipts"):
        r2.audit(record, **kw)


def test_drift_missing_foreign_and_unreferenced_bytes_rejected(sample, tmp_path):
    record, kw, original, outcome = sample
    original.write_bytes(b"changed")
    with pytest.raises(r2.HandoffRejected, match="SHA256 mismatch"):
        r2.audit(record, **kw)
    original.write_bytes(b'{"kind":"probe","session":"native-s"}\n')
    kw["receipt_root"] = tmp_path
    # Nested root includes originals; this case is legal, but foreign root is not.
    assert r2.audit(record, **kw)["original_files_sha256_checked"] == 2
    kw["receipt_root"] = tmp_path / "other"
    kw["receipt_root"].mkdir()
    with pytest.raises(r2.HandoffRejected, match="foreign receipt root"):
        r2.audit(record, **kw)
    kw["receipt_root"] = original.parent
    record["evidence_sha256_index"][str(outcome.parent / "unreferenced")] = "f" * 64
    with pytest.raises(r2.HandoffRejected, match="unreferenced or missing"):
        r2.audit(record, **kw)


def test_symlinked_parent_or_special_display_rejected(sample, tmp_path):
    record, kw, original, _ = sample
    symlink = tmp_path / "indirect"
    symlink.symlink_to(original.parent, target_is_directory=True)
    record["original_receipt_refs"][0]["path"] = str(symlink / original.name)
    index = record["evidence_sha256_index"]
    index[str(symlink / original.name)] = index.pop(str(original))
    with pytest.raises(r2.HandoffRejected, match="symlinked ancestor"):
        r2.audit(record, **kw)
    del index[str(symlink / original.name)]
    index[str(original)] = r1.read_only_receipt_index({"native": original})[str(original)]
    record["original_receipt_refs"][0]["path"] = str(original)
    display = original.parent / "relayui-timeline.json"
    display.write_bytes(b"view")
    record["original_receipt_refs"][0] = {
        "path": str(display), "sha256": r1.read_only_receipt_index({"view": display})[str(display)]
    }
    index[str(display)] = record["original_receipt_refs"][0]["sha256"]
    del index[str(original)]
    with pytest.raises(r2.HandoffRejected, match="display projection"):
        r2.audit(record, **kw)


def test_duplicate_refs_and_missing_originals_rejected(sample):
    record, kw, _, _ = sample
    record["original_receipt_refs"].append(dict(record["original_receipt_refs"][0]))
    with pytest.raises(r2.HandoffRejected, match="duplicate original receipt"):
        r2.audit(record, **kw)
    record["original_receipt_refs"] = record["original_receipt_refs"][:1]
    record["timeline_is_physical_proof"] = True
    with pytest.raises(r2.HandoffRejected, match="R1 provenance envelope"):
        r2.audit(record, **kw)


def test_file_readback_rejects_duplicate_json_and_oversized(sample, tmp_path):
    record, kw, _, _ = sample
    envelope = tmp_path / "unmodified-envelope.json"
    envelope.write_text(json.dumps(record), encoding="utf-8")
    got = r2.audit_file(envelope, **kw)
    assert got["classification"] == "RSEE_R2_RAW_BYTES_MATCH_REVIEW_ONLY"
    envelope.write_text('{"lane":"S","lane":"V"}', encoding="utf-8")
    with pytest.raises(r2.HandoffRejected, match="invalid existing evidence envelope"):
        r2.audit_file(envelope, **kw)
    envelope.write_bytes(b" " * (r2.MAX_ENVELOPE_BYTES + 1))
    with pytest.raises(r2.HandoffRejected, match="oversized"):
        r2.audit_file(envelope, **kw)


def test_cli_pure_plan_and_invalid_verify_fails_closed(capsys, monkeypatch):
    def no_originals(*_args, **_kwargs):
        pytest.fail("not allowed for default R2 plan")

    monkeypatch.setattr(r2, "audit_file", no_originals)
    assert r2.main(["--from-lane", "S", "--to-lane", "V"]) == 0
    assert json.loads(capsys.readouterr().out)["classification"] == "RSEE_R2_PLAN_ONLY"
    assert r2.main(["--from-lane", "S", "--to-lane", "V",
                    "--envelope", "/tmp/synthetic.json"]) == 2
    report = json.loads(capsys.readouterr().out)
    assert report["classification"] == "RSEE_R2_HANDOFF_BLOCKED"
    assert report["physical_execution_authorized"] is False
