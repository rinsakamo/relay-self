"""K3-G opt-in ten-Action L2 choice, raw one-shot HTTP and source gates."""

from __future__ import annotations

import copy
import hashlib
import json
import urllib.request
from pathlib import Path

import pytest

from experiments.skill_crystallization_dev import (
    gemma_l2,
    skill_json_schema,
    validate_skill,
)
from experiments.skill_crystallization_k3f_budget_dev import budget10_schema
from experiments.skill_crystallization_k3g_ten_action_choice_dev import (
    FIXTURE_SEED,
    PREVIOUS_SEEDS,
    REAL_SKILL_HOLDOUT_SEED,
    choice_schema,
    fresh_trials,
    paired_evaluation,
    run_choice,
    validate_choice,
    verified_context,
    verify_input_manifests,
)

EVIDENCE_DIR = Path(__file__).resolve().parents[1] / "evidence"


@pytest.fixture
def originals():
    files = (
        "l431-gemma-20261108/first-report.json",
        "l431-k3b-gemma-20261108/report.json",
        "l431-k3d-gemma-20261108/report.json",
        "l431-k3e-gemma-20261108/proposal.json",
    )
    return [json.loads((EVIDENCE_DIR / name).read_text(encoding="utf-8"))
            for name in files]


@pytest.fixture
def source(originals):
    return verified_context(*originals)


def response(status, *, skill=None, evidence_ids=None):
    return {
        "status": status, "reason": "Grounded tentative control option",
        "skill": skill, "hypothesis": "INDETERMINATE",
        "probe_id": "NONE", "prediction": "UNKNOWN",
        "evidence_ids": evidence_ids if evidence_ids is not None else [],
    }


def revised(old, *, max_actions=10):
    return {
        **old, "skill_id": "ten-action-conditional-shadow",
        "max_actions": max_actions,
    }


def requires_schema():
    pytest.importorskip("jsonschema")


def test_old_four_action_contract_never_mutated(source):
    old = source["old_skill"]
    assert old["max_actions"] == 4
    assert skill_json_schema()["properties"]["max_actions"]["enum"] == [1, 2, 3, 4]
    assert budget10_schema()["properties"]["max_actions"]["enum"] == list(range(1, 11))
    with pytest.raises(ValueError, match="ACTION_BUDGET_INVALID"):
        validate_skill(revised(old), source["ids"])
    assert old["max_actions"] == 4


def test_real_abstention_chain_is_source_qualified(source):
    assert len(source["evidence"]) == 28
    assert source["prior_decisions"] == ["K3D_ABSTAIN", "K3E_ABSTAIN"]


def test_mutated_parent_abstention_refused(originals):
    fake = copy.deepcopy(originals)
    fake[-1]["proposal"]["status"] = "PROBE"
    with pytest.raises(ValueError, match="K3E_ABSTENTION_SOURCE_INVALID"):
        verified_context(*fake)


def test_mutated_shift_outcome_refused(originals):
    fake = copy.deepcopy(originals)
    fake[1]["shift_observations"][0]["outcome_success"] = (
        not fake[1]["shift_observations"][0]["outcome_success"]
    )
    with pytest.raises(ValueError, match="PRIOR_SOURCE_MISMATCH"):
        verified_context(*fake)


def test_g3_wire_enum_uses_only_optin_ten_not_original():
    schema = choice_schema()
    assert schema["properties"]["status"]["enum"] == ["SKILL", "PROBE", "ABSTAIN"]
    assert schema["additionalProperties"] is False
    assert schema["properties"]["skill"]["anyOf"][0]["properties"][
        "max_actions"]["enum"] == list(range(1, 11))
    assert skill_json_schema()["properties"]["max_actions"]["enum"] == [1, 2, 3, 4]


@pytest.mark.parametrize("bad", [0, 11, True, 4.5, "10", None])
def test_bad_ten_action_proposals_rejected(source, bad):
    requires_schema()
    skill = revised(source["old_skill"], max_actions=bad)
    with pytest.raises(ValueError):
        validate_choice(response("SKILL", skill=skill), evidence_ids=source["ids"])


def test_skill_requires_cited_experience_and_no_branch_conflict(source):
    requires_schema()
    wrong_skill = revised(source["old_skill"])
    wrong_skill["evidence_ids"] = ["future-seed-experience"]
    with pytest.raises(ValueError, match="EVIDENCE_NOT_TRAINING_SOURCED"):
        validate_choice(response("SKILL", skill=wrong_skill), evidence_ids=source["ids"])
    valid = response("SKILL", skill=revised(source["old_skill"]))
    valid["probe_id"] = "MOTION_REGIME_PAIR"
    with pytest.raises(ValueError, match="SKILL_CHOICE_BRANCH_CONFLICT"):
        validate_choice(valid, evidence_ids=source["ids"])


def test_abstain_does_not_select_skill_or_probe(source, originals):
    requires_schema()
    result = run_choice(*originals, mode="fixture", fixture=response("ABSTAIN"))
    assert result["status"] == "ABSTAIN"
    assert result["skill_holdout"] is None
    assert "EXPLICIT_ABSTENTION_ACCEPTED" in result["stages"]
    assert result["preserved_seeds"]["20261126"] == "UNOPENED"
    assert result["preserved_seeds"]["20261205"] == "UNOPENED"
    bad = response("ABSTAIN", skill=revised(source["old_skill"]))
    with pytest.raises(ValueError, match="ABSTAIN_CANNOT_SELECT_ACTION_OR_PROBE"):
        validate_choice(bad, evidence_ids=source["ids"])


def test_probe_is_choice_not_auto_executed(originals):
    requires_schema()
    value = response("PROBE", evidence_ids=["shift-experience-010"])
    value.update({
        "hypothesis": "START_MARGIN_SENSITIVE",
        "probe_id": "START_MARGIN_PAIR",
        "prediction": "A_FAILS_B_SUCCEEDS",
    })
    result = run_choice(*originals, mode="fixture", fixture=value)
    assert result["status"] == "PROBE"
    assert result["skill_holdout"] is None
    assert "PROBE_SELECTED_NOT_EXECUTED" in result["stages"]
    assert result["native_s49_actions"] == 0


@pytest.mark.parametrize("invalid", [
    {"hypothesis": "INDETERMINATE"},
    {"probe_id": "MOTION_REGIME_PAIR"},
    {"prediction": "UNKNOWN"},
    {"evidence_ids": []},
    {"evidence_ids": ["future"]},
])
def test_invalid_probe_refused_without_action(source, invalid):
    requires_schema()
    value = response("PROBE", evidence_ids=["shift-experience-010"])
    value.update({
        "hypothesis": "START_MARGIN_SENSITIVE",
        "probe_id": "START_MARGIN_PAIR",
        "prediction": "A_FAILS_B_SUCCEEDS",
    })
    value.update(invalid)
    with pytest.raises(ValueError):
        validate_choice(value, evidence_ids=source["ids"])


def test_skill_change_evaluated_on_fixture_only(originals, source):
    requires_schema()
    old = source["old_skill"]
    initial = copy.deepcopy(originals)
    result = run_choice(*originals, mode="fixture",
                        fixture=response("SKILL", skill=revised(old)))
    assert originals == initial
    assert result["status"] == "SKILL"
    assert result["skill_holdout_seed"] == FIXTURE_SEED
    assert result["skill_holdout"]["count"] == 64
    assert result["execution_changed_fields"] == ["max_actions"]
    assert "PAIRED_MOCK_HOLDOUT_EVALUATED" in result["stages"]
    assert result["skill_installed"] is False
    assert result["native_s49_actions"] == 0
    assert sum(v["n"] for v in result["skill_holdout"]["by_regime"].values()) == 64


def test_equal_execution_skips_holdout(originals, source, monkeypatch):
    requires_schema()
    import experiments.skill_crystallization_k3g_ten_action_choice_dev as mod

    monkeypatch.setattr(mod, "paired_evaluation", lambda *_a, **_kw: pytest.fail(
        "Equivalent policy must not open holdout"))
    skill = {**source["old_skill"], "skill_id": "only-renamed"}
    result = run_choice(*originals, mode="fixture",
                        fixture=response("SKILL", skill=skill))
    assert result["skill_holdout"] is None
    assert "NO_BEHAVIORAL_CHANGE" in result["stages"]


def test_old_skill_is_comparator_only_and_no_automatic_fallback(source):
    requires_schema()
    result = paired_evaluation(source["old_skill"], revised(source["old_skill"]),
                               evidence_ids=source["ids"], seed=FIXTURE_SEED)
    for regime, stats in result["by_regime"].items():
        assert stats["n"] == 16, regime
        assert stats["automatic_postfailure_actions"] == 0
        assert stats["new_selected_failure_escalations"] >= 0
        assert stats["new_actions"] <= 160
        assert stats["old_actions"] <= 64
        assert stats["cheap_actions"] <= 48
        assert stats["new_success"] >= 0
    assert result["model_calls_in_mock"] == 0


@pytest.mark.parametrize("seed", sorted(PREVIOUS_SEEDS) + [REAL_SKILL_HOLDOUT_SEED])
def test_hidden_and_exposed_seeds_not_usable_in_fixture(seed, source, originals):
    if seed == REAL_SKILL_HOLDOUT_SEED:
        requires_schema()
        with pytest.raises(ValueError, match="HOLDOUT_SEED_NOT_ALLOWED"):
            run_choice(*originals, mode="fixture",
                       fixture=response("SKILL", skill=revised(source["old_skill"])),
                       evaluation_seed=seed)
    else:
        with pytest.raises(ValueError, match="EXPOSED_OR_INVALID_SEED"):
            fresh_trials(seed)


def test_deterministic_ten_effect_generator_for_new_seed_only():
    first = fresh_trials(FIXTURE_SEED, n=16)
    assert first == fresh_trials(FIXTURE_SEED, n=16)
    assert len(first) == 16
    assert all(len(trial.effects) == 10 for _, trial in first)
    assert sorted(set(regime for regime, _ in first)) == [
        "ice_changed", "normal_changed", "normal_reference",
        "normal_slower_stress",
    ]


def test_gemma_requires_verified_endpoint_model_and_raw_dir(originals):
    with pytest.raises(ValueError, match="LOCAL_GEMMA_MODEL_AND_RAW_RECORD_DIR_REQUIRED"):
        run_choice(*originals, mode="gemma",
                   endpoint="http://127.0.0.1:8080/v1/chat/completions",
                   model="some-model")


def test_real_mode_one_call_and_unopened_seed_not_leaked(originals, monkeypatch, tmp_path):
    requires_schema()
    import experiments.skill_crystallization_k3g_ten_action_choice_dev as mod

    calls = []

    def stub(rows, **kwargs):
        calls.append((rows, kwargs))
        return response("ABSTAIN"), {"http_status": 200, "finish_reason": "stop"}

    monkeypatch.setattr(mod, "gemma_l2", stub)
    result = run_choice(
        *originals, mode="gemma", endpoint="http://127.0.0.1:8080/v1/chat/completions",
        model="verified-local", record_dir=tmp_path / "record",
    )
    assert len(calls) == 1
    assert result["status"] == "ABSTAIN"
    assert result["skill_holdout"] is None
    evidence, kwargs = calls[0]
    assert len(evidence) == 28
    assert kwargs["max_actions_allowed"] == 10
    assert kwargs["response_schema"] == choice_schema()
    assert kwargs["system_instruction"].count("TEN") >= 1
    serialized = json.dumps(kwargs)
    assert "20261213" not in serialized
    assert "20261126" not in serialized
    assert "20261205" not in serialized
    assert "20261207" not in serialized
    assert "normal_slower_stress" not in serialized
    assert kwargs["revision_context"]["public_probe_options"][
        "START_MARGIN_PAIR"]["max_actions_per_condition"] == 10
    assert kwargs["revision_context"]["public_probe_options"][
        "MOTION_REGIME_PAIR"]["A_start"] == 2.4
    assert "effect" not in json.dumps(
        kwargs["revision_context"]["public_probe_options"]
    ).lower()
    assert "K3F_SYNTHETIC" not in serialized


def test_gemma_selects_skill_and_holdout_only_after_valid_response(
    originals, source, monkeypatch, tmp_path,
):
    requires_schema()
    import experiments.skill_crystallization_k3g_ten_action_choice_dev as mod

    observations = []

    def stub(_evidence, **_kwargs):
        return response("SKILL", skill=revised(source["old_skill"])), {
            "http_status": 200, "finish_reason": "stop",
        }

    def eval_stub(old, new, *, evidence_ids, seed):
        observations.append(seed)
        assert old["max_actions"] == 4 and new["max_actions"] == 10
        assert evidence_ids == source["ids"]
        return {"count": 64}

    monkeypatch.setattr(mod, "gemma_l2", stub)
    monkeypatch.setattr(mod, "paired_evaluation", eval_stub)
    r = run_choice(*originals, mode="gemma",
                   endpoint="http://127.0.0.1:8080/v1/chat/completions",
                   model="verified-local", record_dir=tmp_path / "new")
    assert observations == [REAL_SKILL_HOLDOUT_SEED]
    assert r["skill_holdout_seed"] == REAL_SKILL_HOLDOUT_SEED


def test_wire_client_sends_ten_without_changing_default(monkeypatch, tmp_path):
    probe_request = []
    reply = response("ABSTAIN")

    class Response:
        status = 200

        def __enter__(self):
            return self

        def __exit__(self, *_exc):
            return False

        def read(self):
            return json.dumps({
                "choices": [{
                    "finish_reason": "stop",
                    "message": {"content": json.dumps(reply), "reasoning_content": None},
                }],
                "usage": {"completion_tokens": 50},
            }).encode()

    def fake_http(request, *, timeout):
        del timeout
        probe_request.append(json.loads(request.data))
        return Response()

    monkeypatch.setattr(urllib.request, "urlopen", fake_http)
    actual, _record = gemma_l2(
        [], endpoint="http://127.0.0.1:8080/v1/chat/completions",
        model="verified", timeout=2, response_schema=choice_schema(),
        max_actions_allowed=10,
        system_instruction="K3-G ten Action decision only",
        record_dir=tmp_path / "raw",
    )
    assert actual == reply
    assert len(probe_request) == 1
    assert json.loads(probe_request[0]["messages"][1]["content"])["maximum_actions"] == 10
    assert probe_request[0]["response_format"]["json_schema"]["strict"] is True
    assert probe_request[0]["response_format"]["json_schema"]["schema"] == choice_schema()
    assert (tmp_path / "raw" / "request.raw.json").is_file()


def test_legacy_client_blocks_unrecorded_ten_budget():
    with pytest.raises(ValueError, match="EXTENDED_BUDGET_REQUIRES_EXPLICIT_SCHEMA_PROMPT"):
        gemma_l2(
            [], endpoint="http://127.0.0.1:8080/v1/chat/completions",
            model="verified", timeout=2, max_actions_allowed=10,
        )


def test_manifest_preflight_accepts_unmodified_multiple_original_files(tmp_path):
    base = tmp_path / "source"
    base.mkdir()
    a = base / "report.json"
    a.write_bytes(b'{"status":"ABSTAIN"}')
    b = base / "audit.txt"
    b.write_bytes(b"unrelated original")
    lines = [
        f"{hashlib.sha256(a.read_bytes()).hexdigest()}  ./report.json",
        f"{hashlib.sha256(b.read_bytes()).hexdigest()}  ./audit.txt",
    ]
    (base / "SHA256SUMS").write_text("\n".join(lines) + "\n")
    audit = verify_input_manifests([a])
    assert audit[str(base.resolve())]["checked_entries"] == 2
    assert audit[str(base.resolve())]["status"] == "PASS"


def test_manifest_preflight_rejects_tampered_noninput_file(tmp_path):
    base = tmp_path / "source"
    base.mkdir()
    a = base / "report.json"
    b = base / "runtime.txt"
    a.write_bytes(b"valid input")
    b.write_bytes(b"valid runtime")
    original = [
        f"{hashlib.sha256(a.read_bytes()).hexdigest()}  report.json",
        f"{hashlib.sha256(b.read_bytes()).hexdigest()}  runtime.txt",
    ]
    (base / "SHA256SUMS").write_text("\n".join(original) + "\n")
    b.write_bytes(b"altered runtime")
    with pytest.raises(ValueError, match="ORIGINAL_SHA_MANIFEST_MISMATCH"):
        verify_input_manifests([a])


def test_manifest_preflight_refuses_unlisted_input(tmp_path):
    base = tmp_path / "source"
    base.mkdir()
    a = base / "report.json"
    b = base / "other.txt"
    a.write_bytes(b"not included")
    b.write_bytes(b"manifested")
    (base / "SHA256SUMS").write_text(
        f"{hashlib.sha256(b.read_bytes()).hexdigest()}  other.txt\n"
    )
    with pytest.raises(ValueError, match="ORIGINAL_INPUT_NOT_MANIFESTED"):
        verify_input_manifests([a])


@pytest.mark.parametrize("invalid", [0, 11, True, 2.5])
def test_model_client_rejects_out_of_range_budget_before_post(invalid, monkeypatch):
    monkeypatch.setattr(urllib.request, "urlopen", lambda *_a, **_kw: pytest.fail(
        "Invalid budget must fail before HTTP"))
    with pytest.raises(ValueError, match="INVALID_L2_ACTION_BUDGET"):
        gemma_l2(
            [], endpoint="http://127.0.0.1:8080/v1/chat/completions",
            model="verified", timeout=2, max_actions_allowed=invalid,
        )


def test_default_model_wire_remains_four_action_budget(monkeypatch):
    seen = []

    class Response:
        status = 200

        def __enter__(self):
            return self

        def __exit__(self, *_exc):
            return False

        def read(self):
            return json.dumps({
                "choices": [{
                    "finish_reason": "stop",
                    "message": {"content": json.dumps({"status": "ABSTAIN"}),
                                "reasoning_content": None},
                }],
                "usage": {},
            }).encode()

    def fake_http(request, *, timeout):
        del timeout
        seen.append(json.loads(request.data))
        return Response()

    monkeypatch.setattr(urllib.request, "urlopen", fake_http)
    response, _record = gemma_l2(
        [], endpoint="http://127.0.0.1:8080/v1/chat/completions",
        model="verified", timeout=2,
    )
    assert response == {"status": "ABSTAIN"}
    assert len(seen) == 1
    assert json.loads(seen[0]["messages"][1]["content"])["maximum_actions"] == 4
    assert seen[0]["response_format"]["json_schema"]["schema"] == skill_json_schema()
