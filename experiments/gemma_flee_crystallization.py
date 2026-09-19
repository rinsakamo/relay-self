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


def _cost_totals(rows: list[dict[str, object]]) -> dict[str, object]:
    return {
        "episode_count": len(rows),
        "model_call_count": sum(
            int(row["model_call_count"])
            for row in rows
            if isinstance(row.get("model_call_count"), int)
        ),
        "prompt_tokens": sum(
            int(row["total_prompt_tokens"])
            for row in rows
            if isinstance(row.get("total_prompt_tokens"), int)
        ),
        "completion_tokens": sum(
            int(row["total_completion_tokens"])
            for row in rows
            if isinstance(row.get("total_completion_tokens"), int)
        ),
        "request_json_bytes": sum(
            int(row["total_request_json_bytes"])
            for row in rows
            if isinstance(row.get("total_request_json_bytes"), int)
        ),
        "model_latency_seconds": sum(
            float(row["total_model_latency_seconds"])
            for row in rows
            if isinstance(
                row.get("total_model_latency_seconds"),
                (int, float),
            )
        ),
    }


def _first_request_hash(row: dict[str, object]) -> str | None:
    calls = row.get("provider_calls")
    if not isinstance(calls, list) or not calls:
        return None
    first = calls[0]
    if not isinstance(first, dict):
        return None
    value = first.get("request_hash")
    return value if isinstance(value, str) else None


def induce_artifact(
    *,
    provider: ObservedLlamaCppProvider,
) -> dict[str, object]:
    training_requests = {
        case.case_id: build_request(case, condition="broad")
        for case in CASES
    }
    expected_key_sets = {
        tuple(sorted(datum.key for datum in request.context))
        for request in training_requests.values()
    }
    if len(expected_key_sets) != 1:
        raise RuntimeError(
            "training BROAD requests do not share one context-key surface"
        )
    all_keys = tuple(sorted(next(iter(expected_key_sets))))

    baseline_rows = [
        run_request_episode(
            provider=provider,
            request=training_requests[case.case_id],
            expected_choice_id=case.expected_choice_id,
            case_id=case.case_id,
            phase="training_baseline",
        )
        for case in CASES
    ]
    baseline_qualified = all(
        episode_is_training_success(row)
        for row in baseline_rows
    )

    retained = list(all_keys)
    trials: list[dict[str, object]] = []
    ablation_rows: list[dict[str, object]] = []

    if baseline_qualified:
        for candidate_key in all_keys:
            if candidate_key not in retained:
                continue
            trial_retained = tuple(
                key for key in retained if key != candidate_key
            )
            rows = [
                run_request_episode(
                    provider=provider,
                    request=filter_request(
                        training_requests[case.case_id],
                        retained_keys=trial_retained,
                    ),
                    expected_choice_id=case.expected_choice_id,
                    case_id=case.case_id,
                    phase=f"ablation:{candidate_key}",
                )
                for case in CASES
            ]
            ablation_rows.extend(rows)
            accepted = all(
                episode_is_training_success(row)
                for row in rows
            )
            if accepted:
                retained = list(trial_retained)
            trials.append(
                {
                    "candidate_key": candidate_key,
                    "accepted": accepted,
                    "trial_retained_keys": list(trial_retained),
                    "retained_keys_after_trial": list(retained),
                    "episodes": rows,
                }
            )

    retained_tuple = tuple(sorted(retained))
    removed_tuple = tuple(
        key for key in all_keys if key not in set(retained_tuple)
    )
    request_hashes = tuple(
        value
        for value in (
            _first_request_hash(row) for row in baseline_rows
        )
        if value is not None
    )
    artifact = CrystallizationArtifact(
        skill_id="FLEE",
        algorithm=ARTIFACT_ALGORITHM,
        retained_context_keys=retained_tuple,
        removed_context_keys=removed_tuple,
        training_request_hashes=request_hashes,
    )
    return {
        "baseline_qualified": baseline_qualified,
        "artifact": {
            "skill_id": artifact.skill_id,
            "algorithm": artifact.algorithm,
            "retained_context_keys": list(
                artifact.retained_context_keys
            ),
            "removed_context_keys": list(
                artifact.removed_context_keys
            ),
            "training_request_hashes": list(
                artifact.training_request_hashes
            ),
        },
        "baseline_episodes": baseline_rows,
        "ablation_trials": trials,
        "acquisition_cost": {
            "ordinary_training": _cost_totals(baseline_rows),
            "ablation_search": _cost_totals(ablation_rows),
            "gross": _cost_totals(
                [*baseline_rows, *ablation_rows]
            ),
        },
    }
