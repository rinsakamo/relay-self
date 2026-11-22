"""I2e: exactly one OPEN L2 followed by one BOUNDED L1 raw HTTP capture.

Actual model I/O is opt-in in the caller's already-qualified original bridge.
This *provider* does not launch llama.cpp, Paper or World. It inherits the
original LlamaCppRelayProvider, so the shared ResidentLlamaInferenceLane owns
both requests. The files contain HTTP entity-body bytes, NOT network packets.
"""
from __future__ import annotations

import hashlib
import json
import urllib.error
import urllib.request
from pathlib import Path

from adapters.llama_cpp.relay_engine import (
    LlamaCppProviderError,
    LlamaCppRelayProvider,
    _write_model_raw_once,
)


class I2eRawModelHold(RuntimeError):
    """Raw model attempt is not safely attributable or bounded."""


class I2eOriginalDualModeRawProvider(LlamaCppRelayProvider):
    """Never accept JEV/THINK, wrong order, third POST or shared evidence dir."""

    def __init__(
        self, *, endpoint: str, model: str, raw_dir: Path, timeout: float = 45,
    ) -> None:
        super().__init__(endpoint=endpoint, model=model, timeout=timeout)
        if (
            type(raw_dir) is not Path or raw_dir.is_symlink()
            or not raw_dir.is_dir() or any(raw_dir.iterdir())
            or type(timeout) not in (float, int)
            or not 0 < timeout <= 60
        ):
            raise I2eRawModelHold("fresh empty original raw model directory required")
        self.raw_dir = raw_dir
        self.attempted = 0
        self.completed = 0
        self.receipts: list[dict] = []
        self.uncertain = False

    def _call(
        self, request_body: dict[str, object], *,
        endpoint: str | None = None,
    ) -> dict:
        if self.uncertain or endpoint is not None or self.attempted >= 2:
            raise I2eRawModelHold("original dual-mode backend or call count forbidden")
        expected_mode = ("OPEN", "BOUNDED")[self.attempted]
        actual_mode = "BOUNDED" if "response_format" in request_body else "OPEN"
        if (
            actual_mode != expected_mode
            or type(request_body) is not dict
            or request_body.get("model") != self.model
            or type(request_body.get("messages")) is not list
            or request_body.get("cache_prompt") is not False
            or request_body.get("reasoning_effort") != "none"
        ):
            raise I2eRawModelHold("OPEN then BOUNDED from same original model required")
        label = ("open-l2", "bounded-l1")[self.attempted]
        raw_request = json.dumps(
            request_body, ensure_ascii=False, sort_keys=True,
            separators=(",", ":"),
        ).encode("utf-8")
        _write_model_raw_once(self.raw_dir / (label + "-request-body.bin"), raw_request)
        self.attempted += 1  # No automatic retry after any partial attempt.
        request = urllib.request.Request(
            self.endpoint, data=raw_request, method="POST",
            headers={"Content-Type": "application/json", "Accept": "application/json"},
        )
        status = None
        raw_response = None
        try:
            with urllib.request.urlopen(request, timeout=self._timeout) as response:
                status = response.status
                raw_response = response.read(1024 * 1024 + 1)
        except urllib.error.HTTPError as exc:
            status = exc.code
            raw_response = exc.read(1024 * 1024 + 1)
        except (urllib.error.URLError, TimeoutError, OSError) as exc:
            self.uncertain = True
            raise I2eRawModelHold(
                "model transport uncertain; backend slot must independently retire"
            ) from exc
        if (type(status) is not int or raw_response is None
                or len(raw_response) > 1024 * 1024):
            self.uncertain = True
            raise I2eRawModelHold("HTTP response bytes or bounded status unavailable")
        _write_model_raw_once(
            self.raw_dir / (label + "-response-body.bin"), raw_response,
        )
        receipt = {
            "schema": 1, "ordinal": self.attempted,
            "mode": expected_mode, "http_status": status,
            "capture_type": "urllib_http_entity_bodies_not_wire_headers",
            "request_body_sha256": hashlib.sha256(raw_request).hexdigest(),
            "response_body_sha256": hashlib.sha256(raw_response).hexdigest(),
            "request_body_bytes": len(raw_request),
            "response_body_bytes": len(raw_response),
        }
        _write_model_raw_once(
            self.raw_dir / (label + "-http-evidence.json"),
            (json.dumps(receipt, ensure_ascii=False, sort_keys=True, indent=2) + "\n").encode(),
        )
        if status != 200:
            self.uncertain = True
            raise I2eRawModelHold("original model HTTP status not 200")
        try:
            response = json.loads(raw_response)
        except (ValueError, UnicodeError) as exc:
            self.uncertain = True
            raise I2eRawModelHold("model response bytes not valid JSON") from exc
        if type(response) is not dict:
            self.uncertain = True
            raise I2eRawModelHold("model response not JSON object")
        self.completed += 1
        self.receipts.append(receipt)
        return response
