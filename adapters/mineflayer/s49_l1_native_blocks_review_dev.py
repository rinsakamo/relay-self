"""Independent original World proof: OBSERVED cells resolve remembered conflict.

Native response comes from the original Mineflayer bot's loaded block cache,
AFTER a newly blocked S16. UNKNOWN is not passable. Goal movement still uses
only the inherited original S49 S15/S16 Action owner.
"""
from __future__ import annotations

import argparse
import json
import math
from pathlib import Path

from adapters.mineflayer.s49_goal_l1_detour_review_dev import review
from adapters.mineflayer.s49_l1_selfworld_memory_dev import (
    recall_from_selfworld_dev,
)
from adapters.mineflayer.python_protocol import (
    MineflayerRouteBlocksDev,
    MineflayerRouteLaneDev,
)
from relay_self.goal_memory_choice_dev import L1RecallStatusDev
from relay_self.goal_navigation import GoalPurpose, L2GoalProposal
from relay_self.provenance import Provenance


class NativeBlockRouteReviewRejected(ValueError):
    pass


def _read(root:Path,name:str)->dict:
    path=root/name/"goal_report.json"
    if path.is_symlink() or not path.is_file() or path.stat().st_size>4_000_000:
        raise NativeBlockRouteReviewRejected("original native World source absent")
    result=json.loads(path.read_text(encoding="utf8"))
    if (
        not isinstance(result,dict)
        or result.get("status")!="PASS"
        or result.get("real_world") is not True
        or result.get("node_exit")!=0
        or result.get("server_exit")!=0
        or result.get("real_model_calls")!=0
    ):
        raise NativeBlockRouteReviewRejected("original source not closed")
    return result


def review_native_block_resolution_dev(root:Path)->dict:
    if root.is_symlink() or not root.is_dir():
        raise NativeBlockRouteReviewRejected("requires four independent Worlds")
    a=review(root)
    b=review(root/"SECOND_AUDIT")
    stop=_read(root,"WALL_STOP")
    right=_read(root,"DETOUR")
    left=_read(root,"DETOUR_B")
    target=_read(root,"TRANSFER")
    if (
        len({r["session_id"] for r in (stop,right,left,target)})!=4
        or a["detour_session"]!=right["session_id"]
        or b["detour_session"]!=left["session_id"]
        or a["control_session"]!=stop["session_id"]
        or b["control_session"]!=stop["session_id"]
        or left.get("detour_left_dev") is not True
        or right.get("detour_left_dev") is not False
        or left["detour"]["stages"][0]["target_x"]
           -left["initial_native_xz"]["x"]!=-2.5
        or right["detour"]["stages"][0]["target_x"]
           -right["initial_native_xz"]["x"]!=2.5
    ):
        raise NativeBlockRouteReviewRejected("not two opposing successful native routes")
    packet=target.get("native_route_blocks_observation_dev")
    chosen=target.get("selfworld_memory_selection_dev")
    actual=target.get("detour")
    actions=target.get("native_actions")
    if (
        target.get("classification")!="DEV_ONLY_S49_L1_SELFWORLD_MEMORY_GOAL_REACHED"
        or target.get("stage")!="L1_DETOUR_ORIGINAL_GOAL_REACHED"
        or target.get("native_route_present_dev") is not True
        or target.get("left_lane_block_dev") is not True
        or target.get("left_lane_block_world_stimulus_requested") is not True
        or target.get("obstacle_wall_dev") is not True
        or target.get("existing_S49_action_supervisor_reused") is not True
        or target.get("qualification_go") is not False
        or target.get("science_go") is not False
        or target.get("learned_L1_attested") is not False
        or not isinstance(packet,dict)
        or packet.get("session_id")!=target["session_id"]
        or packet.get("source")!="mineflayer"
        or packet.get("coverage")!="loaded_client_cache_only"
        or packet.get("samples_per_lane")!=3
        or packet.get("unknown_is_not_clear") is not True
        or not isinstance(chosen,dict)
        or chosen.get("status")!="SELECTED"
        or chosen.get("reason")!="NATIVE_PRESENT_RESOLVED_CONFLICT"
        or chosen.get("matching_successes")!=2
        or chosen.get("matching_failures")!=1
        or chosen.get("selected_memory_id")!="l1-route-success-a"
        or chosen.get("selfworld_origin")!="REMEMBERED"
        or chosen.get("native_block_geometry_observed") is not True
        or chosen.get("native_block_coverage_attested")
           !="loaded_client_cache_only"
        or chosen.get("native_block_present_seq")!=packet["seq"]
        or chosen.get("physical_action_authorized_by_memory") is not False
        or not isinstance(actions,list) or len(actions)!=2
        or actions[0].get("s16_terminal")!="outcome"
        or actions[1].get("s16_terminal")!="unknown"
        or actions[1].get("s16_status")!="undetermined"
        or not isinstance(actual,dict) or actual.get("reached_final_goal") is not True
    ):
        raise NativeBlockRouteReviewRejected("native Present not bound to exact S16 decision")
    lanes=packet.get("lanes")
    if (
        not isinstance(lanes,list) or len(lanes)!=2
        or lanes[0].get("side")!="LEFT"
        or lanes[1].get("side")!="RIGHT"
        or len(lanes[0].get("states",[]))!=3
        or lanes[1].get("states")!=["CLEAR","CLEAR","CLEAR"]
        or "BLOCKED" not in lanes[0]["states"]
        or type(packet.get("seq")) is not int
        or packet["seq"]<=target["wall_handoff"]["native_after_seq"]
        or packet["request_id"].split("-native-route-after-")[-1]
           !=str(target["wall_handoff"]["native_after_seq"])
        or packet["origin_x"]!=target["initial_native_xz"]["x"]
        or packet["origin_z"]!=target["initial_native_xz"]["z"]
    ):
        raise NativeBlockRouteReviewRejected("client cache cannot assert right lane safe")
    source=MineflayerRouteBlocksDev(
        session_id=packet["session_id"],seq=packet["seq"],
        request_id=packet["request_id"],
        origin_x=packet["origin_x"],origin_z=packet["origin_z"],
        player_y=packet["player_y"],
        coverage=packet["coverage"],
        samples_per_lane=packet["samples_per_lane"],
        unknown_is_not_clear=packet["unknown_is_not_clear"],
        lanes=tuple(
            MineflayerRouteLaneDev(x["side"],tuple(x["states"]))
            for x in lanes
        ),
    )
    goal=target["goal_l2"]
    parent=L2GoalProposal(
        goal_id=goal["goal_id"],intent_id=goal["intent_id"],
        session_id=goal["session_id"],target_x=goal["target_x"],
        target_z=goal["target_z"],purpose=GoalPurpose(goal["purpose"]),
        minimum_tolerance_m=goal["minimum_tolerance_m"],
        maximum_tolerance_m=goal["maximum_tolerance_m"],
        danger_interrupt_m=goal["danger_interrupt_m"],
        provenance=Provenance(**goal["provenance"]),
    )
    replay=recall_from_selfworld_dev(
        root/"persistent_self_memory_dev.json",
        root/"selfworld_route_catalog_dev.json",
        parent,
        start_x=float(target["initial_native_xz"]["x"]),
        start_z=float(target["initial_native_xz"]["z"]),
        blocked_action_id=actions[-1]["action_id"],
        blocked_s16_seq=target["wall_handoff"]["native_after_seq"],
        blocked_reason=target["wall_handoff"]["reason"],
        blocked_terminal=actions[-1]["s16_terminal"],
        blocked_consequence=actions[-1]["s16_status"],
        native_route_blocks_dev=source,
    )
    if (
        replay.status is not L1RecallStatusDev.SELECTED
        or replay.reason!=chosen["reason"]
        or replay.selected_memory_id!="l1-route-success-a"
        or replay.plan is None
        or replay.plan.stages[0].target_x-parent.target_x!=2.5
        or not math.isclose(
            math.hypot(
                actual["final_parent_goal_x"]-parent.target_x,
                actual["final_parent_goal_z"]-parent.target_z,
            ),actual["final_parent_goal_error_m"],abs_tol=1e-8,
        )
        or actual["final_parent_goal_error_m"]
           >actual["stages"][-1]["tolerance_m"]
        or not all(s["result"]=="REACHED" and s["actions"]
                   for s in actual["stages"])
    ):
        raise NativeBlockRouteReviewRejected("recalled native GOAL did not physically reach")
    result={
        "classification":"S49_L1_NATIVE_BLOCK_PRESENT_RESOLVES_ROUTE_CONFLICT_DEV",
        "sessions":[r["session_id"] for r in (stop,right,left,target)],
        "native_probe_seq":source.seq,
        "native_probe_request_id":source.request_id,
        "native_source":"mineflayer_loaded_client_cache_only",
        "left_states":list(source.lanes[0].states),
        "right_states":list(source.lanes[1].states),
        "selected_route":"RIGHT",
        "selected_memory":"l1-route-success-a",
        "source_successes":2,"blocked_failure_sources":1,
        "transfer_actions":actual["total_route_native_actions"],
        "final_parent_error_m":actual["final_parent_goal_error_m"],
        "final_parent_tolerance_m":actual["stages"][-1]["tolerance_m"],
        "other_lane_blocked_observed":True,
        "all_right_sampled_columns_clear":True,
        "unloaded_means_unknown":True,
        "real_l2_replan_attested":False,"learned_policy_attested":False,
        "new_action_issuers":0,"new_native_packet_readers":0,
        "qualification_go":False,"science_go":False,
    }
    (root/"native_blocks_route_resolution_dev.json").write_text(
        json.dumps(result,indent=2,sort_keys=True)+"\n",encoding="utf8",
    )
    return result


def main()->int:
    p=argparse.ArgumentParser()
    p.add_argument("--root",required=True,type=Path)
    args=p.parse_args()
    print("S49_L1_NATIVE_BLOCK_ROUTE_RESOLUTION_DEV_PASS",
          json.dumps(review_native_block_resolution_dev(args.root),sort_keys=True))
    return 0


if __name__=="__main__":
    raise SystemExit(main())
