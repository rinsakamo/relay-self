"""D7-E independent real S49/S51 food audit must reject fake success."""
from __future__ import annotations

from pathlib import Path

import pytest

from tools.bug0_d7e_staged_move_eat_post import D7EPostRejected, audit_staged_eat


def source():
    sid = "original-staged-one-session"
    move = "d6-s49-item-back-1-"+sid
    stage = {
        "status": "PASS_DEV",
        "world_uuid": "paper-world",
        "player_uuid": "paper-player",
        "paper_item_uuid": "paper-staged-item",
        "paper_pickup_tick": 55,
        "original_move_action_ids": [move],
        "natural_zombie_drop_proven": False,
        "post_move_eat_authorized": False,
    }
    report = {
        "status": "PASS_DEV",
        "classification": "D6_OPERATOR_STAGED_S49_MOVE_PICKUP_PASS",
        "session_id": sid, "item_origin": "OPERATOR_FIXTURE_NOT_ZOMBIE_DROP",
        "zombie_kill_attested": False,
        "d7e_stage": "ONE_REAL_STAGED_MOVE_PICKUP_STOP_EAT_DEV_PASS",
        "d7e_original_EAT_issued": True,
        "d7e_eat_terminal": "outcome",
        "d7e_stop_original_owner_admitted_dev": True,
        "d7e_physical_server_effective_clear_tick_proven": False,
        "d7e_total_original_s49_action_count": 2,
        "d7e_operator_item_origin": "OPERATOR_FIXTURE_NOT_ZOMBIE_DROP",
        "d7e_original_nonmotion_unresolved": False,
        "node_exit": 0, "java_exit": 0, "cleanup_done": True,
        "d7e_eat_action_id": "d7e-s49-eat-after-move-"+sid,
        "d7e_native_after_eat": {"session_id": sid, "rotten_flesh": 0},
        "d7e_live_stop": {
            "classification": "D7_E_DEV_LIVE_STAGED_BODY_STEADY_SOURCE",
            "session_id": sid, "action_id": move,
            "paper_world_uuid": "paper-world", "paper_player_uuid": "paper-player",
            "paper_item_uuid": "paper-staged-item", "paper_pickup_tick": 55,
            "client_postclear_physics_ticks": 12, "paper_quiet_tail_ticks": 9,
            "server_effective_original_clear_tick": "NOT_CAUSALLY_ATTESTED",
        },
        "d7e_original_eat_outcome": {
            "session_id": sid, "action_id": "d7e-s49-eat-after-move-"+sid,
            "consumed_item": "rotten_flesh", "count_before": 1, "count_after": 0,
            "food_before": 11, "food_after": 15,
        },
    }
    return report, stage


@pytest.mark.parametrize("mutation", [
    "false_stop", "false_eat", "fake_zombie", "wrong_move",
    "wrong_world", "wrong_item", "late_pickup", "nonterminal",
    "spoofed_food", "spoofed_inventory", "fake_causal_tick",
    "zero_paper", "old_session", "other_issuer",
])
def test_fake_eat_or_source_never_reaches_fence(mutation, tmp_path: Path):
    report, stage = source()
    if mutation == "false_stop":
        report["d7e_stop_original_owner_admitted_dev"] = False
    elif mutation == "false_eat":
        report["d7e_original_EAT_issued"] = False
    elif mutation == "fake_zombie":
        report["zombie_kill_attested"] = True
    elif mutation == "wrong_move":
        stage["original_move_action_ids"] = ["wrong"]
    elif mutation == "wrong_world":
        report["d7e_live_stop"]["paper_world_uuid"] = "foreign"
    elif mutation == "wrong_item":
        report["d7e_live_stop"]["paper_item_uuid"] = "foreign"
    elif mutation == "late_pickup":
        report["d7e_live_stop"]["paper_pickup_tick"] = 600
    elif mutation == "nonterminal":
        report["d7e_eat_terminal"] = "unknown"
    elif mutation == "spoofed_food":
        report["d7e_original_eat_outcome"]["food_after"] = 11
    elif mutation == "spoofed_inventory":
        report["d7e_original_eat_outcome"]["count_after"] = 1
    elif mutation == "fake_causal_tick":
        report["d7e_live_stop"]["server_effective_original_clear_tick"] = 72
    elif mutation == "zero_paper":
        report["d7e_live_stop"]["paper_quiet_tail_ticks"] = 0
    elif mutation == "old_session":
        report["d7e_live_stop"]["session_id"] = "foreign"
    elif mutation == "other_issuer":
        report["d7e_total_original_s49_action_count"] = 3
    with pytest.raises(D7EPostRejected):
        audit_staged_eat(report, stage, nonmotion_path=tmp_path/"never-exists")


def test_no_persistent_original_eat_ledger_is_never_a_pass(tmp_path: Path):
    report, stage = source()
    with pytest.raises(Exception):
        audit_staged_eat(report, stage, nonmotion_path=tmp_path/"missing")
