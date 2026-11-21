from __future__ import annotations

import argparse
import json
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

import experiments.mineflayer_cognition_opaque_id_calibration as opaque
import experiments.mineflayer_cognition_order_balanced_calibration as balanced

STRICT_MAJORITY = 4
EXPECTED_UNIQUE_CELLS = (
    len(balanced.GEOMETRY_MAPPINGS) * len(balanced.PERMUTATIONS)
)
EXPECTED_HISTORICAL_REPEATS = balanced.EXPECTED_REPEATS
QUALIFIED = "ORDER_MARGINALIZED_OPAQUE_CHOICE_INSTRUMENT_QUALIFIED"
NOT_QUALIFIED = "ORDER_MARGINALIZED_INSTRUMENT_NOT_QUALIFIED"

_VALID_GEOMETRIES = frozenset({"direct", "detour", "observe"})
_PERMUTATION_ORDERS = dict(balanced.PERMUTATIONS)


class InstrumentEvidenceError(ValueError):
    pass


def _validate_record(record: dict[str, object]) -> None:
    geometry_mapping = record.get("geometryMapping")
    permutation = record.get("permutation")
    plan_id = record.get("planId")
    selected_geometry = record.get("selectedGeometry")
    parse_error = record.get("parseError")
    transport_error = record.get("transportError")

    if geometry_mapping not in balanced.GEOMETRY_MAPPINGS:
        raise InstrumentEvidenceError("unknown geometry mapping")
    if permutation not in _PERMUTATION_ORDERS:
        raise InstrumentEvidenceError("unknown permutation")
    if plan_id not in opaque.OPAQUE_PLAN_IDS:
        raise InstrumentEvidenceError("invalid selected opaque id")
    if selected_geometry not in _VALID_GEOMETRIES:
        raise InstrumentEvidenceError("invalid selected geometry")
    if parse_error is not None:
        raise InstrumentEvidenceError("parse error present")
    if transport_error is not None:
        raise InstrumentEvidenceError("transport error present")

    expected_order = list(_PERMUTATION_ORDERS[str(permutation)])
    if record.get("planOrder") != expected_order:
        raise InstrumentEvidenceError("plan order does not match permutation")

    binding = balanced._GEOMETRY_BINDINGS[str(geometry_mapping)]
    if binding[str(plan_id)] != selected_geometry:
        raise InstrumentEvidenceError("selected geometry disagrees with binding")

    direct_plan_id = balanced._DIRECT_GEOMETRY_ID[str(geometry_mapping)]
    if record.get("directGeometryPlanId") != direct_plan_id:
        raise InstrumentEvidenceError("direct geometry id mismatch")

    expected_tracks = selected_geometry == "direct"
    if record.get("tracksDirectGeometry") is not expected_tracks:
        raise InstrumentEvidenceError("tracksDirectGeometry mismatch")


def collapse_repeat_cells(
    records: list[dict[str, object]],
) -> list[dict[str, object]]:
    if len(records) != balanced.EXPECTED_MODEL_CALLS:
        raise InstrumentEvidenceError(
            f"expected {balanced.EXPECTED_MODEL_CALLS} records"
        )

    cells: dict[tuple[str, str], list[dict[str, object]]] = defaultdict(list)
    for record in records:
        if not isinstance(record, dict):
            raise InstrumentEvidenceError("record must be an object")
        _validate_record(record)
        key = (
            str(record["geometryMapping"]),
            str(record["permutation"]),
        )
        cells[key].append(record)

    if len(cells) != EXPECTED_UNIQUE_CELLS:
        raise InstrumentEvidenceError(
            f"expected {EXPECTED_UNIQUE_CELLS} unique cells"
        )

    collapsed: list[dict[str, object]] = []
    for geometry_mapping in balanced.GEOMETRY_MAPPINGS:
        seen_permutations: set[str] = set()
        for permutation_name, _ in balanced.PERMUTATIONS:
            key = (geometry_mapping, permutation_name)
            cell_records = cells.get(key)
            if cell_records is None:
                raise InstrumentEvidenceError(
                    f"missing cell {geometry_mapping}/{permutation_name}"
                )
            if len(cell_records) != EXPECTED_HISTORICAL_REPEATS:
                raise InstrumentEvidenceError(
                    f"cell {geometry_mapping}/{permutation_name} "
                    f"must have {EXPECTED_HISTORICAL_REPEATS} repeats"
                )

            plan_ids = {str(record["planId"]) for record in cell_records}
            geometries = {
                str(record["selectedGeometry"])
                for record in cell_records
            }
            if len(plan_ids) != 1 or len(geometries) != 1:
                raise InstrumentEvidenceError(
                    f"repeat disagreement in "
                    f"{geometry_mapping}/{permutation_name}"
                )

            seen_permutations.add(permutation_name)
            first = cell_records[0]
            collapsed.append(
                {
                    "geometryMapping": geometry_mapping,
                    "permutation": permutation_name,
                    "planId": first["planId"],
                    "selectedGeometry": first["selectedGeometry"],
                    "directGeometryPlanId": first["directGeometryPlanId"],
                    "tracksDirectGeometry": first["tracksDirectGeometry"],
                    "historicalRepeatCount": len(cell_records),
                }
            )

        if seen_permutations != set(_PERMUTATION_ORDERS):
            raise InstrumentEvidenceError(
                f"incomplete permutation set for {geometry_mapping}"
            )

    return collapsed


def aggregate_mapping(
    collapsed_cells: list[dict[str, object]],
    geometry_mapping: str,
) -> dict[str, object]:
    cells = [
        cell
        for cell in collapsed_cells
        if cell["geometryMapping"] == geometry_mapping
    ]
    if len(cells) != len(balanced.PERMUTATIONS):
        raise InstrumentEvidenceError(
            f"expected six unique order votes for {geometry_mapping}"
        )

    vote_counts = Counter(str(cell["selectedGeometry"]) for cell in cells)
    plan_counts = Counter(str(cell["planId"]) for cell in cells)

    majority_geometry: str | None = None
    for geometry, count in vote_counts.items():
        if count >= STRICT_MAJORITY:
            if majority_geometry is not None:
                raise InstrumentEvidenceError("multiple strict majorities")
            majority_geometry = geometry

    return {
        "geometryMapping": geometry_mapping,
        "votes": len(cells),
        "geometryVoteCounts": dict(sorted(vote_counts.items())),
        "planVoteCounts": dict(sorted(plan_counts.items())),
        "strictMajorityThreshold": STRICT_MAJORITY,
        "aggregateWinnerGeometry": (
            majority_geometry
            if majority_geometry is not None
            else "NO_MAJORITY"
        ),
        "directGeometryVotes": vote_counts["direct"],
        "directGeometryStrictMajority": (
            vote_counts["direct"] >= STRICT_MAJORITY
        ),
    }


def qualify_result(result: dict[str, object]) -> dict[str, object]:
    records = result.get("records")
    if not isinstance(records, list):
        raise InstrumentEvidenceError("result.records must be a list")

    collapsed = collapse_repeat_cells(records)
    mappings = {
        geometry_mapping: aggregate_mapping(
            collapsed,
            geometry_mapping,
        )
        for geometry_mapping in balanced.GEOMETRY_MAPPINGS
    }

    qualified = all(
        row["aggregateWinnerGeometry"] == "direct"
        for row in mappings.values()
    )

    return {
        "classification": QUALIFIED if qualified else NOT_QUALIFIED,
        "sourceRecordCount": len(records),
        "uniqueCellCount": len(collapsed),
        "oneVotePerUniquePermutation": True,
        "strictMajorityThreshold": STRICT_MAJORITY,
        "mappingResults": mappings,
        "collapsedCells": collapsed,
    }


def qualify_file(path: Path) -> dict[str, object]:
    raw = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(raw, dict):
        raise InstrumentEvidenceError("result file must contain an object")
    return qualify_result(raw)


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Replay #326 evidence non-generatively and qualify the "
            "#329 order-marginalized opaque-choice instrument."
        )
    )
    parser.add_argument(
        "result_path",
        type=Path,
        help="Path to #326 order-balanced-calibration-result.json",
    )
    args = parser.parse_args()

    try:
        output: Any = qualify_file(args.result_path)
    except (
        OSError,
        json.JSONDecodeError,
        InstrumentEvidenceError,
    ) as exc:
        output = {
            "classification": NOT_QUALIFIED,
            "error": f"{type(exc).__name__}: {exc}",
        }
        print(
            json.dumps(
                output,
                indent=2,
                sort_keys=True,
                ensure_ascii=False,
            )
        )
        return 2

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
