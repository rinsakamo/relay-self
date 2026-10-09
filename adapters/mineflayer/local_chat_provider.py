"""S52 explicit loopback-only OpenAI-compatible RelayEngine provider.

All calls use the existing RelayEngine contract and S47 budget allocator.
Provider output is transient text/choice, never World truth or Action grant.
"""
from __future__ import annotations

import json
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass

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


class LocalInferenceUnavailable(ValueError):
    """Reject external URLs, ambiguous response and unbounded inference."""


@dataclass(frozen=True, slots=True)
class LoopbackInferenceConfig:
    model: str
    endpoint: str = "http://127.0.0.1:1234/v1/chat/completions"
    timeout_s: float = 45.0
    max_tokens: int = 256

    def __post_init__(self) -> None:
        parsed = urllib.parse.urlsplit(self.endpoint)
        if (
            not isinstance(self.model, str) or not self.model.strip()
            or not isinstance(self.endpoint, str)
            or parsed.scheme != "http"
            or parsed.hostname not in {"127.0.0.1", "localhost", "::1"}
            or parsed.path != "/v1/chat/completions"
            or parsed.username is not None or parsed.password is not None
            or parsed.query or parsed.fragment
            or not isinstance(self.timeout_s, (int, float))
            or isinstance(self.timeout_s, bool)
            or not 0 < self.timeout_s <= 120
            or type(self.max_tokens) is not int
            or not 1 <= self.max_tokens <= 1024
        ):
            raise LocalInferenceUnavailable("explicit bounded local inference required")


class LoopbackChatProvider:
    def __init__(self, config: LoopbackInferenceConfig) -> None:
        if not isinstance(config, LoopbackInferenceConfig):
            raise LocalInferenceUnavailable("typed loopback configuration required")
        self.config = config

    def __call__(
        self, request: BoundedChoiceRequest | OpenCognitionRequest, *,
        mode: CognitionMode,
    ) -> ProviderDecision | ProviderExpression:
        if not isinstance(mode, CognitionMode):
            raise LocalInferenceUnavailable("known inference regime required")
        if mode is CognitionMode.OPEN:
            if not isinstance(request, OpenCognitionRequest):
                raise LocalInferenceUnavailable("OPEN requires explicit open request")
            system = "Provide one concise hypothesis or expression. It is not verified."
        else:
            if not isinstance(request, BoundedChoiceRequest):
                raise LocalInferenceUnavailable("BOUNDED/THINK require finite choices")
            ids = tuple(choice.choice_id for choice in request.choices)
            system = (
                "Reply with exactly one admissible ID or UNRESOLVED; no explanation. "
                "Admissible IDs: " + json.dumps(ids)
            )
        messages = [
            {"role": "system", "content": system},
            {"role": "user", "content": json.dumps({
                "instruction": request.instruction,
                "intent_id": request.intent_id,
                "focus": request.focus,
                "context": [
                    {
                        "key": item.key, "value_json": item.value_json,
                        "source": item.provenance.source,
                        "reference": item.provenance.reference,
                    }
                    for item in request.context
                ],
                "identity_context": None if request.identity_context is None else {
                    "key": request.identity_context.key,
                    "value_json": request.identity_context.value_json,
                    "source": request.identity_context.provenance.source,
                    "reference": request.identity_context.provenance.reference,
                },
            }, ensure_ascii=False)},
        ]
        payload = json.dumps({
            "model": self.config.model,
            "messages": messages,
            "temperature": 0,
            "max_tokens": self.config.max_tokens,
            "stream": False,
        }).encode("utf-8")
        outgoing = urllib.request.Request(
            self.config.endpoint, data=payload,
            headers={"Content-Type": "application/json"}, method="POST",
        )
        # Disable redirects: a loopback HTTP provider must never redirect to
        # another host. The opener below is intentionally request-local.
        opener = urllib.request.build_opener(urllib.request.ProxyHandler({}), _NoRedirect)
        try:
            with opener.open(outgoing, timeout=self.config.timeout_s) as response:
                if response.geturl() != self.config.endpoint:
                    raise LocalInferenceUnavailable("redirected model host forbidden")
                raw = response.read(131073)
        except (OSError, urllib.error.URLError) as exc:
            raise LocalInferenceUnavailable("local inference unavailable") from exc
        if len(raw) > 131072:
            raise LocalInferenceUnavailable("provider response too large")
        try:
            parsed = json.loads(raw)
            answer = parsed["choices"][0]["message"]["content"]
            usage = parsed.get("usage", {})
            finish = parsed["choices"][0].get("finish_reason")
            if not isinstance(answer, str) or not answer.strip():
                raise ValueError("empty response")
            if not isinstance(usage, dict):
                raise ValueError("invalid token usage")
            if finish is not None and not isinstance(finish, str):
                raise ValueError("invalid finish reason")
            facts = ProviderCallFacts(
                requested_max_output_tokens=self.config.max_tokens,
                prompt_tokens=usage.get("prompt_tokens"),
                completion_tokens=usage.get("completion_tokens"),
                total_tokens=usage.get("total_tokens"),
                finish_reason=finish,
            )
        except (KeyError, IndexError, TypeError, ValueError) as exc:
            raise LocalInferenceUnavailable("invalid local completion envelope") from exc
        if mode is CognitionMode.OPEN:
            return ProviderExpression(
                answer.strip(),
                Provenance("local-llm", f"{self.config.model}:{request.request_id}:open"),
                facts,
            )
        choice = answer.strip()
        if choice in {x.choice_id for x in request.choices}:
            return ProviderDecision(
                DecisionStatus.RESOLVED, choice, "local bounded choice", facts,
            )
        return ProviderDecision(
            DecisionStatus.UNRESOLVED, None, "nonadmissible local choice", facts,
        )


class _NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None
