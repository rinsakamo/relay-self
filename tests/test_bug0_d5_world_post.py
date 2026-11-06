"""D5 post-audit negatives; no real World or physical Action in these tests."""
from __future__ import annotations

from copy import deepcopy

import pytest

from tools import bug0_d5_post as post


def _report():
    sid = "session-a"
    return {
        "status": "PASS_DEV",
        "classification": "D5_REAL_S49_SECOND_INTENT_ATTACK_PASS",
        "node_exit": 0, "java_exit": 0, "cleanup_done": True,
        "d4_natural_food_pickup_eat_proven": True,
        "d5_second_experience_completed": False,
        "d5_second_kill_attested": False,
        "d5_self_move_to_loot": False,
        "session_id": sid,
        "native_initial": {"zombie_entity_id": 21},
        "native_respawn": {"zombie_entity_id": 35, "seq": 70},
        "d4_final_action_count": 3,
        "s49_actions": [
            {"action_id": "attack1", "after_seq": 10},
            {"action_id": "attack2", "after_seq": 20},
        ],
        "d5_new_zombie_native": {
            "session_id": sid, "zombie_entity_id": 35, "seq": 75,
            "source": "native-75", "request_id": "read-75",
            "candidate_count": 1, "truncated": False,
        },
        "d5_rearm": {
            "session_id": sid, "completed_intent_id": "escape-threat",
            "next_intent_id": "bug0-d5-second-zombie-encounter",
            "next_epoch": 2, "completed_action_count": 3,
            "previous_zombie_entity_id": 21, "next_zombie_entity_id": 35,
            "next_source": "native-75", "physically_issued": False,
        },
        "d5_operator_world_staging": [
            "execute at RelaySelf run tp @e[type=minecraft:zombie,limit=1] ~0.65 ~ ~",
            "data merge entity @e[type=minecraft:zombie,limit=1] {NoAI:1b,Silent:1b}",
        ],
        "d5_second_action": {
            "action_id": "attack-epoch2", "intent_id": "bug0-d5-second-zombie-encounter",
            "session_id": sid, "target_entity_id": 35,
            "previous_seq": 81, "admitted_seq": 82,
            "effect_seq": 83, "after_seq": 84,
            "ack": "applied", "terminal": "outcome",
        },
        "d5_owner_total_action_count": 4,
        "d5_supervisor_open_count": 0,
        "d5_retained_old_actions": True,
        "d5_same_supervisor_identity": True,
    }


def test_d5_reuses_d4_audit_and_second_action_without_cycle_claim(monkeypatch):
    seen = []

    def d4(log, report):
        seen.append((log, report["classification"]))
        return {"classification": "D4_REAL_NATURAL_LOOT_PICKUP_S49_EAT_AND_RESPAWN_PASS"}

    monkeypatch.setattr(post, "audit_d4", d4)
    result = post.audit("Paper original", _report())
    assert seen == [(
        "Paper original", "D4_REAL_NATURAL_LOOT_PICKUP_S49_EAT_AND_RESPAWN_PASS",
    )]
    assert result["second_intent_attack_proven"] is True
    assert result["second_experience_cycle_completed"] is False
    assert result["second_kill_pickup_eat_proven"] is False


@pytest.mark.parametrize(("field", "value"), [
    ("status", "FAIL"),
    ("classification", "D4_REAL_NATURAL_LOOT_PICKUP_S49_EAT_AND_RESPAWN_PASS"),
    ("d5_second_experience_completed", True),
    ("d5_second_kill_attested", True),
    ("d5_same_supervisor_identity", False),
    ("d5_retained_old_actions", False),
    ("d5_supervisor_open_count", 1),
    ("d5_owner_total_action_count", 3),
])
def test_d5_refuses_broken_source_and_false_cycle(monkeypatch, field, value):
    monkeypatch.setattr(post, "audit_d4", lambda *_: {})
    report = _report()
    report[field] = value
    with pytest.raises(post.D5OriginalAuditRejected):
        post.audit("original", report)


@pytest.mark.parametrize(("field", "value"), [
    ("completed_action_count", 2),
    ("next_epoch", 1),
    ("next_zombie_entity_id", 21),
    ("physically_issued", True),
    ("next_source", "foreign"),
])
def test_d5_rearm_cannot_forge_old_world_proof(monkeypatch, field, value):
    monkeypatch.setattr(post, "audit_d4", lambda *_: {})
    report = _report()
    report["d5_rearm"][field] = value
    with pytest.raises(post.D5OriginalAuditRejected):
        post.audit("original", report)


@pytest.mark.parametrize(("field", "value"), [
    ("action_id", "attack1"),
    ("target_entity_id", 21),
    ("intent_id", "escape-threat"),
    ("admitted_seq", 75),
    ("ack", "rejected"),
    ("terminal", "unknown"),
])
def test_d5_fences_second_action_staleness_and_replay(monkeypatch, field, value):
    monkeypatch.setattr(post, "audit_d4", lambda *_: {})
    report = deepcopy(_report())
    report["d5_second_action"][field] = value
    with pytest.raises(post.D5OriginalAuditRejected):
        post.audit("original", report)


def test_d5_genuine_zero_loot_is_valid_first_outcome(monkeypatch):
    seen = []

    def d4(_log, report):
        seen.append(report["classification"])
        return {"classification": report["classification"]}

    monkeypatch.setattr(post, "audit_d4", d4)
    report = _report()
    report["d4_natural_food_pickup_eat_proven"] = False
    result = post.audit("Paper genuine rotten_count=0", report)
    assert seen == ["D4_GENUINE_ZERO_LOOT_NO_EAT_RESPAWN_PASS"]
    assert result["first_world_zero_loot_valid"] is True
    assert result["first_real_food_eaten"] is False
    assert result["second_intent_attack_proven"] is True
    assert result["second_experience_cycle_completed"] is False


def test_d5_requires_independent_d4_first_cycle(monkeypatch):
    def fail(_log, _report):
        raise ValueError("D4 original not proven")

    monkeypatch.setattr(post, "audit_d4", fail)
    with pytest.raises(post.D5OriginalAuditRejected):
        post.audit("original", _report())
