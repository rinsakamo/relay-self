"""K3-D focused contracts: no real model HTTP or native Minecraft Action."""

from __future__ import annotations

import json

import pytest

import experiments.skill_crystallization_k3d_dev as k3d
from experiments.skill_crystallization_dev import make_trials, observed_training
from experiments.skill_crystallization_k3b_dev import prepare_revision, proposal_json_schema


def inputs():
    training = observed_training(make_trials(20261108, 16, phase="train"))
    old = {
        "version": 1, "skill_id": "old_normal", "surface": "normal",
        "min_distance": 2.314917, "max_distance": 2.457525,
        "target_distance": 3.2, "max_actions": 4, "on_failure": "ESCALATE",
        "evidence_ids": [r["experience_id"] for r in training if r["surface_cue"] == "normal"],
    }
    first = {"candidate_raw": old, "training": training}
    initial = prepare_revision(first, {"shift_observations": []})
    assert initial["suspended"]
    prior = {
        "shift_observations": initial["shift_observations"],
        "proposal_status": "SKILL", "schema_validation": "PASS",
        "proposal": {
            "status": "SKILL", "reason": "previous structured proposal",
            "skill": {**old, "skill_id": "renamed", "evidence_ids": [
                initial["shift_observations"][0]["experience_id"]
            ]},
        },
    }
    return first, prior


def proposal(first, prior, *, mode="narrow"):
    old = first["candidate_raw"]
    skill = {**old, "skill_id": "k3d",
             "evidence_ids": [r["experience_id"] for r in prior["shift_observations"]]}
    if mode == "narrow":
        skill["min_distance"] = 2.39
    if mode == "unbounded":
        skill["max_actions"] = 5
    return {"status": "SKILL", "reason": "test proposal", "skill": skill}


def test_previous_structured_policy_is_execution_equivalent():
    first, prior = inputs()
    state = k3d._grounded_prior(first, prior)
    assert state["suspended"]
    assert state["prior_skill"]["max_actions"] == 4


def test_gemma_holdout_seed_is_unopened_in_fixture_mode():
    first, prior = inputs()
    with pytest.raises(ValueError, match="HOLDOUT_SEED_CONTAMINATION"):
        k3d.run_k3d(first, prior, mode="fixture", fixture_proposal=proposal(first, prior),
                    evaluation_seed=k3d.REAL_GEMMA_HOLDOUT_SEED)


def test_execution_equivalent_metadata_is_not_new_skill(monkeypatch):
    pytest.importorskip("jsonschema")
    first, prior = inputs()
    monkeypatch.setattr(k3d, "evaluate_comparison", lambda *_a, **_kw: pytest.fail(
        "equivalent proposal must never open the reserved holdout"))
    result = k3d.run_k3d(first, prior, mode="fixture",
                         fixture_proposal=proposal(first, prior, mode="equivalent"))
    assert "NO_BEHAVIORAL_CHANGE" in result["stages"]
    assert result["holdout"] is None
    assert result["evaluation_seed"] is None
    assert result["model_record"] is None


@pytest.mark.parametrize("status", ["ABSTAIN", "UNSATISFIABLE_WITHIN_BUDGET"])
def test_valid_abstention_performs_no_evaluation(monkeypatch, status):
    pytest.importorskip("jsonschema")
    first, prior = inputs()
    monkeypatch.setattr(k3d, "evaluate_comparison", lambda *_a, **_kw: pytest.fail(
        "abstention must not run the simulated Skill"))
    result = k3d.run_k3d(first, prior, mode="fixture",
                         fixture_proposal={"status": status, "reason": "inconclusive",
                                           "skill": None})
    assert result["proposal_status"] == status
    assert "EXPLICIT_ABSTENTION_ACCEPTED" in result["stages"]
    assert result["holdout"] is None


def test_bounded_narrow_skill_uses_new_fixture_holdout():
    pytest.importorskip("jsonschema")
    first, prior = inputs()
    result = k3d.run_k3d(first, prior, mode="fixture",
                         fixture_proposal=proposal(first, prior))
    assert result["schema_validation"] == "PASS"
    assert result["semantic_delta"]["classification"] == "EXECUTION_SPEC_CHANGED"
    assert "PAIRED_MOCK_HOLDOUT_EVALUATED" in result["stages"]
    assert result["evaluation_seed"] == k3d.FIXTURE_SEED
    assert result["holdout"]["n"] == 32
    assert result["holdout"]["new_automatic_postfailure_actions"] == 0
    assert result["holdout"]["cue_negative_rejections"] == 128
    assert result["model_calls_in_mock_runner"] == 0
    assert result["observed_scope"]["observed_selected"] > 0


def test_previous_outcome_tampering_rejected():
    first, prior = inputs()
    prior["shift_observations"][0]["outcome_success"] = not prior["shift_observations"][0]["outcome_success"]
    with pytest.raises(ValueError, match="PRIOR_SOURCE_MISMATCH"):
        k3d.run_k3d(first, prior, mode="fixture", fixture_proposal=proposal(first, prior))


def test_parent_must_be_equivalent():
    first, prior = inputs()
    prior["proposal"]["skill"]["min_distance"] = 2.4
    with pytest.raises(ValueError, match="K3B_PARENT_NOT_EXECUTION_EQUIVALENT"):
        k3d.run_k3d(first, prior, mode="fixture", fixture_proposal=proposal(first, prior))


def test_wire_rejects_invalid_budget_before_new_holdout(monkeypatch):
    pytest.importorskip("jsonschema")
    first, prior = inputs()
    monkeypatch.setattr(k3d, "evaluate_comparison", lambda *_a, **_kw: pytest.fail(
        "validator rejection must not open the holdout"))
    result = k3d.run_k3d(first, prior, mode="fixture",
                         fixture_proposal=proposal(first, prior, mode="unbounded"))
    assert result["schema_validation"] == "REJECTED"
    assert result["holdout"] is None
    assert result["evaluation_seed"] is None


def test_unobserved_evidence_is_refused():
    pytest.importorskip("jsonschema")
    first, prior = inputs()
    raw = proposal(first, prior)
    raw["skill"]["evidence_ids"] = ["future-holdout-001"]
    result = k3d.run_k3d(first, prior, mode="fixture", fixture_proposal=raw)
    assert result["validator_error"] == "EVIDENCE_NOT_TRAINING_SOURCED"
    assert result["holdout"] is None


def test_gemma_request_one_call_and_no_holdout_leak(monkeypatch):
    pytest.importorskip("jsonschema")
    first, prior = inputs()
    captured = []

    def fake_gemma(evidence, **kwargs):
        captured.append((evidence, kwargs))
        return proposal(first, prior, mode="equivalent"), {"finish_reason": "stop"}

    monkeypatch.setattr(k3d, "gemma_l2", fake_gemma)
    result = k3d.run_k3d(first, prior, mode="gemma",
                         endpoint="http://127.0.0.1:8080/v1/chat/completions",
                         model="verified-model-id")
    assert len(captured) == 1
    evidence, kwargs = captured[0]
    assert kwargs["response_schema"] == proposal_json_schema()
    assert "20261126" not in json.dumps(kwargs)
    assert "holdout" not in json.dumps(kwargs)
    assert "20261126" not in json.dumps(evidence)
    assert kwargs["revision_context"]["previous_revision_execution_equal_to_old"]
    assert "L2_REVISION_ATTEMPTED" in result["stages"]
    assert "NO_BEHAVIORAL_CHANGE" in result["stages"]
    assert result["holdout"] is None


def test_missing_model_credentials_do_not_send():
    first, prior = inputs()
    with pytest.raises(ValueError, match="LOCAL_GEMMA_ENDPOINT_AND_MODEL_REQUIRED"):
        k3d.run_k3d(first, prior, mode="gemma")


def test_real_mode_rejects_recycled_seed():
    first, prior = inputs()
    with pytest.raises(ValueError, match="HOLDOUT_SEED_CONTAMINATION"):
        k3d.run_k3d(first, prior, mode="gemma", evaluation_seed=20261120,
                    endpoint="http://localhost:8080/v1/chat/completions", model="model")


def test_invalid_status_and_abstain_with_skill_rejected():
    pytest.importorskip("jsonschema")
    first, prior = inputs()
    invalid = {"status": "ABSTAIN", "reason": "inconclusive", "skill": proposal(first, prior)["skill"]}
    r = k3d.run_k3d(first, prior, mode="fixture", fixture_proposal=invalid)
    assert r["validator_error"] == "ABSTENTION_CANNOT_EXECUTE_SKILL"
    assert r["holdout"] is None


def test_evidence_scope_uses_observed_prefix_not_future_physics():
    first, prior = inputs()
    skill = proposal(first, prior)["skill"]
    skill["max_actions"] = 2
    counts = k3d._evidence_scope(skill, prior["shift_observations"])
    assert counts["observed_selected"] > 0
    assert counts["observed_selected_success"] == 0
    assert sum(counts[k] for k in ["observed_selected", "observed_excluded_failure",
                                  "observed_excluded_success"]) == 12


def test_original_non_suspended_rows_are_not_synthesized():
    first, prior = inputs()
    prior["shift_observations"] = prior["shift_observations"][:-2]
    with pytest.raises(ValueError, match="ORIGINAL_SUSPENSION_REQUIRED"):
        k3d._grounded_prior(first, prior)
