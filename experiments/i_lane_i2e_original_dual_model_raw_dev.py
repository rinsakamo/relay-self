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
from dataclasses import asdict
from pathlib import Path

from adapters.llama_cpp.relay_engine import (
    LlamaCppRelayProvider,
    _write_model_raw_once,
)
from relay_self.i_lane_i2d_self_schema_adoption_dev import (
    finish_i2d_self_adoption,
    submit_i2d_original_l1_acceptance,
    submit_i2d_original_l2,
)
from relay_self.persistent_cognition import load_persistent_cognition
from relay_self.resident_llama_inference_lane_dev import ResidentLlamaInferenceLane


class I2eRawModelHold(RuntimeError):
    """Raw model attempt is not safely attributable or bounded."""


class I2eOriginalDualModeRawProvider(LlamaCppRelayProvider):
    """Never accept JEV/THINK, wrong order, third POST or shared evidence dir."""

    def __init__(
        self, *, endpoint: str, model: str, raw_dir: Path, timeout: float = 45,
    ) -> None:
        super().__init__(endpoint=endpoint, model=model, timeout=timeout)
        if (
            not isinstance(raw_dir, Path) or raw_dir.is_symlink()
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


async def run_i2e_original_dual_raw(
    *, bridge, boot, world, links, self_id: str,
    lane: ResidentLlamaInferenceLane,
    provider: I2eOriginalDualModeRawProvider,
    timeout_s: float = 60.0,
) -> dict:
    """No retry: collect both original model entity bodies, requests and Owner.

    This callable must be injected by a separate provenance-qualified owned
    Paper/Native runner. It does not attest the World or start any process.
    A partial trial retains the raw original evidence for a later HOLD audit.
    """
    if (
        type(provider) is not I2eOriginalDualModeRawProvider
        or not isinstance(lane, ResidentLlamaInferenceLane)
        or lane.provider is not provider
        or bridge.inference_lane is not lane
        or bridge.cognitive_work is not lane.cognitive_work
        or not bridge.physical.observation_only
        or bridge.physical.active_action_ids
        or provider.attempted or provider.completed
        or type(timeout_s) not in (int, float)
        or not 0 < timeout_s <= 60
    ):
        raise I2eRawModelHold("single original owned lane/raw preflight required")
    owner = bridge.owners[self_id]
    raw_dir = provider.raw_dir
    with lane.cognitive_work.lock:
        original_bytes = owner.files.cognition_file.read_bytes()
        if load_persistent_cognition(owner.files.cognition_file) != owner.retained:
            raise I2eRawModelHold("original durable cognition not authoritative")
        _write_model_raw_once(raw_dir / "before-cognition.json", original_bytes)
    proposed = submit_i2d_original_l2(
        bridge=bridge, boot=boot, world=world, links=links,
        self_id=self_id, lane=lane,
    )
    await lane.await_result(proposed.ticket, timeout_s=timeout_s)
    accepted = submit_i2d_original_l1_acceptance(
        bridge=bridge, boot=boot, world=world, links=links,
        proposed=proposed, lane=lane,
    )
    await lane.await_result(accepted.ticket, timeout_s=timeout_s)
    outcome = finish_i2d_self_adoption(
        bridge=bridge, boot=boot, world=world, links=links,
        accepted=accepted, lane=lane,
    )
    if (provider.attempted != 2 or provider.completed != 2
            or provider.uncertain or outcome.physical_action_authorized
            or not outcome.goal_unresolved):
        raise I2eRawModelHold("dual real model attempts/Owner result uncertain")
    with lane.cognitive_work.lock:
        after_bytes = owner.files.cognition_file.read_bytes()
        if load_persistent_cognition(owner.files.cognition_file) != owner.retained:
            raise I2eRawModelHold("original updated durable cognition not readable")
        _write_model_raw_once(raw_dir / "after-cognition.json", after_bytes)
        manifest = {
            "schema": 1,
            "source_category": "original_bridge_unattested_world",
            "self_id": self_id,
            "model_alias": provider.model,
            "backend_ref": lane.backend_ref,
            "open_l2_request": asdict(proposed.request),
            "bounded_l1_request": asdict(accepted.request),
            "open_l2_ticket": asdict(proposed.ticket),
            "bounded_l1_ticket": asdict(accepted.ticket),
            "handoff": asdict(proposed.handoff),
            "l2_pattern": {
                "pattern_id": accepted.pattern.pattern_id,
                "provenance": asdict(accepted.pattern.provenance),
            },
            "outcome": asdict(outcome),
            "before_cognition_sha256": hashlib.sha256(original_bytes).hexdigest(),
            "after_cognition_sha256": hashlib.sha256(after_bytes).hexdigest(),
            "all_physical_actions": 0,
            "world_independent_audit_attested": False,
        }
        _write_model_raw_once(
            raw_dir / "i2e-dual-model-report.json",
            (json.dumps(manifest, ensure_ascii=False, sort_keys=True,
                        indent=2) + "\n").encode("utf-8"),
        )
        return manifest
