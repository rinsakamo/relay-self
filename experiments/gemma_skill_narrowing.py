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
from experiments.nld_tri_mode_repeatability import _numeric_summary

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
        request_id=f"skill-narrowing:{case.case_id}:{condition}",
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
