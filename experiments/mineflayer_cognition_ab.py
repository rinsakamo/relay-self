from __future__ import annotations

import argparse
import hashlib
import json
import os
import urllib.error
import urllib.parse
import urllib.request
from collections import Counter
from dataclasses import dataclass
from typing import Any

from experiments.mineflayer_viability_relay import compile_cognition_payload, respawn_trace

SYSTEM_INSTRUCTION = (
    "Choose exactly one candidate plan for the stated task using only the supplied data. "
    "Return one JSON object with exactly one key, plan_id. Do not add prose."
)
TASK = {
    "instruction": "Reach the target location efficiently.",
    "target": {"x": -8.0, "y": 64.0, "z": 0.0},
}
CANDIDATE_PLANS = (
    {
        "plan_id": "direct",
        "waypoints": [
            {"x": 2.0, "y": 64.0, "z": 0.0},
            {"x": -8.0, "y": 64.0, "z": 0.0},
        ],
    },
    {
        "plan_id": "detour",
        "waypoints": [
            {"x": 10.0, "y": 64.0, "z": -10.0},
            {"x": -8.0, "y": 64.0, "z": -10.0},
            {"x": -8.0, "y": 64.0, "z": 0.0},
        ],
    },
    {
        "plan_id": "observe",
        "waypoints": [{"x": 10.0, "y": 64.0, "z": 10.0}],
    },
)
PLAN_IDS = frozenset(plan["plan_id"] for plan in CANDIDATE_PLANS)

OBSERVATIONS_ONLY = "observationsOnly"
WITH_HEALTH_GRADIENT = "withHealthGradient"
NEUTRAL_OBSERVATIONS_ONLY = "neutralObservationsOnly"
NEUTRAL_WITH_GRADIENT = "neutralWithGradient"
CONDITIONS = (
    OBSERVATIONS_ONLY,
    WITH_HEALTH_GRADIENT,
    NEUTRAL_OBSERVATIONS_ONLY,
    NEUTRAL_WITH_GRADIENT,
)

SIGNAL_SEMANTICS = {
    "negative": "adverse_direction",
    "zero": "neutral_direction",
    "positive": "favorable_direction",
}
KEY_ALIASES = {
    "health": "resource_0",
    "food": "resource_1",
    "oxygenLevel": "resource_2",
    "hurtSource": "event_source",
    "valueGradient": "signal_0",
    "field": "source_channel",
}
EVENT_ALIASES = {
    "health": "event_0",
    "entityHurt": "event_1",
    "death": "event_2",
    "respawn": "event_3",
    "breath": "event_4",
}
VALUE_ALIASES = {
    "PrismarineJS/mineflayer": "opaque_fixture",
    "bot.health": "resource_0",
}


@dataclass(frozen=True)
class ParsedChoice:
    plan_id: str | None
    error: str | None


def _canonical_json(value: object) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def _request_hash(request_body: dict[str, object]) -> str:
    return hashlib.sha256(_canonical_json(request_body).encode("utf-8")).hexdigest()


def _neutralize(value: object) -> object:
    if isinstance(value, dict):
        result: dict[str, object] = {}
        for key, item in value.items():
            alias = KEY_ALIASES.get(key, key)
            if key == "events" and isinstance(item, list):
                result[alias] = [EVENT_ALIASES.get(str(event), str(event)) for event in item]
            else:
                result[alias] = _neutralize(item)
        return result
    if isinstance(value, list):
        return [_neutralize(item) for item in value]
    if isinstance(value, str):
        return VALUE_ALIASES.get(value, value)
    return value


def build_request(
    *,
    model: str,
    include_gradient: bool,
    neutral_labels: bool = False,
) -> dict[str, object]:
    history = compile_cognition_payload(respawn_trace(), include_gradient=include_gradient)
    if neutral_labels:
        history = _neutralize(history)
        if not isinstance(history, dict):
            raise AssertionError("neutralized history must remain an object")
    user_payload = {
        "task": TASK,
        "candidate_plans": CANDIDATE_PLANS,
        "signal_semantics": SIGNAL_SEMANTICS,
        "history": history,
    }
    return {
        "model": model,
        "temperature": 0,
        "max_tokens": 32,
        "messages": [
            {"role": "system", "content": SYSTEM_INSTRUCTION},
            {"role": "user", "content": _canonical_json(user_payload)},
        ],
    }


def _bundle(
    *,
    model: str,
    include_gradient: bool,
    neutral_labels: bool,
) -> dict[str, object]:
    request = build_request(
        model=model,
        include_gradient=include_gradient,
        neutral_labels=neutral_labels,
    )
    return {
        "request": request,
        "requestHash": _request_hash(request),
    }


def render_ab_requests(model: str) -> dict[str, object]:
    return {
        OBSERVATIONS_ONLY: _bundle(
            model=model,
            include_gradient=False,
            neutral_labels=False,
        ),
        WITH_HEALTH_GRADIENT: _bundle(
            model=model,
            include_gradient=True,
            neutral_labels=False,
        ),
        NEUTRAL_OBSERVATIONS_ONLY: _bundle(
            model=model,
            include_gradient=False,
            neutral_labels=True,
        ),
        NEUTRAL_WITH_GRADIENT: _bundle(
            model=model,
            include_gradient=True,
            neutral_labels=True,
        ),
    }


def _normalize_choice_text(raw_text: str) -> str:
    stripped = raw_text.strip()
    lines = stripped.splitlines()
    if (
        len(lines) >= 3
        and lines[0] == "```json"
        and lines[-1] == "```"
        and all("```" not in line for line in lines[1:-1])
    ):
        return "\n".join(lines[1:-1]).strip()
    return stripped


def parse_choice(raw_text: str) -> ParsedChoice:
    try:
        value = json.loads(_normalize_choice_text(raw_text))
    except json.JSONDecodeError as exc:
        return ParsedChoice(plan_id=None, error=f"invalid_json:{exc.msg}")
    if not isinstance(value, dict):
        return ParsedChoice(plan_id=None, error="response_not_object")
    if set(value) != {"plan_id"}:
        return ParsedChoice(plan_id=None, error="response_schema_mismatch")
    plan_id = value.get("plan_id")
    if not isinstance(plan_id, str):
        return ParsedChoice(plan_id=None, error="missing_plan_id")
    if plan_id not in PLAN_IDS:
        return ParsedChoice(plan_id=None, error="unknown_plan_id")
    return ParsedChoice(plan_id=plan_id, error=None)


def endpoint_metadata(endpoint: str) -> str:
    parsed = urllib.parse.urlsplit(endpoint)
    return urllib.parse.urlunsplit((parsed.scheme, parsed.netloc, parsed.path, "", ""))


def _extract_content(response_body: dict[str, Any]) -> str:
    try:
        content = response_body["choices"][0]["message"]["content"]
    except (KeyError, IndexError, TypeError) as exc:
        raise ValueError("response missing choices[0].message.content") from exc
    if not isinstance(content, str):
        raise ValueError("message content must be a string")
    return content


def call_openai_compatible(
    *,
    endpoint: str,
    request_body: dict[str, object],
    api_key: str | None,
    timeout: float,
) -> str:
    headers = {"Content-Type": "application/json"}
    if api_key:
        headers["Authorization"] = f"Bearer {api_key}"
    request = urllib.request.Request(
        endpoint,
        data=_canonical_json(request_body).encode("utf-8"),
        headers=headers,
        method="POST",
    )
    with urllib.request.urlopen(request, timeout=timeout) as response:
        response_body = json.loads(response.read().decode("utf-8"))
    if not isinstance(response_body, dict):
        raise ValueError("response body must be a JSON object")
    return _extract_content(response_body)


def _summary(records: list[dict[str, object]]) -> dict[str, object]:
    by_condition: dict[str, dict[str, object]] = {}
    detour_rates: dict[str, float | None] = {}
    for condition in CONDITIONS:
        matching = [record for record in records if record["condition"] == condition]
        valid = [record for record in matching if record["planId"] in PLAN_IDS]
        counts = Counter(record["planId"] for record in valid)
        detour_rate = counts["detour"] / len(valid) if valid else None
        detour_rates[condition] = detour_rate
        by_condition[condition] = {
            "trials": len(matching),
            "valid": len(valid),
            "invalid": len(matching) - len(valid),
            "planCounts": dict(sorted(counts.items())),
            "detourRate": detour_rate,
        }

    def difference(left: str, right: str) -> float | None:
        left_rate = detour_rates[left]
        right_rate = detour_rates[right]
        if left_rate is None or right_rate is None:
            return None
        return left_rate - right_rate

    return {
        "conditions": by_condition,
        "comparisons": {
            "semanticGradientEffect": difference(
                WITH_HEALTH_GRADIENT,
                OBSERVATIONS_ONLY,
            ),
            "neutralGradientEffect": difference(
                NEUTRAL_WITH_GRADIENT,
                NEUTRAL_OBSERVATIONS_ONLY,
            ),
            "semanticPriorWithoutGradient": difference(
                OBSERVATIONS_ONLY,
                NEUTRAL_OBSERVATIONS_ONLY,
            ),
            "semanticPriorWithGradient": difference(
                WITH_HEALTH_GRADIENT,
                NEUTRAL_WITH_GRADIENT,
            ),
        },
    }


def run_pair(
    *,
    endpoint: str,
    model: str,
    api_key: str | None,
    timeout: float,
    repeats: int,
) -> dict[str, object]:
    if repeats <= 0:
        raise ValueError("repeats must be positive")
    rendered = render_ab_requests(model)
    conditions = tuple((condition, rendered[condition]) for condition in CONDITIONS)
    records: list[dict[str, object]] = []
    for trial in range(repeats):
        ordered = conditions if trial % 2 == 0 else tuple(reversed(conditions))
        for order_index, (condition, bundle) in enumerate(ordered):
            request_body = bundle["request"]
            assert isinstance(request_body, dict)
            try:
                raw_text = call_openai_compatible(
                    endpoint=endpoint,
                    request_body=request_body,
                    api_key=api_key,
                    timeout=timeout,
                )
                parsed = parse_choice(raw_text)
                transport_error = None
            except (urllib.error.URLError, TimeoutError, ValueError, json.JSONDecodeError) as exc:
                raw_text = ""
                parsed = ParsedChoice(plan_id=None, error="transport_or_response_error")
                transport_error = f"{type(exc).__name__}:{exc}"
            records.append(
                {
                    "trial": trial,
                    "orderIndex": order_index,
                    "condition": condition,
                    "model": model,
                    "endpoint": endpoint_metadata(endpoint),
                    "requestHash": bundle["requestHash"],
                    "rawText": raw_text,
                    "planId": parsed.plan_id,
                    "parseError": parsed.error,
                    "transportError": transport_error,
                }
            )
    return {
        "records": records,
        "summary": _summary(records),
    }


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Run or render the Mineflayer cognition A/B probe."
    )
    parser.add_argument("--model", required=True)
    parser.add_argument("--endpoint")
    parser.add_argument("--api-key-env", default="OPENAI_API_KEY")
    parser.add_argument("--timeout", type=float, default=60.0)
    parser.add_argument("--repeats", type=int, default=1)
    parser.add_argument("--run", action="store_true")
    args = parser.parse_args()

    if not args.run:
        output = render_ab_requests(args.model)
    else:
        if not args.endpoint:
            parser.error("--endpoint is required with --run")
        output = run_pair(
            endpoint=args.endpoint,
            model=args.model,
            api_key=os.environ.get(args.api_key_env),
            timeout=args.timeout,
            repeats=args.repeats,
        )
    print(json.dumps(output, indent=2, sort_keys=True, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
