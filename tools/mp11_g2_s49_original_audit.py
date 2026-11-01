"""Independent readback of MP11 G2 original S49 one-session three Action DEV.

No source data invented by the audit. This does not qualify L2 experiments,
Paper S50 windows, or standalone Minecraft world UUID (vanilla lacks one).
"""
from __future__ import annotations

import json
from pathlib import Path


class MP11G2Rejected(ValueError):
    """No three source-linked original S49/S15/S16 closures in one session."""


def audit_original(report: dict, *, require_completed_cleanup: bool = True) -> dict:
    if not isinstance(report, dict):
        raise MP11G2Rejected("original report required")
    sid=report.get("session_id")
    mp=report.get("mp11_g2")
    actions=report.get("actual_native_actions")
    decisions=report.get("decisions")
    traces=report.get("source_pair_trace")
    if (not isinstance(sid,str) or not sid
            or not isinstance(mp,dict) or not isinstance(actions,list)
            or not isinstance(decisions,list) or not isinstance(traces,list)
            or mp.get("action_budget") != 3
            or mp.get("l2_provider_calls") != 0
            or mp.get("l2_selected_trials") != 0
            or mp.get("l10_s10_s11_admissions") != 0
            or mp.get("paper_s50_windows") != 0
            or len(actions) != 3 or len(mp.get("typed_s16_actions",[])) != 3
            or len(decisions) != 4 or len(traces) != 4):
        raise MP11G2Rejected("no bounded three Action original native source")
    if ([d.get("selected") for d in decisions] !=
            ["WAIT","MOVE_AWAY","MOVE_AWAY","MOVE_AWAY"]
            or [d.get("issued") for d in decisions] != [False,True,True,True]
            or len({d.get("entity_id") for d in decisions}) != 4):
        raise MP11G2Rejected("not an independently chosen original L0 sequence")
    typed=mp["typed_s16_actions"]
    previous_seq=-1
    seen_ids=set()
    movements=[]
    for i,(a,closed) in enumerate(zip(actions,typed)):
        evid=a.get("execution_evidence")
        if not isinstance(evid,dict):
            raise MP11G2Rejected("missing decoded genuine S15 receipts")
        action=a.get("action")
        if (not isinstance(action,str) or not action.startswith("s49-native-move-")
                or action in seen_ids or a.get("source") != sid
                or a.get("terminal") != "outcome"
                or closed.get("action_id") != action
                or closed.get("session_id") != sid
                or closed.get("outcome") != "outcome"
                or closed.get("source_status") != "executed"
                or closed.get("new_action_issuers") != 0
                or closed.get("before_after_source_original") is not True
                or evid.get("action_id") != action
                or evid.get("session_id") != sid
                or evid.get("action_ref") != "MOVE_BACKWARD"
                or evid.get("status") != "executed"
                or evid.get("learning_feedback_qualified") is not False
                or evid.get("goal_success_attested") is not False):
            raise MP11G2Rejected("Action outcome or original typed closure not linked")
        before=evid.get("before_observation")
        after=evid.get("after_observation")
        dispatch=evid.get("dispatch_receipt")
        clear=evid.get("cleanup_receipt")
        if any(not isinstance(x,dict) for x in (before,after,dispatch,clear)):
            raise MP11G2Rejected("missing exact before/after/dispatch/clear receipts")
        b_seq,issued_seq,clear_seq,after_seq=(
            before.get("seq"),dispatch.get("seq"),
            clear.get("seq"),after.get("seq"),
        )
        if (not all(type(v) is int and v >= 0
                    for v in (b_seq,issued_seq,clear_seq,after_seq))
                or not b_seq < issued_seq < clear_seq < after_seq
                or any(x.get("session_id") != sid
                       for x in (before,after,dispatch,clear))
                or dispatch.get("action_id") != action
                or dispatch.get("result") != "applied"
                or clear.get("action_id") != action+"-s15-clear"
                or clear.get("effect") != "clear_controls"
                or clear.get("result") != "applied"
                or not isinstance(closed.get("native_ref"),str)
                or closed.get("native_seq") != after_seq
                or closed["native_ref"] != (
                    f"native-probe:{sid}:{after_seq}:{after.get('request_id')}"
                )
                or b_seq <= previous_seq):
            raise MP11G2Rejected("Action S15 sequence not strictly ordered and cleared")
        if (a.get("event_seq") != decisions[i+1].get("event_seq")
                or a.get("probe_seq") != decisions[i+1].get("probe_seq")
                or not isinstance(a.get("movement_m"),(int,float))
                or a["movement_m"] < .05):
            raise MP11G2Rejected("native L0 event not linked to S16 movement")
        previous_seq=after_seq
        seen_ids.add(action)
        movements.append(a["movement_m"])
    if require_completed_cleanup and (
        report.get("status") != "PASS"
        or report.get("classification")
        != "DEV_ONLY_MP11_G2_ONE_WORLD_THREE_TYPED_S16_ACTIONS"
        or report.get("node_exit") != 0
        or report.get("server_exit") != 0
        or report.get("learning_in_world") is not False
        or report.get("real_model_calls") != 0
    ):
        raise MP11G2Rejected("qualified finished original Java/Node session absent")
    return {
        "classification": "MP11_G2_DEV_SINGLE_SERVER_ONE_SESSION_THREE_ORIGINAL_S16",
        "session_id":sid,
        "original_s49_actions":3,
        "original_s15_clear_receipts":3,
        "original_typed_s16_outcomes":3,
        "source_native_after_seq": [r["native_seq"] for r in typed],
        "action_ids":[r["action_id"] for r in typed],
        "movement_m":movements,
        "single_server_process_session": True,
        "minecraft_world_uuid":"NOT_AVAILABLE_FROM_VANILLA_SOURCE",
        "paper_s50_windows":0,
        "real_l2_provider_calls":0,
        "autonomous_l2_experiment_selection":False,
        "s10_s11_l10_admissions":0,
        "qualification":"DEV_ONLY",
        "science":"NOT_RUN",
    }


def main() -> int:
    import argparse
    p=argparse.ArgumentParser()
    p.add_argument("--report",type=Path,required=True)
    p.add_argument("--output",type=Path,required=True)
    args=p.parse_args()
    result=audit_original(json.loads(args.report.read_text()))
    with args.output.open("x") as out:
        out.write(json.dumps(result,sort_keys=True,indent=2)+"\n")
    print("MP11_G2_SOURCE_READBACK="+json.dumps(result,sort_keys=True))
    return 0


if __name__=="__main__":
    raise SystemExit(main())
