import json
from pathlib import Path

import pytest

from experiments.nld_tri_mode_transaction import (
    PhysicalTransactionError,
    _prepare_evidence_root,
    build_probe_command,
    validate_actual_payload,
)


def test_build_probe_command_keeps_first_gate_canonical(tmp_path: Path) -> None:
    command = build_probe_command(
        model_id="example/nld",
        output_path=tmp_path / "result.json",
        run=True,
    )

    assert "--run" in command
    assert command[command.index("--modes") + 1] == "all"
    assert command[command.index("--dtype") + 1] == "bf16"
    assert command[command.index("--max-new-tokens") + 1] == "32"
    assert command[command.index("--max-thinking-tokens") + 1] == "32"


def test_validate_actual_payload_accepts_complete_tri_mode_result() -> None:
    payload = {
        "evidence_class": "actual-model experiment",
        "model_id": "example/nld",
        "dtype": "bf16",
        "gpu_name": "GPU",
        "torch_version": "2.test",
        "transformers_version": "5.test",
        "load_elapsed_seconds": 2.0,
        "cuda_before_load": {"free_bytes": 10},
        "cuda_after_load": {"free_bytes": 4},
        "method_availability": {
            "ar": True,
            "dlm": True,
            "linear_spec": True,
        },
        "results": [
            {
                "mode": "ar",
                "elapsed_seconds": 1.0,
                "nfe": 8,
                "tokens_per_forward": 1.0,
                "generated_token_count": 8,
                "parsed_label": "A",
                "expected_label": "A",
                "decision_correct": True,
                "cuda_peak_allocated_bytes": 100,
            },
            {
                "mode": "dlm",
                "elapsed_seconds": 0.8,
                "nfe": 4,
                "tokens_per_forward": 2.0,
                "generated_token_count": 8,
                "parsed_label": "A",
                "expected_label": "A",
                "decision_correct": True,
                "cuda_peak_allocated_bytes": 110,
            },
            {
                "mode": "linear_spec",
                "elapsed_seconds": 0.7,
                "nfe": 3,
                "tokens_per_forward": 3.0,
                "generated_token_count": 9,
                "parsed_label": "A",
                "expected_label": "A",
                "decision_correct": True,
                "cuda_peak_allocated_bytes": 120,
            },
        ],
    }

    observed = validate_actual_payload(payload, model_id="example/nld")

    assert observed["model_id"] == "example/nld"
    assert set(observed["modes"]) == {"ar", "dlm", "linear_spec"}
    assert observed["modes"]["dlm"]["decision_correct"] is True


def test_validate_actual_payload_rejects_missing_native_method() -> None:
    payload = {
        "evidence_class": "actual-model experiment",
        "model_id": "example/nld",
        "dtype": "bf16",
        "method_availability": {
            "ar": True,
            "dlm": True,
            "linear_spec": False,
        },
        "results": [],
    }

    with pytest.raises(PhysicalTransactionError, match="unavailable"):
        validate_actual_payload(payload, model_id="example/nld")


def test_validate_actual_payload_rejects_missing_mode_result() -> None:
    payload = {
        "evidence_class": "actual-model experiment",
        "model_id": "example/nld",
        "dtype": "bf16",
        "method_availability": {
            "ar": True,
            "dlm": True,
            "linear_spec": True,
        },
        "results": [
            {"mode": "ar"},
            {"mode": "dlm"},
        ],
    }

    with pytest.raises(PhysicalTransactionError, match="missing mode results"):
        validate_actual_payload(payload, model_id="example/nld")


def test_prepare_evidence_root_accepts_new_or_empty_and_rejects_nonempty(
    tmp_path: Path,
) -> None:
    new_root = tmp_path / "new"
    assert _prepare_evidence_root(new_root) == new_root.resolve()

    empty_root = tmp_path / "empty"
    empty_root.mkdir()
    assert _prepare_evidence_root(empty_root) == empty_root.resolve()

    nonempty = tmp_path / "nonempty"
    nonempty.mkdir()
    (nonempty / "x.json").write_text(json.dumps({"x": 1}), encoding="utf-8")

    with pytest.raises(PhysicalTransactionError, match="new or empty"):
        _prepare_evidence_root(nonempty)
