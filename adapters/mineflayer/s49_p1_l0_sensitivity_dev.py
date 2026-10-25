"""DEV-only P1 parameter knockdown on ONE original S49/Paper/native run.

Compare baseline and high-exertion sensitivity model under *identical*
World evidence. A higher MOVE fatigue rate is deliberately a scenario,
not a physiologically measured rate, original P1 rate change, R attestation,
nor permission for S49/L0 to issue any extra Action.
"""
from __future__ import annotations

from adapters.mineflayer.m02_paper_dev.s50_boundary import BoundaryRejected
from adapters.mineflayer.python_protocol import MineflayerObservation
from adapters.mineflayer.s49_p1_l0_capability_dev import (
    compare_body_capability_l0_dev,
)
from adapters.mineflayer.s49_p1_self_body_dev import (
    compose_s49_p1_dev_self_body,
    compose_s49_p1_postwait_native_dev,
)
from experiments.fatigue_p1 import FatigueProfile, Rate
from relay_self.learning import LearningPreferenceState

BASELINE = FatigueProfile(enabled=True, initial=0.0)
# Deliberately uncalibrated upper-stress sensitivity, not a measured property.
CHALLENGE = FatigueProfile(
    enabled=True,
    initial=0.0,
    move_per_block=Rate(2.0),
)


def compare_p1_knockdown_dev(
    original_s49: dict,
    paper_window: str,
    postwait_probe: MineflayerObservation,
    *,
    expected_player_uuid: str,
    retained: LearningPreferenceState,
) -> dict[str, object]:
    """Rerun existing P1+SelfBody+S42 on same real World with two *profiles*.

    Replays are pure. Neither variation is a live L0 policy update. The
    post-WAIT probe was obtained once by the existing original S49 owner.
    """
    if (not isinstance(original_s49, dict)
            or not isinstance(postwait_probe, MineflayerObservation)
            or not isinstance(retained, LearningPreferenceState)):
        raise BoundaryRejected("original typed World/owner required")
    actions = original_s49.get("actual_native_actions")
    if not isinstance(actions, list) or len(actions) != 2:
        raise BoundaryRejected("original S49 pair required")
    modes = []
    for label, profile in (("BASELINE", BASELINE), ("STRESS", CHALLENGE)):
        handoff, checked = compose_s49_p1_dev_self_body(
            original_s49, paper_window,
            expected_player_uuid=expected_player_uuid,
            profile=profile,
        )
        expected_request_id = (
            f"s49-postwait:{handoff.session_id}:{handoff.action_id}"
        )
        body, readback = compose_s49_p1_postwait_native_dev(
            handoff, checked, actions[-1], postwait_probe,
            expected_request_id=expected_request_id,
        )
        comparison = compare_body_capability_l0_dev(
            body, postwait_probe, handoff, checked, profile, retained,
        )
        if (readback["native_seq"] != comparison["native_seq"]
                or readback["native_source_ref"] != body.observation.source_ref
                or comparison["session_id"] != handoff.session_id
                or comparison["world"] != checked["world"]
                or comparison["observer_run_id"] != checked["observer_run_id"]
                or comparison["original_l0_policy_modified"] is not False
                or comparison["new_action_grant_issued"] is not False
                or comparison["actual_native_actions_added"] != 0
                or comparison["original_l0_decide_called"] is not False):
            raise BoundaryRejected("P1 sensitivity case moved native/Action ownership")
        modes.append((label, profile, handoff, checked, comparison))

    _, _, base_handoff, baseline, base_choice = modes[0]
    _, stress_profile, stress_handoff, stress, stress_choice = modes[1]
    if (base_choice["native_seq"] != stress_choice["native_seq"]
            or base_choice["native_request_id"] != stress_choice["native_request_id"]
            or base_choice["body_epoch_id"] != stress_choice["body_epoch_id"]
            or base_choice["s42_selection_unchanged"]
            != stress_choice["s42_selection_unchanged"]
            or base_handoff.model_source_digest != stress_handoff.model_source_digest
            or baseline["dev_move"]["movement_m"]
            != stress["dev_move"]["movement_m"]
            or baseline["dev_wait_count"] != stress["dev_wait_count"]
            or baseline["dev_fatigue_before"] >= stress["dev_fatigue_before"]
            or stress["dev_fatigue_after"] <= baseline["dev_fatigue_after"]
            or stress_choice["modeled_after_wait_one_tick_capacity_blocks"]
            >= base_choice["modeled_after_wait_one_tick_capacity_blocks"]
            or stress["wait_ticks_admitted"] != 0
            or stress["qualification_go"] is not False):
        raise BoundaryRejected("P1 stress must be same World with distinct model outcome")
    return {
        "status": "DEV_SAME_WORLD_P1_RATE_KNOCKDOWN",
        "classification": "DEV_ONLY_MODEL_SENSITIVITY_NOT_CALIBRATION",
        "session_id": baseline["session_id"],
        "action_id": baseline["action_id"],
        "world": baseline["world"],
        "observer_run_id": baseline["observer_run_id"],
        "paper_window_sha256": baseline["paper_window_sha256"],
        "native_seq": base_choice["native_seq"],
        "native_request_id": base_choice["native_request_id"],
        "native_body_epoch_id": base_choice["body_epoch_id"],
        "last_actual_move_m": baseline["dev_move"]["movement_m"],
        "wait_samples": baseline["dev_wait_count"],
        "baseline_move_rate_per_block": BASELINE.move_per_block.value,
        "stress_move_rate_per_block": stress_profile.move_per_block.value,
        "baseline_fatigue_after_move": baseline["dev_fatigue_before"],
        "stress_fatigue_after_move": stress["dev_fatigue_before"],
        "baseline_fatigue_after_wait": baseline["dev_fatigue_after"],
        "stress_fatigue_after_wait": stress["dev_fatigue_after"],
        "s42_original_selection": base_choice["s42_selection_unchanged"],
        "baseline_l0_capability_candidate": (
            base_choice["after_wait_on_actual_postwait_world_model"]
        ),
        "stress_l0_capability_candidate": (
            stress_choice["after_wait_on_actual_postwait_world_model"]
        ),
        "baseline_one_tick_capacity": (
            base_choice["modeled_after_wait_one_tick_capacity_blocks"]
        ),
        "stress_one_tick_capacity": (
            stress_choice["modeled_after_wait_one_tick_capacity_blocks"]
        ),
        "stress_profile_is_measured": False,
        "native_paper_tick_alignment_attested": False,
        "real_next_l0_decide_called": False,
        "new_native_probes": 0,
        "new_action_issuers": 0,
        "real_action_count_added": 0,
        "production_p1_mutated": False,
        "qualification_go": False,
        "science_go": False,
    }
