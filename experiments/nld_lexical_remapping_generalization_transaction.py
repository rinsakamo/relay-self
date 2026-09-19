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


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--evidence-root", type=Path, required=True)
    parser.parse_args()


if __name__ == "__main__":
    main()
