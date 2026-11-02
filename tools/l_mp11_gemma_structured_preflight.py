"""Pre-World real llama.cpp/Gemma strict-JSON + thinking-OFF HTTP probe.

This is a TRANSPORT capability probe on synthetic data, not a physical
Minecraft run, original-source attestation, or a Gemma GGUF hash check.
Only a complete source-checked probe report may unlock the new DEV mode.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
from urllib.parse import urlsplit

from adapters.mineflayer.l_mp11_gemma_wire_contract import (
    GEMMA_MAX_COMPLETION,
    GEMMA_SCHEMA_NAME,
    REQUIRED,
    enforce_gemma_thinking_off,
    strict_gemma_evidence_schema,
)
from adapters.mineflayer.l_mp11_live_l2_shadow import JournaledLiveLlamaProvider
from adapters.llama_cpp.relay_engine import _extract_completion

REPORT_FILENAME = "gemma-structured-preflight.json"
REQUEST_FILENAME = "llama-request-1.raw.json"
RESPONSE_FILENAME = "llama-response-1.raw.json"
STATUS = "REAL_GEMMA_WIRE_PROBE_PASS_UNATTESTED_WEIGHTS"


class GemmaPreflightRejected(ValueError):
    """No valid nonreasoning strict-schema local Gemma HTTP protocol probe."""


def _loopback(endpoint: object, model: object) -> tuple[str, str]:
    if type(endpoint) is not str or type(model) is not str or not model.strip():
        raise GemmaPreflightRejected("explicit local endpoint/model alias required")
    try:
        u = urlsplit(endpoint)
        port = u.port
    except ValueError as exc:
        raise GemmaPreflightRejected("malformed localhost port") from exc
    if (u.scheme != "http" or u.hostname not in {"127.0.0.1", "localhost", "::1"}
            or port is None or u.path != "/v1/chat/completions"
            or u.username is not None or u.password is not None
            or u.query or u.fragment):
        raise GemmaPreflightRejected("local llama.cpp /v1/chat/completions only")
    return endpoint, model


def synthetic_test_body(model: str) -> dict:
    """Finite first-trial fake motion context, visibly NOT a Paper observation."""
    source = []
    source.append({"evidence_id": "T1_W8", "metric_role": "WAIT8_TOTAL_M",
                   "trial_ordinal": 1, "pair_index": 0, "value_m": .4})
    source.append({"evidence_id": "T1_CMAE",
                   "metric_role": "PAPER_CHEAP_NEXT_TICK_MAE_M",
                   "trial_ordinal": 1, "pair_index": 0, "value_m": .05})
    for pair in range(1, 8):
        for label, role, value in (
            ("PRED", "PAPER_NEXT_TICK_PREDICTION_M", .0325),
            ("ERR", "PAPER_NEXT_TICK_ABS_ERROR_M", .0175),
        ):
            source.append({
                "evidence_id": f"T1_P{pair}{label}",
                "metric_role": role, "trial_ordinal": 1,
                "pair_index": pair, "value_m": value,
            })
    payload = {
        "request_id": "SYNTHETIC_WIRE_PREFLIGHT_NO_WORLD",
        "intent_id": "transport-only",
        "focus": "Can the server finish strict JSON with thinking OFF?",
        "instruction": (
            "Return one compact JSON object with the ten required schema keys. "
            "Cite only T1_W8, model_family PHASE_DEPENDENT, "
            "prior_hypothesis_relation FIRST_HYPOTHESIS, short falsifiable idea. "
            "This is SYNTHETIC not a real Minecraft World observation."
        ),
        "context": [{
            "key": "typed_Paper_evidence_ID_catalog",
            "value": {
                "source_kind": "CLOSED_ORIGINAL_PAPER_AND_PRIOR_L2_FEEDBACK",
                "indexed": source,
                "unit": "m",
                "selection_note": "SYNTHETIC_TRANSPORT_ONLY",
            },
            "provenance": {
                "source": "l.mp11.live.paper.numeric.role-table.readonly",
                "reference": "SYNTHETIC_NO_PHYSICAL_SOURCE",
            },
        }],
    }
    return {
        "model": model,
        "temperature": 0,
        "max_tokens": GEMMA_MAX_COMPLETION,
        "messages": [
            {"role": "system", "content": "You are RelaySelf L2, schema output only. "
             "This is a synthetic HTTP transport test, not real World truth."},
            {"role": "user", "content": json.dumps(
                payload, separators=(",", ":"), ensure_ascii=False,
            )},
        ],
    }


def _sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _check_json_output(response: dict, request_body: dict) -> None:
    enforce_gemma_thinking_off(response)
    text, facts = _extract_completion(response, request_body=request_body)
    if facts.finish_reason != "stop" or not text.strip():
        raise GemmaPreflightRejected("Gemma did not stop with a completed JSON answer")
    try:
        output = json.loads(text)
    except (ValueError, TypeError) as exc:
        raise GemmaPreflightRejected("Gemma output was not complete JSON") from exc
    if type(output) is not dict or set(output) != set(REQUIRED):
        raise GemmaPreflightRejected("Gemma failed exact ten-field structured output")
    if (
        output["prior_hypothesis_relation"] != "FIRST_HYPOTHESIS"
        or output["evidence_ids"] != ["T1_W8"]
        or output["referenced_prior_ordinals"] != [1]
    ):
        raise GemmaPreflightRejected("Gemma did not reference the given synthetic source")


def verify_preflight_report(path: Path, *, endpoint: str, model: str) -> dict:
    """Strictly read the pre-World fixture result AND raw saved request/response."""
    endpoint, model = _loopback(endpoint, model)
    if type(path) is not Path or path.name != REPORT_FILENAME:
        raise GemmaPreflightRejected("exact known preflight filename required")
    try:
        report = json.loads(path.read_text(encoding="utf-8"))
        request_raw = (path.parent / REQUEST_FILENAME).read_bytes()
        response_raw = (path.parent / RESPONSE_FILENAME).read_bytes()
        req = json.loads(request_raw)
        res = json.loads(response_raw)
    except (ValueError, OSError, UnicodeError) as exc:
        raise GemmaPreflightRejected("missing immutable raw preflight evidence") from exc
    if type(report) is not dict or (
        report.get("status") != STATUS
        or report.get("endpoint") != endpoint
        or report.get("model") != model
        or report.get("request_sha256") != _sha(request_raw)
        or report.get("response_sha256") != _sha(response_raw)
        or report.get("strict_json_schema") is not True
        or report.get("thinking_off_checked") is not True
        or report.get("physical_paper_observation") is not False
        or report.get("model_weights_attested") is not False
        or report.get("world_qualified") is not False
        or report.get("actual_requests") != 1
    ):
        raise GemmaPreflightRejected("preflight status/provenance/hash mismatch")
    if (req.get("model") != model
            or req.get("max_tokens") != GEMMA_MAX_COMPLETION
            or req.get("reasoning_effort") != "none"
            or req.get("chat_template_kwargs") != {"enable_thinking": False}
            or req.get("stream") is not False
            or req.get("cache_prompt") is not False
            or req.get("temperature") != 0
            or req.get("seed") != 1
            or req.get("response_format") != strict_gemma_evidence_schema(req)
            or req.get("response_format", {}).get("json_schema", {}).get("name")
            != GEMMA_SCHEMA_NAME):
        raise GemmaPreflightRejected("strict schema or Reasoning OFF not genuinely sent")
    _check_json_output(res, req)
    return report


def run(endpoint: str, model: str, evidence_root: Path) -> dict:
    """ONE actual local HTTP probe (not an Action; no retries or substitution)."""
    endpoint, model = _loopback(endpoint, model)
    if type(evidence_root) is not Path:
        raise GemmaPreflightRejected("explicit NEW proof root required")
    evidence_root.mkdir(mode=0o700, parents=True, exist_ok=False)
    provider = JournaledLiveLlamaProvider(
        endpoint=endpoint, model=model, timeout=40.0, journal_root=evidence_root,
        strict_gemma_evidence=True,
    )
    request = synthetic_test_body(model)
    response = provider._call(request)
    request_raw = (evidence_root / REQUEST_FILENAME).read_bytes()
    response_raw = (evidence_root / RESPONSE_FILENAME).read_bytes()
    _check_json_output(response, json.loads(request_raw))
    report = {
        "status": STATUS,
        "endpoint": endpoint,
        "model": model,
        "request_sha256": _sha(request_raw),
        "response_sha256": _sha(response_raw),
        "strict_json_schema": True,
        "thinking_off_checked": True,
        "physical_paper_observation": False,
        "model_weights_attested": False,
        "world_qualified": False,
        "actual_requests": 1,
        "max_tokens": GEMMA_MAX_COMPLETION,
        "chat_template_kwargs": {"enable_thinking": False},
        "reasoning_effort": "none",
    }
    target = evidence_root / REPORT_FILENAME
    with target.open("x", encoding="utf-8") as stream:
        json.dump(report, stream, ensure_ascii=False, sort_keys=True, indent=2)
        stream.flush()
        os.fsync(stream.fileno())
    verify_preflight_report(target, endpoint=endpoint, model=model)
    return report


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--endpoint", required=True)
    parser.add_argument("--model", required=True)
    parser.add_argument("--evidence-root", type=Path, required=True)
    args = parser.parse_args()
    if os.environ.get("L_MP11_GEMMA_PREFLIGHT_DEV") != "1":
        parser.error("real HTTP preflight requires L_MP11_GEMMA_PREFLIGHT_DEV=1")
    print(json.dumps(run(args.endpoint, args.model, args.evidence_root),
                     ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
