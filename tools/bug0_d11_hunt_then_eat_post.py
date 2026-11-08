"""D11 independent original Paper+S49/S51 EAT audit; no new Action authority."""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from tools.bug0_d6_multigen_post import MultigenAuditRejected, audit


def audit_d11(raw: str, report: dict, *, nonmotion_path: Path,
              motion_path: Path, s50_sidecar: str) -> dict:
    if (
        not isinstance(report, dict)
        or report.get("d11_hunt_then_eat_dev") is not True
        or report.get("d10_until_drop_dev") is not True
        or report.get("d7f_live_eat_optin") is not True
        or not isinstance(s50_sidecar, str)
        or "S50_DEV_NATIVE_READBACK_V1" not in s50_sidecar
    ):
        raise MultigenAuditRejected("original D11 S49/S50/S51 scope unqualified")
    result = audit(
        raw, report, nonmotion_path=nonmotion_path,
        motion_path=motion_path,
        d10_hunt_until_drop_dev=True, d11_hunt_then_eat_dev=True,
    )
    counts = result["natural_counts"]
    positive = result["status"] == "PASS_DEV"
    if (
        result["completed_original_s49_kill_generations"] != len(counts)
        or not 1 <= len(counts) <= 12
        or any(n != 0 for n in counts[:-1])
        or result["d10_dev_safety_limit_not_product_policy"] != 12
        or result["hunt_goal_first_true_natural_drop_picked"] is not positive
        or result["d11_first_real_eat_verified"] is not positive
        or result["no_eat_after_move"] is positive
        or result["original_attack_count"] != len(counts)
        or result["same_supervisor_retained"] is not True
    ):
        raise MultigenAuditRejected("D11 genuine original hunter/EAT continuity missing")
    if positive:
        outcome = report.get("d11_eat_outcome")
        stop = (
            report.get("d7f_live_natural_stop")
            if result["d11_eat_generation"] == 1 else
            report.get("d11_live_natural_stop")
        )
        if (
            counts[-1] not in (1, 2)
            or not result["natural_item_uuid"]
            or result["original_move_count"] < 1
            or result["d11_eat_generation"] != len(counts)
            or not isinstance(outcome, dict)
            or outcome.get("count_before") != counts[-1]
            or outcome.get("count_after") != counts[-1] - 1
            or outcome.get("consumed_item") != "rotten_flesh"
            or outcome.get("food_after", 0) <= outcome.get("food_before", 0)
            or not isinstance(stop, dict)
            or stop.get("session_id") != result["session_id"]
            or stop.get("classification")
                != "D7_F_DEV_LIVE_NATURAL_BODY_STEADY_SOURCE"
            or stop.get("paper_pickup_tick", 0) < 1
            or stop.get("server_effective_original_clear_tick")
                != "NOT_CAUSALLY_ATTESTED"
        ):
            raise MultigenAuditRejected("D11 S51 original Food/S50 STOP unproven")
    else:
        if (
            len(counts) != 12 or counts != [0]*12
            or result["original_move_count"] != 0
            or result["d11_eat_action_id"] is not None
            or report.get("self_eat") is not False
        ):
            raise MultigenAuditRejected("D11 zero-drop safety stop invented food")
    return {
        **result,
        "classification": (
            "D11_ZERO_DROP_HUNT_REAL_PICKUP_STOP_S51_EAT_PASS"
            if positive
            else "D11_TWELVE_ZERO_DROPS_NO_REAL_EAT_NOT_EXERCISED"
        ),
        "genuine_s51_eat": positive,
        "world_safety_budget_not_goal": True,
        "long_term_survival_proven": False,
        "server_effective_clear_tick_proven": False,
    }


def main() -> None:
    p = argparse.ArgumentParser()
    for name in (
        "report", "server-log", "nonmotion-fence", "motion-fence",
        "s50-sidecar", "out",
    ):
        p.add_argument("--" + name, type=Path, required=True)
    a = p.parse_args()
    result = audit_d11(
        a.server_log.read_text(encoding="utf8"),
        json.loads(a.report.read_text(encoding="utf8")),
        nonmotion_path=a.nonmotion_fence, motion_path=a.motion_fence,
        s50_sidecar=a.s50_sidecar.read_text(encoding="utf8"),
    )
    a.out.write_text(
        json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf8",
    )
    print(result["classification"])


if __name__ == "__main__":
    main()
