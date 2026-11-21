import json

from adapters.llama_cpp.relay_engine import render_llama_cpp_request
from experiments.gemma_flee_artifact_reuse import (
    CHOICE_ORDERS,
    CONDITIONS,
    FROZEN_RETAINED_KEYS,
    MAPPINGS,
    STATES,
    build_full_request,
    build_schedule,
    classify_result,
    decode_destination,
    expected_choice_id,
)
from experiments.gemma_flee_crystallization import filter_request
from relay_self.relay_engine import CognitionMode


def test_state_surface_has_known_and_novel_expectations() -> None:
    states = {state.state_id: state for state in STATES}

    assert states["K1"].expected_destination == "cave"
    assert states["K2"].expected_destination == "ridge"
    assert states["K3"].expected_destination == "cave"
    assert states["K4"].expected_destination == "ridge"

    assert states["N1"].expected_destination is None
    assert states["N2"].expected_destination is None
    assert states["N3"].expected_destination is None
    assert states["N4"].expected_destination == "cave"
    assert states["N5"].expected_destination == "ridge"


def test_choice_mapping_round_trips_destination_semantics() -> None:
    state = STATES[0]
    for mapping_index in range(len(MAPPINGS)):
        choice_id = expected_choice_id(
            state,
            mapping_index=mapping_index,
        )
        assert choice_id is not None
        assert decode_destination(
            choice_id,
            mapping_index=mapping_index,
        ) == "cave"


def test_schedule_covers_all_cells_and_balances_condition_order() -> None:
    schedule = build_schedule()

    assert len(schedule) == (
        len(STATES)
        * len(MAPPINGS)
        * len(CHOICE_ORDERS)
        * len(CONDITIONS)
    )
    assert len(schedule) == 108

    cells: dict[int, list[dict[str, object]]] = {}
    for row in schedule:
        cells.setdefault(int(row["cell_index"]), []).append(row)

    assert len(cells) == 54
    assert all(
        {row["condition"] for row in rows} == set(CONDITIONS)
        for rows in cells.values()
    )

    orders = [
        tuple(str(row["condition"]) for row in cells[index])
        for index in sorted(cells)
    ]
    assert ("full", "artifact") in orders
    assert ("artifact", "full") in orders


def test_frozen_artifact_filters_to_exact_three_keys() -> None:
    full = build_full_request(
        STATES[0],
        state_index=0,
        mapping_index=0,
        order_index=0,
    )
    artifact = filter_request(
        full,
        retained_keys=FROZEN_RETAINED_KEYS,
    )

    assert tuple(datum.key for datum in artifact.context) == (
        "route_open:cave",
        "route_open:ridge",
        "shelter:ridge",
    )


def test_provider_visible_identifiers_are_opaque() -> None:
    forbidden = {
        "cave_only",
        "ridge_only",
        "both_cave_shelter",
        "both_ridge_shelter",
        "K1",
        "K2",
        "K3",
        "K4",
        "N1",
        "N2",
        "N3",
        "N4",
        "N5",
    }

    for state_index, state in enumerate(STATES):
        request = build_full_request(
            state,
            state_index=state_index,
            mapping_index=2,
            order_index=1,
        )
        rendered = render_llama_cpp_request(
            request,
            mode=CognitionMode.BOUNDED,
            model="gemma-local",
        )
        user = json.loads(rendered["messages"][1]["content"])
        metadata = json.dumps(
            {
                "request_id": user["request_id"],
                "provenance": [
                    datum["provenance"]["reference"]
                    for datum in user["context"]
                ],
            },
            sort_keys=True,
        )
        assert all(token not in metadata for token in forbidden)


def _synthetic_observations() -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []
    for state in STATES:
        for condition in CONDITIONS:
            rows.append(
                {
                    "state_id": state.state_id,
                    "family": state.family,
                    "condition": condition,
                    "decision_correct": True,
                    "final_status": (
                        "unresolved"
                        if state.expected_destination is None
                        else "resolved"
                    ),
                }
            )
    return rows


def test_classification_a_when_full_and_artifact_are_correct() -> None:
    rows = _synthetic_observations()

    assert classify_result(rows) == "A_REMAPPING_ROBUST_TESTED_SURFACE"


def test_classification_b_when_only_novel_artifact_breaks() -> None:
    rows = _synthetic_observations()
    target = next(
        row
        for row in rows
        if row["state_id"] == "N1"
        and row["condition"] == "artifact"
    )
    target["decision_correct"] = False
    target["final_status"] = "resolved"

    assert classify_result(rows) == "B_REUSE_BOUNDARY_EXPOSED"


def test_classification_c_when_known_artifact_breaks() -> None:
    rows = _synthetic_observations()
    target = next(
        row
        for row in rows
        if row["state_id"] == "K3"
        and row["condition"] == "artifact"
    )
    target["decision_correct"] = False

    assert classify_result(rows) == "C_REPRESENTATION_DEPENDENT_FAILURE"


def test_classification_d_when_no_route_artifact_resolves() -> None:
    rows = _synthetic_observations()
    target = next(
        row
        for row in rows
        if row["state_id"] == "N3"
        and row["condition"] == "artifact"
    )
    target["decision_correct"] = False
    target["final_status"] = "resolved"

    assert classify_result(rows) == "D_STRONG_SEMANTIC_FAILURE"
