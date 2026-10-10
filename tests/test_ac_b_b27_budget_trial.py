"""B27: MOCK ONLY. 2048 budget isolation and non-loss of INVALID raw HTTP.

No test in this file issues a real local L2 call or launches llama.cpp.
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from experiments.ac_b_b24_structural_transfer import StructuralWorld
from experiments.ac_b_b26_l2_trial import (
    InvalidB26Proposal,
    prompt_messages,
    run_local_one_call,
    train_original_world,
)
from experiments.ac_b_b27_budget_trial import (
    NEW_BUDGET,
    PREVIOUS_BUDGET,
    execute_b27_once,
    main,
)

NORMAL = tuple(int(x in (1, 2, 4, 8, 3)) for x in range(16))


class MockResponse:
    def __init__(self, reply: dict[str, object]) -> None:
        self.data = json.dumps(reply, separators=(",", ":")).encode("utf-8")

    def __enter__(self):
        return self

    def __exit__(self, *_args):
        return None

    def read(self, _limit):
        return self.data


def make_fake_transport(monkeypatch, reply: dict[str, object]):
    calls = []

    def simulated_response(request, timeout):
        calls.append((json.loads(request.data.decode("utf-8")), timeout))
        return MockResponse(reply)

    monkeypatch.setattr(
        "experiments.ac_b_b26_l2_trial.urlopen", simulated_response
    )
    return calls


def wire(content: str, *, finish: str = "stop", reasoning: str = ""):
    return {
        "id": "MOCKED-B27-NOT-A-REAL-MODEL-RESPONSE",
        "model": "FAKE_MOCK_MODEL",
        "choices": [{
            "finish_reason": finish,
            "message": {
                "role": "assistant",
                "content": content,
                "reasoning_content": reasoning,
            },
        }],
        "usage": {
            "prompt_tokens": 336, "completion_tokens": NEW_BUDGET,
            "total_tokens": 336 + NEW_BUDGET,
        },
        "system_fingerprint": "MOCKED_NOT_REAL",
    }


def request_canonical(messages, *, max_tokens):
    return {
        "model": "FAKE_MOCK_MODEL",
        "messages": messages,
        "temperature": 0,
        "max_tokens": max_tokens,
        "stream": False,
    }


def test_b26_legacy_request_exactly_same_except_frozen_b27_max_tokens(monkeypatch):
    original = train_original_world(
        StructuralWorld("b27-original-source-only", twin=False)
    )
    messages = prompt_messages(original)
    calls = make_fake_transport(
        monkeypatch, wire(json.dumps({"coefficients": list(NORMAL)}))
    )
    kw = {
        "endpoint": "http://127.0.0.1:1234/v1/chat/completions",
        "model": "FAKE_MOCK_MODEL",
        "messages": messages,
        "timeout_seconds": 30,
    }
    assert PREVIOUS_BUDGET == 512
    assert NEW_BUDGET == 2048
    run_local_one_call(**kw)
    run_local_one_call(**kw, max_tokens=NEW_BUDGET)
    assert len(calls) == 2  # only MOCKED requests, not physical inference
    legacy, revised = calls[0][0], calls[1][0]
    assert legacy == request_canonical(messages, max_tokens=512)
    assert revised == request_canonical(messages, max_tokens=2048)
    assert {k: v for k, v in legacy.items() if k != "max_tokens"} == {
        k: v for k, v in revised.items() if k != "max_tokens"
    }


def test_b27_2048_reasoning_only_length_invalid_retains_full_raw(monkeypatch, tmp_path):
    message = wire("", finish="length", reasoning="unfinished thoughts, not JSON")
    calls = make_fake_transport(monkeypatch, message)
    root = tmp_path / "b27-invalid"
    receipt = execute_b27_once(
        endpoint="http://127.0.0.1:1234/v1/chat/completions",
        model="FAKE_MOCK_MODEL",
        evidence_root=root,
    )
    assert len(calls) == 1 and calls[0][0]["max_tokens"] == 2048
    assert receipt["classification"] == "B27_INVALID_2048_EXHAUSTED_BEFORE_CONTENT"
    assert receipt["result_validity"] == "INVALID"
    assert receipt["generation_requests_attempted"] == 1
    assert receipt["heldout_actions"] == receipt["eval_world_actions"] == 0
    assert receipt["prompt_training_actions"] == 16
    assert receipt["wire_observation"]["finish_reason"] == "length"
    assert receipt["wire_observation"]["raw_content_length"] == 0
    assert receipt["wire_observation"]["reasoning_content_present"] is True
    assert receipt["wire_observation"]["usage"]["completion_tokens"] == 2048
    assert json.loads((root / "response.raw.json").read_text()) == message
    assert not (root / "evaluation.json").exists()
    assert json.loads((root / "terminal.json").read_text()) == receipt
    sums = (root / "SHA256SUMS").read_text()
    assert "response.raw.json" in sums and "terminal.json" in sums
    assert "request.json" in sums
    assert receipt["B26_512_trial"] == "INVALID_FIXED_UNCHANGED"
    assert receipt["wire_observation"]["reported_model"] == "FAKE_MOCK_MODEL"


def test_b27_valid_source_model_frozen_before_world_eval(monkeypatch, tmp_path):
    response = wire(json.dumps({"coefficients": list(NORMAL)}))
    calls = make_fake_transport(monkeypatch, response)
    root = tmp_path / "b27-valid"
    receipt = execute_b27_once(
        endpoint="http://127.0.0.1:1234/v1/chat/completions",
        model="FAKE_MOCK_MODEL",
        evidence_root=root,
    )
    assert len(calls) == 1
    assert receipt["classification"] == "B27_VALID_STRUCTURE_OFFLINE_WORLD_EVALUATED"
    assert receipt["result_validity"] == "VALID_TRAINING_FIT"
    assert receipt["heldout_actions"] == 30
    assert receipt["eval_world_actions"] == 94
    assert receipt["proposed_coefficients"] == list(NORMAL)
    result = json.loads((root / "evaluation.json").read_text())
    assert result["model_call_was_performed_by_this_evaluator"] is False
    assert result["worlds"]["NORMAL:LOCAL_L2_FROZEN_PROPOSAL"][
        "novel_first_correct"
    ] == 5
    assert result["worlds"]["TWIN:LOCAL_L2_FROZEN_PROPOSAL"][
        "novel_first_correct"
    ] == 0
    assert result["worlds"]["NORMAL:CHEAP_DEG2"]["novel_first_correct"] == 5
    assert result["worlds"]["TWIN:CHEAP_DEG2"]["novel_first_correct"] == 0
    assert result["total_independently_issued_offline_world_actions"] == 94
    assert (root / "response.raw.json").exists()
    assert (root / "request.json").exists()
    assert (root / "terminal.json").exists()
    request = json.loads((root / "request.json").read_text())
    assert request["max_tokens"] == 2048
    assert request["temperature"] == 0
    assert request["additional_reasoning_effort"] is None
    assert len(json.loads(request["messages"][1]["content"])["observations"]) == 11


@pytest.mark.parametrize("content", [
    "not json",
    '{"coefficients":[]}',
    '{"coefficients":[0],"coefficients":[1]}',
    json.dumps({"coefficients": [0] * 16}),  # source-inconsistent
])
def test_b27_invalid_proposals_still_get_wire_and_terminal(
    monkeypatch, tmp_path, content
):
    calls = make_fake_transport(monkeypatch, wire(content))
    root = tmp_path / ("invalid-" + str(len(content)))
    receipt = execute_b27_once(
        endpoint="http://127.0.0.1:1234/v1/chat/completions",
        model="FAKE_MOCK_MODEL",
        evidence_root=root,
    )
    assert len(calls) == 1
    assert receipt["result_validity"] == "INVALID"
    assert receipt["classification"] == "B27_INVALID_RESPONSE_OR_TRAINING_FIT"
    assert receipt["eval_world_actions"] == 0
    assert receipt["heldout_actions"] == 0
    assert receipt["wire_observation"]["raw_content_length"] == len(content)
    assert (root / "terminal.json").exists()
    assert (root / "response.raw.json").exists()
    assert not (root / "evaluation.json").exists()


def test_b27_transport_failure_is_single_attempt_and_persisted(monkeypatch, tmp_path):
    calls = []

    def fail_once(_request, _timeout):
        calls.append(1)
        raise OSError("MOCKED CONNECTION FAILURE")

    monkeypatch.setattr("experiments.ac_b_b26_l2_trial.urlopen", fail_once)
    root = tmp_path / "transport-failed"
    receipt = execute_b27_once(
        endpoint="http://127.0.0.1:1234/v1/chat/completions",
        model="FAKE_MOCK_MODEL",
        evidence_root=root,
    )
    assert len(calls) == 1
    assert receipt["classification"] == "B27_TRANSPORT_OR_PREFLIGHT_FAILURE"
    assert receipt["generation_requests_attempted"] == 1
    assert receipt["wire_observation"]["wire_response_received"] is False
    assert (root / "terminal.json").exists()
    assert not (root / "response.raw.json").exists()
    assert not (root / "evaluation.json").exists()


def test_b27_existing_evidence_path_must_not_overwrite_prior_trial(monkeypatch, tmp_path):
    root = tmp_path / "preexisting"
    root.mkdir()
    (root / "prior.txt").write_text("do not overwrite")
    def must_not_call(*_args, **_kw):
        raise AssertionError("no model call should happen on preexisting path")
    monkeypatch.setattr("experiments.ac_b_b26_l2_trial.urlopen", must_not_call)
    with pytest.raises(FileExistsError):
        execute_b27_once(
            endpoint="http://127.0.0.1:1234/v1/chat/completions",
            model="FAKE_MOCK_MODEL",
            evidence_root=root,
        )
    assert (root / "prior.txt").read_text() == "do not overwrite"


def test_no_real_model_access_on_import_or_default_cli(monkeypatch):
    def forbidden(*_args, **_kw):
        raise AssertionError("GitHub tests may not call native model")
    monkeypatch.setattr("experiments.ac_b_b26_l2_trial.urlopen", forbidden)
    with pytest.raises(SystemExit) as ex:
        main([])
    assert ex.value.code == 2
    with pytest.raises(SystemExit) as ex:
        main(["--run-local-l2", "--model", "FAKE_MOCK_MODEL"])
    assert ex.value.code == 2


@pytest.mark.parametrize("budget", [0, -1, 4097, True, "2048"])
def test_legacy_transport_refuses_unexpected_generation_budget(
    monkeypatch, budget: object
):
    def forbidden(*_args, **_kw):
        raise AssertionError("invalid preflight cannot reach real model")
    monkeypatch.setattr("experiments.ac_b_b26_l2_trial.urlopen", forbidden)
    with pytest.raises(InvalidB26Proposal, match="generation budget"):
        run_local_one_call(
            endpoint="http://127.0.0.1:1234/v1/chat/completions",
            model="FAKE_MOCK_MODEL",
            messages=[],
            max_tokens=budget,
        )


def test_wire_path_exclusive_even_in_legacy_shared_transport(monkeypatch, tmp_path):
    calls = make_fake_transport(monkeypatch, wire("irrelevant"))
    path: Path = tmp_path / "already-recorded.json"
    path.write_text("immutable old source")
    with pytest.raises(FileExistsError):
        run_local_one_call(
            endpoint="http://127.0.0.1:1234/v1/chat/completions",
            model="FAKE_MOCK_MODEL", messages=[],
            max_tokens=2048, raw_response_path=path,
        )
    assert len(calls) == 1
    assert path.read_text() == "immutable old source"
