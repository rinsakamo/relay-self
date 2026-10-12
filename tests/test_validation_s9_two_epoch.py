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
