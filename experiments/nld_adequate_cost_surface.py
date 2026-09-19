from __future__ import annotations

import argparse
import collections
import json
import time
from dataclasses import asdict
from pathlib import Path

from experiments.nld_lexical_remapping_generalization import (
    LexicalCase,
    build_cases,
    parsed_destination,
)
from experiments.nld_tri_mode import (
    DEFAULT_MAX_THINKING_TOKENS,
    DEFAULT_MODEL_ID,
    DEFAULT_MODES,
    DEFAULT_SEED,
    _cuda_memory_snapshot,
    _import_runtime,
    _nfe_value,
    _prepare_prompt,
    _reset_seed,
    _torch_dtype,
    dispatch_generation,
    mode_arguments,
    parse_decision,
)
from experiments.nld_tri_mode_repeatability import (
    MODE_PERMUTATIONS,
    _numeric_summary,
)

DEFAULT_DTYPE = "bf16"
DEFAULT_MAX_NEW_TOKENS = 32


def build_cost_cases() -> tuple[LexicalCase, ...]:
    return tuple(
        case for case in build_cases() if case.family_id == "color"
    )


def build_schedule() -> list[dict[str, object]]:
    schedule: list[dict[str, object]] = []
    observation_index = 0
    for case in build_cost_cases():
        for permutation_index, order in enumerate(MODE_PERMUTATIONS):
            for ordinal_position, mode in enumerate(order, start=1):
                schedule.append(
                    {
                        "observation_index": observation_index,
                        "case_id": case.case_id,
                        "expected_label": case.expected_label,
                        "feasible_destination": case.feasible_destination,
                        "permutation_index": permutation_index,
                        "order": list(order),
                        "ordinal_position": ordinal_position,
                        "mode": mode,
                    }
                )
                observation_index += 1
    return schedule


def decision_prefix_events(
    tokenizer: object,
    token_ids: list[int],
) -> list[dict[str, object]]:
    events: list[dict[str, object]] = []
    for index in range(1, len(token_ids) + 1):
        text = tokenizer.decode(
            token_ids[:index],
            skip_special_tokens=True,
        )
        parsed = parse_decision(text)
        events.append(
            {
                "token_index_1based": index,
                "parsed_label": parsed.label,
                "parse_source": parsed.source,
                "explicit_label": parsed.explicit_label,
                "fallback_label": parsed.fallback_label,
            }
        )
    return events


def first_event_index(
    events: list[dict[str, object]],
    *,
    source: str | None = None,
    require_label: bool = False,
) -> int | None:
    for event in events:
        if source is not None and event.get("parse_source") != source:
            continue
        if require_label and event.get("parsed_label") is None:
            continue
        value = event.get("token_index_1based")
        if isinstance(value, int):
            return value
    return None


def _count_values(
    rows: list[dict[str, object]],
    key: str,
) -> dict[str, int]:
    counts: collections.Counter[str] = collections.Counter()
    for row in rows:
        value = row.get(key)
        counts[str(value) if value is not None else "INVALID"] += 1
    return dict(sorted(counts.items()))
