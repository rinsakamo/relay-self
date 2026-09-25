from __future__ import annotations

import argparse
import hashlib
import json
from collections import Counter
from dataclasses import dataclass
from typing import Any

from experiments.mineflayer_viability_relay import (
    compile_cognition_payload,
    respawn_trace,
)

SYSTEM_INSTRUCTION = (
    "Choose exactly one candidate plan for the stated task using only the "
    "supplied data. Return one JSON object with exactly one key, plan_id. "
    "Do not add prose."
)

TASK = {"instruction": "Reach the target location efficiently."}
TARGET = {"x": -8.0, "y": 64.0, "z": 0.0}
SIGNAL_SEMANTICS = {
    "negative": "adverse_direction",
    "zero": "neutral_direction",
    "positive": "favorable_direction",
}

C0_OBSERVATIONS_ONLY = "C0_OBSERVATIONS_ONLY"
C1_EXPLICIT_DERIVED_GRADIENT = "C1_EXPLICIT_DERIVED_GRADIENT"
ARMS = (
    C0_OBSERVATIONS_ONLY,
    C1_EXPLICIT_DERIVED_GRADIENT,
)

A = "q_4n7x"
B = "q_8p2m"
C = "q_6r9k"
OPAQUE_PLAN_IDS = frozenset({A, B, C})

GEOMETRIES = {
    "direct": (
        {"x": 2.0, "y": 64.0, "z": 0.0},
        {"x": -8.0, "y": 64.0, "z": 0.0},
    ),
    "detour": (
        {"x": 10.0, "y": 64.0, "z": -10.0},
        {"x": -8.0, "y": 64.0, "z": -10.0},
        {"x": -8.0, "y": 64.0, "z": 0.0},
    ),
    "observe": (
        {"x": 10.0, "y": 64.0, "z": 10.0},
    ),
}

M0 = "M0"
M1 = "M1"
M2 = "M2"
MAPPINGS = (M0, M1, M2)

GEOMETRY_BINDINGS = {
    M0: {
        A: "direct",
        B: "detour",
        C: "observe",
    },
    M1: {
        A: "detour",
        B: "observe",
        C: "direct",
    },
    M2: {
        A: "observe",
        B: "direct",
        C: "detour",
    },
}

PERMUTATIONS = (
    ("ABC", (A, B, C)),
    ("ACB", (A, C, B)),
    ("BAC", (B, A, C)),
    ("BCA", (B, C, A)),
    ("CAB", (C, A, B)),
    ("CBA", (C, B, A)),
)
PERMUTATION_NAMES = tuple(name for name, _ in PERMUTATIONS)
PERMUTATION_ORDERS = dict(PERMUTATIONS)

BLOCK_SCHEDULE = (
    ("B0", M0, C0_OBSERVATIONS_ONLY, 0),
    ("B1", M1, C1_EXPLICIT_DERIVED_GRADIENT, 1),
    ("B2", M2, C0_OBSERVATIONS_ONLY, 2),
    ("B3", M2, C1_EXPLICIT_DERIVED_GRADIENT, 3),
    ("B4", M1, C0_OBSERVATIONS_ONLY, 4),
    ("B5", M0, C1_EXPLICIT_DERIVED_GRADIENT, 5),
)

STRICT_MAJORITY = 4
EXPECTED_BLOCKS = 6
EXPECTED_CALLS_PER_BLOCK = 6
EXPECTED_MODEL_CALLS = EXPECTED_BLOCKS * EXPECTED_CALLS_PER_BLOCK

EFFECT = "F46_SUCCESSOR_EFFECT"
NO_EFFECT = "F46_SUCCESSOR_NO_EFFECT"
NON_DISCRIMINATING = "F46_SUCCESSOR_NON_DISCRIMINATING"
MIXED = "F46_SUCCESSOR_MIXED"
INVALID = "F46_SUCCESSOR_INVALID"


@dataclass(frozen=True)
class ParsedChoice:
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


def _normalize_choice_text(raw_text: str) -> str:
    stripped = raw_text.strip()
    lines = stripped.splitlines()
    fence = "```"
    if (
        len(lines) >= 3
        and lines[0] == fence + "json"
        and lines[-1] == fence
        and all(fence not in line for line in lines[1:-1])
    ):
        return "\n".join(lines[1:-1]).strip()
    return stripped


def parse_choice(raw_text: str) -> ParsedChoice:
    try:
        value = json.loads(_normalize_choice_text(raw_text))
    except json.JSONDecodeError as exc:
        return ParsedChoice(
            plan_id=None,
            error=f"invalid_json:{exc.msg}",
        )
    if not isinstance(value, dict):
        return ParsedChoice(None, "response_not_object")
    if set(value) != {"plan_id"}:
        return ParsedChoice(None, "response_schema_mismatch")
    plan_id = value.get("plan_id")
    if not isinstance(plan_id, str):
        return ParsedChoice(None, "missing_plan_id")
    if plan_id not in OPAQUE_PLAN_IDS:
        return ParsedChoice(None, "unknown_plan_id")
    return ParsedChoice(plan_id, None)


def gradient_sequence() -> list[dict[str, object]]:
    payload = compile_cognition_payload(
        respawn_trace(),
        include_gradient=True,
    )
    frames = payload["frames"]
    if not isinstance(frames, list):
        raise AssertionError("compiled frames must be a list")
    return [
        dict(row["valueGradient"])
        for row in frames
        if isinstance(row, dict) and "valueGradient" in row
    ]


def _history_for_arm(arm: str) -> dict[str, object]:
    if arm not in ARMS:
        raise ValueError(f"unknown arm: {arm}")
    return compile_cognition_payload(
        respawn_trace(),
        include_gradient=arm == C1_EXPLICIT_DERIVED_GRADIENT,
    )


def candidate_plans(
    mapping: str,
    permutation: str,
) -> list[dict[str, object]]:
    if mapping not in MAPPINGS:
        raise ValueError(f"unknown mapping: {mapping}")
    if permutation not in PERMUTATION_ORDERS:
        raise ValueError(f"unknown permutation: {permutation}")

    binding = GEOMETRY_BINDINGS[mapping]
    return [
        {
            "plan_id": plan_id,
            "waypoints": [
                dict(waypoint)
                for waypoint in GEOMETRIES[binding[plan_id]]
            ],
        }
        for plan_id in PERMUTATION_ORDERS[permutation]
    ]


def build_request(
    *,
    model: str,
    arm: str,
    mapping: str,
    permutation: str,
) -> dict[str, object]:
    payload = {
        "task": TASK,
        "target": TARGET,
        "candidate_plans": candidate_plans(mapping, permutation),
        "signal_semantics": SIGNAL_SEMANTICS,
        "history": _history_for_arm(arm),
    }
    return {
        "model": model,
        "temperature": 0,
        "max_tokens": 32,
        "reasoning_effort": "none",
        "cache_prompt": False,
        "messages": [
            {
                "role": "system",
                "content": SYSTEM_INSTRUCTION,
            },
            {
                "role": "user",
                "content": _canonical_json(payload),
            },
        ],
    }


def planned_ledger(model: str) -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []
    execution_index = 0

    for block_id, mapping, arm, rotation in BLOCK_SCHEDULE:
        rotated = (
            PERMUTATION_NAMES[rotation:]
            + PERMUTATION_NAMES[:rotation]
        )
        for block_call_index, permutation in enumerate(rotated):
            request = build_request(
                model=model,
                arm=arm,
                mapping=mapping,
                permutation=permutation,
            )
            rows.append(
                {
                    "blockId": block_id,
                    "mapping": mapping,
                    "arm": arm,
                    "permutation": permutation,
                    "planOrder": list(
                        PERMUTATION_ORDERS[permutation]
                    ),
                    "requestHash": _request_hash(request),
                    "gradientPresent": (
                        arm == C1_EXPLICIT_DERIVED_GRADIENT
                    ),
                    "executionIndex": execution_index,
                    "blockCallIndex": block_call_index,
                    "request": request,
                }
            )
            execution_index += 1

    if len(rows) != EXPECTED_MODEL_CALLS:
        raise AssertionError("successor ledger size drift")
    return rows


def selected_geometry(
    mapping: str,
    plan_id: str | None,
) -> str | None:
    if mapping not in MAPPINGS:
        raise ValueError(f"unknown mapping: {mapping}")
    if plan_id not in OPAQUE_PLAN_IDS:
        return None
    return GEOMETRY_BINDINGS[mapping][plan_id]


def selected_position(
    plan_order: list[str],
    plan_id: str | None,
) -> int | None:
    if plan_id not in OPAQUE_PLAN_IDS:
        return None
    try:
        return plan_order.index(plan_id)
    except ValueError:
        return None


def aggregate_block(
    block_rows: list[dict[str, object]],
) -> dict[str, object]:
    if len(block_rows) != EXPECTED_CALLS_PER_BLOCK:
        return {
            "outcome": "BLOCK_INVALID",
            "reason": "incomplete_block",
        }

    block_ids = {row.get("blockId") for row in block_rows}
    mappings = {row.get("mapping") for row in block_rows}
    arms = {row.get("arm") for row in block_rows}
    permutations = {row.get("permutation") for row in block_rows}

    if len(block_ids) != 1 or len(mappings) != 1 or len(arms) != 1:
        return {
            "outcome": "BLOCK_INVALID",
            "reason": "block_metadata_mismatch",
        }
    if permutations != set(PERMUTATION_NAMES):
        return {
            "outcome": "BLOCK_INVALID",
            "reason": "permutation_set_mismatch",
        }

    for row in block_rows:
        if row.get("parseError") is not None:
            return {
                "outcome": "BLOCK_INVALID",
                "reason": "parse_error",
            }
        if row.get("transportError") is not None:
            return {
                "outcome": "BLOCK_INVALID",
                "reason": "transport_error",
            }
        if row.get("planId") not in OPAQUE_PLAN_IDS:
            return {
                "outcome": "BLOCK_INVALID",
                "reason": "invalid_plan_id",
            }
        if row.get("selectedGeometry") not in GEOMETRIES:
            return {
                "outcome": "BLOCK_INVALID",
                "reason": "invalid_selected_geometry",
            }

    plan_counts = Counter(
        str(row["planId"])
        for row in block_rows
    )
    geometry_counts = Counter(
        str(row["selectedGeometry"])
        for row in block_rows
    )

    winners = [
        geometry
        for geometry, count in geometry_counts.items()
        if count >= STRICT_MAJORITY
    ]
    if len(winners) > 1:
        return {
            "outcome": "BLOCK_INVALID",
            "reason": "multiple_strict_majorities",
        }

    block_id = str(next(iter(block_ids)))
    mapping = str(next(iter(mappings)))
    arm = str(next(iter(arms)))

    if not winners:
        return {
            "blockId": block_id,
            "mapping": mapping,
            "arm": arm,
            "outcome": "NO_MAJORITY",
            "winnerGeometry": None,
            "planVoteCounts": dict(sorted(plan_counts.items())),
            "geometryVoteCounts": dict(
                sorted(geometry_counts.items())
            ),
            "strictMajorityThreshold": STRICT_MAJORITY,
            "voteCount": EXPECTED_CALLS_PER_BLOCK,
        }

    return {
        "blockId": block_id,
        "mapping": mapping,
        "arm": arm,
        "outcome": "WIN",
        "winnerGeometry": winners[0],
        "planVoteCounts": dict(sorted(plan_counts.items())),
        "geometryVoteCounts": dict(sorted(geometry_counts.items())),
        "strictMajorityThreshold": STRICT_MAJORITY,
        "voteCount": EXPECTED_CALLS_PER_BLOCK,
    }


def aggregate_blocks(
    records: list[dict[str, object]],
) -> list[dict[str, object]]:
    grouped: dict[str, list[dict[str, object]]] = {
        block_id: []
        for block_id, _, _, _ in BLOCK_SCHEDULE
    }
    for row in records:
        block_id = row.get("blockId")
        if block_id not in grouped:
            return [
                {
                    "outcome": "BLOCK_INVALID",
                    "reason": "unknown_block_id",
                }
            ]
        grouped[str(block_id)].append(row)

    return [
        aggregate_block(grouped[block_id])
        for block_id, _, _, _ in BLOCK_SCHEDULE
    ]


def _outcome_key(block: dict[str, object]) -> str:
    outcome = block.get("outcome")
    if outcome == "WIN":
        return f"WIN({block.get('winnerGeometry')})"
    if outcome == "NO_MAJORITY":
        return "NO_MAJORITY"
    return "BLOCK_INVALID"


def classify_blocks(
    blocks: list[dict[str, object]],
) -> str:
    if len(blocks) != EXPECTED_BLOCKS:
        return INVALID
    if any(block.get("outcome") == "BLOCK_INVALID" for block in blocks):
        return INVALID

    by_pair: dict[str, dict[str, str]] = {
        mapping: {}
        for mapping in MAPPINGS
    }
    for block in blocks:
        mapping = block.get("mapping")
        arm = block.get("arm")
        if mapping not in MAPPINGS or arm not in ARMS:
            return INVALID
        if str(arm) in by_pair[str(mapping)]:
            return INVALID
        by_pair[str(mapping)][str(arm)] = _outcome_key(block)

    if any(len(pair) != 2 for pair in by_pair.values()):
        return INVALID

    outcome_keys = [_outcome_key(block) for block in blocks]
    if all(key == "NO_MAJORITY" for key in outcome_keys):
        return NON_DISCRIMINATING

    if all(block.get("outcome") == "WIN" for block in blocks):
        if all(
            pair[C0_OBSERVATIONS_ONLY]
            == pair[C1_EXPLICIT_DERIVED_GRADIENT]
            for pair in by_pair.values()
        ):
            return NO_EFFECT

    transitions = [
        (
            pair[C0_OBSERVATIONS_ONLY],
            pair[C1_EXPLICIT_DERIVED_GRADIENT],
        )
        for pair in by_pair.values()
    ]
    if (
        len(set(transitions)) == 1
        and transitions[0][0] != transitions[0][1]
    ):
        return EFFECT

    return MIXED


def summarize_records(
    records: list[dict[str, object]],
) -> dict[str, object]:
    blocks = aggregate_blocks(records)
    return {
        "plannedModelCallCount": EXPECTED_MODEL_CALLS,
        "recordCount": len(records),
        "blocks": blocks,
        "classification": classify_blocks(blocks),
    }


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Render the frozen #331 viability-gradient successor ledger "
            "without executing model calls."
        )
    )
    parser.add_argument("--model", required=True)
    args = parser.parse_args()

    output: Any = planned_ledger(args.model)
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
