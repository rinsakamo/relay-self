"""Prospective offline observer only; never wired into the physical B2 runner."""
from __future__ import annotations

import asyncio
import time
from collections import deque
from dataclasses import dataclass

from adapters.mineflayer.s60b2_owned_backend_probe import (
    FINGERPRINT,
    MeasuredTransport,
    parse_json,
)

STAGES = frozenset({
    "HTTP_READ_OR_FRAMING_UNCONFIRMED", "JSON_DECODE_FAILURE",
    "MODEL_OR_FINGERPRINT_MISMATCH", "USAGE_ENVELOPE_UNCONFIRMED",
    "SCHEMA_UNCONFIRMED", "CLIENT_CANCEL_OR_UNKNOWN",
    "TRANSPORT_PRE_RESPONSE_UNKNOWN", "TRANSPORT_STAGE_UNKNOWN",
})


@dataclass(frozen=True, slots=True)
class DiagnosticReceipt:
    stage: str
    generation: int
    elapsed_ms: int


class OfflineDiagnosticTransport(MeasuredTransport):
    """Inherited transport remains sole completion authority; no observer I/O.

    Use only with synthetic offline HTTP. The physical runner never constructs
    this class. HTTP sub-stages and remaining B1 schema gates lack distinct seams.
    """

    def __init__(self, config, payload, journal):
        super().__init__(config, payload, journal)
        self._diagnostics = deque(maxlen=64)
        self._diagnostic_start = time.monotonic()
        self._response_entered = False
        self._failure_observed = False

    @property
    def diagnostics(self) -> tuple[DiagnosticReceipt, ...]:
        return tuple(self._diagnostics)

    def _observe(self, stage, attempt, *, task_required=True):
        # A foreign callback or manual parser invocation cannot mint provenance.
        if (attempt is None or attempt is not self._attempt or self._owner is None
            or attempt.request.context != self._owner.context
            or (task_required and asyncio.current_task() is not attempt.task)):
            return
        elapsed = min(86_400_000, max(0, int(
            (time.monotonic() - self._diagnostic_start) * 1000)))
        self._diagnostics.append(DiagnosticReceipt(
            stage if stage in STAGES else "TRANSPORT_STAGE_UNKNOWN",
            attempt.request.generation, elapsed))
        self._failure_observed = True

    def _record(self, event, attempt):
        if event == "START_INVOKED" and attempt is self._attempt:
            self._response_entered = self._failure_observed = False
        if event == "CLIENT_CANCEL_UNCONFIRMED":
            self._observe("CLIENT_CANCEL_OR_UNKNOWN", attempt, task_required=False)
        elif event == "TRANSPORT_UNCONFIRMED" and not self._failure_observed:
            self._observe("TRANSPORT_STAGE_UNKNOWN" if self._response_entered
                          else "TRANSPORT_PRE_RESPONSE_UNKNOWN", attempt)
        super()._record(event, attempt)

    async def _response(self, reader):
        self._response_entered = True
        try:
            return await super()._response(reader)
        except asyncio.CancelledError:
            self._observe("CLIENT_CANCEL_OR_UNKNOWN", self._attempt)
            raise
        except Exception:
            self._observe("HTTP_READ_OR_FRAMING_UNCONFIRMED", self._attempt)
            raise

    def _validate_response(self, body, max_tokens):
        # Classification only: always delegate acceptance to the exact frozen
        # implementation, even after the observer cannot decode the body.
        stage = "TRANSPORT_STAGE_UNKNOWN"
        try:
            value = parse_json(body)
        except Exception:
            stage = "JSON_DECODE_FAILURE"
        else:
            if not isinstance(value, dict):
                stage = "SCHEMA_UNCONFIRMED"
            elif (value.get("model") != self.config.model
                  or value.get("system_fingerprint") != FINGERPRINT):
                stage = "MODEL_OR_FINGERPRINT_MISMATCH"
            elif not isinstance(value.get("usage"), dict):
                stage = "USAGE_ENVELOPE_UNCONFIRMED"
            else:
                stage = "SCHEMA_UNCONFIRMED"
        try:
            return super()._validate_response(body, max_tokens)
        except Exception:
            self._observe(stage, self._attempt)
            raise
