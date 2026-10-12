"""V S6 source-report identity and scientific overclaim negatives."""
from __future__ import annotations

import copy
import json

import pytest

from experiments.validation import s6_report_review as v


def original():
    return json.loads(v.REPORT.read_text(encoding="utf-8"))


def test_pinned_issue_report_is_not_raw_or_scientific_go():
    out = v.assess(original())
    assert out["engineering"]["r5_original_admission"] == "S6_DERIVED_ONLY_RAW_NOT_ARCHIVED"
    assert out["v_host_original_bytes_read"] is False
    assert out["behavioral"]["reported_physical_actions"] == 1
    assert out["behavioral"]["s10_learning_updates"] == 0
    assert out["scientific"]["science_qualified"] is False
    assert out["scientific"]["G3"].startswith("NO_GO")
    assert out["s7_physical"] == "NOT_RUN"


@pytest.mark.parametrize(("key", "value"), [
    ("source_head", v.S7_HEAD),
    ("r5_source_head", v.S6_HEAD),
    ("target_type", "NATURAL_HOSTILE_ZOMBIE"),
    ("native_outer_frames_reported", 188),
    ("physical_retry_reported", 1),
    ("retained_observational_memories_reported", 2),
    ("s10_updates_reported", 1),
    ("l2_model_calls_reported", 1),
    ("task_goal_attested", True),
    ("native_predecode_bridge_original_archived", True),
    ("s6_late_reconstruction_allowed", True),
    ("r1_r2_original_action_envelope_present", True),
    ("native_stop_ack_attested", True),
    ("same_source_cheap_control_run", True),
    ("heldout_goal_outcomes_attested", True),
    ("independent_transfer_attested", True),
    ("physical_origin_independently_verified_by_v", True),
])
def test_no_historical_source_or_science_upgrade(key, value):
    row = original()
    row[key] = value
    with pytest.raises(v.VRejected):
        v.assess(row)


def test_reported_index_are_distinct_documents_not_missing_sha():
    row = original()
    row["sha_indexes_reported"]["SHA256SUMS"] = copy.deepcopy(
        row["sha_indexes_reported"]["FINAL_SHA256SUMS"]
    )
    with pytest.raises(v.VRejected):
        v.assess(row)
    row = original()
    row["sha_indexes_reported"]["FINAL_SHA256SUMS"]["checked_entries"] = 32
    with pytest.raises(v.VRejected):
        v.assess(row)


def test_derived_memory_never_becomes_original_action_receipt():
    row = original()
    row["derived_files_reported"]["native_bridge_received_original.jsonl"] = (
        "a" * 64
    )
    with pytest.raises(v.VRejected):
        v.assess(row)


def test_no_attestation_from_synthetic_digest_shape():
    row = original()
    row["native_evidence_sha256_reported"] = "a" * 64
    with pytest.raises(v.VRejected):
        v.assess(row)


def test_symlink_source_rejected_and_report_is_not_mutated(tmp_path):
    original_bytes = v.REPORT.read_bytes()
    link = tmp_path / "report.json"
    link.symlink_to(v.REPORT)
    assert v.main(["--report", str(link)]) == 2
    assert v.REPORT.read_bytes() == original_bytes
    assert v.main([]) == 0
