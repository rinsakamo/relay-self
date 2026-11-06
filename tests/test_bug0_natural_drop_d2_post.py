"""Do not infer Self killing or natural loot from staged item evidence."""
from copy import deepcopy

import pytest

from tools.bug0_natural_drop_d2_post import NaturalDropD2Rejected, audit

WORLD = "11111111-1111-4111-8111-111111111111"
DEAD = "22222222-2222-4222-8222-222222222222"
NEXT = "33333333-3333-4333-8333-333333333333"
ITEM = "44444444-4444-4444-8444-444444444444"
PLAYER = "55555555-5555-4555-8555-555555555555"
LOG = (
    f"RSELF_RESPAWN_DEATH world={WORLD} entity={DEAD} generation=1 "
    "tick=100 due_tick=700 paper_drops=1 killer=UNKNOWN\n"
    f"RSELF_NATURAL_DROP_DEATH world={WORLD} zombie={DEAD} tick=100 "
    "rotten_count=1 killer=UNKNOWN source=ACTUAL_PAPER_ENTITY_DEATH_DROPS\n"
    f"RSELF_NATURAL_DROP_SPAWN world={WORLD} zombie={DEAD} item={ITEM} "
    "tick=100 rotten_count=1 source=ACTUAL_PAPER_ITEM_SPAWN_NEAR_DEATH\n"
    f"RSELF_NATURAL_DROP_PICKUP world={WORLD} zombie={DEAD} item={ITEM} "
    f"player={PLAYER} tick=102 rotten_count=1 source=ACTUAL_PAPER_ITEM_PICKUP\n"
    f"RSELF_RESPAWN_SPAWN world={WORLD} entity={NEXT} generation=2 tick=700\n"
)
REPORT = {
    "status": "PASS_DEV",
    "classification": "D2_OPERATOR_KILLED_REAL_ZOMBIE_NATURAL_DROP",
    "zombie_kill_principal": "OPERATOR_CONSOLE_ONLY",
    "item_origin": "ACTUAL_PAPER_ZOMBIE_DEATH_EVENT",
    "original_s49_actions": 0,
    "self_move_issued": False, "self_eat_issued": False,
    "java_exit": 0, "node_exit": 0,
    "session_id": "s",
    "native_before": {"seq": 4, "session_id": "s", "rotten_flesh": 0, "health": 20},
    "native_after": {"seq": 20, "session_id": "s", "rotten_flesh": 1, "health": 20},
    "native_initial": {"seq": 7, "session_id": "s", "zombie_entity_id": 26},
    "native_respawn": {"seq": 40, "session_id": "s", "zombie_entity_id": 28},
}


def test_matched_source_but_no_self_credit():
    x = audit(LOG, REPORT)
    assert x["native_inventory_rotten_flesh_delta"] == 1
    assert x["self_attack_issued"] is False
    assert x["autonomous_survival_proven"] is False


@pytest.mark.parametrize("changed", [
    LOG.replace("due_tick=700", "due_tick=699"),
    LOG.replace("tick=700\n", "tick=699\n"),
    LOG.replace(f"item={ITEM}", "item=66666666-6666-4666-8666-666666666666", 1),
    LOG.replace("rotten_count=1 source=ACTUAL_PAPER_ITEM_PICKUP",
                "rotten_count=2 source=ACTUAL_PAPER_ITEM_PICKUP"),
    LOG.replace("tick=102", "tick=99"),
    LOG.replace("source=ACTUAL_PAPER_ENTITY_DEATH_DROPS",
                "source=OPERATOR_STAGED"),
    LOG.replace("RSELF_NATURAL_DROP_SPAWN", "NOT_ACTUAL_ITEM_SPAWN"),
    LOG.replace("rotten_count=1 killer=UNKNOWN", "rotten_count=0 killer=UNKNOWN"),
    LOG.replace(f"entity={NEXT}", f"entity={DEAD}"),
    LOG + "RSELF_NATURAL_DROP_FAULT overlap=TRUE\n",
    LOG + LOG.splitlines()[2] + "\n",
])
def test_unqualified_original(changed):
    with pytest.raises(NaturalDropD2Rejected):
        audit(changed, REPORT)


@pytest.mark.parametrize("k,v", [
    ("status", "FAIL"),
    ("zombie_kill_principal", "SELF"),
    ("item_origin", "OPERATOR_STAGE"),
    ("original_s49_actions", 1),
    ("self_move_issued", True),
    ("self_eat_issued", True),
    ("node_exit", 1),
    ("session_id", "bad"),
])
def test_report_denies_fake_self_credit(k, v):
    r = deepcopy(REPORT)
    r[k] = v
    with pytest.raises(NaturalDropD2Rejected):
        audit(LOG, r)


def test_wrong_native_item_count():
    r = deepcopy(REPORT)
    r["native_after"]["rotten_flesh"] = 0
    with pytest.raises(NaturalDropD2Rejected):
        audit(LOG, r)


def test_death_handlers_can_run_in_either_order():
    rows = LOG.splitlines()
    reordered = "\n".join([rows[1], rows[0], *rows[2:]]) + "\n"
    assert audit(reordered, REPORT)["respawn_server_tick_delta"] == 600
