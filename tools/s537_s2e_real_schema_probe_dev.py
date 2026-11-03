"""S #537 S2-E: bounded *one* real schema HTTP probe, before Minecraft.

An independently authorized local-only DEV diagnostic. The original S60-B1
strict response validator is reused. This tool never starts or stops a model,
creates a World, issues an Action, or grants cognition/learning authority.
"""
from __future__ import annotations

import argparse
import asyncio
import hashlib
import http.client
import json
import os
from pathlib import Path

from adapters.mineflayer.s57_owned_llama_backend import OwnedBackendSpec
from adapters.mineflayer.s60b1_loopback_adapter import (
    LoopbackDisplacementAdapter,
    LoopbackTransportConfig,
    TransportUnconfirmed,
    structured_review_format,
)
from tools.s537_s2d_model_preflight import verify_running_backend

REQUEST_LIMIT = 65536
RESPONSE_LIMIT = 131072


def probe_payload(model: str, max_tokens: int) -> dict[str, object]:
    """Use the very same strict S60 schema source; no World-derived contents."""
    if not isinstance(model, str) or not 1 <= max_tokens <= 256:
        raise ValueError("invalid probe budget")
    return {
        "model": model,
        "messages": [
            {"role": "system", "content": (
                "You are a read-only Minecraft observation reviewer. "
                "Return only the strict JSON object requested by the schema, "
                "with status ADVISORY or DEFER, observation, uncertainty. "
                "No actions, markdown, or reasoning text."
            )},
            {"role": "user", "content": (
                "Synthetic, not a real World observation: previous motion "
                "has completed. State that the next movement is uncertain. "
                "Do not issue commands."
            )},
        ],
        "stream": False,
        "temperature": 0,
        "max_tokens": max_tokens,
        "response_format": structured_review_format(),
    }


def assert_build10874_shape(payload: dict[str, object]) -> None:
    """Fail before HTTP when nested schema, required keys, or bounds drift."""
    fmt = payload.get("response_format")
    if not isinstance(fmt, dict) or set(fmt) != {"type", "json_schema"}:
        raise ValueError("response_format wrapper mismatch")
    if fmt["type"] != "json_schema":
        raise ValueError("schema mode unavailable")
    wrapper = fmt["json_schema"]
    if not isinstance(wrapper, dict) or set(wrapper) != {"schema"}:
        raise ValueError("build10874 nested schema missing")
    schema = wrapper["schema"]
    if (
        not isinstance(schema, dict)
        or schema != structured_review_format()["json_schema"]["schema"]
        or schema.get("additionalProperties") is not False
        or set(schema.get("required", [])) != {
            "status", "observation", "uncertainty",
        }
    ):
        raise ValueError("unbounded or unexpected schema")


def probe_once(
    *,
    model: str, port: int, max_tokens: int, timeout_s: float,
) -> tuple[int, bytes, bytes]:
    """One localhost POST. No retry, fallback, polling, or redirected request."""
    if not 0 < timeout_s <= 60:
        raise ValueError("invalid timeout")
    cfg = LoopbackTransportConfig(
        model=model, port=port, max_tokens=max_tokens, whole_s=timeout_s,
        read_s=min(timeout_s, 15.0), structured_json=True,
    )
    payload = probe_payload(model, max_tokens)
    assert_build10874_shape(payload)
    data = json.dumps(payload, ensure_ascii=False, allow_nan=False).encode("utf-8")
    if len(data) > REQUEST_LIMIT:
        raise ValueError("request too large")
    conn = http.client.HTTPConnection("127.0.0.1", port, timeout=timeout_s)
    try:
        conn.request(
            "POST", "/v1/chat/completions", body=data,
            headers={"Content-Type": "application/json", "Accept": "application/json"},
        )
        response = conn.getresponse()
        status = response.status
        raw = response.read(RESPONSE_LIMIT + 1)
    finally:
        conn.close()
    return status, data, raw


def validate_completion(model: str, port: int, max_tokens: int, raw: bytes) -> dict:
    """Use original S60-B1 response validator with the exact strict schema."""
    cfg = LoopbackTransportConfig(
        model=model, port=port, max_tokens=max_tokens, structured_json=True,
    )
    async def validate() -> str:
        adapter = LoopbackDisplacementAdapter(cfg, lambda _request: {})
        return adapter._validate_response(raw, max_tokens)

    return json.loads(asyncio.run(validate()))

def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--model-pid", type=int, required=True)
    parser.add_argument("--llama-server", type=Path, required=True)
    parser.add_argument("--binary-sha256", required=True)
    parser.add_argument("--gguf", type=Path, required=True)
    parser.add_argument("--gguf-sha256", required=True)
    parser.add_argument("--model-alias", required=True)
    parser.add_argument("--model-port", type=int, required=True)
    parser.add_argument("--gpu-layers", type=int, required=True)
    parser.add_argument("--max-tokens", type=int, default=128)
    parser.add_argument("--timeout-s", type=float, default=45.0)
    parser.add_argument("--evidence-dir", type=Path, required=True)
    parser.add_argument("--one-shot-dev", action="store_true")
    args = parser.parse_args()

    if not (
        args.one_shot_dev
        and os.environ.get("S537_S2E_SCHEMA_PROBE_DEV_ONLY") == "1"
        and os.environ.get("GITHUB_ACTIONS") != "true"
        and not os.environ.get("NODE_OPTIONS")
    ):
        print(json.dumps({"status": "BLOCKED", "reason": "explicit_local_dev_grant_missing"}))
        return 2
    output = args.evidence_dir
    if (
        not output.is_absolute() or output.is_symlink() or output.exists()
        or not output.parent.is_dir() or output.parent.is_symlink()
    ):
        print(json.dumps({"status": "BLOCKED", "reason": "fresh_absolute_evidence_dir_required"}))
        return 2
    try:
        spec = OwnedBackendSpec(
            binary=args.llama_server, gguf=args.gguf,
            binary_sha256=args.binary_sha256,
            gguf_sha256=args.gguf_sha256,
            alias=args.model_alias, port=args.model_port,
            gpu_layers=args.gpu_layers, ctx_size=8192,
            inference_parallel=1,
        )
        assert_build10874_shape(probe_payload(args.model_alias, args.max_tokens))
        identity = verify_running_backend(spec, pid=args.model_pid)
    except (OSError, TypeError, ValueError) as exc:
        print(json.dumps({
            "status": "BLOCKED_PREWORLD", "reason": "model_or_schema_preflight_rejected",
            "detail": type(exc).__name__,
        }))
        return 2

    # A preflight-verified owned process can still fail or exit during the POST.
    # Pre-create evidence before any network operation, preserving failed attempts.
    output.mkdir(mode=0o700)
    report: dict[str, object] = {
        "schema": "S537_S2E_REAL_HTTP_PROBE_V1",
        "classification": "DEV_ONLY",
        "status": "POST_NOT_STARTED",
        "model_identity_preworld": identity,
        "model_http_attempts": 0,
        "http_completion_observed": False,
        "structured_response_validated": False,
        "worlds": 0,
        "actions": 0,
        "learning_updates": 0,
        "energy_debits": 0,
        "source_attested": False,
        "backend_stop_ack": False,
        "gpu_release_verified": False,
        "qualification": "NO_GO",
        "science": "NOT_RUN",
    }
    request_data = b""
    response_data = b""
    try:
        # Record one attempt before the call; a broken connection is still an attempt.
        report["model_http_attempts"] = 1
        report["status"] = "HTTP_ATTEMPTED_UNCONFIRMED"
        http_status, request_data, response_data = probe_once(
            model=args.model_alias, port=args.model_port,
            max_tokens=args.max_tokens, timeout_s=args.timeout_s,
        )
        report["http_completion_observed"] = True
        report["http_status"] = http_status
        report["response_oversized"] = len(response_data) > RESPONSE_LIMIT
        if http_status != 200 or report["response_oversized"]:
            report["status"] = "HTTP_COMPLETED_UNQUALIFIED"
        else:
            report["status"] = "HTTP_COMPLETED_SCHEMA_REJECTED"
            report["review"] = validate_completion(
                args.model_alias, args.model_port, args.max_tokens, response_data,
            )
            report["status"] = "HTTP_VALIDATED_READ_ONLY"
            report["structured_response_validated"] = True
    except (OSError, TimeoutError, ValueError, TransportUnconfirmed) as exc:
        report["reason"] = type(exc).__name__
    finally:
        # Local client disconnect is not a backend STOP or GPU release.
        (output / "request.json").write_bytes(request_data)
        (output / "response.raw").write_bytes(response_data)
        (output / "result.json").write_text(
            json.dumps(report, ensure_ascii=False, sort_keys=True, indent=2) + "\n",
            encoding="utf-8",
        )
        names = ("request.json", "response.raw", "result.json")
        (output / "SHA256SUMS").write_text(
            "".join(f"{_sha(output / name)}  {name}\n" for name in names),
            encoding="utf-8",
        )
    print(json.dumps({
        "status": report["status"],
        "evidence_dir": str(output),
        "worlds": 0,
        "http_attempts": report["model_http_attempts"],
    }))
    return 0 if report["structured_response_validated"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
