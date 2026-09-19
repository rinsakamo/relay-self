from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path

from experiments.mineflayer_cognition_llama_cpp_transaction import (
    DEFAULT_HOST,
    DEFAULT_PORT,
    EXPECTED_GGUF_SHA256,
    PhysicalTransactionError,
    _collect_gpu_identity,
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
from experiments.nld_gemma_cross_substrate_transaction import (
    _gpu_memory_used_mib,
)
from experiments.nld_tri_mode_transaction import (
    DEFAULT_TIMEOUT_SECONDS,
    _load_json,
    _prepare_evidence_root,
    _run_probe_command,
    _write_json,
)

FORMAT_VERSION = 1


def _experiment_command(
    *,
    endpoint: str,
    model: str,
    timeout: float,
    output_path: Path,
    run: bool,
) -> list[str]:
    command = [
        sys.executable,
        "-B",
        "-m",
        "experiments.gemma_skill_narrowing",
    ]
    if run:
        command.append("--run")
    command.extend(
        [
            "--endpoint",
            endpoint,
            "--model",
            model,
            "--timeout",
            str(timeout),
            "--output",
            str(output_path),
        ]
    )
    return command


def validate_payload(payload: object) -> dict[str, object]:
    if not isinstance(payload, dict):
        raise PhysicalTransactionError(
            "Gemma narrowing evidence must be a JSON object"
        )
    if payload.get("evidence_class") != (
        "actual-model gemma skill narrowing"
    ):
        raise PhysicalTransactionError(
            "Gemma narrowing evidence class is incorrect"
        )

    observations = payload.get("observations")
    if not isinstance(observations, list) or len(observations) != 48:
        count = len(observations) if isinstance(observations, list) else "non-list"
        raise PhysicalTransactionError(
            f"expected 48 measured episodes; found {count}"
        )

    expected_cases = {
        "cave_only",
        "ridge_only",
        "both_cave_shelter",
        "both_ridge_shelter",
    }
    expected_conditions = {"broad", "narrow"}
    cell_counts: dict[tuple[str, str], int] = {}

    for row in observations:
        if not isinstance(row, dict):
            raise PhysicalTransactionError(
                "measured episode must be a JSON object"
            )
        case_id = row.get("case_id")
        condition = row.get("condition")
        if case_id not in expected_cases:
            raise PhysicalTransactionError(
                f"unexpected case_id: {case_id!r}"
            )
        if condition not in expected_conditions:
            raise PhysicalTransactionError(
                f"unexpected condition: {condition!r}"
            )
        key = (str(case_id), str(condition))
        cell_counts[key] = cell_counts.get(key, 0) + 1

        calls = row.get("provider_calls")
        if not isinstance(calls, list) or len(calls) not in {1, 2}:
            raise PhysicalTransactionError(
                f"{key!r} episode must contain one or two provider calls"
            )
        for call in calls:
            if not isinstance(call, dict):
                raise PhysicalTransactionError(
                    "provider call record must be an object"
                )
            if not isinstance(call.get("prompt_tokens"), int):
                raise PhysicalTransactionError(
                    "provider call is missing prompt_tokens"
                )
            if not isinstance(call.get("completion_tokens"), int):
                raise PhysicalTransactionError(
                    "provider call is missing completion_tokens"
                )
            if not isinstance(call.get("elapsed_seconds"), (int, float)):
                raise PhysicalTransactionError(
                    "provider call is missing elapsed_seconds"
                )

    if len(cell_counts) != 8:
        raise PhysicalTransactionError(
            f"expected 8 case/condition cells; found {len(cell_counts)}"
        )
    for key, count in cell_counts.items():
        if count != 6:
            raise PhysicalTransactionError(
                f"{key!r} expected 6 episodes; found {count}"
            )

    summary = payload.get("summary")
    if not isinstance(summary, dict):
        raise PhysicalTransactionError("summary is missing")
    by_condition = summary.get("by_condition")
    if not isinstance(by_condition, dict):
        raise PhysicalTransactionError(
            "by_condition summary is missing"
        )
    for condition in expected_conditions:
        subject = by_condition.get(condition)
        if not isinstance(subject, dict) or subject.get("count") != 24:
            raise PhysicalTransactionError(
                f"{condition} summary must contain 24 episodes"
            )

    return {
        "measured_episode_count": len(observations),
        "cost_comparison_eligible": summary.get(
            "cost_comparison_eligible"
        ),
        "by_condition": by_condition,
        "by_case_condition": summary.get("by_case_condition"),
    }
