"""R13 original S49 owner Action Catalog and inert conditional Skill tests."""
from __future__ import annotations

import copy
import json

import pytest

from tools import bug0_d14_r13_action_catalog as r13


def skill() -> dict:
    return {
        "name": "guarded eat with retreat fallback",
        "cue": "observed hunger and zombie risk",
        "steps": [
            {
                "action": "ATTACK", "guard": "STABLE_CLOSE_ZOMBIE",
                "binding": "NATIVE_STABLE_ZOMBIE_ID", "repeat": 2,
                "if_unavailable": "SKIP",
            },
            {
                "action": "EAT", "guard": "S51_SAFE_EAT_CANDIDATE",
                "binding": "S51_OBSERVED_EAT_CHOICE", "repeat": 1,
                "if_unavailable": "STOP",
            },
            {
                "action": "WAIT", "guard": "ALWAYS",
                "binding": "NONE", "repeat": 1,
                "if_unavailable": "STOP",
            },
        ],
        "max_actions": 5,
        "stop_condition": "GOAL_OR_SOURCE_CHANGE",
        "on_failure": "ESCALATE",
    }


def test_catalog_reflects_actual_owner_grant_fields() -> None:
    catalog = r13.action_catalog()
    assert catalog["scope"] == "POST_WORLD_L2_REFERENCE_ONLY"
    assert catalog["no_implicit_action_grant"] is True
    assert catalog["no_skill_execution_or_installation"] is True
    assert len(catalog["catalog_sha256"]) == 64
    assert [x["action"] for x in catalog["entries"]] == list(r13.ACTIONS)
    by_action = {x["action"]: x for x in catalog["entries"]}
    assert "target_entity_id" in by_action["ATTACK"][
        "owner_contract"
    ]["authorization_fields"]
    assert "food_slot" in by_action["EAT"][
        "owner_contract"
    ]["authorization_fields"]
    assert "entity_id" in by_action["MOVE_AWAY"][
        "owner_contract"
    ]["authorization_fields"]
    assert by_action["REST"]["kind"] == "intent_only"
    assert by_action["WAIT"]["kind"] == "non_issuing_choice"
    assert by_action["REST"]["binding"] == "NONE"
    assert by_action["WAIT"]["parameters"] == []


def test_catalog_deterministic_and_no_elevation() -> None:
    a, b = r13.action_catalog(), r13.action_catalog()
    assert a == b
    assert not hasattr(r13, "execute_skill")
    assert r13.skill_program_schema()["properties"]["steps"][
        "items"
    ]["additionalProperties"] is False


def test_typed_conditional_program_and_inert_compilation() -> None:
    catalog = r13.action_catalog()
    assert r13.validate_skill_program(skill(), catalog) == skill()
    compiled = r13.shadow_compile(skill(), catalog)
    assert compiled["catalog_sha256"] == catalog["catalog_sha256"]
    assert compiled["total_declared_attempts"] == 4
    assert compiled["max_attempts"] == 5
    assert compiled["physical_actions_issued"] == 0
    assert compiled["authority"] == "NONE"
    assert compiled["skill_installs"] == 0
    assert compiled["learning_updates"] == 0
    assert [s["argument_source"] for s in compiled["conditional_steps"]] == [
        "NATIVE_STABLE_ZOMBIE_ID", "S51_OBSERVED_EAT_CHOICE", "NONE",
    ]


@pytest.mark.parametrize(("step_index", "change"), [
    (0, {"action": "TELEPORT"}),
    (0, {"guard": "ALWAYS"}),
    (0, {"binding": "NONE"}),
    (0, {"binding": "123"}),
    (0, {"repeat": 100}),
    (0, {"repeat": True}),
    (1, {"guard": "STABLE_CLOSE_ZOMBIE"}),
    (1, {"binding": "NATIVE_STABLE_ZOMBIE_ID"}),
    (2, {"binding": "S51_OBSERVED_EAT_CHOICE"}),
    (2, {"if_unavailable": "KEEP_TRYING_FOREVER"}),
    (2, {"extra_call": "run arbitrary python"}),
])
def test_reject_unowned_or_unbounded_step(
    step_index: int, change: dict,
) -> None:
    program = skill()
    program["steps"][step_index].update(change)
    with pytest.raises(r13.CatalogRejected):
        r13.validate_skill_program(program, r13.action_catalog())


@pytest.mark.parametrize("change", [
    {"max_actions": 3},
    {"max_actions": True},
    {"max_actions": 11},
    {"stop_condition": "NEVER_STOP"},
    {"on_failure": "IGNORE_S49_DENIAL"},
    {"cue": ""},
    {"name": ""},
    {"steps": []},
    {"unknown_grant": True},
])
def test_reject_bad_budget_and_extra_physical_authority(change: dict) -> None:
    program = skill()
    program.update(change)
    with pytest.raises(r13.CatalogRejected):
        r13.validate_skill_program(program, r13.action_catalog())


def test_reject_forged_catalog_and_bad_provenance() -> None:
    catalog = r13.action_catalog()
    forged = copy.deepcopy(catalog)
    forged["entries"][0]["guard"] = "ALWAYS"
    with pytest.raises(r13.CatalogRejected, match="SKILL_CATALOG_NOT_CURRENT"):
        r13.validate_skill_program(skill(), forged)


def test_detect_owner_method_signature_drift(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def badly_changed_api(self, unknown):
        return None
    monkeypatch.setattr(
        r13.NormalSessionActionExecutor,
        "require_attack_authorizations", badly_changed_api,
    )
    with pytest.raises(r13.CatalogRejected, match="SIGNATURE_DRIFT"):
        r13.action_catalog()


def test_catalog_and_program_json_roundtrip() -> None:
    catalog = json.loads(json.dumps(r13.action_catalog()))
    program = json.loads(json.dumps(skill()))
    assert r13.validate_skill_program(program, catalog) == program


def test_added_owner_argument_also_rejects(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def expanded_api(
        self, previous_probe, probe, target_entity_id, propose, issue,
        *, unqualified_grant=False,
    ):
        return None
    monkeypatch.setattr(
        r13.NormalSessionActionExecutor,
        "require_attack_authorizations", expanded_api,
    )
    with pytest.raises(r13.CatalogRejected, match="SIGNATURE_DRIFT"):
        r13.action_catalog()


def test_added_authorization_field_rejects(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from types import SimpleNamespace

    original = r13.fields

    def augmented_fields(cls):
        members = list(original(cls))
        if cls is r13.NormalAttackingAuthorization:
            members.append(SimpleNamespace(name="unsafe_new_grant"))
        return members

    monkeypatch.setattr(r13, "fields", augmented_fields)
    with pytest.raises(r13.CatalogRejected, match="FIELDS_DRIFT"):
        r13.action_catalog()
