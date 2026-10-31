"""L20 CLI: review an independent pre-World Goal commitment, never create one.

PRE-WORLD: use --target-x/--target-z to check pre-existing external bytes.
POST-WORLD: use --root/--s49-report to independently re-audit the first
Action's S7/L18 prefix and confirm the same predeclared geometry. Neither
mode authenticates chronology, an external observer or a reward.
"""
from __future__ import annotations

import argparse
import json
import sys
from dataclasses import asdict
from pathlib import Path

from adapters.mineflayer.l16_first_action_goal_originals import (
    L16FirstActionWindow,
    L16GoalPlan,
    load_original_prefix,
)
from adapters.mineflayer.l17_saved_original_goal_readback import (
    audit_saved_l16_capture,
)
from relay_self.l14_original_bridge_goal_window import _json
from relay_self.l20_external_goal_commitment import (
    L20GoalCommitmentRejected,
    review_external_pre_world_criterion,
    review_l20_post_s49_source,
)


def _read_external(path: Path) -> bytes:
    if (
        not isinstance(path, Path)
        or not path.is_absolute()
        or path.is_symlink()
        or not path.is_file()
        or path.resolve(strict=True) != path
        or not 0 < path.stat().st_size <= 4096
    ):
        raise L20GoalCommitmentRejected(
            "external reviewer file must be bounded canonical absolute original"
        )
    return path.read_bytes()


def audit_l20_external_goal(
    *, external_path: Path, admitted_sha256: str,
    operator_plan: L16GoalPlan,
    root: Path | None = None,
    report_path: Path | None = None,
) -> dict[str, object]:
    """Preflight is before World only if independently time-authenticated."""
    if (root is None) != (report_path is None):
        raise L20GoalCommitmentRejected("root and S49 report are paired")
    if root is not None and (
        not isinstance(root, Path) or not root.is_absolute()
        or not isinstance(report_path, Path) or not report_path.is_absolute()
        or external_path.is_relative_to(root)
    ):
        raise L20GoalCommitmentRejected(
            "external commitment must be outside S49 source directory"
        )
    original = _read_external(external_path)
    pre = review_external_pre_world_criterion(
        original=original,
        admitted_sha256=admitted_sha256, operator_plan=operator_plan,
    )
    if root is None:
        return {
            "mode": "PREWORLD_SOURCE_ONLY_NO_TIMESTAMP_AUTHENTICATION",
            "preflight": asdict(pre),
            "physical_world_read": False,
            "pre_world_time_independently_attested": False,
            "authenticated_independent_goal_owner": False,
            "independent_goal_result_original_present": False,
            "qualified_real_l10_pairs": 0,
            "s10_updates": 0,
        }
    assert report_path is not None
    # Re-audit whole raw received/sent S7 source and original S49 report
    # BEFORE trusting their stored structured window.
    saved = audit_saved_l16_capture(root, report_path)
    if (
        saved["qualified_real_learning_pairs"] != 0
        or saved["s10_updates"] != 0
        or saved["independent_goal_original_present"]
    ):
        raise L20GoalCommitmentRejected("L17 source-only status unexpectedly upgraded")
    _, _, _, plan_original = load_original_prefix(root)
    if operator_plan.original_bytes() != plan_original:
        raise L20GoalCommitmentRejected(
            "external criterion was not checked against original pre-World S49 plan"
        )
    report = _json(report_path.read_bytes())
    window = L16FirstActionWindow(**report["l16_capture"]["window"])
    bound = review_l20_post_s49_source(
        preflight=pre, window=window, operator_plan=operator_plan,
    )
    return {
        "mode": "POSTWORLD_FIRST_ACTION_SOURCE_ONLY",
        "preflight": asdict(pre),
        "binding": asdict(bound),
        "s16_owner_original_present": saved["s16_owner_original_present"],
        "independent_goal_result_original_present": False,
        "pre_world_time_independently_attested": False,
        "external_goal_owner_authenticated": False,
        "physical_nonintervention_attested": False,
        "qualified_real_l10_pairs": 0,
        "s10_updates": 0,
        "s11_habit_grants": 0,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--external-criterion-original", type=Path, required=True)
    parser.add_argument("--admitted-sha256", required=True)
    parser.add_argument("--target-x", type=float, required=True)
    parser.add_argument("--target-z", type=float, required=True)
    parser.add_argument("--tolerance-m", type=float, default=0.49)
    parser.add_argument("--stability-m", type=float, default=0.05)
    parser.add_argument("--root", type=Path)
    parser.add_argument("--s49-report", type=Path)
    args = parser.parse_args(argv)
    try:
        plan = L16GoalPlan(
            args.target_x, args.target_z,
            args.tolerance_m, args.stability_m,
        )
        result = audit_l20_external_goal(
            external_path=args.external_criterion_original,
            admitted_sha256=args.admitted_sha256,
            operator_plan=plan,
            root=args.root, report_path=args.s49_report,
        )
    except (ValueError, OSError, KeyError, TypeError) as exc:
        print(f"L20 rejected: {type(exc).__name__}: {exc}", file=sys.stderr)
        return 2
    print(json.dumps(result, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
