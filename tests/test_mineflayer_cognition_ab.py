import json
from unittest.mock import patch

import experiments.mineflayer_cognition_ab as ab


def _remove_gradients(value):
    if isinstance(value, dict):
        return {k: _remove_gradients(v) for k, v in value.items() if k != "valueGradient"}
    if isinstance(value, list):
        return [_remove_gradients(v) for v in value]
    return value


def _user_payload(request):
    return json.loads(request["messages"][1]["content"])


def test_ab_requests_differ_only_by_value_gradient():
    rendered = ab.render_ab_requests("model-x")
    plain = rendered["observationsOnly"]["request"]
    gradient = rendered["withHealthGradient"]["request"]
    assert plain != gradient
    assert plain["model"] == gradient["model"]
    assert plain["temperature"] == gradient["temperature"]
    assert plain["max_tokens"] == gradient["max_tokens"]
    assert plain["messages"][0] == gradient["messages"][0]
    assert _remove_gradients(_user_payload(plain)) == _remove_gradients(
        _user_payload(gradient)
    )


def test_requests_use_merged_fixture_history():
    rendered = ab.render_ab_requests("model-x")
    plain = _user_payload(rendered["observationsOnly"]["request"])
    gradient = _user_payload(rendered["withHealthGradient"]["request"])
    assert [row["observation"]["health"] for row in plain["history"]["frames"]] == [
        20,
        12,
        0,
        20,
    ]
    deltas = [
        row["valueGradient"]["delta"] for row in gradient["history"]["frames"][1:]
    ]
    assert deltas == [-8, -12, 20]
    assert plain["history"]["frames"][3]["observation"]["events"] == [
        "respawn",
        "health",
    ]


def test_candidate_surface_has_no_affective_labels():
    text = json.dumps({"task": ab.TASK, "candidate_plans": ab.CANDIDATE_PLANS}).lower()
    for banned in ("fear", "danger", "safe", "safety", "hunger", "courage", "emotion"):
        assert banned not in text


def test_request_hashes_are_deterministic_and_distinct():
    first = ab.render_ab_requests("model-x")
    second = ab.render_ab_requests("model-x")
    assert first == second
    assert (
        first["observationsOnly"]["requestHash"]
        != first["withHealthGradient"]["requestHash"]
    )


def test_parse_choice_accepts_only_closed_plan_set():
    assert ab.parse_choice('{"plan_id":"direct"}').plan_id == "direct"
    assert ab.parse_choice('{"plan_id":"detour"}').plan_id == "detour"
    assert ab.parse_choice('{"plan_id":"observe"}').plan_id == "observe"
    assert ab.parse_choice('{"plan_id":"fly"}').error == "unknown_plan_id"
    assert ab.parse_choice("not-json").plan_id is None


def test_endpoint_metadata_strips_query_and_fragment():
    assert (
        ab.endpoint_metadata("http://localhost:1234/v1/chat/completions?token=secret#x")
        == "http://localhost:1234/v1/chat/completions"
    )


def test_render_mode_does_not_call_network():
    with patch("experiments.mineflayer_cognition_ab.urllib.request.urlopen") as urlopen:
        ab.render_ab_requests("model-x")
    urlopen.assert_not_called()
