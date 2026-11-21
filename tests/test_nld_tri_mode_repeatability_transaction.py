from pathlib import Path

import pytest

from experiments.nld_tri_mode_repeatability_transaction import (
    PhysicalTransactionError,
    build_repeatability_command,
    validate_repeatability_payload,
)


def test_build_repeatability_command_keeps_canonical_subject(
    tmp_path: Path,
) -> None:
    command = build_repeatability_command(
        model_id="example/nld",
        output_path=tmp_path / "result.json",
        run=True,
        permutation_repeats=2,
    )

    assert "--run" in command
    assert command[command.index("--dtype") + 1] == "bf16"
    assert command[command.index("--permutation-repeats") + 1] == "2"
    assert command[command.index("--max-new-tokens") + 1] == "32"
    assert command[command.index("--max-thinking-tokens") + 1] == "32"
    assert command[command.index("--seed") + 1] == "1"


def _payload() -> dict[str, object]:
    observations = []
    modes = ("ar", "dlm", "linear_spec")
    orders = [
        ("ar", "dlm", "linear_spec"),
        ("ar", "linear_spec", "dlm"),
        ("dlm", "ar", "linear_spec"),
        ("dlm", "linear_spec", "ar"),
        ("linear_spec", "ar", "dlm"),
        ("linear_spec", "dlm", "ar"),
    ]
    index = 0
    for repeat in range(2):
        for permutation_index, order in enumerate(orders):
            for position, mode in enumerate(order, start=1):
                observations.append(
                    {
                        "observation_index": index,
                        "repeat_index": repeat,
                        "permutation_index": permutation_index,
                        "order": list(order),
                        "ordinal_position": position,
                        "mode": mode,
                        "elapsed_seconds": 0.1,
                        "nfe": 2,
                        "tokens_per_forward": 1.5,
                        "generated_token_count": 3,
                        "parsed_label": "A",
                        "expected_label": "A",
                        "decision_correct": True,
                        "cuda_peak_allocated_bytes": 100,
                    }
                )
                index += 1

    summary = {
        mode: {
            "count": 12,
            "correct_count": 12,
            "invalid_output_count": 0,
            "latency_seconds": {
                "count": 12,
                "min": 0.1,
                "median": 0.1,
                "p95_nearest_rank": 0.1,
                "max": 0.1,
            },
            "nfe": {"count": 12, "min": 2, "median": 2, "p95_nearest_rank": 2, "max": 2},
            "generated_token_count": {
                "count": 12,
                "min": 3,
                "median": 3,
                "p95_nearest_rank": 3,
                "max": 3,
            },
            "tokens_per_forward": {
                "count": 12,
                "min": 1.5,
                "median": 1.5,
                "p95_nearest_rank": 1.5,
                "max": 1.5,
            },
            "cuda_peak_allocated_bytes": {
                "count": 12,
                "min": 100,
                "median": 100,
                "p95_nearest_rank": 100,
                "max": 100,
            },
            "latency_by_ordinal_position": {
                str(position): {
                    "count": 4,
                    "latency_seconds": {
                        "count": 4,
                        "min": 0.1,
                        "median": 0.1,
                        "p95_nearest_rank": 0.1,
                        "max": 0.1,
                    },
                }
                for position in (1, 2, 3)
            },
        }
        for mode in modes
    }

    return {
        "evidence_class": "actual-model repeatability experiment",
        "model_id": "example/nld",
        "dtype": "bf16",
        "gpu_name": "GPU",
        "torch_version": "2.test",
        "transformers_version": "5.test",
        "load_elapsed_seconds": 1.0,
        "cuda_before_load": {"free_bytes": 1000},
        "cuda_after_load": {"free_bytes": 500},
        "permutation_repeats": 2,
        "method_availability": {
            "ar": True,
            "dlm": True,
            "linear_spec": True,
        },
        "warmup": [{"mode": mode} for mode in modes],
        "observations": observations,
        "summary_by_mode": summary,
    }


def test_validate_repeatability_payload_accepts_balanced_trace() -> None:
    result = validate_repeatability_payload(
        _payload(),
        model_id="example/nld",
        permutation_repeats=2,
    )

    assert result["measured_observation_count"] == 36
    assert result["modes"]["ar"]["count"] == 12
    assert result["modes"]["dlm"]["correct_count"] == 12


def test_validate_repeatability_payload_rejects_unbalanced_position() -> None:
    payload = _payload()
    payload["observations"][0]["ordinal_position"] = 2

    with pytest.raises(PhysicalTransactionError, match="position 1"):
        validate_repeatability_payload(
            payload,
            model_id="example/nld",
            permutation_repeats=2,
        )


def test_validate_repeatability_payload_does_not_require_correct_labels() -> None:
    payload = _payload()
    payload["observations"][0]["parsed_label"] = "B"
    payload["observations"][0]["decision_correct"] = False

    result = validate_repeatability_payload(
        payload,
        model_id="example/nld",
        permutation_repeats=2,
    )

    assert result["measured_observation_count"] == 36
