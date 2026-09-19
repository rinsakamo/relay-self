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
    artifact_output_path: Path | None,
    run: bool,
) -> list[str]:
    command = [
        sys.executable,
        "-B",
        "-m",
        "experiments.gemma_flee_crystallization",
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
    if artifact_output_path is not None:
        command.extend(
            [
                "--artifact-output",
                str(artifact_output_path),
            ]
        )
    return command


def validate_payload(payload: object) -> dict[str, object]:
    if not isinstance(payload, dict):
        raise PhysicalTransactionError(
            "crystallization evidence must be a JSON object"
        )
    if payload.get("evidence_class") != (
        "actual-model gemma flee crystallization"
    ):
        raise PhysicalTransactionError(
            "crystallization evidence class is incorrect"
        )

    induction = payload.get("induction")
    if not isinstance(induction, dict):
        raise PhysicalTransactionError(
            "crystallization induction evidence is missing"
        )

    baseline = induction.get("baseline_episodes")
    if not isinstance(baseline, list) or len(baseline) != 4:
        count = len(baseline) if isinstance(baseline, list) else "non-list"
        raise PhysicalTransactionError(
            f"expected 4 training baseline episodes; found {count}"
        )

    trials = induction.get("ablation_trials")
    if not isinstance(trials, list):
        raise PhysicalTransactionError(
            "ablation_trials must be a list"
        )
    baseline_qualified = induction.get("baseline_qualified")
    if baseline_qualified is True and len(trials) != 22:
        raise PhysicalTransactionError(
            "qualified induction must contain 22 ablation trials"
        )
    if baseline_qualified is False and trials:
        raise PhysicalTransactionError(
            "unqualified induction must not continue ablation"
        )

    artifact = induction.get("artifact")
    if not isinstance(artifact, dict):
        raise PhysicalTransactionError(
            "crystallization artifact is missing"
        )
    retained = artifact.get("retained_context_keys")
    removed = artifact.get("removed_context_keys")
    if (
        not isinstance(retained, list)
        or not all(isinstance(key, str) for key in retained)
        or not isinstance(removed, list)
        or not all(isinstance(key, str) for key in removed)
    ):
        raise PhysicalTransactionError(
            "artifact key lists are invalid"
        )
    if set(retained) & set(removed):
        raise PhysicalTransactionError(
            "artifact retained/removed key sets overlap"
        )
    if len(retained) + len(removed) != 22:
        raise PhysicalTransactionError(
            "artifact must account for all 22 training context keys"
        )

    holdout = payload.get("holdout")
    if not isinstance(holdout, dict):
        raise PhysicalTransactionError(
            "holdout evidence is missing"
        )
    observations = holdout.get("observations")
    if not isinstance(observations, list) or len(observations) != 48:
        count = len(observations) if isinstance(observations, list) else "non-list"
        raise PhysicalTransactionError(
            f"expected 48 holdout episodes; found {count}"
        )

    cell_counts: dict[tuple[str, str], int] = {}
    expected_conditions = {"before", "after"}
    for row in observations:
        if not isinstance(row, dict):
            raise PhysicalTransactionError(
                "holdout episode must be an object"
            )
        case_id = row.get("case_id")
        condition = row.get("condition")
        if not isinstance(case_id, str):
            raise PhysicalTransactionError(
                "holdout case_id must be text"
            )
        if condition not in expected_conditions:
            raise PhysicalTransactionError(
                f"unexpected holdout condition: {condition!r}"
            )
        key = (case_id, str(condition))
        cell_counts[key] = cell_counts.get(key, 0) + 1
        calls = row.get("provider_calls")
        if not isinstance(calls, list) or len(calls) not in {1, 2}:
            raise PhysicalTransactionError(
                f"{key!r} must contain one or two provider calls"
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

    if len(cell_counts) != 8 or any(
        count != 6 for count in cell_counts.values()
    ):
        raise PhysicalTransactionError(
            "holdout must contain 8 case/condition cells with 6 episodes each"
        )

    holdout_summary = holdout.get("summary")
    if not isinstance(holdout_summary, dict):
        raise PhysicalTransactionError(
            "holdout summary is missing"
        )

    summary = payload.get("summary")
    if not isinstance(summary, dict):
        raise PhysicalTransactionError(
            "top-level crystallization summary is missing"
        )

    return {
        "artifact_induction_qualified": summary.get(
            "artifact_induction_qualified"
        ),
        "retained_context_key_count": summary.get(
            "retained_context_key_count"
        ),
        "removed_context_key_count": summary.get(
            "removed_context_key_count"
        ),
        "future_cost_comparison_eligible": summary.get(
            "future_cost_comparison_eligible"
        ),
        "acquisition_cost": induction.get("acquisition_cost"),
        "artifact": artifact,
        "holdout_by_condition": holdout_summary.get("by_condition"),
        "holdout_by_case_condition": holdout_summary.get(
            "by_case_condition"
        ),
    }
