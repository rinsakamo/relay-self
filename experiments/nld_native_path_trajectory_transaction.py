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




def run_transaction(
    *,
    repo_root: Path,
    evidence_root: Path,
    model_id: str,
    timeout_seconds: float,
) -> int:
    if timeout_seconds <= 0:
        raise PhysicalTransactionError(
            "timeout_seconds must be positive"
        )

    evidence_root = _prepare_evidence_root(evidence_root)
    summary_path = evidence_root / "summary.json"
    summary = _initial_summary(
        repo_root=repo_root,
        evidence_root=evidence_root,
        model_id=model_id,
    )
    _write_json(summary_path, summary)

    try:
        stage = "repo_preflight"
        summary["current_stage"] = stage
        _write_json(summary_path, summary)
        head, tree, branch_name = _require_clean_repo(repo_root)
        summary["git"] = {
            "head": head,
            "tree": tree,
            "branch": branch_name,
        }
        _complete_stage(summary, stage)
        _write_json(summary_path, summary)

        stage = "gpu_preflight"
        summary["current_stage"] = stage
        _write_json(summary_path, summary)
        summary["gpu"] = _collect_gpu_identity()
        _complete_stage(summary, stage)
        _write_json(summary_path, summary)

        stage = "python_preflight"
        summary["current_stage"] = stage
        _write_json(summary_path, summary)
        summary["python_environment"] = _collect_python_environment()
        _complete_stage(summary, stage)
        _write_json(summary_path, summary)

        stage = "analysis_dry_run"
        summary["current_stage"] = stage
        _write_json(summary_path, summary)
        dry_output = evidence_root / "trajectory-plan.json"
        dry_command = build_analysis_command(
            input_path=None,
            output_path=dry_output,
        )
        summary["analysis_dry_run_command"] = dry_command
        returncode = _run_probe_command(
            dry_command,
            repo_root=repo_root,
            stdout_path=evidence_root / "trajectory-plan.stdout.txt",
            stderr_path=evidence_root / "trajectory-plan.stderr.txt",
            timeout_seconds=timeout_seconds,
        )
        if returncode != 0:
            raise PhysicalTransactionError(
                f"trajectory dry run exited with code {returncode}"
            )
        _complete_stage(summary, stage)
        _write_json(summary_path, summary)

        stage = "actual_model"
        summary["current_stage"] = stage
        _write_json(summary_path, summary)
        raw_output = evidence_root / "actual-model.json"
        actual_command = build_budget_command(
            model_id=model_id,
            output_path=raw_output,
            run=True,
        )
        summary["actual_model_command"] = actual_command
        returncode = _run_probe_command(
            actual_command,
            repo_root=repo_root,
            stdout_path=evidence_root / "actual-model.stdout.txt",
            stderr_path=evidence_root / "actual-model.stderr.txt",
            timeout_seconds=timeout_seconds,
        )
        summary["actual_model_returncode"] = returncode
        if returncode != 0:
            raise PhysicalTransactionError(
                f"actual model run exited with code {returncode}"
            )
        raw_payload = _load_json(raw_output)
        summary["source_observation"] = validate_budget_payload(
            raw_payload,
            model_id=model_id,
        )
        _complete_stage(summary, stage)
        _write_json(summary_path, summary)

        stage = "trajectory_analysis"
        summary["current_stage"] = stage
        _write_json(summary_path, summary)
        analysis_output = evidence_root / "trajectory-analysis.json"
        analysis_command = build_analysis_command(
            input_path=raw_output,
            output_path=analysis_output,
        )
        summary["trajectory_analysis_command"] = analysis_command
        returncode = _run_probe_command(
            analysis_command,
            repo_root=repo_root,
            stdout_path=evidence_root / "trajectory-analysis.stdout.txt",
            stderr_path=evidence_root / "trajectory-analysis.stderr.txt",
            timeout_seconds=timeout_seconds,
        )
        if returncode != 0:
            raise PhysicalTransactionError(
                f"trajectory analysis exited with code {returncode}"
            )
        analysis_payload = _load_json(analysis_output)
        summary["trajectory"] = validate_analysis(analysis_payload)
        _complete_stage(summary, stage)

        summary["status"] = "NATIVE_OUTPUT_TRAJECTORY_PASS"
        summary["non_claims"] = [
            "PASS means fresh native output-token trajectory evidence was recorded.",
            "The analysis does not expose hidden states or prove a causal mechanism.",
            "The full 72-call source trace remains the physical evidence surface.",
            "Model output is not World truth or Action authorization.",
        ]
        _write_json(summary_path, summary)
        return 0

    except PhysicalTransactionError as exc:
        summary["status"] = "FAIL_NOT_QUALIFIED"
        summary["failure_stage"] = summary.get("current_stage")
        summary["failure_reason"] = str(exc)
        summary["current_stage"] = None
        _write_json(summary_path, summary)
        return 2



def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--evidence-root", type=Path, required=True)
    parser.parse_args()


if __name__ == "__main__":
    main()
