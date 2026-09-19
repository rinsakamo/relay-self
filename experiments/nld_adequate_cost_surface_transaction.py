from __future__ import annotations

import argparse
from pathlib import Path

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


def build_command(
    *,
    model_id: str,
    output_path: Path,
    run: bool,
) -> list[str]:
    import sys

    command = [
        sys.executable,
        "-B",
        "-m",
        "experiments.nld_adequate_cost_surface",
    ]
    if run:
        command.append("--run")
    command.extend(
        [
            "--model",
            model_id,
            "--dtype",
            "bf16",
            "--seed",
            "1",
            "--output",
            str(output_path),
        ]
    )
    return command


def validate_payload(
    payload: object,
    *,
    model_id: str,
) -> dict[str, object]:
    if not isinstance(payload, dict):
        raise PhysicalTransactionError(
            "adequate cost evidence must be a JSON object"
        )
    if payload.get("evidence_class") != (
        "actual-model adequate cost surface"
    ):
        raise PhysicalTransactionError(
            "adequate cost payload has wrong evidence class"
        )
    if payload.get("model_id") != model_id:
        raise PhysicalTransactionError(
            "adequate cost model id does not match"
        )
    if payload.get("dtype") != "bf16":
        raise PhysicalTransactionError(
            "adequate cost run did not use bf16"
        )

    methods = payload.get("method_availability")
    if not isinstance(methods, dict):
        raise PhysicalTransactionError(
            "method_availability is missing"
        )
    modes = ("ar", "dlm", "linear_spec")
    if any(methods.get(mode) is not True for mode in modes):
        raise PhysicalTransactionError(
            "one or more native methods are unavailable"
        )

    warmup = payload.get("warmup")
    if not isinstance(warmup, list) or len(warmup) != 3:
        raise PhysicalTransactionError(
            "adequate cost run requires three warm-ups"
        )

    observations = payload.get("observations")
    if not isinstance(observations, list):
        raise PhysicalTransactionError(
            "observations must be a list"
        )
    if len(observations) != 72:
        raise PhysicalTransactionError(
            f"expected 72 observations; found {len(observations)}"
        )

    cells: dict[tuple[str, str], list[dict[str, object]]] = {}
    for item in observations:
        if not isinstance(item, dict):
            raise PhysicalTransactionError(
                "observation must be a JSON object"
            )
        case_id = item.get("case_id")
        mode = item.get("mode")
        if not isinstance(case_id, str) or mode not in modes:
            raise PhysicalTransactionError(
                "unexpected case or mode"
            )
        cells.setdefault((case_id, str(mode)), []).append(item)

    if len(cells) != 12:
        raise PhysicalTransactionError(
            f"expected 12 case/mode cells; found {len(cells)}"
        )
    for key, rows in cells.items():
        if len(rows) != 6:
            raise PhysicalTransactionError(
                f"{key!r} expected 6 rows; found {len(rows)}"
            )
        for position in (1, 2, 3):
            count = sum(
                row.get("ordinal_position") == position
                for row in rows
            )
            if count != 2:
                raise PhysicalTransactionError(
                    f"{key!r} position {position} expected 2; "
                    f"found {count}"
                )

    summary = payload.get("summary")
    if not isinstance(summary, dict):
        raise PhysicalTransactionError("summary is missing")
    overall = summary.get("overall_by_mode")
    if not isinstance(overall, dict):
        raise PhysicalTransactionError(
            "overall_by_mode summary is missing"
        )

    return {
        "model_id": model_id,
        "gpu_name": payload.get("gpu_name"),
        "torch_version": payload.get("torch_version"),
        "transformers_version": payload.get("transformers_version"),
        "warm_cache_load_elapsed_seconds": payload.get(
            "load_elapsed_seconds"
        ),
        "measured_observation_count": len(observations),
        "cost_comparison_eligible": summary.get(
            "cost_comparison_eligible"
        ),
        "overall_by_mode": overall,
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
        "qualification_scope": "nld_adequate_cost_surface",
        "canonical_runtime": {
            "engine": "pytorch_transformers_direct",
            "dtype": "bf16",
            "case_count": 4,
            "modes": ["ar", "dlm", "linear_spec"],
            "warmup_calls_per_mode": 1,
            "measured_call_count": 72,
            "cuda_synchronized_timing": True,
            "lora": False,
            "quantization": None,
            "serving_framework": None,
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

        stage = "dry_run"
        summary["current_stage"] = stage
        _write_json(summary_path, summary)
        dry_output = evidence_root / "dry-run.json"
        dry_command = build_command(
            model_id=model_id,
            output_path=dry_output,
            run=False,
        )
        summary["dry_run_command"] = dry_command
        returncode = _run_probe_command(
            dry_command,
            repo_root=repo_root,
            stdout_path=evidence_root / "dry-run.stdout.txt",
            stderr_path=evidence_root / "dry-run.stderr.txt",
            timeout_seconds=timeout_seconds,
        )
        if returncode != 0:
            raise PhysicalTransactionError(
                f"adequate-cost dry run exited with code {returncode}"
            )
        dry_payload = _load_json(dry_output)
        if (
            not isinstance(dry_payload, dict)
            or dry_payload.get("evidence_class")
            != "adequate cost surface plan only"
        ):
            raise PhysicalTransactionError(
                "dry-run output has wrong evidence class"
            )
        _complete_stage(summary, stage)
        _write_json(summary_path, summary)

        stage = "actual_model"
        summary["current_stage"] = stage
        _write_json(summary_path, summary)
        actual_output = evidence_root / "actual-model.json"
        actual_command = build_command(
            model_id=model_id,
            output_path=actual_output,
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
                f"actual adequate-cost run exited with code {returncode}"
            )

        actual_payload = _load_json(actual_output)
        summary["observation"] = validate_payload(
            actual_payload,
            model_id=model_id,
        )
        _complete_stage(summary, stage)

        summary["status"] = "ADEQUATE_COST_SURFACE_PASS"
        summary["non_claims"] = [
            "PASS means a structurally valid physical trace was recorded.",
            "Cost comparison is conditional on fresh matched adequacy.",
            "No weighted total cognition score is defined.",
            "No permanent mode selector is promoted.",
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
    default_repo_root = Path(__file__).resolve().parents[1]
    parser = argparse.ArgumentParser(
        description="Run the NLD matched-adequacy cost transaction."
    )
    parser.add_argument(
        "--repo-root",
        type=Path,
        default=default_repo_root,
    )
    parser.add_argument(
        "--evidence-root",
        type=Path,
        required=True,
    )
    parser.add_argument("--model", default=DEFAULT_MODEL_ID)
    parser.add_argument(
        "--timeout-seconds",
        type=float,
        default=DEFAULT_TIMEOUT_SECONDS,
    )
    args = parser.parse_args()

    try:
        result = run_transaction(
            repo_root=args.repo_root.resolve(),
            evidence_root=args.evidence_root,
            model_id=args.model,
            timeout_seconds=args.timeout_seconds,
        )
    except PhysicalTransactionError as exc:
        parser.error(str(exc))

    raise SystemExit(result)


if __name__ == "__main__":
    main()
