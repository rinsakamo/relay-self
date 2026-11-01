"""H9a bounded, untrained DEV comparison of two original S49 S42 distances.

The caller must separately execute the existing H8 independent original audit
against each World before passing its results here. This is observational,
not a physical clear certification, a trained policy, or a causal estimate.
"""
from __future__ import annotations

import hashlib
import math
from dataclasses import asdict, dataclass

from relay_self.l_bcg_h9a_stimulus import (
    ARM_DISTANCES_M,
    CHEAP_THRESHOLD_M,
    H9aRejected,
    select_h9a_stimulus,
    verify_h9a_observed_distance,
)

REQUIRED_UNKNOWN = (
    "goal_remaining_m", "goal_tolerance_m", "selected_gait",
    "p1_fatigue_high", "m_energy_low", "verified_obstacle",
    "world_revision", "verified_post_clear_training",
)
EXPECTED_PREREG_CEILING = "H9A_DEV_EXPLORATORY_NO_PHYSICAL_LEARNING"


@dataclass(frozen=True, slots=True)
class H9aArmResult:
    arm_id: str
    requested_distance_m: float
    observed_s42_distance_m: float
    original_preaction_native_seq: int
    original_session_id: str
    original_paper_world_id: str
    executor_head: str
    original_report_sha256: str
    cheap_near_under_3m: bool
    sampled_reported_input_off_motion_m: float
    original_l0_selection: str = "MOVE_AWAY"
    observed_arm_matched: bool = True
    l_bcg_advice: str = "DEFER_UNKNOWN"
    physical_effective_clear_attested: bool = False
    qualified_training_worlds: int = 0
    new_actions: int = 0
    learning_updates: int = 0


@dataclass(frozen=True, slots=True)
class H9aPairComparison:
    arms: tuple[H9aArmResult, H9aArmResult]
    distance_delta_m: float
    sampled_motion_delta_m: float
    cheap_comparator_differs: bool
    classification: str = "H9A_TWO_INDEPENDENT_WORLDS_DEV_EXPLORATORY_ONLY"
    formal_train_worlds: int = 0
    formal_heldout_worlds: int = 0
    real_causal_improvement_attested: bool = False
    learned_l1_attention: str = "DEFER_UNKNOWN"
    l0_policy_modified: bool = False
    action_authority: bool = False


def _check(ok: bool, message: str) -> None:
    if not ok:
        raise H9aRejected(message)


def _number(x: object) -> bool:
    return type(x) in (int, float) and math.isfinite(x)


def review_h9a_arm(
    *, report: dict, independent_h8_audit: dict, prereg: dict,
    original_report_bytes: bytes,
) -> H9aArmResult:
    """Review original event20 S42 + pre-Action sidecar, not requested distance.

    H8's separate-process audit must already have reconstructed original
    Sidecar/S7/S16/Paper/command/cleanup. A forged in-memory H8 audit is
    outside this function's trusted boundary; don't call without that review.
    """
    _check(
        type(report) is dict and type(independent_h8_audit) is dict
        and type(prereg) is dict and type(original_report_bytes) is bytes,
        "H9a original, prereg and audit required",
    )
    _check(
        prereg.get("schema") == "L_BCG_H9A_ARM_PREREG_V1"
        and prereg.get("source_ceiling") == EXPECTED_PREREG_CEILING
        and prereg.get("arm_id") in ("A", "B")
        and prereg.get("worlds") == 1
        and prereg.get("max_original_actions") == 1
        and prereg.get("retries") == 0
        and prereg.get("additional_l_bcg_actions") == 0
        and prereg.get("additional_native_probes") == 0
        and prereg.get("model_calls") == 0
        and prereg.get("learning_updates") == 0
        and prereg.get("qualified_training_worlds") == 0
        and prereg.get("cheap_threshold_m") == CHEAP_THRESHOLD_M,
        "missing or changed frozen H9a prereg",
    )
    requested = prereg.get("requested_distance_m")
    _check(
        _number(requested) and float(requested) in ARM_DISTANCES_M
        and type(prereg.get("executor_head")) is str
        and len(prereg["executor_head"]) == 40
        and all(ch in "0123456789abcdef" for ch in prereg["executor_head"]),
        "H9a arm or executor HEAD not pinned",
    )
    arm = select_h9a_stimulus(
        requested, l_bcg_shadow_dev=True, live_next_epoch_dev=True,
        l22_settling_probes=5,
    )
    _check(arm is not None, "missing H9a arm")
    _check(
        report.get("l_bcg_h9a_stimulus") == asdict(arm)
        and independent_h8_audit.get("classification")
        == "DEV_H8_ORIGINAL_CHAIN_AND_BCG_DEFER_VERIFIED"
        and independent_h8_audit.get("worlds") == 1
        and independent_h8_audit.get("actions") == 1
        and independent_h8_audit.get("s16_outcomes") == 1
        and independent_h8_audit.get("qualified_training_worlds") == 0
        and independent_h8_audit.get("effective_clear") == "NOT_ATTESTED"
        and independent_h8_audit.get("goal") == "UNDETERMINED"
        and independent_h8_audit.get("qualification") == "NO_GO"
        and independent_h8_audit.get("science") == "NOT_RUN"
        and independent_h8_audit.get("model_calls") == 0
        and independent_h8_audit.get("additional_actions") == 0
        and independent_h8_audit.get("additional_native_probes") == 0
        and independent_h8_audit.get("learning_updates") == 0,
        "H9a original audit/source limit invalid",
    )
    _check(
        independent_h8_audit.get("original_sha256", {}).get("s49-report.json")
        == hashlib.sha256(original_report_bytes).hexdigest(),
        "H9a report original digest mismatch",
    )
    try:
        sid = report["session_id"]
        original_l0 = report["decisions"]
        move = original_l0[1]
        sidecar = report["l_bcg_h8_preaction"]
        window = report["live_next_epoch"]["window"]
        shadow = report["l_bcg_shadow"]
        entity_id = move["entity_id"]
        original_distance = move["distance_m"]
    except (KeyError, IndexError, TypeError) as exc:
        raise H9aRejected("H9a S49 original fields missing") from exc
    _check(
        type(sidecar) is dict and type(window) is dict
        and type(shadow) is dict,
        "H9a preaction/window/shadow type invalid",
    )
    _check(
        type(sid) is str and bool(sid)
        and len(original_l0) == 3
        and [v["selected"] for v in original_l0] == ["WAIT", "MOVE_AWAY", "WAIT"]
        and [v["issued"] for v in original_l0] == [False, True, False]
        and original_l0[0]["distance_m"] >= 4
        and original_l0[2]["distance_m"] >= 4
        and move["probe_seq"] == sidecar["native_seq"]
        and move["event_seq"] == sidecar["event_seq"]
        and sid == sidecar["session_id"] == window["session_id"]
        and sidecar["phase"] == "AFTER_ORIGINAL_L0_BEFORE_SOLE_EXECUTOR"
        and sidecar["native_source_ref"] == (
            f"native-probe:{sid}:{move['probe_seq']}:"
            f"s49-actual:{sid}:event-{move['event_seq']}"
        )
        and sidecar == independent_h8_audit.get("preaction")
        and sidecar["owner_receipts"] == {}
        and set(sidecar["conditions"]) == set(REQUIRED_UNKNOWN)
        and all(sidecar["conditions"][key] == "UNKNOWN" for key in REQUIRED_UNKNOWN)
        and sidecar["qualified_training_worlds"] == 0
        and sidecar["advice"] == "DEFER_UNKNOWN"
        and sidecar["action_authority"] is False
        and shadow["advice"] == "DEFER_UNKNOWN"
        and shadow["action_authority"] is False
        and shadow["used_physical_training_worlds"] == 0
        and window["provisional"] is True
        and window["effective_clear_tick"] == "NOT_ATTESTED"
        and window["physical_stability_attested"] is False,
        "H9a pre-Action and post-Action original source leaked",
    )
    _check(
        type(entity_id) is int and _number(original_distance),
        "H9a original observed S42 distance required",
    )
    _check(
        any(
            e.get("entity_ref") == f"entity-{entity_id}"
            and e.get("label") == "zombie"
            and e.get("distance_m") == original_distance
            for e in sidecar["world"]["entities"]
        ),
        "H9a pre-Action S42 target not in same original World snapshot",
    )
    _check(
        verify_h9a_observed_distance(
            arm, original_s42_distance_m=original_distance,
            original_l0_choice=move["selected"],
        ),
        "H9a native S42 did not reach declared manipulated distance",
    )
    ticks = window.get("ticks")
    _check(isinstance(ticks, list) and len(ticks) == 8, "H9a Paper samples unavailable")
    sampled = 0.0
    for tick in ticks:
        _check(
            type(tick) is dict
            and type(tick.get("last_reported_input_active")) is bool
            and _number(tick.get("displacement_m"))
            and tick["displacement_m"] >= 0,
            "H9a invalid Paper sample",
        )
        if not tick["last_reported_input_active"]:
            sampled += tick["displacement_m"]
    _check(math.isfinite(sampled), "H9a nonfinite observed proxy")
    wid = window.get("paper_world_uuid")
    _check(type(wid) is str and bool(wid), "H9a paper World identifier missing")
    return H9aArmResult(
        arm_id=prereg["arm_id"],
        requested_distance_m=float(requested),
        observed_s42_distance_m=float(original_distance),
        original_preaction_native_seq=move["probe_seq"],
        original_session_id=sid,
        original_paper_world_id=wid,
        executor_head=prereg["executor_head"],
        original_report_sha256=hashlib.sha256(original_report_bytes).hexdigest(),
        cheap_near_under_3m=original_distance < CHEAP_THRESHOLD_M,
        sampled_reported_input_off_motion_m=sampled,
    )


def compare_h9a_pair(
    a: H9aArmResult, b: H9aArmResult,
) -> H9aPairComparison:
    """One 2m and one 3.5m arm, each independent World; NOT generalization."""
    _check(type(a) is type(b) is H9aArmResult, "two bounded reviewed arms required")
    _check(
        a.arm_id == "A" and b.arm_id == "B"
        and (a.requested_distance_m, b.requested_distance_m) == ARM_DISTANCES_M
        and a.original_session_id != b.original_session_id
        and a.original_paper_world_id != b.original_paper_world_id
        and a.executor_head == b.executor_head
        and a.original_report_sha256 != b.original_report_sha256
        and a.observed_arm_matched and b.observed_arm_matched
        and a.original_l0_selection == b.original_l0_selection == "MOVE_AWAY"
        and a.l_bcg_advice == b.l_bcg_advice == "DEFER_UNKNOWN"
        and not (a.physical_effective_clear_attested or b.physical_effective_clear_attested)
        and a.qualified_training_worlds == b.qualified_training_worlds == 0
        and a.new_actions == b.new_actions == 0
        and a.learning_updates == b.learning_updates == 0
        and a.cheap_near_under_3m and not b.cheap_near_under_3m,
        "H9a independent World, frozen arms, source ceiling or cheap comparator invalid",
    )
    return H9aPairComparison(
        arms=(a, b),
        distance_delta_m=b.observed_s42_distance_m - a.observed_s42_distance_m,
        sampled_motion_delta_m=(
            b.sampled_reported_input_off_motion_m
            - a.sampled_reported_input_off_motion_m
        ),
        cheap_comparator_differs=True,
    )
