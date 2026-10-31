"""L17: read-only audit of a saved L16/S49 first-Action capture root.

Never starts Java/Node/Minecraft, manufactures independent external Goal
receipts, or changes the original files. No source-authenticity claim.
"""
from __future__ import annotations

import argparse
import json
import sys
from dataclasses import asdict
from pathlib import Path

from adapters.mineflayer.l16_first_action_goal_originals import (
    L16GoalPlan,
    PLAN_SCHEMA,
    load_original_prefix,
)
from relay_self.l14_original_bridge_goal_window import _json
from relay_self.l17_first_action_goal_handoff import (
    L17HandoffRejected,
    review_l17_first_action_goal,
)

REPORT_MAX = 2 * 1024 * 1024
ORIGINAL_FIELDS = (
    "action_id", "session_id", "before_seq", "dispatch_seq", "cleanup_seq",
    "after_seq", "first_probe_seq", "second_probe_seq",
    "first_probe_request_id", "second_probe_request_id",
)


def audit_saved_l16_capture(
    root: Path, report_path: Path,
) -> dict[str, object]:
    """Original-source comparison, not independent R/V authorization."""
    if (
        not isinstance(root, Path) or not root.is_absolute()
        or not isinstance(report_path, Path) or not report_path.is_absolute()
        or root.is_symlink() or report_path.is_symlink()
    ):
        raise L17HandoffRejected("absolute canonical source/report paths required")
    if not root.is_dir() or root.resolve(strict=True) != root:
        raise L17HandoffRejected("source directory is not physical canonical root")
    received, sent, s7, plan_raw = load_original_prefix(root)
    if len(plan_raw) > 4096 or not plan_raw.endswith(b"\n"):
        raise L17HandoffRejected("original pre-World plan invalid")
    plan_doc = _json(plan_raw)
    if (
        set(plan_doc) != {
            "schema", "target_x", "target_z", "tolerance_m",
            "stable_probe_delta_max_m", "independent_external_goal_owner",
            "authorizes_learning",
        }
        or plan_doc["schema"] != PLAN_SCHEMA
        or plan_doc["independent_external_goal_owner"] is not False
        or plan_doc["authorizes_learning"] is not False
    ):
        raise L17HandoffRejected("operator original is not the L16 Goal plan")
    plan = L16GoalPlan(
        plan_doc["target_x"], plan_doc["target_z"],
        plan_doc["tolerance_m"], plan_doc["stable_probe_delta_max_m"],
    )
    if plan.original_bytes() != plan_raw:
        raise L17HandoffRejected("operator pre-World plan original differs")
    if not report_path.is_file() or not 0 < report_path.stat().st_size <= REPORT_MAX:
        raise L17HandoffRejected("S49 report missing or oversized")
    raw_report = report_path.read_bytes()
    if not raw_report.endswith(b"\n") or raw_report.count(b"\n") > 100000:
        raise L17HandoffRejected("S49 report incomplete")
    report = _json(raw_report)
    capture = report.get("l16_capture")
    if (
        not isinstance(capture, dict)
        or capture.get("status") != "SOURCE_PREFIX_CAPTURED_UNQUALIFIED"
        or capture.get("first_action_only") is not True
        or capture.get("real_l10_pairs") != 0
        or capture.get("external_goal_owner_independent") is not False
        or capture.get("s7_index") != s7
        or not isinstance(capture.get("window"), dict)
        or not isinstance(report.get("actual_native_actions"), list)
        or len(report["actual_native_actions"]) < 1
    ):
        raise L17HandoffRejected("S49 first Action source report is not sealed")
    window = capture["window"]
    if (
        window.get("action_id") != report["actual_native_actions"][0].get("action")
        or window.get("session_id") != report.get("session_id")
    ):
        raise L17HandoffRejected("S49 existing Action result does not identify prefix")
    args = {
        "received_original": received, "sent_original": sent,
        "s7_receipt": s7, "plan": plan, "plan_original": plan_raw,
        "action_id": window["action_id"], "session_id": window["session_id"],
        "before_seq": window["before_seq"], "dispatch_seq": window["dispatch_seq"],
        "cleanup_seq": window["cleanup_seq"], "after_seq": window["after_seq"],
        "first_probe_seq": window["goal_probe_seq"],
        "second_probe_seq": window["second_goal_probe_seq"],
        "first_probe_request_id": (
            f'l16:{window["session_id"]}:{window["action_id"]}:goal-1'
        ),
        "second_probe_request_id": (
            f'l16:{window["session_id"]}:{window["action_id"]}:goal-2'
        ),
    }
    result = review_l17_first_action_goal(**args)
    if asdict(result.l16_first_action) != window:
        raise L17HandoffRejected("physical report and re-audited original disagree")
    return {
        "schema": result.schema,
        "classification": result.status.value,
        "l16_diagnostic_goal_status": result.l16_first_action.observed_goal_status,
        "received_sha256": result.l16_first_action.received_sha256,
        "sent_sha256": result.l16_first_action.sent_sha256,
        "source_shaped_l10_candidate_count": 0,
        "qualified_real_learning_pairs": 0,
        "s10_updates": 0,
        "s11_habit_grants": 0,
        "independent_goal_original_present": False,
        "actual_physical_source_authenticated": False,
        "physical_nonintervention_proven": False,
        "new_actions": 0,
        "new_worlds": 0,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path)
    parser.add_argument("--s49-report", type=Path)
    args = parser.parse_args(argv)
    if args.root is None and args.s49_report is None:
        print(json.dumps({
            "classification": "L17_DRY_RUN_NO_HOST_READ",
            "world_reads": 0, "physical_actions": 0,
        }, sort_keys=True))
        return 0
    if args.root is None or args.s49_report is None:
        parser.error("read-only L17 audit requires --root and --s49-report")
    try:
        outcome = audit_saved_l16_capture(args.root, args.s49_report)
    except (OSError, ValueError, TypeError, KeyError, IndexError) as exc:
        print(json.dumps({
            "classification": "L17_ORIGINAL_READBACK_BLOCKED",
            "reason_type": type(exc).__name__,
            "qualified_real_learning_pairs": 0,
        }, sort_keys=True), file=sys.stderr)
        return 2
    print(json.dumps(outcome, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
