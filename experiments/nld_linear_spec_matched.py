from __future__ import annotations

import argparse
import json
import time
from dataclasses import asdict
from pathlib import Path

from experiments.nld_adequate_cost_surface import (
    DEFAULT_DTYPE,
    DEFAULT_MAX_NEW_TOKENS,
    _run_observation,
    build_cost_cases,
)
from experiments.nld_tri_mode import (
    DEFAULT_MAX_THINKING_TOKENS,
    DEFAULT_MODEL_ID,
    DEFAULT_SEED,
    _cuda_memory_snapshot,
    _import_runtime,
    _prepare_prompt,
    _torch_dtype,
)
from experiments.nld_tri_mode_repeatability import _numeric_summary

MODE = "linear_spec"
CASE_ORDERS = (
    (0, 1, 2, 3),
    (3, 2, 1, 0),
    (1, 2, 3, 0),
    (2, 3, 0, 1),
    (0, 3, 2, 1),
    (1, 0, 3, 2),
)


def build_schedule() -> list[dict[str, object]]:
    cases = build_cost_cases()
    rows: list[dict[str, object]] = []
    observation_index = 0
    for repeat_index, order in enumerate(CASE_ORDERS):
        for order_index, case_index in enumerate(order):
            case = cases[case_index]
            rows.append(
                {
                    "observation_index": observation_index,
                    "repeat_index": repeat_index,
                    "order_index": order_index,
                    "case_id": case.case_id,
                    "expected_label": case.expected_label,
                }
            )
            observation_index += 1
    return rows


def summarize(observations: list[dict[str, object]]) -> dict[str, object]:
    return {
        "count": len(observations),
        "correct_count": sum(
            row.get("decision_correct") is True for row in observations
        ),
        "invalid_output_count": sum(
            row.get("parsed_label") is None for row in observations
        ),
        "latency_seconds": _numeric_summary(
            row["elapsed_seconds"]
            for row in observations
            if isinstance(row.get("elapsed_seconds"), (int, float))
        ),
        "generated_token_count": _numeric_summary(
            row["generated_token_count"]
            for row in observations
            if isinstance(row.get("generated_token_count"), (int, float))
        ),
        "nfe": _numeric_summary(
            row["nfe"]
            for row in observations
            if isinstance(row.get("nfe"), (int, float))
        ),
        "tokens_per_forward": _numeric_summary(
            row["tokens_per_forward"]
            for row in observations
            if isinstance(row.get("tokens_per_forward"), (int, float))
        ),
        "cuda_peak_allocated_bytes": _numeric_summary(
            row["cuda_peak_allocated_bytes"]
            for row in observations
            if isinstance(
                row.get("cuda_peak_allocated_bytes"),
                (int, float),
            )
        ),
    }


def dry_run_payload(
    *,
    model_id: str,
    seed: int,
    dtype: str,
) -> dict[str, object]:
    return {
        "evidence_class": "nld linear-spec matched plan only",
        "model_id": model_id,
        "mode": MODE,
        "cases": [asdict(case) for case in build_cost_cases()],
        "schedule": build_schedule(),
        "measured_observation_count": 24,
        "excluded_warmup_count": 1,
        "seed": seed,
        "dtype": dtype,
        "max_new_tokens": DEFAULT_MAX_NEW_TOKENS,
        "max_thinking_tokens": DEFAULT_MAX_THINKING_TOKENS,
    }
