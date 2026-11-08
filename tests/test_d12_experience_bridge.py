"""D12 R2 Learning bridge: no inferred meal, no World/LLM/Memory side effect."""

from __future__ import annotations

from copy import deepcopy

import pytest

from tools.bug0_d12_experience_bridge import (
    D12ExperienceBridgeRejected,
    _project_pass,
    project_d12,
)

WORLD = "11111111-1111-4111-8111-111111111111"
Z1 = "22222222-2222-4222-8222-222222222222"
Z2 = "33333333-3333-4333-8333-333333333333"
Z3 = "44444444-4444-4444-8444-444444444444"
SESSION = "qualified-original-s49"


def sample():
    first = f"RSELF_RESPAWN_INITIAL world={WORLD} entity={Z1} tick=1"
    first_death = f"RSELF_RESPAWN_DEATH world={WORLD} entity={Z1} tick=400"
    second = (f"RSELF_RESPAWN_SPAWN world={WORLD} generation=2 "
              f"entity={Z2} tick=1000")
    third = (f"RSELF_RESPAWN_SPAWN world={WORLD} generation=3 "
             f"entity={Z3} tick=1801")
    r1 = {
        "action_id": "s51-eat-1", "session_id": SESSION,
        "consumed_item": "rotten_flesh", "food_before": 11,
        "food_after": 15, "count_before": 2, "count_after": 1,
    }
    r2 = {
        "action_id": "s51-eat-2", "session_id": SESSION,
        "consumed_item": "rotten_flesh", "food_before": 11,
        "food_after": 15, "count_before": 2, "count_after": 1,
    }
    report = {
        "status": "PASS_DEV", "session_id": SESSION,
        "initial_paper": first, "paper_respawn_death": first_death,
        "paper_respawn": second, "d12_third_paper_spawn": third,
        "native_initial": {"zombie_entity_id": 3},
        "native_respawn": {"zombie_entity_id": 13},
        "d7f_eat_outcome": r1,
        "real_rotten_flesh_count": 2,
        "d6_original_s49_move_actions": [
            {"action_id": "s49-move-1"}, {"action_id": "s49-move-2"},
        ],
        "s49_actions": [{"action_id": "s49-attack-1"}],
        "d8_intent_rearm": {"next_intent": "zombie-gen2"},
        "d8_original_second_attack_action_id": "s49-attack-2",
        "d8_second_generation": {
            "death_tick": 1201, "paper_zombie_uuid": Z2,
            "real_rotten_flesh_count": 1,
            "d7f_eat_outcome": r2,
            "d6_original_s49_move_actions": [{"action_id": "s49-move-3"}],
        },
        "d12_third_rearm": {
            "session_id": SESSION,
            "original_s49_epoch": 3,
            "completed_intent_id": "zombie-gen2",
            "new_intent_id": "zombie-gen3",
            "third_zombie_native_id": 35,
            "native_source_seq": 234,
            "native_request_id": "native-read-3",
            "paper_spawn_tick": 1801, "second_death_tick": 1201,
            "third_physical_action_count": 0,
            "prior_original_action_count": 7,
            "after_rearm_original_action_count": 7,
            "prior_second_s51_action_id": "s51-eat-2",
        },
        "learning_updated": False, "real_model_calls": 0,
    }
    audit = {
        "status": "PASS_DEV",
        "classification": "D12_TWO_TRUE_MEALS_THIRD_REAL_WORLD_INTENT_REARM_PASS",
        "two_real_food_cycles": True,
        "third_real_attack_or_eat": False,
        "third_spawn_after_exactly_600_world_ticks": True,
        "additional_physical_actions": 0,
    }
    return report, "\n".join((first, first_death, second, third)) + "\n", audit


def test_verified_projection_distinguishes_two_food_from_third_intent():
    report, paper, audit = sample()
    view = _project_pass(report, paper, audit)
    assert [e["event_kind"] for e in view] == [
        "OBSERVED_FOOD_CYCLE",
        "OBSERVED_FOOD_CYCLE",
        "OBSERVED_WORLD_RESPAWN_AND_INTENT_REARM",
    ]
    assert [e["intent_epoch"] for e in view] == [1, 2, 3]
    assert len({e["experience_id"] for e in view}) == 3
    assert {e["world_uuid"] for e in view} == {WORLD}
    assert {e["native_session_id"] for e in view} == {SESSION}
    assert [e["observation"]["vanilla_rotten_dropped"] for e in view[:2]] == [2, 1]
    assert [e["observation"]["food_after"] for e in view[:2]] == [15, 15]
    assert view[2]["observation"]["new_original_s49_actions"] == 0
    assert view[2]["observation"]["third_eat"] == "NOT_ISSUED"
    assert all(e["prediction"] is None and e["learned_rule"] is None for e in view)


def test_project_d12_calls_real_independent_audit_before_episode_projection(
    monkeypatch, tmp_path,
):
    import tools.bug0_d12_experience_bridge as mod

    report, paper, audit = sample()
    original = deepcopy(report)
    seen = []

    def fake_audit(p, raw, **kwargs):
        seen.append((p, raw, kwargs))
        return audit

    monkeypatch.setattr(mod, "audit_d12", fake_audit)
    result = project_d12(
        report, paper, nonmotion_path=tmp_path / "nonmotion",
        motion_path=tmp_path / "motion", s50_jsonl="S50 originals",
        source_sha256={"report": "f" * 64},
    )
    assert seen and seen[0][0] is report
    assert result["source_audit"] == audit["classification"]
    assert result["observed_food_cycles"] == 2
    assert result["retained_action_count"] == 7
    assert result["third_intent_committed"] is True
    assert result["third_food_cycle_observed"] is False
    assert result["new_physical_actions"] == 0
    assert result["memory_writes"] == 0
    assert result["l2_calls"] == 0
    assert result["learning_updates"] == 0
    assert result["skill_installs"] == 0
    assert report == original


def test_natural_zero_in_existing_d12_audit_is_not_fake_meal(
    monkeypatch, tmp_path,
):
    import tools.bug0_d12_experience_bridge as mod

    report, paper, _ = sample()
    monkeypatch.setattr(mod, "audit_d12", lambda *_args, **_kwargs: {
        "status": "NOT_EXERCISED",
        "classification": "D12_THIRD_REARM_NOT_EXERCISED_TRUE_ZERO_FOOD",
    })
    result = project_d12(
        report, paper, nonmotion_path=tmp_path / "n",
        motion_path=tmp_path / "m", s50_jsonl="",
        source_sha256={"report": "c" * 64},
    )
    assert result["source_status"] == "NOT_EXERCISED"
    assert result["events"] == []
    assert result["memory_writes"] == 0


@pytest.mark.parametrize(("path", "value"), [
    (("real_model_calls",), 1),
    (("learning_updated",), True),
    (("session_id",), "another-self"),
    (("d12_third_rearm", "session_id"), "another-self"),
    (("d12_third_rearm", "third_physical_action_count"), 1),
    (("d12_third_rearm", "original_s49_epoch"), 2),
    (("d12_third_rearm", "prior_second_s51_action_id"), "old-eat"),
    (("d12_third_rearm", "prior_original_action_count"), 6),
    (("d12_third_rearm", "after_rearm_original_action_count"), 8),
    (("d12_third_rearm", "completed_intent_id"), "stale-intent"),
    (("d12_third_rearm", "paper_spawn_tick"), 1802),
    (("d8_second_generation", "death_tick"), 1200),
    (("d8_second_generation", "real_rotten_flesh_count"), 0),
    (("d7f_eat_outcome", "count_before"), 1),
    (("d7f_eat_outcome", "food_after"), 10),
    (("d8_second_generation", "d7f_eat_outcome", "count_after"), 0),
])
def test_forged_source_never_becomes_experience(path, value):
    report, paper, audit = sample()
    altered = deepcopy(report)
    current = altered
    for part in path[:-1]:
        current = current[part]
    current[path[-1]] = value
    with pytest.raises((D12ExperienceBridgeRejected, ValueError, TypeError)):
        _project_pass(altered, paper, audit)


def test_action_id_replay_or_fabricated_action_rejected():
    report, paper, audit = sample()
    report["d8_second_generation"]["d6_original_s49_move_actions"] = [
        {"action_id": "s49-move-1"},
    ]
    with pytest.raises(D12ExperienceBridgeRejected, match="ACTION_HISTORY_MISMATCH"):
        _project_pass(report, paper, audit)


@pytest.mark.parametrize(("key", "value"), [
    ("two_real_food_cycles", False),
    ("third_real_attack_or_eat", True),
    ("additional_physical_actions", 1),
    ("third_spawn_after_exactly_600_world_ticks", False),
    ("status", "NOT_EXERCISED"),
])
def test_audit_must_be_valid_before_projection(key, value):
    report, paper, audit = sample()
    audit[key] = value
    with pytest.raises(D12ExperienceBridgeRejected, match="INDEPENDENT_SOURCE_NOT"):
        _project_pass(report, paper, audit)


def test_outcome_trace_is_not_rewritten_as_future_prediction():
    report, paper, audit = sample()
    values = _project_pass(report, paper, audit)
    assert all(x["inference"] != "LEARNING_SUCCESS" for x in values)
    assert values[2]["event_kind"] != "OBSERVED_FOOD_CYCLE"
    assert "reliability" not in str(values).lower()
