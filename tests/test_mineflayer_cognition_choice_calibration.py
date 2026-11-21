import json
from unittest.mock import patch

import experiments.mineflayer_cognition_ab as ab
import experiments.mineflayer_cognition_choice_calibration as calibration


def _user_payload(request):
    return json.loads(request["messages"][1]["content"])


def _geometry_by_id(plans):
    return {plan["plan_id"]: plan["waypoints"] for plan in plans}


def _records_for(mapping, repeats=5):
    records = []
    for condition in calibration.CALIBRATION_CONDITIONS:
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


def test_k0_reuses_canonical_candidate_mapping():
    plans = calibration.candidate_plans_for(calibration.K0_CANONICAL)
    assert plans == ab.CANDIDATE_PLANS


def test_k1_swaps_only_direct_and_detour_geometries():
    canonical = _geometry_by_id(ab.CANDIDATE_PLANS)
    plans = calibration.candidate_plans_for(
        calibration.K1_SWAP_DIRECT_DETOUR
    )
    actual = _geometry_by_id(plans)
    assert [plan["plan_id"] for plan in plans] == [
        "direct",
        "detour",
        "observe",
    ]
    assert actual["direct"] == canonical["detour"]
    assert actual["detour"] == canonical["direct"]
    assert actual["observe"] == canonical["observe"]


def test_k2_cycles_geometries_without_renaming_plan_ids():
    canonical = _geometry_by_id(ab.CANDIDATE_PLANS)
    plans = calibration.candidate_plans_for(calibration.K2_CYCLIC_GEOMETRY)
    actual = _geometry_by_id(plans)
    assert [plan["plan_id"] for plan in plans] == [
        "direct",
        "detour",
        "observe",
    ]
    assert actual["direct"] == canonical["observe"]
    assert actual["detour"] == canonical["direct"]
    assert actual["observe"] == canonical["detour"]


def test_k3_reverses_only_candidate_order():
    plans = calibration.candidate_plans_for(calibration.K3_REVERSED_ORDER)
    assert [plan["plan_id"] for plan in plans] == [
        "observe",
        "detour",
        "direct",
    ]
    assert _geometry_by_id(plans) == _geometry_by_id(ab.CANDIDATE_PLANS)


def test_calibration_requests_preserve_base_surface_except_candidates():
    base = ab.build_request(
        model="model-x",
        include_gradient=False,
        neutral_labels=False,
    )
    base_payload = _user_payload(base)

    rendered = calibration.render_calibration_requests("model-x")
    assert set(rendered) == set(calibration.CALIBRATION_CONDITIONS)

    for condition in calibration.CALIBRATION_CONDITIONS:
        request = rendered[condition]["request"]
        payload = _user_payload(request)

        assert request["model"] == base["model"]
        assert request["temperature"] == base["temperature"]
        assert request["max_tokens"] == base["max_tokens"]
        assert request["messages"][0] == base["messages"][0]

        assert payload["task"] == base_payload["task"]
        assert payload["signal_semantics"] == base_payload["signal_semantics"]
        assert payload["history"] == base_payload["history"]
        assert payload["candidate_plans"] == list(
            calibration.candidate_plans_for(condition)
        )


def test_calibration_history_contains_no_value_gradient():
    rendered = calibration.render_calibration_requests("model-x")
    for condition in calibration.CALIBRATION_CONDITIONS:
        payload = _user_payload(rendered[condition]["request"])
        history_text = json.dumps(payload["history"], sort_keys=True)
        assert "valueGradient" not in history_text


def test_calibration_request_hashes_are_deterministic_and_distinct():
    first = calibration.render_calibration_requests("model-x")
    second = calibration.render_calibration_requests("model-x")
    assert first == second
    hashes = {
        first[condition]["requestHash"]
        for condition in calibration.CALIBRATION_CONDITIONS
    }
    assert len(hashes) == len(calibration.CALIBRATION_CONDITIONS)


def test_render_calibration_does_not_call_network():
    with patch(
        "experiments.mineflayer_cognition_ab.urllib.request.urlopen"
    ) as urlopen:
        calibration.render_calibration_requests("model-x")
    urlopen.assert_not_called()


def test_summary_classifies_content_sensitive_positive_control():
    summary = calibration.summarize(
        _records_for(
            {
                calibration.K0_CANONICAL: "direct",
                calibration.K1_SWAP_DIRECT_DETOUR: "detour",
                calibration.K2_CYCLIC_GEOMETRY: "detour",
                calibration.K3_REVERSED_ORDER: "direct",
            }
        )
    )
    assert summary["classification"] == "P"
    assert (
        summary["conditions"][calibration.K1_SWAP_DIRECT_DETOUR][
            "tracksShortestGeometryRate"
        ]
        == 1.0
    )
    assert (
        summary["conditions"][calibration.K2_CYCLIC_GEOMETRY][
            "tracksShortestGeometryRate"
        ]
        == 1.0
    )


def test_summary_classifies_lexical_direct_dominance():
    summary = calibration.summarize(
        _records_for(
            {
                condition: "direct"
                for condition in calibration.CALIBRATION_CONDITIONS
            }
        )
    )
    assert summary["classification"] == "L"
    assert (
        summary["conditions"][calibration.K1_SWAP_DIRECT_DETOUR][
            "tracksShortestGeometryRate"
        ]
        == 0.0
    )


def test_summary_classifies_order_sensitivity():
    summary = calibration.summarize(
        _records_for(
            {
                calibration.K0_CANONICAL: "direct",
                calibration.K1_SWAP_DIRECT_DETOUR: "direct",
                calibration.K2_CYCLIC_GEOMETRY: "direct",
                calibration.K3_REVERSED_ORDER: "observe",
            }
        )
    )
    assert summary["classification"] == "O"


def test_summary_classifies_mixed_behavior():
    records = _records_for(
        {
            calibration.K0_CANONICAL: "direct",
            calibration.K1_SWAP_DIRECT_DETOUR: "direct",
            calibration.K2_CYCLIC_GEOMETRY: "detour",
            calibration.K3_REVERSED_ORDER: "direct",
        }
    )
    assert calibration.summarize(records)["classification"] == "M"


def test_summary_classifies_invalid_calibration():
    records = _records_for(
        {
            condition: "direct"
            for condition in calibration.CALIBRATION_CONDITIONS
        }
    )
    records[0]["planId"] = None
    assert calibration.summarize(records)["classification"] == "X"


def test_run_calibration_alternates_condition_order_and_uses_parser():
    responses = [
        '```json\n{"plan_id":"direct"}\n```'
        for _ in range(8)
    ]
    with patch(
        "experiments.mineflayer_cognition_ab.call_openai_compatible",
        side_effect=responses,
    ) as call:
        result = calibration.run_calibration(
            endpoint="http://localhost:1234/v1/chat/completions",
            model="model-x",
            api_key=None,
            timeout=1.0,
            repeats=2,
        )

    assert call.call_count == 8
    records = result["records"]
    assert [record["condition"] for record in records[:4]] == list(
        calibration.CALIBRATION_CONDITIONS
    )
    assert [record["condition"] for record in records[4:]] == list(
        reversed(calibration.CALIBRATION_CONDITIONS)
    )
    assert all(record["planId"] == "direct" for record in records)
