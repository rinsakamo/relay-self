import json

from adapters.llama_cpp.relay_engine import render_llama_cpp_request
from experiments.identity_prior_trajectory import (
    ACTION_CAPABILITIES,
    AVAILABLE_SKILLS,
    CAUTION_PRIOR,
    COMMON_DIRECTIVES,
    CONDITION_PRIORS,
    EXPLORATION_PRIOR,
    FORBIDDEN_MODEL_VISIBLE_LABELS,
    IDENTITY_CONTEXT_KEY,
    MODEL_RENDER_ID,
    PLANNED_CONDITION_ORDER,
    PLANNED_REPETITIONS_PER_CONDITION,
    build_preparation,
    preparation_report,
    provider_visible_user_payload,
)
from relay_self.relay_engine import CognitionMode


def _without_identity(payload: dict[str, object]) -> dict[str, object]:
    context = payload["context"]
    assert isinstance(context, list)
    return {
        **payload,
        "context": [
            datum
            for datum in context
            if not (
                isinstance(datum, dict)
                and datum.get("key") == IDENTITY_CONTEXT_KEY
            )
        ],
    }


def _identity_datum(payload: dict[str, object]) -> dict[str, object]:
    context = payload["context"]
    assert isinstance(context, list)
    matches = [
        datum
        for datum in context
        if isinstance(datum, dict)
        and datum.get("key") == IDENTITY_CONTEXT_KEY
    ]
    assert len(matches) == 1
    return matches[0]


def test_conditions_share_common_identity_and_only_declared_prior_varies() -> None:
    preparation = build_preparation()
    identities = {
        item.condition_id: item.cognition.identity
        for item in preparation.conditions
    }

    assert identities["A"].directives == COMMON_DIRECTIVES
    assert identities["B"].directives == (
        *COMMON_DIRECTIVES,
        EXPLORATION_PRIOR,
    )
    assert identities["C"].directives == (
        *COMMON_DIRECTIVES,
        CAUTION_PRIOR,
    )
    assert CONDITION_PRIORS == {
        "A": (),
        "B": (EXPLORATION_PRIOR,),
        "C": (CAUTION_PRIOR,),
    }
    assert len({identity.self_id for identity in identities.values()}) == 1
    assert len({identity.provenance for identity in identities.values()}) == 1


def test_condition_labels_do_not_leak_into_actual_llama_cpp_user_payload() -> None:
    preparation = build_preparation()

    for item in preparation.conditions:
        rendered = render_llama_cpp_request(
            item.request,
            mode=CognitionMode.BOUNDED,
            model=MODEL_RENDER_ID,
        )
        rendered_text = json.dumps(
            rendered,
            ensure_ascii=False,
            sort_keys=True,
        ).lower()

        for label in FORBIDDEN_MODEL_VISIBLE_LABELS:
            assert label not in rendered_text
        assert "condition_id" not in rendered_text
        assert "expected_choice" not in rendered_text
        assert "preferred_destination" not in rendered_text


def test_world_skills_budget_and_action_capabilities_are_identical() -> None:
    preparation = build_preparation()
    first = preparation.conditions[0]

    for item in preparation.conditions:
        assert item.observation is preparation.observation
        assert item.scenario is preparation.scenario
        assert item.request.choices == first.request.choices
        assert item.request.instruction == first.request.instruction
        assert item.request.request_id == first.request.request_id
        assert item.request.intent_id == first.request.intent_id
        assert item.request.focus == first.request.focus
        assert item.request.think_allowed is True
        assert item.request.soft_wall_time_budget_s is None
        assert item.pre_cognition_decision.skill.value == "FLEE"
        assert item.pre_cognition_decision.destination is None

    assert AVAILABLE_SKILLS == ("WAIT", "EAT", "FLEE")
    assert ACTION_CAPABILITIES == (
        "equip_item",
        "consume_held",
        "look",
        "set_control",
        "clear_controls",
    )


def test_provider_visible_difference_is_only_identity_directives() -> None:
    preparation = build_preparation()
    payloads = {
        item.condition_id: provider_visible_user_payload(item.request)
        for item in preparation.conditions
    }

    common = _without_identity(payloads["A"])
    assert _without_identity(payloads["B"]) == common
    assert _without_identity(payloads["C"]) == common

    identity_a = _identity_datum(payloads["A"])
    identity_b = _identity_datum(payloads["B"])
    identity_c = _identity_datum(payloads["C"])

    assert identity_a["provenance"] == identity_b["provenance"]
    assert identity_a["provenance"] == identity_c["provenance"]
    assert identity_a["value"]["self_id"] == identity_b["value"]["self_id"]
    assert identity_a["value"]["self_id"] == identity_c["value"]["self_id"]
    assert identity_a["value"]["directives"] == list(COMMON_DIRECTIVES)
    assert identity_b["value"]["directives"] == [
        *COMMON_DIRECTIVES,
        EXPLORATION_PRIOR,
    ]
    assert identity_c["value"]["directives"] == [
        *COMMON_DIRECTIVES,
        CAUTION_PRIOR,
    ]


def test_prior_cannot_rewrite_world_authorize_action_or_create_memory() -> None:
    preparation = build_preparation()
    base_world = _without_identity(
        provider_visible_user_payload(preparation.conditions[0].request)
    )

    for item in preparation.conditions:
        payload = provider_visible_user_payload(item.request)
        assert _without_identity(payload) == base_world
        assert item.cognition.memories == ()
        assert not hasattr(item.request, "action_id")
        assert not hasattr(item.request, "authorization")
        assert not hasattr(item.request, "world_state")

        current_entities = next(
            datum
            for datum in item.request.context
            if datum.key == "nearby_entities"
        )
        assert current_entities.provenance.source == "mineflayer"
        assert current_entities.provenance.reference == "fixture-session:1"


def test_mandatory_viability_admission_occurs_before_identity_prior() -> None:
    preparation = build_preparation()

    assert preparation.observation.snapshot.health == 20
    assert preparation.observation.snapshot.food == 20
    assert {
        entity.name
        for entity in preparation.observation.snapshot.nearby_entities
    } == {"zombie"}

    for item in preparation.conditions:
        assert item.pre_cognition_decision.skill.value == "FLEE"
        assert item.pre_cognition_decision.cognition_result is None
        assert item.pre_cognition_decision.destination is None


def test_preparation_report_separates_bookkeeping_and_has_zero_spend() -> None:
    report = preparation_report()

    assert report["phase"] == "apparatus_preparation"
    assert report["scientific_result"] is None
    assert report["scientific_spend"] == {
        "model_calls": 0,
        "minecraft_sessions": 0,
    }

    records = report["conditions"]
    assert isinstance(records, list)
    assert [record["condition_id"] for record in records] == ["A", "B", "C"]

    for record in records:
        provider_payload = record["provider_visible_request"]
        assert isinstance(provider_payload, dict)
        assert "condition_id" not in provider_payload
        assert record["provider_calls"] == 0
        assert record["bound_destination"] is None
        assert record["issued_actions"] == []
        assert record["world_consequences"] == []
        assert record["durable_memory"] == []
        assert record["later_present"] is None
        assert record["later_decision"] is None
        assert record["interpretation_class"] is None


def test_future_spend_protocol_is_predeclared_not_result_tuned() -> None:
    report = preparation_report()
    protocol = report["future_spend_protocol"]
    assert isinstance(protocol, dict)

    assert PLANNED_CONDITION_ORDER == (
        ("A", "B", "C"),
        ("B", "C", "A"),
        ("C", "A", "B"),
    )
    assert PLANNED_REPETITIONS_PER_CONDITION == 3
    assert protocol["condition_order_by_block"] == [
        ["A", "B", "C"],
        ["B", "C", "A"],
        ["C", "A", "B"],
    ]
    assert protocol["repetitions_per_condition"] == 3
    assert "no hidden retry" in protocol["failure_retry_policy"].lower()
