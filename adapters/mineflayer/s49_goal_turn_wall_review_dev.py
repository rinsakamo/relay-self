"""Original S49 real Minecraft native proof: diagonal LOOK+MOVE, wall fail-close."""
from __future__ import annotations

import argparse
import json
import math
from pathlib import Path


class TurnWallReviewRejected(ValueError):
    pass


def _case(root:Path,arm:str)->dict:
    path=root/arm/"goal_report.json"
    if path.is_symlink() or not path.is_file() or path.stat().st_size>2_000_000:
        raise TurnWallReviewRejected("missing raw World report")
    r=json.loads(path.read_text(encoding="utf8"))
    if (
        not isinstance(r,dict)
        or r.get("status")!="PASS"
        or r.get("real_world") is not True
        or r.get("node_exit")!=0 or r.get("server_exit")!=0
        or r.get("real_model_calls")!=0
        or r.get("learned_L1_attested") is not False
        or r.get("L2_source")!="EXPLICIT_DEV_OPERATOR_NOT_LIVE_L2"
        or r.get("L1_source")!="DETERMINISTIC_DEV_POLICY_NOT_LEARNED"
        or r.get("existing_S49_action_supervisor_reused") is not True
        or r.get("goal_S14_dev_admission") is not True
        or r.get("legacy_zombie_S14_admission_reused") is not False
        or r.get("qualification_go") is not False
        or r.get("science_go") is not False
        or not isinstance(r.get("session_id"),str)
        or not r["session_id"]
        or not isinstance(r.get("native_actions"),list)
        or not isinstance(r.get("native_goal_looks"),list)
    ):
        raise TurnWallReviewRejected("original single-S49 owner source mismatch")
    return r


def review(root:Path)->dict:
    if not isinstance(root,Path) or not root.is_dir() or root.is_symlink():
        raise TurnWallReviewRejected("requires original two-World directory")
    turned=_case(root,"TURN")
    wall=_case(root,"WALL")
    if turned["session_id"]==wall["session_id"]:
        raise TurnWallReviewRejected("World sessions not independent")
    moved=turned["native_actions"]
    looks=turned["native_goal_looks"]
    start=turned["initial_native_xz"]
    goal=turned["goal_l2"]
    last=turned.get("final_native_xz")
    if (
        turned.get("classification")!="DEV_ONLY_S49_L2_L1_GOAL_AUTONOMOUS_L0"
        or turned.get("stage")!="GOAL_REACHED"
        or turned.get("goal_turn_dx_dev")!=1.4
        or turned.get("obstacle_wall_dev") is not False
        or not isinstance(last,dict)
        or not 2<=len(moved)<=6
        or len(looks)!=len(moved)
        or any(x.get("s16_terminal")!="outcome"
               or x.get("s16_status")!="executed" for x in moved)
        or any(x.get("result")!="applied" or x.get("effect")!="look"
               for x in looks)
        or abs(goal["target_x"]-start["x"]-1.4)>1e-9
        or abs(goal["target_z"]-start["z"]-2.6)>1e-9
        or not math.isclose(
            math.hypot(last["x"]-goal["target_x"],last["z"]-goal["target_z"]),
            last["euclidean_error_m"],abs_tol=1e-9,
        )
        or last["euclidean_error_m"]>turned["goal_l1"]["tolerance_m"]
        or moved[0]["native_alignment_to_goal"] is None
        or moved[0]["native_alignment_to_goal"]<0.72
        or abs(moved[0]["native_travel_x"])<0.15
        or any(x.get("kind")!="MOVE"
               for x in turned["l0_decisions"][:len(moved)])
        or turned["l0_decisions"][-1].get("kind")!="REACHED"
    ):
        raise TurnWallReviewRejected("native XZ turn/goal not established")
    wactions=wall["native_actions"]
    wlooks=wall["native_goal_looks"]
    handoff=wall.get("wall_handoff")
    if (
        wall.get("stage")!="NEEDS_REPLAN"
        or wall.get("classification") not in (
            "DEV_ONLY_S49_WALL_MOTOR_UNKNOWN_REPLAN",
            "DEV_ONLY_S49_L0_WALL_REPLAN",
        )
        or wall.get("obstacle_wall_dev") is not True
        or wall.get("goal_turn_dx_dev")!=0.0
        or wall.get("wall_world_stimulus_requested") is not True
        or not isinstance(handoff,dict)
        or handoff.get("no_additional_action_issued") is not True
        or handoff.get("client_obstacle_block_detection_attested") is not False
        or handoff.get("upper_layer_replan_executed") is not False
        or not 1<=len(wactions)<=6
        or len(wlooks)!=len(wactions)
        or any(x.get("effect")!="look" or x.get("result")!="applied"
               for x in wlooks)
        or wactions[0].get("s16_status")!="executed"
        or wactions[0].get("s16_terminal")!="outcome"
        or handoff.get("original_actions")!=len(wactions)
        or not math.isclose(
            handoff.get("retained_target_z",float("nan")),
            wall["goal_l2"]["target_z"],abs_tol=1e-9,
        )
    ):
        raise TurnWallReviewRejected("wall fail-closed original Action source missing")
    if wall["classification"]=="DEV_ONLY_S49_WALL_MOTOR_UNKNOWN_REPLAN":
        if (
            wactions[-1].get("s16_terminal")!="unknown"
            or wactions[-1].get("s16_status")!="undetermined"
            or wactions[-1].get("uncertain_motor_not_success") is not True
        ):
            raise TurnWallReviewRejected("wall unknown falsely treated as success")
    out={
        "classification":"S49_L0_GOAL_REAL_TURN_AND_WALL_FAILCLOSED_DEV",
        "turn_session":turned["session_id"],
        "turn_goal_x":goal["target_x"],
        "turn_goal_z":goal["target_z"],
        "turn_final_x":last["x"],
        "turn_final_z":last["z"],
        "turn_final_euclidean_error_m":last["euclidean_error_m"],
        "turn_L1_tolerance_m":turned["goal_l1"]["tolerance_m"],
        "turn_action_count":len(moved),
        "turn_first_native_alignment":moved[0]["native_alignment_to_goal"],
        "turn_first_native_x_displacement_m":moved[0]["native_travel_x"],
        "wall_session":wall["session_id"],
        "wall_actions":len(wactions),
        "wall_last_terminal":wactions[-1].get("s16_terminal"),
        "wall_handoff_reason":handoff.get("reason"),
        "wall_replan_executed":False,
        "wall_physical_avoidance_proven":False,
        "no_extra_action_issuer":True,
        "no_extra_native_reader":True,
        "qualification_go":False,
        "science_go":False,
    }
    (root/"turn_wall_native_dev.json").write_text(
        json.dumps(out,indent=2,sort_keys=True)+"\n",encoding="utf8",
    )
    return out


def main()->int:
    p=argparse.ArgumentParser()
    p.add_argument("--root",type=Path,required=True)
    a=p.parse_args()
    print("S49_L0_GOAL_REAL_TURN_WALL_DEV_PASS",
          json.dumps(review(a.root),sort_keys=True))
    return 0


if __name__=="__main__":
    raise SystemExit(main())
