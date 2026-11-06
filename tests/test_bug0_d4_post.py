"""D4 real-natural-loot post-audit negatives; synthetic sources, World0."""
from copy import deepcopy

import pytest

from test_bug0_s49_combat_d3_post import LOG as D3_LOG
from test_bug0_s49_combat_d3_post import MOB, PLAYER, WORLD
from test_bug0_s49_combat_d3_post import REPORT as D3_REPORT
from tools.bug0_d4_post import D4NaturalEatRejected, audit

ITEM = "55555555-5555-4555-8555-555555555555"
SPAWN = (
    f"RSELF_NATURAL_DROP_SPAWN world={WORLD} zombie={MOB} "
    f"item={ITEM} tick=102 rotten_count=1 "
    "source=ACTUAL_PAPER_ITEM_SPAWN_NEAR_DEATH\n"
)
PICKUP = (
    f"RSELF_NATURAL_DROP_PICKUP world={WORLD} zombie={MOB} "
    f"item={ITEM} player={PLAYER} tick=109 rotten_count=1 "
    "source=ACTUAL_PAPER_ITEM_PICKUP\n"
)
LOG = D3_LOG.replace(
    "RSELF_RESPAWN_SPAWN",
    SPAWN + PICKUP + "RSELF_RESPAWN_SPAWN",
)
BASE_INV = {
    "session_id": "s", "seq": 5, "request_id": "d4-before",
    "provenance": "native:5", "rotten_flesh": 0, "health": 20,
}
AFTER_PICK = {
    "session_id": "s", "seq": 29, "request_id": "d4-pick",
    "provenance": "native:29", "rotten_flesh": 1, "health": 20,
}
AFTER_EAT = {
    "session_id": "s", "seq": 42, "request_id": "d4-eaten",
    "provenance": "native:42", "rotten_flesh": 0, "health": 20,
}
REPORT = dict(
    deepcopy(D3_REPORT),
    classification="D4_REAL_NATURAL_LOOT_PICKUP_S49_EAT_AND_RESPAWN_PASS",
    self_eat=True,
    d4_natural_food_pickup_eat_proven=True,
    d4_self_move_for_item=False,
    d4_item_manual_stage=False,
    d4_operator_hunger_induced_for_dev=True,
    d4_pickup_passive=True,
    d4_eat_terminal="outcome",
    d4_self_eat_issued=True,
    d4_combat_closed_action_count=2,
    d4_final_action_count=3,
    d4_final_supervisor_open_count=0,
    d4_natural_count=1,
    d4_paper_item_spawn=SPAWN.strip(),
    d4_paper_item_pickup=PICKUP.strip(),
    d4_baseline_inventory=BASE_INV,
    d4_native_after_pickup=AFTER_PICK,
    d4_post_eat=AFTER_EAT,
    d4_native_pickup_attempt=1,
    d4_eat_action_id="real-s49-eat",
    d4_eat_outcome={
        "session_id": "s", "action_id": "real-s49-eat",
        "consumed_item": "rotten_flesh",
        "count_before": 1, "count_after": 0,
        "food_before": 12.0, "food_after": 16.0, "after_probe_seq": 37,
    },
    d4_next_food_decision={
        "selected": "WAIT", "reason": "NOT_HUNGRY", "seq": 42,
    },
)


def test_real_natural_uuid_native_pickup_then_one_s49_eat():
    result = audit(LOG, REPORT)
    assert result["natural_item_uuid"] == ITEM
    assert result["real_rotten_flesh_pickup_proven"] is True
    assert result["real_eat_proven"] is True
    assert result["original_s49_total_actions"] == 3
    assert result["self_move_to_loot_proven"] is False
    assert result["unlimited_survival_proven"] is False


@pytest.mark.parametrize("broken", [
    LOG.replace(f"item={ITEM}", "item=66666666-6666-4666-8666-666666666666", 1),
    LOG.replace("tick=109", "tick=703"),
    LOG.replace("rotten_count=1 source=ACTUAL_PAPER_ITEM_PICKUP",
                "rotten_count=2 source=ACTUAL_PAPER_ITEM_PICKUP"),
    LOG.replace("RSELF_NATURAL_DROP_PICKUP", "STAGED_PICKUP"),
    LOG.replace(f"player={PLAYER}", f"player={MOB}"),
    LOG.replace("killer_is_relay_self=true", "killer_is_relay_self=false"),
    LOG + SPAWN,
    LOG + "RSELF_NATURAL_DROP_FAULT ambiguous_item_count=2\n",
])
def test_server_source_must_match_real_item_count_and_killer(broken):
    with pytest.raises(D4NaturalEatRejected):
        audit(broken, REPORT)


@pytest.mark.parametrize("key,value", [
    ("self_move_to_loot", True),
    ("d4_self_move_for_item", True),
    ("d4_item_manual_stage", True),
    ("d4_operator_hunger_induced_for_dev", False),
    ("operator_world_kill", True),
    ("d4_pickup_passive", False),
    ("d4_eat_terminal", "UNKNOWN"),
    ("d4_self_eat_issued", False),
    ("d4_final_action_count", 2),
    ("d4_final_supervisor_open_count", 1),
    ("self_goal_selected_autonomously", True),
    ("node_exit", 1),
])
def test_qualified_physical_action_scope_cannot_be_forged(key, value):
    report = deepcopy(REPORT)
    report[key] = value
    with pytest.raises(D4NaturalEatRejected):
        audit(LOG, report)


@pytest.mark.parametrize("mutate", [
    lambda r: r["d4_native_after_pickup"].update(rotten_flesh=0),
    lambda r: r["d4_baseline_inventory"].update(rotten_flesh=1),
    lambda r: r["d4_post_eat"].update(rotten_flesh=1),
    lambda r: r["d4_eat_outcome"].update(count_after=1),
    lambda r: r["d4_eat_outcome"].update(food_after=11.0),
    lambda r: r["d4_eat_outcome"].update(consumed_item="bread"),
    lambda r: r["d4_eat_outcome"].update(action_id="replayed"),
    lambda r: r["d4_next_food_decision"].update(selected="EAT"),
])
def test_native_food_receipt_must_be_physically_consistent(mutate):
    report = deepcopy(REPORT)
    mutate(report)
    with pytest.raises(D4NaturalEatRejected):
        audit(LOG, report)


def test_real_zero_loot_waits_for_original_world_respawn_but_does_not_eat():
    no_meat_log = D3_LOG.replace("rotten_count=1", "rotten_count=0")
    report = deepcopy(REPORT)
    report.update(
        real_rotten_flesh_count=0,
        classification="D4_GENUINE_ZERO_LOOT_NO_EAT_RESPAWN_PASS",
        self_eat=False,
        d4_natural_food_pickup_eat_proven=False,
        d4_natural_count=0,
        d4_pickup_passive=False,
        d4_eat_terminal="NOT_ISSUED",
        d4_self_eat_issued=False,
        d4_final_action_count=2,
        d4_native_after_zero=AFTER_PICK | {"rotten_flesh": 0},
        d4_paper_item_spawn=None,
        d4_paper_item_pickup=None,
        d4_eat_outcome=None,
    )
    result = audit(no_meat_log, report)
    assert result["classification"] == "D4_GENUINE_ZERO_LOOT_NO_EAT_RESPAWN_PASS"
    assert result["real_eat_proven"] is False
