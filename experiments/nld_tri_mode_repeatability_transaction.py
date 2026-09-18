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
DEFAULT_PERMUTATION_REPEATS = 2


def build_repeatability_command(
    *,
    model_id: str,
    output_path: Path,
    run: bool,
    permutation_repeats: int = DEFAULT_PERMUTATION_REPEATS,
) -> list[str]:
    import sys

    command = [
        sys.executable,
        "-B",
        "-m",
        "experiments.nld_tri_mode_repeatability",
    ]
    if run:
        command.append("--run")

    command.extend(
        [
            "--model",
            model_id,
            "--permutation-repeats",
            str(permutation_repeats),
            "--dtype",
            "bf16",
            "--max-new-tokens",
            "32",
            "--max-thinking-tokens",
            "32",
            "--seed",
            "1",
            "--output",
            str(output_path),
        ]
    )
    return command


def validate_repeatability_payload(
    payload: object,
    *,
    model_id: str,
    permutation_repeats: int,
) -> dict[str, object]:
    if not isinstance(payload, dict):
        raise PhysicalTransactionError(
            "repeatability evidence must be a JSON object"
        )

    if payload.get("evidence_class") != "actual-model repeatability experiment":
        raise PhysicalTransactionError(
            "repeatability payload has the wrong evidence class"
        )

    if payload.get("model_id") != model_id:
        raise PhysicalTransactionError(
            "repeatability payload model id does not match"
        )

    if payload.get("dtype") != "bf16":
        raise PhysicalTransactionError(
            "repeatability payload did not use canonical bf16"
        )

    if payload.get("permutation_repeats") != permutation_repeats:
        raise PhysicalTransactionError(
            "repeatability payload repeat count does not match"
        )

    methods = payload.get("method_availability")
    if not isinstance(methods, dict):
        raise PhysicalTransactionError("method_availability is missing")

    required_modes = ("ar", "dlm", "linear_spec")
    unavailable = [mode for mode in required_modes if methods.get(mode) is not True]
    if unavailable:
        raise PhysicalTransactionError(
            "native NLD methods unavailable: " + ", ".join(unavailable)
        )

    warmup = payload.get("warmup")
    if not isinstance(warmup, list) or len(warmup) != len(required_modes):
        raise PhysicalTransactionError(
            "repeatability payload must contain one warm-up call per mode"
        )

    expected_observations = permutation_repeats * 6 * len(required_modes)
    observations = payload.get("observations")
    if not isinstance(observations, list):
        raise PhysicalTransactionError("observations must be a list")
    if len(observations) != expected_observations:
        raise PhysicalTransactionError(
            f"expected {expected_observations} measured observations; "
            f"found {len(observations)}"
        )

    by_mode: dict[str, list[dict[str, object]]] = {
        mode: [] for mode in required_modes
    }
    for item in observations:
        if not isinstance(item, dict):
            raise PhysicalTransactionError(
                "measured observation must be a JSON object"
            )
        mode = item.get("mode")
        if mode not in by_mode:
            raise PhysicalTransactionError(
                f"unexpected measured mode: {mode!r}"
            )
        by_mode[mode].append(item)

    expected_per_mode = permutation_repeats * 6
    for mode, rows in by_mode.items():
        if len(rows) != expected_per_mode:
            raise PhysicalTransactionError(
                f"{mode} expected {expected_per_mode} observations; "
                f"found {len(rows)}"
            )
        for position in (1, 2, 3):
            expected_position_count = permutation_repeats * 2
            actual_position_count = sum(
                row.get("ordinal_position") == position for row in rows
            )
            if actual_position_count != expected_position_count:
                raise PhysicalTransactionError(
                    f"{mode} position {position} expected "
                    f"{expected_position_count} observations; "
                    f"found {actual_position_count}"
                )

    summaries = payload.get("summary_by_mode")
    if not isinstance(summaries, dict):
        raise PhysicalTransactionError("summary_by_mode is missing")

    compact_modes: dict[str, object] = {}
    for mode in required_modes:
        summary = summaries.get(mode)
        if not isinstance(summary, dict):
            raise PhysicalTransactionError(
                f"summary for {mode} is missing"
            )
        latency = summary.get("latency_seconds")
        if not isinstance(latency, dict):
            raise PhysicalTransactionError(
                f"latency summary for {mode} is missing"
            )
        compact_modes[mode] = {
            "count": summary.get("count"),
            "correct_count": summary.get("correct_count"),
            "invalid_output_count": summary.get("invalid_output_count"),
            "latency_seconds": latency,
            "nfe": summary.get("nfe"),
            "generated_token_count": summary.get("generated_token_count"),
            "tokens_per_forward": summary.get("tokens_per_forward"),
            "cuda_peak_allocated_bytes": summary.get(
                "cuda_peak_allocated_bytes"
            ),
            "latency_by_ordinal_position": summary.get(
                "latency_by_ordinal_position"
            ),
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
        "permutation_repeats": permutation_repeats,
        "measured_observation_count": len(observations),
        "modes": compact_modes,
    }


def _initial_summary(
    *,
    repo_root: Path,
    evidence_root: Path,
    model_id: str,
    permutation_repeats: int,
) -> dict[str, object]:
    return {
        "format_version": FORMAT_VERSION,
        "status": "STARTED",
        "current_stage": None,
        "completed_stages": [],
        "repo_root": str(repo_root),
        "evidence_root": str(evidence_root),
        "model_id": model_id,
        "qualification_scope": "nld_3b_tri_mode_repeatability_order_effect",
        "canonical_runtime": {
            "engine": "pytorch_transformers_direct",
            "dtype": "bf16",
            "modes": ["ar", "dlm", "linear_spec"],
            "warmup_calls_per_mode": 1,
            "permutation_repeats": permutation_repeats,
            "measured_calls_per_mode": permutation_repeats * 6,
            "cuda_synchronized_timing": True,
            "lora": False,
            "quantization": None,
            "serving_framework": None,
        },
    }


def _complete_stage(summary: dict[str, object], stage: str) -> None:
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
    permutation_repeats: int,
) -> int:
    if timeout_seconds <= 0:
        raise PhysicalTransactionError("timeout_seconds must be positive")
    if permutation_repeats < 1:
        raise PhysicalTransactionError("permutation_repeats must be positive")

    evidence_root = _prepare_evidence_root(evidence_root)
    summary_path = evidence_root / "summary.json"
    summary = _initial_summary(
        repo_root=repo_root,
        evidence_root=evidence_root,
        model_id=model_id,
        permutation_repeats=permutation_repeats,
    )
    _write_json(summary_path, summary)

    try:
        stage = "repo_preflight"
        summary["current_stage"] = stage
        _write_json(summary_path, summary)
        head, tree, branch = _require_clean_repo(repo_root)
        summary["git"] = {"head": head, "tree": tree, "branch": branch}
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
        dry_command = build_repeatability_command(
            model_id=model_id,
            output_path=dry_output,
            run=False,
            permutation_repeats=permutation_repeats,
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
                f"dry-run repeatability probe exited with code {dry_returncode}"
            )

        dry_payload = _load_json(dry_output)
        if (
            not isinstance(dry_payload, dict)
            or dry_payload.get("evidence_class")
            != "repeatability experiment plan only"
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
        actual_command = build_repeatability_command(
            model_id=model_id,
            output_path=actual_output,
            run=True,
            permutation_repeats=permutation_repeats,
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
                f"actual repeatability probe exited with code {actual_returncode}"
            )

        actual_payload = _load_json(actual_output)
        summary["observation"] = validate_repeatability_payload(
            actual_payload,
            model_id=model_id,
            permutation_repeats=permutation_repeats,
        )
        _complete_stage(summary, stage)

        summary["status"] = "REPEATABILITY_PASS"
        summary["non_claims"] = [
            "REPEATABILITY_PASS is a structural physical-evidence result.",
            "One-prompt latency differences are not a general model-quality ranking.",
            "No adaptive RelayEngine mode policy is promoted by this transaction.",
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
        description="Run the NLD-3B tri-mode repeatability physical transaction."
    )
    parser.add_argument(
        "--repo-root",
        type=Path,
        default=default_repo_root,
    )
    parser.add_argument("--evidence-root", type=Path, required=True)
    parser.add_argument("--model", default=DEFAULT_MODEL_ID)
    parser.add_argument(
        "--timeout-seconds",
        type=float,
        default=DEFAULT_TIMEOUT_SECONDS,
    )
    parser.add_argument(
        "--permutation-repeats",
        type=int,
        default=DEFAULT_PERMUTATION_REPEATS,
    )
    args = parser.parse_args()

    try:
        result = run_transaction(
            repo_root=args.repo_root.resolve(),
            evidence_root=args.evidence_root,
            model_id=args.model,
            timeout_seconds=args.timeout_seconds,
            permutation_repeats=args.permutation_repeats,
        )
    except PhysicalTransactionError as exc:
        parser.error(str(exc))

    raise SystemExit(result)


if __name__ == "__main__":
    main()
