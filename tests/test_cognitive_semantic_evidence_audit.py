"""The cross-trial semantic evidence audit never touches a real World."""
from __future__ import annotations

import copy
import json

import pytest

from experiments.audit_cognitive_semantic_results import (
    SemanticEvidenceAuditError,
    audit_three_trials,
    audit_trial,
)
from test_cognitive_semantic_outcome_dev import run_attack, run_eat


def _trials(monkeypatch, tmp_path):
    done = tmp_path / "eat-done"
    active = tmp_path / "eat-active"
    attack = tmp_path / "attack-active"
    for path in (done, active, attack):
        path.mkdir()
    a, _ = run_eat(monkeypatch, done, apply=True, threshold=10)
    b, _ = run_eat(monkeypatch, active, apply=True, threshold=17)
    c, _ = run_attack(monkeypatch, attack, apply=True)
    return a, b, c


@pytest.mark.parametrize("index,role", [
    (0, "EAT_GOAL_DONE"), (1, "EAT_GOAL_ACTIVE"),
    (2, "ATTACK_GOAL_ACTIVE"),
])
def test_one_typed_semantic_trial_audits_without_world_claim(
    monkeypatch, tmp_path, index, role,
):
    trials = _trials(monkeypatch, tmp_path)
    check = audit_trial(trials[index], expected=role)
    assert check["role"] == role
    assert check["skill"] == "succeeded"
    assert check["intent"] == ("completed" if index == 0 else "committed")


@pytest.mark.parametrize("bad", [
    "forged_intent_completion", "stale_goal_probe",
    "unresolved_journal", "other_action_id",
    "wrong_native_source", "skill_not_started_or_completed",
    "missing_evaluation_mode",
])
def test_typed_semantic_audit_rejects_cross_layer_false_success(
    monkeypatch, tmp_path, bad,
):
    done, _, _ = _trials(monkeypatch, tmp_path)
    result = copy.deepcopy(done)
    if bad == "forged_intent_completion":
        result["semantic_assessment"]["goal_evidence"] = "ACTIVE"
    elif bad == "stale_goal_probe":
        result["semantic_evaluation_probe"]["observation"]["seq"] = 1
        result["semantic_evaluation_probe"]["native_source_ref"] = (
            result["world_session"] + ":1"
        )
    elif bad == "unresolved_journal":
        result["physical_journal_unresolved"] = True
    elif bad == "other_action_id":
        result["physical_journal_records"][0]["action_id"] = "foreign-parent"
    elif bad == "wrong_native_source":
        result["semantic_evaluation_probe"]["native_source"] = "not-mineflayer"
    elif bad == "skill_not_started_or_completed":
        result["skill_final_state"] = "started"
    else:
        result["semantic_eval_dev_selected"] = False
    with pytest.raises(SemanticEvidenceAuditError):
        audit_trial(result, expected="EAT_GOAL_DONE")


def test_cross_trial_audit_rejects_reused_world_and_self(
    monkeypatch, tmp_path,
):
    done, active, attack = _trials(monkeypatch, tmp_path)
    with pytest.raises(SemanticEvidenceAuditError, match="distinct trial"):
        audit_three_trials(done, active, attack)


def test_distinct_three_synthetic_worlds_pass_typed_consistency_only(
    monkeypatch, tmp_path,
):
    trials = list(_trials(monkeypatch, tmp_path))
    for i, item in enumerate(trials):
        # Test-only synthetic rewriting of complete JSON session strings.
        # These results are NEVER passed off as native World evidence.
        trials[i] = json.loads(json.dumps(item).replace(
            "session-1", f"offline-world-{i}",
        ))
        trials[i]["semantic_assessment"]["self_id"] = f"offline-self-{i}"
    summary = audit_three_trials(*trials)
    assert summary["trial_count"] == 3
    assert summary["raw_native_verified"] is False
    assert summary["paper_damage_attributed"] is False
    assert summary["classification"].endswith("NOT_WORLD_AUTHENTICATION")
    assert [x["intent"] for x in summary["trials"]] == [
        "completed", "committed", "committed",
    ]


def test_attacked_zombie_disappearing_does_not_count_as_goal_done(
    monkeypatch, tmp_path,
):
    place = tmp_path / "attack"
    place.mkdir()
    result, _ = run_attack(
        monkeypatch, place, apply=True, fail_at="gone_after_attack",
    )
    assert result["semantic_assessment"]["goal_evidence"] == "UNKNOWN"
    with pytest.raises(SemanticEvidenceAuditError):
        audit_trial(result, expected="ATTACK_GOAL_ACTIVE")
