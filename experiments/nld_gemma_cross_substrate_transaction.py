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
