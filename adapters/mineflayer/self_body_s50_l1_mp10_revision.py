"""MP10: typed SelfBody -> next L1 epoch model-error revision *proposal*.

Paper's 8 samples are PROVISIONAL and never native Present. A candidate is
eligible for *future* heldout evaluation only. No L0 change, model admission,
persistent learning, self-action, or source qualification.
"""
from __future__ import annotations

import hashlib
import json
import math
from dataclasses import asdict, dataclass

from adapters.mineflayer.self_body_s50_l1_mp9_selector import (
    MP9Rejected,
    ShadowTicket,
    SurfacePriors,
    train_mp8_only,
)
from adapters.mineflayer.self_body_s50_live_next_epoch import LiveNextEpochReadout
from relay_self.self_body import BodyOrigin, SelfBodyView


class MP10Rejected(ValueError):
    """Unqualified typed body, Paper window, model identity, or replay."""


@dataclass(frozen=True, slots=True)
class MotionRevisionProposal:
    session_id: str
    native_epoch_id: str
    native_observation_ref: str
    world_uuid: str
    action_id: str
    subject_uuid: str
    paper_prefix_sha256: str
    prior_ticket_sha256: str
    surface: str
    previous_slope: float
    proposed_slope: float
    observed_pair_count: int
    old_mae_m: float
    proposed_in_sample_mae_m: float
    trigger_threshold_m: float
    status: str
    revision_sha256: str
    classification: str = "NEXT_NATIVE_EPOCH_PROVISIONAL_PAPER_L1_SHADOW_ONLY"
    source_authority: str = "TYPED_NATIVE_BODY_WITH_PRIOR_PROVISIONAL_PAPER"
    future_heldout_mae_m: str = "NOT_OBSERVED"
    current_l0_action_modified: bool = False
    durable_learning_admissions: int = 0


def propose_from_typed_next_epoch(
    readout: LiveNextEpochReadout,
    ticket: ShadowTicket,
    prior: SurfacePriors,
    *, trigger_threshold_m: float = 0.002,
) -> MotionRevisionProposal:
    if (type(readout) is not LiveNextEpochReadout
            or type(ticket) is not ShadowTicket
            or type(prior) is not SurfacePriors
            or prior != train_mp8_only()):
        raise MP10Rejected("missing authentic typed next epoch and pinned MP8 model")
    body, world, window = readout.current_body, readout.current_world, readout.prior_window
    if (
        type(body) is not SelfBodyView
        or body.observation is None
        or world.self_body is not body
        or world.observation is None
        or body.self_id != world.self_id
        or body.session_id != window.session_id
        or readout.prior_action_id != window.action_id
        or ticket.world_uuid != window.paper_world_uuid
        or ticket.subject_uuid != window.subject_uuid
        or ticket.surface not in ("GRASS_BLOCK", "PACKED_ICE")
        or ticket.prior_source_sha1 != prior.source_sha1
        or ticket.world_uuid in prior.source_worlds
        or readout.learning_updates != 0 or readout.extra_actions != 0
        or readout.l0_choice_modified
        or readout.paper_source_finalized
        or readout.full_node_trace_qualified
        or not window.provisional or window.final_source_verified
        or window.node_trace_complete or window.goal_admitted
        or len(window.ticks) != 8
        or body.observed("position_x").origin is not BodyOrigin.OBSERVATION
        or body.observation.native_seq != world.observation.native_seq
        or body.observation.request_id != world.observation.request_id
        or body.observation.source_provenance != world.observation.provenance
        or type(trigger_threshold_m) is not float
        or not math.isfinite(trigger_threshold_m)
        or not 0 <= trigger_threshold_m <= 0.1
    ):
        raise MP10Rejected("typed SelfBody/Paper/source/epoch boundary invalid")
    # Use MP9 ticket digest verification without borrowing future samples.
    fields = dict(asdict(ticket))
    for k in ("ticket_sha256", "decision", "qualification"):
        fields.pop(k)
    digest = hashlib.sha256(
        json.dumps(fields, sort_keys=True, separators=(",", ":"), allow_nan=False)
        .encode()
    ).hexdigest()
    expected_slope = (
        prior.normal_slope if ticket.surface == "GRASS_BLOCK" else prior.ice_slope
    )
    if ticket.ticket_sha256 != digest or ticket.selected_slope != expected_slope:
        raise MP10Rejected("forged material selector or non-frozen prior")
    samples = window.ticks
    if (any(type(t.world_tick) is not int or
            type(t.displacement_m) is not float or
            not math.isfinite(t.displacement_m) or t.displacement_m < 0
            for t in samples)
            or any(b.world_tick != a.world_tick + 1
                   for a, b in zip(samples[:-1], samples[1:]))):
        raise MP10Rejected("missing consecutive real Paper sample types")
    motions = tuple(t.displacement_m for t in samples)
    xs, ys = motions[:-1], motions[1:]
    old = sum(abs(ticket.selected_slope*x - y) for x,y in zip(xs,ys)) / 7
    denominator = sum(x*x for x in xs)
    if denominator <= 1e-10:
        status = "ABSTAIN_INSUFFICIENT_MOTION"
        fitted = ticket.selected_slope
    elif old < trigger_threshold_m:
        status = "KEEP_NO_MATERIAL_ERROR"
        fitted = ticket.selected_slope
    else:
        slope = sum(x*y for x,y in zip(xs,ys)) / denominator
        if not math.isfinite(slope) or slope < 0 or slope > 2:
            status = "ABSTAIN_OUT_OF_MODEL_DOMAIN"
            fitted = ticket.selected_slope
        else:
            fitted = slope
            status = "REVISE_CANDIDATE_IN_SAMPLE_ONLY"
    in_sample = sum(abs(fitted*x-y) for x,y in zip(xs,ys))/7
    fields = {
        "session_id":window.session_id, "native_epoch_id":body.epoch_id,
        "native_observation_ref":body.observation.source_ref,
        "world_uuid":window.paper_world_uuid,
        "action_id":window.action_id,
        "subject_uuid":window.subject_uuid,
        "paper_prefix_sha256":window.paper_prefix_sha256,
        "prior_ticket_sha256":ticket.ticket_sha256,
        "surface":ticket.surface,
        "previous_slope":ticket.selected_slope, "proposed_slope":fitted,
        "observed_pair_count":7,
        "old_mae_m":old,
        "proposed_in_sample_mae_m":in_sample,
        "trigger_threshold_m":trigger_threshold_m,
        "status":status,
    }
    revision_sha = hashlib.sha256(
        json.dumps(fields, sort_keys=True, separators=(",", ":"), allow_nan=False)
        .encode()
    ).hexdigest()
    return MotionRevisionProposal(**fields, revision_sha256=revision_sha)
