"""SOUL matched L2 choice: deterministic identity input and no action side effects."""

from __future__ import annotations

import copy
import json
from pathlib import Path

import pytest

from experiments.skill_crystallization_dev import skill_json_schema
from experiments.skill_crystallization_k3g_ten_action_choice_dev import (
    K3G_SYSTEM_INSTRUCTION,
    choice_schema,
    verified_context,
)
from experiments.skill_crystallization_soul_matched_dev import (
    SOUL_DIRECTIVES,
    run_matched_choice,
    select_directive,
)

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


def _abstain():
    return {
        "status": "ABSTAIN", "reason": "Insufficient outcome evidence",
        "skill": None, "hypothesis": "INDETERMINATE",
        "probe_id": "NONE", "prediction": "UNKNOWN",
        "evidence_ids": [],
    }


def test_four_conditions_have_no_hardcoded_skill_answers():
    assert tuple(SOUL_DIRECTIVES) == ("neutral", "curious", "cautious", "bold")
    assert SOUL_DIRECTIVES["neutral"] is None
    for name in ("curious", "cautious", "bold"):
        directive = select_directive(name)
        assert isinstance(directive, str)
        assert len(directive) < 500
        assert "\n" not in directive
        assert all(term not in directive for term in ("SKILL", "PROBE", "ABSTAIN"))


def test_unknown_condition_fails():
    with pytest.raises(ValueError, match="UNKNOWN_SOUL_CONDITION"):
        select_directive("must_probe")


def test_existing_skill_schema_stays_bounded_four():
    assert skill_json_schema()["properties"]["max_actions"]["enum"] == [1, 2, 3, 4]
    assert choice_schema()["properties"]["status"]["enum"] == [
        "SKILL", "PROBE", "ABSTAIN",
    ]


def test_fixture_has_no_model_call_and_no_outcome(originals):
    before = copy.deepcopy(originals)
    report = run_matched_choice(
        originals, condition="curious", mode="fixture", fixture=_abstain(),
    )
    assert originals == before
    assert report["status"] == "ABSTAIN"
    assert report["soul_directive"] == SOUL_DIRECTIVES["curious"]
    assert report["choice_semantically_valid"]
    assert report["observed_actions"] == 0
    assert report["holdout_or_probe_executed"] is False
    assert not report["personality_or_learning_proven"]
    assert report["skill_holdout_seed"] is None


def test_fixture_skill_candidate_is_never_evaluated(originals, monkeypatch):
    import experiments.skill_crystallization_k3g_ten_action_choice_dev as k3g

    pytest.importorskip("jsonschema")
    source = verified_context(*originals)
    skill = {**source["old_skill"], "max_actions": 10,
             "skill_id": "new_soul_candidate"}
    fixture = {**_abstain(), "status": "SKILL", "skill": skill}
    monkeypatch.setattr(k3g, "paired_evaluation", lambda *_a, **_k: pytest.fail(
        "matched choice must not open any independent holdout"))
    report = run_matched_choice(
        originals, condition="bold", mode="fixture", fixture=fixture,
    )
    assert report["status"] == "SKILL"
    assert "EXECUTION_SPEC_CHANGED" in report["stages"]
    assert "SKILL_HOLDOUT_SKIPPED_MATCHED_SOUL_COMPARISON" in report["stages"]
    assert report["skill_holdout"] is None
    assert report["skill_installed"] is False


def test_raw_invalid_probe_kept_invalid(originals):
    pytest.importorskip("jsonschema")
    fixture = {**_abstain(), "status": "PROBE",
               "hypothesis": "MOTION_EFFECT_CHANGED",
               "probe_id": "MOTION_REGIME_PAIR",
               "prediction": "UNKNOWN",  # K3-G prior invalid observation.
               "evidence_ids": ["shift-experience-010"]}
    report = run_matched_choice(
        originals, condition="neutral", mode="fixture", fixture=fixture,
    )
    assert report["raw_model_choice"] == "PROBE"
    assert not report["choice_semantically_valid"]
    assert report["validator_error"] == "PROBE_MUST_BE_FALSIFIABLE"
    assert report["skill_holdout"] is None


def test_no_soul_request_is_original_k3g_system_text(originals, monkeypatch, tmp_path):
    import experiments.skill_crystallization_k3g_ten_action_choice_dev as k3g

    calls = []

    def fake_gemma(evidence, **kwargs):
        calls.append((evidence, kwargs))
        return _abstain(), {"http_status": 200, "finish_reason": "stop"}

    monkeypatch.setattr(k3g, "gemma_l2", fake_gemma)
    for name in SOUL_DIRECTIVES:
        run_matched_choice(
            originals, condition=name, mode="gemma",
            endpoint="http://127.0.0.1:8080/v1/chat/completions",
            model="stub", record_dir=tmp_path / name,
        )
    assert len(calls) == 4
    baseline = calls[0][1]
    assert baseline["max_actions_allowed"] == 10
    original_system = baseline["system_instruction"]
    assert original_system == K3G_SYSTEM_INSTRUCTION
    assert "Stable identity value prior" not in original_system
    for i, name in enumerate(SOUL_DIRECTIVES):
        evidence, kwargs = calls[i]
        assert evidence == calls[0][0]
        for key in ("revision_context", "response_schema",
                    "max_actions_allowed", "endpoint", "model", "timeout"):
            assert kwargs[key] == baseline[key]
        assert kwargs["record_dir"] != baseline["record_dir"] or name == "neutral"
        if name == "neutral":
            assert kwargs["system_instruction"] == original_system
        else:
            line, common = kwargs["system_instruction"].split("\n", 1)
            assert common == original_system
            assert line.endswith(SOUL_DIRECTIVES[name])
            assert not any(
                label in kwargs["system_instruction"]
                for label in ("soul_condition", "curious:", "cautious:", "bold:")
            )
        payload = json.dumps(kwargs, default=str)
        assert "20261213" not in payload
        assert "20261205" not in payload


@pytest.mark.parametrize("bad", ["", " ", "bad\nrole", 11, True, "x" * 501])
def test_invalid_directive_rejected_before_provider(originals, bad, monkeypatch, tmp_path):
    import experiments.skill_crystallization_k3g_ten_action_choice_dev as k3g

    monkeypatch.setattr(k3g, "gemma_l2", lambda *_a, **_k: pytest.fail(
        "invalid identity must not get sent"))
    with pytest.raises(ValueError, match="SOUL_DIRECTIVE_INVALID"):
        k3g.run_choice(
            *originals, mode="gemma", soul_directive=bad,
            endpoint="http://127.0.0.1:8080/v1/chat/completions",
            model="stub", record_dir=tmp_path,
            evaluate_skill=False,
        )
