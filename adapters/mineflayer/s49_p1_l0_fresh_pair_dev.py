"""Actual post-Paper native entities event + correlated probe for DEV L0 input.

Uses ONE original S49 Mineflayer receiver, already suspended inside its
Action callback. No new native process/receiver, Action authorization or
actual L0.decide() is introduced. A fresh event-probe pair is a strictly
stronger source than an arbitrary standalone post-WAIT probe; neither
proves fatigue nor gives a World tick attestation to Paper callbacks.
"""
from __future__ import annotations

from adapters.mineflayer.m02_paper_dev.s50_boundary import BoundaryRejected
from adapters.mineflayer.normal_action import NormalWorldL0
from adapters.mineflayer.python_protocol import MineflayerObservation
from adapters.mineflayer.reactive_l0 import ReactiveL0Rejected
from adapters.mineflayer.s49_p1_l0_capability_dev import (
    compare_body_capability_l0_dev,
)
from adapters.mineflayer.s49_p1_self_body_dev import P1DevSelfBodyHandoff
from experiments.fatigue_p1 import FatigueProfile
from relay_self.learning import LearningPreferenceState
from relay_self.self_body import SelfBodyView


def review_postwait_fresh_l0_input_dev(
    event: MineflayerObservation,
    probe: MineflayerObservation,
    *,
    prior_postwait_probe: MineflayerObservation,
    body: SelfBodyView,
    handoff: P1DevSelfBodyHandoff,
    p1_reviewed: dict,
    profile: FatigueProfile,
    retained: LearningPreferenceState,
) -> dict[str, object]:
    """Check genuine paired source with original NormalWorldL0._check only."""
    if (not isinstance(event, MineflayerObservation)
            or not isinstance(probe, MineflayerObservation)
            or not isinstance(prior_postwait_probe, MineflayerObservation)
            or not isinstance(body, SelfBodyView)
            or not isinstance(handoff, P1DevSelfBodyHandoff)
            or not isinstance(p1_reviewed, dict)
            or not isinstance(profile, FatigueProfile)
            or not isinstance(retained, LearningPreferenceState)
            or prior_postwait_probe.session_id != handoff.session_id
            or prior_postwait_probe.kind != "probe"
            or prior_postwait_probe.request_id != (
                f"s49-postwait:{handoff.session_id}:{handoff.action_id}"
            )
            or event.session_id != prior_postwait_probe.session_id
            or probe.session_id != prior_postwait_probe.session_id
            or event.seq <= prior_postwait_probe.seq
            or probe.seq <= event.seq
            or event.kind != "entities" or event.request_id is not None
            or probe.kind != "probe"
            or probe.request_id != (
                f"s49-postwait-event:{handoff.session_id}:{event.seq}"
            )
            or body.observation is None
            or body.observation.native_seq != prior_postwait_probe.seq
            or body.hypotheses != handoff.after_wait.hypotheses
            or body.session_id != handoff.session_id):
        raise BoundaryRejected("post-WAIT L0 event/probe must follow exact owner probe")
    prior_zombies = {
        e.entity_id for e in prior_postwait_probe.snapshot.nearby_entities
        if e.name == "zombie"
    }
    spawned = [
        e for e in event.snapshot.nearby_entities if e.name == "zombie"
    ]
    if len(spawned) != 1 or spawned[0].entity_id in prior_zombies:
        raise BoundaryRejected("a new native zombie World stimulus is required")
    # The original L0's existing exact event/probe check is called WITHOUT
    # decide() or a grant. The event source is real and ordered, but no
    # new owner or Action issuer becomes active.
    try:
        l0 = NormalWorldL0(
            handoff.session_id, "escape-threat", retained,
            max_events=1, max_action_requests=1,
        )
        choice = l0._check(event, probe)
    except (ReactiveL0Rejected, ValueError, TypeError) as exc:
        raise BoundaryRejected("original L0 rejected fresh World stimulus") from exc
    if l0.events != 0 or l0.action_requests != 0 or choice.action_authorized:
        raise BoundaryRejected("read-only L0 check unexpectedly consumed authority")
    comparison = compare_body_capability_l0_dev(
        body, prior_postwait_probe, handoff, p1_reviewed, profile, retained,
    )
    if (comparison["session_id"] != handoff.session_id
            or comparison["s42_selection_unchanged"] != choice.selection.value
            or comparison["new_action_grant_issued"] is not False):
        raise BoundaryRejected("fresh L0 and prior native P1 comparison disagree")
    return {
        "status": "DEV_REAL_NATIVE_POSTWAIT_FRESH_L0_INPUT_PAIRED",
        "session_id": handoff.session_id,
        "action_id": handoff.action_id,
        "world": handoff.world,
        "observer_run_id": handoff.observer_run_id,
        "paper_window_sha256": handoff.model_source_digest,
        "prior_native_seq": prior_postwait_probe.seq,
        "fresh_event_seq": event.seq,
        "fresh_probe_seq": probe.seq,
        "fresh_probe_request_id": probe.request_id,
        "fresh_zombie_entity_id": spawned[0].entity_id,
        "fresh_s42_selection": choice.selection.value,
        "fresh_s42_distance_m": choice.distance_m,
        "postwait_p1_sensor_pct_model_only": (
            body.hypothetical("p1-dev-distance-wait", "p1_sensor_pct").value
        ),
        "postwait_p1_capability_pct_model_only": (
            body.hypothetical("p1-dev-distance-wait", "p1_capability_pct").value
        ),
        "fresh_native_event_and_probe": True,
        "original_l0_input_checked": True,
        "original_l0_decide_called": False,
        "new_l0_owner_registered": False,
        "new_action_grant_issued": False,
        "new_action_issued": False,
        "extra_native_probes": 1,
        "extra_protocol_receivers": 0,
        "paper_native_tick_equivalence": False,
        "p1_model_attested": False,
        "qualification_go": False,
        "science_go": False,
    }
