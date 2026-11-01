"""Independent POSTRUN audit of prior LIVE G3 prefix SHA witnesses.

No retrospective claim can establish when a host sampled bytes by itself:
this reconciles reported in-run prefix hashes with independently audited full
original Paper/S49 logs, original typed S16 and source chronology.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

from tools.mp11_g3_paper_one_world_audit import review


class LivePostrunRejected(ValueError):
    """The live-witness ledger does not match final original source."""


def audit_live_prefixes(report: dict, complete_paper: bytes) -> dict:
    if not isinstance(report, dict) or not isinstance(complete_paper, bytes):
        raise LivePostrunRejected("original report and Paper bytes required")
    shadow = report.get("l_mp11_live_l2")
    n_l2 = (
        shadow.get("validated_open_calls", 0)
        if isinstance(shadow, dict) else 0
    )
    if type(n_l2) is not int or n_l2 not in (0, 2):
        raise LivePostrunRejected("only zero or two qualified L2 shadow calls")
    g3 = review(report, complete_paper, expected_l2_calls=n_l2)
    live = report.get("l_mp11_live_prefix")
    g2 = report.get("mp11_g2")
    if (
        not isinstance(live, dict)
        or live.get("status") != "PROVISIONAL_LIVE_PREFIX_READ_ONLY"
        or live.get("l2_open_calls") != n_l2
        or live.get("learning_admissions") != 0
        or live.get("action_issuers_added") != 0
        or not isinstance(g2, dict)
        or not isinstance(g2.get("typed_s16_actions"), list)
    ):
        raise LivePostrunRejected("missing default-off read-only L provenance")
    windows = live.get("observations")
    native = g2["typed_s16_actions"]
    if (
        type(windows) is not list or len(windows) != 3
        or len(native) != 3
        or len(complete_paper) > 16_000_000
    ):
        raise LivePostrunRejected("not 3 original source windows")
    previous_len = 0
    result = []
    for i, (p, t) in enumerate(zip(windows, native)):
        if not isinstance(p, dict) or not isinstance(t, dict):
            raise LivePostrunRejected("missing original typed witness")
        size = p.get("paper_prefix_length")
        digest = p.get("paper_prefix_sha256")
        if (
            type(size) is not int or not previous_len < size <= len(complete_paper)
            or type(digest) is not str or len(digest) != 64
            or digest != hashlib.sha256(complete_paper[:size]).hexdigest()
            or complete_paper[size-1:size] != b"\n"
        ):
            raise LivePostrunRejected("original complete Paper prefix hash mismatch")
        action_ids = [x.get("action_id") for x in native]
        if (
            p.get("action_id") != action_ids[i]
            or p.get("native_s16_seq") != t.get("native_seq")
            or p.get("paper_first_tick") != g3["per_action_wait_tick_ranges"][i][0]
            or p.get("paper_last_tick") != g3["per_action_wait_tick_ranges"][i][1]
            or p.get("visible_previous_trials") != i+1
            or p.get("source_status") !=
            "LIVE_PAPER_PREFIX_UNSEALED_S49_TYPED_S16_CLAIM"
            or p.get("l2_calls") != (1 if n_l2 and i < 2 else 0)
            or p.get("l2_request_id") !=
            f"l-mp11-live:{g3['paper_world_uuid']}:after-{i+1}"
        ):
            raise LivePostrunRejected("foreign or reordered native S16/Paper source")
        if n_l2 and i < 2:
            proposals = shadow["proposals"]
            hypothesis = proposals[i]
            if (
                hypothesis.get("source_last_action_id") != p["action_id"]
                or hypothesis.get("source_last_prefix_sha256") != digest
                or hypothesis.get("source_world_uuid") != g3["paper_world_uuid"]
                or hypothesis.get("source_session_id") != g3["session_id"]
                or hypothesis.get("request_id") != p["l2_request_id"]
                or hypothesis.get("source_prior_count") != i+1
            ):
                raise LivePostrunRejected("L2 hypothesis was not after its prior source")
        previous_len = size
        result.append({
            "ordinal": i+1,
            "action_id": p["action_id"],
            "paper_prefix_length": size,
            "original_paper_prefix_sha256": digest,
            "native_s16_seq": p["native_s16_seq"],
            "last_wait_tick": p["paper_last_tick"],
        })
    return {
        "classification": (
            "L_MP11_LIVE_L2_SHADOW_POSTRUN_RECONCILED_DEV_ONLY"
            if n_l2 else
            "L_MP11_LIVE_PREFIX_POSTRUN_SOURCE_RECONCILED_DEV_ONLY"
        ),
        "paper_world_uuid": g3["paper_world_uuid"],
        "session_id": g3["session_id"],
        "three_original_s49_s16_paper_windows": True,
        "all_live_prefix_sha_match_final_original": True,
        "source_observations": result,
        "true_live_sample_clock_independently_attested": False,
        "real_l2_calls": n_l2, "learning_admissions": 0,
        "l0_promotion": 0,
        "qualification": "NO_GO", "science": "NOT_RUN",
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--report", type=Path, required=True)
    parser.add_argument("--original-paper", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    source = json.loads(args.report.read_text(encoding="utf-8"))
    original = args.original_paper.read_bytes()
    checked = audit_live_prefixes(source, original)
    args.output.write_text(json.dumps(checked, sort_keys=True, indent=2) + "\n")
    print("L_MP11_LIVE_POSTRUN=" + json.dumps(checked, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
