"""A real zero-drop world still waits for fixed 600 ticks, never invents meat."""
from copy import deepcopy

import pytest

from tools.bug0_natural_drop_d2_post import NaturalDropD2Rejected, audit

WORLD = "11111111-1111-4111-8111-111111111111"
OLD = "22222222-2222-4222-8222-222222222222"
NEW = "33333333-3333-4333-8333-333333333333"
LOG = (
    f"RSELF_RESPAWN_DEATH world={WORLD} entity={OLD} generation=1 "
    "tick=100 due_tick=700 paper_drops=0 killer=UNKNOWN\n"
    f"RSELF_NATURAL_DROP_DEATH world={WORLD} zombie={OLD} tick=100 "
    "rotten_count=0 killer=UNKNOWN source=ACTUAL_PAPER_ENTITY_DEATH_DROPS\n"
    f"RSELF_RESPAWN_SPAWN world={WORLD} entity={NEW} generation=2 tick=700\n"
)
REPORT = {
    "status": "PASS_DEV",
    "classification": "D2_OPERATOR_KILLED_REAL_ZOMBIE_ZERO_LOOT",
    "zombie_kill_principal": "OPERATOR_CONSOLE_ONLY",
    "item_origin": "ACTUAL_PAPER_ZOMBIE_DEATH_EVENT",
    "real_vanilla_loot_count": 0,
    "original_s49_actions": 0,
    "self_move_issued": False,
    "self_attack_issued": False,
    "self_eat_issued": False,
    "node_exit": 0,
    "java_exit": 0,
    "session_id": "s",
    "native_before": {"seq": 5, "session_id": "s", "rotten_flesh": 0, "health": 20},
    "native_after": {"seq": 9, "session_id": "s", "rotten_flesh": 0, "health": 20},
    "native_initial": {"seq": 4, "session_id": "s", "zombie_entity_id": 26},
    "native_respawn": {"seq": 40, "session_id": "s", "zombie_entity_id": 28},
}


def test_zero_is_world_success_but_no_food():
    receipt = audit(LOG, REPORT)
    assert receipt["respawn_server_tick_delta"] == 600
    assert receipt["pickup_proven"] is False
    assert receipt["native_inventory_rotten_flesh_delta"] == 0
    assert receipt["endless_survival_proven"] is False


@pytest.mark.parametrize("log", [
    LOG.replace("due_tick=700", "due_tick=699"),
    LOG.replace("tick=700\n", "tick=699\n"),
    LOG.replace("rotten_count=0", "rotten_count=1"),
    LOG.replace(f"entity={NEW}", f"entity={OLD}"),
    LOG + "RSELF_NATURAL_DROP_SPAWN world=FAKE\n",
    LOG + "RSELF_NATURAL_DROP_PICKUP world=FAKE\n",
    LOG + "RSELF_RESPAWN_FAULT reason=BAD\n",
    LOG + LOG.splitlines()[-1] + "\n",
])
def test_server_truth_contradictions(log):
    with pytest.raises(NaturalDropD2Rejected):
        audit(log, REPORT)


@pytest.mark.parametrize("key,value", [
    ("real_vanilla_loot_count", 1),
    ("original_s49_actions", 1),
    ("self_move_issued", True),
    ("self_eat_issued", True),
    ("self_attack_issued", True),
    ("node_exit", 1),
    ("status", "FAIL"),
])
def test_scope_fail_closed(key, value):
    r = deepcopy(REPORT)
    r[key] = value
    with pytest.raises(NaturalDropD2Rejected):
        audit(LOG, r)


def test_inventory_cannot_mint_rotten_flesh_after_zero_drop():
    r = deepcopy(REPORT)
    r["native_after"]["rotten_flesh"] = 1
    with pytest.raises(NaturalDropD2Rejected):
        audit(LOG, r)


def test_same_native_entity_cannot_be_reborn():
    r = deepcopy(REPORT)
    r["native_respawn"]["zombie_entity_id"] = 26
    with pytest.raises(NaturalDropD2Rejected):
        audit(LOG, r)
