"""Independent read-only persisted original S49 ATTACK/EAT fence audit.

This checks original D4+D5 native ACK/action readbacks against the persisted
pre-ISSUE rows; the independent D5 Paper/native audit runs separately.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from relay_self.s49_nonmotion_physical_fence import OriginalS49NonMotionFence


class D5NonMotionAuditRejected(ValueError):
    """Original durable Action evidence cannot be reconciled."""


def audit(report: dict, path: Path) -> dict:
    if not isinstance(report, dict) or not isinstance(path, Path):
        raise D5NonMotionAuditRejected("typed report and persistent path required")
    pre = report.get("nonmotion_fence_preflight")
    stored = report.get("nonmotion_fence")
    first = report.get("s49_actions")
    second = report.get("d5_second_action")
    eaten = report.get("d4_natural_food_pickup_eat_proven")
    sid = report.get("session_id")
    if (
        report.get("status") != "PASS_DEV"
        or report.get("classification") != "D5_REAL_S49_SECOND_INTENT_ATTACK_PASS"
        or not isinstance(pre, dict)
        or pre.get("checked_before_world") is not True
        or pre.get("prior_actions") != 0
        or pre.get("filename") != path.name
        or not isinstance(stored, dict)
        or not isinstance(first, list) or not first
        or not isinstance(second, dict)
        or type(eaten) is not bool
        or not isinstance(sid, str) or not sid
    ):
        raise D5NonMotionAuditRejected("original D5 fenced run was not qualified")
    fence = OriginalS49NonMotionFence.restore(path, self_id="s49-original-self")
    fence.require_clear()
    rows = fence.actions
    original_actions = [*first, *([{"action_id": report.get("d4_eat_action_id")}]
                                 if eaten else []), second]
    expected_kinds = ["ATTACK"] * len(first) + (["EAT"] if eaten else []) + ["ATTACK"]
    if (
        len(rows) != len(original_actions)
        or [r["kind"] for r in rows] != expected_kinds
        or [r["action_id"] for r in rows] != [x.get("action_id") for x in original_actions]
        or any(r["status"] != "S16_OUTCOME" or r["terminal"] != "outcome"
               for r in rows)
        or any(r["session_id"] != sid or r["source_ref"] !=
               f"{sid}:{r['probe_seq']}" for r in rows)
        or stored.get("sha256") != fence.sha256
        or stored.get("unresolved") is not False
        or stored.get("action_ids") != [r["action_id"] for r in rows]
        or stored.get("kinds") != expected_kinds
        or stored.get("statuses") != ["S16_OUTCOME"] * len(rows)
        or stored.get("physical_exactly_once_attested") is not False
    ):
        raise D5NonMotionAuditRejected("persistent Action lineage or SHA mismatch")
    for i, (row, action) in enumerate(zip(rows, original_actions)):
        if row["kind"] == "ATTACK":
            intent = ("escape-threat" if i < len(first)
                      else "bug0-d5-second-zombie-encounter")
            if (
                row["intent_id"] != intent
                or row["subject"] != action.get("target_entity_id")
                or row["probe_seq"] != action.get("admitted_seq")
                or row["effect_seqs"] != [action.get("effect_seq")]
                or row["after_seq"] != action.get("after_seq")
                or row["result"] != {
                    "effect": "attack_entity", "applied": True,
                    "death_attested": False,
                }
                or action.get("terminal") != "outcome"
                or action.get("ack") != "applied"
            ):
                raise D5NonMotionAuditRejected("ATTACK original S16/native mismatch")
        else:
            outcome = report.get("d4_eat_outcome")
            choice = report.get("d4_preissue_choice")
            if (
                not isinstance(outcome, dict)
                or not isinstance(choice, dict)
                or row["intent_id"] != "escape-threat"
                or row["subject"] != "rotten_flesh"
                or row["probe_seq"] != choice.get("seq")
                or choice.get("item") != "rotten_flesh"
                or row["result"] != {
                    "food_before": outcome.get("food_before"),
                    "food_after": outcome.get("food_after"),
                    "item_count_before": outcome.get("count_before"),
                    "item_count_after": outcome.get("count_after"),
                }
            ):
                raise D5NonMotionAuditRejected("EAT original S51/native mismatch")
    return {
        "status": "PASS_DEV",
        "classification": "D5_NONMOTION_PREISSUE_FENCE_ORIGINAL_READBACK_PASS",
        "session_id": sid,
        "action_ids": [r["action_id"] for r in rows],
        "kinds": expected_kinds,
        "fence_sha256": fence.sha256,
        "first_eat_conditional": eaten,
        "physical_exactly_once_attested": False,
        "second_complete_survival_cycle_attested": False,
        "qualification": "NO_GO",
        "science": "NOT_RUN",
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--report", required=True, type=Path)
    parser.add_argument("--fence", required=True, type=Path)
    parser.add_argument("--out", required=True, type=Path)
    args = parser.parse_args()
    result = audit(json.loads(args.report.read_text(encoding="utf8")), args.fence)
    args.out.write_text(json.dumps(result, sort_keys=True, indent=2) + "\n",
                        encoding="utf8")


if __name__ == "__main__":
    main()
