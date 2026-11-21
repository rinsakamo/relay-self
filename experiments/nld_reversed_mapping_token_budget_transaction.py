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


def build_budget_command(
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
        "experiments.nld_reversed_mapping_token_budget",
    ]
    if run:
        command.append("--run")
    command.extend(
        [
            "--model",
            model_id,
            "--dtype",
            "bf16",
            "--max-thinking-tokens",
            "32",
            "--seed",
            "1",
            "--output",
            str(output_path),
        ]
    )
    return command


def validate_budget_payload(
    payload: object,
    *,
    model_id: str,
) -> dict[str, object]:
    if not isinstance(payload, dict):
        raise PhysicalTransactionError(
            "token-budget evidence must be a JSON object"
        )
    if payload.get("evidence_class") != (
        "actual-model reversed mapping token-budget isolation"
    ):
        raise PhysicalTransactionError(
            "token-budget payload has the wrong evidence class"
        )
    if payload.get("model_id") != model_id:
        raise PhysicalTransactionError("token-budget model id does not match")
    if payload.get("dtype") != "bf16":
        raise PhysicalTransactionError(
            "token-budget payload did not use canonical bf16"
        )
    if payload.get("token_budgets") != [32, 64]:
        raise PhysicalTransactionError(
            "token-budget payload must contain [32, 64]"
        )

    required_modes = ("ar", "dlm", "linear_spec")
    methods = payload.get("method_availability")
    if not isinstance(methods, dict):
        raise PhysicalTransactionError("method_availability is missing")
    unavailable = [
        mode for mode in required_modes if methods.get(mode) is not True
    ]
    if unavailable:
        raise PhysicalTransactionError(
            "native NLD methods unavailable: " + ", ".join(unavailable)
        )

    warmup = payload.get("warmup")
    if not isinstance(warmup, list) or len(warmup) != 6:
        raise PhysicalTransactionError(
            "token-budget payload requires six warm-up calls"
        )

    observations = payload.get("observations")
    if not isinstance(observations, list):
        raise PhysicalTransactionError("observations must be a list")
    if len(observations) != 72:
        raise PhysicalTransactionError(
            f"expected 72 measured observations; found {len(observations)}"
        )

    case_ids = ("reversed_cave_open", "reversed_ridge_open")
    cells: dict[tuple[str, int, str], list[dict[str, object]]] = {
        (case_id, budget, mode): []
        for case_id in case_ids
        for budget in (32, 64)
        for mode in required_modes
    }

    for item in observations:
        if not isinstance(item, dict):
            raise PhysicalTransactionError(
                "measured observation must be a JSON object"
            )
        key = (
            item.get("case_id"),
            item.get("max_new_tokens"),
            item.get("mode"),
        )
        if key not in cells:
            raise PhysicalTransactionError(
                f"unexpected token-budget cell: {key!r}"
            )
        if item.get("parse_source") not in {
            "explicit",
            "fallback",
            "none",
        }:
            raise PhysicalTransactionError(
                "parse_source must be explicit, fallback, or none"
            )
        if not isinstance(item.get("eos_reached"), bool):
            raise PhysicalTransactionError(
                "eos_reached must be boolean"
            )
        if not isinstance(
            item.get("reached_or_exceeded_effective_max_new_tokens"),
            bool,
        ):
            raise PhysicalTransactionError(
                "token-cap proxy must be boolean"
            )
        cells[key].append(item)

    for key, rows in cells.items():
        if len(rows) != 6:
            raise PhysicalTransactionError(
                f"{key!r} expected 6 observations; found {len(rows)}"
            )
        for position in (1, 2, 3):
            actual = sum(
                row.get("ordinal_position") == position for row in rows
            )
            if actual != 2:
                raise PhysicalTransactionError(
                    f"{key!r} position {position} expected 2 "
                    f"observations; found {actual}"
                )

    summaries = payload.get("summary_by_case")
    if not isinstance(summaries, dict):
        raise PhysicalTransactionError("summary_by_case is missing")

    compact_cases: dict[str, object] = {}
    for case_id in case_ids:
        case_summary = summaries.get(case_id)
        if not isinstance(case_summary, dict):
            raise PhysicalTransactionError(
                f"summary for {case_id} is missing"
            )
        budgets = case_summary.get("budgets")
        if not isinstance(budgets, dict):
            raise PhysicalTransactionError(
                f"budget summaries for {case_id} are missing"
            )

        compact_budgets: dict[str, object] = {}
        for budget in ("32", "64"):
            budget_summary = budgets.get(budget)
            if not isinstance(budget_summary, dict):
                raise PhysicalTransactionError(
                    f"summary for {case_id}/{budget} is missing"
                )
            modes = budget_summary.get("modes")
            if not isinstance(modes, dict):
                raise PhysicalTransactionError(
                    f"mode summaries for {case_id}/{budget} are missing"
                )
            compact_modes: dict[str, object] = {}
            for mode in required_modes:
                mode_summary = modes.get(mode)
                if not isinstance(mode_summary, dict):
                    raise PhysicalTransactionError(
                        f"summary for {case_id}/{budget}/{mode} is missing"
                    )
                compact_modes[mode] = {
                    key: mode_summary.get(key)
                    for key in (
                        "count",
                        "correct_count",
                        "invalid_output_count",
                        "observed_labels",
                        "observed_destinations",
                        "parse_sources",
                        "explicit_labels",
                        "fallback_labels",
                        "eos_reached",
                        "token_cap_proxy",
                        "latency_seconds",
                        "nfe",
                        "generated_token_count",
                        "tokens_per_forward",
                        "cuda_peak_allocated_bytes",
                        "latency_by_ordinal_position",
                    )
                }
            compact_budgets[budget] = {
                "observation_count": budget_summary.get(
                    "observation_count"
                ),
                "modes": compact_modes,
            }

        compact_cases[case_id] = {
            "expected_label": case_summary.get("expected_label"),
            "feasible_destination": case_summary.get(
                "feasible_destination"
            ),
            "label_to_destination": case_summary.get(
                "label_to_destination"
            ),
            "route_evidence": case_summary.get("route_evidence"),
            "budgets": compact_budgets,
        }

    return {
        "model_id": model_id,
        "dtype": payload.get("dtype"),
        "gpu_name": payload.get("gpu_name"),
        "torch_version": payload.get("torch_version"),
        "transformers_version": payload.get("transformers_version"),
        "warm_cache_load_elapsed_seconds": payload.get(
            "load_elapsed_seconds"
        ),
        "cuda_before_load": payload.get("cuda_before_load"),
        "cuda_after_load": payload.get("cuda_after_load"),
        "measured_observation_count": len(observations),
        "cases": compact_cases,
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
        "qualification_scope": "nld_reversed_mapping_token_budget",
        "canonical_runtime": {
            "engine": "pytorch_transformers_direct",
            "dtype": "bf16",
            "cases": [
                "reversed_cave_open",
                "reversed_ridge_open",
            ],
            "max_new_tokens": [32, 64],
            "modes": ["ar", "dlm", "linear_spec"],
            "warmup_call_count": 6,
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
        head, tree, branch = _require_clean_repo(repo_root)
        summary["git"] = {
            "head": head,
            "tree": tree,
            "branch": branch,
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
        dry_command = build_budget_command(
            model_id=model_id,
            output_path=dry_output,
            run=False,
        )
        summary["dry_run_command"] = dry_command
        dry_returncode = _run_probe_command(
            dry_command,
            repo_root=repo_root,
            stdout_path=evidence_root / "dry-run.stdout.txt",
            stderr_path=evidence_root / "dry-run.stderr.txt",
            timeout_seconds=timeout_seconds,
        )
        if dry_returncode != 0:
            raise PhysicalTransactionError(
                f"dry-run token-budget probe exited with code {dry_returncode}"
            )
        dry_payload = _load_json(dry_output)
        if (
            not isinstance(dry_payload, dict)
            or dry_payload.get("evidence_class")
            != "reversed mapping token-budget plan only"
        ):
            raise PhysicalTransactionError(
                "dry-run output has the wrong evidence class"
            )
        _complete_stage(summary, stage)
        _write_json(summary_path, summary)

        stage = "actual_model"
        summary["current_stage"] = stage
        _write_json(summary_path, summary)
        actual_output = evidence_root / "actual-model.json"
        actual_command = build_budget_command(
            model_id=model_id,
            output_path=actual_output,
            run=True,
        )
        summary["actual_model_command"] = actual_command
        actual_returncode = _run_probe_command(
            actual_command,
            repo_root=repo_root,
            stdout_path=evidence_root / "actual-model.stdout.txt",
            stderr_path=evidence_root / "actual-model.stderr.txt",
            timeout_seconds=timeout_seconds,
        )
        summary["actual_model_returncode"] = actual_returncode
        if actual_returncode != 0:
            raise PhysicalTransactionError(
                f"actual token-budget probe exited with code {actual_returncode}"
            )

        actual_payload = _load_json(actual_output)
        summary["observation"] = validate_budget_payload(
            actual_payload,
            model_id=model_id,
        )
        _complete_stage(summary, stage)

        summary["status"] = "TOKEN_BUDGET_ISOLATION_PASS"
        summary["non_claims"] = [
            "PASS means a structurally valid physical trace was recorded.",
            "Wrong or fallback decisions remain valid observations.",
            "max_new_tokens is not semantic cognition depth.",
            "No adaptive mode policy is promoted.",
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
        description=(
            "Run the NLD reversed-mapping token-budget physical transaction."
        )
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
