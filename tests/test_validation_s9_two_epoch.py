"""V S8/S9: bounded reported evidence, no causal science or replay."""
from __future__ import annotations

import copy
import json

import pytest

from experiments.validation import s9_two_epoch_review as v


def original():
    return json.loads(v.REPORT.read_text(encoding="utf-8"))


def test_s9_two_action_two_memory_report_not_causal_learning():
    output = v.review(original())
    assert output["s9"] == "TWO_CONTROLLED_NATIVE_OUTCOMES_TWO_MEMORIES_REPORTED"
    assert output["s8"] == "ONE_OUTCOME_THEN_FAIL_CLOSED_RECALL_OBSERVED_REPORTED"
    assert output["memory_effect_on_second_action"] == "NOT_DEMONSTRATED"
    assert output["cheap_control_counterfactual"] == "NOT_RUN_UNMATCHED_S8_S9"
    assert output["r9_qualification"].startswith("NOT_CHECKED")
    assert output["v_science_gates"]["G3"].startswith("NO_GO")
    assert output["science_qualified"] is False
    assert output["production_qualified"] is False
    assert output["new_physical_world_runs"] == 0


@pytest.mark.parametrize(("trial", "key", "value"), [
    ("s9", "source_head", v.S8_HEAD),
    ("s9", "parent_source_head", "0" * 40),
    ("s9", "session_id", "foreign"),
    ("s9", "target_type", "NATURAL_HOSTILE_ZOMBIE"),
    ("s9", "native_executed_outcomes_reported", 3),
    ("s9", "observed_memories_retained_reported", 3),
    ("s9", "read_only_recall_reported", False),
    ("s9", "memory_caused_second_decision_attested", True),
    ("s9", "summon_ack_verified", True),
    ("s9", "world_global_absence_attested", True),
    ("s9", "native_stop_ack_verified", True),
    ("s9", "s10_learning_updates_reported", 1),
    ("s9", "s11_habit_grants_reported", 1),
    ("s9", "l2_model_posts_reported", 1),
    ("s9", "original_bridge_bytes_independently_read_by_v", True),
    ("s9", "r9_exact_head_verified_by_v", True),
    ("s9", "r9_source_receipt_verified_by_v", True),
    ("s9", "matched_cheap_control_performed", True),
    ("s9", "learned_advantage_vs_matched_cheap_control", True),
    ("s9", "heldout_transfer_verified", True),
    ("s9", "measured_resource_adjusted_gain", True),
    ("s9", "grant_consumed", False),
    ("s9", "retry_count", 1),
    ("s9", "native_bridge_received_sha256", "a" * 64),
    ("s9", "pre_posting_index_sha256", "a" * 64),
    ("s9", "native_bridge_received_lines", 0),
    ("s9", "action_distances_m_reported", [0.7, 0.9]),
    ("s8", "second_action_closed", True),
    ("s8", "retained_observations_reported", 2),
    ("s8", "source_sha256_received", "a" * 64),
])
def test_no_unsupported_physical_or_scientific_promotion(trial, key, value):
    ledger = original()
    ledger[trial][key] = value
    with pytest.raises(v.VRejected):
        v.review(ledger)


def test_s8_s9_different_experiment_not_matched_control():
    row = original()
    assert row["s8"]["source_head"] != row["s9"]["source_head"]
    assert row["s8"]["native_actions_reported"] == 1
    assert row["s9"]["native_executed_outcomes_reported"] == 2
    assert v.review(row)["cheap_control_counterfactual"] == "NOT_RUN_UNMATCHED_S8_S9"


def test_foreign_keys_not_admitted():
    row = original()
    row["s9"]["goal_success"] = True
    with pytest.raises(v.VRejected):
        v.review(row)
    row = original()
    row["r9_source_head"] = "claimed"
    with pytest.raises(v.VRejected):
        v.review(row)


def test_cli_rejects_symlink_or_missing_original_readonly(tmp_path, capsys):
    original_bytes = v.REPORT.read_bytes()
    alias = tmp_path / "ref"
    alias.symlink_to(v.REPORT)
    assert v.main(["--report", str(alias)]) == 2
    assert json.loads(capsys.readouterr().out)["classification"] == "V_S9_EVIDENCE_REJECTED"
    assert v.main(["--report", str(tmp_path / "missing")]) == 2
    capsys.readouterr()
    assert v.main([]) == 0
    result = json.loads(capsys.readouterr().out)
    assert result["s8_s9_permissions"] == "BOTH_CONSUMED_NO_REPLAY"
    assert v.REPORT.read_bytes() == original_bytes


def test_report_manipulation_cannot_hide_no_source():
    row = copy.deepcopy(original())
    row["evidence_origin"] = "R9_VERIFIED_RAW_ORIGINALS"
    with pytest.raises(v.VRejected):
        v.review(row)


def synthetic_r6_claim():
    """Source-shaped fixture only; NOT a host original readback."""
    return {
        "classification": v.R6_REVIEW_CLASS,
        "source_head": v.S9_HEAD,
        "source_session": "dacf338b-4ba9-4e91-8eea-d4aebd0aef22",
        "received_sha256_verified": v.S9_IN,
        "sent_sha256_verified": v.S9_OUT,
        "received_original_lines": 39,
        "sent_attempt_lines": 14,
        "retained_memory_count": 2,
        "distinct_reported_action_ids": 2,
        "source_scope": "MINEFLAYER_BRIDGE_JSONL_NOT_MINECRAFT_TCP",
        "hash_expectation_origin":
            "S9_OPERATOR_REPORT_NOT_INDEPENDENT_PHYSICAL_ATTESTATION",
        "r1_envelope_verified": False,
        "r2_raw_handoff_admitted": False,
        "typed_s16_semantics_attested": False,
        "memory_causal_effect_attested": False,
        "native_stop_ack_attested": False,
        "goal_success_attested": False,
        "science_qualified": False,
        "v_admission_granted": False,
        "physical_execution_authorized": False,
        "side_effects": "READ_ONLY_NO_WRITE_NO_PROCESS",
    }


def test_s9_external_staging_gate_is_not_memory_cognitive_policy():
    out = v.review(original())
    assert out["memory_count_gated_external_epoch2"] == "YES_IN_FROZEN_S9_SOURCE"
    assert out["memory_hint_controls_l0_choice"] == "NO_IN_FROZEN_S9_SOURCE"
    assert out["memory_effect_on_second_action"] == "NOT_DEMONSTRATED"


def test_valid_synthetic_r6_result_is_review_only_not_host_attestation():
    x = v.review_r6_result(synthetic_r6_claim())
    assert x["pinned_r6_source_head"] == v.R6_HEAD
    assert x["s9_source_head"] == v.S9_HEAD
    assert x["r1_envelope"] == "NOT_ADMITTED"
    assert x["r2_typed_action_originals"] == "NOT_ADMITTED"
    assert x["v_independent_original_bytes_read"] is False
    assert x["r6_result_origin_independently_attested"] is False
    assert x["science_qualified"] is False
    assert x["product_qualified"] is False


@pytest.mark.parametrize(("field", "value"), [
    ("classification", "RSEE_R1_ORIGINALS_ADMITTED"),
    ("source_head", v.S8_HEAD),
    ("source_session", "foreign"),
    ("received_sha256_verified", "a" * 64),
    ("sent_sha256_verified", v.S9_IN),
    ("retained_memory_count", 1),
    ("distinct_reported_action_ids", 1),
    ("source_scope", "MINECRAFT_TCP_PACKETS"),
    ("r1_envelope_verified", True),
    ("r2_raw_handoff_admitted", True),
    ("typed_s16_semantics_attested", True),
    ("memory_causal_effect_attested", True),
    ("native_stop_ack_attested", True),
    ("goal_success_attested", True),
    ("science_qualified", True),
    ("v_admission_granted", True),
    ("physical_execution_authorized", True),
])
def test_r6_claim_cannot_promote_original_or_science(field, value):
    x = synthetic_r6_claim()
    x[field] = value
    with pytest.raises(v.VRejected):
        v.review_r6_result(x)


def test_r6_unexpected_claim_field_rejected():
    x = synthetic_r6_claim()
    x["model_advantage"] = True
    with pytest.raises(v.VRejected):
        v.review_r6_result(x)


def test_r6_cli_synthetic_candidate_cannot_claim_host_originals(tmp_path, capsys):
    candidate = tmp_path / "synthetic_r6_result.json"
    candidate.write_text(json.dumps(synthetic_r6_claim()), encoding="utf-8")
    assert v.main(["--r6-result", str(candidate)]) == 0
    out = json.loads(capsys.readouterr().out)
    assert out["r6_review_candidate"]["v_independent_original_bytes_read"] is False
    assert out["r6_review_candidate"]["science_qualified"] is False
    symlink = tmp_path / "symlink"
    symlink.symlink_to(candidate)
    assert v.main(["--r6-result", str(symlink)]) == 2
    candidate.write_text(json.dumps({**synthetic_r6_claim(), "science_qualified": True}))
    assert v.main(["--r6-result", str(candidate)]) == 2
