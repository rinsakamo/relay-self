"""MP11 G3 independent postrun readback of original Paper and native reports.

Paper+W3 report are separate source forms, not independent Minecraft TCP
sniffing. This auditor cannot establish causality, autonomy, or L2 learning.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

from adapters.mineflayer.self_body_s50_l2_mp11_paper_audit import (
    MP11PaperRejected,
    audit_multi_trial_paper,
)
from tools.mp11_g2_s49_original_audit import audit_original


def review(
    report: dict, paper_bytes: bytes, *, expected_l2_calls: int = 0,
) -> dict:
    if type(expected_l2_calls) is not int or expected_l2_calls not in (0, 2):
        raise MP11PaperRejected("only zero or two bounded live L2 calls allowed")
    if (not isinstance(report,dict) or report.get("status") != "PASS"
            or report.get("classification") !=
            "DEV_ONLY_MP11_G3_THREE_S49_S16_PAPER_S50_WINDOWS_SAME_WORLD"
            or report.get("node_exit") != 0 or report.get("server_exit") != 0):
        raise MP11PaperRejected("original single-World complete runtime not successful")
    g2=audit_original(
        report, require_completed_cleanup=False,
        expected_l2_calls=expected_l2_calls,
    )
    g3=report.get("mp11_g3")
    if (not isinstance(g3,dict) or g3.get("paper_windows_attested") != 3
            or g3.get("l2_calls") != expected_l2_calls
            or g3.get("learning_updates") != 0
            or g3.get("prior_slope") != .65
            or not isinstance(g3.get("paper_world_uuid"),str)
            or not g3["paper_world_uuid"]
            or not isinstance(g3.get("subject_uuid"),str)
            or not g3["subject_uuid"]):
        raise MP11PaperRejected("MP11 native and Paper report mismatch")
    if expected_l2_calls:
        live = report.get("l_mp11_live_l2")
        proposals = live.get("proposals") if isinstance(live, dict) else None
        if (
            not isinstance(proposals, list) or len(proposals) != 2
            or live.get("validated_open_calls") != 2
            or live.get("attempts") != 2
            or live.get("experiments_selected_and_executed_by_l2") != 0
            or live.get("new_action_issuers") != 0
            or live.get("learning_admissions") != 0
            or live.get("l0_promotions") != 0
            or any(
                type(p) is not dict
                or p.get("provider_source") != "llama.cpp"
                or p.get("source_prior_count") != i+1
                or p.get("action_authority") is not False
                or p.get("next_test_owner_approved") is not False
                or p.get("learning_admissions") != 0
                or p.get("l0_promotions") != 0
                for i, p in enumerate(proposals)
            )
        ):
            raise MP11PaperRejected("unattributed or overclaimed live L2 OPEN calls")
    markers=tuple(g3.get("paper_markers",[]))
    if (len(markers)!=3
            or markers != tuple(a+"-"+report["session_id"] for a in g2["action_ids"])):
        raise MP11PaperRejected("Paper markers do not belong to original S49 Actions")
    paper=audit_multi_trial_paper(
        paper_bytes,action_markers=markers,
        world_uuid=g3["paper_world_uuid"],
        subject_uuid=g3["subject_uuid"],
        surfaces=("GRASS_BLOCK",)*3,
    )
    sha=hashlib.sha256(paper_bytes).hexdigest()
    if (sha != g3.get("original_sha256")
            or g3.get("wait_ticks") != [list(x.wait_ticks) for x in paper]):
        raise MP11PaperRejected("full original Paper source hash/tick mismatch")
    if len({x.wait_ticks[0] for x in paper})!=3:
        raise MP11PaperRejected("no three genuinely disjoint observed World tick windows")
    return {
        "classification": (
            "MP11_G3_LIVE_L2_SHADOW_NO_EXPERIMENT_AUTHORITY_DEV"
            if expected_l2_calls else
            "MP11_G3_THREE_ORIGINAL_S49_S16_AND_PAPER_WINDOWS_DEV"
        ),
        "paper_world_uuid":g3["paper_world_uuid"],
        "subject_uuid":g3["subject_uuid"],
        "session_id":report["session_id"],
        "original_paper_sha256":sha,
        "s49_actions":g2["original_s49_actions"],
        "s16_outcomes":g2["original_typed_s16_outcomes"],
        "s15_clear_receipts":g2["original_s15_clear_receipts"],
        "original_paper_wait_samples":sum(len(x.wait_ticks) for x in paper),
        "original_paper_prequential_frozen_pairs":7*len(paper),
        "per_action_wait_tick_ranges":[
            [x.wait_ticks[0],x.wait_ticks[-1]] for x in paper],
        "per_action_motion_m":[list(x.wait_motion_m) for x in paper],
        "model_type":"FIXED_OPERATOR_UNLEARNED_SLOPE_0_65",
        "surfaces":["GRASS_BLOCK"]*3,
        "actual_L2_model_calls":expected_l2_calls,
        "autonomous_hypothesis_test_selection":False,
        "controlled_input_duration_variation":False,
        "learned_L1_model_admitted":False,
        "world_UUID_from_real_paper_source":True,
        "same_world_3_original_actions":True,
        "l0_owner_unchanged":True,
        "qualification":"DEV_ONLY",
        "science":"NOT_RUN",
    }


def main() -> int:
    p=argparse.ArgumentParser()
    p.add_argument("--report",type=Path,required=True)
    p.add_argument("--original-paper",type=Path,required=True)
    p.add_argument("--output",type=Path,required=True)
    args=p.parse_args()
    data=review(json.loads(args.report.read_text()),args.original_paper.read_bytes())
    args.output.write_text(json.dumps(data,sort_keys=True,indent=2)+"\n")
    print("MP11_G3_READBACK="+json.dumps(data,sort_keys=True),flush=True)
    return 0


if __name__=="__main__":
    raise SystemExit(main())
