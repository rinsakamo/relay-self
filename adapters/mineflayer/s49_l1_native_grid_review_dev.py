"""Independent three actual World audit for native-grid BFS L1 waypoint search."""
from __future__ import annotations

import argparse
import json
import math
from pathlib import Path

from adapters.mineflayer.python_protocol import (
    MineflayerLocalVoxelsDev,
    MineflayerVoxelCellDev,
)
from relay_self.goal_grid_search_dev import choose_grid_route_dev
from relay_self.goal_local_voxel_dev import NativeVoxelPresentDev, VoxelColumnDev
from relay_self.goal_navigation import GoalPurpose, L2GoalProposal
from relay_self.provenance import Provenance


class GridSearchWorldAuditRejected(ValueError):
    pass


def _read(root:Path,arm:str)->dict:
    path=root/arm/"goal_report.json"
    if path.is_symlink() or not path.is_file() or path.stat().st_size>6_000_000:
        raise GridSearchWorldAuditRejected("real native original report missing")
    r=json.loads(path.read_text(encoding="utf8"))
    if (
        r.get("status")!="PASS" or r.get("real_world") is not True
        or r.get("node_exit")!=0 or r.get("server_exit")!=0
        or r.get("real_model_calls")!=0
        or r.get("learned_L1_attested") is not False
        or r.get("existing_S49_action_supervisor_reused") is not True
        or r.get("legacy_zombie_S14_admission_reused") is not False
        or r.get("qualification_go") is not False
        or r.get("science_go") is not False
        or r.get("native_voxel_map_dev") is not True
        or r.get("local_grid_search_dev") is not True
        or r.get("obstacle_wall_dev") is not True
    ):
        raise GridSearchWorldAuditRejected("source World failed to close original S49")
    return r


def _rebuild(r:dict):
    native=r.get("native_local_voxel_observation_dev")
    choice=r.get("native_grid_search_choice_dev")
    actions=r.get("native_actions")
    wall=r.get("wall_handoff")
    if (
        not isinstance(native,dict) or not isinstance(choice,dict)
        or not isinstance(wall,dict)
        or not isinstance(actions,list) or len(actions)!=2
        or actions[0].get("s16_terminal")!="outcome"
        or actions[1].get("s16_terminal")!="unknown"
        or actions[1].get("s16_status")!="undetermined"
        or wall.get("original_actions")!=2
        or wall.get("reason")!="MOTOR_CONSEQUENCE_UNDETERMINED"
        or native.get("source")!="mineflayer"
        or native.get("session_id")!=r.get("session_id")
        or native.get("seq",0)<=wall.get("native_after_seq",0)
        or native.get("request_id","").split("-native-voxels-after-")[-1]
           !=str(wall.get("native_after_seq"))
        or native.get("origin_x")!=r["initial_native_xz"]["x"]
        or native.get("origin_z")!=r["initial_native_xz"]["z"]
        or choice.get("source_seq")!=native.get("seq")
        or choice.get("no_diagonal_edges") is not True
        or choice.get("new_motor_issuer") is not False
        or choice.get("plan_from_current_observation") is not True
    ):
        raise GridSearchWorldAuditRejected("not native blocked S16 + correlated Present")
    msg=MineflayerLocalVoxelsDev(
        session_id=native["session_id"],seq=native["seq"],
        request_id=native["request_id"],
        origin_x=native["origin_x"],origin_z=native["origin_z"],
        player_x=native["player_x"],player_z=native["player_z"],
        player_y=native["player_y"],coverage=native["coverage"],
        x_min=native["x_min"],x_max=native["x_max"],
        z_min=native["z_min"],z_max=native["z_max"],
        unknown_is_not_clear=native["unknown_is_not_clear"],
        cells=tuple(MineflayerVoxelCellDev(
            c["dx"],c["dz"],c["feet"],c["head"],c["floor"],
        ) for c in native["cells"]),
    )
    present=NativeVoxelPresentDev(
        session_id=msg.session_id,native_seq=msg.seq,
        request_id=msg.request_id,origin_x=float(msg.origin_x),
        origin_z=float(msg.origin_z),player_x=float(msg.player_x),
        player_z=float(msg.player_z),player_y=float(msg.player_y),
        coverage=msg.coverage,
        cells=tuple(VoxelColumnDev(
            c.dx,c.dz,c.feet,c.head,c.floor,
        ) for c in msg.cells),provenance=msg.provenance,
    )
    g=r["goal_l2"]
    goal=L2GoalProposal(
        goal_id=g["goal_id"],intent_id=g["intent_id"],
        session_id=g["session_id"],
        target_x=g["target_x"],target_z=g["target_z"],
        purpose=GoalPurpose(g["purpose"]),
        minimum_tolerance_m=g["minimum_tolerance_m"],
        maximum_tolerance_m=g["maximum_tolerance_m"],
        danger_interrupt_m=g["danger_interrupt_m"],
        provenance=Provenance(**g["provenance"]),
    )
    computed=choose_grid_route_dev(
        present,goal,blocked_after_seq=wall["native_after_seq"],
        blocked_action_id=actions[-1]["action_id"],
        provenance=Provenance(
            "s49-goal-dev-operator","l1-native-grid-BFS",
        ),
    )
    if (
        choice.get("status")!=computed.status
        or choice.get("reason")!=computed.reason
        or choice.get("visited_cells")!=computed.visited_cells
        or choice.get("evaluated_columns")!=42
        or choice.get("chosen_cell_path")!=[
            list(pair) for pair in computed.chosen_cell_path
        ]
    ):
        raise GridSearchWorldAuditRejected("recorded path not reproducible from source")
    return computed


def audit_native_grid_three_worlds_dev(root:Path)->dict:
    if root.is_symlink() or not root.is_dir():
        raise GridSearchWorldAuditRejected("three independently started Worlds required")
    names=("LEFT_BLOCKED","RIGHT_BLOCKED","BOTH_BLOCKED")
    reports={n:_read(root,n) for n in names}
    if len({v["session_id"] for v in reports.values()})!=3:
        raise GridSearchWorldAuditRejected("reused original session")
    output={}
    for name in names:
        r=reports[name]
        result=_rebuild(r)
        if (
            r.get("left_lane_block_dev") is not (name!="RIGHT_BLOCKED")
            or r.get("right_lane_block_dev") is not (name!="LEFT_BLOCKED")
        ):
            raise GridSearchWorldAuditRejected("mislabeled original World geometry")
        if name=="BOTH_BLOCKED":
            if (
                result.status!="DEFER" or result.plan is not None
                or r.get("classification")!="DEV_ONLY_S49_L1_GRID_NO_ROUTE_DEFER"
                or r.get("stage")!="L1_GRID_DEFER"
                or r.get("detour") is not None
            ):
                raise GridSearchWorldAuditRejected("no-route World issued an Action")
            output[name]={"status":"DEFER","actions_after_unknown":0,
                          "visited_cells":result.visited_cells}
            continue
        route=r.get("detour")
        stages=route.get("stages") if isinstance(route,dict) else None
        if (
            result.status!="SELECTED"
            or result.plan is None
            or len(result.chosen_cell_path)<=4
            or not isinstance(stages,list)
            or len(stages)!=len(result.plan.stages)
            or not 2<=len(stages)<=12
            or route.get("reached_final_goal") is not True
            or route.get("obstacle_block_perception_attested") is not True
            or route.get("extra_action_issuer") is not False
            or route.get("extra_native_reader") is not False
            or r.get("classification")!="DEV_ONLY_S49_L1_NATIVE_GRID_GOAL_REACHED"
        ):
            raise GridSearchWorldAuditRejected("native BFS route not physically followed")
        action_ids=[v["action_id"] for v in r["native_actions"]]
        for index,stage in enumerate(stages):
            expected=result.plan.stages[index]
            if (
                stage["index"]!=index
                or stage["result"]!="REACHED"
                or not math.isclose(stage["target_x"],expected.target_x,abs_tol=1e-8)
                or not math.isclose(stage["target_z"],expected.target_z,abs_tol=1e-8)
                or stage["reached_error_m"]>stage["tolerance_m"]
                or not stage["actions"]
                or len(stage["look_acks"])!=len(stage["actions"])
                or stage["decisions"][-1]["kind"]!="REACHED"
                or any(
                    action["terminal"]!="outcome"
                    or action["S16_status"]!="executed"
                    or action["after_seq"]<=action["before_seq"]
                    for action in stage["actions"]
                )
            ):
                raise GridSearchWorldAuditRejected("no original S16 settled stage")
            action_ids.extend(a["action_id"] for a in stage["actions"])
        final=stages[-1]
        if (
            len(action_ids)!=len(set(action_ids))
            or final["target_x"]!=r["goal_l2"]["target_x"]
            or final["target_z"]!=r["goal_l2"]["target_z"]
            or not math.isclose(
                math.hypot(
                    route["final_parent_goal_x"]-final["target_x"],
                    route["final_parent_goal_z"]-final["target_z"],
                ),route["final_parent_goal_error_m"],abs_tol=1e-8,
            )
            or route["final_parent_goal_error_m"]>final["tolerance_m"]
        ):
            raise GridSearchWorldAuditRejected("not physically at original Goal")
        output[name]={
            "status":"REACHED",
            "grid_path":[list(node) for node in result.chosen_cell_path],
            "waypoints":len(stages),
            "native_actions":route["total_route_native_actions"],
            "final_error_m":route["final_parent_goal_error_m"],
            "tolerance_m":final["tolerance_m"],
        }
    review={
        "classification":"S49_L1_NATIVE_GRID_BFS_PHYSICAL_DEV",
        "sessions":{n:r["session_id"] for n,r in reports.items()},
        "results":output,
        "grid_coverage":"42_XZ_columns_3_Y_cells_loaded_cache_only",
        "routing":"4_CONNECTED_NO_DIAGONAL_BFS",
        "floor_support":"observed_full_collision_floor_only",
        "unknown_not_traversable":True,
        "new_action_issuer_count":0,"new_native_reader_count":0,
        "general_navigation_proven":False,"learned_L1_proven":False,
        "qualification_go":False,"science_go":False,
    }
    (root/"native_grid_bfs_three_world_review.json").write_text(
        json.dumps(review,indent=2,sort_keys=True)+"\n",encoding="utf8",
    )
    return review


def main()->int:
    p=argparse.ArgumentParser()
    p.add_argument("--root",type=Path,required=True)
    opts=p.parse_args()
    print("S49_NATIVE_LOCAL_GRID_SEARCH_REAL_DEV_PASS",
          json.dumps(audit_native_grid_three_worlds_dev(opts.root),sort_keys=True))
    return 0


if __name__=="__main__":
    raise SystemExit(main())
