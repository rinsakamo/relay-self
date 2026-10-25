"""One bounded REAL native L0 MOVE decision with DEV-only logical grant.

Only one actual S49 session's post-WAIT fresh entities event and matching
native probe are consumed by a separate, one-epoch L0 instance. The caller's
explicit DEV shadow grant is NOT an S49/S15 physical execution authorization.
Nothing may forward the returned request to an Action issuer.
"""
from __future__ import annotations

from adapters.mineflayer.m02_paper_dev.s50_boundary import BoundaryRejected
from adapters.mineflayer.normal_action import NormalWorldL0
from adapters.mineflayer.python_protocol import MineflayerObservation
from adapters.mineflayer.s49_p1_l0_fresh_pair_dev import (
    review_postwait_fresh_l0_input_dev,
)
from adapters.mineflayer.s49_p1_self_body_dev import P1DevSelfBodyHandoff
from experiments.fatigue_p1 import FatigueProfile
from relay_self.learning import LearningPreferenceState
from relay_self.reactive_l0 import L0ActionGrant, ReactiveL0Rejected
from relay_self.self_body import SelfBodyView


def decide_bounded_near_move_dev(
    event: MineflayerObservation,
    probe: MineflayerObservation,
    *,
    prior_postwait_probe: MineflayerObservation,
    body: SelfBodyView,
    handoff: P1DevSelfBodyHandoff,
    p1_reviewed: dict,
    profile: FatigueProfile,
    retained: LearningPreferenceState,
    operator_shadow_grant: L0ActionGrant,
) -> dict[str, object]:
    """Call existing L0.decide on true near native inputs, never execute.

    A real independent event/probe pair is required, but the only permission
    is an isolated DEV *logical* grant supplied independently by the caller.
    This is no S49 NormalActionAuthorization and cannot drive S15/S16.
    """
    checked = review_postwait_fresh_l0_input_dev(
        event, probe, prior_postwait_probe=prior_postwait_probe,
        body=body, handoff=handoff, p1_reviewed=p1_reviewed,
        profile=profile, retained=retained,
    )
    if (checked["fresh_s42_selection"] != "MOVE_AWAY"
            or checked["bounded_dev_shadow_l0_decide_called"] is not False
            or checked["bounded_dev_shadow_l0_events"] != 0
            or checked["new_action_issued"] is not False
            or checked["new_action_grant_issued"] is not False):
        raise BoundaryRejected("bounded near DEV decision requires fresh MOVE choice")
    if (not isinstance(operator_shadow_grant, L0ActionGrant)
            or operator_shadow_grant.authority_id != (
                f"dev-shadow-only:{handoff.session_id}:{event.seq}"
            )
            or operator_shadow_grant.action_id != (
                f"dev-shadow-no-dispatch:{handoff.session_id}:{event.seq}"
            )
            or operator_shadow_grant.intent_id != "escape-threat"
            or operator_shadow_grant.session_id != handoff.session_id
            or operator_shadow_grant.event_seq != event.seq
            or operator_shadow_grant.probe_seq != probe.seq
            or operator_shadow_grant.entity_id != checked["fresh_zombie_entity_id"]
            or operator_shadow_grant.granted is not True
            or operator_shadow_grant.provenance.source != (
                "dev-independent-shadow-only-not-s49-issuer"
            )):
        raise BoundaryRejected("independently provided scoped DEV shadow grant missing")
    try:
        shadow = NormalWorldL0(
            handoff.session_id, "escape-threat", retained,
            max_events=1, max_action_requests=1,
        )
        step = shadow.decide(event, probe, grant=operator_shadow_grant)
    except (ReactiveL0Rejected, ValueError, TypeError) as exc:
        raise BoundaryRejected("original near L0.decide failed closed") from exc
    if (step.choice.selection.value != "MOVE_AWAY"
            or not step.asks_for_action
            or step.action_request_id != operator_shadow_grant.action_id
            or step.grant is not operator_shadow_grant
            or shadow.events != 1 or shadow.action_requests != 1
            or step.choice.probe_seq != probe.seq):
        raise BoundaryRejected("bounded near L0 request/grant correlation invalid")
    return {
        "status": "DEV_REAL_NATIVE_BOUNDED_L0_MOVE_REQUEST_NO_EXECUTION",
        "session_id": handoff.session_id,
        "world": handoff.world,
        "action_id": handoff.action_id,
        "observer_run_id": handoff.observer_run_id,
        "paper_window_sha256": handoff.model_source_digest,
        "fresh_event_seq": event.seq,
        "fresh_probe_seq": probe.seq,
        "native_request_id": probe.request_id,
        "fresh_entity_id": checked["fresh_zombie_entity_id"],
        "original_s42_selection": step.choice.selection.value,
        "bounded_dev_l0_decide_called": True,
        "bounded_dev_l0_events": shadow.events,
        "bounded_dev_l0_action_requests": shadow.action_requests,
        "logical_shadow_action_id": step.action_request_id,
        "logical_dev_grant_source": operator_shadow_grant.provenance.source,
        "logical_dev_grant_used": True,
        "s49_execution_authorization_issued": False,
        "normal_action_executor_called": False,
        "physical_action_issued": False,
        "original_s49_l0_owner_replaced": False,
        "additional_native_receivers": 0,
        "additional_native_probes": 0,
        "p1_modeled_not_native": True,
        "p1_model_changes_s42_choice": False,
        "qualification_go": False,
        "science_go": False,
    }
