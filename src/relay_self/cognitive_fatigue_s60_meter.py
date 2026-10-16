"""L-CF4 opt-in evidence candidate from the existing S60-B1 HTTP transport.

The existing S60-B1 owner still performs every network operation and emits
the original text-only Future. This subclass only preserves validated provider
usage and request/response byte digests for independent S/R verification.
HTTP completion is NOT an independently authenticated receipt, backend idle,
GPU release, scientific result, Action authorization, or completed fatigue charge.
"""
from __future__ import annotations

import json
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from hashlib import sha256
from typing import Any

from adapters.mineflayer.s60b1_loopback_adapter import (
    LoopbackDisplacementAdapter,
    LoopbackTransportConfig,
    TransportUnconfirmed,
)
from relay_self.best_effort_displacement import ModelRequest


@dataclass(frozen=True, slots=True)
class S60MeterCandidate:
    """Sanitized fields from a naturally completed, fully metered HTTP reply."""

    session_id: str
    work_id: str
    generation: int
    world_seq: int
    intent_revision: int
    retained_revision: int
    request_sha256: str
    response_sha256: str
    model_alias: str
    max_output_tokens: int
    prompt_tokens: int
    completion_tokens: int
    total_tokens: int
    finish_reason: str
    status: str = "HTTP_COMPLETION_METER_CANDIDATE"
    externally_qualified: bool = False
    backend_stop_ack: bool = False
    action_authority: bool = False


class MeteredS60Adapter(LoopbackDisplacementAdapter):
    """No second executor; opt-in strict usage validation on original HTTP bytes."""

    def __init__(
        self,
        config: LoopbackTransportConfig,
        payload_for: Callable[[ModelRequest], Mapping[str, Any]],
    ) -> None:
        super().__init__(config, payload_for)
        self._staged: S60MeterCandidate | None = None
        self._request_digest: tuple[str, str] | None = None

    def start(self, request: ModelRequest):
        self._staged = None
        self._request_digest = None
        return super().start(request)

    def _payload(self, request: ModelRequest) -> bytes:
        raw = super()._payload(request)
        self._request_digest = (request.work_id, sha256(raw).hexdigest())
        return raw

    def _validate_response(self, body: bytes, max_tokens: int) -> str:
        # The original S60 implementation owns all envelope checks, duplicate
        # keys, content/finish validation, output bounds and sanitization.
        answer = super()._validate_response(body, max_tokens)
        try:
            parsed = json.loads(body)
            usage = parsed["usage"]
            if not isinstance(usage, dict):
                raise ValueError
            prompt = usage["prompt_tokens"]
            completion = usage["completion_tokens"]
            total = usage["total_tokens"]
            finish = parsed["choices"][0]["finish_reason"]
            if (
                any(type(n) is not int or n < 0 for n in (prompt, completion, total))
                or total != prompt + completion
                or total <= 0
                or completion > max_tokens
                or finish not in ("stop", "length")
            ):
                raise ValueError
            attempt = self._attempt
            digest = self._request_digest
            if (
                attempt is None or digest is None
                or digest[0] != attempt.request.work_id
                or attempt.request.context.session_id != self._owner.context.session_id
                or not isinstance(digest[1], str)
            ):
                raise ValueError
            request = attempt.request
            self._staged = S60MeterCandidate(
                request.context.session_id,
                request.work_id,
                request.generation,
                request.context.world_seq,
                request.context.intent_revision,
                request.context.retained_revision,
                digest[1],
                sha256(body).hexdigest(),
                self.config.model,
                max_tokens,
                prompt,
                completion,
                total,
                finish,
            )
            return answer
        except Exception:
            self._staged = None
            raise TransportUnconfirmed("completed usage meter unconfirmed") from None

    @property
    def metered_completion(self) -> S60MeterCandidate | None:
        """Candidate only after actual natural S60 HTTP Future completion.

        Local cancel, stale/replaced attempt, failed HTTP, missing usage, and
        incomplete completion never expose a cost-settlement candidate.
        A stale World output must STILL be rejected by original S fences.
        """
        attempt = self._attempt
        candidate = self._staged
        if (
            attempt is None or candidate is None
            or attempt.cancelled
            or not attempt.future.done()
            or attempt.future.cancelled()
            or attempt.future.exception() is not None
            or candidate.work_id != attempt.request.work_id
            or candidate.generation != attempt.request.generation
            or candidate.session_id != attempt.request.context.session_id
            or not any(
                event == "HTTP_COMPLETION_OBSERVED"
                and generation == attempt.request.generation
                for event, generation in self.receipts
            )
        ):
            return None
        return candidate
