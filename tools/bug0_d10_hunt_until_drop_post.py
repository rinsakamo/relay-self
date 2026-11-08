"""Independent D10 source audit: stop on first real vanilla drop and pickup."""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from tools.bug0_d6_multigen_post import MultigenAuditRejected, audit


def audit_d10(raw: str, report: dict, *, nonmotion_path: Path,
              motion_path: Path) -> dict:
    if not isinstance(report, dict) or report.get("d10_until_drop_dev") is not True:
        raise MultigenAuditRejected("D10 original World opt-in absent")
    result = audit(
        raw, report, nonmotion_path=nonmotion_path, motion_path=motion_path,
        d10_hunt_until_drop_dev=True,
    )
    if (
        result["status"] not in ("PASS_DEV", "NOT_EXERCISED")
        or result["completed_original_s49_kill_generations"]
            != len(result["natural_counts"])
        or result["natural_counts"][:-1].count(0)
            != len(result["natural_counts"])-1
        or result["hunt_goal_first_true_natural_drop_picked"]
            is not (result["status"] == "PASS_DEV")
        or result["d10_dev_safety_limit_not_product_policy"] != 12
        or result["original_attack_count"]
            < result["completed_original_s49_kill_generations"]
        or result["no_eat_after_move"] is not True
    ):
        raise MultigenAuditRejected("D10 natural hunt/cycle source not qualified")
    if result["status"] == "PASS_DEV":
        if (
            not 1 <= result["first_positive_generation"] <= 12
            or result["natural_counts"][-1] not in (1, 2)
            or not result["natural_item_uuid"]
            or result["original_move_count"] < 1
        ):
            raise MultigenAuditRejected("positive natural drop not genuinely collected")
    elif (
        len(result["natural_counts"]) != 12
        or any(count != 0 for count in result["natural_counts"])
        or result["first_positive_generation"] is not None
        or result["natural_item_uuid"] is not None
        or result["original_move_count"] != 0
    ):
        raise MultigenAuditRejected("exhausted trial cannot masquerade as success")
    return result


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--report", type=Path, required=True)
    p.add_argument("--server-log", type=Path, required=True)
    p.add_argument("--nonmotion-fence", type=Path, required=True)
    p.add_argument("--motion-fence", type=Path, required=True)
    p.add_argument("--out", type=Path, required=True)
    args = p.parse_args()
    result = audit_d10(
        args.server_log.read_text(encoding="utf8"),
        json.loads(args.report.read_text(encoding="utf8")),
        nonmotion_path=args.nonmotion_fence,
        motion_path=args.motion_fence,
    )
    args.out.write_text(
        json.dumps(result, indent=2, sort_keys=True) + "\n",
        encoding="utf8",
    )
    print(result["classification"])


if __name__ == "__main__":
    main()
