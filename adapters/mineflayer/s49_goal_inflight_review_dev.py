"""Two-World verifier: real in-flight L0 stop, not an Action OUTCOME.

The native S15 owner sends correlated probes during active controls and
records actual native CLEAR ACK. S16 returns FAILED with explicit preempt
reason; original ActionSupervisor closes UNKNOWN (not successful movement).
"""
from __future__ import annotations

import argparse
import json
import math
from pathlib import Path


class InflightReviewRejected(ValueError):
    pass


def read_case(root: Path, name: str) -> dict:
    path=root/name/"goal_report.json"
    if path.is_symlink() or not path.is_file() or path.stat().st_size>2_000_000:
        raise InflightReviewRejected("missing original physical report")
    value=json.loads(path.read_text(encoding="utf8"))
    if not isinstance(value,dict):
        raise InflightReviewRejected("invalid original report")
    return value


def review_inflight_two_worlds(root: Path) -> dict:
    if not isinstance(root,Path) or root.is_symlink() or not root.is_dir():
        raise InflightReviewRejected("two isolated physical Worlds required")
    baseline=read_case(root,"BASELINE")
    emergency=read_case(root,"INFLIGHT")
    for r in (baseline,emergency):
        if (
            r.get("status")!="PASS" or r.get("real_world") is not True
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
            or not r.get("session_id")
        ):
            raise InflightReviewRejected("original native owner or world failed")
    if baseline["session_id"]==emergency["session_id"]:
        raise InflightReviewRejected("reused Minecraft session")
    if (
        baseline.get("stage")!="GOAL_REACHED"
        or baseline.get("classification")!="DEV_ONLY_S49_L2_L1_GOAL_AUTONOMOUS_L0"
        or len(baseline.get("native_actions",[]))<2
        or baseline.get("threat_inflight_dev") is not False
        or baseline.get("inflight_l0") is not None
    ):
        raise InflightReviewRejected("baseline goal failed to reach target")
    evidence=emergency.get("inflight_l0")
    actions=emergency.get("native_actions")
    decisions=emergency.get("l0_decisions")
    goal=emergency.get("goal_l2")
    ack=evidence.get("applied_ack") if isinstance(evidence,dict) else None
    clear=evidence.get("clear_ack") if isinstance(evidence,dict) else None
    threat=evidence.get("native_threat") if isinstance(evidence,dict) else None
    if (
        emergency.get("stage")!="INFLIGHT_L0_INTERRUPT"
        or emergency.get("classification")!="DEV_ONLY_S49_L0_INFLIGHT_NATIVE_PREEMPTED"
        or emergency.get("threat_inflight_dev") is not True
        or emergency.get("threat_injection_dev") is not False
        or not isinstance(evidence,dict)
        or not isinstance(actions,list) or len(actions)!=1
        or not isinstance(decisions,list) or len(decisions)!=2
        or decisions[0].get("kind")!="MOVE"
        or decisions[1].get("kind")!="INTERRUPT"
        or not isinstance(goal,dict)
        or evidence.get("goal_id")!=goal.get("goal_id")
        or evidence.get("intent_id")!=goal.get("intent_id")
        or evidence.get("target_x")!=goal.get("target_x")
        or evidence.get("target_z")!=goal.get("target_z")
        or evidence.get("upper_layer_replan_executed") is not False
        or evidence.get("second_action_issued") is not False
        or evidence.get("mid_action_preempted_not_execution_success") is not True
        or evidence.get("native_clear_receipt_applied") is not True
        or evidence.get("S16_consequence_status")!="failed"
        or evidence.get("S16_error")!="DEV_L0_INFLIGHT_NATIVE_THREAT_PREEMPTED"
        or evidence.get("original_action_terminal")!="unknown"
        or actions[0].get("terminal")!="unknown"
        or actions[0].get("S16_status")!="failed"
        or actions[0].get("terminal_not_outcome") is not True
        or evidence.get("source_first_action_id")!=actions[0].get("action_id")
        or evidence.get("native_poll_count",0)<1
        or evidence.get("injected_after_applied") is not True
        or not isinstance(ack,dict) or not isinstance(clear,dict)
        or ack.get("effect")!="set_control" or ack.get("result")!="applied"
        or clear.get("effect")!="clear_controls" or clear.get("result")!="applied"
        or clear.get("seq",0)<=ack.get("seq",-1)
        or not isinstance(threat,dict)
        or threat.get("kind")!="INTERRUPT"
        or threat.get("probe_provenance_source")!="mineflayer"
        or type(threat.get("probe_request_id")) is not str
        or not threat["probe_request_id"]
        or threat.get("probe_seq")!=decisions[-1].get("source_seq")
        or ack.get("seq",-1)>=threat.get("probe_seq",0)
        or threat.get("probe_seq",0)>=clear.get("seq",0)
        or type(threat.get("entity_id")) is not int
        or threat.get("entity_id",0)<1
        or type(threat.get("distance_m")) not in (float,int)
        or not math.isfinite(threat["distance_m"])
        or not 0<threat["distance_m"]<goal["danger_interrupt_m"]
        or not math.isclose(
            threat.get("goal_remaining_m",-1),
            decisions[-1].get("goal_error_m",-2),abs_tol=1e-9,
        )
        or emergency.get("upper_layer_replan_executed") is not False
    ):
        raise InflightReviewRejected("native in-flight preemption sources mismatch")
    summary={
        "classification":"S49_GOAL_REAL_INFLIGHT_L0_CLEAR_DEV",
        "baseline_session":baseline["session_id"],
        "baseline_action_count":len(baseline["native_actions"]),
        "baseline_final_error_m":baseline["final_native_xz"]["euclidean_error_m"],
        "interrupt_session":emergency["session_id"],
        "interrupt_action_count":len(actions),
        "interrupt_action_terminal":"unknown",
        "interrupt_S16_status":"failed",
        "clear_applied_after_real_threat":True,
        "native_threat_id":threat["entity_id"],
        "native_threat_distance_m":threat["distance_m"],
        "native_poll_seq":threat["probe_seq"],
        "native_clear_ack_seq":clear["seq"],
        "inflight_native_poll_count":evidence["native_poll_count"],
        "no_second_action":True,
        "upper_layer_goal_preserved":True,
        "upper_layer_replan_executed":False,
        "world_tick_synchronized":False,
        "new_packet_readers":0,
        "new_action_issuers":0,
        "qualification_go":False,
        "science_go":False,
    }
    (root/"goal_inflight_l0_two_worlds_dev.json").write_text(
        json.dumps(summary,sort_keys=True,indent=2)+"\n",encoding="utf8",
    )
    return summary


def main()->int:
    p=argparse.ArgumentParser()
    p.add_argument("--root",type=Path,required=True)
    args=p.parse_args()
    print("S49_GOAL_REAL_INFLIGHT_NATIVE_PREEMPT_DEV_PASS",
          json.dumps(review_inflight_two_worlds(args.root),sort_keys=True))
    return 0


if __name__=="__main__":
    raise SystemExit(main())
