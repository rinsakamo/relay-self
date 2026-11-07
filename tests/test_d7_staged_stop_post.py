"""D7-D read-only staged D6-C original S49 MOVE → pickup → Paper/S50."""
from __future__ import annotations

import json

import pytest

from tools.bug0_d7_paper_server_tick_post import D7PaperSourceRejected
from tools.bug0_d7_postmove_native_controls_post import D7PassiveReadbackRejected
from tools.bug0_d7_staged_stop_post import (
    D7StagedStopRejected,
    audit_staged_stop,
)

SID = "s49-staged-one-bot-session"
AID = "d6-s49-item-back-1-" + SID
WORLD = "eb8122c1-e748-4033-8b81-5ca240035775"
PLAYER = "cd796add-7f7a-4083-a587-5d409ab487a2"
ITEM = "3816285f-7fc9-4345-92bc-070f227c9100"
OFF = {k: False for k in ("forward", "back", "left", "right",
                        "jump", "sprint", "sneak")}


def source():
    report = {
        "status": "PASS_DEV",
        "classification": "D6_OPERATOR_STAGED_S49_MOVE_PICKUP_PASS",
        "item_origin": "OPERATOR_FIXTURE_NOT_ZOMBIE_DROP",
        "d6_item_origin": "OPERATOR_FIXTURE_NOT_ZOMBIE_DROP",
        "d7_staged_paper_tick_source": True,
        "d7_staged_s50_direct_source": True,
        "d7_staged_original_eat_issued": False,
        "d6_post_move_eat_fenced": True,
        "d6_eat_after_move": False,
        "d6_same_supervisor": True,
        "session_id": SID,
        "node_exit": 0, "java_exit": 0, "cleanup_done": True,
        "real_model_calls": 0, "learning_updated": False,
        "d6_original_s49_move_actions": [{
            "action_id": AID, "session_id": SID,
            "terminal": "outcome", "action_ref": "MOVE_BACKWARD",
            "s15_clear_seq": 14, "s15_after_seq": 15,
        }],
    }
    original = {
        "status": "PASS_DEV",
        "classification": "D6_STAGED_ITEM_ORIGINAL_S49_FENCED_MOVE_PICKUP_PASS",
        "natural_zombie_drop_proven": False,
        "post_move_eat_authorized": False,
        "second_hunt_or_eat_proven": False,
        "physical_exactly_once_attested": False,
        "world_uuid": WORLD, "player_uuid": PLAYER,
        "paper_item_uuid": ITEM, "paper_pickup_tick": 104,
        "original_s49_move_count": 1,
        "original_move_action_ids": [AID],
    }
    client = [{
        "kind": "SESSION_START", "native_seq": 0,
        "client_physics_tick": 0,
    }, {
        "kind": "EFFECT_ACK", "native_seq": 13,
        "native_action_id": AID, "client_physics_tick": 0,
        "controls": {**OFF, "back": True},
    }, {
        "kind": "EFFECT_ACK", "native_seq": 14,
        "native_action_id": AID+"-s15-clear", "client_physics_tick": 0,
        "controls": dict(OFF),
    }]
    client.extend(
        {"kind": "PHYSICS_TICK", "client_physics_tick": t,
         "controls": dict(OFF)}
        for t in range(1, 17)
    )
    client.append({"kind": "SHUTDOWN_ACK", "native_seq": 70,
                   "client_physics_tick": 16, "controls": dict(OFF)})
    return report, original, client


def native_wire(rows):
    return "\n".join(json.dumps({
        "source": "S50_DEV_NATIVE_READBACK_V1", "ordinal": i,
        "session_id": SID, **row,
    }) for i, row in enumerate(rows, 1))+"\n"


def paper_lines():
    rows = [
        "RSELF_D7_PAPER_READY source=PAPER_SERVER_MAIN_THREAD_V1"
        " interval_ticks=1 max_rows=8192 mode=read_only eat_authority=none",
        "RSELF_LOOT_STAGED "
        f"world={WORLD} owner={PLAYER} entity={ITEM} item=rotten_flesh count=1 "
        "tick=100 source=OPERATOR_FIXTURE_NOT_ZOMBIE_DROP",
        "RSELF_LOOT_PICKED "
        f"world={WORLD} owner={PLAYER} entity={ITEM} item=rotten_flesh count=1 "
        "tick=104 source=ACTUAL_PAPER_PICKUP_EVENT",
    ]
    for i in range(20):
        bits = " ".join(f"{k}=false" for k in OFF)
        rows.append(
            "RSELF_D7_PAPER_TICK source=PAPER_SERVER_MAIN_THREAD_V1"
            f" ordinal={i+1} tick={100+i} player={PLAYER} world={WORLD}"
            " x=8.50 y=-60.0 z=10.5 vx=0.0 vy=0.0 vz=0.0"
            f" ground=true {bits}"
        )
    rows.append("RSELF_D7_PAPER_STOP total_ticks=20 input_events=0"
                " truncated=false eat_authority=none")
    return rows


def test_exact_staged_s49_s50_paper_sources_never_grant_stop_or_eat():
    report, original, client = source()
    r = audit_staged_stop("\n".join(paper_lines()), report,
                          original, native_wire(client))
    assert r["status"] == "PASS_DEV"
    assert r["classification"] == "D7_D_STAGED_PAPER_PICKUP_POSTMOVE_SOURCE_ONLY"
    assert r["item_origin"] == "OPERATOR_FIXTURE_NOT_ZOMBIE_DROP"
    assert r["natural_zombie_drop_proven"] is False
    assert r["original_s49_move_ids"] == [AID]
    assert r["original_s50_clear_seq"] == 14
    assert r["paper_pickup_tick"] == 104
    assert r["paper_postpickup_tick_rows"] == 15
    assert r["client_postclear_physics_ticks"] == 16
    assert r["paper_latest_eight_quiet_observed"] is True
    assert r["server_effective_S49_clear_tick"] == "NOT_CAUSALLY_ATTESTED"
    assert r["body_physically_stopped_proven"] is False
    assert r["authenticated_S_owner_EAT_resume_grant"] is False
    assert r["original_EAT_issued"] is False


@pytest.mark.parametrize("mutation", [
    "wrong_stage", "claim_natural", "false_stop", "foreign_session",
    "wrong_move_id", "wrong_paper_item", "wrong_player", "wrong_world",
    "missing_pickup", "duplicate_pickup", "paper_tick_gap",
    "paper_bad_input", "paper_nonfinite", "paper_truncated",
    "paper_too_short", "paper_bad_count", "late_client_move",
    "client_clear_still_held", "client_wrong_clear", "client_legacy_clear_suffix", "fake_eat",
])
def test_corrupt_source_or_fake_authority_fails_closed(mutation):
    report, original, native = source()
    paper = paper_lines()
    if mutation == "wrong_stage":
        report["item_origin"] = "ACTUAL_PAPER_ZOMBIE_DEATH_EVENT"
    elif mutation == "claim_natural":
        original["natural_zombie_drop_proven"] = True
    elif mutation == "false_stop":
        original["post_move_eat_authorized"] = True
    elif mutation == "foreign_session":
        report["session_id"] = "other-bot"
    elif mutation == "wrong_move_id":
        original["original_move_action_ids"] = ["other-move"]
    elif mutation == "wrong_paper_item":
        original["paper_item_uuid"] = "foreign-uuid"
    elif mutation == "wrong_player":
        paper[3] = paper[3].replace(PLAYER, "foreign-player")
    elif mutation == "wrong_world":
        paper[3] = paper[3].replace(WORLD, "other-world")
    elif mutation == "missing_pickup":
        paper.pop(2)
    elif mutation == "duplicate_pickup":
        paper.insert(3, paper[2])
    elif mutation == "paper_tick_gap":
        paper[6] = paper[6].replace("tick=103", "tick=104")
    elif mutation == "paper_bad_input":
        paper[4] = paper[4].replace("back=false", "back=UNKNOWN")
    elif mutation == "paper_nonfinite":
        paper[4] = paper[4].replace("vx=0.0", "vx=NaN")
    elif mutation == "paper_truncated":
        paper.insert(-1, "RSELF_D7_PAPER_TRUNCATED limit=8192")
    elif mutation == "paper_too_short":
        paper = paper[:11] + [
            "RSELF_D7_PAPER_STOP total_ticks=8 input_events=0"
            " truncated=false eat_authority=none"
        ]
    elif mutation == "paper_bad_count":
        paper[-1] = paper[-1].replace("total_ticks=20", "total_ticks=19")
    elif mutation == "late_client_move":
        native[-2]["controls"]["back"] = True
    elif mutation == "client_clear_still_held":
        native[2]["controls"]["back"] = True
    elif mutation == "client_wrong_clear":
        native[2]["native_action_id"] = "foreign-clear"
    elif mutation == "client_legacy_clear_suffix":
        native[2]["native_action_id"] = AID+"-clear"
    elif mutation == "fake_eat":
        report["d7_staged_original_eat_issued"] = True
    with pytest.raises((D7StagedStopRejected, D7PassiveReadbackRejected, D7PaperSourceRejected)):
        audit_staged_stop("\n".join(paper), report, original, native_wire(native))


def test_historical_postpickup_idle_not_latest_body_stationarity():
    report, original, native = source()
    paper = paper_lines()
    paper[-2] = paper[-2].replace("back=false", "back=true")
    result = audit_staged_stop("\n".join(paper), report, original,
                               native_wire(native))
    assert result["paper_postpickup_longest_quiet_streak"] >= 8
    assert result["paper_latest_eight_quiet_observed"] is False
    assert result["authenticated_S_owner_EAT_resume_grant"] is False
