import json
from pathlib import Path

import pytest

from experiments.diffusiongemma_bounded_decision_transaction import (
    PhysicalTransactionError,
    _prepare_evidence_root,
    build_probe_command,
    validate_probe_result,
)


def test_build_probe_command_separates_plan_from_actual_model(tmp_path: Path) -> None:
    common = {
        "repo_root": tmp_path,
        "model_id": "example/model",
        "case_id": "easy_separable",
        "steps": 1,
        "quantization": "bnb4",
        "output_path": tmp_path / "result.json",
    }

    dry = build_probe_command(**common, run=False)
    actual = build_probe_command(**common, run=True)

    assert "--run" not in dry
    assert "--run" in actual
    assert dry[dry.index("--steps") + 1] == "1"
    assert dry[dry.index("--quantization") + 1] == "bnb4"


def test_validate_probe_result_accepts_one_step_actual_model_observation() -> None:
    payload = {
        "evidence_class": "actual-model experiment",
        "model_id": "example/model",
        "quantization": "bnb4",
        "fixed_trace_steps": 1,
        "transformers_version": "5.test",
        "torch_version": "2.test",
        "fixed_results": [
            {
                "case_id": "easy_separable",
                "expected_label": "A",
                "actual_denoising_steps": 1,
                "canvas_length": 256,
                "elapsed_seconds": 1.25,
                "cuda_peak_bytes": 123,
                "tokens_per_forward": [1.0],
                "final_candidate_correct": True,
                "final_candidate_readout": {
                    "winner": "A",
                    "winner_probability": 0.8,
                },
            }
        ],
    }

    observed = validate_probe_result(
        payload,
        model_id="example/model",
        case_id="easy_separable",
        steps=1,
        quantization="bnb4",
    )

    assert observed["winner"] == "A"
    assert observed["candidate_correct"] is True
    assert observed["actual_denoising_steps"] == 1
    assert observed["canvas_length"] == 256


@pytest.mark.parametrize(
    ("field", "value", "message"),
    [
        ("evidence_class", "experiment plan only", "actual-model"),
        ("model_id", "other/model", "model id"),
        ("quantization", "none", "quantization"),
        ("fixed_trace_steps", 2, "fixed_trace_steps"),
    ],
)
def test_validate_probe_result_rejects_mismatched_transaction_subject(
    field: str,
    value: object,
    message: str,
) -> None:
    payload = {
        "evidence_class": "actual-model experiment",
        "model_id": "example/model",
        "quantization": "bnb4",
        "fixed_trace_steps": 1,
        "fixed_results": [
            {
                "case_id": "easy_separable",
                "expected_label": "A",
                "actual_denoising_steps": 1,
                "canvas_length": 256,
                "final_candidate_correct": True,
                "final_candidate_readout": {"winner": "A"},
            }
        ],
    }
    payload[field] = value

    with pytest.raises(PhysicalTransactionError, match=message):
        validate_probe_result(
            payload,
            model_id="example/model",
            case_id="easy_separable",
            steps=1,
            quantization="bnb4",
        )


def test_validate_probe_result_rejects_wrong_actual_step_count() -> None:
    payload = {
        "evidence_class": "actual-model experiment",
        "model_id": "example/model",
        "quantization": "bnb4",
        "fixed_trace_steps": 1,
        "fixed_results": [
            {
                "case_id": "easy_separable",
                "actual_denoising_steps": 2,
                "canvas_length": 256,
                "final_candidate_readout": {"winner": "A"},
            }
        ],
    }

    with pytest.raises(PhysicalTransactionError, match="denoising-step count"):
        validate_probe_result(
            payload,
            model_id="example/model",
            case_id="easy_separable",
            steps=1,
            quantization="bnb4",
        )


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
    (nonempty / "evidence.json").write_text(json.dumps({"x": 1}), encoding="utf-8")

    with pytest.raises(PhysicalTransactionError, match="new or empty"):
        _prepare_evidence_root(nonempty)
