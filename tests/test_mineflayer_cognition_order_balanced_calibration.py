import json
from collections import Counter, defaultdict
from unittest.mock import patch

import experiments.mineflayer_cognition_opaque_id_calibration as opaque
import experiments.mineflayer_cognition_order_balanced_calibration as balanced


def _user_payload(request):
    return json.loads(request["messages"][1]["content"])


def _synthetic_records(chooser):
    records = []
    for item in balanced.render_planned_requests("model-x"):
        plan_id = chooser(item)
        positions = item["candidatePositions"]
        binding = item["geometryBinding"]
        records.append(
            {
                "repeat": item["repeat"],
                "geometryMapping": item["geometryMapping"],
                "permutation": item["permutation"],
                "planOrder": item["planOrder"],
                "planId": plan_id,
                "selectedPosition": positions[plan_id],
                "selectedGeometry": binding[plan_id],
                "directGeometryPlanId": item["directGeometryPlanId"],
                "tracksDirectGeometry": binding[plan_id] == "direct",
                "rawText": json.dumps({"plan_id": plan_id}),
                "parseError": None,
                "transportError": None,
            }
        )
    return records


def test_permutations_are_exhaustive_and_position_balanced():
    assert [name for name, _ in balanced.PERMUTATIONS] == [
        "ABC",
        "ACB",
        "BAC",
        "BCA",
        "CAB",
        "CBA",
    ]
    assert len({order for _, order in balanced.PERMUTATIONS}) == 6

    positions = {
        plan_id: Counter()
        for plan_id in opaque.OPAQUE_PLAN_IDS
    }
    for _, order in balanced.PERMUTATIONS:
        assert set(order) == opaque.OPAQUE_PLAN_IDS
        for position, plan_id in enumerate(order):
            positions[plan_id][position] += 1

    for counts in positions.values():
        assert counts == {0: 2, 1: 2, 2: 2}


def test_geometry_mappings_match_n0_n1_n2():
    abc = dict(balanced.PERMUTATIONS)["ABC"]
    pairs = (
        (balanced.G0_CANONICAL, opaque.N0_CANONICAL),
        (balanced.G1_SWAP_FIRST_TWO, opaque.N1_SWAP_FIRST_TWO),
        (balanced.G2_CYCLIC_GEOMETRY, opaque.N2_CYCLIC_GEOMETRY),
    )
    for geometry_mapping, opaque_condition in pairs:
        assert balanced.candidate_plans_for(
            geometry_mapping,
            abc,
        ) == opaque.candidate_plans_for(opaque_condition)


def test_planned_cells_follow_predeclared_two_repeat_order():
    cells = balanced.planned_cells()
    assert len(cells) == 36

    repeat0 = cells[:18]
    repeat1 = cells[18:]

    assert [row["geometryMapping"] for row in repeat0] == (
        [balanced.G0_CANONICAL] * 6
        + [balanced.G1_SWAP_FIRST_TWO] * 6
        + [balanced.G2_CYCLIC_GEOMETRY] * 6
    )
    assert [row["permutation"] for row in repeat0] == (
        ["ABC", "ACB", "BAC", "BCA", "CAB", "CBA"] * 3
    )

    assert [row["geometryMapping"] for row in repeat1] == (
        [balanced.G2_CYCLIC_GEOMETRY] * 6
        + [balanced.G1_SWAP_FIRST_TWO] * 6
        + [balanced.G0_CANONICAL] * 6
    )
    assert [row["permutation"] for row in repeat1] == (
        ["CBA", "CAB", "BCA", "BAC", "ACB", "ABC"] * 3
    )


def test_requests_preserve_opaque_surface_except_candidate_order():
    rendered = balanced.render_planned_requests("model-x")
    opaque_rendered = opaque.render_opaque_requests("model-x")
    condition_for_mapping = {
        balanced.G0_CANONICAL: opaque.N0_CANONICAL,
        balanced.G1_SWAP_FIRST_TWO: opaque.N1_SWAP_FIRST_TWO,
        balanced.G2_CYCLIC_GEOMETRY: opaque.N2_CYCLIC_GEOMETRY,
    }

    for item in rendered:
        request = item["request"]
        base_request = opaque_rendered[
            condition_for_mapping[item["geometryMapping"]]
        ]["request"]

        payload = _user_payload(request)
        base_payload = _user_payload(base_request)

        assert request["model"] == base_request["model"]
        assert request["temperature"] == 0
        assert request["max_tokens"] == 32
        assert request["messages"][0] == base_request["messages"][0]

        assert payload["task"] == base_payload["task"]
        assert payload["history"] == base_payload["history"]
        assert payload["signal_semantics"] == base_payload["signal_semantics"]
        assert "valueGradient" not in json.dumps(
            payload["history"],
            sort_keys=True,
        )

        plans = payload["candidate_plans"]
        assert [plan["plan_id"] for plan in plans] == item["planOrder"]
        assert plans == list(
            balanced.candidate_plans_for(
                item["geometryMapping"],
                tuple(item["planOrder"]),
            )
        )


def test_exact_cells_repeat_with_identical_request_hashes():
    rendered = balanced.render_planned_requests("model-x")
    hashes_by_cell = defaultdict(list)
    for item in rendered:
        hashes_by_cell[
            (
                item["geometryMapping"],
                item["permutation"],
            )
        ].append(item["requestHash"])

    assert len(hashes_by_cell) == 18
    assert all(len(hashes) == 2 for hashes in hashes_by_cell.values())
    assert all(len(set(hashes)) == 1 for hashes in hashes_by_cell.values())
    assert len({hashes[0] for hashes in hashes_by_cell.values()}) == 18


def test_render_is_deterministic_and_network_free():
    with patch(
        "experiments.mineflayer_cognition_ab.urllib.request.urlopen"
    ) as urlopen:
        first = balanced.render_planned_requests("model-x")
        second = balanced.render_planned_requests("model-x")
    urlopen.assert_not_called()
    assert first == second


def test_summary_classifies_fully_order_invariant_geometry_tracking():
    records = _synthetic_records(
        lambda item: item["directGeometryPlanId"]
    )
    summary = balanced.summarize(records)
    assert summary["classification"] == "G"
    assert summary["valid"] == 36
    assert summary["exactCellCompleteCount"] == 18
    assert summary["exactCellRepeatAgreementCount"] == 18
    assert summary["exactCellRepeatAgreementRate"] == 1.0
    assert all(
        row["tracksDirectGeometryRate"] == 1.0
        for row in summary["byGeometry"].values()
    )


def test_summary_classifies_pure_candidate_position_dominance():
    records = _synthetic_records(
        lambda item: item["planOrder"][1]
    )
    summary = balanced.summarize(records)
    assert summary["classification"] == "P"
    assert summary["selectedPositionCounts"] == {1: 36}


def test_summary_classifies_opaque_id_identity_dominance():
    records = _synthetic_records(lambda item: balanced.A)
    summary = balanced.summarize(records)
    assert summary["classification"] == "I"


def test_summary_classifies_mixed_behavior():
    records = _synthetic_records(
        lambda item: item["directGeometryPlanId"]
    )
    records[0]["planId"] = balanced.B
    records[0]["selectedPosition"] = records[0]["planOrder"].index(balanced.B)
    binding = balanced._GEOMETRY_BINDINGS[
        records[0]["geometryMapping"]
    ]
    records[0]["selectedGeometry"] = binding[balanced.B]
    records[0]["tracksDirectGeometry"] = binding[balanced.B] == "direct"
    summary = balanced.summarize(records)
    assert summary["classification"] == "M"


def test_summary_classifies_invalid_or_incomplete_dataset():
    records = _synthetic_records(
        lambda item: item["directGeometryPlanId"]
    )
    records[0]["planId"] = None
    assert balanced.summarize(records)["classification"] == "X"
    assert balanced.summarize(records[:-1])["classification"] == "X"
