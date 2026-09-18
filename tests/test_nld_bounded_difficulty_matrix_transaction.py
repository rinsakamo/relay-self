from pathlib import Path

import pytest

from experiments.nld_bounded_difficulty_matrix_transaction import (
    PhysicalTransactionError,
    build_matrix_command,
    validate_matrix_payload,
)


def test_build_matrix_command_keeps_canonical_subject(
    tmp_path: Path,
) -> None:
    command = build_matrix_command(
        model_id="example/nld",
        output_path=tmp_path / "result.json",
        run=True,
    )

    assert "--run" in command
    assert command[command.index("--dtype") + 1] == "bf16"
    assert command[command.index("--max-new-tokens") + 1] == "32"
    assert command[command.index("--max-thinking-tokens") + 1] == "32"
    assert command[command.index("--seed") + 1] == "1"


def _payload() -> dict[str, object]:
    case_ids = (
        "easy_separable",
        "coupled_constraints",
        "incomplete_focus",
    )
    expected = {
        "easy_separable": "A",
        "coupled_constraints": "B",
        "incomplete_focus": "C",
    }
    modes = ("ar", "dlm", "linear_spec")
    orders = [
        ("ar", "dlm", "linear_spec"),
        ("ar", "linear_spec", "dlm"),
        ("dlm", "ar", "linear_spec"),
        ("dlm", "linear_spec", "ar"),
        ("linear_spec", "ar", "dlm"),
        ("linear_spec", "dlm", "ar"),
    ]

    observations = []
    index = 0
    for case_id in case_ids:
        for permutation_index, order in enumerate(orders):
            for position, mode in enumerate(order, start=1):
                observations.append(
                    {
                        "observation_index": index,
                        "case_id": case_id,
                        "expected_label": expected[case_id],
                        "permutation_index": permutation_index,
                        "order": list(order),
                        "ordinal_position": position,
                        "mode": mode,
                        "elapsed_seconds": 0.1,
                        "nfe": 2,
                        "tokens_per_forward": 1.5,
                        "generated_token_count": 3,
                        "generated_text": expected[case_id],
                        "parsed_label": expected[case_id],
                        "decision_correct": True,
                        "cuda_peak_allocated_bytes": 100,
                    }
                )
                index += 1

    summary_by_case = {}
    for case_id in case_ids:
        summary_by_case[case_id] = {
            "expected_label": expected[case_id],
            "observation_count": 18,
            "modes": {
                mode: {
                    "count": 6,
                    "correct_count": 6,
                    "invalid_output_count": 0,
                    "observed_labels": {expected[case_id]: 6},
                    "latency_seconds": {
                        "count": 6,
                        "min": 0.1,
                        "median": 0.1,
                        "p95_nearest_rank": 0.1,
                        "max": 0.1,
                    },
                    "nfe": {
                        "count": 6,
                        "min": 2,
                        "median": 2,
                        "p95_nearest_rank": 2,
                        "max": 2,
                    },
                    "generated_token_count": {
                        "count": 6,
                        "min": 3,
                        "median": 3,
                        "p95_nearest_rank": 3,
                        "max": 3,
                    },
                    "tokens_per_forward": {
                        "count": 6,
                        "min": 1.5,
                        "median": 1.5,
                        "p95_nearest_rank": 1.5,
                        "max": 1.5,
                    },
                    "cuda_peak_allocated_bytes": {
                        "count": 6,
                        "min": 100,
                        "median": 100,
                        "p95_nearest_rank": 100,
                        "max": 100,
                    },
                    "latency_by_ordinal_position": {
                        str(position): {
                            "count": 2,
                            "latency_seconds": {
                                "count": 2,
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
            },
        }

    return {
        "evidence_class": "actual-model bounded difficulty matrix",
        "model_id": "example/nld",
        "dtype": "bf16",
        "gpu_name": "GPU",
        "torch_version": "2.test",
        "transformers_version": "5.test",
        "load_elapsed_seconds": 1.0,
        "cuda_before_load": {"free_bytes": 1000},
        "cuda_after_load": {"free_bytes": 500},
        "method_availability": {
            "ar": True,
            "dlm": True,
            "linear_spec": True,
        },
        "warmup": [{"mode": mode} for mode in modes],
        "observations": observations,
        "summary_by_case": summary_by_case,
    }


def test_validate_matrix_payload_accepts_complete_matrix() -> None:
    result = validate_matrix_payload(
        _payload(),
        model_id="example/nld",
    )

    assert result["measured_observation_count"] == 54
    assert result["cases"]["easy_separable"]["modes"]["ar"]["count"] == 6


def test_validate_matrix_payload_preserves_wrong_output() -> None:
    payload = _payload()
    payload["observations"][0]["parsed_label"] = "B"
    payload["observations"][0]["decision_correct"] = False
    payload["summary_by_case"]["easy_separable"]["modes"]["ar"][
        "correct_count"
    ] = 5
    payload["summary_by_case"]["easy_separable"]["modes"]["ar"][
        "observed_labels"
    ] = {"A": 5, "B": 1}

    result = validate_matrix_payload(
        payload,
        model_id="example/nld",
    )

    assert (
        result["cases"]["easy_separable"]["modes"]["ar"]["correct_count"]
        == 5
    )


def test_validate_matrix_payload_rejects_missing_cell_observation() -> None:
    payload = _payload()
    payload["observations"].pop()

    with pytest.raises(PhysicalTransactionError, match="54"):
        validate_matrix_payload(
            payload,
            model_id="example/nld",
        )


def test_validate_matrix_payload_rejects_unbalanced_position() -> None:
    payload = _payload()
    target = next(
        row
        for row in payload["observations"]
        if row["case_id"] == "easy_separable"
        and row["mode"] == "ar"
        and row["ordinal_position"] == 1
    )
    target["ordinal_position"] = 2

    with pytest.raises(PhysicalTransactionError, match="position 1"):
        validate_matrix_payload(
            payload,
            model_id="example/nld",
        )
