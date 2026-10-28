"""Independent four-World audit: governed Memory -> SelfWorld -> real L0 route."""
from __future__ import annotations

import argparse
import hashlib
import json
import math
from pathlib import Path

from adapters.mineflayer.s49_goal_l1_detour_review_dev import review
from adapters.mineflayer.s49_l1_selfworld_memory_dev import (
    recall_from_selfworld_dev,
)
from relay_self.goal_memory_choice_dev import L1RecallStatusDev
from relay_self.goal_navigation import GoalPurpose, L2GoalProposal
from relay_self.provenance import Provenance


class SelfWorldMemoryReviewRejected(ValueError):
    pass


def _report(path:Path)->dict:
    if path.is_symlink() or not path.is_file() or path.stat().st_size>4_000_000:
        raise SelfWorldMemoryReviewRejected("missing original World")
    value=json.loads(path.read_text(encoding="utf8"))
    if not isinstance(value,dict) or value.get("node_exit")!=0 or value.get("server_exit")!=0:
        raise SelfWorldMemoryReviewRejected("failed unverified original World")
    return value


def review_four_worlds_dev(root:Path)->dict:
    if root.is_symlink() or not root.is_dir():
        raise SelfWorldMemoryReviewRejected("four original independent Worlds required")
    source_a=review(root)
    source_b=review(root/"SECOND_AUDIT")
    control=_report(root/"WALL_STOP"/"goal_report.json")
    a=_report(root/"DETOUR"/"goal_report.json")
    b=_report(root/"DETOUR_B"/"goal_report.json")
    transfer=_report(root/"TRANSFER"/"goal_report.json")
    sessions=(control["session_id"],a["session_id"],b["session_id"],transfer["session_id"])
    if (
        len(set(sessions))!=4
        or source_a["control_session"]!=source_b["control_session"]
        or source_a["detour_session"]!=a["session_id"]
        or source_b["detour_session"]!=b["session_id"]
        or not all(r.get("real_world") is True and r.get("status")=="PASS"
                   for r in (control,a,b,transfer))
        or transfer.get("classification")!="DEV_ONLY_S49_L1_SELFWORLD_MEMORY_GOAL_REACHED"
        or transfer.get("stage")!="L1_DETOUR_ORIGINAL_GOAL_REACHED"
        or transfer.get("existing_S49_action_supervisor_reused") is not True
        or transfer.get("legacy_zombie_S14_admission_reused") is not False
        or transfer.get("real_model_calls")!=0
        or transfer.get("learned_L1_attested") is not False
        or transfer.get("qualification_go") is not False
        or transfer.get("science_go") is not False
    ):
        raise SelfWorldMemoryReviewRejected("four World identity or source unsupported")
    chosen=transfer.get("selfworld_memory_selection_dev")
    result=transfer.get("detour")
    goal=transfer["goal_l2"]
    origin=transfer["initial_native_xz"]
    wall=transfer["wall_handoff"]
    actions=transfer["native_actions"]
    if (
        not isinstance(chosen,dict) or not isinstance(result,dict)
        or chosen.get("status")!=L1RecallStatusDev.SELECTED.value
        or chosen.get("reason")!="MATCHED_REMEMBERED_PATTERN"
        or chosen.get("matching_successes")!=2
        or chosen.get("matching_failures")!=1
        or chosen.get("selfworld_origin")!="REMEMBERED"
        or chosen.get("persistent_owner")!="PersistentCognition"
        or chosen.get("native_block_geometry_observed") is not False
        or chosen.get("physical_action_authorized_by_memory") is not False
        or chosen.get("selected_memory_id") not in (
            "l1-route-success-a","l1-route-success-b"
        )
        or len(chosen.get("source_ids",[]))!=3
        or not isinstance(actions,list) or len(actions)!=2
        or actions[-1].get("s16_terminal")!="unknown"
        or actions[-1].get("s16_status")!="undetermined"
        or wall.get("reason")!="MOTOR_CONSEQUENCE_UNDETERMINED"
        or chosen.get("current_world_source_event")!=wall.get("native_after_seq")
        or result.get("reached_final_goal") is not True
        or result.get("learned_l1_attested") is not False
        or result.get("real_l2_replan_attested") is not False
        or result.get("obstacle_block_perception_attested") is not False
        or result.get("extra_action_issuer") is not False
        or result.get("extra_native_reader") is not False
        or result.get("original_wall_action_id")!=actions[-1]["action_id"]
        or result.get("original_wall_S16_after_seq")!=wall["native_after_seq"]
    ):
        raise SelfWorldMemoryReviewRejected("native memory selection absent or forged")
    g=L2GoalProposal(
        goal_id=goal["goal_id"],intent_id=goal["intent_id"],
        session_id=goal["session_id"],target_x=goal["target_x"],
        target_z=goal["target_z"],purpose=GoalPurpose(goal["purpose"]),
        minimum_tolerance_m=goal["minimum_tolerance_m"],
        maximum_tolerance_m=goal["maximum_tolerance_m"],
        danger_interrupt_m=goal["danger_interrupt_m"],
        provenance=Provenance(**goal["provenance"]),
    )
    choice=recall_from_selfworld_dev(
        root/"persistent_self_memory_dev.json",
        root/"selfworld_route_catalog_dev.json",g,
        start_x=float(origin["x"]),start_z=float(origin["z"]),
        blocked_action_id=actions[-1]["action_id"],
        blocked_s16_seq=wall["native_after_seq"],
        blocked_reason=wall["reason"],
        blocked_terminal=actions[-1]["s16_terminal"],
        blocked_consequence=actions[-1]["s16_status"],
    )
    if (
        choice.status is not L1RecallStatusDev.SELECTED
        or choice.selected_memory_id!=chosen["selected_memory_id"]
        or choice.plan is None
        or result["l1_detour_plan"]["route_id"]!=choice.plan.route_id
        or result["l1_detour_plan"]["source_action_id"]!=choice.plan.source_action_id
        or result["l1_detour_plan"]["source_s16_seq"]!=choice.plan.source_s16_seq
    ):
        raise SelfWorldMemoryReviewRejected("recorded Memory decision not reproducible")
    stages=result["stages"]
    ids=[a["action_id"] for a in actions]
    for i,stage in enumerate(stages):
        actual=choice.plan.stages[i]
        if (
            stage["index"]!=i or stage["stage_id"]!=actual.stage_id
            or stage["result"]!="REACHED"
            or not math.isclose(stage["target_x"],actual.target_x,abs_tol=1e-8)
            or not math.isclose(stage["target_z"],actual.target_z,abs_tol=1e-8)
            or stage["reached_error_m"]>stage["tolerance_m"]
            or not stage["actions"]
            or len(stage["look_acks"])!=len(stage["actions"])
            or stage["decisions"][-1]["kind"]!="REACHED"
            or any(a["terminal"]!="outcome" or a["S16_status"]!="executed"
                   or a["after_seq"]<=a["before_seq"]
                   for a in stage["actions"])
        ):
            raise SelfWorldMemoryReviewRejected("selected stage not real original S16")
        ids.extend(a["action_id"] for a in stage["actions"])
    if (
        len(ids)!=len(set(ids))
        or stages[-1]["target_x"]!=goal["target_x"]
        or stages[-1]["target_z"]!=goal["target_z"]
        or not math.isclose(
            math.hypot(result["final_parent_goal_x"]-goal["target_x"],
                       result["final_parent_goal_z"]-goal["target_z"]),
            result["final_parent_goal_error_m"],abs_tol=1e-8,
        )
        or result["final_parent_goal_error_m"]>stages[-1]["tolerance_m"]
    ):
        raise SelfWorldMemoryReviewRejected("original L2 destination not reached")
    summary={
        "classification":"S49_L1_SELFWORLD_MULTI_EPISODE_DEV",
        "source_sessions":[a["session_id"],b["session_id"]],
        "blocked_failure_session":control["session_id"],
        "transfer_session":transfer["session_id"],
        "selected_memory_id":chosen["selected_memory_id"],
        "matching_successes":2,"matching_failures":1,
        "transfer_actions":result["total_route_native_actions"],
        "transfer_stage_errors_m":[s["reached_error_m"] for s in stages],
        "transfer_parent_error_m":result["final_parent_goal_error_m"],
        "transfer_parent_tolerance_m":stages[-1]["tolerance_m"],
        "memory_snapshot_sha256":hashlib.sha256(
            (root/"persistent_self_memory_dev.json").read_bytes()
        ).hexdigest(),
        "selfworld_origin":"REMEMBERED",
        "memory_owner":"PersistentCognition",
        "learned_general_policy":False,
        "actual_block_geometry_observed":False,
        "new_action_issuers":0,"new_packet_readers":0,
        "qualification_go":False,"science_go":False,
    }
    (root/"l1_selfworld_multi_episode_dev.json").write_text(
        json.dumps(summary,sort_keys=True,indent=2)+"\n",encoding="utf8",
    )
    return summary


def main()->int:
    p=argparse.ArgumentParser()
    p.add_argument("--root",type=Path,required=True)
    a=p.parse_args()
    print("S49_L1_SELFWORLD_MULTI_EPISODE_DEV_PASS",
          json.dumps(review_four_worlds_dev(a.root),sort_keys=True))
    return 0


if __name__=="__main__":
    raise SystemExit(main())
