"""Read-only reconciliation of a registered bounded result with original sources.

The receipt conveys no authority to persist or consume a decision.
"""

from dataclasses import dataclass

from relay_self.bd1b_owner_source_dev import BD1bOwnerSource, BD1bSourceHold
from relay_self.bd1b_post_gpu_source_dev import verify_post_gpu_source
from relay_self.relay_engine import (
    CognitionMode,
    DecisionStatus,
    ProviderCallFacts,
    RelayEngine,
)
from relay_self.resident_llama_inference_lane_dev import (
    ResidentInferenceTicket,
    _request_sha256,
)


@dataclass(frozen=True, slots=True)
class IssuerReadback:
    self_id: str
    owner_scope: tuple[int, str, int]
    ticket: ResidentInferenceTicket
    work_ref: str
    request_id: str
    inquiry_ref: str
    source: BD1bOwnerSource
    candidate_set_sha256: str
    verified_submitted_request_sha256: str
    selection: str
    provider_status: DecisionStatus
    provider_choice_id: str | None
    provider_reason: str
    call_facts: ProviderCallFacts


def read_issuer_result(*, bridge, lane, boot, world, links, turn, ticket):
    """Read the actual terminal job, bracketed by current source verification."""
    resident = getattr(bridge, "cognitive_work", None)
    if resident is None or type(ticket) is not ResidentInferenceTicket:
        raise BD1bSourceHold("original resident and ticket required")
    with resident.lock:
        before = verify_post_gpu_source(
            bridge=bridge,
            lane=lane,
            boot=boot,
            world=world,
            links=links,
            turn=turn,
        )
        if (
            ticket.self_id != turn.self_id
            or ticket.work_ref != turn.work_ref
            or ticket.request_id != turn.request.request_id
            or ticket.mode is not CognitionMode.BOUNDED
            or (ticket.self_epoch, ticket.native_session_id, ticket.world_epoch) != turn.owner_scope
            or ticket.backend_ref != lane.backend_ref
            or before.source != turn.source
            or before.candidate_set_sha256 != turn.candidate_set_sha256
        ):
            raise BD1bSourceHold("ticket or source does not match prepared turn")
        with lane._lock:
            job = lane._require_current_job(ticket)
            if job.ticket is not ticket:
                raise BD1bSourceHold("original issued ticket required")
            decision = lane.verify_submitted_bounded_request(ticket, turn.request)
        digest = _request_sha256(turn.request, ticket.mode)
        # This provider returns only the already completed decision. No inference occurs.
        normalized = RelayEngine(lambda request, mode: decision)(turn.request)
        selection = {"1": "ADOPT", "2": "HOLD", "3": "DECLINE"}.get(
            normalized.choice_id, "UNRESOLVED"
        )
        after = verify_post_gpu_source(
            bridge=bridge,
            lane=lane,
            boot=boot,
            world=world,
            links=links,
            turn=turn,
        )
        if (
            before != after
            or after.source != turn.source
            or (after.candidate_set_sha256 != turn.candidate_set_sha256)
        ):
            raise BD1bSourceHold("source changed during result readback")
        return IssuerReadback(
            turn.self_id,
            turn.owner_scope,
            ticket,
            turn.work_ref,
            ticket.request_id,
            turn.inquiry.question_ref,
            after.source,
            after.candidate_set_sha256,
            digest,
            selection,
            decision.status,
            decision.choice_id,
            decision.reason,
            decision.call_facts,
        )
