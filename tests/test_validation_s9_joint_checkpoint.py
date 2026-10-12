"""V R6 operator-WLS2 report intake and S10/L4 scientific controls."""
from __future__ import annotations

import copy
import json

import pytest

from experiments.validation import s9_joint_checkpoint as v


def source():
    return json.loads(v.CHECKPOINT.read_text(encoding="utf-8"))


def test_real_r_operator_audit_is_not_v_host_attestation_or_scientific_go():
    d = v.adjudicate(source())
    assert d["engineering_g0_r_host"].startswith("REAL_S9_ORIGINAL_BYTE_READBACK")
    assert d["engineering_g0_v_direct"] == "NOT_RUN"
    assert d["engineering_r1_r2_typed_s16"] == "NOT_ADMITTED"
    assert d["s10_offline_ablation"] == "MEMORY_RECALL_CONTRAST_NO_L0_CHOICE_DELTA"
    assert d["l4_prospective_comparator"] == "CONTRACT_QUALIFIED_NO_PHYSICAL_PAIRS"
    assert d["scientific_g3"].startswith("NO_GO")
    assert d["science_qualified"] is False and d["product_qualified"] is False
    assert d["new_physical_runs"] == d["new_model_posts"] == 0


@pytest.mark.parametrize(("lane", "name", "value"), [
    ("r6", "source_head", "a" * 40),
    ("r6", "physical_producer_head", "a" * 40),
    ("r6", "source_session", "foreign"),
    ("r6", "exit_status", 1),
    ("r6", "read_only", False),
    ("r6", "independent_v_host_readback", True),
    ("r6", "existing_files_prepost_identical", 56),
    ("r6", "existing_r1_envelope_qualified", True),
    ("r6", "independent_r2_typed_action_outcome_qualified", True),
    ("r6", "goal_success_attested", True),
    ("r6", "memory_caused_action_attested", True),
    ("r6", "science_qualified", True),
    ("r6", "replay_count", 1),
    ("s10", "l0_action_equal", False),
    ("s10", "measured_goal_delta", 0),
    ("s10", "scientific_go", True),
    ("l4", "independent_original_goals_verified", True),
    ("l4", "physical_matched_retained_vs_cheap_trials", 2),
    ("l4", "scientific_go", True),
])
def test_forged_source_qualification_is_rejected(lane, name, value):
    data = source()
    data[lane][name] = value
    with pytest.raises(v.JointRejected):
        v.adjudicate(data)


def test_different_sha_index_scopes_not_conflated():
    data = source()
    data["r6"]["pre_post_index"] = copy.deepcopy(data["r6"]["final_index"])
    with pytest.raises(v.JointRejected):
        v.adjudicate(data)
    data = source()
    data["r6"]["final_index"]["entries"] = 47
    with pytest.raises(v.JointRejected):
        v.adjudicate(data)


def test_original_bridge_and_derived_memory_have_distinct_hashes_and_sizes():
    data = source()
    data["r6"]["original_files"]["session_events.jsonl"]["sha256"] = (
        data["r6"]["original_files"]["native_bridge_received_original.jsonl"]["sha256"]
    )
    with pytest.raises(v.JointRejected):
        v.adjudicate(data)
    data = source()
    data["r6"]["original_files"]["s3_observed_memory.json"]["bytes"] = 21924
    with pytest.raises(v.JointRejected):
        v.adjudicate(data)


def test_missing_foreign_receipt_fields_fail_closed():
    data = source()
    data["r6"]["original_files"]["native_bridge_sent_original.jsonl"].pop("lines")
    with pytest.raises(v.JointRejected):
        v.adjudicate(data)
    data = source()
    data["r6"]["native_action_success"] = True
    with pytest.raises(v.JointRejected):
        v.adjudicate(data)


def test_cli_never_reads_original_world_or_permits_replay(tmp_path, capsys):
    original_bytes = v.CHECKPOINT.read_bytes()
    assert v.main([]) == 0
    d = json.loads(capsys.readouterr().out)
    assert d["new_physical_runs"] == 0
    alias = tmp_path / "alias"
    alias.symlink_to(v.CHECKPOINT)
    assert v.main(["--report", str(alias)]) == 2
    assert v.CHECKPOINT.read_bytes() == original_bytes
