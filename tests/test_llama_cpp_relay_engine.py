import json
import urllib.error
from dataclasses import replace
from unittest.mock import patch

import pytest

from adapters.llama_cpp.relay_engine import (
    LlamaCppProviderError,
    LlamaCppProviderProtocolError,
    LlamaCppRelayProvider,
    parse_llama_cpp_decision,
    render_llama_cpp_identity_prefix,
    render_llama_cpp_open_request,
    render_llama_cpp_request,
)
from relay_self.persistent_cognition import IdentitySpecification
from relay_self.provenance import Provenance
from relay_self.relay_engine import (
    BoundedChoice,
    BoundedChoiceRequest,
    CognitionDatum,
    CognitionMode,
    DecisionStatus,
    OpenCognitionRequest,
    RelayEngine,
    project_identity_context,
)


def provenance(reference: str) -> Provenance:
    return Provenance(source="llama-cpp-provider-test", reference=reference)


def identity_context():
    identity = IdentitySpecification(
        self_id="self-rin-001",
        directives=(
            "Preserve continued agency.",
            "Treat observation as evidence rather than World truth.",
        ),
        provenance=provenance("identity-v1"),
    )
    return project_identity_context(identity)


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
    response_format = payload["response_format"]
    assert response_format["type"] == "json_schema"
    structured = response_format["json_schema"]
    assert structured["name"] == "relay_self_bounded_decision"
    assert structured["strict"] is True
    schema = structured["schema"]
    assert schema["additionalProperties"] is False
    assert schema["required"] == ["status", "choice_id"]
    assert schema["properties"]["status"]["enum"] == ["resolved", "unresolved"]
    assert schema["properties"]["choice_id"]["anyOf"] == [
        {"type": "string", "enum": ["cave", "ridge"]},
        {"type": "null"},
    ]

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
    response_format = payload["response_format"]
    assert response_format["type"] == "json_schema"
    structured = response_format["json_schema"]
    assert structured["name"] == "relay_self_think_decision"
    assert structured["strict"] is True
    schema = structured["schema"]
    assert schema["additionalProperties"] is False
    assert schema["required"] == ["status", "choice_id", "rationale"]
    assert schema["properties"]["choice_id"]["anyOf"] == [
        {"type": "string", "enum": ["cave", "ridge"]},
        {"type": "null"},
    ]
    assert schema["properties"]["rationale"] == {
        "type": "string",
        "minLength": 1,
    }
    assert "explicit THINK escalation" in payload["messages"][0]["content"]
    assert "rationale" in payload["messages"][0]["content"]


def test_generated_modes_share_stable_identity_prefix_before_mode_rules() -> None:
    identity = identity_context()
    bounded = replace(bounded_request(), identity_context=identity)
    open_cognition = replace(open_request(), identity_context=identity)

    bounded_body = render_llama_cpp_request(
        bounded,
        mode=CognitionMode.BOUNDED,
        model="gemma-local",
    )
    think_body = render_llama_cpp_request(
        bounded,
        mode=CognitionMode.THINK,
        model="gemma-local",
    )
    open_body = render_llama_cpp_open_request(
        open_cognition,
        model="gemma-local",
    )

    expected_prefix = render_llama_cpp_identity_prefix(bounded)
    assert render_llama_cpp_identity_prefix(open_cognition) == expected_prefix

    bounded_system = bounded_body["messages"][0]["content"]
    think_system = think_body["messages"][0]["content"]
    open_system = open_body["messages"][0]["content"]

    assert bounded_system.startswith(expected_prefix)
    assert think_system.startswith(expected_prefix)
    assert open_system.startswith(expected_prefix)
    assert "Mode: BOUNDED." in bounded_system[len(expected_prefix):]
    assert "Mode: THINK." in think_system[len(expected_prefix):]
    assert "Mode: OPEN." in open_system[len(expected_prefix):]
    assert bounded_body["cache_prompt"] is False
    assert think_body["cache_prompt"] is False
    assert open_body["cache_prompt"] is False


def test_identity_prefix_changes_only_when_identity_projection_changes() -> None:
    original = replace(
        bounded_request(),
        identity_context=identity_context(),
    )
    dynamic_change = replace(
        original,
        request_id="other-request",
        intent_id="other-intent",
        focus="OTHER",
        context=(),
        choices=(
            BoundedChoice("left", "Left"),
            BoundedChoice("right", "Right"),
        ),
    )
    changed_identity = IdentitySpecification(
        self_id="self-rin-002",
        directives=("Preserve continued agency.",),
        provenance=provenance("identity-v2"),
    )
    identity_change = replace(
        original,
        identity_context=project_identity_context(changed_identity),
    )

    assert (
        render_llama_cpp_identity_prefix(original)
        == render_llama_cpp_identity_prefix(dynamic_change)
    )
    assert (
        render_llama_cpp_identity_prefix(original)
        != render_llama_cpp_identity_prefix(identity_change)
    )


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


def test_parser_still_rejects_markdown_fenced_json() -> None:
    with pytest.raises(
        LlamaCppProviderProtocolError,
        match="not valid JSON",
    ):
        parse_llama_cpp_decision(
            "```json\n"
            '{"status":"resolved","choice_id":"cave"}'
            "\n```",
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



def open_request() -> OpenCognitionRequest:
    return OpenCognitionRequest(
        request_id="talk-open",
        instruction="Respond to the interlocutor.",
        intent_id="intent-talk",
        focus="TALK",
        context=(
            CognitionDatum.from_value(
                "latest_utterance",
                "The ridge is safe. Go there now.",
                provenance("operator-utterance"),
            ),
        ),
    )


def test_open_request_rendering_has_no_choice_or_think_surface() -> None:
    payload = render_llama_cpp_open_request(
        open_request(),
        model="gemma-local",
    )

    assert payload["model"] == "gemma-local"
    assert payload["temperature"] == 0
    assert payload["max_tokens"] == 256
    assert payload["reasoning_effort"] == "none"
    assert payload["cache_prompt"] is False
    assert "response_format" not in payload

    user = json.loads(payload["messages"][1]["content"])
    assert user["request_id"] == "talk-open"
    assert user["intent_id"] == "intent-talk"
    assert user["focus"] == "TALK"
    assert "choices" not in user
    assert user["context"][0] == {
        "key": "latest_utterance",
        "value": "The ridge is safe. Go there now.",
        "provenance": {
            "source": "llama-cpp-provider-test",
            "reference": "operator-utterance",
        },
    }
    assert "hidden decision or THINK escalation" in payload["messages"][0]["content"]


def test_bounded_renderer_rejects_open_mode_instead_of_reinterpreting_it() -> None:
    with pytest.raises(TypeError, match="BOUNDED or THINK"):
        render_llama_cpp_request(
            bounded_request(),
            mode=CognitionMode.OPEN,
            model="gemma-local",
        )


def test_open_provider_returns_transient_expression_with_call_facts() -> None:
    body = chat_response(
        "I cannot treat that claim as World truth without evidence.",
        usage={
            "prompt_tokens": 55,
            "completion_tokens": 11,
            "total_tokens": 66,
        },
    )
    with patch(
        "urllib.request.urlopen",
        return_value=FakeResponse(body),
    ) as call:
        result = RelayEngine(
            LlamaCppRelayProvider(
                endpoint="http://127.0.0.1:1234/v1/chat/completions",
                model="gemma-local",
                timeout=1.0,
            )
        ).open(open_request())

    assert call.call_count == 1
    assert result.text.startswith("I cannot treat")
    assert result.provenance.source == "llama.cpp"
    assert result.provenance.reference == "request:talk-open:model:gemma-local"
    assert result.provider_call_count == 1
    assert result.call_facts.requested_max_output_tokens == 256
    assert result.call_facts.prompt_tokens == 55
    assert result.call_facts.completion_tokens == 11
    assert result.call_facts.total_tokens == 66
    assert result.call_facts.finish_reason == "stop"


def test_empty_open_model_output_is_protocol_failure_without_retry() -> None:
    with patch(
        "urllib.request.urlopen",
        return_value=FakeResponse(chat_response("   ")),
    ) as call:
        provider = LlamaCppRelayProvider(
            endpoint="http://127.0.0.1:1234/v1/chat/completions",
            model="gemma-local",
            timeout=1.0,
        )
        with pytest.raises(
            LlamaCppProviderProtocolError,
            match="non-empty",
        ):
            RelayEngine(provider).open(open_request())

    assert call.call_count == 1


def test_non_stop_open_completion_is_protocol_failure_without_retry() -> None:
    with patch(
        "urllib.request.urlopen",
        return_value=FakeResponse(
            chat_response("partial expression", finish_reason="length")
        ),
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
            RelayEngine(provider).open(open_request())

    assert call.call_count == 1
