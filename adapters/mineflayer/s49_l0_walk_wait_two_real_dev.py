"""Two isolated Minecraft Worlds: original third WALK vs original L0 WAIT.

No extra Action issuer, no packet reader, no Paper sync, no P1 grant.
The second S16 is used only for original L0 input timing or genuine WAIT.
"""
from __future__ import annotations

import argparse
import asyncio
import json
import math
import os
from pathlib import Path

from adapters.mineflayer.s49_normal_session_real_ci import qualify


def review_native(mode: str, r: dict) -> dict:
    actions = r.get("actual_native_actions")
    if (
        r.get("status") != "PASS"
        or r.get("real_model_calls") != 0
        or not isinstance(actions, list)
        or len(actions) != (3 if mode == "WALK" else 2)
        or any(a.get("terminal") != "outcome" for a in actions)
        or any(not math.isfinite(a.get("movement_m", float("nan"))) for a in actions)
        or r.get("dev_l0_observed_feedback", {}).get("second_actual_outcome")
           != "outcome"
    ):
        raise ValueError("missing native original S49 S16 source")
    feedback = r["dev_l0_observed_feedback"]
    if (
        feedback.get("session_id") != r.get("session_id")
        or feedback.get("second_action_id") != actions[1]["action"]
        or feedback.get("second_actual_s16_m") != actions[1]["movement_m"]
        or feedback.get("requested_next_step_m") != 1.0
        or feedback.get("goal_reached_attested") is not False
    ):
        raise ValueError("stale closed second native Action")
    result = {
        "mode": mode, "classification":r.get("classification"),
        "session_id":r["session_id"],
        "native_actions":len(actions),
        "native_action_ids":[a["action"] for a in actions],
        "first_s16_m":actions[0]["movement_m"],
        "second_s16_m":actions[1]["movement_m"],
        "second_input_s":feedback["second_input_duration_s"],
        "target_relative_step_m":1.0,
        "same_original_l0":True,
        "new_native_action_issuers":0,
        "new_native_packet_readers":0,
        "node_paper_tick_phase_equivalence":False,
        "absolute_world_goal_attested":False,
        "qualification_go":False,"science_go":False,
    }
    if mode=="WALK":
        third=r.get("dev_l0_residual_third")
        if (
            r.get("classification")
              !="DEV_ONLY_S49_S16_RESIDUAL_THIRD_WALK_ORIGINAL_OWNER"
            or not isinstance(third,dict)
            or third.get("third_gait")!="WALK"
            or third.get("third_action_id")!=actions[2]["action"]
            or third.get("second_action_id")!=actions[1]["action"]
            or third.get("third_terminal_state")!="outcome"
            or third.get("same_original_S49_executor") is not True
            or actions[2].get("execution_evidence",{}).get("action_ref")
               !="MOVE_FORWARD"
            or not 0.10<=third.get("proposed_duration_s",float("nan"))<=0.60
        ):
            raise ValueError("not genuine original L0 third WALK")
        result.update({
            "third_gait":"WALK",
            "third_input_s":third["proposed_duration_s"],
            "third_s16_m":actions[2]["movement_m"],
            "second_only_error_m":third["original_second_only_error_m"],
            "combined_second_third_m":third["second_plus_third_s16_m"],
            "combined_error_m":third["second_plus_third_error_m"],
            "improved_with_walk":(
                third["second_plus_third_error_m"] <
                third["original_second_only_error_m"]
            ),
            "third_physical_action_issued":True,
        })
    else:
        stop=r.get("dev_l0_goal_wait")
        choices=r.get("decisions")
        if (
            r.get("classification")
              !="DEV_ONLY_S49_CLOSED_S16_GOAL_WAIT_NO_THIRD_ACTION"
            or not isinstance(stop,dict)
            or stop.get("original_l0_armed") is not True
            or stop.get("actual_l0_choice")!="WAIT"
            or stop.get("fourth_action_issued") is not False
            or stop.get("original_action_count")!=2
            or stop.get("native_event_wait_not_yet_observed") is not False
            or stop.get("second_action_id")!=actions[1]["action"]
            or stop.get("session_id")!=r["session_id"]
            or not isinstance(choices,list) or len(choices)!=4
            or choices[-1].get("selected")!="WAIT"
            or choices[-1].get("issued") is not False
            or stop.get("decision")!="STOP_AVOID_OVERSHOOT"
            or stop.get("residual_m",99)>0.20
        ):
            raise ValueError("original L0 did not select real WAIT")
        result.update({
            "fourth_l0_choice":"WAIT",
            "fourth_native_event_seq":stop["fourth_native_event_seq"],
            "third_physical_action_issued":False,
            "second_only_error_m":abs(actions[1]["movement_m"]-1.0),
            "stop_deadband_m":0.20,
        })
    return result


def main() -> int:
    p=argparse.ArgumentParser()
    p.add_argument("--root",type=Path,required=True)
    p.add_argument("--confirm",required=True)
    a=p.parse_args()
    gates=(
        "S49_REAL_SERVER_CI", "S49_FORWARD_MOTOR_DEV_ONLY",
        "S49_SPRINT_MOTOR_DEV_ONLY", "S49_NEXT_EPOCH_DEV_ONLY",
        "S49_L0_OBSERVED_FEEDBACK_DEV_ONLY",
        "S49_L0_RESIDUAL_THIRD_DEV_ONLY",
        "S49_L0_WALK_THIRD_DEV_ONLY",
        "S49_L0_GOAL_WAIT_DEV_ONLY",
    )
    if (
        a.confirm!="S49-L0-WALK-AND-WAIT-TWO-WORLDS-DEV"
        or any(os.environ.get(k)!="1" for k in gates)
        or os.environ.get("NODE_OPTIONS")
        or a.root.exists()
    ):
        raise RuntimeError("original DEV gates and new two-World root required")
    a.root.mkdir(parents=True,mode=0o700)
    cases={}
    for mode in ("WALK","WAIT"):
        directory=a.root/mode
        directory.mkdir(mode=0o700)
        report=directory/"s49_original_report.json"
        log=directory/"original_minecraft_server.log"
        rc=asyncio.run(qualify(
            report,log,dev_forward_motor=True,dev_sprint_motor=True,
            dev_next_epoch="MOVE_AWAY" if mode=="WALK" else "WAIT",
            dev_l0_next_step_m=1.0,
            dev_l0_residual_third_dev=mode=="WALK",
            dev_l0_walk_third_dev=mode=="WALK",
            dev_l0_goal_wait_dev=mode=="WAIT",
        ))
        if not report.is_file():
            raise RuntimeError("missing original S49 terminal report")
        data=json.loads(report.read_text(encoding="utf8"))
        if rc!=0:
            raise RuntimeError(
                f"DEV {mode} original World failed closed: "
                f"{data.get('status')} / {data.get('error')}"
            )
        cases[mode]=review_native(mode,data)
    if cases["WALK"]["session_id"]==cases["WAIT"]["session_id"]:
        raise RuntimeError("replayed original World session")
    result={
        "classification":"S49_L0_OBSERVED_WALK_AND_REAL_WAIT_TWO_WORLD_DEV",
        "cases":cases,
        "original_s14_s15_s16_retained":True,
        "goal_relative_not_absolute":True,
        "paper_node_tick_synced":False,
        "new_action_issuers":0,"new_packet_readers":0,
        "qualification_go":False,"science_go":False,
    }
    (a.root/"l0_walk_wait_two_worlds_dev.json").write_text(
        json.dumps(result,sort_keys=True,indent=2)+"\n",encoding="utf8"
    )
    print("S49_L0_WALK_WAIT_TWO_REAL_WORLDS_DEV_PASS",json.dumps(result,sort_keys=True))
    return 0


if __name__=="__main__":
    raise SystemExit(main())
