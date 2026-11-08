"""Focused K3-B tests: no actual model, World, S49, or owner writes."""

from __future__ import annotations

import json
import urllib.request

import pytest

from experiments.skill_crystallization_dev import (
    make_trials,
    observed_training,
    skill_json_schema,
)
from experiments.skill_crystallization_k3b_dev import (
    evaluate_revision,
    prepare_revision,
    proposal_json_schema,
    run_k3b,
    validate_proposal,
    verify_suspension,
)


def _first(*, eligible: bool = True):
    training = observed_training(make_trials(20261108, 16, phase="train"))
    return {
        "candidate_raw": {
            "version": 1, "skill_id": "GEMMA_NORMAL_TEST", "surface": "normal",
            "min_distance": 2.314917 if eligible else 0.01,
            "max_distance": 2.457525 if eligible else 0.02,
            "target_distance": 3.2, "max_actions": 4, "on_failure": "ESCALATE",
            "evidence_ids": [x["experience_id"] for x in training
                             if x["surface_cue"] == "normal"],
        },
        "training": training,
    }


def _skill(first):
    skill = dict(first["candidate_raw"])
    skill["skill_id"] = "REVISED_NORMAL_K3B"
    skill["min_distance"] = 0.0
    skill["max_distance"] = 3.2
    return {"status": "SKILL", "reason": "Bounded test candidate", "skill": skill}


def test_wire_action_budget_closed_and_abstention_statuses():
    assert skill_json_schema()["properties"]["max_actions"]["enum"] == [1, 2, 3, 4]
    schema = proposal_json_schema()
    assert schema["additionalProperties"] is False
    assert set(schema["required"]) == set(schema["properties"])
    assert schema["properties"]["status"]["enum"] == [
        "SKILL", "ABSTAIN", "UNSATISFIABLE_WITHIN_BUDGET",
    ]


def test_json_schema_independent_if_installed():
    jsonschema = pytest.importorskip("jsonschema")
    first = _first()
    jsonschema.validate(_skill(first), proposal_json_schema())
    with pytest.raises(jsonschema.ValidationError):
        jsonschema.validate({
            **_skill(first),
            "skill": {**_skill(first)["skill"], "max_actions": 5},
        }, proposal_json_schema())
    for status in ("ABSTAIN", "UNSATISFIABLE_WITHIN_BUDGET"):
        jsonschema.validate({"status": status, "reason": "unknown", "skill": None},
                            proposal_json_schema())


@pytest.mark.parametrize("status", ["ABSTAIN", "UNSATISFIABLE_WITHIN_BUDGET"])
def test_explicit_abstain_keeps_no_executable_skill(status):
    pytest.importorskip("jsonschema")
    first = _first()
    report = run_k3b(first, {"shift_observations": []}, mode="fixture",
                     fixture_proposal={"status": status, "reason": "uncertain",
                                       "skill": None})
    assert report["proposal_status"] == status
    assert report["old_skill_state"] == "SUSPENDED"
    assert report["rollback"] == "FIXED_L0_FALLBACK"
    assert report["holdout"] is None
    assert "EXPLICIT_ABSTENTION_ACCEPTED" in report["stages"]


def test_refuse_invalid_budget_and_unobserved_source():
    first = _first()
    ids = {row["experience_id"] for row in first["training"]}
    raw = _skill(first)
    raw["skill"]["max_actions"] = 5
    with pytest.raises(ValueError, match="ACTION_BUDGET_INVALID"):
        validate_proposal(raw, ids)
    raw = _skill(first)
    raw["skill"]["evidence_ids"] = ["heldout-000"]
    with pytest.raises(ValueError, match="EVIDENCE_NOT_TRAINING_SOURCED"):
        validate_proposal(raw, ids)


def test_refuse_abstain_with_executable_skill():
    first = _first()
    raw = _skill(first)
    raw["status"] = "ABSTAIN"
    with pytest.raises(ValueError, match="ABSTENTION_CANNOT_EXECUTE_SKILL"):
        validate_proposal(raw, {x["experience_id"] for x in first["training"]})


def test_shift_suspension_derived_from_real_mock_failures_not_text():
    state = prepare_revision(_first(), {"shift_observations": []})
    assert state["suspended"]
    assert len(state["shift_observations"]) == 12
    assert [x["outcome_success"] for x in state["shift_observations"][-2:]] == [
        False, False,
    ]
    assert "20261112" not in json.dumps(state["revision_context"])
    assert verify_suspension([{"outcome_success": False}]) is False
    assert verify_suspension([{"outcome_success": False},
                              {"outcome_success": True}]) is False


def test_no_model_or_rollback_before_suspension(monkeypatch):
    import experiments.skill_crystallization_k3b_dev as mod

    def forbidden(*_args, **_kwargs):
        raise AssertionError("unexpected model call")

    monkeypatch.setattr(mod, "gemma_l2", forbidden)
    report = run_k3b(_first(eligible=False), {"shift_observations": []},
                     mode="gemma", endpoint="http://127.0.0.1:8080/v1/chat/completions",
                     model="test")
    assert report["old_skill_state"] == "ACTIVE"
    assert report["rollback"] is None
    assert report["model_record"] is None
    assert report["validator_error"] == "TWO_CONSECUTIVE_FAILURES_NOT_OBSERVED"


def test_preserves_prior_terminated_shift_without_extra_trials():
    state = prepare_revision(_first(), {"shift_observations": []})
    again = prepare_revision(_first(), {
        "shift_observations": state["shift_observations"],
    })
    assert again["shift_observations"] == state["shift_observations"]


def test_fixture_skill_holdout_no_llm_and_bounded_actions(monkeypatch):
    pytest.importorskip("jsonschema")
    import experiments.skill_crystallization_k3b_dev as mod

    def forbidden(*_args, **_kwargs):
        raise AssertionError("unexpected model call in mock runner")

    monkeypatch.setattr(mod, "gemma_l2", forbidden)
    first = _first()
    report = run_k3b(first, {"shift_observations": []},
                     mode="fixture", fixture_proposal=_skill(first))
    holdout = report["holdout"]
    assert report["proposal_status"] == "SKILL"
    assert holdout["n"] == 16
    assert holdout["actions"] <= 16 * 4
    assert holdout["invalid_cue_selected"] == 0
    assert holdout["misapplication"] == 0
    assert holdout["runtime_error"] == 0
    assert "NEW_SKILL_MOCK_EVALUATED" in report["stages"]
    assert report["model_record"] is None
    assert evaluate_revision(_skill(first)["skill"])["n"] == 16


def test_http_request_is_one_call_and_excludes_future_holdout(monkeypatch):
    pytest.importorskip("jsonschema")
    first = _first()
    captured = []
    output = {"status": "UNSATISFIABLE_WITHIN_BUDGET",
              "reason": "Not enough evidence for a viable bounded skill",
              "skill": None}

    class Response:
        status = 200

        def __enter__(self):
            return self

        def __exit__(self, *_):
            return False

        def read(self):
            return json.dumps({"choices": [{
                "finish_reason": "stop",
                "message": {"content": json.dumps(output),
                            "reasoning_content": None},
            }]}).encode()

    def send(request, *, timeout):
        captured.append(json.loads(request.data))
        return Response()

    monkeypatch.setattr(urllib.request, "urlopen", send)
    report = run_k3b(first, {"shift_observations": []}, mode="gemma",
                     endpoint="http://127.0.0.1:8080/v1/chat/completions",
                     model="test")
    assert report["proposal_status"] == "UNSATISFIABLE_WITHIN_BUDGET"
    assert report["holdout"] is None
    assert len(captured) == 1
    request = captured[0]
    assert request["reasoning_effort"] == "none"
    assert request["response_format"]["json_schema"]["strict"] is True
    assert request["response_format"]["json_schema"]["schema"] == proposal_json_schema()
    assert "20261112" not in json.dumps(request)
    assert "hidden_physics" not in json.dumps(request)
    assert "holdout" not in request["messages"][1]["content"]


def test_wire_rejection_prevents_execution():
    pytest.importorskip("jsonschema")
    first = _first()
    proposal = _skill(first)
    proposal["skill"]["max_actions"] = 5
    report = run_k3b(first, {"shift_observations": []}, mode="fixture",
                     fixture_proposal=proposal)
    assert report["schema_validation"] == "REJECTED"
    assert report["holdout"] is None


def test_tampered_prior_evidence_rejected_before_model():
    state = prepare_revision(_first(), {"shift_observations": []})
    rows = [dict(x) for x in state["shift_observations"]]
    rows[0]["outcome_success"] = False
    with pytest.raises(ValueError, match="PRIOR_SOURCE_MISMATCH"):
        prepare_revision(_first(), {"shift_observations": rows})
    rows = [dict(x) for x in state["shift_observations"]]
    rows[0]["observed_trace"] = [100.0]
    with pytest.raises(ValueError, match="PRIOR_SOURCE_MISMATCH"):
        prepare_revision(_first(), {"shift_observations": rows})
