import json
from unittest.mock import patch

import experiments.mineflayer_cognition_ab as ab
import experiments.mineflayer_cognition_opaque_id_calibration as opaque


def _user_payload(request):
    return json.loads(request["messages"][1]["content"])


def _geometry_by_id(plans):
    return {plan["plan_id"]: plan["waypoints"] for plan in plans}


def _records_for(mapping, repeats=5):
    records = []
    for condition in opaque.OPAQUE_CONDITIONS:
        plan_id = mapping[condition]
        for trial in range(repeats):
            records.append(
                {
                    "trial": trial,
                    "orderIndex": 0,
                    "condition": condition,
                    "planId": plan_id,
                    "transportError": None,
                }
            )
    return records


def test_opaque_ids_are_frozen_and_equal_form():
    assert opaque.OPAQUE_PLAN_IDS == {
        "p_17c4",
        "p_5a92",
        "p_c803",
    }
    assert {len(value) for value in opaque.OPAQUE_PLAN_IDS} == {6}


def test_n0_uses_canonical_geometries_with_opaque_ids():
    canonical = _geometry_by_id(ab.CANDIDATE_PLANS)
    plans = opaque.candidate_plans_for(opaque.N0_CANONICAL)
    actual = _geometry_by_id(plans)
    assert [plan["plan_id"] for plan in plans] == [
        opaque.OPAQUE_DIRECT_SLOT,
        opaque.OPAQUE_DETOUR_SLOT,
        opaque.OPAQUE_OBSERVE_SLOT,
    ]
    assert actual[opaque.OPAQUE_DIRECT_SLOT] == canonical["direct"]
    assert actual[opaque.OPAQUE_DETOUR_SLOT] == canonical["detour"]
    assert actual[opaque.OPAQUE_OBSERVE_SLOT] == canonical["observe"]


def test_n1_swaps_only_first_two_geometry_bindings():
    canonical = _geometry_by_id(ab.CANDIDATE_PLANS)
    actual = _geometry_by_id(
        opaque.candidate_plans_for(opaque.N1_SWAP_FIRST_TWO)
    )
    assert actual[opaque.OPAQUE_DIRECT_SLOT] == canonical["detour"]
    assert actual[opaque.OPAQUE_DETOUR_SLOT] == canonical["direct"]
    assert actual[opaque.OPAQUE_OBSERVE_SLOT] == canonical["observe"]


def test_n2_cycles_geometry_bindings():
    canonical = _geometry_by_id(ab.CANDIDATE_PLANS)
    actual = _geometry_by_id(
        opaque.candidate_plans_for(opaque.N2_CYCLIC_GEOMETRY)
    )
    assert actual[opaque.OPAQUE_DIRECT_SLOT] == canonical["observe"]
    assert actual[opaque.OPAQUE_DETOUR_SLOT] == canonical["direct"]
    assert actual[opaque.OPAQUE_OBSERVE_SLOT] == canonical["detour"]


def test_n3_reverses_only_candidate_order():
    plans = opaque.candidate_plans_for(opaque.N3_REVERSED_ORDER)
    assert [plan["plan_id"] for plan in plans] == [
        opaque.OPAQUE_OBSERVE_SLOT,
        opaque.OPAQUE_DETOUR_SLOT,
        opaque.OPAQUE_DIRECT_SLOT,
    ]
    canonical = _geometry_by_id(ab.CANDIDATE_PLANS)
    actual = _geometry_by_id(plans)
    assert actual[opaque.OPAQUE_DIRECT_SLOT] == canonical["direct"]
    assert actual[opaque.OPAQUE_DETOUR_SLOT] == canonical["detour"]
    assert actual[opaque.OPAQUE_OBSERVE_SLOT] == canonical["observe"]


def test_requests_match_base_except_candidate_ids_and_geometry_binding():
    base = ab.build_request(
        model="model-x",
        include_gradient=False,
        neutral_labels=False,
    )
    base_payload = _user_payload(base)
    rendered = opaque.render_opaque_requests("model-x")

    for condition in opaque.OPAQUE_CONDITIONS:
        request = rendered[condition]["request"]
        payload = _user_payload(request)
        assert request["model"] == base["model"]
        assert request["temperature"] == base["temperature"]
        assert request["max_tokens"] == base["max_tokens"]
        assert request["messages"][0] == base["messages"][0]
        assert payload["task"] == base_payload["task"]
        assert payload["target"] if "target" in payload else True
        assert payload["history"] == base_payload["history"]
        assert payload["signal_semantics"] == base_payload["signal_semantics"]
        assert payload["candidate_plans"] == list(
            opaque.candidate_plans_for(condition)
        )


def test_requests_have_no_gradient_and_no_semantic_plan_ids():
    rendered = opaque.render_opaque_requests("model-x")
    for condition in opaque.OPAQUE_CONDITIONS:
        payload = _user_payload(rendered[condition]["request"])
        history_text = json.dumps(payload["history"], sort_keys=True)
        assert "valueGradient" not in history_text
        plan_ids = {
            plan["plan_id"]
            for plan in payload["candidate_plans"]
        }
        assert plan_ids == opaque.OPAQUE_PLAN_IDS
        assert plan_ids.isdisjoint({"direct", "detour", "observe"})


def test_request_hashes_are_deterministic_and_distinct():
    first = opaque.render_opaque_requests("model-x")
    second = opaque.render_opaque_requests("model-x")
    assert first == second
    hashes = {
        first[condition]["requestHash"]
        for condition in opaque.OPAQUE_CONDITIONS
    }
    assert len(hashes) == 4


def test_render_does_not_call_network():
    with patch(
        "experiments.mineflayer_cognition_ab.urllib.request.urlopen"
    ) as urlopen:
        opaque.render_opaque_requests("model-x")
    urlopen.assert_not_called()


def test_parser_accepts_only_opaque_closed_ids():
    for plan_id in sorted(opaque.OPAQUE_PLAN_IDS):
        parsed = opaque.parse_opaque_choice(
            json.dumps({"plan_id": plan_id})
        )
        assert parsed.plan_id == plan_id
        assert parsed.error is None

    for old_id in ("direct", "detour", "observe"):
        parsed = opaque.parse_opaque_choice(
            json.dumps({"plan_id": old_id})
        )
        assert parsed.plan_id is None
        assert parsed.error == "unknown_plan_id"


def test_parser_accepts_single_full_response_json_fence():
    fence = "`" * 3
    raw = (
        fence
        + 'json\n{"plan_id":"'
        + opaque.OPAQUE_DIRECT_SLOT
        + '"}\n'
        + fence
    )
    parsed = opaque.parse_opaque_choice(raw)
    assert parsed.plan_id == opaque.OPAQUE_DIRECT_SLOT
    assert parsed.error is None


def test_parser_preserves_strict_schema_and_rejects_multiple_fences():
    extra = opaque.parse_opaque_choice(
        json.dumps(
            {
                "plan_id": opaque.OPAQUE_DIRECT_SLOT,
                "reason": "x",
            }
        )
    )
    assert extra.error == "response_schema_mismatch"

    fence = "`" * 3
    multiple = opaque.parse_opaque_choice(
        fence
        + 'json\n{"plan_id":"'
        + opaque.OPAQUE_DIRECT_SLOT
        + '"}\n'
        + fence
        + "\n"
        + fence
        + 'json\n{"plan_id":"'
        + opaque.OPAQUE_DETOUR_SLOT
        + '"}\n'
        + fence
    )
    assert multiple.plan_id is None
    assert multiple.error is not None
    assert multiple.error.startswith("invalid_json:")


def test_summary_classifies_geometry_tracking():
    summary = opaque.summarize(
        _records_for(
            {
                opaque.N0_CANONICAL: opaque.OPAQUE_DIRECT_SLOT,
                opaque.N1_SWAP_FIRST_TWO: opaque.OPAQUE_DETOUR_SLOT,
                opaque.N2_CYCLIC_GEOMETRY: opaque.OPAQUE_DETOUR_SLOT,
                opaque.N3_REVERSED_ORDER: opaque.OPAQUE_DIRECT_SLOT,
            }
        )
    )
    assert summary["classification"] == "G"


def test_summary_classifies_opaque_identity_dominance():
    summary = opaque.summarize(
        _records_for(
            {
                condition: opaque.OPAQUE_DIRECT_SLOT
                for condition in opaque.OPAQUE_CONDITIONS
            }
        )
    )
    assert summary["classification"] == "I"


def test_summary_classifies_order_sensitivity():
    summary = opaque.summarize(
        _records_for(
            {
                opaque.N0_CANONICAL: opaque.OPAQUE_DIRECT_SLOT,
                opaque.N1_SWAP_FIRST_TWO: opaque.OPAQUE_DIRECT_SLOT,
                opaque.N2_CYCLIC_GEOMETRY: opaque.OPAQUE_DIRECT_SLOT,
                opaque.N3_REVERSED_ORDER: opaque.OPAQUE_OBSERVE_SLOT,
            }
        )
    )
    assert summary["classification"] == "O"


def test_summary_classifies_mixed_behavior():
    summary = opaque.summarize(
        _records_for(
            {
                opaque.N0_CANONICAL: opaque.OPAQUE_DIRECT_SLOT,
                opaque.N1_SWAP_FIRST_TWO: opaque.OPAQUE_DETOUR_SLOT,
                opaque.N2_CYCLIC_GEOMETRY: opaque.OPAQUE_DIRECT_SLOT,
                opaque.N3_REVERSED_ORDER: opaque.OPAQUE_DIRECT_SLOT,
            }
        )
    )
    assert summary["classification"] == "M"


def test_summary_classifies_invalid_calibration():
    records = _records_for(
        {
            condition: opaque.OPAQUE_DIRECT_SLOT
            for condition in opaque.OPAQUE_CONDITIONS
        }
    )
    records[0]["planId"] = None
    assert opaque.summarize(records)["classification"] == "X"


def test_run_alternates_condition_order_and_uses_opaque_parser():
    fence = "`" * 3
    response = (
        fence
        + 'json\n{"plan_id":"'
        + opaque.OPAQUE_DIRECT_SLOT
        + '"}\n'
        + fence
    )
    with patch(
        "experiments.mineflayer_cognition_ab.call_openai_compatible",
        side_effect=[response] * 8,
    ) as call:
        result = opaque.run_opaque_calibration(
            endpoint="http://localhost:1234/v1/chat/completions",
            model="model-x",
            api_key=None,
            timeout=1.0,
            repeats=2,
        )

    assert call.call_count == 8
    records = result["records"]
    assert [record["condition"] for record in records[:4]] == list(
        opaque.OPAQUE_CONDITIONS
    )
    assert [record["condition"] for record in records[4:]] == list(
        reversed(opaque.OPAQUE_CONDITIONS)
    )
