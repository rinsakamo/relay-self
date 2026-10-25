"""DEV-only SelfWorld/Cognition companion to the one S49 post-WAIT probe.

Original S49 Action callback is the ONLY native JSONL receiver. This file
consumes a frame already received by that original owner; it never reads
another protocol message or issues an Action. The P1 quantity stays a model
hypothesis even though native health/food/position are now observable.
"""
from __future__ import annotations

from adapters.mineflayer.m02_paper_dev.s50_boundary import BoundaryRejected
from adapters.mineflayer.present_projection import project_mineflayer_present
from adapters.mineflayer.python_protocol import MineflayerObservation
from adapters.mineflayer.s49_p1_self_body_dev import MODEL
from adapters.mineflayer.self_body_projection import project_body_present
from adapters.mineflayer.self_world_projection import project_self_world_present
from relay_self.self_body import BodyOrigin, SelfBodyView
from relay_self.self_world import compose_self_world_view


def compose_postwait_native_self_world_dev(
    body: SelfBodyView,
    native: MineflayerObservation,
) -> dict[str, object]:
    """Join SelfWorld to same native Present + already validated SelfBody.

    The original owner must have provided a *later* correlated native probe
    and constructed the SelfBody with that observation first. Equality to
    the original typed native observation is checked again here.
    """
    if not isinstance(body, SelfBodyView) or not isinstance(
        native, MineflayerObservation
    ):
        raise BoundaryRejected("post-WAIT next epoch needs typed Body and native probe")
    if (body.observation is None or body.self_id is None
            or native.kind != "probe"
            or native.session_id != body.session_id
            or native.seq != body.observation.native_seq
            or native.request_id != body.observation.request_id
            or body.interoceptions
            or len(body.hypotheses) != 1
            or body.hypothetical(MODEL, "p1_phase").value != "after-wait"
            or body.hypothetical(MODEL, "p1_source_scope").value is None
            or body.sensed("p1_fatigue_sensor").origin is not BodyOrigin.UNKNOWN
            or body.observed("p1_fatigue").origin is not BodyOrigin.UNKNOWN):
        raise BoundaryRejected("post-WAIT Body did not keep P1 model distinct")
    present = project_mineflayer_present(native)
    if project_body_present(present) != body.observation:
        raise BoundaryRejected("post-WAIT native frame and Body observation mismatch")
    world = compose_self_world_view(
        session_id=body.session_id,
        self_id=body.self_id,
        epoch_id=body.epoch_id,
        observation=project_self_world_present(
            present, observer_id=body.self_id,
        ),
        self_body=body,
    )
    if (world.self_body is not body or world.observation is None
            or world.observation.provenance != body.observation.source_provenance
            or world.observation.native_seq != body.observation.native_seq
            or world.observation.request_id != body.observation.request_id):
        raise BoundaryRejected("SelfWorld and SelfBody next cognition epoch differ")
    return {
        "status": "DEV_NEXT_COGNITION_WORLD_BODY_SOURCE_JOINED",
        "session_id": body.session_id,
        "self_id": body.self_id,
        "epoch_id": body.epoch_id,
        "native_seq": present.seq,
        "native_request_id": present.request_id,
        "native_source_ref": body.observation.source_ref,
        "selfworld_native_source_ref": world.observation.source_ref,
        "world_entity_count": len(world.observation.entities),
        "world_coverage_truncated": world.observation.coverage_truncated,
        "world_body_same_epoch": world.epoch_id == body.epoch_id,
        "world_body_same_object": world.self_body is body,
        "p1_model_sensor_pct": body.hypothetical(
            MODEL, "p1_sensor_pct",
        ).value,
        "p1_source_kind": "SELF_BODY_HYPOTHESIS_NOT_NATIVE_OBSERVATION",
        "native_fatigue_observed": False,
        "p1_sensor_attested": False,
        "native_paper_exact_tick_joined": False,
        "extra_protocol_receivers": 0,
        "extra_action_issuers": 0,
        "next_l0_consumed": False,
        "qualification_go": False,
        "science_go": False,
    }
