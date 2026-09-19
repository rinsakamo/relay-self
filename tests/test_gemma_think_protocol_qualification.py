from experiments.gemma_think_protocol_qualification import (
    TARGET_CANDIDATE_KEY,
    build_reconstructed_request,
    dry_run_payload,
)


def test_dry_run_is_exactly_one_think_call() -> None:
    payload = dry_run_payload()

    assert payload["model_generation_calls"] == 1
    assert payload["mode"] == "think"
    assert payload["surface"]["case_id"] == "cave_only"
    assert payload["surface"]["candidate_key"] == TARGET_CANDIDATE_KEY
    assert payload["request_contract"] == {
        "max_tokens": 256,
        "temperature": 0,
        "reasoning_effort": "none",
        "cache_prompt": False,
    }


def test_reconstructed_request_matches_observed_trial_14_surface() -> None:
    request = build_reconstructed_request()

    assert tuple(datum.key for datum in request.context) == (
        "threat_nearby",
        "route_open:ridge",
        "shelter:cave",
        "shelter:ridge",
        "saturation",
        "tool:pickaxe_durability",
        "xp_level",
        "storage_free_slots",
    )
    values = {
        datum.key: datum.value_json
        for datum in request.context
    }
    assert values["route_open:ridge"] == "false"
    assert values["shelter:cave"] == "true"
    assert "route_open:cave" not in values
