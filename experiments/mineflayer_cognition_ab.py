from __future__ import annotations

import argparse
import hashlib
import json
import os
import urllib.error
import urllib.parse
import urllib.request
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


@dataclass(frozen=True)
class ParsedChoice:
    plan_id: str | None
    error: str | None


def _canonical_json(value: object) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def _request_hash(request_body: dict[str, object]) -> str:
    return hashlib.sha256(_canonical_json(request_body).encode("utf-8")).hexdigest()


def build_request(*, model: str, include_gradient: bool) -> dict[str, object]:
    payload = compile_cognition_payload(respawn_trace(), include_gradient=include_gradient)
    user_payload = {
        "task": TASK,
        "candidate_plans": CANDIDATE_PLANS,
        "history": payload,
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


def render_ab_requests(model: str) -> dict[str, object]:
    observations = build_request(model=model, include_gradient=False)
    gradient = build_request(model=model, include_gradient=True)
    return {
        "observationsOnly": {
            "request": observations,
            "requestHash": _request_hash(observations),
        },
        "withHealthGradient": {
            "request": gradient,
            "requestHash": _request_hash(gradient),
        },
    }


def parse_choice(raw_text: str) -> ParsedChoice:
    try:
        value = json.loads(raw_text)
    except json.JSONDecodeError as exc:
        return ParsedChoice(plan_id=None, error=f"invalid_json:{exc.msg}")
    if not isinstance(value, dict):
        return ParsedChoice(plan_id=None, error="response_not_object")
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
    conditions = (
        ("observationsOnly", rendered["observationsOnly"]),
        ("withHealthGradient", rendered["withHealthGradient"]),
    )
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
    return {"records": records}


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
