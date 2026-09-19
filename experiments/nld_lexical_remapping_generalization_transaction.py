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
        "experiments.nld_lexical_remapping_generalization",
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
            "lexical generalization evidence must be a JSON object"
        )
    if payload.get("evidence_class") != (
        "actual-model lexical remapping generalization"
    ):
        raise PhysicalTransactionError(
            "lexical generalization payload has wrong evidence class"
        )
    if payload.get("model_id") != model_id:
        raise PhysicalTransactionError(
            "lexical generalization model id does not match"
        )
    if payload.get("dtype") != "bf16":
        raise PhysicalTransactionError(
            "lexical generalization did not use bf16"
        )

    methods = payload.get("method_availability")
    if not isinstance(methods, dict):
        raise PhysicalTransactionError("method_availability is missing")
    required_modes = ("ar", "dlm", "linear_spec")
    if any(methods.get(mode) is not True for mode in required_modes):
        raise PhysicalTransactionError(
            "one or more native methods are unavailable"
        )

    observations = payload.get("observations")
    if not isinstance(observations, list):
        raise PhysicalTransactionError("observations must be a list")
    if len(observations) != 216:
        raise PhysicalTransactionError(
            f"expected 216 observations; found {len(observations)}"
        )

    expected_families = ("route", "color", "code")
    cells: dict[tuple[str, str], list[dict[str, object]]] = {}
    for item in observations:
        if not isinstance(item, dict):
            raise PhysicalTransactionError(
                "each observation must be a JSON object"
            )
        family_id = item.get("family_id")
        mode = item.get("mode")
        case_id = item.get("case_id")
        if family_id not in expected_families:
            raise PhysicalTransactionError(
                f"unexpected family id: {family_id!r}"
            )
        if mode not in required_modes:
            raise PhysicalTransactionError(
                f"unexpected mode: {mode!r}"
            )
        if not isinstance(case_id, str):
            raise PhysicalTransactionError("case_id must be a string")
        if not isinstance(item.get("parsed_destination"), str):
            raise PhysicalTransactionError(
                "parsed_destination is missing"
            )
        cells.setdefault((case_id, mode), []).append(item)

    if len(cells) != 36:
        raise PhysicalTransactionError(
            f"expected 36 case/mode cells; found {len(cells)}"
        )
    for key, rows in cells.items():
        if len(rows) != 6:
            raise PhysicalTransactionError(
                f"{key!r} expected 6 rows; found {len(rows)}"
            )
        for position in (1, 2, 3):
            count = sum(
                row.get("ordinal_position") == position for row in rows
            )
            if count != 2:
                raise PhysicalTransactionError(
                    f"{key!r} position {position} expected 2; found {count}"
                )

    summary = payload.get("summary")
    if not isinstance(summary, dict):
        raise PhysicalTransactionError("summary is missing")
    by_family = summary.get("by_family")
    overall = summary.get("overall_by_mode")
    if not isinstance(by_family, dict):
        raise PhysicalTransactionError("by_family summary is missing")
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
        "entity_tokenization": payload.get("entity_tokenization"),
        "measured_observation_count": len(observations),
        "by_family": by_family,
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
        "qualification_scope": "nld_lexical_remapping_generalization",
        "canonical_runtime": {
            "engine": "pytorch_transformers_direct",
            "dtype": "bf16",
            "family_count": 3,
            "case_count": 12,
            "modes": ["ar", "dlm", "linear_spec"],
            "warmup_calls_per_mode": 1,
            "measured_call_count": 216,
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
                f"lexical dry run exited with code {returncode}"
            )
        dry_payload = _load_json(dry_output)
        if (
            not isinstance(dry_payload, dict)
            or dry_payload.get("evidence_class")
            != "lexical remapping generalization plan only"
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
                f"actual lexical matrix exited with code {returncode}"
            )

        actual_payload = _load_json(actual_output)
        summary["observation"] = validate_payload(
            actual_payload,
            model_id=model_id,
        )
        _complete_stage(summary, stage)

        summary["status"] = "LEXICAL_GENERALIZATION_PASS"
        summary["non_claims"] = [
            "PASS means a structurally valid physical trace was recorded.",
            "Wrong or invalid decisions remain valid observations.",
            "Aggregate correctness is not a product ranking.",
            "This gate does not establish cross-model generalization.",
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
