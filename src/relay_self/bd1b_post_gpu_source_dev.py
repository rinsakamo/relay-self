"""Read-only CPU reconciliation after attaching the original GPU lane.

This is neither an issuer attestation nor authority to adopt or save a Question.
"""
from dataclasses import dataclass

from relay_self.bd1b_coverage_adoption_turn_dev import CoverageAdoptionTurn, _snapshot
from relay_self.bd1b_coverage_inquiry_dev import _build_inquiry
from relay_self.bd1b_owner_present_dev import _build_present
from relay_self.bd1b_owner_source_dev import BD1bOwnerSource, BD1bSourceHold, _build_source
from relay_self.owned_resident_physical_bridge_dev import OwnedResidentPhysicalBridge
from relay_self.resident_cognitive_work_owner_dev import ResidentCognitiveWorkOwner
from relay_self.resident_llama_inference_lane_dev import ResidentLlamaInferenceLane
from relay_self.stage28c2c_fresh_recovered_l1_dev import _require_original_sources


@dataclass(frozen=True, slots=True)
class PostGpuSourceReadout:
    source: BD1bOwnerSource
    candidate_set_sha256: str
    work_ref: str


def verify_post_gpu_source(*, bridge, lane, boot, world, links, turn):
    """Rebuild current sources and the prepared turn under the resident lock."""
    if (not isinstance(bridge, OwnedResidentPhysicalBridge)
            or not isinstance(bridge.cognitive_work, ResidentCognitiveWorkOwner)
            or not isinstance(lane, ResidentLlamaInferenceLane)
            or type(turn) is not CoverageAdoptionTurn):
        raise BD1bSourceHold("original bridge, resident, lane and turn required")
    resident = bridge.cognitive_work
    with resident.lock:
        def require_original(*, bridge, sid, boot, world):
            if (bridge.cognitive_work is not resident or bridge.inference_lane is not lane
                    or lane.cognitive_work is not resident):
                raise BD1bSourceHold("connected original lane required")
            for who in ("A", "B"):
                resident.current_scope(who)
                resident.owners[who]._eligible()
            return _require_original_sources(bridge=bridge, sid=sid, boot=boot, world=world)

        def source_reader(**kw):
            return _build_source(**kw, require_original=require_original)

        def present_reader(**kw):
            return _build_present(**kw, source_reader=source_reader)

        def inquiry_reader(**kw):
            present = present_reader(**kw)
            return _build_inquiry(**kw, readout=present, present_reader=present_reader)

        try:
            if resident._coverage_adoption_turns.get(turn.work_ref) is not turn:
                raise BD1bSourceHold("unregistered prepared turn")
            owner, scope, rev, inquiry, source, probe, request, digest = _snapshot(
                bridge=bridge, boot=boot, world=world, links=links, self_id=turn.self_id,
                request_id=turn.request.request_id, present_reader=present_reader,
                inquiry_reader=inquiry_reader,
            )
            if (owner is not turn.owner or owner.intent is not turn.intent_owner
                    or owner.intent.events != turn.intent_events or scope != turn.owner_scope
                    or any(resident.owners[sid] is not turn.cohort_owners[i]
                           or resident.current_scope(sid) != turn.cohort_scopes[i]
                           or resident.owners[sid].current_worldbody_observation is not turn.cohort_probes[i]
                           for i, sid in enumerate(("A", "B")))
                    or rev != turn.continuity_revision or inquiry != turn.inquiry
                    or source != turn.source or probe is not turn.original_probe
                    or request != turn.request or digest != turn.candidate_set_sha256
                    or not turn.work_ref.startswith("coverage-adoption-work-")):
                raise BD1bSourceHold("prepared turn changed or stale")
            return PostGpuSourceReadout(source, digest, turn.work_ref)
        except BD1bSourceHold:
            raise
        except (ValueError, RuntimeError, KeyError, AttributeError, TypeError, OSError) as exc:
            raise BD1bSourceHold("post-GPU original source unavailable or stale") from exc
