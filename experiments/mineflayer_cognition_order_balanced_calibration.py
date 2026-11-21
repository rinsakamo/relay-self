from __future__ import annotations

import argparse
import copy
import hashlib
import json
import os
import urllib.error
from collections import Counter, defaultdict
from typing import Any

import experiments.mineflayer_cognition_ab as cognition
import experiments.mineflayer_cognition_opaque_id_calibration as opaque

G0_CANONICAL = "G0Canonical"
G1_SWAP_FIRST_TWO = "G1SwapFirstTwo"
G2_CYCLIC_GEOMETRY = "G2CyclicGeometry"
GEOMETRY_MAPPINGS = (
    G0_CANONICAL,
    G1_SWAP_FIRST_TWO,
    G2_CYCLIC_GEOMETRY,
)

A = opaque.OPAQUE_DIRECT_SLOT
B = opaque.OPAQUE_DETOUR_SLOT
C = opaque.OPAQUE_OBSERVE_SLOT

PERMUTATIONS = (
    ("ABC", (A, B, C)),
    ("ACB", (A, C, B)),
    ("BAC", (B, A, C)),
    ("BCA", (B, C, A)),
    ("CAB", (C, A, B)),
    ("CBA", (C, B, A)),
)

_GEOMETRY_BINDINGS = {
    G0_CANONICAL: {
        A: "direct",
        B: "detour",
        C: "observe",
    },
    G1_SWAP_FIRST_TWO: {
        A: "detour",
        B: "direct",
        C: "observe",
    },
    G2_CYCLIC_GEOMETRY: {
        A: "observe",
        B: "direct",
        C: "detour",
    },
}

_DIRECT_GEOMETRY_ID = {
    mapping: next(
        plan_id
        for plan_id, geometry_name in binding.items()
        if geometry_name == "direct"
    )
    for mapping, binding in _GEOMETRY_BINDINGS.items()
}

EXPECTED_REPEATS = 2
EXPECTED_CELLS_PER_REPEAT = len(GEOMETRY_MAPPINGS) * len(PERMUTATIONS)
EXPECTED_MODEL_CALLS = EXPECTED_REPEATS * EXPECTED_CELLS_PER_REPEAT


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


def candidate_plans_for(
    geometry_mapping: str,
    permutation: tuple[str, str, str],
) -> tuple[dict[str, object], ...]:
    if geometry_mapping not in GEOMETRY_MAPPINGS:
        raise ValueError(f"unknown geometry mapping: {geometry_mapping}")
    if tuple(sorted(permutation)) != tuple(sorted(opaque.OPAQUE_PLAN_IDS)):
        raise ValueError("permutation must contain each opaque id exactly once")
    geometries = _canonical_geometry_by_name()
    binding = _GEOMETRY_BINDINGS[geometry_mapping]
    return tuple(
        {
            "plan_id": plan_id,
            "waypoints": copy.deepcopy(geometries[binding[plan_id]]),
        }
        for plan_id in permutation
    )


def build_order_balanced_request(
    *,
    model: str,
    geometry_mapping: str,
    permutation: tuple[str, str, str],
) -> dict[str, object]:
    base_condition = {
        G0_CANONICAL: opaque.N0_CANONICAL,
        G1_SWAP_FIRST_TWO: opaque.N1_SWAP_FIRST_TWO,
        G2_CYCLIC_GEOMETRY: opaque.N2_CYCLIC_GEOMETRY,
    }[geometry_mapping]
    request = copy.deepcopy(
        opaque.build_opaque_request(
            model=model,
            condition=base_condition,
        )
    )
    messages = request.get("messages")
    if not isinstance(messages, list) or len(messages) != 2:
        raise AssertionError("opaque request must have two messages")
    user_message = messages[1]
    if not isinstance(user_message, dict):
        raise AssertionError("user message must be an object")
    content = user_message.get("content")
    if not isinstance(content, str):
        raise AssertionError("user message content must be a string")
    payload = json.loads(content)
    if not isinstance(payload, dict):
        raise AssertionError("user payload must be an object")
    payload["candidate_plans"] = candidate_plans_for(
        geometry_mapping,
        permutation,
    )
    user_message["content"] = _canonical_json(payload)
    return request


def render_cell(
    *,
    model: str,
    geometry_mapping: str,
    permutation_name: str,
    permutation: tuple[str, str, str],
) -> dict[str, object]:
    request = build_order_balanced_request(
        model=model,
        geometry_mapping=geometry_mapping,
        permutation=permutation,
    )
    return {
        "request": request,
        "requestHash": _request_hash(request),
        "geometryMapping": geometry_mapping,
        "geometryBinding": dict(_GEOMETRY_BINDINGS[geometry_mapping]),
        "permutation": permutation_name,
        "planOrder": list(permutation),
        "directGeometryPlanId": _DIRECT_GEOMETRY_ID[geometry_mapping],
        "candidatePositions": {
            plan_id: position
            for position, plan_id in enumerate(permutation)
        },
    }


def planned_cells() -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []
    forward_permutations = PERMUTATIONS
    reverse_permutations = tuple(reversed(PERMUTATIONS))

    for geometry_mapping in GEOMETRY_MAPPINGS:
        for permutation_name, permutation in forward_permutations:
            rows.append(
                {
                    "repeat": 0,
                    "geometryMapping": geometry_mapping,
                    "permutation": permutation_name,
                    "planOrder": list(permutation),
                }
            )

    for geometry_mapping in reversed(GEOMETRY_MAPPINGS):
        for permutation_name, permutation in reverse_permutations:
            rows.append(
                {
                    "repeat": 1,
                    "geometryMapping": geometry_mapping,
                    "permutation": permutation_name,
                    "planOrder": list(permutation),
                }
            )

    if len(rows) != EXPECTED_MODEL_CALLS:
        raise AssertionError("order-balanced cell count drift")
    return rows


def render_planned_requests(model: str) -> list[dict[str, object]]:
    permutation_lookup = dict(PERMUTATIONS)
    output: list[dict[str, object]] = []
    for row in planned_cells():
        geometry_mapping = str(row["geometryMapping"])
        permutation_name = str(row["permutation"])
        bundle = render_cell(
            model=model,
            geometry_mapping=geometry_mapping,
            permutation_name=permutation_name,
            permutation=permutation_lookup[permutation_name],
        )
        output.append({**row, **bundle})
    return output


def _classification(
    records: list[dict[str, object]],
    *,
    invalid_count: int,
    transport_failure_count: int,
) -> str:
    if (
        invalid_count
        or transport_failure_count
        or len(records) != EXPECTED_MODEL_CALLS
    ):
        return "X"

    if all(record.get("tracksDirectGeometry") is True for record in records):
        return "G"

    selected_positions = {
        record.get("selectedPosition")
        for record in records
    }
    if len(selected_positions) == 1 and None not in selected_positions:
        return "P"

    selected_ids = {
        record.get("planId")
        for record in records
    }
    if len(selected_ids) == 1 and None not in selected_ids:
        return "I"

    return "M"


def summarize(records: list[dict[str, object]]) -> dict[str, object]:
    valid = [
        record
        for record in records
        if record.get("planId") in opaque.OPAQUE_PLAN_IDS
        and record.get("transportError") is None
    ]
    invalid_count = len(records) - len(valid)
    transport_failure_count = sum(
        1
        for record in records
        if record.get("transportError") is not None
    )

    by_geometry: dict[str, dict[str, object]] = {}
    for geometry_mapping in GEOMETRY_MAPPINGS:
        matching = [
            record
            for record in valid
            if record["geometryMapping"] == geometry_mapping
        ]
        plan_counts = Counter(str(record["planId"]) for record in matching)
        direct_count = sum(
            1
            for record in matching
            if record.get("tracksDirectGeometry") is True
        )
        by_geometry[geometry_mapping] = {
            "valid": len(matching),
            "planCounts": dict(sorted(plan_counts.items())),
            "directGeometryPlanId": _DIRECT_GEOMETRY_ID[geometry_mapping],
            "tracksDirectGeometryCount": direct_count,
            "tracksDirectGeometryRate": (
                direct_count / len(matching)
                if matching
                else None
            ),
        }

    by_permutation: dict[str, dict[str, object]] = {}
    for permutation_name, _ in PERMUTATIONS:
        matching = [
            record
            for record in valid
            if record["permutation"] == permutation_name
        ]
        direct_count = sum(
            1
            for record in matching
            if record.get("tracksDirectGeometry") is True
        )
        by_permutation[permutation_name] = {
            "valid": len(matching),
            "planCounts": dict(
                sorted(
                    Counter(
                        str(record["planId"])
                        for record in matching
                    ).items()
                )
            ),
            "tracksDirectGeometryCount": direct_count,
            "tracksDirectGeometryRate": (
                direct_count / len(matching)
                if matching
                else None
            ),
        }

    position_counts = Counter(
        int(record["selectedPosition"])
        for record in valid
        if isinstance(record.get("selectedPosition"), int)
    )

    cell_groups: dict[tuple[str, str], list[dict[str, object]]] = defaultdict(list)
    for record in valid:
        cell_groups[
            (
                str(record["geometryMapping"]),
                str(record["permutation"]),
            )
        ].append(record)

    agreeing_cells = 0
    complete_cells = 0
    for cell_records in cell_groups.values():
        if len(cell_records) != EXPECTED_REPEATS:
            continue
        complete_cells += 1
        if len({record["planId"] for record in cell_records}) == 1:
            agreeing_cells += 1

    raw_pattern_counts = Counter(
        str(record.get("rawText", ""))
        for record in records
    )

    return {
        "expectedModelCalls": EXPECTED_MODEL_CALLS,
        "records": len(records),
        "valid": len(valid),
        "invalid": invalid_count,
        "transportFailureCount": transport_failure_count,
        "classification": _classification(
            records,
            invalid_count=invalid_count,
            transport_failure_count=transport_failure_count,
        ),
        "byGeometry": by_geometry,
        "byPermutation": by_permutation,
        "selectedPositionCounts": dict(sorted(position_counts.items())),
        "exactCellCompleteCount": complete_cells,
        "exactCellRepeatAgreementCount": agreeing_cells,
        "exactCellRepeatAgreementRate": (
            agreeing_cells / complete_cells
            if complete_cells
            else None
        ),
        "rawPatternCounts": dict(sorted(raw_pattern_counts.items())),
    }


def run_order_balanced_calibration(
    *,
    endpoint: str,
    model: str,
    api_key: str | None,
    timeout: float,
) -> dict[str, object]:
    planned = render_planned_requests(model)
    records: list[dict[str, object]] = []

    for execution_index, item in enumerate(planned):
        request_body = item["request"]
        assert isinstance(request_body, dict)
        try:
            raw_text = cognition.call_openai_compatible(
                endpoint=endpoint,
                request_body=request_body,
                api_key=api_key,
                timeout=timeout,
            )
            parsed = opaque.parse_opaque_choice(raw_text)
            transport_error = None
        except (
            urllib.error.URLError,
            TimeoutError,
            ValueError,
            json.JSONDecodeError,
        ) as exc:
            raw_text = ""
            parsed = opaque.ParsedOpaqueChoice(
                plan_id=None,
                error="transport_or_response_error",
            )
            transport_error = f"{type(exc).__name__}:{exc}"

        plan_id = parsed.plan_id
        geometry_mapping = str(item["geometryMapping"])
        binding = item["geometryBinding"]
        positions = item["candidatePositions"]
        assert isinstance(binding, dict)
        assert isinstance(positions, dict)

        selected_geometry = (
            binding[plan_id]
            if plan_id in opaque.OPAQUE_PLAN_IDS
            else None
        )
        selected_position = (
            positions[plan_id]
            if plan_id in opaque.OPAQUE_PLAN_IDS
            else None
        )

        records.append(
            {
                "executionIndex": execution_index,
                "repeat": item["repeat"],
                "geometryMapping": geometry_mapping,
                "permutation": item["permutation"],
                "planOrder": item["planOrder"],
                "candidatePositions": positions,
                "model": model,
                "endpoint": cognition.endpoint_metadata(endpoint),
                "requestHash": item["requestHash"],
                "rawText": raw_text,
                "planId": plan_id,
                "selectedPosition": selected_position,
                "selectedGeometry": selected_geometry,
                "directGeometryPlanId": item["directGeometryPlanId"],
                "tracksDirectGeometry": (
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
        description="Render or run the #326 exhaustive-order calibration."
    )
    parser.add_argument("--model", required=True)
    parser.add_argument("--endpoint")
    parser.add_argument("--api-key-env", default="OPENAI_API_KEY")
    parser.add_argument("--timeout", type=float, default=60.0)
    parser.add_argument("--run", action="store_true")
    args = parser.parse_args()

    if args.run:
        if not args.endpoint:
            parser.error("--endpoint is required with --run")
        output: Any = run_order_balanced_calibration(
            endpoint=args.endpoint,
            model=args.model,
            api_key=os.environ.get(args.api_key_env),
            timeout=args.timeout,
        )
    else:
        output = render_planned_requests(args.model)

    print(json.dumps(output, indent=2, sort_keys=True, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
