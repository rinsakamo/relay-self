"""Original real World conflict proof: different valid routes -> DEFER/no MOVE.

The evidence is four separately started Minecraft sessions. Both route
templates have original native S16 success; the new World has its own blocked
S16. No source document alone may substitute for a real World action.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

from adapters.mineflayer.s49_goal_l1_detour_review_dev import review
from adapters.mineflayer.s49_l1_selfworld_memory_dev import recall_from_selfworld_dev
from relay_self.goal_memory_choice_dev import L1RecallStatusDev
from relay_self.goal_navigation import GoalPurpose, L2GoalProposal
from relay_self.provenance import Provenance


class ConflictingRealRoutesRejected(ValueError):
    pass


def _read(path:Path)->dict:
    if path.is_symlink() or not path.is_file() or path.stat().st_size>4_000_000:
        raise ConflictingRealRoutesRejected("missing original session")
    v=json.loads(path.read_text(encoding="utf8"))
    if not isinstance(v,dict):
        raise ConflictingRealRoutesRejected("malformed native report")
    if (
        v.get("status")!="PASS" or v.get("real_world") is not True
        or v.get("node_exit")!=0 or v.get("server_exit")!=0
        or v.get("real_model_calls")!=0
        or v.get("learned_L1_attested") is not False
        or v.get("qualification_go") is not False
        or v.get("science_go") is not False
    ):
        raise ConflictingRealRoutesRejected("unverified original World")
    return v


def audit_conflicting_real_routes_dev(root:Path)->dict:
    if not isinstance(root,Path) or root.is_symlink() or not root.is_dir():
        raise ConflictingRealRoutesRejected("four independent Minecraft Worlds required")
    prior=review(root)
    second=review(root/"SECOND_AUDIT")
    stop=_read(root/"WALL_STOP"/"goal_report.json")
    right=_read(root/"DETOUR"/"goal_report.json")
    left=_read(root/"DETOUR_B"/"goal_report.json")
    rejected=_read(root/"TRANSFER"/"goal_report.json")
    ids=[s["session_id"] for s in (stop,right,left,rejected)]
    if (
        len(set(ids))!=4
        or second["control_session"]!=stop["session_id"]
        or prior["control_session"]!=stop["session_id"]
        or prior["detour_session"]!=right["session_id"]
        or second["detour_session"]!=left["session_id"]
        or right.get("detour_left_dev") is not False
        or left.get("detour_left_dev") is not True
        or rejected.get("detour_left_dev") is not False
    ):
        raise ConflictingRealRoutesRejected("no independent source/route signs")
    ga=right["detour"]["stages"]
    gb=left["detour"]["stages"]
    if (
        len(ga)!=3 or len(gb)!=3
        or ga[0]["target_x"]-right["initial_native_xz"]["x"]!=2.5
        or gb[0]["target_x"]-left["initial_native_xz"]["x"]!=-2.5
        or any(s["result"]!="REACHED" or not s["actions"]
               or s["reached_error_m"]>s["tolerance_m"] for s in (*ga,*gb))
        or not right["detour"]["reached_final_goal"]
        or not left["detour"]["reached_final_goal"]
    ):
        raise ConflictingRealRoutesRejected("must conflict between TWO successful paths")
    selection=rejected.get("selfworld_memory_selection_dev")
    actions=rejected.get("native_actions")
    if (
        rejected.get("stage")!="L1_MEMORY_DEFER"
        or rejected.get("classification")!="DEV_ONLY_S49_L1_SELFWORLD_MEMORY_DEFER"
        or rejected.get("detour_after_wall_dev") is not True
        or rejected.get("obstacle_wall_dev") is not True
        or rejected.get("existing_S49_action_supervisor_reused") is not True
        or rejected.get("legacy_zombie_S14_admission_reused") is not False
        or rejected.get("detour") is not None
        or not isinstance(selection,dict)
        or selection.get("status")!="DEFER"
        or selection.get("reason")!="CONFLICTING_RECALLED_ROUTES"
        or selection.get("matching_successes")!=2
        or selection.get("matching_failures")!=1
        or selection.get("selected_memory_id") is not None
        or selection.get("selfworld_origin")!="REMEMBERED"
        or selection.get("physical_action_authorized_by_memory") is not False
        or selection.get("native_block_geometry_observed") is not False
        or not isinstance(actions,list) or len(actions)!=2
        or actions[0].get("s16_terminal")!="outcome"
        or actions[1].get("s16_terminal")!="unknown"
        or actions[1].get("s16_status")!="undetermined"
        or rejected["wall_handoff"]["original_actions"]!=2
        or rejected["wall_handoff"]["native_after_seq"]!=selection[
            "current_world_source_event"
        ]
    ):
        raise ConflictingRealRoutesRejected("not an actual blocked S16 followed by safe DEFER")
    goal=rejected["goal_l2"]
    first=rejected["initial_native_xz"]
    g=L2GoalProposal(
        goal_id=goal["goal_id"],intent_id=goal["intent_id"],
        session_id=goal["session_id"],target_x=goal["target_x"],
        target_z=goal["target_z"],purpose=GoalPurpose(goal["purpose"]),
        minimum_tolerance_m=goal["minimum_tolerance_m"],
        maximum_tolerance_m=goal["maximum_tolerance_m"],
        danger_interrupt_m=goal["danger_interrupt_m"],
        provenance=Provenance(**goal["provenance"]),
    )
    again=recall_from_selfworld_dev(
        root/"persistent_self_memory_dev.json",
        root/"selfworld_route_catalog_dev.json",
        g,start_x=float(first["x"]),start_z=float(first["z"]),
        blocked_action_id=actions[-1]["action_id"],
        blocked_s16_seq=rejected["wall_handoff"]["native_after_seq"],
        blocked_reason=rejected["wall_handoff"]["reason"],
        blocked_terminal=actions[-1]["s16_terminal"],
        blocked_consequence=actions[-1]["s16_status"],
    )
    if (
        again.status is not L1RecallStatusDev.DEFER
        or again.reason!=selection["reason"]
        or again.matching_successes!=2
        or again.matching_failures!=1
        or again.plan is not None
        or again.selected_memory_id is not None
    ):
        raise ConflictingRealRoutesRejected("offline memory decision disagrees with World")
    result={
        "classification":"S49_L1_TWO_NATIVE_CONFLICTING_ROUTES_DEFER_DEV",
        "control_session":stop["session_id"],
        "right_route_session":right["session_id"],
        "left_route_session":left["session_id"],
        "conflict_world_session":rejected["session_id"],
        "right_route_actions":right["detour"]["total_route_native_actions"],
        "left_route_actions":left["detour"]["total_route_native_actions"],
        "right_source_error_m":right["detour"]["final_parent_goal_error_m"],
        "left_source_error_m":left["detour"]["final_parent_goal_error_m"],
        "source_right_stage_offset_x_m":2.5,
        "source_left_stage_offset_x_m":-2.5,
        "matching_successes":2,"matching_failures":1,
        "decision":"DEFER",
        "reason":"CONFLICTING_RECALLED_ROUTES",
        "motor_actions_before_defer":2,
        "motor_actions_after_defer":0,
        "owner":"PersistentCognition",
        "world_read_origin":"REMEMBERED",
        "native_block_geometry_observed":False,
        "learned_policy_attested":False,
        "new_packet_readers":0,
        "new_action_issuers":0,
        "snapshot_sha256":hashlib.sha256(
            (root/"persistent_self_memory_dev.json").read_bytes()
        ).hexdigest(),
        "qualification_go":False,
        "science_go":False,
    }
    (root/"l1_native_conflicting_routes_defer_dev.json").write_text(
        json.dumps(result,indent=2,sort_keys=True)+"\n",encoding="utf8",
    )
    return result


def main()->int:
    p=argparse.ArgumentParser()
    p.add_argument("--root",type=Path,required=True)
    a=p.parse_args()
    print("S49_L1_NATIVE_CONFLICT_DEFER_DEV_PASS",
          json.dumps(audit_conflicting_real_routes_dev(a.root),sort_keys=True))
    return 0


if __name__=="__main__":
    raise SystemExit(main())
