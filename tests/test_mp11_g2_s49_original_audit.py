"""Synthetic audit cases built from an archived *single*-Action report.

All changes here are fixture manufacture; none is a real three-Action World.
"""
from __future__ import annotations

import copy
import json
from pathlib import Path

import pytest

from tools.mp11_g2_s49_original_audit import MP11G2Rejected, audit_original

ARCHIVED = Path(__file__).resolve().parents[1] / (
    "docs/evidence/issue653-mp3-host-20261101/run1/s49-report.json"
)


def synthetic():
    d=json.loads(ARCHIVED.read_text())
    assert len(d["actual_native_actions"]) == 1
    origin=d["actual_native_actions"][0]
    session=d["session_id"]
    actions=[]
    typed=[]
    for idx in range(3):
        action=copy.deepcopy(origin)
        eid=20+idx
        action_id=f"s49-native-move-{eid}"
        action["action"]=action_id
        action["event_seq"]=eid
        action["probe_seq"]=21+idx*40
        evidence=action["execution_evidence"]
        evidence["action_id"]=action_id
        before, dispatch, clear, after = (
            evidence["before_observation"],evidence["dispatch_receipt"],
            evidence["cleanup_receipt"],evidence["after_observation"],
        )
        for obj in (before,dispatch,clear,after):
            obj["seq"]+=idx*40
        for req in (before,after):
            req["request_id"]=f"s15:{session}:{action_id}:{'before' if req is before else 'after'}"
        dispatch["action_id"]=action_id
        clear["action_id"]=action_id+"-s15-clear"
        actions.append(action)
        typed.append({
            "action_id":action_id,
            "session_id":session,
            "native_seq":after["seq"],
            "native_ref":f"native-probe:{session}:{after['seq']}:{after['request_id']}",
            "outcome":"outcome",
            "source_status":"executed",
            "before_after_source_original":True,
            "new_action_issuers":0,
        })
    d["actual_native_actions"]=actions
    d["mp11_g2"]={
        "action_budget":3,"l2_provider_calls":0,"l2_selected_trials":0,
        "l10_s10_s11_admissions":0,"paper_s50_windows":0,
        "typed_s16_actions":typed,
    }
    d["decisions"]=[
        {"selected":"WAIT","issued":False,"entity_id":100},
        *[{"selected":"MOVE_AWAY","issued":True,"entity_id":101+i,
           "event_seq":a["event_seq"],"probe_seq":a["probe_seq"]}
          for i,a in enumerate(actions)],
    ]
    d["source_pair_trace"]=[{"event_seq":i} for i in range(4)]
    d["status"]="PASS"
    d["classification"]="DEV_ONLY_MP11_G2_ONE_WORLD_THREE_TYPED_S16_ACTIONS"
    d["node_exit"]=d["server_exit"]=0
    d["real_model_calls"]=0
    d["learning_in_world"]=False
    return d


def test_synthetic_contract_three_actions_and_one_session_only():
    fixture=synthetic()
    result=audit_original(fixture)
    assert result["original_s49_actions"]==3
    assert result["original_s15_clear_receipts"]==3
    assert result["original_typed_s16_outcomes"]==3
    assert result["minecraft_world_uuid"]=="NOT_AVAILABLE_FROM_VANILLA_SOURCE"
    assert result["paper_s50_windows"]==0
    assert result["autonomous_l2_experiment_selection"] is False


@pytest.mark.parametrize("attack",[
    "foreign_session","s16_duplicate","s16_not_executed",
    "missing_action","missing_clear","wrong_clear",
    "no_native_monotonicity","bad_node_exit","not_original_action",
    "learning_admitted","not_original_wait",
])
def test_synthetic_foreign_or_unqualified_action_fail_closed(attack):
    d=synthetic()
    typed=d["mp11_g2"]["typed_s16_actions"]
    if attack=="foreign_session":
        typed[1]["session_id"]="not-this-native-session"
    elif attack=="s16_duplicate":
        typed[1]["action_id"]=typed[0]["action_id"]
    elif attack=="s16_not_executed":
        typed[1]["source_status"]="unknown"
    elif attack=="missing_action":
        d["actual_native_actions"].pop()
    elif attack=="missing_clear":
        d["actual_native_actions"][1]["execution_evidence"]["cleanup_receipt"]=None
    elif attack=="wrong_clear":
        d["actual_native_actions"][1]["execution_evidence"]["cleanup_receipt"]["action_id"]="wrong"
    elif attack=="no_native_monotonicity":
        typed[1]["native_seq"]=typed[0]["native_seq"]
    elif attack=="bad_node_exit":
        d["node_exit"]=1
    elif attack=="not_original_action":
        d["actual_native_actions"][1]["action"]="operator-move-2"
    elif attack=="learning_admitted":
        d["mp11_g2"]["l10_s10_s11_admissions"]=1
    elif attack=="not_original_wait":
        d["decisions"][0]["selected"]="MOVE_AWAY"
    with pytest.raises(MP11G2Rejected):
        audit_original(d)


def test_unmodified_archival_single_action_never_becomes_three_action_evidence():
    report=json.loads(ARCHIVED.read_text())
    with pytest.raises(MP11G2Rejected):
        audit_original(report)
