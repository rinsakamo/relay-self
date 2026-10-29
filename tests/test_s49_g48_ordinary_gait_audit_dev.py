"""G4.8 ordinary Action effect provenance and immutable T2 audit tests."""
import hashlib
import json
from copy import deepcopy

import pytest

from adapters.mineflayer.g48_ordinary_gait_audit_dev import (
    join_g48_ordinary_original_t2_dev,
)


def _args(mode="JOG"):
    act="goal-demo-step-4"
    rmode="JOG_ACTION" if mode=="JOG" else "WALK_ACTION"
    kind=("STABLE_ORDINARY_FORWARD_CANDIDATE" if mode=="JOG"
          else "STABLE_SNEAK_FORWARD_CANDIDATE")
    args={
        "session_id":"one",
        "ordinary_acks":[{
            "action_id":act,"effect_id":act,"ack_seq":10,
            "requested_mode":mode,
            "effect":"set_control" if mode=="JOG" else "set_forward_sneak_dev",
            "source":"ORIGINAL_S49_NATIVE_APPLIED",
        }],
        "original_clear_acks":[{
            "action_id":act,"clear_seq":20,"s16_seq":22,
            "s16_terminal":"outcome",
        }],
        "paper_rows":[],
        "t2_rows":[],
        "original_g47_rows":[],
    }
    for seq,wt,k,after,gait in (
        (12,200,"TRANSITION_OR_UNDETERMINED",False,None),
        (15,201,kind,True,mode),
        (18,202,kind,True,mode),
        (23,203,"STABLE_PHYSICAL_IDLE_CANDIDATE",False,None),
    ):
        frame={
            "session_id":"one","source_seq":seq,"world_tick":wt,
            "kind":k,"g46_challenge_after_control_dev":after,
            "g46_motor_boundary_dev":{
                "action_id":act,"effect_id":act,
                "requested_mode":rmode,"control_phase":"MOVING",
                "control_generation":4,"transition_index":0,
            },
        }
        t2={
            "session_id":"one","source_seq":seq,"world_tick":wt,
            "active_action":act if seq<20 else None,
            "applied_gait":gait,"g3_unknown_fallback_dev":gait is None,
            "g3_extra_m0_paid_dev":0.0,
            "g3_single_p1_owner_dev":True,
            "full_tick_R_attested":False,"qualification":False,
            "p1":{"after":{"fatigue":0.1}},"m0":{"after":{"energy":5.0}},
        }
        sha=hashlib.sha256(json.dumps(
            t2,sort_keys=True,separators=(",",":"),
        ).encode()).hexdigest()
        old={
            "session_id":"one","source_seq":seq,"world_tick":wt,
            "original_active_action":t2["active_action"],
            "original_t2_applied_gait":gait,
            "original_p1":deepcopy(t2["p1"]),
            "original_m0":deepcopy(t2["m0"]),
            "original_t2_row_sha256":sha,
            "status":"UNKNOWN_NO_ORIGINAL_G46_EFFECT_WINDOW",
        }
        args["paper_rows"].append(frame)
        args["t2_rows"].append(t2)
        args["original_g47_rows"].append(old)
    return args


@pytest.mark.parametrize("mode",["JOG","WALK"])
def test_g48_ordinary_original_worldtick_new_candidates(mode):
    a=_args(mode)
    saved=deepcopy(a)
    x=join_g48_ordinary_original_t2_dev(**a)
    assert a==saved
    assert len(x)==len(a["t2_rows"])==4
    assert [r.newly_bound_ordinary_candidate for r in x]==[
        False,True,True,False,
    ]
    assert x[0].g48_status=="UNKNOWN_ORDINARY_PRECHANGE_CHALLENGE"
    assert x[1].g48_status=="SOURCE_BOUND_ORDINARY_GAIT_CANDIDATE_DEV"
    assert x[-1].g48_status=="UNKNOWN_NO_ORIGINAL_G46_EFFECT_WINDOW"
    assert all(not r.p1_m0_reposted and not r.exact_physics_tick_motor_attested
               and not r.new_t2_owner for r in x)
    x[1].original_p1["after"]["fatigue"]=77
    assert a==saved


@pytest.mark.parametrize("failure",[
    "foreign_session","forged_ack","wrong_effect","duplicate_ack",
    "missing_paper","g47_receipt_forgery","nested_p1_change",
    "extra_m0_charge","double_g47_certification",
])
def test_g48_strict_negative_control(failure):
    a=_args()
    if failure=="foreign_session":
        a["t2_rows"][1]["session_id"]="foreign"
    elif failure=="forged_ack":
        a["ordinary_acks"][0]["source"]="forged"
    elif failure=="wrong_effect":
        a["ordinary_acks"][0]["effect"]="set_forward_sneak_dev"
    elif failure=="duplicate_ack":
        a["ordinary_acks"].append(deepcopy(a["ordinary_acks"][0]))
    elif failure=="missing_paper":
        a["paper_rows"].pop(1)
    elif failure=="g47_receipt_forgery":
        a["original_g47_rows"][1]["original_t2_row_sha256"]="0"*64
    elif failure=="nested_p1_change":
        a["original_g47_rows"][1]["original_p1"]["after"]["fatigue"]=123
    elif failure=="extra_m0_charge":
        a["t2_rows"][1]["g3_extra_m0_paid_dev"]=0.25
        a["original_g47_rows"][1]["original_t2_row_sha256"]=hashlib.sha256(
            json.dumps(a["t2_rows"][1],sort_keys=True,
                       separators=(",",":")).encode(),
        ).hexdigest()
    else:
        a["original_g47_rows"][1]["status"]="SOURCE_BOUND_STABLE_GAIT_CANDIDATE_DEV"
    with pytest.raises(ValueError,match="G4.8"):
        join_g48_ordinary_original_t2_dev(**a)


def test_g48_missing_challenge_and_fallback_never_grant_candidate():
    a=_args()
    a["paper_rows"][1]["g46_challenge_after_control_dev"]=False
    a["t2_rows"][2]["applied_gait"]=None
    a["t2_rows"][2]["g3_unknown_fallback_dev"]=True
    a["original_g47_rows"][2]["original_t2_applied_gait"]=None
    a["original_g47_rows"][2]["original_t2_row_sha256"]=hashlib.sha256(
        json.dumps(a["t2_rows"][2],sort_keys=True,
                   separators=(",",":")).encode(),
    ).hexdigest()
    rows=join_g48_ordinary_original_t2_dev(**a)
    assert not any(x.newly_bound_ordinary_candidate for x in rows)
    assert rows[1].g48_status=="UNKNOWN_ORDINARY_PRECHANGE_CHALLENGE"
    assert rows[2].g48_status=="UNKNOWN_ORDINARY_ORIGINAL_T2_FALLBACK"


def test_g48_unseen_ordinary_ack_retains_all_original_unknown():
    a=_args()
    a["ordinary_acks"]=[]
    rows=join_g48_ordinary_original_t2_dev(**a)
    assert all(not x.newly_bound_ordinary_candidate for x in rows)
    assert all(x.g48_status==x.original_g47_status for x in rows)
