"""Original physical native source audit for wall stop vs same-owner L1 detour."""
from __future__ import annotations

import argparse
import json
import math
from pathlib import Path


class DetourEvidenceRejected(ValueError):
    pass


def _read(root:Path,name:str)->dict:
    path=root/name/"goal_report.json"
    if path.is_symlink() or not path.is_file() or path.stat().st_size>4_000_000:
        raise DetourEvidenceRejected("original World report missing")
    value=json.loads(path.read_text(encoding="utf8"))
    if not isinstance(value,dict):
        raise DetourEvidenceRejected("invalid native evidence")
    for key in ("session_id","goal_l2","goal_l1","native_actions"):
        if key not in value:
            raise DetourEvidenceRejected("missing session or goal provenance")
    if (
        value.get("status")!="PASS" or value.get("real_world") is not True
        or value.get("node_exit")!=0 or value.get("server_exit")!=0
        or value.get("learned_L1_attested") is not False
        or value.get("real_model_calls")!=0
        or value.get("legacy_zombie_S14_admission_reused") is not False
        or value.get("existing_S49_action_supervisor_reused") is not True
        or value.get("qualification_go") is not False
        or value.get("science_go") is not False
    ):
        raise DetourEvidenceRejected("no actual original S49 physical source")
    return value


def review(root:Path)->dict:
    if root.is_symlink() or not root.is_dir():
        raise DetourEvidenceRejected("requires two independent original Worlds")
    control=_read(root,"WALL_STOP")
    case=_read(root,"DETOUR")
    if not control["session_id"] or control["session_id"]==case["session_id"]:
        raise DetourEvidenceRejected("two distinct original Minecraft sessions required")
    if (
        control.get("classification")!="DEV_ONLY_S49_WALL_MOTOR_UNKNOWN_REPLAN"
        or control.get("stage")!="NEEDS_REPLAN"
        or control.get("obstacle_wall_dev") is not True
        or control.get("detour_after_wall_dev") is not False
        or control.get("wall_handoff",{}).get("reason")
           !="MOTOR_CONSEQUENCE_UNDETERMINED"
        or control["native_actions"][-1].get("s16_terminal")!="unknown"
    ):
        raise DetourEvidenceRejected("wall-only control no longer fails closed")
    route=case.get("detour")
    if (
        case.get("classification")!="DEV_ONLY_S49_L1_DETOUR_PARENT_GOAL_REACHED"
        or case.get("stage")!="L1_DETOUR_ORIGINAL_GOAL_REACHED"
        or case.get("obstacle_wall_dev") is not True
        or case.get("detour_after_wall_dev") is not True
        or case.get("wall_handoff",{}).get("reason")
           !="MOTOR_CONSEQUENCE_UNDETERMINED"
        or not isinstance(route,dict)
        or route.get("reached_final_goal") is not True
        or route.get("learned_l1_attested") is not False
        or route.get("real_l2_replan_attested") is not False
        or route.get("obstacle_block_perception_attested") is not False
        or route.get("extra_action_issuer") is not False
        or route.get("extra_native_reader") is not False
    ):
        raise DetourEvidenceRejected("false learned L1, block perception, or goal success")
    base_actions=case["native_actions"]
    plan=route.get("l1_detour_plan")
    stages=route.get("stages")
    if (
        not isinstance(plan,dict)
        or plan.get("revision")!=1
        or plan.get("reason")!="NATIVE_MOTOR_UNDETERMINED_NO_BLOCK_SENSOR"
        or plan.get("parent",{}).get("goal_id")!=case["goal_l2"]["goal_id"]
        or plan.get("parent",{}).get("target_x")!=case["goal_l2"]["target_x"]
        or plan.get("parent",{}).get("target_z")!=case["goal_l2"]["target_z"]
        or not isinstance(stages,list) or len(stages)!=3
        or plan.get("source_action_id")!=base_actions[-1]["action_id"]
        or plan.get("source_s16_seq")!=case["wall_handoff"]["native_after_seq"]
        or base_actions[-1].get("s16_terminal")!="unknown"
        or base_actions[-1].get("s16_status")!="undetermined"
        or any(
            s.get("index")!=i or s.get("result")!="REACHED"
            or not isinstance(s.get("decisions"),list)
            or s["decisions"][-1].get("kind")!="REACHED"
            or not isinstance(s.get("actions"),list) or not s["actions"]
            or len(s.get("look_acks",[]))!=len(s["actions"])
            or s.get("reached_error_m",float("inf"))>s.get("tolerance_m",0)
            or not all(a.get("terminal")=="outcome"
                       and a.get("S16_status")=="executed"
                       and a.get("after_seq",0)>a.get("before_seq",0)
                       and a.get("native_displacement_m",0)>=0.05
                       for a in s["actions"])
            for i,s in enumerate(stages)
        )
    ):
        raise DetourEvidenceRejected("L1 route lacks original native S16 stage lineage")
    if (
        stages[-1]["target_x"]!=case["goal_l2"]["target_x"]
        or stages[-1]["target_z"]!=case["goal_l2"]["target_z"]
        or not math.isclose(
            math.hypot(
                stages[-1]["reached_x"]-case["goal_l2"]["target_x"],
                stages[-1]["reached_z"]-case["goal_l2"]["target_z"],
            ),route["final_parent_goal_error_m"],abs_tol=1e-9,
        )
        or route["total_route_native_actions"]!=sum(
            len(s["actions"]) for s in stages
        )
        or case["wall_handoff"]["original_actions"]!=len(base_actions)
    ):
        raise DetourEvidenceRejected("final L2 original target not physically reached")
    unique_ids=[a["action_id"] for a in base_actions]+[
        a["action_id"] for stage in stages for a in stage["actions"]
    ]
    if len(set(unique_ids))!=len(unique_ids):
        raise DetourEvidenceRejected("reissued previous physical Action ID")
    out={
        "classification":"S49_L1_NATIVE_DETOUR_ORIGINAL_L2_GOAL_DEV",
        "control_session":control["session_id"],
        "detour_session":case["session_id"],
        "blocked_action_id":base_actions[-1]["action_id"],
        "blocked_action_terminal":base_actions[-1]["s16_terminal"],
        "l1_revision":1,
        "stages":[
            {"id":s["stage_id"],"actions":len(s["actions"]),
             "goal_x":s["target_x"],"goal_z":s["target_z"],
             "final_error_m":s["reached_error_m"],"tolerance_m":s["tolerance_m"]}
            for s in stages
        ],
        "original_L2_final_goal_error_m":route["final_parent_goal_error_m"],
        "original_L2_goal_reached":True,
        "no_reused_action_ids":True,
        "real_l1_learning_proven":False,
        "block_sensing_proven":False,
        "qualification_go":False,
        "science_go":False,
    }
    (root/"l1_original_goal_detour_dev.json").write_text(
        json.dumps(out,indent=2,sort_keys=True)+"\n",encoding="utf8",
    )
    return out


def main()->int:
    p=argparse.ArgumentParser()
    p.add_argument("--root",required=True,type=Path)
    a=p.parse_args()
    print("S49_L1_NATIVE_WAYPOINT_DETOUR_DEV_PASS",
          json.dumps(review(a.root),sort_keys=True))
    return 0


if __name__=="__main__":
    raise SystemExit(main())
