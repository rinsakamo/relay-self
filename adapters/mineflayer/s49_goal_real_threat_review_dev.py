"""Source audit for two independent original S49 goal-runner DEV Worlds.

Only a genuine Mineflayer native zombie probe can attest interruption.
A World command is a stimulus, never evidence of entity detection.
"""
from __future__ import annotations

import argparse
import json
import math
from pathlib import Path


class GoalThreatReviewRejected(ValueError):
    pass


def _read(path:Path)->dict:
    if (path.is_symlink() or not path.is_file()
        or path.stat().st_size>2_000_000):
        raise GoalThreatReviewRejected("absent or unsafe real World report")
    value=json.loads(path.read_text(encoding="utf8"))
    if not isinstance(value,dict):
        raise GoalThreatReviewRejected("untyped World report")
    return value


def review_world_reports(root:Path)->dict:
    if not isinstance(root,Path) or root.is_symlink() or not root.is_dir():
        raise GoalThreatReviewRejected("must read two actual isolated Worlds")
    base=_read(root/"BASELINE"/"goal_report.json")
    interrupted=_read(root/"INTERRUPT"/"goal_report.json")
    for r in (base,interrupted):
        if (
            r.get("status")!="PASS"
            or r.get("real_world") is not True
            or r.get("node_exit")!=0 or r.get("server_exit")!=0
            or r.get("real_model_calls")!=0
            or r.get("learned_L1_attested") is not False
            or r.get("L2_source")!="EXPLICIT_DEV_OPERATOR_NOT_LIVE_L2"
            or r.get("L1_source")!="DETERMINISTIC_DEV_POLICY_NOT_LEARNED"
            or r.get("existing_S49_action_supervisor_reused") is not True
            or r.get("goal_S14_dev_admission") is not True
            or r.get("legacy_zombie_S14_admission_reused") is not False
            or r.get("upper_layer_replan_executed") is not False
            or r.get("qualification_go") is not False
            or r.get("science_go") is not False
            or type(r.get("session_id")) is not str
            or not r["session_id"]
            or not isinstance(r.get("native_actions"),list)
            or not isinstance(r.get("l0_decisions"),list)
            or any(a.get("s16_terminal")!="outcome"
                   or a.get("s16_status")!="executed"
                   for a in r["native_actions"])
        ):
            raise GoalThreatReviewRejected("unverified original native S16")
    if base["session_id"]==interrupted["session_id"]:
        raise GoalThreatReviewRejected("same simulated World reused")
    if (
        base.get("classification")!="DEV_ONLY_S49_L2_L1_GOAL_AUTONOMOUS_L0"
        or base.get("stage")!="GOAL_REACHED"
        or len(base["native_actions"])<2
        or base["l0_decisions"][-1].get("kind")!="REACHED"
        or base.get("threat_injection_dev") is not False
        or base.get("goal_handoff") is not None
    ):
        raise GoalThreatReviewRejected("baseline no longer reaches goal")
    h=interrupted.get("goal_handoff")
    p=interrupted.get("goal_l2")
    action=interrupted["native_actions"]
    decisions=interrupted["l0_decisions"]
    injected=interrupted.get("hazard_injection_after_first_s16")
    if (
        interrupted.get("classification")
          !="DEV_ONLY_S49_NATIVE_GOAL_REAL_THREAT_INTERRUPTED"
        or interrupted.get("stage")!="INTERRUPT"
        or interrupted.get("threat_injection_dev") is not True
        or not isinstance(h,dict) or not isinstance(p,dict)
        or not isinstance(injected,dict)
        or injected.get("world_command_requested") is not True
        or injected.get("native_confirmed") is not True
        or len(action)!=1 or len(decisions)!=2
        or injected.get("after_terminal_action_id")!=action[0].get("action_id")
        or action[0].get("s16_terminal")!="outcome"
        or decisions[0].get("kind")!="MOVE"
        or decisions[1].get("kind")!="INTERRUPT"
        or h.get("kind")!="INTERRUPT"
        or h.get("reason")!="OBSERVED_NEAR_THREAT"
        or h.get("goal_id")!=p.get("goal_id")
        or h.get("intent_id")!=p.get("intent_id")
        or h.get("session_id")!=interrupted["session_id"]
        or h.get("target_x")!=p.get("target_x")
        or h.get("target_z")!=p.get("target_z")
        or h.get("native_actions_before_handoff")!=1
        or h.get("additional_action_issued_after_interrupt") is not False
        or h.get("owner_open_actions")!=0
        or h.get("L0_goal_following_closed") is not True
        or h.get("original_goal_retained_for_upper_layer") is not True
        or h.get("upper_layer_replan_executed") is not False
        or h.get("probe_provenance_source")!="mineflayer"
        or h.get("probe_seq")!=decisions[-1].get("source_seq")
        or type(h.get("probe_request_id")) is not str
        or not h["probe_request_id"]
        or type(h.get("threat_entity_id")) is not int
        or h["threat_entity_id"]<=0
        or type(h.get("threat_distance_m")) not in (int,float)
        or not math.isfinite(h["threat_distance_m"])
        or not 0 < h["threat_distance_m"] < p["danger_interrupt_m"]
        or not math.isclose(
            h.get("remaining_goal_error_m",-1),
            decisions[-1].get("goal_error_m",-2),abs_tol=1e-9,
        )
    ):
        raise GoalThreatReviewRejected("physical interruption not source-backed")
    result={
        "classification":"S49_GOAL_REAL_WORLD_S16_THREAT_HANDOFF_TWO_WORLDS_DEV",
        "baseline_session_id":base["session_id"],
        "interrupt_session_id":interrupted["session_id"],
        "baseline_actions":len(base["native_actions"]),
        "baseline_final_error_m":base["final_native_xz"]["euclidean_error_m"],
        "interrupted_actions":len(action),
        "interrupted_after_s16_action_id":action[0]["action_id"],
        "interrupted_threat_id":h["threat_entity_id"],
        "interrupted_threat_distance_m":h["threat_distance_m"],
        "interrupted_goal_error_m":h["remaining_goal_error_m"],
        "native_probe_seq":h["probe_seq"],
        "no_new_action_after_interrupt":True,
        "no_synthetic_threat_observation":True,
        "no_upper_level_replan_execution":True,
        "goal_metadata_preserved":True,
        "original_action_supervisor_reused":True,
        "qualification_go":False,
        "science_go":False,
    }
    (root/"goal_real_threat_handoff_two_worlds_dev.json").write_text(
        json.dumps(result,sort_keys=True,indent=2)+"\n",encoding="utf8",
    )
    return result


def main()->int:
    parser=argparse.ArgumentParser()
    parser.add_argument("--root",type=Path,required=True)
    args=parser.parse_args()
    print("S49_GOAL_REAL_THREAT_INTERRUPT_DEV_PASS",
          json.dumps(review_world_reports(args.root),sort_keys=True))
    return 0


if __name__=="__main__":
    raise SystemExit(main())
