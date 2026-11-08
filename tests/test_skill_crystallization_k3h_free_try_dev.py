"""K3-H DEV stage gates: optional prediction, bounded mock effect, L2 readback."""

from __future__ import annotations

import copy
import json
from pathlib import Path

import pytest

from experiments.skill_crystallization_dev import skill_json_schema
from experiments.skill_crystallization_k3h_free_try_dev import (
    FIXTURE_SEED,
    NEW_MODEL_TRIAL_SEED,
    execute_mock,
    proposal_schema,
    reflection_schema,
    run_proposal,
    run_reflection,
    validate_proposal,
    validate_reflection,
)
from experiments.skill_crystallization_k3g_ten_action_choice_dev import verified_context

ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture
def originals():
    relative = (
        "evidence/l431-gemma-20261108/first-report.json",
        "evidence/l431-k3b-gemma-20261108/report.json",
        "evidence/l431-k3d-gemma-20261108/report.json",
        "evidence/l431-k3e-gemma-20261108/proposal.json",
    )
    return [json.loads((ROOT / name).read_text(encoding="utf-8"))
            for name in relative]


@pytest.fixture
def source(originals):
    return verified_context(*originals)


def trial(*, choice="COMPARE_ARMS", arm="NONE", n=5,
          prediction="UNKNOWN", ids=None):
    return {
        "decision": choice, "arm": arm, "max_actions_per_arm": n,
        "prediction": prediction, "reason": "Need to learn how movement changes",
        "evidence_ids": ids if ids is not None else ["shift-experience-010"],
    }


def reflect(*, skill=None, next_decision="TRY_MOVE", ids=None):
    return {
        "next_decision": next_decision,
        "understanding": "This single mock observation warrants more tests",
        "skill": skill,
        "evidence_ids": ["k3h-experience-B"] if ids is None else ids,
    }


def test_legacy_contract_and_new_schema_independent():
    assert skill_json_schema()["properties"]["max_actions"]["enum"] == [1, 2, 3, 4]
    assert proposal_schema()["properties"]["prediction"]["enum"][0] == "UNKNOWN"
    assert set(proposal_schema()["properties"]["decision"]["enum"]) == {
        "TRY_MOVE", "COMPARE_ARMS", "OBSERVE_ONLY", "DEFER",
    }
    assert reflection_schema()["properties"]["skill"]["anyOf"][1] == {"type": "null"}


def test_unknown_prediction_accepted_with_valid_action(source):
    assert validate_proposal(trial(), source["ids"])["prediction"] == "UNKNOWN"
    assert validate_proposal(trial(choice="TRY_MOVE", arm="B", n=10),
                             source["ids"])["prediction"] == "UNKNOWN"


@pytest.mark.parametrize("bad", [
    trial(choice="TRY_MOVE"),  # arm NONE
    trial(choice="COMPARE_ARMS", arm="A"),
    trial(choice="DEFER", n=1),
    trial(choice="OBSERVE_ONLY", n=2),
    trial(n=11), trial(n=-1), trial(n=2.5), trial(n=True),
    trial(prediction="GOAL_REACHED"),
    trial(choice="TRY_MOVE", arm="A", prediction="BOTH_FAIL"),
    trial(ids=["unobserved-experience"]),
])
def test_invalid_action_envelope_rejected(source, bad):
    with pytest.raises(ValueError):
        validate_proposal(bad, source["ids"])


def test_defer_and_observe_only_do_not_move(originals, source):
    for choice, label in (("DEFER", "DEFER_NO_NEW_EXPERIENCE"),
                          ("OBSERVE_ONLY", "READ_ONLY_CUE_OBSERVED")):
        proposal = run_proposal(
            *originals, mode="fixture",
            fixture=trial(choice=choice, n=0, ids=[], prediction="UNKNOWN"),
        )
        before = copy.deepcopy(proposal)
        result = execute_mock(proposal, source, mock_grant=True,
                              result_mode="fixture")
        assert proposal == before
        assert result["mock_actions"] == 0
        assert result["native_s49_actions"] == 0
        assert label in result["stages"]
        if choice == "OBSERVE_ONLY":
            assert result["new_experiences"][0]["outcome_success"] is None
        else:
            assert not result["new_experiences"]


def test_comparison_same_seed_arms_and_goal_stop(originals, source):
    proposal = run_proposal(*originals, mode="fixture", fixture=trial(n=10))
    first = execute_mock(proposal, source, mock_grant=True,
                         result_mode="fixture")
    second = execute_mock(proposal, source, mock_grant=True,
                          result_mode="fixture")
    assert first == second
    assert first["mock_seed"] == FIXTURE_SEED
    assert first["mock_actions"] <= 20
    assert len(first["new_experiences"]) == 2
    a, b = first["new_experiences"]
    assert a["experience_id"] == "k3h-experience-A"
    assert b["experience_id"] == "k3h-experience-B"
    assert a["start_distance"] == b["start_distance"] == 2.4
    assert a["source_session"] != b["source_session"]
    assert a["outcome_success"] and b["outcome_success"]
    assert a["action_count"] < 10 and b["action_count"] <= 10
    assert a["final_distance"] >= 3.2 and b["final_distance"] >= 3.2
    assert not any("2016" in r["source_session"] for r in (a, b))
    assert first["protected_seeds"] == {
        "20261126": "UNOPENED", "20261205": "UNOPENED",
        "20261213": "UNOPENED",
    }


def test_try_move_one_arm_and_no_post_goal_actions(originals, source):
    proposal = run_proposal(*originals, mode="fixture",
                            fixture=trial(choice="TRY_MOVE", arm="A", n=10))
    result = execute_mock(proposal, source, mock_grant=True,
                          result_mode="fixture")
    assert len(result["new_experiences"]) == 1
    assert result["new_experiences"][0]["action_count"] <= 2
    assert result["mock_actions"] <= 2


def test_try_one_action_keeps_failure_not_auto_retry(originals, source):
    proposal = run_proposal(*originals, mode="fixture",
                            fixture=trial(choice="TRY_MOVE", arm="B", n=1))
    result = execute_mock(proposal, source, mock_grant=True,
                          result_mode="fixture")
    assert result["mock_actions"] == 1
    assert result["new_experiences"][0]["outcome_success"] is False


def test_mock_requires_explicit_grant_and_valid_source(originals, source):
    proposal = run_proposal(*originals, mode="fixture", fixture=trial())
    with pytest.raises(ValueError, match="EXPLICIT_DEV_MOCK_GRANT_REQUIRED"):
        execute_mock(proposal, source, mock_grant=False, result_mode="fixture")
    altered = copy.deepcopy(proposal)
    altered["source_fingerprint"] = "bogus"
    with pytest.raises(ValueError, match="PROPOSAL_SOURCE_MISMATCH"):
        execute_mock(altered, source, mock_grant=True, result_mode="fixture")


def test_future_real_seed_never_used_in_fixture(originals, source):
    proposal = run_proposal(*originals, mode="fixture", fixture=trial())
    result = execute_mock(proposal, source, mock_grant=True, result_mode="fixture")
    assert result["mock_seed"] != NEW_MODEL_TRIAL_SEED


def test_no_real_model_source_no_new_mock_outcome(originals, source):
    proposal = run_proposal(*originals, mode="fixture", fixture=trial())
    proposal["mode"] = "gemma"
    with pytest.raises(ValueError, match="REAL_MODEL_SOURCE_UNATTESTED"):
        execute_mock(proposal, source, mock_grant=True, result_mode="gemma")


def test_reflect_after_real_observed_mock_not_auto_install(originals, source):
    prior = copy.deepcopy(originals)
    proposal = run_proposal(*originals, mode="fixture",
                            fixture=trial(choice="TRY_MOVE", arm="B", n=5))
    mock = execute_mock(proposal, source, mock_grant=True,
                        result_mode="fixture")
    result = run_reflection(*originals, proposal_report=proposal,
                            outcome_report=mock, mode="fixture",
                            fixture=reflect())
    assert originals == prior
    assert result["schema_validation"] == "PASS"
    assert result["semantic_validation"] == "PASS"
    assert result["reflection"]["next_decision"] == "TRY_MOVE"
    assert result["skill_installed"] is False
    assert result["skill_evaluated"] is False
    assert result["native_s49_actions"] == 0
    assert result["mock_actions"] == 0


def test_reflect_may_return_valid_source_grounded_tentative_skill(
    originals, source,
):
    proposal = run_proposal(*originals, mode="fixture",
                            fixture=trial(choice="TRY_MOVE", arm="B", n=10))
    mock = execute_mock(proposal, source, mock_grant=True,
                        result_mode="fixture")
    skill = {
        **source["old_skill"], "skill_id": "new-after-k3h",
        "max_actions": 10,
        "evidence_ids": ["k3h-experience-B"],
    }
    result = run_reflection(
        *originals, proposal_report=proposal, outcome_report=mock,
        mode="fixture", fixture=reflect(skill=skill),
    )
    assert result["schema_validation"] == "PASS"
    assert result["semantic_validation"] == "PASS"
    assert "TENTATIVE_SKILL_NOT_EVALUATED_OR_INSTALLED" in result["stages"]
    assert not result["skill_installed"]


def test_hallucinated_reflection_evidence_rejected(originals, source):
    proposal = run_proposal(*originals, mode="fixture", fixture=trial())
    mock = execute_mock(proposal, source, mock_grant=True,
                        result_mode="fixture")
    rejected = run_reflection(
        *originals, proposal_report=proposal, outcome_report=mock,
        mode="fixture", fixture=reflect(ids=["fabricated-action"]),
    )
    assert rejected["schema_validation"] == "PASS"
    assert rejected["semantic_validation"] == "REJECTED"
    assert rejected["reflection"]["evidence_ids"] == ["fabricated-action"]


def test_reflection_rejects_tampered_outcome_chain(originals, source):
    proposal = run_proposal(*originals, mode="fixture", fixture=trial())
    mock = execute_mock(proposal, source, mock_grant=True,
                        result_mode="fixture")
    mock["proposal_fingerprint"] = "not-the-original-proposal"
    with pytest.raises(ValueError, match="OUTCOME_CHAIN_SOURCE_MISMATCH"):
        run_reflection(
            *originals, proposal_report=proposal, outcome_report=mock,
            mode="fixture", fixture=reflect(),
        )


def test_defer_cannot_be_converted_to_fake_learning(originals, source):
    proposal = run_proposal(*originals, mode="fixture",
                            fixture=trial(choice="DEFER", n=0, ids=[]))
    mock = execute_mock(proposal, source, mock_grant=True,
                        result_mode="fixture")
    with pytest.raises(ValueError, match="NO_EXPERIENCE_FOR_REFLECTION"):
        run_reflection(
            *originals, proposal_report=proposal, outcome_report=mock,
            mode="fixture", fixture=reflect(),
        )


def test_real_model_proposal_one_call_no_future_physics_leak(
    originals, monkeypatch, tmp_path,
):
    import experiments.skill_crystallization_k3h_free_try_dev as mod

    calls = []

    def stub(evidence, **kwargs):
        calls.append((evidence, kwargs))
        return trial(choice="COMPARE_ARMS", n=5), {
            "http_status": 200, "finish_reason": "stop",
        }

    monkeypatch.setattr(mod, "gemma_l2", stub)
    r = run_proposal(
        *originals, mode="gemma",
        endpoint="http://127.0.0.1:8080/v1/chat/completions",
        model="verified-local", record_dir=tmp_path / "proposal",
    )
    assert r["schema_validation"] == "PASS"
    assert len(calls) == 1
    evidence, kw = calls[0]
    assert len(evidence) == 28
    assert kw["max_actions_allowed"] == 10
    assert kw["response_schema"] == proposal_schema()
    as_text = json.dumps(kw, default=str)
    assert "20261219" not in as_text
    assert "future_effects" not in as_text
    assert "MOTION_REGIMES" not in as_text
    assert "SOUL" not in as_text


def test_fake_real_model_reflection_source_is_rejected(
    originals, source, monkeypatch, tmp_path,
):
    import experiments.skill_crystallization_k3h_free_try_dev as mod

    proposal = run_proposal(
        *originals, mode="fixture",
        fixture=trial(choice="TRY_MOVE", arm="B", n=10),
    )
    mock = execute_mock(
        proposal, source, mock_grant=True, result_mode="fixture",
    )
    # No future holdout/real-seed opening. Changing a fixture label must not
    # turn a synthetic mock observation into an attested real-model sequence.
    proposal["mode"] = "gemma"
    mock["mode"] = "gemma"
    mock["proposal_fingerprint"] = mod._canonical_sha(proposal)
    monkeypatch.setattr(mod, "gemma_l2", lambda *_a, **_k: pytest.fail(
        "unsourced outcome must not be sent to the model"
    ))
    with pytest.raises(ValueError, match="REAL_MODEL_SOURCE_UNATTESTED"):
        run_reflection(
            *originals, proposal_report=proposal, outcome_report=mock,
            mode="gemma", endpoint="http://127.0.0.1:8080/v1/chat/completions",
            model="verified-local", record_dir=tmp_path / "reflect",
        )


def test_outcome_value_tampering_is_caught_before_reflection(originals, source):
    proposal = run_proposal(*originals, mode="fixture", fixture=trial(n=5))
    mock = execute_mock(proposal, source, mock_grant=True,
                        result_mode="fixture")
    mock["new_experiences"][0]["final_distance"] = 1234
    with pytest.raises(ValueError, match="NEW_MOCK_OUTCOME_NOT_REPRODUCIBLE"):
        run_reflection(
            *originals, proposal_report=proposal, outcome_report=mock,
            mode="fixture", fixture=reflect(),
        )


def test_extra_cli_sha_fields_do_not_break_mock_readback(originals, source):
    proposal = run_proposal(*originals, mode="fixture", fixture=trial(n=5))
    mock = execute_mock(proposal, source, mock_grant=True,
                        result_mode="fixture")
    mock["original_source_sha256"] = {"first": "example"}
    mock["original_manifest_audit"] = {"example": "PASS"}
    result = run_reflection(
        *originals, proposal_report=proposal, outcome_report=mock,
        mode="fixture", fixture=reflect(),
    )
    assert result["schema_validation"] == "PASS"



def test_invalid_prediction_rejected_after_schema_pass(originals):
    proposal = run_proposal(
        *originals, mode="fixture", fixture=trial(
            choice="TRY_MOVE", arm="A", prediction="BOTH_FAIL"
        ),
    )
    assert proposal["schema_validation"] == "PASS"
    assert proposal["semantic_validation"] == "REJECTED"
    assert "VALID_BOUNDED_CHOICE" not in proposal["stages"]


def test_no_outcome_from_rejected_semantic_proposal(originals, source):
    proposal = run_proposal(
        *originals, mode="fixture", fixture=trial(n=0),
    )
    assert proposal["semantic_validation"] == "REJECTED"
    with pytest.raises(ValueError, match="UNADMITTED_PROPOSAL"):
        execute_mock(proposal, source, mock_grant=True, result_mode="fixture")


def test_prediction_can_be_wrong_without_blocking_experience(originals, source):
    proposal = run_proposal(
        *originals, mode="fixture",
        fixture=trial(choice="TRY_MOVE", arm="A", n=1,
                      prediction="GOAL_REACHED"),
    )
    assert proposal["semantic_validation"] == "PASS"
    observed = execute_mock(
        proposal, source, mock_grant=True, result_mode="fixture",
    )
    assert observed["predicted_pattern"] == "GOAL_REACHED"
    assert observed["new_experiences"][0]["outcome_success"] is False
    assert observed["mock_actions"] == 1
    # Correctness of a prediction is a separate retrospective check.
    assert "PREDICTION_RECORDED_BUT_NOT_AUTOMATICALLY_SCIENCE_VALIDATED" == (
        observed["prediction_assessment"]
    )
