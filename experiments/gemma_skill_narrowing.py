from __future__ import annotations

import argparse
import collections
import hashlib
import json
import time
import urllib.error
import urllib.request
from dataclasses import dataclass
from pathlib import Path

from adapters.llama_cpp.relay_engine import (
    parse_llama_cpp_decision,
    render_llama_cpp_request,
)
from experiments.nld_tri_mode_repeatability import _numeric_summary
from relay_self.provenance import Provenance
from relay_self.relay_engine import (
    BoundedChoice,
    BoundedChoiceRequest,
    CognitionDatum,
    CognitionMode,
    DecisionStatus,
    ProviderDecision,
    RelayEngine,
)

SOURCE = "gemma-skill-narrowing"
CONDITIONS = ("broad", "narrow")
ORDER_SCHEDULE = (
    ("broad", "narrow"),
    ("narrow", "broad"),
) * 3


@dataclass(frozen=True, slots=True)
class NarrowingCase:
    case_id: str
    route_cave: bool
    route_ridge: bool
    shelter_cave: bool
    shelter_ridge: bool
    expected_choice_id: str


CASES = (
    NarrowingCase(
        case_id="cave_only",
        route_cave=True,
        route_ridge=False,
        shelter_cave=True,
        shelter_ridge=False,
        expected_choice_id="cave",
    ),
    NarrowingCase(
        case_id="ridge_only",
        route_cave=False,
        route_ridge=True,
        shelter_cave=True,
        shelter_ridge=False,
        expected_choice_id="ridge",
    ),
    NarrowingCase(
        case_id="both_cave_shelter",
        route_cave=True,
        route_ridge=True,
        shelter_cave=True,
        shelter_ridge=False,
        expected_choice_id="cave",
    ),
    NarrowingCase(
        case_id="both_ridge_shelter",
        route_cave=True,
        route_ridge=True,
        shelter_cave=False,
        shelter_ridge=True,
        expected_choice_id="ridge",
    ),
)

BROAD_DISTRACTORS: tuple[tuple[str, object], ...] = (
    ("hunger", 14),
    ("saturation", 3.5),
    ("inventory:oak_log", 12),
    ("inventory:cobblestone", 31),
    ("inventory:torch", 9),
    ("tool:pickaxe_durability", 0.62),
    ("xp_level", 7),
    ("crafting_queue", ["stone_pickaxe"]),
    ("furnace_active", False),
    ("farm:wheat_mature_count", 3),
    ("storage_free_slots", 11),
    ("conversation_topic", "base organization"),
    ("companion_speaking", False),
    ("chat_unread_count", 2),
    ("recipe_unlocked_count", 18),
    ("map_marker_count", 4),
)


def _provenance(reference: str) -> Provenance:
    return Provenance(source=SOURCE, reference=reference)


def _datum(key: str, value: object, reference: str) -> CognitionDatum:
    return CognitionDatum.from_value(
        key,
        value,
        _provenance(reference),
    )


def relevant_context(case: NarrowingCase) -> tuple[CognitionDatum, ...]:
    return (
        _datum("threat_nearby", True, f"{case.case_id}:threat"),
        _datum("health", 6, f"{case.case_id}:health"),
        _datum(
            "route_open:cave",
            case.route_cave,
            f"{case.case_id}:route:cave",
        ),
        _datum(
            "route_open:ridge",
            case.route_ridge,
            f"{case.case_id}:route:ridge",
        ),
        _datum(
            "shelter:cave",
            case.shelter_cave,
            f"{case.case_id}:shelter:cave",
        ),
        _datum(
            "shelter:ridge",
            case.shelter_ridge,
            f"{case.case_id}:shelter:ridge",
        ),
    )


def broad_context(case: NarrowingCase) -> tuple[CognitionDatum, ...]:
    relevant = relevant_context(case)
    distractors = tuple(
        _datum(key, value, f"{case.case_id}:broad:{index}:{key}")
        for index, (key, value) in enumerate(BROAD_DISTRACTORS)
    )
    return relevant + distractors


def build_request(
    case: NarrowingCase,
    *,
    condition: str,
) -> BoundedChoiceRequest:
    if condition not in CONDITIONS:
        raise ValueError(f"unsupported condition: {condition}")
    context = (
        broad_context(case)
        if condition == "broad"
        else relevant_context(case)
    )
    return BoundedChoiceRequest(
        request_id=f"skill-narrowing:{case.case_id}",
        instruction=(
            "Choose the safer currently reachable destination for the active "
            "FLEE skill. A destination is admissible only when route_open is "
            "true. If both destinations are reachable, prefer the one whose "
            "shelter fact is true. Use only supplied context."
        ),
        intent_id="intent-reach-safety",
        focus="FLEE",
        choices=(
            BoundedChoice("cave", "Destination cave"),
            BoundedChoice("ridge", "Destination ridge"),
        ),
        context=context,
    )


def build_schedule() -> list[dict[str, object]]:
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


def _canonical_json(value: object) -> str:
    return json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    )


def _sha256_json(value: object) -> str:
    return hashlib.sha256(
        _canonical_json(value).encode("utf-8")
    ).hexdigest()


def _post_json(
    endpoint: str,
    payload: dict[str, object],
    *,
    timeout: float,
) -> dict[str, object]:
    request = urllib.request.Request(
        endpoint,
        data=_canonical_json(payload).encode("utf-8"),
        headers={
            "Content-Type": "application/json",
            "Accept": "application/json",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(
            request,
            timeout=timeout,
        ) as response:
            body = json.loads(response.read().decode("utf-8"))
    except (
        urllib.error.URLError,
        TimeoutError,
        UnicodeDecodeError,
        json.JSONDecodeError,
    ) as exc:
        raise RuntimeError(
            f"llama.cpp request failed: {type(exc).__name__}: {exc}"
        ) from exc
    if not isinstance(body, dict):
        raise RuntimeError("llama.cpp response must be a JSON object")
    return body


def _response_content(body: dict[str, object]) -> str:
    choices = body.get("choices")
    if not isinstance(choices, list) or len(choices) != 1:
        raise RuntimeError("llama.cpp response requires exactly one choice")
    choice = choices[0]
    if not isinstance(choice, dict):
        raise RuntimeError("llama.cpp choice must be an object")
    message = choice.get("message")
    if not isinstance(message, dict):
        raise RuntimeError("llama.cpp choice message is missing")
    content = message.get("content")
    if not isinstance(content, str):
        raise RuntimeError("llama.cpp response content must be text")
    return content


def _usage_int(
    body: dict[str, object],
    key: str,
) -> int | None:
    usage = body.get("usage")
    if not isinstance(usage, dict):
        return None
    value = usage.get(key)
    return value if isinstance(value, int) else None


class ObservedLlamaCppProvider:
    def __init__(
        self,
        *,
        endpoint: str,
        model: str,
        timeout: float,
    ) -> None:
        self.endpoint = endpoint
        self.model = model
        self.timeout = timeout
        self.records: list[dict[str, object]] = []

    def clear_records(self) -> None:
        self.records.clear()

    def __call__(
        self,
        request: BoundedChoiceRequest,
        *,
        mode: CognitionMode,
    ) -> ProviderDecision:
        request_body = render_llama_cpp_request(
            request,
            mode=mode,
            model=self.model,
        )
        encoded = _canonical_json(request_body).encode("utf-8")
        started = time.perf_counter()
        response_body = _post_json(
            self.endpoint,
            request_body,
            timeout=self.timeout,
        )
        elapsed_seconds = time.perf_counter() - started
        raw_text = _response_content(response_body)
        decision = parse_llama_cpp_decision(
            raw_text,
            mode=mode,
        )
        choices = response_body.get("choices")
        finish_reason = None
        if (
            isinstance(choices, list)
            and choices
            and isinstance(choices[0], dict)
        ):
            finish_reason = choices[0].get("finish_reason")

        self.records.append(
            {
                "mode": mode.value,
                "elapsed_seconds": elapsed_seconds,
                "request_json_bytes": len(encoded),
                "request_hash": _sha256_json(request_body),
                "response_hash": _sha256_json(response_body),
                "prompt_tokens": _usage_int(
                    response_body,
                    "prompt_tokens",
                ),
                "completion_tokens": _usage_int(
                    response_body,
                    "completion_tokens",
                ),
                "raw_text": raw_text,
                "provider_status": decision.status.value,
                "provider_choice_id": decision.choice_id,
                "provider_reason": decision.reason,
                "finish_reason": finish_reason,
                "usage": response_body.get("usage"),
                "timings": response_body.get("timings"),
            }
        )
        return decision


def _sum_numeric(
    records: list[dict[str, object]],
    key: str,
) -> int | float | None:
    values = [
        record[key]
        for record in records
        if isinstance(record.get(key), (int, float))
    ]
    if len(values) != len(records):
        return None
    return sum(values)


def run_episode(
    *,
    provider: ObservedLlamaCppProvider,
    case: NarrowingCase,
    condition: str,
) -> dict[str, object]:
    request = build_request(case, condition=condition)
    provider.clear_records()
    result = RelayEngine(provider)(request)
    records = [dict(record) for record in provider.records]
    correct = (
        result.status is DecisionStatus.RESOLVED
        and result.choice_id == case.expected_choice_id
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
        "case_id": case.case_id,
        "condition": condition,
        "expected_choice_id": case.expected_choice_id,
        "context_datum_count": len(request.context),
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


def _condition_summary(
    rows: list[dict[str, object]],
) -> dict[str, object]:
    final_choices = collections.Counter(
        str(row.get("final_choice_id"))
        if row.get("final_choice_id") is not None
        else "UNRESOLVED"
        for row in rows
    )
    return {
        "count": len(rows),
        "correct_count": sum(
            row.get("decision_correct") is True for row in rows
        ),
        "final_unresolved_count": sum(
            row.get("final_status") == DecisionStatus.UNRESOLVED.value
            for row in rows
        ),
        "inadmissible_attempt_count": sum(
            row.get("inadmissible_attempt") is True
            for row in rows
        ),
        "bounded_resolution_count": sum(
            row.get("model_call_count") == 1
            and row.get("final_status") == DecisionStatus.RESOLVED.value
            for row in rows
        ),
        "think_escalation_count": sum(
            row.get("escalated") is True for row in rows
        ),
        "final_choice_distribution": dict(sorted(final_choices.items())),
        "context_datum_count": _numeric_summary(
            row["context_datum_count"]
            for row in rows
            if isinstance(row.get("context_datum_count"), (int, float))
        ),
        "model_call_count": _numeric_summary(
            row["model_call_count"]
            for row in rows
            if isinstance(row.get("model_call_count"), (int, float))
        ),
        "total_model_latency_seconds": _numeric_summary(
            row["total_model_latency_seconds"]
            for row in rows
            if isinstance(
                row.get("total_model_latency_seconds"),
                (int, float),
            )
        ),
        "bounded_latency_seconds": _numeric_summary(
            row["bounded_latency_seconds"]
            for row in rows
            if isinstance(row.get("bounded_latency_seconds"), (int, float))
        ),
        "think_latency_seconds": _numeric_summary(
            row["think_latency_seconds"]
            for row in rows
            if isinstance(row.get("think_latency_seconds"), (int, float))
        ),
        "total_prompt_tokens": _numeric_summary(
            row["total_prompt_tokens"]
            for row in rows
            if isinstance(row.get("total_prompt_tokens"), (int, float))
        ),
        "total_completion_tokens": _numeric_summary(
            row["total_completion_tokens"]
            for row in rows
            if isinstance(
                row.get("total_completion_tokens"),
                (int, float),
            )
        ),
        "total_request_json_bytes": _numeric_summary(
            row["total_request_json_bytes"]
            for row in rows
            if isinstance(
                row.get("total_request_json_bytes"),
                (int, float),
            )
        ),
    }


def summarize(
    observations: list[dict[str, object]],
) -> dict[str, object]:
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
    eligible = all(
        isinstance(by_condition[condition], dict)
        and by_condition[condition].get("count") == 24
        and by_condition[condition].get("correct_count") == 24
        and by_condition[condition].get("final_unresolved_count") == 0
        for condition in CONDITIONS
    )
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
    return {
        "by_condition": by_condition,
        "by_case_condition": by_case_condition,
        "cost_comparison_eligible": eligible,
    }


def dry_run_payload() -> dict[str, object]:
    return {
        "evidence_class": "gemma skill narrowing plan only",
        "conditions": list(CONDITIONS),
        "cases": [
            {
                "case_id": case.case_id,
                "expected_choice_id": case.expected_choice_id,
            }
            for case in CASES
        ],
        "schedule": build_schedule(),
        "measured_episode_count": 48,
        "observations_per_case_condition": 6,
        "excluded_warmups": [
            CognitionMode.BOUNDED.value,
            CognitionMode.THINK.value,
        ],
        "broad_distractor_count": len(BROAD_DISTRACTORS),
        "non_claims": [
            "narrowing evidence is not experience-dependent crystallization",
            "lower cognition cost does not authorize an Action",
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
    warmup_request = build_request(CASES[0], condition="narrow")
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

    cases = {case.case_id: case for case in CASES}
    observations: list[dict[str, object]] = []
    for schedule_row in build_schedule():
        case = cases[str(schedule_row["case_id"])]
        episode = run_episode(
            provider=provider,
            case=case,
            condition=str(schedule_row["condition"]),
        )
        episode.update(schedule_row)
        observations.append(episode)

    return {
        "evidence_class": "actual-model gemma skill narrowing",
        "endpoint": endpoint,
        "model": model,
        "warmups": warmups,
        "observations": observations,
        "summary": summarize(observations),
    }


def write_payload(
    payload: dict[str, object],
    output: str | None,
) -> None:
    serialized = json.dumps(
        payload,
        ensure_ascii=False,
        indent=2,
        sort_keys=True,
    )
    if output is None:
        print(serialized)
        return
    path = Path(output)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(serialized + "\n", encoding="utf-8")
    print(path)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Measure Gemma cognition cost under FLEE context narrowing."
    )
    parser.add_argument("--run", action="store_true")
    parser.add_argument(
        "--endpoint",
        default="http://127.0.0.1:1234/v1/chat/completions",
    )
    parser.add_argument("--model", default="gemma-local")
    parser.add_argument("--timeout", type=float, default=600.0)
    parser.add_argument("--output")
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
    except (RuntimeError, ValueError) as exc:
        parser.error(str(exc))

    write_payload(payload, args.output)


if __name__ == "__main__":
    main()
