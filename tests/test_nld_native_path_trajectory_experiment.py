from experiments.nld_native_path_trajectory import (
    common_token_count,
    dry_run_payload,
    pairwise_divergence,
)


def test_dry_run_counts() -> None:
    plan = dry_run_payload()
    assert plan["physical_measured_calls"] == 72
    assert plan["focus_observations"] == 18


def test_common_token_count() -> None:
    assert common_token_count([1, 2, 3], [1, 2, 4]) == 2
    assert common_token_count([1, 2], [1, 2]) == 2
    assert common_token_count([1], [2]) == 0


def test_pairwise_divergence_reports_first_difference() -> None:
    first = {
        "generated_token_ids": [10, 11, 12],
        "generated_token_texts": ["a", "b", "c"],
    }
    second = {
        "generated_token_ids": [10, 11, 13],
        "generated_token_texts": ["a", "b", "d"],
    }

    result = pairwise_divergence(first, second)

    assert result["common_token_count"] == 2
    assert result["first_divergence_token_index_1based"] == 3
    assert result["first_next_token_id"] == 12
    assert result["second_next_token_id"] == 13
