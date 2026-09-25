import copy
import json
from collections import Counter

import experiments.mineflayer_cognition_f46_successor as probe


def _payload(request):
    return json.loads(request["messages"][1]["content"])


def _strip_gradients(history):
    result = copy.deepcopy(history)
    for row in result["frames"]:
        row.pop("valueGradient", None)
    return result


def _block(block_id, mapping, arm, outcome, winner=None):
    return {
        "blockId": block_id,
        "mapping": mapping,
        "arm": arm,
        "outcome": outcome,
        "winnerGeometry": winner,
    }


def _valid_record(row, plan_id):
    return {
        "blockId": row["blockId"],
        "mapping": row["mapping"],
        "arm": row["arm"],
        "permutation": row["permutation"],
        "planOrder": row["planOrder"],
        "requestHash": row["requestHash"],
        "gradientPresent": row["gradientPresent"],
        "executionIndex": row["executionIndex"],
        "rawText": json.dumps({"plan_id": plan_id}),
        "planId": plan_id,
        "selectedGeometry": probe.selected_geometry(
            row["mapping"],
            plan_id,
        ),
        "selectedPosition": probe.selected_position(
            row["planOrder"],
            plan_id,
        ),
        "parseError": None,
        "transportError": None,
    }


def test_frozen_ids_geometries_and_latin_mapping_balance():
    assert probe.OPAQUE_PLAN_IDS == {
        "q_4n7x",
        "q_8p2m",
        "q_6r9k",
    }
    assert probe.GEOMETRIES == {
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

    for plan_id in probe.OPAQUE_PLAN_IDS:
        assigned = [
            probe.GEOMETRY_BINDINGS[mapping][plan_id]
            for mapping in probe.MAPPINGS
        ]
        assert set(assigned) == {"direct", "detour", "observe"}


def test_six_permutations_are_exhaustive():
    assert probe.PERMUTATION_NAMES == (
        "ABC",
        "ACB",
        "BAC",
        "BCA",
        "CAB",
        "CBA",
    )
    assert len(set(probe.PERMUTATION_ORDERS.values())) == 6
    assert all(
        set(order) == probe.OPAQUE_PLAN_IDS
        for order in probe.PERMUTATION_ORDERS.values()
    )


def test_frozen_block_schedule_and_cyclic_permutation_position_balance():
    assert probe.BLOCK_SCHEDULE == (
        ("B0", probe.M0, probe.C0_OBSERVATIONS_ONLY, 0),
        ("B1", probe.M1, probe.C1_EXPLICIT_DERIVED_GRADIENT, 1),
        ("B2", probe.M2, probe.C0_OBSERVATIONS_ONLY, 2),
        ("B3", probe.M2, probe.C1_EXPLICIT_DERIVED_GRADIENT, 3),
        ("B4", probe.M1, probe.C0_OBSERVATIONS_ONLY, 4),
        ("B5", probe.M0, probe.C1_EXPLICIT_DERIVED_GRADIENT, 5),
    )

    ledger = probe.planned_ledger("model-x")
    assert len(ledger) == 36

    by_permutation = {
        name: Counter()
        for name in probe.PERMUTATION_NAMES
    }
    for row in ledger:
        by_permutation[row["permutation"]][row["blockCallIndex"]] += 1

    for counts in by_permutation.values():
        assert counts == {0: 1, 1: 1, 2: 1, 3: 1, 4: 1, 5: 1}


def test_control_and_treatment_requests_differ_only_by_gradients():
    for mapping in probe.MAPPINGS:
        for permutation in probe.PERMUTATION_NAMES:
            control = probe.build_request(
                model="model-x",
                arm=probe.C0_OBSERVATIONS_ONLY,
                mapping=mapping,
                permutation=permutation,
            )
            treatment = probe.build_request(
                model="model-x",
                arm=probe.C1_EXPLICIT_DERIVED_GRADIENT,
                mapping=mapping,
                permutation=permutation,
            )

            control_payload = _payload(control)
            treatment_payload = _payload(treatment)

            assert control["model"] == treatment["model"]
            assert control["temperature"] == treatment["temperature"] == 0
            assert control["max_tokens"] == treatment["max_tokens"] == 32
            assert control["reasoning_effort"] == treatment["reasoning_effort"] == "none"
            assert control["cache_prompt"] is treatment["cache_prompt"] is False
            assert control["messages"][0] == treatment["messages"][0]

            control_history = control_payload.pop("history")
            treatment_history = treatment_payload.pop("history")
            assert control_payload == treatment_payload
            assert _strip_gradients(treatment_history) == control_history

            assert all(
                "valueGradient" not in row
                for row in control_history["frames"]
            )
            assert [
                row["valueGradient"]
                for row in treatment_history["frames"]
                if "valueGradient" in row
            ] == probe.gradient_sequence()


def test_gradient_sequence_is_exactly_frozen_respawn_derivation():
    assert probe.gradient_sequence() == [
        {"tick": 1, "field": "bot.health", "delta": -8.0},
        {"tick": 2, "field": "bot.health", "delta": -12.0},
        {"tick": 3, "field": "bot.health", "delta": 20.0},
    ]


def test_model_facing_candidate_surface_has_no_geometry_or_owner_labels():
    ledger = probe.planned_ledger("model-x")
    forbidden_plan_ids = {"direct", "detour", "observe"}

    for row in ledger:
        payload = _payload(row["request"])
        plans = payload["candidate_plans"]

        assert {plan["plan_id"] for plan in plans} <= probe.OPAQUE_PLAN_IDS
        assert not ({plan["plan_id"] for plan in plans} & forbidden_plan_ids)
        assert "arm" not in payload
        assert "mapping" not in payload
        assert "blockId" not in payload
        assert "executionIndex" not in payload


def test_ledger_is_deterministic_and_hashes_match_requests():
    first = probe.planned_ledger("model-x")
    second = probe.planned_ledger("model-x")
    assert first == second
    assert len(first) == 36
    assert [row["executionIndex"] for row in first] == list(range(36))

    for row in first:
        assert row["requestHash"] == probe._request_hash(row["request"])


def test_parser_accepts_only_frozen_q_ids_and_strict_envelope():
    assert probe.parse_choice('{"plan_id":"q_4n7x"}').plan_id == "q_4n7x"
    fence = chr(96) * 3
    fenced = fence + 'json\n{"plan_id":"q_8p2m"}\n' + fence
    assert probe.parse_choice(fenced).plan_id == "q_8p2m"

    assert probe.parse_choice('{"plan_id":"direct"}').error == "unknown_plan_id"
    assert probe.parse_choice('{"plan_id":"q_4n7x","x":1}').error == (
        "response_schema_mismatch"
    )
    assert probe.parse_choice('prefix {"plan_id":"q_4n7x"}').error.startswith(
        "invalid_json:"
    )


def test_block_aggregator_requires_all_six_calls():
    ledger = probe.planned_ledger("model-x")
    block = [row for row in ledger if row["blockId"] == "B0"]
    records = [_valid_record(row, row["planOrder"][0]) for row in block]

    assert probe.aggregate_block(records[:-1]) == {
        "outcome": "BLOCK_INVALID",
        "reason": "incomplete_block",
    }


def test_block_aggregator_win_and_no_majority():
    ledger = probe.planned_ledger("model-x")
    block = [row for row in ledger if row["blockId"] == "B0"]

    direct_id = next(
        plan_id
        for plan_id, geometry in probe.GEOMETRY_BINDINGS[probe.M0].items()
        if geometry == "direct"
    )
    detour_id = next(
        plan_id
        for plan_id, geometry in probe.GEOMETRY_BINDINGS[probe.M0].items()
        if geometry == "detour"
    )
    observe_id = next(
        plan_id
        for plan_id, geometry in probe.GEOMETRY_BINDINGS[probe.M0].items()
        if geometry == "observe"
    )

    win_ids = [direct_id] * 4 + [detour_id, observe_id]
    win_records = [
        _valid_record(row, plan_id)
        for row, plan_id in zip(block, win_ids, strict=True)
    ]
    win = probe.aggregate_block(win_records)
    assert win["outcome"] == "WIN"
    assert win["winnerGeometry"] == "direct"
    assert win["geometryVoteCounts"]["direct"] == 4

    no_majority_ids = [
        direct_id,
        direct_id,
        detour_id,
        detour_id,
        observe_id,
        observe_id,
    ]
    no_majority_records = [
        _valid_record(row, plan_id)
        for row, plan_id in zip(block, no_majority_ids, strict=True)
    ]
    no_majority = probe.aggregate_block(no_majority_records)
    assert no_majority["outcome"] == "NO_MAJORITY"
    assert no_majority["winnerGeometry"] is None


def test_block_invalid_on_parse_or_transport_error():
    ledger = probe.planned_ledger("model-x")
    block = [row for row in ledger if row["blockId"] == "B0"]
    records = [_valid_record(row, row["planOrder"][0]) for row in block]

    records[0]["parseError"] = "invalid_json"
    assert probe.aggregate_block(records)["outcome"] == "BLOCK_INVALID"

    records = [_valid_record(row, row["planOrder"][0]) for row in block]
    records[0]["transportError"] = "URLError:boom"
    assert probe.aggregate_block(records)["outcome"] == "BLOCK_INVALID"


def test_taxonomy_effect():
    blocks = [
        _block("B0", probe.M0, probe.C0_OBSERVATIONS_ONLY, "WIN", "direct"),
        _block("B1", probe.M1, probe.C1_EXPLICIT_DERIVED_GRADIENT, "WIN", "detour"),
        _block("B2", probe.M2, probe.C0_OBSERVATIONS_ONLY, "WIN", "direct"),
        _block("B3", probe.M2, probe.C1_EXPLICIT_DERIVED_GRADIENT, "WIN", "detour"),
        _block("B4", probe.M1, probe.C0_OBSERVATIONS_ONLY, "WIN", "direct"),
        _block("B5", probe.M0, probe.C1_EXPLICIT_DERIVED_GRADIENT, "WIN", "detour"),
    ]
    assert probe.classify_blocks(blocks) == probe.EFFECT


def test_taxonomy_no_effect():
    blocks = [
        _block("B0", probe.M0, probe.C0_OBSERVATIONS_ONLY, "WIN", "direct"),
        _block("B1", probe.M1, probe.C1_EXPLICIT_DERIVED_GRADIENT, "WIN", "detour"),
        _block("B2", probe.M2, probe.C0_OBSERVATIONS_ONLY, "WIN", "observe"),
        _block("B3", probe.M2, probe.C1_EXPLICIT_DERIVED_GRADIENT, "WIN", "observe"),
        _block("B4", probe.M1, probe.C0_OBSERVATIONS_ONLY, "WIN", "detour"),
        _block("B5", probe.M0, probe.C1_EXPLICIT_DERIVED_GRADIENT, "WIN", "direct"),
    ]
    assert probe.classify_blocks(blocks) == probe.NO_EFFECT


def test_taxonomy_non_discriminating():
    blocks = [
        _block(block_id, mapping, arm, "NO_MAJORITY")
        for block_id, mapping, arm, _ in probe.BLOCK_SCHEDULE
    ]
    assert probe.classify_blocks(blocks) == probe.NON_DISCRIMINATING


def test_taxonomy_mixed():
    blocks = [
        _block("B0", probe.M0, probe.C0_OBSERVATIONS_ONLY, "WIN", "direct"),
        _block("B1", probe.M1, probe.C1_EXPLICIT_DERIVED_GRADIENT, "WIN", "detour"),
        _block("B2", probe.M2, probe.C0_OBSERVATIONS_ONLY, "WIN", "direct"),
        _block("B3", probe.M2, probe.C1_EXPLICIT_DERIVED_GRADIENT, "WIN", "observe"),
        _block("B4", probe.M1, probe.C0_OBSERVATIONS_ONLY, "WIN", "direct"),
        _block("B5", probe.M0, probe.C1_EXPLICIT_DERIVED_GRADIENT, "WIN", "direct"),
    ]
    assert probe.classify_blocks(blocks) == probe.MIXED


def test_taxonomy_invalid():
    blocks = [
        _block(block_id, mapping, arm, "NO_MAJORITY")
        for block_id, mapping, arm, _ in probe.BLOCK_SCHEDULE
    ]
    blocks[0] = {"outcome": "BLOCK_INVALID"}
    assert probe.classify_blocks(blocks) == probe.INVALID
