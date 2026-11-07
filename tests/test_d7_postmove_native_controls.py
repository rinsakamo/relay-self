"""D7-A: genuine S49 original S15 MOVE -> read-only S50 native client controls.

No EAT or extra S49 Action, no inference about Paper effective release.
"""
from __future__ import annotations

import asyncio
import json
from copy import deepcopy

import pytest

from adapters.mineflayer.process_session import (
    MineflayerProcessSession,
    MineflayerProcessStartError,
)
from adapters.mineflayer.python_protocol import MineflayerLaunchConfig
from tools.bug0_d7_postmove_native_controls_post import (
    D7PassiveReadbackRejected,
    audit_passive_controls,
)

SID="s49-original-native-session"
AID="d6-s49-item-back-1-"+SID
OFF={k: False for k in ("forward", "back", "left", "right", "jump", "sprint", "sneak")}


def fixture():
    report={
        "status":"PASS_DEV","node_exit":0,"java_exit":0,"cleanup_done":True,
        "d7_same_s49_passive_s50_readback":True,
        "d7_paper_effective_stop_proven":False,
        "d7_eat_grant_issued":False,"self_eat":False,
        "d6_post_move_eat_fenced":True,"d6_multigen_no_eat":True,
        "session_id":SID,
        "d6_original_s49_move_actions":[{
            "action_id":AID,"session_id":SID,"action_ref":"MOVE_BACKWARD",
            "terminal":"outcome","s15_clear_seq":14,"s15_after_seq":15,
        }],
    }
    prior={
        "status":"PASS_DEV","no_eat_after_move":True,
        "same_supervisor_retained":True,"unresolved_motion":False,
        "unresolved_nonmotion":False,"session_id":SID,
        "original_move_count":1,
    }
    rows=[{"kind":"SESSION_START","native_seq":0,"client_physics_tick":0}]
    rows.append({"kind":"EFFECT_ACK","native_action_id":AID,
                 "native_seq":13,"client_physics_tick":0,
                 "controls":{**OFF,"back":True}})
    rows.append({"kind":"EFFECT_ACK","native_action_id":AID+"-s15-clear",
                 "native_seq":14,"client_physics_tick":0,"controls":dict(OFF)})
    for i in range(1,13):
        rows.append({"kind":"PHYSICS_TICK",
                     "client_physics_tick":i,"controls":dict(OFF)})
    rows.append({"kind":"SHUTDOWN_ACK","native_seq":66,
                 "client_physics_tick":12,"controls":dict(OFF)})
    return report, prior, rows


def wire(rows):
    return "\n".join(json.dumps({
        "source":"S50_DEV_NATIVE_READBACK_V1", "ordinal":i,
        "session_id":SID, **row
    }) for i,row in enumerate(rows,1))+"\n"


def test_valid_direct_native_control_source_remains_strictly_readonly():
    report,prior,rows=fixture()
    output=audit_passive_controls(wire(rows),report,prior)
    assert output["classification"].endswith("POSTMOVE_QUIET_OBSERVED")
    assert output["post_clear_client_physics_tick_rows"] == 12
    assert output["first_post_clear_client_physics_tick"] == 1
    assert output["eighth_post_clear_client_physics_tick"] == 8
    assert output["source_session"] == SID
    assert output["server_effective_release_tick"] == "NOT_ATTESTED"
    assert output["full_Paper_world_tick_motor_coverage"] == "NOT_ATTESTED"
    assert output["body_physically_stopped_proven"] is False
    assert output["authenticated_S_owner_EAT_resume_grant"] is False
    assert output["original_EAT_issued"] is False


@pytest.mark.parametrize("mutation", [
    "no_clear","legacy_wrong_suffix","wrong_clear_seq","clear_held","postclear_held",
    "postclear_gap","short_window","duplicate_source","wrong_session",
    "bad_source","duplicate_ordinal","missing_shutdown","late_reissue",
    "foreign_move","incomplete_controls","postmove_eat","false_stop_claim",
    "source_audit_not_pass","wrong_original_move_count",
])
def test_native_source_and_owner_mismatch_fail_closed(mutation):
    report,prior,rows=fixture()
    rows=deepcopy(rows)
    if mutation=="no_clear":
        rows[2]["native_action_id"] = "other-clear"
    elif mutation=="legacy_wrong_suffix":
        rows[2]["native_action_id"] = AID+"-clear"
    elif mutation=="wrong_clear_seq":
        rows[2]["native_seq"] = 25
    elif mutation=="clear_held":
        rows[2]["controls"]["back"]=True
    elif mutation=="postclear_held":
        rows[5]["controls"]["forward"]=True
    elif mutation=="postclear_gap":
        rows[5]["client_physics_tick"]=99
    elif mutation=="short_window":
        rows=rows[:10]+[rows[-1]]
        rows[-1]["client_physics_tick"]=6
    elif mutation=="duplicate_source":
        rows.append(deepcopy(rows[-1]))
    elif mutation=="wrong_session":
        report["session_id"]="foreign-owner"
    elif mutation=="bad_source":
        rows[3]["source"]="wrong"
    elif mutation=="duplicate_ordinal":
        rows[3]["ordinal"]=3
    elif mutation=="missing_shutdown":
        rows.pop()
    elif mutation=="late_reissue":
        rows.insert(-1, {"kind":"EFFECT_ACK",
             "native_action_id":"another-move","native_seq":70,
             "client_physics_tick":12,"controls":{**OFF,"back":True}})
    elif mutation=="foreign_move":
        report["d6_original_s49_move_actions"][0]["action_id"]="wrong-action"
    elif mutation=="incomplete_controls":
        del rows[5]["controls"]["sneak"]
    elif mutation=="postmove_eat":
        report["d7_eat_grant_issued"]=True
    elif mutation=="false_stop_claim":
        report["d7_paper_effective_stop_proven"]=True
    elif mutation=="source_audit_not_pass":
        prior["status"]="FAIL"
    elif mutation=="wrong_original_move_count":
        prior["original_move_count"]=2
    with pytest.raises(D7PassiveReadbackRejected):
        audit_passive_controls(wire(rows),report,prior)


def test_duplicate_source_json_field_rejected():
    report,prior,rows=fixture()
    raw=wire(rows).splitlines()
    raw[3]=raw[3].replace('"ordinal": 4', '"ordinal": 4, "ordinal": 4')
    with pytest.raises(D7PassiveReadbackRejected):
        audit_passive_controls("\n".join(raw),report,prior)


def test_passive_bridge_is_explicit_fresh_same_process_scope(monkeypatch,tmp_path):
    for k in ("D7_PASSIVE_CONTROLS_WORLD_ONLY",
              "RELAYSELF_S50_P1_READBACK_FILE"):
        monkeypatch.delenv(k,raising=False)
    config=MineflayerLaunchConfig(
        host="127.0.0.1",port=25565,username="RelaySelf",version="1.21.8",
    )
    path=tmp_path/"native-original-direct-controls.jsonl"
    with pytest.raises(MineflayerProcessStartError):
        asyncio.run(MineflayerProcessSession.launch(
            config,w4_native_orientation_dev=True,
            s50_direct_controls_sidecar_dev=path,
        ))
    assert not path.exists()
    monkeypatch.setenv("D7_PASSIVE_CONTROLS_WORLD_ONLY","1")
    path.write_text("PREVIOUS_WORLD_ALREADY_EXISTS",encoding="utf8")
    with pytest.raises(MineflayerProcessStartError):
        asyncio.run(MineflayerProcessSession.launch(
            config,w4_native_orientation_dev=True,
            s50_direct_controls_sidecar_dev=path,
        ))
    assert path.read_text()=="PREVIOUS_WORLD_ALREADY_EXISTS"
