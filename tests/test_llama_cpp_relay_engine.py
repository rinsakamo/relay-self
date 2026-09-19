import json
import urllib.error
from unittest.mock import patch

import pytest

from adapters.llama_cpp.relay_engine import (
    LlamaCppProviderError,
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


def chat_response(content: str) -> dict[str, object]:
    return {
        "choices": [
            {
                "message": {
                    "content": content,
                }
            }
        ]
    }


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

    malformed = parse_llama_cpp_decision(
        '{"status":"resolved","choice_id":"cave","extra":1}',
        mode=CognitionMode.BOUNDED,
    )
    assert malformed.status is DecisionStatus.UNRESOLVED
    assert "schema" in malformed.reason


def test_think_parser_requires_explicit_rationale_field() -> None:
    resolved = parse_llama_cpp_decision(
        '{"status":"resolved","choice_id":"cave","rationale":"night shelter"}',
        mode=CognitionMode.THINK,
    )
    assert resolved.status is DecisionStatus.RESOLVED
    assert resolved.choice_id == "cave"
    assert resolved.reason == "night shelter"

    malformed = parse_llama_cpp_decision(
        '{"status":"resolved","choice_id":"cave"}',
        mode=CognitionMode.THINK,
    )
    assert malformed.status is DecisionStatus.UNRESOLVED
    assert "schema" in malformed.reason


def test_malformed_bounded_model_output_explicitly_escalates_to_think() -> None:
    responses = iter(
        [
            FakeResponse(chat_response("not-json")),
            FakeResponse(
                chat_response(
                    '{"status":"resolved","choice_id":"cave",'
                    '"rationale":"reconsidered carefully"}'
                )
            ),
        ]
    )

    with patch(
        "urllib.request.urlopen",
        side_effect=lambda *_args, **_kwargs: next(responses),
    ) as call:
        provider = LlamaCppRelayProvider(
            endpoint="http://127.0.0.1:1234/v1/chat/completions",
            model="gemma-local",
            timeout=1.0,
        )
        result = RelayEngine(provider)(bounded_request())

    assert result.status is DecisionStatus.RESOLVED
    assert result.choice_id == "cave"
    assert result.escalated is True
    assert [attempt.mode for attempt in result.attempts] == [
        CognitionMode.BOUNDED,
        CognitionMode.THINK,
    ]
    assert call.call_count == 2


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
