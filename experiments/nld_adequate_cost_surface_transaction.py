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


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--evidence-root", type=Path, required=True)
    parser.parse_args()


if __name__ == "__main__":
    main()
