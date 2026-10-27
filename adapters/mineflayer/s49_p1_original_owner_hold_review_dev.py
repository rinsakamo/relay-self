"""Read-only source join for the original S49 S15 Paper tick hold (DEV).

Same Paper producer tick threshold in two new Worlds is evidenced, not
synchronized exact client Action onset/offset, physiological recovery or R WAIT.
"""
from __future__ import annotations

import json
import math
from pathlib import Path

from adapters.mineflayer.s49_p1_original_owner_hold_dev import (
    TARGET_PAPER_INDEX,
    inspect_original_paper_hold_dev,
)
from adapters.mineflayer.s49_p1_steady_phase_review_dev import (
    review_p1_steady_phase_worlds_dev,
)


class S49OriginalOwnerHoldReviewRejected(ValueError):
    pass


def join_original_owner_hold_dev(prior: dict, arms: dict[str, dict]) -> dict:
    if (
        type(prior) is not dict or type(arms) is not dict
        or set(arms) != {"CARRY", "WAIT_ASSUMED"}
        or prior.get("classification") != (
            "P1_SEVEN_BONUS_TICKS_PAPER_NODE_STABLE_PHASE_DESCRIPTIVE_DEV_ONLY"
        )
        or prior.get("paper_bonus_count_per_world") != 7
        or prior.get("model_preload_not_true_same_self_recovery") is not True
        or prior.get("original_s49_action_duration_matched") is not False
        or prior.get("world_tick_phase_synchronized") is not False
        or prior.get("native_paper_effect_tick_correspondence_proven") is not False
        or prior.get("physical_l0_dash_capability_admitted") is not None
        or prior.get("new_native_action_issuers") != 0
        or prior.get("new_native_packet_readers") != 0
        or prior.get("qualified_r_wait_ticks") != 0
        or prior.get("qualification_go") is not False
        or prior.get("science_go") is not False
    ):
        raise S49OriginalOwnerHoldReviewRejected("previous S49 motor source promoted")
    details = {}
    for case in ("CARRY", "WAIT_ASSUMED"):
        a = arms[case]
        record = a.get("hold")
        if (
            type(a) is not dict or type(record) is not dict
            or record.get("classification") != (
                "ORIGINAL_S49_S15_PAPER_PRODUCER_TICK_HOLD_DEV_ONLY"
            )
            or record.get("action_id") != a.get("first_action_id")
            or record.get("session_id") != a.get("session_id")
            or record.get("world") != a.get("world")
            or record.get("paper_hold_target_sample_index") != TARGET_PAPER_INDEX
            or record.get("paper_positive_boost_ticks_before_release") != 7
            or record.get("same_original_s15_clear_owner") is not True
            or record.get("node_paper_host_clocks_synchronized") is not False
            or record.get("native_action_duration_world_ticks_exact") is not False
            or record.get("qualification_go") is not False
            or record.get("science_go") is not False
            or type(a.get("first_native_displacement_m")) not in (float, int)
            or not math.isfinite(a["first_native_displacement_m"])
        ):
            raise S49OriginalOwnerHoldReviewRejected(f"{case} original S15 hold source absent")
        details[case] = {
            "first_action_id": a["first_action_id"],
            "session_id": a["session_id"],
            "world": a["world"],
            "paper_hold_target_sample_index": TARGET_PAPER_INDEX,
            "paper_hold_target_world_tick": record["paper_hold_target_world_tick"],
            "native_first_s16_displacement_m": a["first_native_displacement_m"],
            "same_original_s15_owner": True,
        }
    if (
        details["CARRY"]["session_id"] == details["WAIT_ASSUMED"]["session_id"]
        or details["CARRY"]["world"] == details["WAIT_ASSUMED"]["world"]
    ):
        raise S49OriginalOwnerHoldReviewRejected("duplicate source World")
    return {
        "classification": "P1_TWO_WORLDS_ORIGINAL_S49_OWNER_PAPER_HOLD_TICK_DEV_ONLY",
        "arms": details,
        "paper_owner_first_action_hold_target_index": TARGET_PAPER_INDEX,
        "original_s15_waited_for_Paper_tick_before_own_native_clear": True,
        "same_paper_hold_target_both_worlds": True,
        "same_paper_positive_boost_ticks": True,
        "paper_steady_speed_delta_by_ordinal_mps":
            prior["paper_stable_speed_delta_by_ordinal_mps"],
        "node_common_speed_proxy_delta_by_ordinal_mps":
            prior["node_speed_proxy_delta_by_ordinal_mps"],
        "native_first_s16_displacement_gain_m": (
            details["WAIT_ASSUMED"]["native_first_s16_displacement_m"]
            - details["CARRY"]["native_first_s16_displacement_m"]
        ),
        "same_native_action_elapsed_world_ticks_proven": False,
        "client_paper_effect_ticks_joined": False,
        "worlds_paper_ticks_synchronized": False,
        "native_wall_time_movement_phase_matched": False,
        "hypothesis_preloads_not_actual_P1_fatigue_sensor": True,
        "original_s49_sole_native_action_issuer": True,
        "source_bound_wait_admitted": False,
        "same_self_longitudinal_physical_recovery": False,
        "physical_L0_DASH_admission": None,
        "new_issuers_or_native_readers": 0,
        "additional_P1_M0_postings": 0,
        "qualification_go": False,
        "science_go": False,
    }


def review_original_owner_paper_hold_worlds_dev(root: Path) -> dict:
    if not isinstance(root, Path) or root.is_symlink() or not root.is_dir():
        raise S49OriginalOwnerHoldReviewRejected("untrusted original DEV World source root")
    prior = review_p1_steady_phase_worlds_dev(root)
    a = {}
    for case in ("CARRY", "WAIT_ASSUMED"):
        place = root / case
        outer = json.loads((place / "paper_forward_dash_dev_report.json").read_text())
        original = json.loads((place / "original_s49_report.json").read_text())
        first = original["actual_native_actions"][0]
        raw = (place / "paper_server.log").read_text(encoding="utf-8")
        if (
            original.get("status") != "PASS"
            or not outer.get("p1_matched_paper_boost_dev")
            or outer.get("p1_matched_paper_boost_dev", {}).get(
                "paper_positive_boost_ticks"
            ) != 7
        ):
            raise S49OriginalOwnerHoldReviewRejected("original native motor source changed")
        receipt = outer.get("original_s15_paper_owner_hold_dev")
        if receipt != inspect_original_paper_hold_dev(
            raw, action_id=first["action"], session_id=original["session_id"],
        ):
            raise S49OriginalOwnerHoldReviewRejected("original Paper owner receipt mismatch")
        a[case] = {
            "hold": receipt,
            "first_action_id": first["action"],
            "session_id": original["session_id"],
            "world": outer["paper_action_bracket"]["world_uuid"],
            "first_native_displacement_m": first["movement_m"],
        }
    result = join_original_owner_hold_dev(prior, a)
    (root / "p1_original_s15_tick_hold_comparison_dev.json").write_text(
        json.dumps(result, sort_keys=True, indent=2) + "\n",
        encoding="utf-8",
    )
    return result


def main() -> int:
    import argparse

    p = argparse.ArgumentParser()
    p.add_argument("--root", type=Path, required=True)
    args = p.parse_args()
    print(json.dumps(review_original_owner_paper_hold_worlds_dev(args.root), sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
