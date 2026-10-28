"""Independent native Minecraft DEV comparison: episodic L1 reuse.

First World route is explicitly supplied and source-audited against an
independent wall-only World; third World selects from saved experience ONLY.
No future data enters the recall path.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
from pathlib import Path

from adapters.mineflayer.s49_goal_l1_detour_review_dev import review
from adapters.mineflayer.s49_l1_experience_export_dev import load_episode_dev


class EpisodeTransferRejected(ValueError):
    pass


def verify_episode_transfer_dev(root:Path)->dict:
    if not isinstance(root,Path) or root.is_symlink() or not root.is_dir():
        raise EpisodeTransferRejected("three original Minecraft Worlds required")
    prior=review(root)
    trained=root/"DETOUR"/"goal_report.json"
    memory=root/"l1_route_episode_dev.json"
    episode,envelope=load_episode_dev(memory,trained)
    transferred_file=root/"TRANSFER"/"goal_report.json"
    if (
        transferred_file.is_symlink() or not transferred_file.is_file()
        or transferred_file.stat().st_size>4_000_000
    ):
        raise EpisodeTransferRejected("missing source of real transfer")
    t=json.loads(transferred_file.read_text(encoding="utf8"))
    m=t.get("experience_selection_dev")
    route=t.get("detour")
    if (
        t.get("status")!="PASS" or t.get("real_world") is not True
        or t.get("node_exit")!=0 or t.get("server_exit")!=0
        or t.get("qualification_go") is not False
        or t.get("science_go") is not False
        or t.get("real_model_calls")!=0
        or t.get("learned_L1_attested") is not False
        or t.get("existing_S49_action_supervisor_reused") is not True
        or t.get("legacy_zombie_S14_admission_reused") is not False
        or t.get("classification")
           !="DEV_ONLY_S49_L1_EPISODE_REUSED_PARENT_GOAL_REACHED"
        or t.get("stage")!="L1_DETOUR_ORIGINAL_GOAL_REACHED"
        or t.get("detour_after_wall_dev") is not True
        or t.get("experience_requested_dev") is not True
        or t.get("obstacle_wall_dev") is not True
        or t.get("wall_world_stimulus_requested") is not True
        or not isinstance(route,dict) or not isinstance(m,dict)
        or m.get("source_session_id")!=episode.source_session_id
        or m.get("source_report_sha256")!=envelope["source_report_sha256"]
        or m.get("source_native_actions")!=episode.source_native_actions
        or m.get("source_goal_id")!=episode.source_goal_id
        or m.get("new_session_id")!=t.get("session_id")
        or m.get("new_session_id")==m.get("source_session_id")
        or m.get("new_session_id")==prior["control_session"]
        or m.get("only_real_prior_episode") is not True
        or m.get("learned_general_policy") is not False
        or m.get("wall_block_sensed") is not False
        or m.get("selected_route_offsets")!=[
            list(s) for s in episode.stages
        ]
        or route.get("reached_final_goal") is not True
        or route.get("learned_l1_attested") is not False
        or route.get("real_l2_replan_attested") is not False
        or route.get("obstacle_block_perception_attested") is not False
        or route.get("extra_action_issuer") is not False
        or route.get("extra_native_reader") is not False
    ):
        raise EpisodeTransferRejected("source-attested route transfer not established")
    original=t["goal_l2"]
    origin=t["initial_native_xz"]
    stages=route.get("stages")
    actions=t.get("native_actions")
    if (
        not isinstance(stages,list) or len(stages)!=3
        or not isinstance(actions,list) or len(actions)!=2
        or actions[-1].get("s16_terminal")!="unknown"
        or actions[-1].get("s16_status")!="undetermined"
        or t["wall_handoff"]["reason"]!="MOTOR_CONSEQUENCE_UNDETERMINED"
        or route.get("original_wall_action_id")!=actions[-1]["action_id"]
        or route.get("original_wall_S16_after_seq")
           !=t["wall_handoff"]["native_after_seq"]
        or route["l1_detour_plan"]["source_action_id"]!=actions[-1]["action_id"]
        or route["l1_detour_plan"]["source_s16_seq"]
           !=t["wall_handoff"]["native_after_seq"]
        or route["l1_detour_plan"]["revision"]!=1
        or route["l1_detour_plan"]["route_id"]!=f"recalled-{original['goal_id']}"
        or not math.isclose(
            original["target_x"]-origin["x"],
            episode.original_goal_offset_x,abs_tol=1e-8,
        )
        or not math.isclose(
            original["target_z"]-origin["z"],
            episode.original_goal_offset_z,abs_tol=1e-8,
        )
    ):
        raise EpisodeTransferRejected("no new World original native wall UNKNOWN")
    for i,stage in enumerate(stages):
        stage_id,offset_x,offset_z=episode.stages[i]
        if (
            stage["index"]!=i
            or stage["stage_id"]!=stage_id
            or stage["result"]!="REACHED"
            or stage["decisions"][-1]["kind"]!="REACHED"
            or not math.isclose(
                stage["target_x"],origin["x"]+offset_x,abs_tol=1e-8,
            )
            or not math.isclose(
                stage["target_z"],origin["z"]+offset_z,abs_tol=1e-8,
            )
            or not stage["actions"]
            or len(stage["look_acks"])!=len(stage["actions"])
            or stage["reached_error_m"]>stage["tolerance_m"]
            or any(
                a["terminal"]!="outcome" or a["S16_status"]!="executed"
                or a["native_displacement_m"]<0.05
                or a["after_seq"]<=a["before_seq"]
                for a in stage["actions"]
            )
        ):
            raise EpisodeTransferRejected("native waypoint did not use recalled offsets")
    ids=[a["action_id"] for a in actions]+[
        a["action_id"] for s in stages for a in s["actions"]
    ]
    if (
        len(set(ids))!=len(ids)
        or stages[-1]["target_x"]!=original["target_x"]
        or stages[-1]["target_z"]!=original["target_z"]
        or route["total_route_native_actions"]!=sum(
            len(s["actions"]) for s in stages
        )
        or route["final_parent_goal_error_m"]>stages[-1]["tolerance_m"]
        or not math.isclose(
            math.hypot(
                route["final_parent_goal_x"]-original["target_x"],
                route["final_parent_goal_z"]-original["target_z"],
            ),route["final_parent_goal_error_m"],abs_tol=1e-8,
        )
        or m.get("new_world_goal_x")!=original["target_x"]
        or m.get("new_world_goal_z")!=original["target_z"]
    ):
        raise EpisodeTransferRejected("source/target mismatch or Action replay")
    summary={
        "classification":"S49_L1_CROSS_WORLD_EPISODIC_WAYPOINT_REUSE_DEV",
        "source_session":episode.source_session_id,
        "transfer_session":t["session_id"],
        "control_session":prior["control_session"],
        "source_report_sha256":hashlib.sha256(
            trained.read_bytes()
        ).hexdigest(),
        "native_source_route_actions":episode.source_native_actions,
        "native_transfer_route_actions":route["total_route_native_actions"],
        "transfer_original_parent_error_m":route["final_parent_goal_error_m"],
        "transfer_original_parent_tolerance_m":stages[-1]["tolerance_m"],
        "transfer_stage_errors_m":[s["reached_error_m"] for s in stages],
        "transfer_stage_offsets":[list(s) for s in episode.stages],
        "same_original_s49_issuer":True,
        "new_packet_readers":0,
        "learned_policy_attested":False,
        "actual_block_perception_attested":False,
        "new_l2_plan_attested":False,
        "qualification_go":False,
        "science_go":False,
    }
    (root/"native_l1_episode_transfer_dev.json").write_text(
        json.dumps(summary,indent=2,sort_keys=True)+"\n",encoding="utf8",
    )
    return summary


def main()->int:
    p=argparse.ArgumentParser()
    p.add_argument("--root",type=Path,required=True)
    args=p.parse_args()
    print("S49_L1_CROSS_WORLD_EPISODIC_REUSE_DEV_PASS",
          json.dumps(verify_episode_transfer_dev(args.root),sort_keys=True))
    return 0


if __name__=="__main__":
    raise SystemExit(main())
