"""One existing S49 owner, one later native probe, one DEV Cognition epoch.

The native probe follows the Paper WAIT window, but its protocol has NO
native mapping to the exact last Paper World tick. This bridge is read-only,
does not create L0 decisions/Action grants or P1 R-tick authentication.
"""
from __future__ import annotations

from adapters.mineflayer.m02_paper_dev.s50_boundary import BoundaryRejected
from adapters.mineflayer.present_projection import project_mineflayer_present
from adapters.mineflayer.python_protocol import MineflayerObservation
from adapters.mineflayer.s49_p1_self_body_dev import (
    MODEL,
    P1DevSelfBodyHandoff,
)
from adapters.mineflayer.self_body_projection import project_body_present
from adapters.mineflayer.self_world_projection import project_self_world_present
from relay_self.self_body import BodyOrigin, compose_self_body_view
from relay_self.self_world import compose_self_world_view


def compose_postwait_native_cognition_dev(
    handoff: P1DevSelfBodyHandoff,
    frame: MineflayerObservation,
    *,
    last_s49_action_after_seq: int,
    required_request_id: str,
    self_id: str = "RelaySelf",
) -> dict[str, object]:
    """Project a real *later* native probe plus fallible P1 Body hypothesis.

    Native SelfBody/World observations share exact source, epoch and instance;
    P1 only enters as a hypothesis from the completed Paper/model replay.
    A post-Paper native message cannot attest an exact Paper tick or full idle.
    """
    if not isinstance(handoff, P1DevSelfBodyHandoff) or not isinstance(
        frame, MineflayerObservation
    ):
        raise BoundaryRejected("typed P1 handoff and existing native protocol required")
    if (frame.kind != "probe"
            or type(last_s49_action_after_seq) is not int
            or last_s49_action_after_seq < 0
            or not isinstance(required_request_id, str)
            or not required_request_id.startswith("s49-postwait:")
            or not isinstance(self_id, str) or not self_id.strip()
            or frame.session_id != handoff.session_id
            or frame.seq <= last_s49_action_after_seq
            or frame.request_id != required_request_id
            or handoff.after_wait.session_id != frame.session_id
            or handoff.after_wait.observation is not None
            or handoff.after_wait.sensed("p1_fatigue_sensor").origin
            is not BodyOrigin.UNKNOWN):
        raise BoundaryRejected("post-WAIT native request/session/seq/owner mismatch")

    present = project_mineflayer_present(frame)
    if (present.provenance.source != "mineflayer"
            or present.provenance.reference
            != f"{handoff.session_id}:{present.seq}"
            or present.coverage_truncated
            or present.coverage_candidates < len(present.observed_entities)):
        raise BoundaryRejected("native post-WAIT probe source or coverage invalid")
    epoch = f"p1-dev-postwait-native-{present.seq}"
    obs = project_body_present(present)
    body = compose_self_body_view(
        session_id=present.session_id,
        epoch_id=epoch,
        self_id=self_id,
        observation=obs,
        minimum_native_seq=last_s49_action_after_seq + 1,
        # Existing SelfBody hypothesis: never forge a producer sensor.
        hypotheses=handoff.after_wait.hypotheses,
    )
    world = compose_self_world_view(
        session_id=present.session_id,
        epoch_id=epoch,
        self_id=self_id,
        observation=project_self_world_present(present, observer_id=self_id),
        self_body=body,
    )
    if (world.self_body is not body
            or world.observation is None
            or world.observation.native_seq != obs.native_seq
            or world.observation.provenance != obs.source_provenance
            or world.observation.request_id != obs.request_id
            or body.observed("health").origin is not BodyOrigin.OBSERVATION
            or body.sensed("p1_fatigue_sensor").origin is not BodyOrigin.UNKNOWN
            or body.observed("p1_fatigue").origin is not BodyOrigin.UNKNOWN
            or body.hypothetical(MODEL, "p1_sensor_pct").origin
            is not BodyOrigin.HYPOTHESIS):
        raise BoundaryRejected("post-WAIT SelfBody/SelfWorld epoch split or promotion")
    return {
        "classification": "DEV_NEXT_COGNITION_NATIVE_PROBE_WITH_P1_HYPOTHESIS",
        "session_id": handoff.session_id,
        "action_id": handoff.action_id,
        "observer_run_id": handoff.observer_run_id,
        "world": handoff.world,
        "paper_window_sha256": handoff.model_source_digest,
        "epoch_id": epoch,
        "native_request_id": present.request_id,
        "native_seq": present.seq,
        "native_source_ref": obs.source_ref,
        "native_source_provenance": {
            "source": present.provenance.source,
            "reference": present.provenance.reference,
        },
        "last_action_native_after_seq": last_s49_action_after_seq,
        "native_health": body.observed("health").value,
        "native_food": body.observed("food").value,
        "native_position": list(present.body_position),
        "native_visible_entities": len(world.observation.entities),
        "self_world_body_same_epoch": world.epoch_id == body.epoch_id,
        "self_world_body_same_object": world.self_body is body,
        "p1_model_fatigue_sensor_pct": body.hypothetical(
            MODEL, "p1_sensor_pct"
        ).value,
        "p1_model_capability_pct": body.hypothetical(
            MODEL, "p1_capability_pct"
        ).value,
        "p1_model_origin": "hypothesis",
        "native_p1_fatigue_observed": False,
        "p1_owner_sensor_attested": False,
        "native_postwait_paper_tick_exactly_correlated": False,
        "native_postwait_world_tick": None,
        "single_original_session_receiver": True,
        "postwait_native_probe_requests": 1,
        "additional_native_receivers": 0,
        "additional_action_issuers": 0,
        "actual_next_l0_decision_consumed": False,
        "qualification_go": False,
        "science_go": False,
    }
