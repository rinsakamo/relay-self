from __future__ import annotations

import argparse
import copy
import hashlib
import json
import os
import urllib.error
from collections import Counter
from typing import Any

import experiments.mineflayer_cognition_ab as cognition

K0_CANONICAL = "K0Canonical"
K1_SWAP_DIRECT_DETOUR = "K1SwapDirectDetour"
K2_CYCLIC_GEOMETRY = "K2CyclicGeometry"
K3_REVERSED_ORDER = "K3ReversedOrder"
CALIBRATION_CONDITIONS = (
    K0_CANONICAL,
    K1_SWAP_DIRECT_DETOUR,
    K2_CYCLIC_GEOMETRY,
    K3_REVERSED_ORDER,
)

_GEOMETRY_BINDINGS = {
    K0_CANONICAL: {
        "direct": "direct",
        "detour": "detour",
        "observe": "observe",
    },
    K1_SWAP_DIRECT_DETOUR: {
        "direct": "detour",
        "detour": "direct",
        "observe": "observe",
    },
    K2_CYCLIC_GEOMETRY: {
        "direct": "observe",
        "detour": "direct",
        "observe": "detour",
    },
    K3_REVERSED_ORDER: {
        "direct": "direct",
        "detour": "detour",
        "observe": "observe",
    },
}

_PLAN_ORDERS = {
    K0_CANONICAL: ("direct", "detour", "observe"),
    K1_SWAP_DIRECT_DETOUR: ("direct", "detour", "observe"),
    K2_CYCLIC_GEOMETRY: ("direct", "detour", "observe"),
    K3_REVERSED_ORDER: ("observe", "detour", "direct"),
}

_SHORTEST_GEOMETRY_PLAN = {
    condition: next(
        plan_id
        for plan_id, geometry_id in geometry_binding.items()
        if geometry_id == "direct"
    )
    for condition, geometry_binding in _GEOMETRY_BINDINGS.items()
}


def _canonical_json(value: object) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def _request_hash(request_body: dict[str, object]) -> str:
    return hashlib.sha256(_canonical_json(request_body).encode("utf-8")).hexdigest()


def _canonical_plan_by_id() -> dict[str, dict[str, object]]:
    return {
        str(plan["plan_id"]): copy.deepcopy(plan)
        for plan in cognition.CANDIDATE_PLANS
    }


def candidate_plans_for(condition: str) -> tuple[dict[str, object], ...]:
    if condition not in CALIBRATION_CONDITIONS:
        raise ValueError(f"unknown calibration condition: {condition}")
    canonical = _canonical_plan_by_id()
    binding = _GEOMETRY_BINDINGS[condition]
    plans: list[dict[str, object]] = []
    for plan_id in _PLAN_ORDERS[condition]:
        geometry_source = binding[plan_id]
        source = canonical[geometry_source]
        plans.append(
            {
                "plan_id": plan_id,
                "waypoints": copy.deepcopy(source["waypoints"]),
            }
        )
    return tuple(plans)


def build_calibration_request(*, model: str, condition: str) -> dict[str, object]:
    request = copy.deepcopy(
        cognition.build_request(
            model=model,
            include_gradient=False,
            neutral_labels=False,
        )
    )
    messages = request.get("messages")
    if not isinstance(messages, list) or len(messages) != 2:
        raise AssertionError("base cognition request must have exactly two messages")
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


def render_calibration_requests(model: str) -> dict[str, dict[str, object]]:
    output: dict[str, dict[str, object]] = {}
    for condition in CALIBRATION_CONDITIONS:
        request = build_calibration_request(model=model, condition=condition)
        output[condition] = {
            "request": request,
            "requestHash": _request_hash(request),
            "geometryBinding": dict(_GEOMETRY_BINDINGS[condition]),
            "planOrder": list(_PLAN_ORDERS[condition]),
            "shortestGeometryPlanId": _SHORTEST_GEOMETRY_PLAN[condition],
        }
    return output


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
        unanimous(K0_CANONICAL, "direct")
        and unanimous(K1_SWAP_DIRECT_DETOUR, "detour")
        and unanimous(K2_CYCLIC_GEOMETRY, "detour")
        and unanimous(K3_REVERSED_ORDER, "direct")
    ):
        return "P"

    if all(unanimous(condition, "direct") for condition in CALIBRATION_CONDITIONS):
        return "L"

    k0_counts = by_condition[K0_CANONICAL]["planCounts"]
    k3_counts = by_condition[K3_REVERSED_ORDER]["planCounts"]
    if isinstance(k0_counts, dict) and isinstance(k3_counts, dict):
        if len(k0_counts) == 1 and len(k3_counts) == 1 and k0_counts != k3_counts:
            return "O"

    return "M"


def summarize(records: list[dict[str, object]]) -> dict[str, object]:
    by_condition: dict[str, dict[str, object]] = {}
    invalid_count = 0
    transport_failure_count = 0

    for condition in CALIBRATION_CONDITIONS:
        matching = [record for record in records if record["condition"] == condition]
        valid = [
            record
            for record in matching
            if record.get("planId") in cognition.PLAN_IDS
            and record.get("transportError") is None
        ]
        invalid = len(matching) - len(valid)
        invalid_count += invalid
        transport_failure_count += sum(
            1 for record in matching if record.get("transportError") is not None
        )
        plan_counts = Counter(str(record["planId"]) for record in valid)
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
            "selectedGeometryCounts": dict(sorted(selected_geometry_counts.items())),
            "shortestGeometryPlanId": shortest_geometry_plan_id,
            "tracksShortestGeometryCount": shortest_geometry_count,
            "tracksShortestGeometryRate": (
                shortest_geometry_count / len(valid) if valid else None
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


def run_calibration(
    *,
    endpoint: str,
    model: str,
    api_key: str | None,
    timeout: float,
    repeats: int,
) -> dict[str, object]:
    if repeats <= 0:
        raise ValueError("repeats must be positive")
    rendered = render_calibration_requests(model)
    records: list[dict[str, object]] = []
    for trial in range(repeats):
        ordered = (
            CALIBRATION_CONDITIONS
            if trial % 2 == 0
            else tuple(reversed(CALIBRATION_CONDITIONS))
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
                parsed = cognition.parse_choice(raw_text)
                transport_error = None
            except (
                urllib.error.URLError,
                TimeoutError,
                ValueError,
                json.JSONDecodeError,
            ) as exc:
                raw_text = ""
                parsed = cognition.ParsedChoice(
                    plan_id=None,
                    error="transport_or_response_error",
                )
                transport_error = f"{type(exc).__name__}:{exc}"
            plan_id = parsed.plan_id
            selected_geometry = (
                _GEOMETRY_BINDINGS[condition][plan_id]
                if plan_id in cognition.PLAN_IDS
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
        description="Render or run the #320 candidate-choice calibration."
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
        output: Any = run_calibration(
            endpoint=args.endpoint,
            model=args.model,
            api_key=os.environ.get(args.api_key_env),
            timeout=args.timeout,
            repeats=args.repeats,
        )
    else:
        output = render_calibration_requests(args.model)

    print(json.dumps(output, indent=2, sort_keys=True, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
