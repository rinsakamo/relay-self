"""One-shot original-owner bounded issuer path (DEV, not issuer attestation).

A prepared B+D turn exists BEFORE the original GPU lane is connected. This
adapter does not create a second owner, choose a model result, or issue an
Action/L2 request. Admission, result readback and commit reuse original locks.
"""
from dataclasses import dataclass

from relay_self.bd1b_adopt_commit_dev import commit_issuer_adoption
from relay_self.bd1b_issuer_readback_dev import IssuerReadback, read_issuer_result
from relay_self.bd1b_owner_source_dev import BD1bSourceHold
from relay_self.bd1b_post_gpu_source_dev import verify_post_gpu_source
from relay_self.relay_engine import CognitionMode
from relay_self.resident_llama_inference_lane_dev import ResidentInferenceTicket


@dataclass(frozen=True, slots=True)
class OriginalAdoptionOutcome:
    """A readback of the completed job, never a standalone authorization."""

    ticket: ResidentInferenceTicket
    readback: IssuerReadback
    selection: str


async def issue_original_adoption_once(*, bridge, lane, boot, world, links, turn,
                                       timeout_s: float = 60.0) -> OriginalAdoptionOutcome:
    """Submit a previously prepared turn to the existing resident L1 lane once.

    The worker thread must finish and the backend must be idle before the
    original Owner may recheck the entire Native/Paper/Schema/Request/Result
    source and decide whether to persist one OPEN Question.

    Any uncertainty *after submission* fences both original cognition and the
    lane for that Self. No forced ADOPT, no replay, no physical or L2 authority.
    """
    if type(timeout_s) not in (int, float) or not 0 < timeout_s <= 120:
        raise ValueError("bounded original issuer deadline required")
    resident = getattr(bridge, "cognitive_work", None)
    if resident is None:
        raise BD1bSourceHold("original resident required")
    # Keep pre-submission verification AND ticket registration under the same
    # existing Resident RLock. No inference thread wait is made under this lock.
    with resident.lock:
        verify_post_gpu_source(
            bridge=bridge, lane=lane, boot=boot, world=world, links=links, turn=turn,
        )
        ticket = lane.submit(
            turn.self_id, work_ref=turn.work_ref, request=turn.request,
            mode=CognitionMode.BOUNDED,
        )
    try:
        # await_result shields the actual worker: timing out does not prove that
        # llama-server stopped generating. Fence, never retry this work_ref.
        await lane.await_result(ticket, timeout_s=timeout_s)
        with resident.lock:
            receipt = read_issuer_result(
                bridge=bridge, lane=lane, boot=boot, world=world,
                links=links, turn=turn, ticket=ticket,
            )
            selection = commit_issuer_adoption(
                bridge=bridge, lane=lane, boot=boot, world=world,
                links=links, turn=turn, ticket=ticket,
            )
            if selection != receipt.selection:
                raise BD1bSourceHold("issuer readback disagrees with original commit")
            return OriginalAdoptionOutcome(ticket, receipt, selection)
    except BaseException:
        # Even if a completed result was returned, a changed source/readback
        # cannot become another choice or retry. Do not equate this fence with
        # backend termination, full physical quarantine, or crash durability.
        with resident.lock:
            lane.fence_self(turn.self_id)
            resident.fence_self(turn.self_id)
        raise
