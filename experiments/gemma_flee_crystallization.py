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


def build_holdout_schedule() -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []
    observation_index = 0
    for case in CASES:
        for permutation_index, order in enumerate(ORDER_SCHEDULE):
            for order_index, condition in enumerate(order):
                rows.append(
                    {
                        "observation_index": observation_index,
                        "case_id": case.case_id,
                        "expected_choice_id": case.expected_choice_id,
                        "permutation_index": permutation_index,
                        "order_index": order_index,
                        "condition": condition,
                    }
                )
                observation_index += 1
    return rows


def run_holdout(
    *,
    provider: ObservedLlamaCppProvider,
    retained_keys: tuple[str, ...],
) -> dict[str, object]:
    case_index = {
        case.case_id: index
        for index, case in enumerate(CASES)
    }
    broad_requests = {
        case.case_id: build_holdout_broad_request(
            case,
            case_index=case_index[case.case_id],
        )
        for case in CASES
    }
    cases = {case.case_id: case for case in CASES}

    observations: list[dict[str, object]] = []
    for schedule_row in build_holdout_schedule():
        case = cases[str(schedule_row["case_id"])]
        condition = str(schedule_row["condition"])
        broad = broad_requests[case.case_id]
        request = (
            broad
            if condition == "before"
            else filter_request(
                broad,
                retained_keys=retained_keys,
            )
        )
        row = run_request_episode(
            provider=provider,
            request=request,
            expected_choice_id=case.expected_choice_id,
            case_id=case.case_id,
            phase=f"holdout:{condition}",
        )
        row["condition"] = condition
        row.update(schedule_row)
        observations.append(row)

    by_condition = {
        condition: _condition_summary(
            [
                row
                for row in observations
                if row.get("condition") == condition
            ]
        )
        for condition in CONDITIONS
    }
    by_case_condition = {
        case.case_id: {
            condition: _condition_summary(
                [
                    row
                    for row in observations
                    if row.get("case_id") == case.case_id
                    and row.get("condition") == condition
                ]
            )
            for condition in CONDITIONS
        }
        for case in CASES
    }
    eligible = all(
        by_condition[condition].get("count") == 24
        and by_condition[condition].get("correct_count") == 24
        and by_condition[condition].get("final_unresolved_count") == 0
        for condition in CONDITIONS
    )
    return {
        "observations": observations,
        "summary": {
            "by_condition": by_condition,
            "by_case_condition": by_case_condition,
            "future_cost_comparison_eligible": eligible,
        },
    }


def dry_run_payload() -> dict[str, object]:
    training_request = build_request(CASES[0], condition="broad")
    candidate_keys = tuple(
        sorted(datum.key for datum in training_request.context)
    )
    return {
        "evidence_class": "gemma flee crystallization plan only",
        "artifact_algorithm": ARTIFACT_ALGORITHM,
        "candidate_keys": list(candidate_keys),
        "candidate_key_count": len(candidate_keys),
        "training_case_count": len(CASES),
        "ordinary_training_episode_count": len(CASES),
        "maximum_ablation_episode_count": (
            len(candidate_keys) * len(CASES)
        ),
        "holdout_schedule": build_holdout_schedule(),
        "holdout_measured_episode_count": 48,
        "holdout_observations_per_case_condition": 6,
        "excluded_warmups": [
            CognitionMode.BOUNDED.value,
            CognitionMode.THINK.value,
        ],
        "non_claims": [
            "artifact induction is experiment-local, not a production Skill registry",
            "experience-dependent artifact induction is not neural weight learning",
            "model output is not World truth or Action authorization",
        ],
    }


def run_actual(
    *,
    endpoint: str,
    model: str,
    timeout: float,
) -> dict[str, object]:
    provider = ObservedLlamaCppProvider(
        endpoint=endpoint,
        model=model,
        timeout=timeout,
    )
    warmup_request = build_request(CASES[0], condition="broad")
    warmups: list[dict[str, object]] = []
    for mode in (CognitionMode.BOUNDED, CognitionMode.THINK):
        provider.clear_records()
        provider(warmup_request, mode=mode)
        warmups.extend(
            {
                **record,
                "warmup": True,
            }
            for record in provider.records
        )

    induction = induce_artifact(provider=provider)
    artifact = induction["artifact"]
    if not isinstance(artifact, dict):
        raise RuntimeError("artifact induction did not return an artifact")
    retained_raw = artifact.get("retained_context_keys")
    if not isinstance(retained_raw, list) or not all(
        isinstance(key, str) for key in retained_raw
    ):
        raise RuntimeError(
            "artifact retained_context_keys is invalid"
        )
    retained_keys = tuple(retained_raw)
    holdout = run_holdout(
        provider=provider,
        retained_keys=retained_keys,
    )

    removed_raw = artifact.get("removed_context_keys")
    removed_count = (
        len(removed_raw) if isinstance(removed_raw, list) else 0
    )
    holdout_summary = holdout["summary"]
    if not isinstance(holdout_summary, dict):
        raise RuntimeError("holdout summary is invalid")

    return {
        "evidence_class": "actual-model gemma flee crystallization",
        "endpoint": endpoint,
        "model": model,
        "warmups": warmups,
        "induction": induction,
        "holdout": holdout,
        "summary": {
            "artifact_induction_qualified": induction.get(
                "baseline_qualified"
            ),
            "retained_context_key_count": len(retained_keys),
            "removed_context_key_count": removed_count,
            "future_cost_comparison_eligible": holdout_summary.get(
                "future_cost_comparison_eligible"
            ),
        },
    }


def write_payload(
    payload: dict[str, object],
    output: str | None,
    artifact_output: str | None,
) -> None:
    serialized = json.dumps(
        payload,
        ensure_ascii=False,
        indent=2,
        sort_keys=True,
    )
    if output is None:
        print(serialized)
    else:
        path = Path(output)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(serialized + "\n", encoding="utf-8")
        print(path)

    if artifact_output is not None:
        induction = payload.get("induction")
        artifact = (
            induction.get("artifact")
            if isinstance(induction, dict)
            else None
        )
        if not isinstance(artifact, dict):
            raise RuntimeError(
                "artifact output requested but no artifact exists"
            )
        artifact_path = Path(artifact_output)
        artifact_path.parent.mkdir(parents=True, exist_ok=True)
        artifact_path.write_text(
            json.dumps(
                artifact,
                ensure_ascii=False,
                indent=2,
                sort_keys=True,
            )
            + "\n",
            encoding="utf-8",
        )


def main() -> None:
    parser = argparse.ArgumentParser(
        description=(
            "Induce and evaluate one experience-dependent FLEE "
            "context crystallization artifact."
        )
    )
    parser.add_argument("--run", action="store_true")
    parser.add_argument(
        "--endpoint",
        default="http://127.0.0.1:1234/v1/chat/completions",
    )
    parser.add_argument("--model", default="gemma-local")
    parser.add_argument("--timeout", type=float, default=600.0)
    parser.add_argument("--output")
    parser.add_argument("--artifact-output")
    args = parser.parse_args()

    if args.timeout <= 0:
        parser.error("--timeout must be positive")

    try:
        payload = (
            run_actual(
                endpoint=args.endpoint,
                model=args.model,
                timeout=args.timeout,
            )
            if args.run
            else dry_run_payload()
        )
        write_payload(
            payload,
            args.output,
            args.artifact_output,
        )
    except (RuntimeError, ValueError) as exc:
        parser.error(str(exc))


if __name__ == "__main__":
    main()
