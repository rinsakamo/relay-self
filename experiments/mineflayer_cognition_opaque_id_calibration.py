from __future__ import annotations

import argparse
import copy
import hashlib
import json
import os
import urllib.error
from collections import Counter
from dataclasses import dataclass
from typing import Any

import experiments.mineflayer_cognition_ab as cognition

N0_CANONICAL = "N0Canonical"
N1_SWAP_FIRST_TWO = "N1SwapFirstTwo"
N2_CYCLIC_GEOMETRY = "N2CyclicGeometry"
N3_REVERSED_ORDER = "N3ReversedOrder"
OPAQUE_CONDITIONS = (
    N0_CANONICAL,
    N1_SWAP_FIRST_TWO,
    N2_CYCLIC_GEOMETRY,
    N3_REVERSED_ORDER,
)

OPAQUE_DIRECT_SLOT = "p_17c4"
OPAQUE_DETOUR_SLOT = "p_5a92"
OPAQUE_OBSERVE_SLOT = "p_c803"
OPAQUE_PLAN_IDS = frozenset(
    {
        OPAQUE_DIRECT_SLOT,
        OPAQUE_DETOUR_SLOT,
        OPAQUE_OBSERVE_SLOT,
    }
)

_GEOMETRY_BINDINGS = {
    N0_CANONICAL: {
        OPAQUE_DIRECT_SLOT: "direct",
        OPAQUE_DETOUR_SLOT: "detour",
        OPAQUE_OBSERVE_SLOT: "observe",
    },
    N1_SWAP_FIRST_TWO: {
        OPAQUE_DIRECT_SLOT: "detour",
        OPAQUE_DETOUR_SLOT: "direct",
        OPAQUE_OBSERVE_SLOT: "observe",
    },
    N2_CYCLIC_GEOMETRY: {
        OPAQUE_DIRECT_SLOT: "observe",
        OPAQUE_DETOUR_SLOT: "direct",
        OPAQUE_OBSERVE_SLOT: "detour",
    },
    N3_REVERSED_ORDER: {
        OPAQUE_DIRECT_SLOT: "direct",
        OPAQUE_DETOUR_SLOT: "detour",
        OPAQUE_OBSERVE_SLOT: "observe",
    },
}

_PLAN_ORDERS = {
    N0_CANONICAL: (
        OPAQUE_DIRECT_SLOT,
        OPAQUE_DETOUR_SLOT,
        OPAQUE_OBSERVE_SLOT,
    ),
    N1_SWAP_FIRST_TWO: (
        OPAQUE_DIRECT_SLOT,
        OPAQUE_DETOUR_SLOT,
        OPAQUE_OBSERVE_SLOT,
    ),
    N2_CYCLIC_GEOMETRY: (
        OPAQUE_DIRECT_SLOT,
        OPAQUE_DETOUR_SLOT,
        OPAQUE_OBSERVE_SLOT,
    ),
    N3_REVERSED_ORDER: (
        OPAQUE_OBSERVE_SLOT,
        OPAQUE_DETOUR_SLOT,
        OPAQUE_DIRECT_SLOT,
    ),
}

_SHORTEST_GEOMETRY_PLAN = {
    condition: next(
        plan_id
        for plan_id, geometry_id in geometry_binding.items()
        if geometry_id == "direct"
    )
    for condition, geometry_binding in _GEOMETRY_BINDINGS.items()
}


@dataclass(frozen=True)
class ParsedOpaqueChoice:
    plan_id: str | None
    error: str | None


def _canonical_json(value: object) -> str:
    return json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    )


def _request_hash(request_body: dict[str, object]) -> str:
    return hashlib.sha256(
        _canonical_json(request_body).encode("utf-8")
    ).hexdigest()


def _canonical_geometry_by_name() -> dict[str, list[dict[str, object]]]:
    return {
        str(plan["plan_id"]): copy.deepcopy(plan["waypoints"])
        for plan in cognition.CANDIDATE_PLANS
    }


def candidate_plans_for(condition: str) -> tuple[dict[str, object], ...]:
    if condition not in OPAQUE_CONDITIONS:
        raise ValueError(f"unknown opaque calibration condition: {condition}")
    geometries = _canonical_geometry_by_name()
    binding = _GEOMETRY_BINDINGS[condition]
    return tuple(
        {
            "plan_id": plan_id,
            "waypoints": copy.deepcopy(geometries[binding[plan_id]]),
        }
        for plan_id in _PLAN_ORDERS[condition]
    )


def build_opaque_request(*, model: str, condition: str) -> dict[str, object]:
    request = copy.deepcopy(
        cognition.build_request(
            model=model,
            include_gradient=False,
            neutral_labels=False,
        )
    )
    messages = request.get("messages")
    if not isinstance(messages, list) or len(messages) != 2:
        raise AssertionError("base cognition request must have two messages")
    user_message = messages[1]
    if not isinstance(user_message, dict):
        raise AssertionError("user message must be an object")
    content = user_message.get("content")
    if not isinstance(content, str):
        raise AssertionError("user message content must be a string")
    payload = json.loads(content)
    if not isinstance(payload, dict):
        raise AssertionError("user payload must be an object")
    payload["candidate_plans"] = candidate_plans_for(condition)
    user_message["content"] = _canonical_json(payload)
    return request


def render_opaque_requests(model: str) -> dict[str, dict[str, object]]:
    output: dict[str, dict[str, object]] = {}
    for condition in OPAQUE_CONDITIONS:
        request = build_opaque_request(model=model, condition=condition)
        output[condition] = {
            "request": request,
            "requestHash": _request_hash(request),
            "geometryBinding": dict(_GEOMETRY_BINDINGS[condition]),
            "planOrder": list(_PLAN_ORDERS[condition]),
            "shortestGeometryPlanId": _SHORTEST_GEOMETRY_PLAN[condition],
        }
    return output


def _normalize_choice_text(raw_text: str) -> str:
    stripped = raw_text.strip()
    lines = stripped.splitlines()
    fence = "`" * 3
    if (
        len(lines) >= 3
        and lines[0] == fence + "json"
        and lines[-1] == fence
        and all(fence not in line for line in lines[1:-1])
    ):
        return "\n".join(lines[1:-1]).strip()
    return stripped


def parse_opaque_choice(raw_text: str) -> ParsedOpaqueChoice:
    try:
        value = json.loads(_normalize_choice_text(raw_text))
    except json.JSONDecodeError as exc:
        return ParsedOpaqueChoice(
            plan_id=None,
            error=f"invalid_json:{exc.msg}",
        )
    if not isinstance(value, dict):
        return ParsedOpaqueChoice(
            plan_id=None,
            error="response_not_object",
        )
    if set(value) != {"plan_id"}:
        return ParsedOpaqueChoice(
            plan_id=None,
            error="response_schema_mismatch",
        )
    plan_id = value.get("plan_id")
    if not isinstance(plan_id, str):
        return ParsedOpaqueChoice(
            plan_id=None,
            error="missing_plan_id",
        )
    if plan_id not in OPAQUE_PLAN_IDS:
        return ParsedOpaqueChoice(
            plan_id=None,
            error="unknown_plan_id",
        )
    return ParsedOpaqueChoice(plan_id=plan_id, error=None)


def _classification(
    by_condition: dict[str, dict[str, object]],
    *,
    invalid_count: int,
    transport_failure_count: int,
) -> str:
    if invalid_count or transport_failure_count:
        return "X"

    def unanimous(condition: str, plan_id: str) -> bool:
        summary = by_condition[condition]
        trials = summary["trials"]
        counts = summary["planCounts"]
        return (
            isinstance(trials, int)
            and trials > 0
            and isinstance(counts, dict)
            and counts.get(plan_id) == trials
        )

    if (
        unanimous(N0_CANONICAL, OPAQUE_DIRECT_SLOT)
        and unanimous(N1_SWAP_FIRST_TWO, OPAQUE_DETOUR_SLOT)
        and unanimous(N2_CYCLIC_GEOMETRY, OPAQUE_DETOUR_SLOT)
        and unanimous(N3_REVERSED_ORDER, OPAQUE_DIRECT_SLOT)
    ):
        return "G"

    for plan_id in OPAQUE_PLAN_IDS:
        if all(
            unanimous(condition, plan_id)
            for condition in OPAQUE_CONDITIONS
        ):
            return "I"

    n0_counts = by_condition[N0_CANONICAL]["planCounts"]
    n3_counts = by_condition[N3_REVERSED_ORDER]["planCounts"]
    if isinstance(n0_counts, dict) and isinstance(n3_counts, dict):
        if (
            len(n0_counts) == 1
            and len(n3_counts) == 1
            and n0_counts != n3_counts
        ):
            return "O"

    return "M"


def summarize(records: list[dict[str, object]]) -> dict[str, object]:
    by_condition: dict[str, dict[str, object]] = {}
    invalid_count = 0
    transport_failure_count = 0

    for condition in OPAQUE_CONDITIONS:
        matching = [
            record
            for record in records
            if record["condition"] == condition
        ]
        valid = [
            record
            for record in matching
            if record.get("planId") in OPAQUE_PLAN_IDS
            and record.get("transportError") is None
        ]
        invalid = len(matching) - len(valid)
        invalid_count += invalid
        transport_failure_count += sum(
            1
            for record in matching
            if record.get("transportError") is not None
        )

        plan_counts = Counter(
            str(record["planId"])
            for record in valid
        )
        selected_geometry_counts = Counter(
            _GEOMETRY_BINDINGS[condition][str(record["planId"])]
            for record in valid
        )
        shortest_geometry_plan_id = _SHORTEST_GEOMETRY_PLAN[condition]
        shortest_geometry_count = plan_counts[shortest_geometry_plan_id]

        by_condition[condition] = {
            "trials": len(matching),
            "valid": len(valid),
            "invalid": invalid,
            "planCounts": dict(sorted(plan_counts.items())),
            "selectedGeometryCounts": dict(
                sorted(selected_geometry_counts.items())
            ),
            "shortestGeometryPlanId": shortest_geometry_plan_id,
            "tracksShortestGeometryCount": shortest_geometry_count,
            "tracksShortestGeometryRate": (
                shortest_geometry_count / len(valid)
                if valid
                else None
            ),
            "planOrder": list(_PLAN_ORDERS[condition]),
            "geometryBinding": dict(_GEOMETRY_BINDINGS[condition]),
        }

    return {
        "conditions": by_condition,
        "invalidCount": invalid_count,
        "transportFailureCount": transport_failure_count,
        "classification": _classification(
            by_condition,
            invalid_count=invalid_count,
            transport_failure_count=transport_failure_count,
        ),
    }


def run_opaque_calibration(
    *,
    endpoint: str,
    model: str,
    api_key: str | None,
    timeout: float,
    repeats: int,
) -> dict[str, object]:
    if repeats <= 0:
        raise ValueError("repeats must be positive")

    rendered = render_opaque_requests(model)
    records: list[dict[str, object]] = []

    for trial in range(repeats):
        ordered = (
            OPAQUE_CONDITIONS
            if trial % 2 == 0
            else tuple(reversed(OPAQUE_CONDITIONS))
        )
        for order_index, condition in enumerate(ordered):
            bundle = rendered[condition]
            request_body = bundle["request"]
            assert isinstance(request_body, dict)
            try:
                raw_text = cognition.call_openai_compatible(
                    endpoint=endpoint,
                    request_body=request_body,
                    api_key=api_key,
                    timeout=timeout,
                )
                parsed = parse_opaque_choice(raw_text)
                transport_error = None
            except (
                urllib.error.URLError,
                TimeoutError,
                ValueError,
                json.JSONDecodeError,
            ) as exc:
                raw_text = ""
                parsed = ParsedOpaqueChoice(
                    plan_id=None,
                    error="transport_or_response_error",
                )
                transport_error = f"{type(exc).__name__}:{exc}"

            plan_id = parsed.plan_id
            selected_geometry = (
                _GEOMETRY_BINDINGS[condition][plan_id]
                if plan_id in OPAQUE_PLAN_IDS
                else None
            )
            records.append(
                {
                    "trial": trial,
                    "orderIndex": order_index,
                    "condition": condition,
                    "model": model,
                    "endpoint": cognition.endpoint_metadata(endpoint),
                    "requestHash": bundle["requestHash"],
                    "rawText": raw_text,
                    "planId": plan_id,
                    "selectedGeometry": selected_geometry,
                    "tracksShortestGeometry": (
                        selected_geometry == "direct"
                        if selected_geometry is not None
                        else None
                    ),
                    "parseError": parsed.error,
                    "transportError": transport_error,
                }
            )

    return {
        "records": records,
        "summary": summarize(records),
    }


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Render or run the #323 opaque-plan-id calibration."
    )
    parser.add_argument("--model", required=True)
    parser.add_argument("--endpoint")
    parser.add_argument("--api-key-env", default="OPENAI_API_KEY")
    parser.add_argument("--timeout", type=float, default=60.0)
    parser.add_argument("--repeats", type=int, default=5)
    parser.add_argument("--run", action="store_true")
    args = parser.parse_args()

    if args.run:
        if not args.endpoint:
            parser.error("--endpoint is required with --run")
        output: Any = run_opaque_calibration(
            endpoint=args.endpoint,
            model=args.model,
            api_key=os.environ.get(args.api_key_env),
            timeout=args.timeout,
            repeats=args.repeats,
        )
    else:
        output = render_opaque_requests(args.model)

    print(
        json.dumps(
            output,
            indent=2,
            sort_keys=True,
            ensure_ascii=False,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
