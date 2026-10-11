"""B29 exact native-schema single-call protocol qualification: MOCK ONLY."""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from experiments.ac_b_b24_structural_transfer import StructuralWorld
from experiments.ac_b_b26_l2_trial import (
    prompt_messages,
    run_local_one_call,
    train_original_world,
)
from experiments.ac_b_b29_native_schema_trial import (
    COEFFICIENT_SCHEMA,
    MAX_TOKENS,
    REASONING_EFFORT,
    RESPONSE_FORMAT,
    SCHEMA_NAME,
    _canonical_digest,
    execute_b29_once,
    main,
)

NORMAL = tuple(int(i in (1, 2, 3, 4, 8)) for i in range(16))
# B28's historical fenced ANF content was NOT source-fit (6/11).
B28_OBSERVED = (0, 1, 1, 0, 1, 0, 0, 1, 0, 0, 0, 1, 0, 0, 0, 0)


class FakeHTTP:
    def __init__(self, data: dict[str, object]):
        self.body = json.dumps(data, separators=(",", ":")).encode()

    def __enter__(self):
        return self

    def __exit__(self, *_args):
        return None

    def read(self, _limit):
        return self.body


def fake_transport(monkeypatch, source: dict[str, object]):
    calls = []

    def no_network(req, timeout):
        calls.append((json.loads(req.data.decode()), timeout))
        return FakeHTTP(source)

    monkeypatch.setattr("experiments.ac_b_b26_l2_trial.urlopen", no_network)
    return calls


def envelope(
    content: str, *, finish_reason: str = "stop", reasoning: str | None = None,
    details: dict[str, object] | None = None,
) -> dict[str, object]:
    usage = {"prompt_tokens": 350, "completion_tokens": 85, "total_tokens": 435}
    if details is not None:
        usage["completion_tokens_details"] = details
    return {
        "id": "MOCK_NO_MODEL_CALL",
        "model": "B29_FAKE_CI_ONLY",
        "choices": [{
            "finish_reason": finish_reason,
            "message": {
                "role": "assistant", "content": content,
                "reasoning_content": reasoning,
            },
        }],
        "usage": usage,
        "system_fingerprint": "FAKE_NOT_PHYSICAL",
    }


def original_messages():
    world = StructuralWorld("b29-fake-original-world", twin=False)
    training = train_original_world(world)
    assert world.actions_executed == 16
    return prompt_messages(training)


def test_preregistered_schema_matches_code_and_relaylm_native_wire():
    manifest = json.loads(
        (Path(__file__).resolve().parents[1] /
         "experiments/ac_b_b29_manifest.json").read_text()
    )
    assert manifest["response_format"] == RESPONSE_FORMAT
    assert SCHEMA_NAME == "relay_self_b29_anf_coefficients_v1"
    assert RESPONSE_FORMAT == {
        "type": "json_schema",
        "json_schema": {
            "name": SCHEMA_NAME, "strict": True, "schema": COEFFICIENT_SCHEMA,
        },
    }
    assert COEFFICIENT_SCHEMA == {
        "type": "object",
        "properties": {"coefficients": {
            "type": "array", "items": {
                "type": "integer", "minimum": 0, "maximum": 1,
            }, "minItems": 16, "maxItems": 16,
        }},
        "required": ["coefficients"],
        "additionalProperties": False,
    }
    assert len(_canonical_digest(RESPONSE_FORMAT)) == 64
    assert MAX_TOKENS == 2048
    assert REASONING_EFFORT == "none"


def test_only_b29_new_top_level_response_format_diff_in_actual_wire(monkeypatch):
    calls = fake_transport(
        monkeypatch, envelope(json.dumps({"coefficients": list(NORMAL)}))
    )
    kw = {
        "endpoint": "http://127.0.0.1:1234/v1/chat/completions",
        "model": "B29_FAKE_CI_ONLY",
        "messages": original_messages(),
        "max_tokens": 2048,
        "timeout_seconds": 25,
        "reasoning_effort": "none",
    }
    run_local_one_call(**kw)
    run_local_one_call(**kw, response_format=RESPONSE_FORMAT)
    assert len(calls) == 2  # mocked network, 0 actual LLM calls
    b28, b29 = calls[0][0], calls[1][0]
    assert b28 == {
        "model": "B29_FAKE_CI_ONLY",
        "messages": kw["messages"],
        "temperature": 0,
        "max_tokens": 2048,
        "stream": False,
        "reasoning_effort": "none",
    }
    assert b29 == {**b28, "response_format": RESPONSE_FORMAT}
    assert "response_format" not in b28
    assert "chat_template_kwargs" not in b29


def test_one_mock_valid_native_schema_and_semantic_fit_reaches_world(monkeypatch, tmp_path):
    fixture = envelope(
        json.dumps({"coefficients": list(NORMAL)}),
        details={"reasoning_tokens": 0},
    )
    calls = fake_transport(monkeypatch, fixture)
    root = tmp_path / "b29-valid"
    outcome = execute_b29_once(
        endpoint="http://127.0.0.1:1234/v1/chat/completions",
        model="B29_FAKE_CI_ONLY", evidence_root=root,
    )
    assert len(calls) == 1
    wire = calls[0][0]
    assert wire["response_format"] == RESPONSE_FORMAT
    assert wire["reasoning_effort"] == "none"
    assert wire["max_tokens"] == 2048
    assert wire["messages"] == original_messages()
    assert outcome["classification"] == "B29_VALID_NATIVE_JSON_AND_SOURCE_FIT_EVALUATED"
    assert outcome["result_validity"] == "VALID_TRAINING_FIT"
    assert outcome["generation_requests_attempted"] == 1
    assert outcome["retries"] == 0
    assert outcome["heldout_action_attempts"] == 30
    assert outcome["evaluation_action_attempts"] == 94
    assert outcome["proposed_coefficients"] == list(NORMAL)
    assert outcome["thinking_off_check"]["reported_reasoning_token_count"] == "ZERO_REPORTED"
    assert outcome["B26_B27_B28_invalid_unchanged"]
    report = json.loads((root / "evaluation.json").read_text())
    assert report["total_independently_issued_offline_world_actions"] == 94
    assert report["worlds"]["NORMAL:LOCAL_L2_FROZEN_PROPOSAL"]["novel_first_correct"] == 5
    assert report["worlds"]["TWIN:LOCAL_L2_FROZEN_PROPOSAL"]["novel_first_correct"] == 0
    assert report["worlds"]["NORMAL:CHEAP_DEG2"]["novel_first_correct"] == 5
    assert report["worlds"]["TWIN:CHEAP_DEG2"]["novel_first_correct"] == 0
    original = json.loads((root / "request.json").read_text())
    assert original["response_format_sha256"] == _canonical_digest(RESPONSE_FORMAT)
    assert original["schema_sha256"] == _canonical_digest(COEFFICIENT_SCHEMA)
    assert len(json.loads(original["messages"][1]["content"])["observations"]) == 11
    assert json.loads((root / "response.raw.json").read_text()) == fixture
    assert json.loads((root / "terminal.json").read_text()) == outcome
    assert "response.raw.json" in (root / "SHA256SUMS").read_text()


def test_structurally_valid_b28_coefficients_still_fail_source_fit(
    monkeypatch, tmp_path
):
    # No rescue of historical B28; this is a separate TEST-ONLY injected vector.
    calls = fake_transport(
        monkeypatch, envelope(json.dumps({"coefficients": list(B28_OBSERVED)}))
    )
    root = tmp_path / "b29-semantic-invalid"
    outcome = execute_b29_once(
        endpoint="http://127.0.0.1:1234/v1/chat/completions",
        model="B29_FAKE_CI_ONLY", evidence_root=root,
    )
    assert len(calls) == 1
    assert outcome["classification"] == "B29_INVALID_SOURCE_SEMANTIC_FIT"
    assert outcome["result_validity"] == "INVALID"
    assert outcome["heldout_action_attempts"] == 0
    assert outcome["evaluation_action_attempts"] == 0
    assert outcome["failure_description"] == "proposed structure contradicts executed training"
    assert not (root / "evaluation.json").exists()
    assert (root / "response.raw.json").exists()


@pytest.mark.parametrize("reply,reason", [
    (
        envelope("```json\n" + json.dumps({"coefficients": list(NORMAL)}) + "\n```"),
        "B29_INVALID_NATIVE_OUTPUT_OR_RESPONSE",
    ),
    (envelope("", finish_reason="length"), "B29_INVALID_NATIVE_OUTPUT_OR_RESPONSE"),
    (envelope('{"coefficients":[]}', finish_reason="stop"), "B29_INVALID_NATIVE_OUTPUT_OR_RESPONSE"),
    (envelope(json.dumps({"coefficients": list(NORMAL)}), reasoning="unexpected thought"),
     "B29_INVALID_THINKING_OFF_UNQUALIFIED"),
    (envelope(json.dumps({"coefficients": list(NORMAL)}), details={"reasoning_tokens": 5}),
     "B29_INVALID_THINKING_OFF_UNQUALIFIED"),
])
def test_fail_closed_original_invalid_wire_unchanged(
    monkeypatch, tmp_path, reply, reason
):
    calls = fake_transport(monkeypatch, reply)
    root = tmp_path / "one"
    outcome = execute_b29_once(
        endpoint="http://127.0.0.1:1234/v1/chat/completions",
        model="B29_FAKE_CI_ONLY", evidence_root=root,
    )
    assert len(calls) == 1
    assert outcome["classification"] == reason
    assert outcome["result_validity"] == "INVALID"
    assert outcome["heldout_action_attempts"] == 0
    assert outcome["evaluation_action_attempts"] == 0
    assert json.loads((root / "response.raw.json").read_text()) == reply
    assert not (root / "evaluation.json").exists()
    assert (root / "terminal.json").exists()
    assert "response.raw.json" in (root / "SHA256SUMS").read_text()


def test_missing_thought_tokens_not_falsely_declared_zero(monkeypatch, tmp_path):
    calls = fake_transport(
        monkeypatch, envelope(json.dumps({"coefficients": list(NORMAL)}))
    )
    outcome = execute_b29_once(
        endpoint="http://127.0.0.1:1234/v1/chat/completions",
        model="B29_FAKE_CI_ONLY", evidence_root=tmp_path / "unknown-reasoning-usage",
    )
    assert len(calls) == 1
    assert outcome["thinking_off_check"]["reported_reasoning_token_count"] == "UNKNOWN_UNREPORTED"


def test_mock_transport_error_exactly_one_attempt_and_terminal(monkeypatch, tmp_path):
    calls = []

    def one_error(request, timeout):
        calls.append((request, timeout))
        raise OSError("MOCK_NO_SERVER")

    monkeypatch.setattr("experiments.ac_b_b26_l2_trial.urlopen", one_error)
    root = tmp_path / "error"
    outcome = execute_b29_once(
        endpoint="http://127.0.0.1:1234/v1/chat/completions",
        model="B29_FAKE_CI_ONLY", evidence_root=root,
    )
    assert len(calls) == 1
    assert outcome["classification"] == "B29_TRANSPORT_OR_PREFLIGHT_FAILURE"
    assert outcome["generation_requests_attempted"] == 1
    assert not (root / "response.raw.json").exists()
    assert (root / "terminal.json").exists()


def test_b29_not_automatically_executed_and_never_overwrites_prior_evidence(
    monkeypatch, tmp_path
):
    def must_not_infer(*_args, **_kwargs):
        raise AssertionError("model inference must never occur in CI/default CLI")

    monkeypatch.setattr("experiments.ac_b_b26_l2_trial.urlopen", must_not_infer)
    with pytest.raises(SystemExit) as ex:
        main([])
    assert ex.value.code == 2
    with pytest.raises(SystemExit) as ex:
        main(["--run-local-l2", "--model", "FAKE"])
    assert ex.value.code == 2
    existing = tmp_path / "prior"
    existing.mkdir()
    (existing / "old").write_text("keep unchanged")
    with pytest.raises(FileExistsError):
        execute_b29_once(
            endpoint="http://127.0.0.1:1234/v1/chat/completions",
            model="B29_FAKE_CI_ONLY", evidence_root=existing,
        )
    assert (existing / "old").read_text() == "keep unchanged"
