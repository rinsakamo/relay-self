"""D3 original S49 Action issuer/Paper natural kill source negative audit (offline)."""
from copy import deepcopy

import pytest

from tools.bug0_s49_combat_d3_post import D3CombatAuditRejected, audit

WORLD = "11111111-1111-4111-8111-111111111111"
MOB = "22222222-2222-4222-8222-222222222222"
NEW = "33333333-3333-4333-8333-333333333333"
PLAYER = "44444444-4444-4444-8444-444444444444"
LOG = (
    f"RSELF_RESPAWN_INITIAL world={WORLD} entity={MOB} generation=1 tick=10\n"
    f"RSELF_RESPAWN_DEATH world={WORLD} entity={MOB} generation=1 "
    f"tick=102 due_tick=702 paper_drops=1 killer={PLAYER}\n"
    f"RSELF_NATURAL_DROP_DEATH world={WORLD} zombie={MOB} tick=102 "
    f"rotten_count=1 killer={PLAYER} "
    "source=ACTUAL_PAPER_ENTITY_DEATH_DROPS killer_is_relay_self=true\n"
    f"RSELF_RESPAWN_SPAWN world={WORLD} entity={NEW} generation=2 tick=702\n"
)
ACTIONS = [
    dict(
        action_id=f"d3-action-{i}", session_id="s", target_entity_id=26,
        previous_seq=i * 10, admitted_seq=i * 10 + 1,
        effect_seq=i * 10 + 2, after_seq=i * 10 + 3,
        terminal="outcome", ack="applied",
        kill_attested_by_effect_ack=False,
        scope="ORIGINAL_S49_NATIVE_ATTACK_COMMAND_ONLY",
    )
    for i in (1, 2)
]
REPORT = dict(
    status="PASS_DEV", classification="D3_S49_MULTIHIT_PAPER_KILL_RESPAWN_PASS",
    operator_world_kill=False, operator_staged_no_ai=True,
    self_goal_selected_autonomously=False, self_attack_principal_attested=True,
    self_move_to_loot=False, self_eat=False, node_exit=0, java_exit=0,
    attack_count=2, owner_action_count=2, owner_attack_count=2,
    original_supervisor_open_count=0,
    s49_actions=ACTIONS, session_id="s",
    native_initial={"session_id": "s", "seq": 4, "zombie_entity_id": 26},
    native_respawn={"session_id": "s", "seq": 50, "zombie_entity_id": 28},
    real_rotten_flesh_count=1,
)


def test_paper_original_killer_with_two_distinct_s49_actions():
    r = audit(LOG, REPORT)
    assert r["original_s49_attack_action_count"] == 2
    assert r["paper_killer_is_relay_self"] is True
    assert r["source_delta_ticks"] == 600
    assert r["real_rotten_flesh_pickup_proven"] is False


@pytest.mark.parametrize("log", [
    LOG.replace("killer_is_relay_self=true", "killer_is_relay_self=false"),
    LOG.replace(f"killer={PLAYER}", "killer=UNKNOWN", 1),
    LOG.replace("due_tick=702", "due_tick=703"),
    LOG.replace("tick=702\n", "tick=701\n"),
    LOG.replace("generation=2", "generation=1"),
    LOG.replace(f"entity={NEW}", f"entity={MOB}"),
    LOG.replace("rotten_count=1", "rotten_count=2"),
    LOG.replace("source=ACTUAL_PAPER_ENTITY_DEATH_DROPS",
                "source=OPERATOR_SPAWNED_LOOT"),
    LOG + "RSELF_RESPAWN_FAULT new_spawns_fenced=true\n",
    LOG + LOG.splitlines()[2] + "\n",
])
def test_original_world_truth_fail_closed(log):
    with pytest.raises(D3CombatAuditRejected):
        audit(log, REPORT)


@pytest.mark.parametrize("name,value", [
    ("status", "FAIL"),
    ("operator_world_kill", True),
    ("self_attack_principal_attested", False),
    ("self_goal_selected_autonomously", True),
    ("self_move_to_loot", True),
    ("self_eat", True),
    ("attack_count", 1),
    ("owner_action_count", 1),
    ("owner_attack_count", 1),
    ("original_supervisor_open_count", 1),
    ("node_exit", 1),
    ("session_id", "foreign"),
    ("real_rotten_flesh_count", 0),
])
def test_report_may_not_mint_self_or_food_success(name, value):
    report = deepcopy(REPORT)
    report[name] = value
    with pytest.raises(D3CombatAuditRejected):
        audit(LOG, report)


def test_action_replay_and_wrong_native_id_fail():
    for variant in ("replay-id", "same-seq", "different-target", "missing-ack"):
        report = deepcopy(REPORT)
        current = report["s49_actions"][1]
        if variant == "replay-id":
            current["action_id"] = report["s49_actions"][0]["action_id"]
        elif variant == "same-seq":
            current["previous_seq"] = report["s49_actions"][0]["after_seq"]
        elif variant == "different-target":
            current["target_entity_id"] = 27
        else:
            current["ack"] = "rejected"
        with pytest.raises(D3CombatAuditRejected):
            audit(LOG, report)


def test_one_hit_is_allowed_but_not_labelled_repeated():
    report = deepcopy(REPORT)
    report["s49_actions"] = report["s49_actions"][:1]
    report["attack_count"] = 1
    report["owner_action_count"] = 1
    report["owner_attack_count"] = 1
    report["classification"] = "D3_S49_ONE_HIT_PAPER_KILL_RESPAWN_PASS"
    result = audit(LOG, report)
    assert result["original_s49_attack_action_count"] == 1
    assert result["autonomous_target_selection_proven"] is False
