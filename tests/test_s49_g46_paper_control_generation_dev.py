"""G4.6 pure source-generation join; never doubles T2 or claims Paper tick causality."""
from copy import deepcopy

import pytest

from adapters.mineflayer.g46_paper_control_generation_dev import (
    join_g46_control_generation_dev,
)


def _f(seq, tick, mode, gen, effect, kind, *, after=True):
    controls={k:False for k in (
        "forward","back","left","right","jump","sneak","sprint",
    )}
    controls["forward"]=True
    controls["sprint"]=mode=="SPRINT_INPUT"
    controls["sneak"]=mode=="WALK"
    return {
        "session_id":"one","source_seq":seq,"world_tick":tick,
        "kind":kind,"applied_controls":controls,
        "paper_gait":{
            "sprinting":mode=="SPRINT_INPUT","sneaking":mode=="WALK",
            "speed_base":0.1,
            "speed_value":0.13 if mode=="SPRINT_INPUT" else 0.1,
            "speed_modifiers":1 if mode=="SPRINT_INPUT" else 0,
        },
        "g46_motor_boundary_dev":{
            "action_id":"goal-a-step-2","effect_id":effect,
            "requested_mode":mode,
            "control_generation":gen,"control_phase":"MOVING",
            "transition_index":{"SPRINT_INPUT":0,"JOG":1,"WALK":2}[mode],
        },
        "g46_challenge_after_control_dev":after,
    }


def _args():
    action="goal-a-step-2"
    rows=[
        _f(8,200,"SPRINT_INPUT",1,action,
           "STABLE_SPRINT_FORWARD_CANDIDATE"),
        _f(12,201,"JOG",2,action+"-g44-1-jog",
           "TRANSITION_OR_UNDETERMINED"),
        _f(15,202,"JOG",2,action+"-g44-1-jog",
           "STABLE_ORDINARY_FORWARD_CANDIDATE"),
        _f(20,203,"WALK",3,action+"-g44-2-walk",
           "TRANSITION_OR_UNDETERMINED"),
        _f(22,204,"WALK",3,action+"-g44-2-walk",
           "STABLE_SNEAK_FORWARD_CANDIDATE"),
    ]
    return {
        "session_id":"one",
        "original_run_acks":[{
            "action_id":action,"effect_id":action,"ack_seq":6,
            "source":"ORIGINAL_S49_NATIVE_APPLIED",
            "requested_not_paper_gait":True,
        }],
        "transition_acks":[{
            "action_id":action,"parent_s49_issued_action_id":action,
            "effect":"g44_gait_transition_dev","applied":True,
            "world_tick_gait_attested":False,"mode_to":"JOG",
            "native_probe_seq":9,"ack_seq":10,
            "transition_effect_id":action+"-g44-1-jog",
        },{
            "action_id":action,"parent_s49_issued_action_id":action,
            "effect":"g44_gait_transition_dev","applied":True,
            "world_tick_gait_attested":False,"mode_to":"WALK",
            "native_probe_seq":17,"ack_seq":18,
            "transition_effect_id":action+"-g44-2-walk",
        }],
        "original_clear_acks":[{
            "action_id":action,"clear_seq":24,"s16_seq":25,
            "s16_terminal":"outcome",
        }],
        "paper_rows":rows,
        "t2_rows":[{"source_seq":r["source_seq"],"world_tick":r["world_tick"]}
                   for r in rows],
    }


def test_g46_source_generation_for_run_jog_walk_without_tick_attestation():
    rows=join_g46_control_generation_dev(**_args())
    assert [x.requested_input_mode for x in rows]==[
        "SPRINT_INPUT","JOG","WALK",
    ]
    assert [x.post_change_challenge_frames for x in rows]==[1,2,2]
    assert [x.two_frame_stable_candidate_frames for x in rows]==[1,1,1]
    assert [x.observed_node_generations for x in rows]==[(1,),(2,),(3,)]
    assert all(x.status=="PAPER_STABLE_CANDIDATE_NOT_R_QUALIFIED"
               and not x.exact_physics_tick_to_effect_attested
               and not x.second_t2_owner_created for x in rows)


def test_g46_single_concordant_frame_is_weaker_than_stable_gait():
    args=_args()
    args["paper_rows"][3]["g46_challenge_after_control_dev"]=False
    args["paper_rows"][4]["kind"]="TRANSITION_OR_UNDETERMINED"
    rows=join_g46_control_generation_dev(**args)
    assert rows[-1].status=="POST_EFFECT_CHALLENGE_MODE_CONCORDANT"
    assert rows[-1].two_frame_stable_candidate_frames==0


def test_g46_early_challenge_cannot_certify_later_effect():
    args=_args()
    for row in args["paper_rows"]:
        row["g46_challenge_after_control_dev"]=False
    assert all(row.post_change_challenge_frames==0
               for row in join_g46_control_generation_dev(**args))


@pytest.mark.parametrize("mutation",[
    "foreign_original_run","duplicate_original_run",
    "missing_original_t2","contradictory_generation",
    "transition_has_no_original_run","missing_node_generation",
])
def test_g46_rejects_unbound_or_forged_generation_evidence(mutation):
    args=_args()
    if mutation=="foreign_original_run":
        args["original_run_acks"][0]["source"]="forged"
    elif mutation=="duplicate_original_run":
        args["original_run_acks"]*=2
    elif mutation=="missing_original_t2":
        args["t2_rows"].pop()
    elif mutation=="contradictory_generation":
        args["paper_rows"][2]["g46_motor_boundary_dev"]["control_generation"]=9
    elif mutation=="transition_has_no_original_run":
        args["original_run_acks"]=[]
    else:
        args["paper_rows"][1]["g46_motor_boundary_dev"]=None
    with pytest.raises(ValueError,match="G4.[56]"):
        join_g46_control_generation_dev(**args)


def test_g46_wrong_effect_mode_is_unknown_not_false_positive():
    args=deepcopy(_args())
    args["paper_rows"][2]["g46_motor_boundary_dev"]["effect_id"]="different"
    res=join_g46_control_generation_dev(**args)
    assert res[1].matched_callback_frames==1
    assert res[1].two_frame_stable_candidate_frames==0
