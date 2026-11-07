"""No Gemma, World, or physical Action calls in these focused DEV tests."""

import json
import urllib.request

import pytest

from experiments.skill_crystallization_dev import (
    Cue,
    applicable,
    eval_trials,
    experiment,
    gemma_l2,
    make_trials,
    negative_controls,
    observed_training,
    proxy_l2,
    run_skill,
    skill_json_schema,
    validate_skill,
)


def _candidate_and_training():
    training = observed_training(make_trials(14, 16, phase="train"))
    candidate = proxy_l2(training)
    ids = {row["experience_id"] for row in training}
    return validate_skill(candidate, ids), ids


def test_proxy_uses_only_observed_training_and_is_reproducible():
    first = experiment(mode="proxy", seed=20261108)
    second = experiment(mode="proxy", seed=20261108)
    assert first == second
    assert first["candidate_raw"]["max_actions"] <= 4
    assert first["provider_record"] is None
    assert first["validator_error"] is None
    assert (first["holdout"]["ice"]["skill_success"]
            > first["holdout"]["ice"]["baseline_success"])
    assert first["holdout"]["ice"]["cheap_success"] == first["holdout"]["ice"]["skill_success"]
    assert (first["holdout"]["normal"]["baseline_actions"]
            == first["holdout"]["normal"]["skill_actions"])
    assert first["shift"]["suspended_at_episode"] is not None
    assert all(first["negatives"].values())


def test_fail_closed_for_unknown_stale_and_wrong_session():
    candidate, ids = _candidate_and_training()
    t = make_trials(15, 1, phase="test")[0]
    t = type(t)("ice", t.start, t.effects, t.session)
    checks = negative_controls(candidate, ids, t)
    assert all(checks.values())
    for cue in (Cue("ice", t.start, t.session, 11, 10),
                Cue(None, t.start, t.session, 10, 11),
                Cue("ice", t.start, "other", 10, 11)):
        assert not applicable(candidate, cue, t)
        with pytest.raises(ValueError, match="NO_MATCH"):
            run_skill(candidate, t, cue)


@pytest.mark.parametrize("field,value", [
    ("max_actions", 500), ("max_actions", True), ("min_distance", float("nan")),
    ("surface", "wildcard"), ("evidence_ids", ["fabricated"]),
    ("on_failure", "REPEAT_FOREVER"),
])
def test_validator_rejects_invalid_candidate(field, value):
    candidate, ids = _candidate_and_training()
    with pytest.raises(ValueError):
        validate_skill({**candidate, field: value}, ids)


def test_gemma_schema_is_closed():
    schema = skill_json_schema()
    assert schema["additionalProperties"] is False
    assert set(schema["required"]) == set(schema["properties"])


def test_gemma_request_excludes_holdout_and_records_raw(monkeypatch):
    training = observed_training(make_trials(43, 16, phase="train"))
    expected = proxy_l2(training)
    captured = []

    class Response:
        status = 200
        def __enter__(self):
            return self
        def __exit__(self, *_):
            return False
        def read(self):
            return json.dumps({"choices": [{"finish_reason": "stop", "message": {
                "content": json.dumps(expected), "reasoning_content": None}}],
                "usage": {"completion_tokens": 128}}).encode()

    def fake_urlopen(request, *, timeout):
        del timeout
        captured.append(json.loads(request.data))
        return Response()

    monkeypatch.setattr(urllib.request, "urlopen", fake_urlopen)
    spec, record = gemma_l2(training, endpoint="http://127.0.0.1:8080/v1/chat/completions",
                            model="test-GGUF", timeout=5)
    assert spec == expected
    assert record["finish_reason"] == "stop"
    assert len(captured) == 1
    assert captured[0]["response_format"]["type"] == "json_schema"
    assert captured[0]["reasoning_effort"] == "none"
    assert "holdout" not in json.dumps(captured[0])
    assert "effects" not in json.dumps(captured[0])


def test_refuse_nonlocal_model_endpoint():
    with pytest.raises(ValueError, match="LOCAL_ENDPOINT_REQUIRED"):
        gemma_l2([], endpoint="https://example.com/v1/chat/completions",
                 model="x", timeout=2)


def test_interpreter_bounded_effect_and_no_change_on_normal():
    candidate, _ = _candidate_and_training()
    trials = make_trials(30, 32, phase="holdout")
    rows = eval_trials(candidate, trials)
    assert rows["ice"]["skill_selected"] == 16
    assert rows["normal"]["skill_selected"] == 0
    assert rows["ice"]["skill_actions"] <= 16 * 4
    assert rows["normal"]["skill_actions"] == rows["normal"]["baseline_actions"]
    with pytest.raises(ValueError, match="INVALID_RUNTIME_SKILL"):
        ice = type(trials[0])("ice", trials[0].start, trials[0].effects, trials[0].session)
        run_skill(
            {**candidate, "max_actions": 100}, ice,
            Cue("ice", ice.start, ice.session, 10, 11),
        )


def test_protocol_failure_preserves_raw_evidence(monkeypatch):
    from experiments.skill_crystallization_dev import ModelCallFailure

    raw = json.dumps({"choices": [{"finish_reason": "length", "message": {
        "content": "{}", "reasoning_content": None}}]})

    class Response:
        status = 200
        def __enter__(self):
            return self
        def __exit__(self, *_):
            return False
        def read(self):
            return raw.encode()

    monkeypatch.setattr(urllib.request, "urlopen", lambda *a, **k: Response())
    with pytest.raises(ModelCallFailure, match="GEMMA_PROTOCOL_INVALID") as caught:
        gemma_l2([], endpoint="http://localhost:8000/v1/chat/completions",
                 model="test", timeout=2)
    assert caught.value.record["response_raw"] == raw


def test_revision_context_stays_in_single_request(monkeypatch):
    training = observed_training(make_trials(43, 16, phase="train"))
    expected = proxy_l2(training)
    captured = []

    class Response:
        status = 200

        def __enter__(self):
            return self

        def __exit__(self, *_):
            return False

        def read(self):
            return json.dumps({"choices": [{"finish_reason": "stop", "message": {
                "content": json.dumps(expected)}}]}).encode()

    def send(request, *, timeout):
        captured.append(json.loads(request.data))
        return Response()

    monkeypatch.setattr(urllib.request, "urlopen", send)
    gemma_l2(training, endpoint="http://localhost:8000/v1/chat/completions", model="x",
             timeout=2, revision_context={"failure_reason": "observed failure"})
    assert len(captured) == 1
    assert "observed failure" in captured[0]["messages"][1]["content"]


def test_revision_stops_at_two_failures_and_preserves_prior():
    from experiments.skill_crystallization_dev import WorldTrial
    from experiments.skill_crystallization_revision_dev import failures

    candidate, _ = _candidate_and_training()
    prior = [{"source_session": "prior", "outcome_success": True}]
    trials = [WorldTrial("ice", 2.3, (0.01,) * 5, f"s{i}") for i in range(3)]
    rows = failures(candidate, trials, prior)
    assert rows[0] == prior[0]
    assert [x["source_session"] for x in rows[1:]] == ["s0", "s1"]
    assert not any(x["outcome_success"] for x in rows[-2:])
    assert len(prior) == 1


def test_malformed_model_json_is_preserved(monkeypatch):
    from experiments.skill_crystallization_dev import ModelCallFailure

    class Response:
        status = 200

        def __enter__(self):
            return self

        def __exit__(self, *_):
            return False

        def read(self):
            return b'{"choices":[{"finish_reason":"stop","message":{"content":"{"}}]}'

    monkeypatch.setattr(urllib.request, "urlopen", lambda *a, **k: Response())
    with pytest.raises(ModelCallFailure) as caught:
        gemma_l2([], endpoint="http://localhost:8000/v1/chat/completions", model="x", timeout=2)
    assert caught.value.record["response_raw"]
