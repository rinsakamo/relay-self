import json

import pytest

import experiments.mineflayer_cognition_order_balanced_calibration as balanced
import experiments.mineflayer_cognition_order_marginalized_instrument as instrument


def _records_for(cell_choice):
    records = []
    for item in balanced.render_planned_requests("model-x"):
        plan_id = cell_choice(item)
        binding = item["geometryBinding"]
        positions = item["candidatePositions"]
        selected_geometry = binding[plan_id]
        records.append(
            {
                "executionIndex": len(records),
                "repeat": item["repeat"],
                "geometryMapping": item["geometryMapping"],
                "permutation": item["permutation"],
                "planOrder": item["planOrder"],
                "candidatePositions": positions,
                "model": "model-x",
                "endpoint": {"origin": "fixture"},
                "requestHash": item["requestHash"],
                "rawText": json.dumps({"plan_id": plan_id}),
                "planId": plan_id,
                "selectedPosition": positions[plan_id],
                "selectedGeometry": selected_geometry,
                "directGeometryPlanId": item["directGeometryPlanId"],
                "tracksDirectGeometry": selected_geometry == "direct",
                "parseError": None,
                "transportError": None,
            }
        )
    return records


def _direct_choice(item):
    return item["directGeometryPlanId"]


def test_collapse_uses_one_vote_per_unique_permutation():
    records = _records_for(_direct_choice)
    collapsed = instrument.collapse_repeat_cells(records)

    assert len(records) == 36
    assert len(collapsed) == 18
    assert all(cell["historicalRepeatCount"] == 2 for cell in collapsed)

    keys = {
        (cell["geometryMapping"], cell["permutation"])
        for cell in collapsed
    }
    assert len(keys) == 18


def test_qualified_when_each_mapping_has_strict_direct_majority():
    bad_permutation_by_mapping = {
        balanced.G0_CANONICAL: "CAB",
        balanced.G1_SWAP_FIRST_TWO: "ACB",
        balanced.G2_CYCLIC_GEOMETRY: "CAB",
    }

    def chooser(item):
        mapping = item["geometryMapping"]
        permutation = item["permutation"]
        if permutation == bad_permutation_by_mapping[mapping]:
            direct_id = item["directGeometryPlanId"]
            return next(
                plan_id
                for plan_id in item["planOrder"]
                if plan_id != direct_id
            )
        return direct_id_from(item)

    def direct_id_from(item):
        return item["directGeometryPlanId"]

    result = instrument.qualify_result(
        {"records": _records_for(chooser)}
    )

    assert result["classification"] == instrument.QUALIFIED
    assert result["sourceRecordCount"] == 36
    assert result["uniqueCellCount"] == 18
    assert result["oneVotePerUniquePermutation"] is True
    assert result["strictMajorityThreshold"] == 4

    for mapping in balanced.GEOMETRY_MAPPINGS:
        row = result["mappingResults"][mapping]
        assert row["votes"] == 6
        assert row["directGeometryVotes"] == 5
        assert row["directGeometryStrictMajority"] is True
        assert row["aggregateWinnerGeometry"] == "direct"


def test_qualified_at_exact_four_of_six_direct_votes():
    allowed_direct = {"ABC", "BAC", "BCA", "CBA"}

    def chooser(item):
        if item["permutation"] in allowed_direct:
            return item["directGeometryPlanId"]
        direct_id = item["directGeometryPlanId"]
        return next(
            plan_id
            for plan_id in item["planOrder"]
            if plan_id != direct_id
        )

    result = instrument.qualify_result(
        {"records": _records_for(chooser)}
    )

    assert result["classification"] == instrument.QUALIFIED
    for row in result["mappingResults"].values():
        assert row["directGeometryVotes"] == 4
        assert row["aggregateWinnerGeometry"] == "direct"


def test_not_qualified_without_strict_majority():
    allowed_direct = {"ABC", "BAC", "BCA"}

    def chooser(item):
        if item["permutation"] in allowed_direct:
            return item["directGeometryPlanId"]
        direct_id = item["directGeometryPlanId"]
        return next(
            plan_id
            for plan_id in item["planOrder"]
            if plan_id != direct_id
        )

    result = instrument.qualify_result(
        {"records": _records_for(chooser)}
    )

    assert result["classification"] == instrument.NOT_QUALIFIED
    for row in result["mappingResults"].values():
        assert row["directGeometryVotes"] == 3
        assert row["aggregateWinnerGeometry"] == "NO_MAJORITY"


def test_repeat_disagreement_fails_closed():
    records = _records_for(_direct_choice)
    first = records[0]
    cell_key = (
        first["geometryMapping"],
        first["permutation"],
    )
    mate = next(
        record
        for record in records[1:]
        if (
            record["geometryMapping"],
            record["permutation"],
        )
        == cell_key
    )
    alternate = next(
        plan_id
        for plan_id in mate["planOrder"]
        if plan_id != mate["planId"]
    )
    binding = balanced._GEOMETRY_BINDINGS[mate["geometryMapping"]]
    mate["planId"] = alternate
    mate["selectedGeometry"] = binding[alternate]
    mate["tracksDirectGeometry"] = binding[alternate] == "direct"

    with pytest.raises(
        instrument.InstrumentEvidenceError,
        match="repeat disagreement",
    ):
        instrument.qualify_result({"records": records})


def test_missing_record_fails_closed():
    records = _records_for(_direct_choice)
    with pytest.raises(
        instrument.InstrumentEvidenceError,
        match="expected 36 records",
    ):
        instrument.qualify_result({"records": records[:-1]})


def test_parse_or_transport_error_fails_closed():
    records = _records_for(_direct_choice)
    records[0]["parseError"] = "invalid_json"

    with pytest.raises(
        instrument.InstrumentEvidenceError,
        match="parse error present",
    ):
        instrument.qualify_result({"records": records})


def test_plan_order_must_match_frozen_permutation():
    records = _records_for(_direct_choice)
    records[0]["planOrder"] = list(reversed(records[0]["planOrder"]))

    with pytest.raises(
        instrument.InstrumentEvidenceError,
        match="plan order does not match permutation",
    ):
        instrument.qualify_result({"records": records})


def test_selected_geometry_must_match_frozen_binding():
    records = _records_for(_direct_choice)
    records[0]["selectedGeometry"] = "detour"

    with pytest.raises(
        instrument.InstrumentEvidenceError,
        match="selected geometry disagrees with binding",
    ):
        instrument.qualify_result({"records": records})


def test_aggregation_does_not_double_weight_historical_repeats():
    records = _records_for(_direct_choice)
    collapsed = instrument.collapse_repeat_cells(records)
    g0 = instrument.aggregate_mapping(
        collapsed,
        balanced.G0_CANONICAL,
    )

    assert g0["votes"] == 6
    assert g0["directGeometryVotes"] == 6
    assert sum(g0["geometryVoteCounts"].values()) == 6
