"""Read-only S42/L0 shadow comparison on a real S49 post-WAIT probe.

A correlated native probe plus the P1 modeled SelfBody is sufficient for a
*comparison*, NOT a fresh entities event, independent Action grant or genuine
ReactiveL0.decide(). Frozen S42 policy has no P1 input and must not be altered.
"""
from __future__ import annotations

from adapters.mineflayer.m02_paper_dev.s50_boundary import BoundaryRejected
from adapters.mineflayer.python_protocol import MineflayerObservation
from adapters.mineflayer.s34_native_world_cognition_ci import _native_threat
from adapters.mineflayer.s49_p1_postwait_native_dev import (
    compose_postwait_native_self_world_dev,
)
from adapters.mineflayer.s49_p1_self_body_dev import (
    MODEL,
    P1DevSelfBodyHandoff,
)
from experiments.fatigue_p1 import FatigueProfile, FatigueState, capability
from relay_self.learning import LearningPreferenceState
from relay_self.self_body import BodyOrigin, SelfBodyView
from relay_self.world_conditioned_choice import select_world_conditioned_choice


def preview_postwait_l0_dev(
    body: SelfBodyView,
    native: MineflayerObservation,
    handoff: P1DevSelfBodyHandoff,
    reviewed: dict,
    profile: FatigueProfile,
    retained: LearningPreferenceState,
) -> dict[str, object]:
    """Re-evaluate original S42 against a post-WAIT native probe, no Action.

    The P1 hypothesis does NOT enter original S42 scoring. It is read
    alongside the unchanged choice so that future L0 integration can
    measure which capabilities the decision would need to account for.
    """
    if (not isinstance(handoff, P1DevSelfBodyHandoff)
            or not isinstance(reviewed, dict)
            or not isinstance(profile, FatigueProfile)
            or not profile.enabled or profile.initial != 0
            or not isinstance(retained, LearningPreferenceState)
            or retained.target_id != "risk_weight"
            or retained.revision != 1 or retained.value != 4
            or body.session_id != handoff.session_id
            or native.session_id != handoff.session_id
            or reviewed.get("session_id") != handoff.session_id
            or reviewed.get("action_id") != handoff.action_id
            or reviewed.get("observer_run_id") != handoff.observer_run_id
            or reviewed.get("paper_window_sha256") != handoff.model_source_digest
            or reviewed.get("dev_fatigue_mode") != "MOVE_DISTANCE"
            or reviewed.get("dev_wait_count") != 8
            or reviewed.get("dev_fatigue_recovered", 0) <= 0
            or body.hypotheses != handoff.after_wait.hypotheses
            or body.hypothetical(MODEL, "p1_phase").value != "after-wait"
            or body.hypothetical(MODEL, "p1_sensor_pct").origin is not BodyOrigin.HYPOTHESIS):
        raise BoundaryRejected("S42 preview requires original post-WAIT typed sources")

    joined = compose_postwait_native_self_world_dev(body, native)
    # The source is a real native probe; it is not the fresh, independent
    # entities-event/probe pair required by original ReactiveL0.decide().
    try:
        threat = _native_threat(native, native.request_id)
        choice = select_world_conditioned_choice(
            threat, retained,
            expected_session_id=handoff.session_id,
            expected_entity_id=threat.entity_id,
        )
    except (ValueError, TypeError) as exc:
        raise BoundaryRejected("post-WAIT S42 shadow source/policy rejected") from exc

    move_tick = reviewed["uncertain_release_tick_excluded"]
    wait_tick = reviewed["dev_wait_ticks"][-1]["tick"]
    pre = FatigueState(
        handoff.session_id, profile.sha256, move_tick,
        reviewed["dev_fatigue_before"],
    )
    post = FatigueState(
        handoff.session_id, profile.sha256, wait_tick,
        reviewed["dev_fatigue_after"],
    )
    cap_move = capability(profile, pre)
    cap_wait = capability(profile, post)
    if (int(round(cap_move.efficiency * 100))
            != handoff.after_move.hypothetical(MODEL, "p1_capability_pct").value
            or int(round(cap_wait.efficiency * 100))
            != body.hypothetical(MODEL, "p1_capability_pct").value
            or joined["p1_model_sensor_pct"]
            != body.hypothetical(MODEL, "p1_sensor_pct").value
            or cap_wait.efficiency < cap_move.efficiency
            or choice.action_authorized):
        raise BoundaryRejected("native L0 preview/model capability mismatch")

    return {
        "status": "DEV_S42_ORIGINAL_POLICY_SHADOW_COMPARISON",
        "session_id": handoff.session_id,
        "native_seq": native.seq,
        "native_request_id": native.request_id,
        "body_epoch_id": body.epoch_id,
        "action_id": handoff.action_id,
        "world": handoff.world,
        "observer_run_id": handoff.observer_run_id,
        "original_frozen_retained_revision": retained.revision,
        "original_frozen_retained_value": retained.value,
        "original_s42_selection": choice.selection.value,
        "s42_distance_m": choice.distance_m,
        "s42_wait_score": choice.wait_score,
        "s42_move_score": choice.move_score,
        "after_move_p1_model_max_blocks_per_tick": (
            cap_move.max_move_blocks_per_world_tick
        ),
        "after_wait_p1_model_max_blocks_per_tick": (
            cap_wait.max_move_blocks_per_world_tick
        ),
        "after_move_p1_model_efficiency_pct": (
            handoff.after_move.hypothetical(
                MODEL, "p1_capability_pct",
            ).value
        ),
        "after_wait_p1_model_efficiency_pct": (
            body.hypothetical(MODEL, "p1_capability_pct").value
        ),
        "s42_has_p1_input": False,
        "p1_changed_original_s42_selection": False,
        "original_l0_entities_event_consumed": False,
        "actual_reactive_l0_decide_called": False,
        "fresh_action_grant_issued": False,
        "additional_native_probes": 0,
        "extra_action_issuers": 0,
        "independent_fatigue_attested": False,
        "qualification_go": False,
        "science_go": False,
    }
