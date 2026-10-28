"""Source audit: physical right/left dynamic voxel-template choice and DEFER.

Three separate actual Minecraft Worlds; the 7x6x3 grid itself must come
from the original Mineflayer client, not the server operator stimulus.
"""
from __future__ import annotations

import argparse
import json
import math
from pathlib import Path

from adapters.mineflayer.python_protocol import (
    MineflayerLocalVoxelsDev,
    MineflayerVoxelCellDev,
)
from relay_self.goal_local_voxel_dev import (
    NativeVoxelPresentDev,
    VoxelColumnDev,
    choose_voxel_waypoint_dev,
)
from relay_self.goal_navigation import GoalPurpose, L2GoalProposal
from relay_self.provenance import Provenance


class LocalVoxelAuditRejected(ValueError):
    pass


def _report(root:Path, arm:str)->dict:
    path=root/arm/"goal_report.json"
    if path.is_symlink() or not path.is_file() or path.stat().st_size>6_000_000:
        raise LocalVoxelAuditRejected("raw Minecraft World report missing")
    value=json.loads(path.read_text(encoding="utf8"))
    if (
        not isinstance(value,dict) or value.get("status")!="PASS"
        or value.get("real_world") is not True
        or value.get("node_exit")!=0
        or value.get("server_exit")!=0
        or value.get("real_model_calls")!=0
        or value.get("learned_L1_attested") is not False
        or value.get("existing_S49_action_supervisor_reused") is not True
        or value.get("legacy_zombie_S14_admission_reused") is not False
        or value.get("qualification_go") is not False
        or value.get("science_go") is not False
        or value.get("native_voxel_map_dev") is not True
        or value.get("obstacle_wall_dev") is not True
        or value.get("detour_after_wall_dev") is not True
    ):
        raise LocalVoxelAuditRejected("invalid physical original World source")
    return value


def _decision_from_raw(report:dict):
    raw=report.get("native_local_voxel_observation_dev")
    choice=report.get("native_local_voxel_choice_dev")
    original=report.get("native_actions")
    if (
        not isinstance(raw,dict) or not isinstance(choice,dict)
        or not isinstance(original,list) or len(original)!=2
        or original[0].get("s16_terminal")!="outcome"
        or original[1].get("s16_terminal")!="unknown"
        or original[1].get("s16_status")!="undetermined"
        or report.get("wall_handoff",{}).get("original_actions")!=2
        or raw.get("source")!="mineflayer"
        or raw.get("session_id")!=report.get("session_id")
        or raw.get("coverage")!="mineflayer_loaded_cache_fixed_7x6x3"
        or raw.get("unknown_is_not_clear") is not True
        or (raw.get("x_min"),raw.get("x_max"),raw.get("z_min"),raw.get("z_max"))
           !=(-3,3,0,5)
        or raw.get("seq",0)<=report["wall_handoff"]["native_after_seq"]
        or raw.get("request_id","").split("-native-voxels-after-")[-1]
           !=str(report["wall_handoff"]["native_after_seq"])
        or raw.get("origin_x")!=report["initial_native_xz"]["x"]
        or raw.get("origin_z")!=report["initial_native_xz"]["z"]
        or choice.get("source_seq")!=raw.get("seq")
        or choice.get("sampled_voxel_columns")!=42
        or choice.get("plan_from_current_observation") is not True
        or choice.get("action_authorized_by_map") is not False
    ):
        raise LocalVoxelAuditRejected("voxel Present not bound to fresh blocked S16")
    packet=MineflayerLocalVoxelsDev(
        session_id=raw["session_id"],seq=raw["seq"],
        request_id=raw["request_id"],
        origin_x=raw["origin_x"],origin_z=raw["origin_z"],
        player_y=raw["player_y"],
        player_x=raw["player_x"],player_z=raw["player_z"],
        coverage=raw["coverage"],
        x_min=raw["x_min"],x_max=raw["x_max"],
        z_min=raw["z_min"],z_max=raw["z_max"],
        cells=tuple(
            MineflayerVoxelCellDev(
                c["dx"],c["dz"],c["feet"],c["head"],c["floor"],
            ) for c in raw["cells"]
        ),
        unknown_is_not_clear=raw["unknown_is_not_clear"],
    )
    present=NativeVoxelPresentDev(
        session_id=packet.session_id,native_seq=packet.seq,
        request_id=packet.request_id,
        origin_x=float(packet.origin_x),origin_z=float(packet.origin_z),
        player_y=float(packet.player_y),
        player_x=float(packet.player_x),player_z=float(packet.player_z),
        coverage=packet.coverage,
        cells=tuple(VoxelColumnDev(
            c.dx,c.dz,c.feet,c.head,c.floor,
        ) for c in packet.cells),
        provenance=packet.provenance,
    )
    original_goal=report["goal_l2"]
    goal=L2GoalProposal(
        goal_id=original_goal["goal_id"],
        intent_id=original_goal["intent_id"],
        session_id=original_goal["session_id"],
        target_x=original_goal["target_x"],
        target_z=original_goal["target_z"],
        purpose=GoalPurpose(original_goal["purpose"]),
        minimum_tolerance_m=original_goal["minimum_tolerance_m"],
        maximum_tolerance_m=original_goal["maximum_tolerance_m"],
        danger_interrupt_m=original_goal["danger_interrupt_m"],
        provenance=Provenance(**original_goal["provenance"]),
    )
    reconstructed=choose_voxel_waypoint_dev(
        present,goal,
        blocked_after_seq=report["wall_handoff"]["native_after_seq"],
        blocked_action_id=original[1]["action_id"],
        provenance=Provenance("s49-goal-dev-operator",
                              "l1-observed-local-voxel-waypoints"),
    )
    if (
        reconstructed.status!=choice.get("status")
        or reconstructed.reason!=choice.get("reason")
        or reconstructed.selected_side!=choice.get("selected_side")
        or reconstructed.left_state!=choice.get("left_state")
        or reconstructed.right_state!=choice.get("right_state")
    ):
        raise LocalVoxelAuditRejected("local voxel choice is not reproducible")
    return reconstructed


def audit_three_worlds_dev(root:Path)->dict:
    if not isinstance(root,Path) or root.is_symlink() or not root.is_dir():
        raise LocalVoxelAuditRejected("three independent World reports required")
    arms=("LEFT_BLOCKED","RIGHT_BLOCKED","BOTH_OPEN")
    reports={arm:_report(root,arm) for arm in arms}
    if len({r["session_id"] for r in reports.values()})!=3:
        raise LocalVoxelAuditRejected("source sessions not independent")
    summary={}
    for arm in arms:
        record=reports[arm]
        choice=_decision_from_raw(record)
        should_side={"LEFT_BLOCKED":"RIGHT","RIGHT_BLOCKED":"LEFT",
                     "BOTH_OPEN":None}[arm]
        if (
            choice.selected_side!=should_side
            or record.get("left_lane_block_dev") is not (arm=="LEFT_BLOCKED")
            or record.get("right_lane_block_dev") is not (arm=="RIGHT_BLOCKED")
        ):
            raise LocalVoxelAuditRejected("operator stimulus mismatched actual Present")
        if should_side is None:
            if (
                choice.status!="DEFER"
                or choice.plan is not None
                or record.get("stage")!="L1_VOXEL_DEFER"
                or record.get("classification")!="DEV_ONLY_S49_L1_VOXEL_DEFER"
                or record.get("detour") is not None
            ):
                raise LocalVoxelAuditRejected("uncertain map issued new physical Action")
            summary[arm]={"status":"DEFER","actions_after_blocked_s16":0,
                          "left_state":choice.left_state,
                          "right_state":choice.right_state}
            continue
        route=record.get("detour")
        stages=route.get("stages") if isinstance(route,dict) else None
        if (
            choice.status!="SELECTED"
            or choice.reason!="NATIVE_VOXEL_TEMPLATE_SELECTED"
            or choice.plan is None
            or record.get("classification")!="DEV_ONLY_S49_L1_VOXEL_GOAL_REACHED"
            or record.get("stage")!="L1_DETOUR_ORIGINAL_GOAL_REACHED"
            or not isinstance(stages,list) or len(stages)!=3
            or route.get("reached_final_goal") is not True
            or route.get("extra_action_issuer") is not False
            or route.get("extra_native_reader") is not False
            or route.get("learned_l1_attested") is not False
        ):
            raise LocalVoxelAuditRejected("native waypoint goal not attained")
        action_ids=[x["action_id"] for x in record["native_actions"]]
        for i,stage in enumerate(stages):
            if (
                stage["index"]!=i or stage["result"]!="REACHED"
                or not math.isclose(
                    stage["target_x"],choice.plan.stages[i].target_x,
                    abs_tol=1e-8,
                )
                or not math.isclose(
                    stage["target_z"],choice.plan.stages[i].target_z,
                    abs_tol=1e-8,
                )
                or stage["reached_error_m"]>stage["tolerance_m"]
                or not stage["actions"]
                or len(stage["look_acks"])!=len(stage["actions"])
                or any(action["S16_status"]!="executed"
                       or action["terminal"]!="outcome"
                       or action["after_seq"]<=action["before_seq"]
                       for action in stage["actions"])
            ):
                raise LocalVoxelAuditRejected("no actual original S16 waypoint arrival")
            action_ids.extend(action["action_id"] for action in stage["actions"])
        if (
            len(action_ids)!=len(set(action_ids))
            or stages[-1]["target_x"]!=record["goal_l2"]["target_x"]
            or stages[-1]["target_z"]!=record["goal_l2"]["target_z"]
            or not math.isclose(
                math.hypot(
                    route["final_parent_goal_x"]-record["goal_l2"]["target_x"],
                    route["final_parent_goal_z"]-record["goal_l2"]["target_z"],
                ),route["final_parent_goal_error_m"],abs_tol=1e-8,
            )
            or route["final_parent_goal_error_m"]>stages[-1]["tolerance_m"]
        ):
            raise LocalVoxelAuditRejected("parent L2 goal falsely completed")
        summary[arm]={
            "status":"REACHED","selected_side":choice.selected_side,
            "left_state":choice.left_state,"right_state":choice.right_state,
            "native_route_actions":route["total_route_native_actions"],
            "final_error_m":route["final_parent_goal_error_m"],
            "tolerance_m":stages[-1]["tolerance_m"],
        }
    out={
        "classification":"S49_L1_REAL_VOXEL_LOCAL_WAYPOINT_DEV",
        "sessions":{arm:r["session_id"] for arm,r in reports.items()},
        "results":summary,
        "grid":"7x6_columns_3_heights_cache_only",
        "origin":"SelfWorld_OBSERVED_DEV_EXTENSION",
        "native_packet_readers_added":0,
        "action_issuers_added":0,
        "general_pathfinding_proven":False,
        "learned_L1_proven":False,
        "qualification_go":False,"science_go":False,
    }
    (root/"local_voxel_waypoint_three_world_review.json").write_text(
        json.dumps(out,sort_keys=True,indent=2)+"\n",encoding="utf8",
    )
    return out


def main()->int:
    p=argparse.ArgumentParser()
    p.add_argument("--root",type=Path,required=True)
    a=p.parse_args()
    print("S49_L1_LOCAL_VOXEL_THREE_WORLD_DEV_PASS",
          json.dumps(audit_three_worlds_dev(a.root),sort_keys=True))
    return 0


if __name__=="__main__":
    raise SystemExit(main())
