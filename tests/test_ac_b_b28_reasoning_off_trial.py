"""B28: MOCKED ONLY, no actual llama.cpp/GPU/LLM inference in CI."""
from __future__ import annotations

import json

import pytest

from experiments.ac_b_b24_structural_transfer import StructuralWorld
from experiments.ac_b_b26_l2_trial import (
    InvalidB26Proposal,
    prompt_messages,
    run_local_one_call,
    train_original_world,
)
from experiments.ac_b_b28_reasoning_off_trial import (
    MAX_TOKENS,
    REASONING_EFFORT,
    _check_no_thinking_from_original_wire,
    execute_b28_once,
    main,
)

NORMAL = tuple(int(x in (1, 2, 3, 4, 8)) for x in range(16))


class MockHTTPResponse:
    def __init__(self, data: dict[str, object]) -> None:
        self.raw = json.dumps(data, separators=(",", ":")).encode()

    def __enter__(self):
        return self

    def __exit__(self, *_args):
        return None

    def read(self, _max_bytes):
        return self.raw


def mocked(monkeypatch, response):
    calls = []

    def fake(request, timeout):
        calls.append((json.loads(request.data.decode()), timeout))
        return MockHTTPResponse(response)

    monkeypatch.setattr("experiments.ac_b_b26_l2_trial.urlopen", fake)
    return calls


def response(
    content: str,
    *,
    finish_reason: str = "stop",
    reasoning_content=None,
    reasoning_tokens=0,
    usage_details: bool = True,
    reasoning=None,
):
    usage = {"prompt_tokens": 336, "completion_tokens": 100, "total_tokens": 436}
    if usage_details:
        usage["completion_tokens_details"] = {"reasoning_tokens": reasoning_tokens}
    return {
        "id": "MOCK_B28_NOT_A_REAL_MODEL",
        "model": "MOCK_NO_PHYSICAL_LLM",
        "choices": [{
            "finish_reason": finish_reason,
            "message": {
                "role": "assistant",
                "content": content,
                "reasoning_content": reasoning_content,
                "reasoning": reasoning,
            },
        }],
        "usage": usage,
        "system_fingerprint": "MOCKED-NOT-ATTESTED",
    }


def src_messages():
    world = StructuralWorld("b28-test-prompt-only", twin=False)
    original = train_original_world(world)
    assert world.actions_executed == 16
    return prompt_messages(original)


def test_b28_diff_is_exactly_top_level_reasoning_effort_none(monkeypatch):
    result = response(json.dumps({"coefficients": list(NORMAL)}))
    calls = mocked(monkeypatch, result)
    options = {
        "endpoint": "http://127.0.0.1:1234/v1/chat/completions",
        "model": "MOCK_NO_PHYSICAL_LLM",
        "messages": src_messages(),
        "max_tokens": 2048,
        "timeout_seconds": 30,
    }
    # All three calls are intercepted by mock. Real CI model calls == 0.
    run_local_one_call(**options)
    run_local_one_call(**options, reasoning_effort="none")
    assert len(calls) == 2
    b27, b28 = calls[0][0], calls[1][0]
    assert MAX_TOKENS == 2048 and REASONING_EFFORT == "none"
    assert b27 == {
        "model": "MOCK_NO_PHYSICAL_LLM",
        "messages": options["messages"],
        "temperature": 0,
        "max_tokens": 2048,
        "stream": False,
    }
    assert b28 == {**b27, "reasoning_effort": "none"}
    assert "chat_template_kwargs" not in b28
    assert "reasoning_format" not in b28
    assert "reasoning" not in b28


def test_b28_valid_non_thinking_source_fit_and_original_world_actions(monkeypatch, tmp_path):
    calls = mocked(monkeypatch, response(json.dumps({"coefficients": list(NORMAL)})))
    root = tmp_path / "b28-valid"
    report = execute_b28_once(
        endpoint="http://127.0.0.1:1234/v1/chat/completions",
        model="MOCK_NO_PHYSICAL_LLM",
        evidence_root=root,
    )
    assert len(calls) == 1
    assert calls[0][0]["reasoning_effort"] == "none"
    assert report["classification"] == "B28_VALID_NONTHINKING_STRUCTURE_EVALUATED"
    assert report["result_validity"] == "VALID_TRAINING_FIT"
    assert report["generation_requests_attempted"] == 1
    assert report["heldout_action_attempts"] == 30
    assert report["evaluation_action_attempts"] == 94
    assert report["thinking_off_check"]["reported_reasoning_token_count"] == "ZERO_REPORTED"
    assert report["thinking_off_check"]["reasoning_text_empty"]
    assert report["proposed_coefficients"] == list(NORMAL)
    assert report["B26_B27_invalid_unchanged"]
    evidence = json.loads((root / "evaluation.json").read_text())
    assert evidence["worlds"]["NORMAL:LOCAL_L2_FROZEN_PROPOSAL"][
        "novel_first_correct"
    ] == 5
    assert evidence["worlds"]["TWIN:LOCAL_L2_FROZEN_PROPOSAL"][
        "novel_first_correct"
    ] == 0
    assert evidence["model_call_was_performed_by_this_evaluator"] is False
    request = json.loads((root / "request.json").read_text())
    assert request["reasoning_effort"] == "none"
    assert request["max_tokens"] == 2048
    assert request["temperature"] == 0
    assert request["stream"] is False
    assert len(json.loads(request["messages"][1]["content"])["observations"]) == 11
    assert json.loads((root / "response.raw.json").read_text()) == response(
        json.dumps({"coefficients": list(NORMAL)})
    )
    assert "response.raw.json" in (root / "SHA256SUMS").read_text()


@pytest.mark.parametrize("bad_response,expected", [
    (
        response("", finish_reason="length", reasoning_content="still thinking"),
        "B28_INVALID_REASONING_OFF_NOT_EFFECTIVE",
    ),
    (
        response(json.dumps({"coefficients": list(NORMAL)}), reasoning_content="thoughts"),
        "B28_INVALID_REASONING_OFF_NOT_EFFECTIVE",
    ),
    (
        response(json.dumps({"coefficients": list(NORMAL)}), reasoning_tokens=8),
        "B28_INVALID_REASONING_OFF_NOT_EFFECTIVE",
    ),
    (
        response("invalid-json"),
        "B28_INVALID_OUTPUT_OR_TRAINING_FIT",
    ),
    (
        response('{"coefficients":[]}', finish_reason="stop"),
        "B28_INVALID_OUTPUT_OR_TRAINING_FIT",
    ),
    (
        response("", finish_reason="stop"),
        "B28_INVALID_OUTPUT_OR_TRAINING_FIT",
    ),
])
def test_b28_invalid_never_issues_heldout_and_retains_original_http(
    monkeypatch, tmp_path, bad_response, expected
):
    calls = mocked(monkeypatch, bad_response)
    root = tmp_path / "invalid"
    report = execute_b28_once(
        endpoint="http://127.0.0.1:1234/v1/chat/completions",
        model="MOCK_NO_PHYSICAL_LLM",
        evidence_root=root,
    )
    assert len(calls) == 1
    assert report["classification"] == expected
    assert report["result_validity"] == "INVALID"
    assert report["heldout_action_attempts"] == 0
    assert report["evaluation_action_attempts"] == 0
    assert report["generation_requests_attempted"] == 1
    assert not (root / "evaluation.json").exists()
    assert json.loads((root / "response.raw.json").read_text()) == bad_response
    assert json.loads((root / "terminal.json").read_text()) == report
    assert "response.raw.json" in (root / "SHA256SUMS").read_text()


def test_response_without_reasoning_token_details_is_not_falsely_zero(
    monkeypatch, tmp_path
):
    calls = mocked(
        monkeypatch,
        response(json.dumps({"coefficients": list(NORMAL)}), usage_details=False),
    )
    root = tmp_path / "unknown-usage"
    terminal = execute_b28_once(
        endpoint="http://127.0.0.1:1234/v1/chat/completions",
        model="MOCK_NO_PHYSICAL_LLM",
        evidence_root=root,
    )
    assert len(calls) == 1
    assert terminal["result_validity"] == "VALID_TRAINING_FIT"
    assert (
        terminal["thinking_off_check"]["reported_reasoning_token_count"]
        == "UNKNOWN_UNREPORTED"
    )


def test_effective_reasoning_check_rejects_non_stop_even_if_json_is_valid(tmp_path):
    path = tmp_path / "bad-finish.json"
    path.write_text(json.dumps(response(
        json.dumps({"coefficients": list(NORMAL)}), finish_reason="length"
    )))
    with pytest.raises(InvalidB26Proposal, match="finish with stop"):
        _check_no_thinking_from_original_wire(path)


def test_reasoning_off_rejects_unsupported_values_without_llm_call(monkeypatch):
    def forbidden(*_args, **_kwargs):
        raise AssertionError("unsupported thinking control reached transport")
    monkeypatch.setattr("experiments.ac_b_b26_l2_trial.urlopen", forbidden)
    for attempt in ("off", "low", "high", True, 0):
        with pytest.raises(InvalidB26Proposal, match="reasoning_effort"):
            run_local_one_call(
                endpoint="http://127.0.0.1:1234/v1/chat/completions",
                model="FAKE",
                messages=src_messages(),
                max_tokens=2048,
                reasoning_effort=attempt,
            )


def test_transport_failure_terminal_is_original_and_one_attempt(monkeypatch, tmp_path):
    calls = []
    def fail(request, timeout):
        calls.append((request, timeout))
        raise OSError("MOCK_ONLY_SERVER_DOWN")
    monkeypatch.setattr("experiments.ac_b_b26_l2_trial.urlopen", fail)
    root = tmp_path / "failure"
    terminal = execute_b28_once(
        endpoint="http://127.0.0.1:1234/v1/chat/completions",
        model="MOCK_NO_PHYSICAL_LLM",
        evidence_root=root,
    )
    assert len(calls) == 1
    assert terminal["classification"] == "B28_TRANSPORT_OR_PREFLIGHT_FAILURE"
    assert terminal["result_validity"] == "INVALID"
    assert not (root / "response.raw.json").exists()
    assert (root / "terminal.json").exists()
    assert (root / "SHA256SUMS").exists()


def test_existing_evidence_dir_and_nonexplicit_cli_never_calls_model(
    monkeypatch, tmp_path
):
    def forbidden(*_args, **_kwargs):
        raise AssertionError("not an authorized actual L2 call")
    monkeypatch.setattr("experiments.ac_b_b26_l2_trial.urlopen", forbidden)
    with pytest.raises(SystemExit) as e:
        main([])
    assert e.value.code == 2
    with pytest.raises(SystemExit) as e:
        main(["--run-local-l2", "--model", "FAKE"])
    assert e.value.code == 2
    existing = tmp_path / "prior"
    existing.mkdir()
    with pytest.raises(FileExistsError):
        execute_b28_once(
            endpoint="http://127.0.0.1:1234/v1/chat/completions",
            model="MOCK_NO_PHYSICAL_LLM",
            evidence_root=existing,
        )
