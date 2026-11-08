"""K3-E: deterministic mock probe and one-shot L2 request contracts."""

from __future__ import annotations

import json

import pytest

from experiments.skill_crystallization_dev import make_trials, observed_training
from experiments.skill_crystallization_k3b_dev import prepare_revision
from experiments.skill_crystallization_k3e_dev import (
    FIXTURE_PROBE_SEED,
    REAL_PROBE_SEED,
    _verified_context,
    execute_mock_probe,
    probe_protocols,
    proposal_schema,
    run_proposal,
    run_reassessment,
    update_schema,
    validate_probe,
    validate_update,
)


@pytest.fixture(autouse=True)
def _optional_jsonschema_gate(request):
    if request.node.name not in {
        "test_wire_schema_closed_and_fixed_protocols",
        "test_context_preserves_prior_abstention_as_unproven",
        "test_real_http_client_accepts_custom_investigation_system_prompt",
    }:
        pytest.importorskip("jsonschema")


def parent_data():
    training = observed_training(make_trials(20261108, 16, phase="train"))
    old = {
        "version": 1, "skill_id": "move_away_on_normal_surface", "surface": "normal",
        "min_distance": 2.314917, "max_distance": 2.457525,
        "target_distance": 3.2, "max_actions": 4, "on_failure": "ESCALATE",
        "evidence_ids": [x["experience_id"] for x in training
                         if x["surface_cue"] == "normal"],
    }
    first = {"candidate_raw": old, "training": training}
    state = prepare_revision(first, {"shift_observations": []})
    assert state["suspended"]
    prior_skill = {**old, "skill_id": "renamed_with_new_evidence",
                   "evidence_ids": [state["shift_observations"][0]["experience_id"]]}
    k3b = {
        "shift_observations": state["shift_observations"],
        "schema_validation": "PASS", "proposal_status": "SKILL",
        "proposal": {"status": "SKILL", "reason": "renamed", "skill": prior_skill},
    }
    k3d = {
        "mode": "gemma", "schema_validation": "PASS", "proposal_status": "ABSTAIN",
        "proposal": {"status": "ABSTAIN", "skill": None,
                     "reason": "Already optimized is an unverified claim."},
    }
    return first, k3b, k3d


def chosen_probe(probe_id="START_MARGIN_PAIR"):
    return {
        "status": "PROBE",
        "hypothesis": ("START_MARGIN_SENSITIVE" if probe_id == "START_MARGIN_PAIR"
                       else "MOTION_EFFECT_CHANGED"),
        "probe_id": probe_id,
        "prediction": "A_FAILS_B_SUCCEEDS" if probe_id == "START_MARGIN_PAIR"
        else "A_SUCCEEDS_B_FAILS",
        "reason": "Distinguish hypotheses with paired conditions, not a Skill proposal.",
        "evidence_ids": ["shift-experience-010", "shift-experience-011"],
    }


def test_wire_schema_closed_and_fixed_protocols():
    assert proposal_schema()["additionalProperties"] is False
    assert update_schema()["additionalProperties"] is False
    assert set(proposal_schema()["properties"]) == set(proposal_schema()["required"])
    assert probe_protocols()["common"]["max_actions_per_trial"] == 4
    assert "hidden_effects" not in json.dumps(probe_protocols())


def test_context_preserves_prior_abstention_as_unproven():
    src = _verified_context(*parent_data())
    assert "unverified" in src["k3d_abstain_reason"]
    assert len(src["evidence"]) == 28


def test_valid_margin_probe_observation_and_no_fallback():
    first, k3b, k3d = parent_data()
    r = run_proposal(first, k3b, k3d, mode="fixture", fixture=chosen_probe())
    assert r["status"] == "PROBE"
    assert r["probe"]["seed"] == FIXTURE_PROBE_SEED
    assert r["probe"]["observed_pattern"] == "A_FAILS_B_SUCCEEDS"
    assert r["probe"]["prediction_matches"] is True
    assert r["prediction_assessment"] == "PREDICTION_MATCHED"
    assert "PREDICTION_MATCHED" in r["stages"]
    assert len(r["probe"]["observations"]) == 2
    assert r["probe"]["mock_actions"] <= 8
    assert all(o["action_count"] <= 4 for o in r["probe"]["observations"])
    assert r["holdout_20261126"] == "UNOPENED"
    assert r["model_calls_in_mock_probe"] == 0


def test_regime_probe_prediction_can_be_falsified():
    first, k3b, k3d = parent_data()
    r = run_proposal(first, k3b, k3d, mode="fixture",
                     fixture=chosen_probe("MOTION_REGIME_PAIR"))
    assert r["probe"]["observed_pattern"] == "BOTH_SUCCEED"
    assert r["probe"]["prediction_matches"] is False
    assert r["prediction_assessment"] == "PREDICTION_FALSIFIED"
    assert "PREDICTION_FALSIFIED" in r["stages"]
    assert r["probe"]["observations"][0]["start_distance"] == 2.4
    assert r["probe"]["observations"][1]["start_distance"] == 2.4


def test_abstain_does_not_probe_or_expose_seed():
    first, k3b, k3d = parent_data()
    r = run_proposal(first, k3b, k3d, mode="fixture", fixture={
        "status": "ABSTAIN", "hypothesis": "INDETERMINATE", "probe_id": "NONE",
        "prediction": "UNKNOWN", "reason": "More evidence not warranted",
        "evidence_ids": [],
    })
    assert r["status"] == "ABSTAIN"
    assert r["probe"] is None
    assert r["prediction_assessment"] == "NOT_RUN"
    assert r["holdout_20261126"] == "UNOPENED"


@pytest.mark.parametrize("change,code", [
    ({"hypothesis": "MOTION_EFFECT_CHANGED"}, "NON_DISCRIMINATING"),
    ({"prediction": "UNKNOWN"}, "NON_DISCRIMINATING"),
    ({"evidence_ids": ["future-unknown"]}, "UNSOURCED"),
    ({"evidence_ids": []}, "UNSOURCED"),
])
def test_reject_unsourced_or_non_discriminating_proposal(change, code):
    first, k3b, k3d = parent_data()
    value = {**chosen_probe(), **change}
    with pytest.raises(ValueError, match=code):
        validate_probe(value, _verified_context(first, k3b, k3d)["ids"])


def test_bad_abstain_selection_rejected():
    first, k3b, k3d = parent_data()
    with pytest.raises(ValueError, match="ABSTAIN_MUST_NOT_SELECT_PROBE"):
        validate_probe({**chosen_probe(), "status": "ABSTAIN"},
                       _verified_context(first, k3b, k3d)["ids"])


def test_reject_probe_without_mock_grant():
    with pytest.raises(ValueError, match="PROBE_MOCK_GRANT_REQUIRED"):
        execute_mock_probe(chosen_probe(), seed=FIXTURE_PROBE_SEED, mock_grant=False)


def test_one_model_call_and_no_probe_outcome_leak(monkeypatch, tmp_path):
    import experiments.skill_crystallization_k3e_dev as mod

    first, k3b, k3d = parent_data()
    calls = []

    def stub(evidence, **kwargs):
        calls.append((evidence, kwargs))
        return chosen_probe(), {"finish_reason": "stop"}

    monkeypatch.setattr(mod, "gemma_l2", stub)
    observed_seeds = []

    def do_not_open_real_seed(proposal, *, seed, mock_grant):
        observed_seeds.append(seed)
        return {"mock_seed_not_opened": True, "prediction_matches": True}

    monkeypatch.setattr(mod, "execute_mock_probe", do_not_open_real_seed)
    r = run_proposal(first, k3b, k3d, mode="gemma",
                     endpoint="http://127.0.0.1:8080/v1/chat/completions",
                     model="verified", record_dir=tmp_path / "propose")
    assert len(calls) == 1
    ctx = calls[0][1]["revision_context"]
    assert "20261205" not in json.dumps(ctx)
    assert "20261126" not in json.dumps(ctx)
    assert "observed_pattern" not in json.dumps(ctx)
    assert "hidden_effects" not in json.dumps(ctx)
    assert calls[0][1]["response_schema"] == proposal_schema()
    assert "not creating a Skill" in calls[0][1]["system_instruction"]
    assert r["probe"] == {"mock_seed_not_opened": True, "prediction_matches": True}
    assert r["prediction_assessment"] == "PREDICTION_MATCHED"
    assert observed_seeds == [REAL_PROBE_SEED]
    assert r["provider"]["finish_reason"] == "stop"


def test_explicit_reassess_after_observed_probe_without_skill_execution():
    first, k3b, k3d = parent_data()
    r = run_proposal(first, k3b, k3d, mode="fixture", fixture=chosen_probe())
    result = run_reassessment(first, k3b, k3d, r, mode="fixture", fixture={
        "status": "UPDATE", "hypothesis": "START_MARGIN_SENSITIVE",
        "reason": "Paired outcomes differ; this is not yet a universal rule.",
        "evidence_ids": ["k3e-probe-A", "k3e-probe-B"], "skill_candidate": None,
    })
    assert result["status"] == "UPDATE"
    assert result["hypothesis_assessment"] == "HYPOTHESIS_RETAINED"
    assert result["prediction_assessment"] == "PREDICTION_MATCHED"
    assert result["reason_truth"] == "NOT_INDEPENDENTLY_VERIFIED"
    assert result["skill_execution"] == "NOT_RUN"
    assert result["new_skill_installed"] is False
    assert result["holdout_20261126"] == "UNOPENED"


def test_reassess_rejects_mutated_probe_trace():
    first, k3b, k3d = parent_data()
    r = run_proposal(first, k3b, k3d, mode="fixture", fixture=chosen_probe())
    r["probe"]["observations"][0]["observed_trace"][1] = 999.0
    with pytest.raises(ValueError, match="PROBE_OBSERVATION_SOURCE_MISMATCH"):
        run_reassessment(first, k3b, k3d, r, mode="fixture", fixture={})


def test_no_reassessment_of_abstention():
    first, k3b, k3d = parent_data()
    r = run_proposal(first, k3b, k3d, mode="fixture", fixture={
        "status": "ABSTAIN", "hypothesis": "INDETERMINATE", "probe_id": "NONE",
        "prediction": "UNKNOWN", "reason": "No probe", "evidence_ids": [],
    })
    with pytest.raises(ValueError, match="VALID_PROBE_REPORT_REQUIRED"):
        run_reassessment(first, k3b, k3d, r, mode="fixture", fixture={})


def test_update_rejects_invented_source_and_bad_skill():
    first, k3b, k3d = parent_data()
    ids = _verified_context(first, k3b, k3d)["ids"] | {"k3e-probe-A", "k3e-probe-B"}
    bad = {"status": "UPDATE", "hypothesis": "START_MARGIN_SENSITIVE",
           "reason": "revised", "evidence_ids": ["unobserved"], "skill_candidate": None}
    with pytest.raises(ValueError, match="UNSOURCED"):
        validate_update(bad, ids)
    bad["evidence_ids"] = ["k3e-probe-A"]
    bad["skill_candidate"] = {"foo": "bar"}
    with pytest.raises(ValueError, match="SCHEMA_INVALID"):
        validate_update(bad, ids)


def test_reassess_gemma_receives_probe_observations_only_after_execution(monkeypatch, tmp_path):
    import experiments.skill_crystallization_k3e_dev as mod

    first, k3b, k3d = parent_data()
    r = run_proposal(first, k3b, k3d, mode="fixture", fixture=chosen_probe())
    r["mode"] = "gemma"
    # Never open the real seed in an HTTP contract test.
    fixture_probe = r["probe"]
    monkeypatch.setattr(mod, "_verify_proposal_report", lambda *_: fixture_probe)
    got = []

    def stub(evidence, **kwargs):
        got.append((evidence, kwargs))
        return {"status": "ABSTAIN", "hypothesis": "INDETERMINATE",
                "reason": "Inconclusive pair", "evidence_ids": [],
                "skill_candidate": None}, {}

    monkeypatch.setattr(mod, "gemma_l2", stub)
    z = run_reassessment(first, k3b, k3d, r, mode="gemma",
                         endpoint="http://127.0.0.1:8080/v1/chat/completions", model="test", record_dir=tmp_path / "reassess")
    assert z["status"] == "ABSTAIN"
    assert z["hypothesis_assessment"] == "HYPOTHESIS_WITHHELD"
    assert len(got) == 1
    assert len(got[0][0]) == 30
    assert "k3e-probe-A" in json.dumps(got[0][0])
    assert "k3e-probe-B" in json.dumps(got[0][0])
    assert got[0][1]["response_schema"] == update_schema()
    assert "20261126" not in json.dumps(got[0][1]["revision_context"])


def test_real_http_client_accepts_custom_investigation_system_prompt(monkeypatch):
    import urllib.request

    from experiments.skill_crystallization_dev import gemma_l2

    captured = []
    answer = chosen_probe()

    class Response:
        status = 200

        def __enter__(self):
            return self

        def __exit__(self, *_args):
            return False

        def read(self):
            return json.dumps({
                "choices": [{
                    "finish_reason": "stop",
                    "message": {"content": json.dumps(answer),
                                "reasoning_content": None},
                }],
                "usage": {"completion_tokens": 50},
            }).encode("utf-8")

    def mock_urlopen(request, *, timeout):
        del timeout
        captured.append(json.loads(request.data))
        return Response()

    monkeypatch.setattr(urllib.request, "urlopen", mock_urlopen)
    spec, record = gemma_l2(
        [], endpoint="http://127.0.0.1:8080/v1/chat/completions",
        model="stub", timeout=2,
        response_schema=proposal_schema(),
        system_instruction="K3-E hypothesis investigation, not Skill generation",
    )
    assert spec == answer
    assert record["finish_reason"] == "stop"
    assert len(captured) == 1
    request = captured[0]
    assert request["messages"][0]["content"].startswith("K3-E hypothesis")
    assert "You may propose one low-cost" not in request["messages"][0]["content"]
    assert request["reasoning_effort"] == "none"
    assert request["response_format"]["json_schema"]["strict"] is True
    assert request["response_format"]["json_schema"]["schema"] == proposal_schema()


def test_reassessment_changed_hypothesis_is_not_claimed_correct():
    first, k3b, k3d = parent_data()
    report = run_proposal(first, k3b, k3d, mode="fixture",
                          fixture=chosen_probe("MOTION_REGIME_PAIR"))
    assert report["prediction_assessment"] == "PREDICTION_FALSIFIED"
    result = run_reassessment(first, k3b, k3d, report, mode="fixture", fixture={
        "status": "UPDATE", "hypothesis": "START_MARGIN_SENSITIVE",
        "reason": "The expected A/B success separation was not observed.",
        "evidence_ids": ["k3e-probe-A", "k3e-probe-B"],
        "skill_candidate": None,
    })
    assert result["hypothesis_assessment"] == "HYPOTHESIS_CHANGED"
    assert "HYPOTHESIS_CHANGED" in result["stages"]
    assert result["prediction_assessment"] == "PREDICTION_FALSIFIED"
    assert result["reason_truth"] == "NOT_INDEPENDENTLY_VERIFIED"
    assert result["skill_execution"] == "NOT_RUN"


def test_forged_gemma_mode_is_rejected_before_hidden_probe_replay(monkeypatch):
    import experiments.skill_crystallization_k3e_dev as mod

    first, k3b, k3d = parent_data()
    source = run_proposal(first, k3b, k3d, mode="fixture",
                          fixture=chosen_probe())
    source["mode"] = "gemma"
    monkeypatch.setattr(mod, "execute_mock_probe",
                        lambda *_args, **_kwargs: pytest.fail(
                            "Unverified mode must not access reserved real seed"))
    with pytest.raises(ValueError, match="GEMMA_PROPOSAL_SOURCE_UNVERIFIED"):
        run_reassessment(first, k3b, k3d, source, mode="gemma",
                         endpoint="http://127.0.0.1:8080/v1/chat/completions",
                         model="test")


def test_forged_gemma_request_hash_is_rejected_before_probe_replay(monkeypatch):
    import experiments.skill_crystallization_k3e_dev as mod

    first, k3b, k3d = parent_data()
    source = run_proposal(first, k3b, k3d, mode="fixture",
                          fixture=chosen_probe())
    source["mode"] = "gemma"
    source["provider"] = {
        "http_status": 200, "finish_reason": "stop",
        "reasoning_content": None,
        "request": {"model": "fake"},
        "request_sha256": "invalid",
        "response_raw": "{}",
    }
    monkeypatch.setattr(mod, "execute_mock_probe",
                        lambda *_args, **_kwargs: pytest.fail(
                            "Bad hash must not access reserved real seed"))
    with pytest.raises(ValueError, match="GEMMA_REQUEST_HASH_MISMATCH"):
        run_reassessment(first, k3b, k3d, source, mode="gemma",
                         endpoint="http://127.0.0.1:8080/v1/chat/completions",
                         model="test")


def test_real_gemma_mode_requires_raw_record_dir_before_http(monkeypatch):
    import experiments.skill_crystallization_k3e_dev as mod

    first, k3b, k3d = parent_data()
    monkeypatch.setattr(mod, "_invoke", lambda *_a, **_k: pytest.fail(
        "No model call without a raw recording directory"))
    with pytest.raises(ValueError, match="GEMMA_RAW_RECORD_DIR_REQUIRED"):
        run_proposal(first, k3b, k3d, mode="gemma",
                     endpoint="http://127.0.0.1:8080/v1/chat/completions",
                     model="verified")
    report = run_proposal(first, k3b, k3d, mode="fixture",
                          fixture=chosen_probe())
    report["mode"] = "gemma"
    monkeypatch.setattr(mod, "_verify_proposal_report", lambda *_: report["probe"])
    with pytest.raises(ValueError, match="GEMMA_RAW_RECORD_DIR_REQUIRED"):
        run_reassessment(first, k3b, k3d, report, mode="gemma",
                         endpoint="http://127.0.0.1:8080/v1/chat/completions",
                         model="verified")
