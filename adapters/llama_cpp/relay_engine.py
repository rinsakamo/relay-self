from __future__ import annotations

import json
import urllib.error
import urllib.parse
import urllib.request
from typing import Any

from relay_self.relay_engine import (
    BoundedChoiceRequest,
    CognitionMode,
    DecisionStatus,
    ProviderDecision,
)

BOUNDED_MAX_TOKENS = 48
THINK_MAX_TOKENS = 256

_BOUNDED_SYSTEM = (
    "You are the bounded cognition provider for RelaySelf. "
    "Use only the supplied transient context and finite choices. "
    "If one admissible choice is sufficiently justified, return exactly one JSON "
    "object with keys status and choice_id: "
    '{"status":"resolved","choice_id":"<id>"}. '
    "If the bounded surface is insufficient or contradictory, return exactly "
    '{"status":"unresolved","choice_id":null}. '
    "Do not add prose, markdown, or other keys."
)

_THINK_SYSTEM = (
    "You are handling an explicit THINK escalation for RelaySelf after bounded "
    "cognition did not safely resolve. Reconsider interactions and constraints "
    "using only the supplied transient context and finite choices. "
    "Return exactly one JSON object with keys status, choice_id, and rationale. "
    'For resolution use {"status":"resolved","choice_id":"<id>",'
    '"rationale":"<brief reasoning>"}. '
    'If still insufficient use {"status":"unresolved","choice_id":null,'
    '"rationale":"<brief reason>"}. '
    "Do not add prose, markdown, or other keys."
)


class LlamaCppProviderError(RuntimeError):
    """Raised when the local llama.cpp provider path fails operationally."""


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
        "choices": [
            {
                "choice_id": choice.choice_id,
                "description": choice.description,
            }
            for choice in request.choices
        ],
        "context": context,
    }

    system = (
        _BOUNDED_SYSTEM
        if mode is CognitionMode.BOUNDED
        else _THINK_SYSTEM
    )
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


def parse_llama_cpp_decision(
    raw_text: str,
    *,
    mode: CognitionMode,
) -> ProviderDecision:
    if not isinstance(raw_text, str):
        return ProviderDecision.unresolved(
            reason=f"{mode.value}_parse_error:content_not_text"
        )
    try:
        value = json.loads(raw_text)
    except json.JSONDecodeError as exc:
        return ProviderDecision.unresolved(
            reason=f"{mode.value}_parse_error:invalid_json:{exc.msg}"
        )
    if not isinstance(value, dict):
        return ProviderDecision.unresolved(
            reason=f"{mode.value}_parse_error:response_not_object"
        )

    expected = (
        {"status", "choice_id"}
        if mode is CognitionMode.BOUNDED
        else {"status", "choice_id", "rationale"}
    )
    if set(value) != expected:
        return ProviderDecision.unresolved(
            reason=f"{mode.value}_parse_error:schema_mismatch"
        )

    status = value.get("status")
    choice_id = value.get("choice_id")

    if mode is CognitionMode.THINK:
        rationale = value.get("rationale")
        if not isinstance(rationale, str) or not rationale.strip():
            return ProviderDecision.unresolved(
                reason="think_parse_error:rationale_missing"
            )
        reason = rationale
    else:
        reason = ""

    if status == DecisionStatus.RESOLVED.value:
        if not isinstance(choice_id, str) or not choice_id.strip():
            return ProviderDecision.unresolved(
                reason=f"{mode.value}_parse_error:resolved_choice_missing"
            )
        return ProviderDecision.resolved(
            choice_id,
            reason=reason,
        )

    if status == DecisionStatus.UNRESOLVED.value and choice_id is None:
        return ProviderDecision.unresolved(
            reason=reason or f"{mode.value}_model_unresolved"
        )

    return ProviderDecision.unresolved(
        reason=f"{mode.value}_parse_error:status_or_choice_invalid"
    )


class LlamaCppRelayProvider:
    """Target-local llama.cpp realization of the RelayEngine provider seam."""

    def __init__(
        self,
        *,
        endpoint: str,
        model: str,
        timeout: float = 60.0,
    ) -> None:
        self._endpoint = _validate_endpoint(endpoint)
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

    def __call__(
        self,
        request: BoundedChoiceRequest,
        *,
        mode: CognitionMode,
    ) -> ProviderDecision:
        request_body = render_llama_cpp_request(
            request,
            mode=mode,
            model=self._model,
        )
        raw_text = self._call(request_body)
        return parse_llama_cpp_decision(raw_text, mode=mode)

    def _call(self, request_body: dict[str, object]) -> str:
        request = urllib.request.Request(
            self._endpoint,
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
            raise LlamaCppProviderError(
                "llama.cpp response body must be a JSON object"
            )
        return _extract_content(body)


def _extract_content(body: dict[str, Any]) -> str:
    try:
        content = body["choices"][0]["message"]["content"]
    except (KeyError, IndexError, TypeError) as exc:
        raise LlamaCppProviderError(
            "llama.cpp response missing choices[0].message.content"
        ) from exc
    if not isinstance(content, str):
        raise LlamaCppProviderError(
            "llama.cpp message content must be text"
        )
    return content


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
