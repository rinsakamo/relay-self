import json
from unittest.mock import patch

import experiments.mineflayer_cognition_ab as ab


def _remove_gradients(value):
    if isinstance(value, dict):
        return {
            k: _remove_gradients(v)
            for k, v in value.items()
            if k not in {"valueGradient", "signal_0"}
        }
    if isinstance(value, list):
        return [_remove_gradients(v) for v in value]
    return value


def _user_payload(request):
    return json.loads(request["messages"][1]["content"])


def test_semantic_ab_requests_differ_only_by_value_gradient():
    rendered = ab.render_ab_requests("model-x")
    plain = rendered[ab.OBSERVATIONS_ONLY]["request"]
    gradient = rendered[ab.WITH_HEALTH_GRADIENT]["request"]
    assert plain != gradient
    assert plain["model"] == gradient["model"]
    assert plain["temperature"] == gradient["temperature"]
    assert plain["max_tokens"] == gradient["max_tokens"]
    assert plain["messages"][0] == gradient["messages"][0]
    assert _remove_gradients(_user_payload(plain)) == _remove_gradients(
        _user_payload(gradient)
    )


def test_neutral_ab_requests_differ_only_by_signal_values():
    rendered = ab.render_ab_requests("model-x")
    plain = rendered[ab.NEUTRAL_OBSERVATIONS_ONLY]["request"]
    gradient = rendered[ab.NEUTRAL_WITH_GRADIENT]["request"]
    assert plain != gradient
    assert plain["model"] == gradient["model"]
    assert plain["messages"][0] == gradient["messages"][0]
    assert _remove_gradients(_user_payload(plain)) == _remove_gradients(
        _user_payload(gradient)
    )


def test_requests_use_merged_fixture_history():
    rendered = ab.render_ab_requests("model-x")
    plain = _user_payload(rendered[ab.OBSERVATIONS_ONLY]["request"])
    gradient = _user_payload(rendered[ab.WITH_HEALTH_GRADIENT]["request"])
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


def test_neutral_history_removes_minecraft_and_human_value_labels():
    rendered = ab.render_ab_requests("model-x")
    for condition in (ab.NEUTRAL_OBSERVATIONS_ONLY, ab.NEUTRAL_WITH_GRADIENT):
        payload = _user_payload(rendered[condition]["request"])
        history_text = json.dumps(payload["history"], sort_keys=True).lower()
        for banned in (
            "health",
            "food",
            "oxygen",
            "death",
            "respawn",
            "hurt",
            "mineflayer",
            "minecraft",
            "danger",
            "safe",
            "fear",
            "survival",
            "hunger",
            "emotion",
        ):
            assert banned not in history_text


def test_neutral_gradient_preserves_values_and_source_association():
    rendered = ab.render_ab_requests("model-x")
    gradient = _user_payload(rendered[ab.NEUTRAL_WITH_GRADIENT]["request"])
    frames = gradient["history"]["frames"]
    assert [row["signal_0"]["delta"] for row in frames[1:]] == [-8, -12, 20]
    assert frames[1]["signal_0"]["source_channel"] == "resource_0"
    assert frames[1]["observation"]["event_source"]["entityId"] == 41


def test_task_candidate_surface_and_signal_semantics_match_all_conditions():
    rendered = ab.render_ab_requests("model-x")
    payloads = [_user_payload(rendered[condition]["request"]) for condition in ab.CONDITIONS]
    first = payloads[0]
    assert all(payload["task"] == first["task"] for payload in payloads)
    assert all(payload["candidate_plans"] == first["candidate_plans"] for payload in payloads)
    assert all(payload["signal_semantics"] == first["signal_semantics"] for payload in payloads)


def test_candidate_surface_has_no_affective_labels():
    text = json.dumps({"task": ab.TASK, "candidate_plans": ab.CANDIDATE_PLANS}).lower()
    for banned in ("fear", "danger", "safe", "safety", "hunger", "courage", "emotion"):
        assert banned not in text


def test_request_hashes_are_deterministic_and_distinct():
    first = ab.render_ab_requests("model-x")
    second = ab.render_ab_requests("model-x")
    assert first == second
    hashes = {first[condition]["requestHash"] for condition in ab.CONDITIONS}
    assert len(hashes) == len(ab.CONDITIONS)


def test_parse_choice_accepts_only_exact_closed_plan_schema():
    assert ab.parse_choice('{"plan_id":"direct"}').plan_id == "direct"
    assert ab.parse_choice('{"plan_id":"detour"}').plan_id == "detour"
    assert ab.parse_choice('{"plan_id":"observe"}').plan_id == "observe"
    assert ab.parse_choice('{"plan_id":"fly"}').error == "unknown_plan_id"
    assert ab.parse_choice('{"plan_id":"direct","reason":"x"}').error == (
        "response_schema_mismatch"
    )
    assert ab.parse_choice("not-json").plan_id is None


def test_parse_choice_accepts_single_full_response_json_fence():
    for plan_id in ("direct", "detour", "observe"):
        raw = f'```json\n{{"plan_id":"{plan_id}"}}\n```'
        parsed = ab.parse_choice(raw)
        assert parsed.plan_id == plan_id
        assert parsed.error is None


def test_parse_choice_accepts_whitespace_around_single_json_fence():
    parsed = ab.parse_choice(
        '  \n```json\n{"plan_id":"direct"}\n```\n  '
    )
    assert parsed.plan_id == "direct"
    assert parsed.error is None


def test_parse_choice_preserves_schema_checks_inside_json_fence():
    extra = ab.parse_choice(
        '```json\n{"plan_id":"direct","reason":"x"}\n```'
    )
    unknown = ab.parse_choice(
        '```json\n{"plan_id":"fly"}\n```'
    )
    assert extra.error == "response_schema_mismatch"
    assert unknown.error == "unknown_plan_id"


def test_parse_choice_rejects_prose_around_json_fence():
    before = ab.parse_choice(
        'choice follows\n```json\n{"plan_id":"direct"}\n```'
    )
    after = ab.parse_choice(
        '```json\n{"plan_id":"direct"}\n```\nchoice complete'
    )
    assert before.plan_id is None
    assert before.error is not None and before.error.startswith("invalid_json:")
    assert after.plan_id is None
    assert after.error is not None and after.error.startswith("invalid_json:")


def test_parse_choice_rejects_multiple_json_fences():
    parsed = ab.parse_choice(
        '```json\n{"plan_id":"direct"}\n```\n'
        '```json\n{"plan_id":"detour"}\n```'
    )
    assert parsed.plan_id is None
    assert parsed.error is not None and parsed.error.startswith("invalid_json:")


def test_endpoint_metadata_strips_query_and_fragment():
    assert (
        ab.endpoint_metadata("http://localhost:1234/v1/chat/completions?token=secret#x")
        == "http://localhost:1234/v1/chat/completions"
    )


def test_render_mode_does_not_call_network():
    with patch("experiments.mineflayer_cognition_ab.urllib.request.urlopen") as urlopen:
        ab.render_ab_requests("model-x")
    urlopen.assert_not_called()


def test_summary_keeps_four_conditions_and_separate_effects():
    records = [
        {"condition": ab.OBSERVATIONS_ONLY, "planId": "direct"},
        {"condition": ab.WITH_HEALTH_GRADIENT, "planId": "detour"},
        {"condition": ab.NEUTRAL_OBSERVATIONS_ONLY, "planId": "direct"},
        {"condition": ab.NEUTRAL_WITH_GRADIENT, "planId": "detour"},
    ]
    summary = ab._summary(records)
    assert set(summary["conditions"]) == set(ab.CONDITIONS)
    assert summary["comparisons"]["semanticGradientEffect"] == 1.0
    assert summary["comparisons"]["neutralGradientEffect"] == 1.0
    assert summary["comparisons"]["semanticPriorWithoutGradient"] == 0.0
    assert summary["comparisons"]["semanticPriorWithGradient"] == 0.0
