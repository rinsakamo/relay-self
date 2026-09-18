from pathlib import Path

import pytest

from experiments.nld_easy_permutation_isolation_transaction import (
    PhysicalTransactionError,
    build_isolation_command,
    validate_isolation_payload,
)


def test_build_isolation_command_keeps_qualified_subject(
    tmp_path: Path,
) -> None:
    command = build_isolation_command(
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
        "cave_open_a_cave",
        "cave_open_a_ridge",
        "ridge_open_a_cave",
        "ridge_open_a_ridge",
    )
    expected = {
        "cave_open_a_cave": ("A", "cave"),
        "cave_open_a_ridge": ("B", "cave"),
        "ridge_open_a_cave": ("B", "ridge"),
        "ridge_open_a_ridge": ("A", "ridge"),
    }
    mappings = {
        "cave_open_a_cave": {
            "A": "cave",
            "B": "ridge",
            "C": "DEFER",
        },
        "cave_open_a_ridge": {
            "A": "ridge",
            "B": "cave",
            "C": "DEFER",
        },
        "ridge_open_a_cave": {
            "A": "cave",
            "B": "ridge",
            "C": "DEFER",
        },
        "ridge_open_a_ridge": {
            "A": "ridge",
            "B": "cave",
            "C": "DEFER",
        },
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
        expected_label, feasible = expected[case_id]
        for permutation_index, order in enumerate(orders):
            for position, mode in enumerate(order, start=1):
                observations.append(
                    {
                        "observation_index": index,
                        "case_id": case_id,
                        "expected_label": expected_label,
                        "feasible_destination": feasible,
                        "permutation_index": permutation_index,
                        "order": list(order),
                        "ordinal_position": position,
                        "mode": mode,
                        "parsed_label": expected_label,
                        "parsed_destination": feasible,
                        "decision_correct": True,
                        "elapsed_seconds": 0.1,
                        "nfe": 2,
                        "generated_token_count": 3,
                        "tokens_per_forward": 1.5,
                        "cuda_peak_allocated_bytes": 100,
                    }
                )
                index += 1

    summary_by_case = {}
    for case_id in case_ids:
        expected_label, feasible = expected[case_id]
        summary_by_case[case_id] = {
            "expected_label": expected_label,
            "feasible_destination": feasible,
            "label_to_destination": mappings[case_id],
            "route_evidence": {},
            "observation_count": 18,
            "modes": {
                mode: {
                    "count": 6,
                    "correct_count": 6,
                    "invalid_output_count": 0,
                    "observed_labels": {expected_label: 6},
                    "observed_destinations": {feasible: 6},
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
        "evidence_class": "actual-model easy permutation isolation",
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


def test_validate_isolation_payload_accepts_complete_trace() -> None:
    result = validate_isolation_payload(
        _payload(),
        model_id="example/nld",
    )

    assert result["measured_observation_count"] == 72
    assert (
        result["cases"]["cave_open_a_ridge"]["modes"]["ar"][
            "observed_destinations"
        ]
        == {"cave": 6}
    )


def test_validate_isolation_payload_preserves_wrong_decision() -> None:
    payload = _payload()
    payload["observations"][0]["parsed_label"] = "B"
    payload["observations"][0]["parsed_destination"] = "ridge"
    payload["observations"][0]["decision_correct"] = False
    payload["summary_by_case"]["cave_open_a_cave"]["modes"]["ar"][
        "correct_count"
    ] = 5

    result = validate_isolation_payload(
        payload,
        model_id="example/nld",
    )

    assert (
        result["cases"]["cave_open_a_cave"]["modes"]["ar"][
            "correct_count"
        ]
        == 5
    )


def test_validate_isolation_payload_rejects_missing_observation() -> None:
    payload = _payload()
    payload["observations"].pop()

    with pytest.raises(PhysicalTransactionError, match="72"):
        validate_isolation_payload(
            payload,
            model_id="example/nld",
        )


def test_validate_isolation_payload_requires_semantic_projection() -> None:
    payload = _payload()
    del payload["observations"][0]["parsed_destination"]

    with pytest.raises(
        PhysicalTransactionError,
        match="parsed_destination",
    ):
        validate_isolation_payload(
            payload,
            model_id="example/nld",
        )
