"""Q1j read-only typed SelfOwnerCut S1 historical WAL/Git attacks (offline)."""
from __future__ import annotations

import copy
import hashlib
import json
import subprocess
from pathlib import Path

import pytest

from experiments.q_lane_typed_owner_move_place_join_dev import (
    QTypedOriginalSourceJoinHold,
    audit_q1j_typed_owner_move_place_git_join,
)
from test_q_lane_original_move_place_wal_dev import (
    _git_pre_s2_source,
    _setup,
)
from test_q_lane_typed_owner_cut_audit_dev import _cut_payload


def _canon(value):
    return (json.dumps(
        value, sort_keys=True, separators=(",", ":"), ensure_ascii=False,
        allow_nan=False,
    ) + "\n").encode()


def _sha(raw):
    return hashlib.sha256(raw).hexdigest()


def _fixture(tmp_path: Path, *, fault: str | None = None, schema: int = 1):
    root, wal = _setup(tmp_path)
    owner = copy.deepcopy(_cut_payload(schema=schema))
    if fault == "unbound-s1-skill":
        owner["skills"][0]["execution_id"] = "foreign-skill"
    elif fault == "unbound-s1-intent":
        owner["skills"][0]["intent_id"] = "foreign-intent"
        owner["intent_events"][0]["intent_id"] = "foreign-intent"
        owner["intent_events"][1]["intent_id"] = "foreign-intent"
    elif fault == "s1-success":
        owner["skills"][0]["events"][-1]["state"] = "succeeded"
    elif fault == "s1-incomplete":
        owner["intent_events"] = owner["intent_events"][:1]
    elif fault == "s1-intent-failed":
        owner["intent_events"][1]["kind"] = "failed"
    elif fault == "wrong-generation":
        owner["generation_id"] = "g-000000000005"
    elif fault == "wrong-branch":
        owner["branch_id"] = "foreign-branch"
    elif fault == "wrong-native-session":
        owner["former_native_session_id"] = "other-session"
    elif fault == "unknown-skill-end":
        owner["skills"][0]["events"][-1]["state"] = "FAKE_FINISHED"
    elif fault == "extra-s2-in-owner":
        owner["skills"].append({
            "execution_id": "skill-2", "skill_id": "MOVE_PLACE",
            "intent_id": "intent-1",
            "events": [{
                "state": "started", "at_ns": 1040,
                "reason": None, "provenance": owner["skills"][0]["events"][0]["provenance"],
            }],
        })
    raw_checkpoint = _canon({
        "payload": owner, "sha256": _sha(_canon(owner)),
    })
    (root / "checkpoint.json").write_bytes(raw_checkpoint)
    original_anchor = {
        "schema": 1, "phase": "S1_TERMINAL_PRE_S2",
        "head": "1"*40, "world_uuid": "world-uuid-A",
        "owner_id": "original-owner-A", "self_id": "A",
        "native_session_id": "session-A", "checkpoint_generation": 4,
        "s1_intent_id": "intent-1", "s1_skill_execution_id": "skill-1",
        "s1_action_id": "action-1", "s1_status": "NATIVE_PLACE_MOVE_SETTLED",
        "s1_wal_sha256": wal["expected_s1_wal_sha256"],
        "s1_checkpoint_sha256": _sha(raw_checkpoint),
        "s1_action_count": 1,
    }
    anchor = _canon(original_anchor)
    repo, git = _git_pre_s2_source(
        tmp_path, anchor, (root / wal["s2_wal_file"]).read_bytes(),
    )
    q1h = {
        "evidence_dir": root,
        "git_repo_root": repo,
        "external_anchor_bytes": anchor,
        "externally_pinned_anchor_sha256": _sha(anchor),
        "expected_code_head": "1"*40,
        "expected_world_uuid": "world-uuid-A",
        "expected_owner_id": "original-owner-A",
        "expected_self_id": "A",
        "expected_native_session_id": "session-A",
        "expected_checkpoint_generation": 4,
        "s1_wal_file": wal["s1_wal_file"],
        "s1_checkpoint_file": "checkpoint.json",
        "s2_wal_file": wal["s2_wal_file"],
        "expected_s2_action_id": "action-2",
        "git_claims": git,
    }
    return root, repo, q1h


def _audit(q1h, *, world_id="World-A", branch_id="dev-branch"):
    return audit_q1j_typed_owner_move_place_git_join(
        q1h_source_claims=q1h,
        expected_checkpoint_world_id=world_id,
        expected_checkpoint_branch_id=branch_id,
    )


@pytest.mark.parametrize("schema", [1, 2])
def test_q1j_same_generation_owner_intent_and_canonical_wal_is_bounded(
    tmp_path, schema,
):
    root, repo, q1h = _fixture(tmp_path, schema=schema)
    originals = {p.name: (p.read_bytes(), p.stat().st_mtime_ns)
                 for p in root.iterdir()}
    head = subprocess.check_output(
        ["git", "-C", str(repo), "rev-parse", "HEAD"], text=True,
    ).strip()
    receipt = _audit(q1h)
    assert receipt["classification"] == (
        "Q1J_TYPED_OWNER_CANONICAL_S1_S2_GIT_JOIN_CPU_OFFLINE_DEV"
    )
    assert receipt["original_generation_id"] == "g-000000000004"
    assert receipt["s1_intent_id"] == "intent-1"
    assert receipt["s1_skill_execution_id"] == "skill-1"
    assert receipt["s1_skill_last_state"] == "cancelled"
    assert receipt["s1_intent_last_state"] == "completed"
    assert receipt["matched_original_source_bytes_and_lineage"] is True
    assert receipt["actual_original_owner_identity_authenticated"] is False
    assert receipt["typed_product_full_restore_attested"] is False
    assert receipt["independent_prior_witness_authenticated"] is False
    assert receipt["physical_issue_authorized"] is False
    assert receipt["real_world_attested"] is False
    assert receipt["qual_go"] is False and receipt["science_run"] is False
    assert originals == {p.name: (p.read_bytes(), p.stat().st_mtime_ns)
                         for p in root.iterdir()}
    assert subprocess.check_output(
        ["git", "-C", str(repo), "rev-parse", "HEAD"], text=True,
    ).strip() == head


@pytest.mark.parametrize("fault", [
    "unbound-s1-skill", "unbound-s1-intent", "s1-success", "s1-incomplete",
    "s1-intent-failed", "wrong-generation", "wrong-branch",
    "wrong-native-session", "unknown-skill-end",
])
def test_q1j_forged_checkpoint_canonically_rehashed_and_git_pinned_holds(
    tmp_path, fault,
):
    _root, _repo, q1h = _fixture(tmp_path, fault=fault)
    # Both S1 checkpoint SHA and the earlier Git anchor were constructed
    # AFTER the attack, so every hash agrees. Independent lineage must
    # still refuse identity, wrong terminal or wrong generation.
    with pytest.raises(QTypedOriginalSourceJoinHold):
        _audit(q1h)


@pytest.mark.parametrize(("name", "value"), [
    ("expected_checkpoint_world_id", "World-B"),
    ("expected_checkpoint_branch_id", "foreign-branch"),
])
def test_q1j_separately_qualified_world_or_branch_must_match(
    tmp_path, name, value,
):
    _root, _repo, q1h = _fixture(tmp_path)
    claims = {
        "expected_checkpoint_world_id": "World-A",
        "expected_checkpoint_branch_id": "dev-branch",
    }
    claims[name] = value
    with pytest.raises(QTypedOriginalSourceJoinHold):
        audit_q1j_typed_owner_move_place_git_join(
            q1h_source_claims=q1h, **claims,
        )


def test_q1j_rejects_self_reported_pass_receipt_in_place_of_raw_file(tmp_path):
    _root, _repo, q1h = _fixture(tmp_path)
    q1h["verified_stage28_receipt"] = {"classification": "PASS"}
    with pytest.raises(QTypedOriginalSourceJoinHold, match="exact"):
        _audit(q1h)


def test_q1j_rejects_git_head_drift_between_typed_reads(tmp_path, monkeypatch):
    from experiments import q_lane_typed_owner_move_place_join_dev as join

    _root, repo, q1h = _fixture(tmp_path)
    original = join.audit_q1i_typed_owner_cut
    calls = 0

    def mutate_git(*args, **kwargs):
        nonlocal calls
        row = original(*args, **kwargs)
        calls += 1
        if calls == 1:
            (repo / "drift.txt").write_text("Git ref was changed\n")
            subprocess.run(
                ["git", "-C", str(repo), "add", "drift.txt"], check=True,
            )
            subprocess.run(
                ["git", "-C", str(repo), "commit", "-qm", "drift"], check=True,
            )
        return row

    monkeypatch.setattr(join, "audit_q1i_typed_owner_cut", mutate_git)
    with pytest.raises(QTypedOriginalSourceJoinHold):
        _audit(q1h)
    assert calls == 1


def test_q1j_self_consistent_new_git_and_checkpoint_can_never_authenticate(
    tmp_path,
):
    _root, _repo, q1h = _fixture(tmp_path)
    result = _audit(q1h)
    assert result["independent_prior_witness_authenticated"] is False
    assert result["actual_s1_s2_runtime_order_attested"] is False
    assert result["original_stage28_full_generation_verified"] is False if (
        "original_stage28_full_generation_verified" in result
    ) else result["typed_product_full_restore_attested"] is False
