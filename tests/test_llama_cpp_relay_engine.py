import json
import urllib.error
from unittest.mock import patch

import pytest

from adapters.llama_cpp.relay_engine import (
    LlamaCppProviderError,
    LlamaCppProviderProtocolError,
    LlamaCppRelayProvider,
    parse_llama_cpp_decision,
    render_llama_cpp_request,
)
from relay_self.provenance import Provenance
from relay_self.relay_engine import (
    BoundedChoice,
    BoundedChoiceRequest,
    CognitionDatum,
    CognitionMode,
    DecisionStatus,
    RelayEngine,
)


def provenance(reference: str) -> Provenance:
    return Provenance(source="llama-cpp-provider-test", reference=reference)


def bounded_request() -> BoundedChoiceRequest:
    return BoundedChoiceRequest(
        request_id="flee-destination",
        instruction="Choose the safer reachable destination.",
        intent_id="intent-safe",
        focus="FLEE",
        choices=(
            BoundedChoice("cave", "Sheltered cave"),
            BoundedChoice("ridge", "Exposed ridge"),
        ),
        context=(
            CognitionDatum.from_value(
                "health",
                8,
                provenance("health"),
            ),
            CognitionDatum.from_value(
                "is_day",
                False,
                provenance("time"),
            ),
        ),
    )


class FakeResponse:
    def __init__(self, body: dict[str, object]) -> None:
        self._payload = json.dumps(body).encode("utf-8")

    def __enter__(self):
        return self

    def __exit__(self, *_args) -> None:
        return None

    def read(self) -> bytes:
        return self._payload


def chat_response(
    content: str,
    *,
    usage: dict[str, int] | None = None,
    finish_reason: str | None = "stop",
) -> dict[str, object]:
    body: dict[str, object] = {
        "choices": [
            {
                "message": {
                    "content": content,
                },
                "finish_reason": finish_reason,
            }
        ]
    }
    if usage is not None:
        body["usage"] = usage
    return body


def test_bounded_request_preserves_finite_choices_and_provenance() -> None:
    payload = render_llama_cpp_request(
        bounded_request(),
        mode=CognitionMode.BOUNDED,
        model="gemma-local",
    )

    assert payload["model"] == "gemma-local"
    assert payload["temperature"] == 0
    assert payload["max_tokens"] == 48
    assert payload["reasoning_effort"] == "none"
    assert payload["cache_prompt"] is False

    user = json.loads(payload["messages"][1]["content"])
    assert user["request_id"] == "flee-destination"
    assert user["intent_id"] == "intent-safe"
    assert user["focus"] == "FLEE"
    assert user["choices"] == [
        {"choice_id": "cave", "description": "Sheltered cave"},
        {"choice_id": "ridge", "description": "Exposed ridge"},
    ]
    assert user["context"][0] == {
        "key": "health",
        "value": 8,
        "provenance": {
            "source": "llama-cpp-provider-test",
            "reference": "health",
        },
    }


def test_think_request_is_explicit_and_has_larger_budget() -> None:
    payload = render_llama_cpp_request(
        bounded_request(),
        mode=CognitionMode.THINK,
        model="gemma-local",
    )

    assert payload["max_tokens"] == 256
    assert payload["reasoning_effort"] == "none"
    assert "explicit THINK escalation" in payload["messages"][0]["content"]
    assert "rationale" in payload["messages"][0]["content"]


def test_bounded_parser_accepts_only_exact_schema() -> None:
    resolved = parse_llama_cpp_decision(
        '{"status":"resolved","choice_id":"cave"}',
        mode=CognitionMode.BOUNDED,
    )
    assert resolved.status is DecisionStatus.RESOLVED
    assert resolved.choice_id == "cave"

    unresolved = parse_llama_cpp_decision(
        '{"status":"unresolved","choice_id":null}',
        mode=CognitionMode.BOUNDED,
    )
    assert unresolved.status is DecisionStatus.UNRESOLVED
    assert unresolved.choice_id is None

    with pytest.raises(
        LlamaCppProviderProtocolError,
        match="schema mismatch",
    ):
        parse_llama_cpp_decision(
            '{"status":"resolved","choice_id":"cave","extra":1}',
            mode=CognitionMode.BOUNDED,
        )


def test_think_parser_requires_explicit_rationale_field() -> None:
    resolved = parse_llama_cpp_decision(
        '{"status":"resolved","choice_id":"cave","rationale":"night shelter"}',
        mode=CognitionMode.THINK,
    )
    assert resolved.status is DecisionStatus.RESOLVED
    assert resolved.choice_id == "cave"
    assert resolved.reason == "night shelter"

    with pytest.raises(
        LlamaCppProviderProtocolError,
        match="schema mismatch",
    ):
        parse_llama_cpp_decision(
            '{"status":"resolved","choice_id":"cave"}',
            mode=CognitionMode.THINK,
        )


def test_malformed_bounded_model_output_is_protocol_failure_not_think() -> None:
    with patch(
        "urllib.request.urlopen",
        return_value=FakeResponse(chat_response("not-json")),
    ) as call:
        provider = LlamaCppRelayProvider(
            endpoint="http://127.0.0.1:1234/v1/chat/completions",
            model="gemma-local",
            timeout=1.0,
        )
        with pytest.raises(
            LlamaCppProviderProtocolError,
            match="not valid JSON",
        ):
            RelayEngine(provider)(bounded_request())

    assert call.call_count == 1

def test_transport_failure_is_not_relabelled_as_cognitive_unresolved() -> None:
    with patch(
        "urllib.request.urlopen",
        side_effect=urllib.error.URLError("connection refused"),
    ) as call:
        provider = LlamaCppRelayProvider(
            endpoint="http://127.0.0.1:1234/v1/chat/completions",
            model="gemma-local",
            timeout=1.0,
        )
        with pytest.raises(LlamaCppProviderError, match="model call failed"):
            RelayEngine(provider)(bounded_request())

    assert call.call_count == 1


def test_response_shape_failure_is_provider_error_not_think_trigger() -> None:
    with patch(
        "urllib.request.urlopen",
        return_value=FakeResponse({"not_choices": []}),
    ) as call:
        provider = LlamaCppRelayProvider(
            endpoint="http://127.0.0.1:1234/v1/chat/completions",
            model="gemma-local",
            timeout=1.0,
        )
        with pytest.raises(LlamaCppProviderError, match="choices"):
            RelayEngine(provider)(bounded_request())

    assert call.call_count == 1


def test_provider_validates_endpoint_and_positive_timeout() -> None:
    with pytest.raises(ValueError, match="http"):
        LlamaCppRelayProvider(
            endpoint="file:///tmp/model",
            model="x",
        )
    with pytest.raises(ValueError, match="timeout"):
        LlamaCppRelayProvider(
            endpoint="http://127.0.0.1:1234/v1/chat/completions",
            model="x",
            timeout=0,
        )


def test_provider_preserves_usage_finish_reason_and_requested_limit() -> None:
    body = chat_response(
        '{"status":"resolved","choice_id":"cave"}',
        usage={
            "prompt_tokens": 123,
            "completion_tokens": 5,
            "total_tokens": 128,
        },
    )
    with patch(
        "urllib.request.urlopen",
        return_value=FakeResponse(body),
    ):
        result = RelayEngine(
            LlamaCppRelayProvider(
                endpoint="http://127.0.0.1:1234/v1/chat/completions",
                model="gemma-local",
                timeout=1.0,
            )
        )(bounded_request())

    facts = result.attempts[0].call_facts
    assert facts.requested_max_output_tokens == 48
    assert facts.prompt_tokens == 123
    assert facts.completion_tokens == 5
    assert facts.total_tokens == 128
    assert facts.finish_reason == "stop"
    assert result.observed_prompt_tokens == 123
    assert result.observed_completion_tokens == 5


def test_non_stop_finish_reason_is_protocol_failure() -> None:
    body = chat_response(
        '{"status":"resolved","choice_id":"cave"}',
        finish_reason="length",
    )
    with patch(
        "urllib.request.urlopen",
        return_value=FakeResponse(body),
    ) as call:
        provider = LlamaCppRelayProvider(
            endpoint="http://127.0.0.1:1234/v1/chat/completions",
            model="gemma-local",
            timeout=1.0,
        )
        with pytest.raises(
            LlamaCppProviderProtocolError,
            match="did not finish with stop",
        ):
            RelayEngine(provider)(bounded_request())

    assert call.call_count == 1
