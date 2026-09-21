from __future__ import annotations

import json
from unittest.mock import patch

import pytest

from adapters.llama_cpp.relay_engine import (
    LlamaCppProviderProtocolError,
    LlamaCppRelayProvider,
    render_llama_cpp_bounded_state,
    render_llama_cpp_jev_request,
    render_llama_cpp_systemtwo_request,
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


class FakeResponse:
    def __init__(self, body: dict[str, object]) -> None:
        self._body = json.dumps(body).encode("utf-8")

    def __enter__(self) -> "FakeResponse":
        return self

    def __exit__(self, *args: object) -> bool:
        return False

    def read(self) -> bytes:
        return self._body


def bounded_request(*, think_allowed: bool = True) -> BoundedChoiceRequest:
    return BoundedChoiceRequest(
        request_id="jev-flee-1",
        instruction="Choose the safer reachable destination.",
        intent_id="intent-reach-safety",
        focus="FLEE",
        choices=(
            BoundedChoice(choice_id="cave", description="Reachable cave shelter"),
            BoundedChoice(choice_id="ridge", description="Exposed ridge"),
        ),
        context=(
            CognitionDatum.from_value(
                "threat_nearby",
                True,
                Provenance(source="fixture.world", reference="rev:1:threat"),
            ),
            CognitionDatum.from_value(
                "route_open:cave",
                True,
                Provenance(source="fixture.world", reference="rev:1:route:cave"),
            ),
        ),
        think_allowed=think_allowed,
    )


def jev_response(
    choice: str,
    *,
    input_tokens: int = 123,
    output_tokens: int = 0,
) -> dict[str, object]:
    return {
        "model": "gemma-local",
        "answers": {
            "decision": {
                "type": "choice",
                "choice": choice,
                "probabilities": {
                    "cave": 0.8,
                    "ridge": 0.1,
                    "__relay_self_unresolved__": 0.1,
                },
                "confidence": 0.6,
            }
        },
        "usage": {
            "input_tokens": input_tokens,
            "output_tokens": output_tokens,
        },
    }


def think_response(choice: str) -> dict[str, object]:
    content = json.dumps(
        {
            "status": "resolved",
            "choice_id": choice,
            "rationale": "The broader bounded reconsideration supports this option.",
        },
        separators=(",", ":"),
    )
    return {
        "choices": [
            {
                "message": {"content": content},
                "finish_reason": "stop",
            }
        ],
        "usage": {
            "prompt_tokens": 150,
            "completion_tokens": 18,
            "total_tokens": 168,
        },
    }


def test_render_jev_request_preserves_bounded_state_and_explicit_unresolved() -> None:
    body = render_llama_cpp_jev_request(
        bounded_request(),
        model="gemma-local",
    )

    assert body["model"] == "gemma-local"
    assert body["state"] == {
        "request_id": "jev-flee-1",
        "intent_id": "intent-reach-safety",
        "focus": "FLEE",
        "context": [
            {
                "key": "threat_nearby",
                "value": True,
                "provenance": {
                    "source": "fixture.world",
                    "reference": "rev:1:threat",
                },
            },
            {
                "key": "route_open:cave",
                "value": True,
                "provenance": {
                    "source": "fixture.world",
                    "reference": "rev:1:route:cave",
                },
            },
        ],
    }
    decision = body["questions"]["decision"]
    assert decision["type"] == "choice"
    assert decision["instructions"] == "Choose the safer reachable destination."
    assert decision["criteria"]["cave"] == "Reachable cave shelter"
    assert decision["criteria"]["ridge"] == "Exposed ridge"
    assert "__relay_self_unresolved__" in decision["criteria"]


def test_systemtwo_candidate_shares_state_and_preserves_closed_answer_space() -> None:
    request = bounded_request()
    state = render_llama_cpp_bounded_state(request)
    systemone = render_llama_cpp_jev_request(
        request,
        model="gemma-local",
    )
    systemtwo = render_llama_cpp_systemtwo_request(
        request,
        model="gemma-local",
    )

    assert systemone["state"] == state
    assert systemtwo["model"] == "gemma-local"
    assert systemtwo["temperature"] == 0
    assert systemtwo["max_tokens"] == 256
    assert systemtwo["reasoning_effort"] == "none"
    assert systemtwo["cache_prompt"] is False

    messages = systemtwo["messages"]
    assert len(messages) == 1
    assert messages[0]["role"] == "user"

    state_prefix = (
        "Context:\n"
        + json.dumps(
            state,
            ensure_ascii=False,
            sort_keys=True,
            indent=2,
        )
        + "\n\n"
    )
    user = messages[0]["content"]
    assert user.startswith(state_prefix)
    assert "Question: Choose the safer reachable destination." in user
    assert "cave: Reachable cave shelter" in user
    assert "ridge: Exposed ridge" in user
    assert "__relay_self_unresolved__" not in user

    schema = systemtwo["response_format"]["json_schema"]["schema"]
    assert schema["required"] == ["status", "choice_id", "rationale"]
    assert schema["properties"]["choice_id"]["anyOf"] == [
        {"type": "string", "enum": ["cave", "ridge"]},
        {"type": "null"},
    ]


def test_systemtwo_candidate_does_not_mutate_current_systemone_request_shape() -> None:
    request = bounded_request()
    body = render_llama_cpp_jev_request(
        request,
        model="gemma-local",
    )

    assert body == {
        "model": "gemma-local",
        "state": {
            "request_id": "jev-flee-1",
            "intent_id": "intent-reach-safety",
            "focus": "FLEE",
            "context": [
                {
                    "key": "threat_nearby",
                    "value": True,
                    "provenance": {
                        "source": "fixture.world",
                        "reference": "rev:1:threat",
                    },
                },
                {
                    "key": "route_open:cave",
                    "value": True,
                    "provenance": {
                        "source": "fixture.world",
                        "reference": "rev:1:route:cave",
                    },
                },
            ],
        },
        "questions": {
            "decision": {
                "type": "choice",
                "instructions": "Choose the safer reachable destination.",
                "criteria": {
                    "cave": "Reachable cave shelter",
                    "ridge": "Exposed ridge",
                    "__relay_self_unresolved__": (
                        "The supplied transient context is insufficient or "
                        "contradictory for choosing any admissible option."
                    ),
                },
            }
        },
    }


def test_jev_bounded_resolves_without_chat_generation() -> None:
    with patch(
        "urllib.request.urlopen",
        return_value=FakeResponse(jev_response("cave", input_tokens=441)),
    ) as call:
        result = RelayEngine(
            LlamaCppRelayProvider(
                endpoint="http://127.0.0.1:8080/v1/chat/completions",
                systemone_endpoint="http://127.0.0.1:8080/v1/systemone",
                model="gemma-local",
                timeout=1.0,
            )
        )(bounded_request())

    assert call.call_count == 1
    assert call.call_args.args[0].full_url == "http://127.0.0.1:8080/v1/systemone"
    assert result.status is DecisionStatus.RESOLVED
    assert result.choice_id == "cave"
    assert result.escalated is False
    assert len(result.attempts) == 1
    assert result.attempts[0].mode is CognitionMode.BOUNDED
    assert result.attempts[0].call_facts.requested_max_output_tokens is None
    assert result.attempts[0].call_facts.prompt_tokens == 441
    assert result.attempts[0].call_facts.completion_tokens == 0
    assert result.attempts[0].call_facts.total_tokens == 441
    assert result.attempts[0].call_facts.finish_reason is None


def test_jev_unresolved_uses_existing_explicit_think_escalation() -> None:
    with patch(
        "urllib.request.urlopen",
        side_effect=[
            FakeResponse(jev_response("__relay_self_unresolved__", input_tokens=440)),
            FakeResponse(think_response("ridge")),
        ],
    ) as call:
        result = RelayEngine(
            LlamaCppRelayProvider(
                endpoint="http://127.0.0.1:8080/v1/chat/completions",
                systemone_endpoint="http://127.0.0.1:8080/v1/systemone",
                model="gemma-local",
                timeout=1.0,
            )
        )(bounded_request())

    assert call.call_count == 2
    assert call.call_args_list[0].args[0].full_url == (
        "http://127.0.0.1:8080/v1/systemone"
    )
    assert call.call_args_list[1].args[0].full_url == (
        "http://127.0.0.1:8080/v1/chat/completions"
    )
    active_think_body = json.loads(
        call.call_args_list[1].args[0].data.decode("utf-8")
    )
    assert active_think_body["messages"][0]["role"] == "system"
    assert "explicit THINK escalation" in active_think_body["messages"][0]["content"]
    assert result.status is DecisionStatus.RESOLVED
    assert result.choice_id == "ridge"
    assert result.escalated is True
    assert [attempt.mode for attempt in result.attempts] == [
        CognitionMode.BOUNDED,
        CognitionMode.THINK,
    ]
    assert result.attempts[0].reason == "jev_model_unresolved"


def test_jev_inadmissible_choice_is_protocol_failure_without_fallback() -> None:
    with patch(
        "urllib.request.urlopen",
        return_value=FakeResponse(jev_response("ocean")),
    ) as call:
        provider = LlamaCppRelayProvider(
            endpoint="http://127.0.0.1:8080/v1/chat/completions",
            systemone_endpoint="http://127.0.0.1:8080/v1/systemone",
            model="gemma-local",
            timeout=1.0,
        )
        with pytest.raises(
            LlamaCppProviderProtocolError,
            match="inadmissible choice_id",
        ):
            RelayEngine(provider)(bounded_request())

    assert call.call_count == 1


def test_jev_nonzero_output_tokens_is_protocol_failure() -> None:
    with patch(
        "urllib.request.urlopen",
        return_value=FakeResponse(
            jev_response("cave", output_tokens=1)
        ),
    ) as call:
        provider = LlamaCppRelayProvider(
            endpoint="http://127.0.0.1:8080/v1/chat/completions",
            systemone_endpoint="http://127.0.0.1:8080/v1/systemone",
            model="gemma-local",
            timeout=1.0,
        )
        with pytest.raises(
            LlamaCppProviderProtocolError,
            match="must not generate output tokens",
        ):
            RelayEngine(provider)(bounded_request())

    assert call.call_count == 1
