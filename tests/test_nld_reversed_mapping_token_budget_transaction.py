from pathlib import Path

import pytest

from experiments.nld_reversed_mapping_token_budget_transaction import (
    PhysicalTransactionError,
    build_budget_command,
    validate_budget_payload,
)


def test_build_budget_command_keeps_qualified_subject(
    tmp_path: Path,
) -> None:
    command = build_budget_command(
        model_id="example/nld",
        output_path=tmp_path / "result.json",
        run=True,
    )

    assert "--run" in command
    assert command[command.index("--dtype") + 1] == "bf16"
    assert command[command.index("--max-thinking-tokens") + 1] == "32"
    assert command[command.index("--seed") + 1] == "1"


def _payload() -> dict[str, object]:
    case_ids = ("reversed_cave_open", "reversed_ridge_open")
    expected = {
        "reversed_cave_open": ("B", "cave"),
        "reversed_ridge_open": ("A", "ridge"),
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
        expected_label, destination = expected[case_id]
        for budget in (32, 64):
            for permutation_index, order in enumerate(orders):
                for position, mode in enumerate(order, start=1):
                    observations.append(
                        {
                            "observation_index": index,
                            "case_id": case_id,
                            "expected_label": expected_label,
                            "feasible_destination": destination,
                            "max_new_tokens": budget,
                            "permutation_index": permutation_index,
                            "order": list(order),
                            "ordinal_position": position,
                            "mode": mode,
                            "parse_source": "explicit",
                            "explicit_label": expected_label,
                            "fallback_label": expected_label,
                            "parsed_label": expected_label,
                            "parsed_destination": destination,
                            "decision_correct": True,
                            "eos_reached": True,
                            "reached_or_exceeded_effective_max_new_tokens": False,
                            "elapsed_seconds": 0.1,
                            "nfe": 2,
                            "generated_token_count": 10,
                            "tokens_per_forward": 5.0,
                            "cuda_peak_allocated_bytes": 100,
                        }
                    )
                    index += 1

    summary_by_case = {}
    for case_id in case_ids:
        expected_label, destination = expected[case_id]
        budgets = {}
        for budget in ("32", "64"):
            budgets[budget] = {
                "observation_count": 18,
                "modes": {
                    mode: {
                        "count": 6,
                        "correct_count": 6,
                        "invalid_output_count": 0,
                        "observed_labels": {expected_label: 6},
                        "observed_destinations": {destination: 6},
                        "parse_sources": {"explicit": 6},
                        "explicit_labels": {expected_label: 6},
                        "fallback_labels": {expected_label: 6},
                        "eos_reached": {"true": 6},
                        "token_cap_proxy": {"false": 6},
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
                            "min": 10,
                            "median": 10,
                            "p95_nearest_rank": 10,
                            "max": 10,
                        },
                        "tokens_per_forward": {
                            "count": 6,
                            "min": 5.0,
                            "median": 5.0,
                            "p95_nearest_rank": 5.0,
                            "max": 5.0,
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

        summary_by_case[case_id] = {
            "expected_label": expected_label,
            "feasible_destination": destination,
            "label_to_destination": {
                "A": "ridge",
                "B": "cave",
                "C": "DEFER",
            },
            "route_evidence": {},
            "budgets": budgets,
        }

    return {
        "evidence_class": "actual-model reversed mapping token-budget isolation",
        "model_id": "example/nld",
        "token_budgets": [32, 64],
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
        "warmup": [{"mode": mode} for mode in modes for _ in (32, 64)],
        "observations": observations,
        "summary_by_case": summary_by_case,
    }


def test_validate_budget_payload_accepts_complete_trace() -> None:
    result = validate_budget_payload(
        _payload(),
        model_id="example/nld",
    )

    assert result["measured_observation_count"] == 72
    assert (
        result["cases"]["reversed_cave_open"]["budgets"]["64"]["modes"][
            "linear_spec"
        ]["parse_sources"]
        == {"explicit": 6}
    )


def test_validate_budget_payload_preserves_fallback_decision() -> None:
    payload = _payload()
    payload["observations"][0]["parse_source"] = "fallback"
    payload["observations"][0]["explicit_label"] = None
    payload["observations"][0]["eos_reached"] = False
    payload["observations"][0][
        "reached_or_exceeded_effective_max_new_tokens"
    ] = True

    result = validate_budget_payload(
        payload,
        model_id="example/nld",
    )

    assert result["measured_observation_count"] == 72


def test_validate_budget_payload_rejects_missing_observation() -> None:
    payload = _payload()
    payload["observations"].pop()

    with pytest.raises(PhysicalTransactionError, match="72"):
        validate_budget_payload(
            payload,
            model_id="example/nld",
        )


def test_validate_budget_payload_requires_parse_source() -> None:
    payload = _payload()
    payload["observations"][0]["parse_source"] = "other"

    with pytest.raises(PhysicalTransactionError, match="parse_source"):
        validate_budget_payload(
            payload,
            model_id="example/nld",
        )
