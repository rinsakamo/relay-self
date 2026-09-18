from __future__ import annotations

import argparse
from pathlib import Path

from experiments.nld_reversed_mapping_token_budget_transaction import (
    build_budget_command,
    validate_budget_payload,
)
from experiments.nld_tri_mode_transaction import (
    DEFAULT_MODEL_ID,
    DEFAULT_TIMEOUT_SECONDS,
    PhysicalTransactionError,
    _collect_gpu_identity,
    _collect_python_environment,
    _load_json,
    _prepare_evidence_root,
    _require_clean_repo,
    _run_probe_command,
    _write_json,
)

FORMAT_VERSION = 1


def build_analysis_command(
    *,
    input_path: Path | None,
    output_path: Path,
) -> list[str]:
    import sys

    command = [
        sys.executable,
        "-B",
        "-m",
        "experiments.nld_native_path_trajectory",
    ]
    if input_path is not None:
        command.extend(["--input", str(input_path)])
    command.extend(["--output", str(output_path)])
    return command


def validate_analysis(payload: object) -> dict[str, object]:
    if not isinstance(payload, dict):
        raise PhysicalTransactionError(
            "trajectory analysis must be a JSON object"
        )
    if payload.get("evidence_class") != (
        "native output-token trajectory analysis"
    ):
        raise PhysicalTransactionError(
            "trajectory analysis has the wrong evidence class"
        )
    if payload.get("focus_case_id") != "reversed_ridge_open":
        raise PhysicalTransactionError(
            "trajectory analysis has the wrong focus case"
        )
    if payload.get("focus_max_new_tokens") != 32:
        raise PhysicalTransactionError(
            "trajectory analysis has the wrong token budget"
        )
    if payload.get("focus_observation_count") != 18:
        raise PhysicalTransactionError(
            "trajectory analysis must contain 18 focus observations"
        )

    summary = payload.get("summary_by_mode")
    if not isinstance(summary, dict):
        raise PhysicalTransactionError(
            "trajectory summary_by_mode is missing"
        )
    compact = {}
    for mode in ("ar", "dlm", "linear_spec"):
        row = summary.get(mode)
        if not isinstance(row, dict) or row.get("count") != 6:
            raise PhysicalTransactionError(
                f"trajectory mode summary invalid for {mode}"
            )
        compact[mode] = row

    pairwise = payload.get("pairwise_output_divergence")
    if not isinstance(pairwise, dict) or len(pairwise) != 3:
        raise PhysicalTransactionError(
            "trajectory pairwise divergence summary is incomplete"
        )

    return {
        "focus_case_id": payload.get("focus_case_id"),
        "focus_max_new_tokens": payload.get(
            "focus_max_new_tokens"
        ),
        "focus_observation_count": payload.get(
            "focus_observation_count"
        ),
        "summary_by_mode": compact,
        "pairwise_output_divergence": pairwise,
    }



def _initial_summary(
    *,
    repo_root: Path,
    evidence_root: Path,
    model_id: str,
) -> dict[str, object]:
    return {
        "format_version": FORMAT_VERSION,
        "status": "STARTED",
        "current_stage": None,
        "completed_stages": [],
        "repo_root": str(repo_root),
        "evidence_root": str(evidence_root),
        "model_id": model_id,
        "qualification_scope": "nld_native_output_token_trajectory",
        "physical_subject": {
            "source_apparatus": "reversed_mapping_token_budget",
            "measured_call_count": 72,
            "focus_case_id": "reversed_ridge_open",
            "focus_max_new_tokens": 32,
            "focus_observation_count": 18,
        },
    }


def _complete_stage(
    summary: dict[str, object],
    stage: str,
) -> None:
    completed = summary.get("completed_stages")
    if not isinstance(completed, list):
        raise AssertionError("completed_stages must be a list")
    completed.append(stage)
    summary["current_stage"] = None



def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--evidence-root", type=Path, required=True)
    parser.parse_args()


if __name__ == "__main__":
    main()
