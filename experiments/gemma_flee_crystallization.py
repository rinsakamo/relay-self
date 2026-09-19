from __future__ import annotations

import argparse
import json
from dataclasses import dataclass
from pathlib import Path

from experiments.gemma_skill_narrowing import (
    CASES,
    ObservedLlamaCppProvider,
    _condition_summary,
    _sum_numeric,
    build_request,
)
from relay_self.provenance import Provenance
from relay_self.relay_engine import (
    BoundedChoiceRequest,
    CognitionDatum,
    CognitionMode,
    DecisionStatus,
    RelayEngine,
)

SOURCE = "gemma-flee-crystallization"
ARTIFACT_ALGORITHM = "greedy_lexicographic_ablation_v1"
CONDITIONS = ("before", "after")
ORDER_SCHEDULE = (
    ("before", "after"),
    ("after", "before"),
) * 3


@dataclass(frozen=True, slots=True)
class CrystallizationArtifact:
    skill_id: str
    algorithm: str
    retained_context_keys: tuple[str, ...]
    removed_context_keys: tuple[str, ...]
    training_request_hashes: tuple[str, ...]


def _holdout_value(
    key: str,
    value: object,
    *,
    case_index: int,
) -> object:
    relevant = {
        "threat_nearby",
        "health",
        "route_open:cave",
        "route_open:ridge",
        "shelter:cave",
        "shelter:ridge",
    }
    if key in relevant:
        return value
    if isinstance(value, bool):
        return not value
    if isinstance(value, int):
        return value + 3 * (case_index + 1)
    if isinstance(value, float):
        return round(value + 0.25 * (case_index + 1), 4)
    if isinstance(value, str):
        return f"{value}:holdout:{case_index}"
    if isinstance(value, list):
        return [*value, f"holdout-{case_index}"]
    return value


def build_holdout_broad_request(case, *, case_index: int) -> BoundedChoiceRequest:
    base = build_request(case, condition="broad")
    context = tuple(
        CognitionDatum.from_value(
            datum.key,
            _holdout_value(
                datum.key,
                json.loads(datum.value_json),
                case_index=case_index,
            ),
            Provenance(
                source=SOURCE,
                reference=f"holdout:{case.case_id}:{datum.key}",
            ),
        )
        for datum in base.context
    )
    return BoundedChoiceRequest(
        request_id=f"crystallization:holdout:{case.case_id}",
        instruction=base.instruction,
        intent_id=base.intent_id,
        focus=base.focus,
        choices=base.choices,
        context=context,
    )


def filter_request(
    request: BoundedChoiceRequest,
    *,
    retained_keys: tuple[str, ...] | list[str] | set[str],
) -> BoundedChoiceRequest:
    allowed = set(retained_keys)
    return BoundedChoiceRequest(
        request_id=request.request_id,
        instruction=request.instruction,
        intent_id=request.intent_id,
        focus=request.focus,
        choices=request.choices,
        context=tuple(
            datum
            for datum in request.context
            if datum.key in allowed
        ),
    )


def run_request_episode(
    *,
    provider: ObservedLlamaCppProvider,
    request: BoundedChoiceRequest,
    expected_choice_id: str,
    case_id: str,
    phase: str,
) -> dict[str, object]:
    provider.clear_records()
    result = RelayEngine(provider)(request)
    records = [dict(record) for record in provider.records]
    correct = (
        result.status is DecisionStatus.RESOLVED
        and result.choice_id == expected_choice_id
    )
    inadmissible = any(
        "inadmissible" in attempt.reason
        for attempt in result.attempts
    )
    bounded_record = next(
        (
            record
            for record in records
            if record.get("mode") == CognitionMode.BOUNDED.value
        ),
        None,
    )
    think_record = next(
        (
            record
            for record in records
            if record.get("mode") == CognitionMode.THINK.value
        ),
        None,
    )
    return {
        "case_id": case_id,
        "phase": phase,
        "expected_choice_id": expected_choice_id,
        "context_datum_count": len(request.context),
        "context_keys": [datum.key for datum in request.context],
        "final_status": result.status.value,
        "final_choice_id": result.choice_id,
        "decision_correct": correct,
        "escalated": result.escalated,
        "inadmissible_attempt": inadmissible,
        "model_call_count": len(records),
        "total_model_latency_seconds": _sum_numeric(
            records,
            "elapsed_seconds",
        ),
        "total_prompt_tokens": _sum_numeric(
            records,
            "prompt_tokens",
        ),
        "total_completion_tokens": _sum_numeric(
            records,
            "completion_tokens",
        ),
        "total_request_json_bytes": _sum_numeric(
            records,
            "request_json_bytes",
        ),
        "bounded_latency_seconds": (
            bounded_record.get("elapsed_seconds")
            if isinstance(bounded_record, dict)
            else None
        ),
        "think_latency_seconds": (
            think_record.get("elapsed_seconds")
            if isinstance(think_record, dict)
            else None
        ),
        "attempts": [
            {
                "mode": attempt.mode.value,
                "status": attempt.status.value,
                "choice_id": attempt.choice_id,
                "reason": attempt.reason,
            }
            for attempt in result.attempts
        ],
        "provider_calls": records,
    }


def episode_is_training_success(row: dict[str, object]) -> bool:
    return (
        row.get("decision_correct") is True
        and row.get("escalated") is False
        and row.get("model_call_count") == 1
        and row.get("inadmissible_attempt") is False
    )
