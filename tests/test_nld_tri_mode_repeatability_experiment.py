import math

import pytest

from experiments.nld_tri_mode_repeatability import (
    MODE_PERMUTATIONS,
    _nearest_rank_percentile,
    build_measured_schedule,
    dry_run_payload,
    summarize_observations,
)


def test_schedule_uses_all_six_orders_twice_and_balances_positions() -> None:
    schedule = build_measured_schedule(permutation_repeats=2)

    assert len(MODE_PERMUTATIONS) == math.factorial(3)
    assert len(schedule) == 36

    for mode in ("ar", "dlm", "linear_spec"):
        rows = [row for row in schedule if row["mode"] == mode]
        assert len(rows) == 12
        for position in (1, 2, 3):
            assert sum(
                row["ordinal_position"] == position for row in rows
            ) == 4


def test_schedule_is_deterministic() -> None:
    first = build_measured_schedule(permutation_repeats=2)
    second = build_measured_schedule(permutation_repeats=2)
    assert first == second


def test_schedule_rejects_nonpositive_repeat_count() -> None:
    with pytest.raises(ValueError, match="positive"):
        build_measured_schedule(permutation_repeats=0)


def test_nearest_rank_percentile_is_explicit() -> None:
    assert _nearest_rank_percentile([1.0, 2.0, 3.0, 4.0], 0.95) == 4.0
    assert _nearest_rank_percentile([1.0, 2.0, 3.0, 4.0], 0.5) == 2.0


def test_summary_separates_modes_and_ordinal_positions() -> None:
    observations = []
    for mode_index, mode in enumerate(("ar", "dlm", "linear_spec"), start=1):
        for position in (1, 2, 3):
            observations.append(
                {
                    "mode": mode,
                    "ordinal_position": position,
                    "elapsed_seconds": float(mode_index * position),
                    "nfe": mode_index,
                    "generated_token_count": 3,
                    "tokens_per_forward": 3 / mode_index,
                    "parsed_label": "A",
                    "decision_correct": True,
                    "cuda_peak_allocated_bytes": 100 + mode_index,
                }
            )

    summary = summarize_observations(observations)

    assert summary["ar"]["count"] == 3
    assert summary["ar"]["correct_count"] == 3
    assert summary["ar"]["invalid_output_count"] == 0
    assert summary["ar"]["latency_seconds"]["median"] == 2.0
    assert (
        summary["ar"]["latency_by_ordinal_position"]["3"]["latency_seconds"][
            "median"
        ]
        == 3.0
    )


def test_dry_run_records_counterbalanced_protocol() -> None:
    payload = dry_run_payload(
        model_id="example/nld",
        permutation_repeats=2,
        max_new_tokens=32,
        max_thinking_tokens=32,
        seed=1,
        dtype="bf16",
    )

    assert payload["evidence_class"] == "repeatability experiment plan only"
    assert payload["measured_observation_count"] == 36
    assert payload["observations_per_mode"] == 12
    assert payload["warmup_modes"] == ["ar", "dlm", "linear_spec"]
    assert payload["runtime"]["same_loaded_model"] is True
    assert any(
        "torch.cuda.synchronize()" in step
        for step in payload["timing_protocol"]
    )
