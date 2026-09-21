from __future__ import annotations

import json
import urllib.error
import urllib.parse
import urllib.request
from typing import Any

from relay_self.provenance import Provenance
from relay_self.relay_engine import (
    BoundedChoiceRequest,
    CognitionMode,
    DecisionStatus,
    OpenCognitionRequest,
    ProviderCallFacts,
    ProviderDecision,
    ProviderExpression,
)

BOUNDED_MAX_TOKENS = 48
THINK_MAX_TOKENS = 256
OPEN_MAX_TOKENS = 256

_JEV_QUESTION_ID = "decision"
_JEV_UNRESOLVED_CHOICE = "__relay_self_unresolved__"

_COMMON_SYSTEM_PREFIX = (
    "You are a cognition provider for RelaySelf. "
    "The Identity Specification block below is transient model-facing input "
    "derived from durable Self authority. It does not establish World truth, "
    "authorize an Action, mutate Current Intent, or persist generated claims."
)

_BOUNDED_SYSTEM = (
    "Mode: BOUNDED. "
    "Use only the supplied transient context and finite choices. "
    "If one admissible choice is sufficiently justified, return exactly one JSON "
    "object with keys status and choice_id: "
    '{"status":"resolved","choice_id":"<id>"}. '
    "If the bounded surface is insufficient or contradictory, return exactly "
    '{"status":"unresolved","choice_id":null}. '
    "Do not add prose, markdown, or other keys."
)

_THINK_SYSTEM = (
    "Mode: THINK. This is an explicit THINK escalation after bounded cognition "
    "did not safely resolve. Reconsider interactions and constraints "
    "using only the supplied transient context and finite choices. "
    "Return exactly one JSON object with keys status, choice_id, and rationale. "
    'For resolution use {"status":"resolved","choice_id":"<id>",'
    '"rationale":"<brief reasoning>"}. '
    'If still insufficient use {"status":"unresolved","choice_id":null,'
    '"rationale":"<brief reason>"}. '
    "Do not add prose, markdown, or other keys."
)

_OPEN_SYSTEM = (
    "Mode: OPEN. "
    "Use only the supplied transient context to generate one expression. "
    "Return expression text only. The generated text is transient cognition: "
    "it does not itself establish World truth, mutate Current Intent, persist "
    "Memory, authorize an Action, or prove external delivery. "
    "Do not add a hidden decision or THINK escalation."
)


class LlamaCppProviderError(RuntimeError):
    """Raised when the local llama.cpp provider path fails operationally."""


class LlamaCppProviderProtocolError(LlamaCppProviderError):
    """Raised when provider/model output violates the declared wire contract."""


def _identity_payload(
    request: BoundedChoiceRequest | OpenCognitionRequest,
) -> dict[str, object] | None:
    identity = request.identity_context
    if identity is None:
        return None
    return {
        "key": identity.key,
        "value": json.loads(identity.value_json),
        "provenance": {
            "source": identity.provenance.source,
            "reference": identity.provenance.reference,
        },
    }


def render_llama_cpp_identity_prefix(
    request: BoundedChoiceRequest | OpenCognitionRequest,
) -> str:
    """Render the mode-independent leading system prefix for one identity."""

    if not isinstance(request, (BoundedChoiceRequest, OpenCognitionRequest)):
        raise TypeError(
            "request must be BoundedChoiceRequest or OpenCognitionRequest"
        )
    identity_text = json.dumps(
        _identity_payload(request),
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    )
    return (
        _COMMON_SYSTEM_PREFIX
        + "\nIdentity Specification:\n"
        + identity_text
        + "\n\n"
    )


def _system_message(
    request: BoundedChoiceRequest | OpenCognitionRequest,
    *,
    mode: CognitionMode,
) -> str:
    if mode is CognitionMode.BOUNDED:
        suffix = _BOUNDED_SYSTEM
    elif mode is CognitionMode.THINK:
        suffix = _THINK_SYSTEM
    elif mode is CognitionMode.OPEN:
        suffix = _OPEN_SYSTEM
    else:
        raise TypeError("unsupported cognition mode")
    return render_llama_cpp_identity_prefix(request) + suffix


def _decision_response_format(
    request: BoundedChoiceRequest,
    *,
    mode: CognitionMode,
) -> dict[str, object]:
    if mode not in {CognitionMode.BOUNDED, CognitionMode.THINK}:
        raise TypeError("decision response format requires BOUNDED or THINK")
    choice_ids = [choice.choice_id for choice in request.choices]
    properties: dict[str, object] = {
        "status": {
            "type": "string",
            "enum": [
                DecisionStatus.RESOLVED.value,
                DecisionStatus.UNRESOLVED.value,
            ],
        },
        "choice_id": {
            "anyOf": [
                {"type": "string", "enum": choice_ids},
                {"type": "null"},
            ]
        },
    }
    required = ["status", "choice_id"]
    schema_name = "relay_self_bounded_decision"

    if mode is CognitionMode.THINK:
        properties["rationale"] = {
            "type": "string",
            "minLength": 1,
        }
        required.append("rationale")
        schema_name = "relay_self_think_decision"

    return {
        "type": "json_schema",
        "json_schema": {
            "name": schema_name,
            "strict": True,
            "schema": {
                "type": "object",
                "properties": properties,
                "required": required,
                "additionalProperties": False,
            },
        },
    }


def render_llama_cpp_bounded_state(
    request: BoundedChoiceRequest,
) -> dict[str, object]:
    """Render the cognition state shared by bounded execution realizations."""

    if not isinstance(request, BoundedChoiceRequest):
        raise TypeError("request must be BoundedChoiceRequest")

    state: dict[str, object] = {
        "request_id": request.request_id,
        "intent_id": request.intent_id,
        "focus": request.focus,
        "context": [
            {
                "key": datum.key,
                "value": json.loads(datum.value_json),
                "provenance": {
                    "source": datum.provenance.source,
                    "reference": datum.provenance.reference,
                },
            }
            for datum in request.context
        ],
    }
    identity = _identity_payload(request)
    if identity is not None:
        state["identity_context"] = identity
    return state


def render_llama_cpp_request(
    request: BoundedChoiceRequest,
    *,
    mode: CognitionMode,
    model: str,
) -> dict[str, object]:
    if not isinstance(request, BoundedChoiceRequest):
        raise TypeError("request must be BoundedChoiceRequest")
    _require_text("model", model)
    if not isinstance(mode, CognitionMode):
        raise TypeError("mode must be CognitionMode")
    if mode not in {CognitionMode.BOUNDED, CognitionMode.THINK}:
        raise TypeError("bounded request mode must be BOUNDED or THINK")

    state = render_llama_cpp_bounded_state(request)
    dynamic_state = {
        key: value
        for key, value in state.items()
        if key != "identity_context"
    }
    payload = {
        **dynamic_state,
        "instruction": request.instruction,
        "choices": [
            {
                "choice_id": choice.choice_id,
                "description": choice.description,
            }
            for choice in request.choices
        ],
    }

    system = _system_message(request, mode=mode)
    max_tokens = (
        BOUNDED_MAX_TOKENS
        if mode is CognitionMode.BOUNDED
        else THINK_MAX_TOKENS
    )
    return {
        "model": model,
        "temperature": 0,
        "max_tokens": max_tokens,
        "reasoning_effort": "none",
        "cache_prompt": False,
        "response_format": _decision_response_format(request, mode=mode),
        "messages": [
            {"role": "system", "content": system},
            {
                "role": "user",
                "content": json.dumps(
                    payload,
                    ensure_ascii=False,
                    sort_keys=True,
                    separators=(",", ":"),
                ),
            },
        ],
    }


def render_llama_cpp_jev_request(
    request: BoundedChoiceRequest,
    *,
    model: str,
) -> dict[str, object]:
    """Render one explicit Jev/System One finite-choice request.

    This is an execution optimization for the existing BOUNDED contract. It
    does not add a new semantic owner or confidence policy. Cognitive
    insufficiency remains one explicit finite choice so RelayEngine can retain
    its existing BOUNDED -> THINK escalation semantics without a hidden
    threshold or fallback.
    """

    if not isinstance(request, BoundedChoiceRequest):
        raise TypeError("request must be BoundedChoiceRequest")
    _require_text("model", model)

    choice_ids = {choice.choice_id for choice in request.choices}
    if _JEV_UNRESOLVED_CHOICE in choice_ids:
        raise LlamaCppProviderProtocolError(
            "bounded choice_id collides with reserved Jev unresolved choice"
        )

    state = render_llama_cpp_bounded_state(request)
    criteria = {
        choice.choice_id: choice.description
        for choice in request.choices
    }
    criteria[_JEV_UNRESOLVED_CHOICE] = (
        "The supplied transient context is insufficient or contradictory for "
        "choosing any admissible option."
    )

    return {
        "model": model,
        "state": state,
        "questions": {
            _JEV_QUESTION_ID: {
                "type": "choice",
                "instructions": request.instruction,
                "criteria": criteria,
            }
        },
    }


def render_llama_cpp_systemtwo_request(
    request: BoundedChoiceRequest,
    *,
    model: str,
) -> dict[str, object]:
    """Render an additive System Two candidate over the same bounded state.

    The active provider path does not use this renderer yet. It exists to freeze
    the deterministic sibling shape before any endpoint switch or cache claim.
    """

    if not isinstance(request, BoundedChoiceRequest):
        raise TypeError("request must be BoundedChoiceRequest")
    _require_text("model", model)

    state = render_llama_cpp_bounded_state(request)
    state_text = json.dumps(
        state,
        ensure_ascii=False,
        sort_keys=True,
        indent=2,
    )
    options = "\n".join(
        f"{choice.choice_id}: {choice.description}"
        for choice in request.choices
    )
    user_message = (
        "Context:\n"
        + state_text
        + "\n\n"
        + "Perform deeper bounded cognition using only the supplied transient "
        "context and admissible options. Resolve to one option only when "
        "sufficiently justified; otherwise report unresolved. Include a brief "
        "rationale in the structured response.\n"
        + "Question: "
        + request.instruction
        + "\nOptions:\n"
        + options
    )

    return {
        "model": model,
        "temperature": 0,
        "max_tokens": THINK_MAX_TOKENS,
        "reasoning_effort": "none",
        "cache_prompt": False,
        "response_format": _decision_response_format(
            request,
            mode=CognitionMode.THINK,
        ),
        "messages": [
            {
                "role": "user",
                "content": user_message,
            }
        ],
    }


def render_llama_cpp_open_request(
    request: OpenCognitionRequest,
    *,
    model: str,
) -> dict[str, object]:
    if not isinstance(request, OpenCognitionRequest):
        raise TypeError("request must be OpenCognitionRequest")
    _require_text("model", model)

    context = [
        {
            "key": datum.key,
            "value": json.loads(datum.value_json),
            "provenance": {
                "source": datum.provenance.source,
                "reference": datum.provenance.reference,
            },
        }
        for datum in request.context
    ]
    payload = {
        "request_id": request.request_id,
        "instruction": request.instruction,
        "intent_id": request.intent_id,
        "focus": request.focus,
        "context": context,
    }
    return {
        "model": model,
        "temperature": 0,
        "max_tokens": OPEN_MAX_TOKENS,
        "reasoning_effort": "none",
        "cache_prompt": False,
        "messages": [
            {
                "role": "system",
                "content": _system_message(request, mode=CognitionMode.OPEN),
            },
            {
                "role": "user",
                "content": json.dumps(
                    payload,
                    ensure_ascii=False,
                    sort_keys=True,
                    separators=(",", ":"),
                ),
            },
        ],
    }


def parse_llama_cpp_decision(
    raw_text: str,
    *,
    mode: CognitionMode,
) -> ProviderDecision:
    if mode not in {CognitionMode.BOUNDED, CognitionMode.THINK}:
        raise TypeError("decision parser requires BOUNDED or THINK")
    if not isinstance(raw_text, str):
        raise LlamaCppProviderProtocolError(
            f"{mode.value} model content must be text"
        )
    try:
        value = json.loads(raw_text)
    except json.JSONDecodeError as exc:
        raise LlamaCppProviderProtocolError(
            f"{mode.value} model content is not valid JSON: {exc.msg}"
        ) from exc
    if not isinstance(value, dict):
        raise LlamaCppProviderProtocolError(
            f"{mode.value} model response must be a JSON object"
        )

    expected = (
        {"status", "choice_id"}
        if mode is CognitionMode.BOUNDED
        else {"status", "choice_id", "rationale"}
    )
    if set(value) != expected:
        raise LlamaCppProviderProtocolError(
            f"{mode.value} model response schema mismatch"
        )

    status = value.get("status")
    choice_id = value.get("choice_id")

    if mode is CognitionMode.THINK:
        rationale = value.get("rationale")
        if not isinstance(rationale, str) or not rationale.strip():
            raise LlamaCppProviderProtocolError(
                "think model response requires non-empty rationale"
            )
        reason = rationale
    else:
        reason = ""

    if status == DecisionStatus.RESOLVED.value:
        if not isinstance(choice_id, str) or not choice_id.strip():
            raise LlamaCppProviderProtocolError(
                f"{mode.value} resolved response requires choice_id"
            )
        return ProviderDecision.resolved(choice_id, reason=reason)

    if status == DecisionStatus.UNRESOLVED.value and choice_id is None:
        return ProviderDecision.unresolved(
            reason=reason or f"{mode.value}_model_unresolved"
        )

    raise LlamaCppProviderProtocolError(
        f"{mode.value} model response status/choice combination is invalid"
    )


def parse_llama_cpp_jev_decision(
    body: dict[str, Any],
    *,
    request: BoundedChoiceRequest,
) -> ProviderDecision:
    """Parse one Jev/System One answer into the existing ProviderDecision."""

    if not isinstance(body, dict):
        raise LlamaCppProviderProtocolError(
            "Jev response body must be a JSON object"
        )
    answers = body.get("answers")
    if not isinstance(answers, dict):
        raise LlamaCppProviderProtocolError(
            "Jev response missing answers object"
        )
    answer = answers.get(_JEV_QUESTION_ID)
    if not isinstance(answer, dict):
        raise LlamaCppProviderProtocolError(
            "Jev response missing bounded decision answer"
        )
    if answer.get("type") != "choice":
        raise LlamaCppProviderProtocolError(
            "Jev bounded decision answer must have type=choice"
        )
    choice_id = answer.get("choice")
    if not isinstance(choice_id, str) or not choice_id.strip():
        raise LlamaCppProviderProtocolError(
            "Jev bounded decision answer requires non-empty choice"
        )

    usage = body.get("usage")
    if usage is not None and not isinstance(usage, dict):
        raise LlamaCppProviderProtocolError(
            "Jev usage must be a JSON object when present"
        )
    prompt_tokens = _jev_usage_int(usage, "input_tokens")
    completion_tokens = _jev_usage_int(usage, "output_tokens")
    if completion_tokens not in {None, 0}:
        raise LlamaCppProviderProtocolError(
            "Jev bounded decision must not generate output tokens"
        )
    total_tokens = (
        None
        if prompt_tokens is None or completion_tokens is None
        else prompt_tokens + completion_tokens
    )
    call_facts = ProviderCallFacts(
        requested_max_output_tokens=None,
        prompt_tokens=prompt_tokens,
        completion_tokens=completion_tokens,
        total_tokens=total_tokens,
        finish_reason=None,
    )

    if choice_id == _JEV_UNRESOLVED_CHOICE:
        return ProviderDecision.unresolved(
            reason="jev_model_unresolved",
            call_facts=call_facts,
        )

    allowed = {choice.choice_id for choice in request.choices}
    if choice_id not in allowed:
        raise LlamaCppProviderProtocolError(
            f"Jev returned inadmissible choice_id: {choice_id}"
        )
    return ProviderDecision.resolved(
        choice_id,
        call_facts=call_facts,
    )


class LlamaCppRelayProvider:
    """Target-local llama.cpp realization of the RelayEngine provider seam."""

    def __init__(
        self,
        *,
        endpoint: str,
        model: str,
        timeout: float = 60.0,
        systemone_endpoint: str | None = None,
    ) -> None:
        self._endpoint = _validate_endpoint(endpoint)
        self._systemone_endpoint = (
            None
            if systemone_endpoint is None
            else _validate_endpoint(systemone_endpoint)
        )
        _require_text("model", model)
        if (
            not isinstance(timeout, (int, float))
            or isinstance(timeout, bool)
            or timeout <= 0
        ):
            raise ValueError("timeout must be a positive number")
        self._model = model
        self._timeout = float(timeout)

    @property
    def endpoint(self) -> str:
        return self._endpoint

    @property
    def model(self) -> str:
        return self._model

    @property
    def systemone_endpoint(self) -> str | None:
        return self._systemone_endpoint

    def __call__(
        self,
        request: BoundedChoiceRequest | OpenCognitionRequest,
        *,
        mode: CognitionMode,
    ) -> ProviderDecision | ProviderExpression:
        if mode is CognitionMode.BOUNDED and self._systemone_endpoint is not None:
            if not isinstance(request, BoundedChoiceRequest):
                raise TypeError("BOUNDED mode requires BoundedChoiceRequest")
            request_body = render_llama_cpp_jev_request(
                request,
                model=self._model,
            )
            body = self._call(
                request_body,
                endpoint=self._systemone_endpoint,
            )
            return parse_llama_cpp_jev_decision(
                body,
                request=request,
            )

        if mode is CognitionMode.OPEN:
            if not isinstance(request, OpenCognitionRequest):
                raise TypeError("OPEN mode requires OpenCognitionRequest")
            request_body = render_llama_cpp_open_request(
                request,
                model=self._model,
            )
            body = self._call(request_body)
            raw_text, call_facts = _extract_completion(
                body,
                request_body=request_body,
            )
            if not raw_text.strip():
                raise LlamaCppProviderProtocolError(
                    "open model content must be non-empty text"
                )
            return ProviderExpression(
                text=raw_text,
                provenance=Provenance(
                    source="llama.cpp",
                    reference=(
                        f"request:{request.request_id}:model:{self._model}"
                    ),
                ),
                call_facts=call_facts,
            )

        if not isinstance(request, BoundedChoiceRequest):
            raise TypeError("BOUNDED/THINK mode requires BoundedChoiceRequest")
        request_body = render_llama_cpp_request(
            request,
            mode=mode,
            model=self._model,
        )
        body = self._call(request_body)
        raw_text, call_facts = _extract_completion(
            body,
            request_body=request_body,
        )
        decision = parse_llama_cpp_decision(raw_text, mode=mode)
        return ProviderDecision(
            status=decision.status,
            choice_id=decision.choice_id,
            reason=decision.reason,
            call_facts=call_facts,
        )

    def _call(
        self,
        request_body: dict[str, object],
        *,
        endpoint: str | None = None,
    ) -> dict[str, Any]:
        target_endpoint = self._endpoint if endpoint is None else endpoint
        request = urllib.request.Request(
            target_endpoint,
            data=json.dumps(
                request_body,
                ensure_ascii=False,
                sort_keys=True,
                separators=(",", ":"),
            ).encode("utf-8"),
            headers={
                "Content-Type": "application/json",
                "Accept": "application/json",
            },
            method="POST",
        )
        try:
            with urllib.request.urlopen(
                request,
                timeout=self._timeout,
            ) as response:
                body = json.loads(response.read().decode("utf-8"))
        except (
            urllib.error.URLError,
            TimeoutError,
            UnicodeDecodeError,
            json.JSONDecodeError,
        ) as exc:
            raise LlamaCppProviderError(
                f"llama.cpp model call failed: {type(exc).__name__}: {exc}"
            ) from exc

        if not isinstance(body, dict):
            raise LlamaCppProviderProtocolError(
                "llama.cpp response body must be a JSON object"
            )
        return body


def _extract_completion(
    body: dict[str, Any],
    *,
    request_body: dict[str, object],
) -> tuple[str, ProviderCallFacts]:
    try:
        choice = body["choices"][0]
        content = choice["message"]["content"]
    except (KeyError, IndexError, TypeError) as exc:
        raise LlamaCppProviderProtocolError(
            "llama.cpp response missing choices[0].message.content"
        ) from exc
    if not isinstance(choice, dict):
        raise LlamaCppProviderProtocolError(
            "llama.cpp choices[0] must be a JSON object"
        )
    if not isinstance(content, str):
        raise LlamaCppProviderProtocolError(
            "llama.cpp message content must be text"
        )

    finish_reason = choice.get("finish_reason")
    if finish_reason is not None:
        if not isinstance(finish_reason, str) or not finish_reason.strip():
            raise LlamaCppProviderProtocolError(
                "llama.cpp finish_reason must be non-empty text when present"
            )
        if finish_reason != "stop":
            raise LlamaCppProviderProtocolError(
                "llama.cpp completion did not finish with stop: "
                f"{finish_reason}"
            )

    usage = body.get("usage")
    if usage is not None and not isinstance(usage, dict):
        raise LlamaCppProviderProtocolError(
            "llama.cpp usage must be a JSON object when present"
        )

    requested_max_output_tokens = request_body.get("max_tokens")
    if (
        isinstance(requested_max_output_tokens, bool)
        or not isinstance(requested_max_output_tokens, int)
        or requested_max_output_tokens <= 0
    ):
        raise LlamaCppProviderProtocolError(
            "serialized request max_tokens must be a positive integer"
        )

    return content, ProviderCallFacts(
        requested_max_output_tokens=requested_max_output_tokens,
        prompt_tokens=_usage_int(usage, "prompt_tokens"),
        completion_tokens=_usage_int(usage, "completion_tokens"),
        total_tokens=_usage_int(usage, "total_tokens"),
        finish_reason=finish_reason,
    )


def _usage_int(
    usage: dict[str, Any] | None,
    key: str,
) -> int | None:
    if usage is None or key not in usage:
        return None
    value = usage[key]
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        raise LlamaCppProviderProtocolError(
            f"llama.cpp usage.{key} must be a non-negative integer"
        )
    return value


def _jev_usage_int(
    usage: dict[str, Any] | None,
    key: str,
) -> int | None:
    if usage is None or key not in usage:
        return None
    value = usage[key]
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        raise LlamaCppProviderProtocolError(
            f"Jev usage.{key} must be a non-negative integer"
        )
    return value


def _validate_endpoint(endpoint: object) -> str:
    _require_text("endpoint", endpoint)
    parsed = urllib.parse.urlsplit(endpoint)
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        raise ValueError("endpoint must be an http(s) URL")
    if parsed.query or parsed.fragment:
        raise ValueError("endpoint must not contain query or fragment")
    return urllib.parse.urlunsplit(
        (
            parsed.scheme,
            parsed.netloc,
            parsed.path,
            "",
            "",
        )
    )


def _require_text(name: str, value: object) -> None:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{name} must be a non-empty string")
