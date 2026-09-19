from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

from experiments.mineflayer_cognition_llama_cpp_transaction import (
    DEFAULT_HOST,
    DEFAULT_PORT,
    EXPECTED_GGUF_SHA256,
    PhysicalTransactionError,
    _collect_llama_revision,
    _collect_server_version,
    _port_is_free,
    _probe_and_attest,
    _require_clean_repo,
    _require_llama_cpp_paths,
    _server_command,
    _start_server,
    _terminate_owned_process,
    _verify_artifact,
    _wait_until_ready,
)
from experiments.nld_adequate_cost_surface import (
    build_cost_cases,
)
from experiments.nld_lexical_remapping_generalization import (
    parsed_destination,
)
from experiments.nld_linear_spec_matched import (
    build_schedule,
)
from experiments.nld_tri_mode import (
    DEFAULT_MODEL_ID,
    parse_decision,
)
from experiments.nld_tri_mode_repeatability import _numeric_summary
from experiments.nld_tri_mode_transaction import (
    DEFAULT_TIMEOUT_SECONDS,
    _load_json,
    _prepare_evidence_root,
    _run_probe_command,
    _write_json,
)

FORMAT_VERSION = 1
GEMMA_MAX_TOKENS = 32
GEMMA_TEMPERATURE = 0
GEMMA_SEED = 1


def _canonical_json(value: object) -> str:
    return json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    )


def _sha256_json(value: object) -> str:
    return hashlib.sha256(
        _canonical_json(value).encode("utf-8")
    ).hexdigest()


def _gpu_memory_used_mib() -> int:
    completed = subprocess.run(
        [
            "nvidia-smi",
            "--query-gpu=memory.used",
            "--format=csv,noheader,nounits",
        ],
        text=True,
        capture_output=True,
        check=False,
    )
    if completed.returncode != 0:
        raise PhysicalTransactionError(
            "nvidia-smi memory query failed"
        )
    first = completed.stdout.strip().splitlines()
    if not first:
        raise PhysicalTransactionError(
            "nvidia-smi returned no memory.used value"
        )
    try:
        return int(first[0].strip())
    except ValueError as exc:
        raise PhysicalTransactionError(
            "nvidia-smi memory.used is not an integer"
        ) from exc


def _post_json(
    url: str,
    payload: dict[str, object],
    *,
    timeout: float,
) -> dict[str, object]:
    request = urllib.request.Request(
        url,
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "Content-Type": "application/json",
            "Accept": "application/json",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(
            request,
            timeout=timeout,
        ) as response:
            decoded = json.loads(
                response.read().decode("utf-8")
            )
    except (
        urllib.error.URLError,
        TimeoutError,
        json.JSONDecodeError,
    ) as exc:
        raise PhysicalTransactionError(
            f"POST {url} failed: {exc}"
        ) from exc
    if not isinstance(decoded, dict):
        raise PhysicalTransactionError(
            f"POST {url} did not return a JSON object"
        )
    return decoded


def _response_content(response: dict[str, object]) -> str:
    choices = response.get("choices")
    if not isinstance(choices, list) or len(choices) != 1:
        raise PhysicalTransactionError(
            "chat response must contain exactly one choice"
        )
    choice = choices[0]
    if not isinstance(choice, dict):
        raise PhysicalTransactionError(
            "chat choice must be an object"
        )
    message = choice.get("message")
    if not isinstance(message, dict):
        raise PhysicalTransactionError(
            "chat choice message is missing"
        )
    content = message.get("content")
    if not isinstance(content, str):
        raise PhysicalTransactionError(
            "chat response content must be a string"
        )
    return content


def _completion_tokens(
    response: dict[str, object],
) -> int | None:
    usage = response.get("usage")
    if not isinstance(usage, dict):
        return None
    value = usage.get("completion_tokens")
    return value if isinstance(value, int) else None


def _gemma_request_body(
    *,
    model: str,
    prompt: str,
) -> dict[str, object]:
    return {
        "model": model,
        "messages": [{"role": "user", "content": prompt}],
        "temperature": GEMMA_TEMPERATURE,
        "max_tokens": GEMMA_MAX_TOKENS,
        "seed": GEMMA_SEED,
        "reasoning_effort": "none",
        "cache_prompt": False,
        "stream": False,
    }


def _run_gemma_observation(
    *,
    endpoint: str,
    model: str,
    case,
    timeout: float,
) -> dict[str, object]:
    request_body = _gemma_request_body(
        model=model,
        prompt=case.prompt,
    )
    started = time.perf_counter()
    response = _post_json(
        endpoint,
        request_body,
        timeout=timeout,
    )
    elapsed_seconds = time.perf_counter() - started
    generated_text = _response_content(response)
    parsed = parse_decision(generated_text)
    return {
        "case_id": case.case_id,
        "expected_label": case.expected_label,
        "feasible_destination": case.feasible_destination,
        "label_to_destination": case.label_to_destination,
        "elapsed_seconds": elapsed_seconds,
        "generated_text": generated_text,
        "completion_token_count": _completion_tokens(response),
        "parsed_label": parsed.label,
        "parse_source": parsed.source,
        "parsed_destination": parsed_destination(case, parsed.label),
        "decision_correct": parsed.label == case.expected_label,
        "request_hash": _sha256_json(request_body),
        "response_hash": _sha256_json(response),
        "usage": response.get("usage"),
        "timings": response.get("timings"),
        "finish_reason": (
            response["choices"][0].get("finish_reason")
            if isinstance(response.get("choices"), list)
            and response["choices"]
            and isinstance(response["choices"][0], dict)
            else None
        ),
    }


def _summarize_rows(
    rows: list[dict[str, object]],
    *,
    token_key: str,
) -> dict[str, object]:
    parse_sources: dict[str, int] = {}
    for row in rows:
        source = str(row.get("parse_source"))
        parse_sources[source] = parse_sources.get(source, 0) + 1
    return {
        "count": len(rows),
        "correct_count": sum(
            row.get("decision_correct") is True for row in rows
        ),
        "invalid_output_count": sum(
            row.get("parsed_label") is None for row in rows
        ),
        "parse_sources": dict(sorted(parse_sources.items())),
        "latency_seconds": _numeric_summary(
            row["elapsed_seconds"]
            for row in rows
            if isinstance(row.get("elapsed_seconds"), (int, float))
        ),
        "completion_token_count": _numeric_summary(
            row[token_key]
            for row in rows
            if isinstance(row.get(token_key), (int, float))
        ),
    }


def run_gemma_calls(
    *,
    endpoint: str,
    model: str,
    timeout: float,
) -> dict[str, object]:
    cases = {case.case_id: case for case in build_cost_cases()}
    first_case = next(iter(cases.values()))
    warmup = _run_gemma_observation(
        endpoint=endpoint,
        model=model,
        case=first_case,
        timeout=timeout,
    )
    warmup["warmup"] = True

    rows: list[dict[str, object]] = []
    for schedule_row in build_schedule():
        case = cases[str(schedule_row["case_id"])]
        row = _run_gemma_observation(
            endpoint=endpoint,
            model=model,
            case=case,
            timeout=timeout,
        )
        row.update(schedule_row)
        row["warmup"] = False
        rows.append(row)

    return {
        "evidence_class": "actual-model gemma llama-cpp matched comparison",
        "model": model,
        "warmup": warmup,
        "observations": rows,
        "summary": _summarize_rows(
            rows,
            token_key="completion_token_count",
        ),
    }
