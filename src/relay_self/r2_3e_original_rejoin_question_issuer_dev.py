"""R2-3e DEV: one Original first-reJOIN bounded Question issuer.

This is an opt-in adapter over the ORIGINAL Resident Cognitive Owner and
its already attached ResidentLlamaInferenceLane. It never constructs a new
Owner, scheduler, GPU lane or request and does not adopt a Question, Memory,
Intent, Skill or Physical Action. Actual model HTTP / World qualification is
outside this synthetic CPU stage.

The preflight and admission of the ORIGINAL work ticket share the resident
RLock; waiting for the backend must occur OUTSIDE that lock. Any ambiguity
from an attempted submission fences the original lane and cognition of
that Self. It does not prove backend cancellation or restore World state.
"""
from __future__ import annotations

from dataclasses import dataclass

from relay_self.r2_3c_original_rejoin_frozen_l1_dev import (
    R23CFrozenOriginalRejoinL1,
)
from relay_self.r2_3d_original_rejoin_gpu_fence_dev import (
    R23DOriginalRejoinResultReadback,
    R23DOriginalRejoinSourceHold,
    preflight_r23d_original_rejoin_cpu,
    read_r23d_original_rejoin_result_cpu,
)
from relay_self.relay_engine import CognitionMode
from relay_self.resident_llama_inference_lane_dev import (
    ResidentInferenceTicket,
    ResidentLlamaInferenceLane,
)


class R23EOriginalRejoinIssueHold(RuntimeError):
    """Original reJOIN issuer unavailable before any submission."""


@dataclass(frozen=True, slots=True, weakref_slot=True)
class R23EOriginalRejoinQuestionOutcome:
    """One completed original job; no authority to persist/adopt a Question."""

    ticket: ResidentInferenceTicket
    readback: R23DOriginalRejoinResultReadback
    selection: str
    original_job_submitted: bool = True
    question_adopted: bool = False
    intent_committed: bool = False
    memory_written: bool = False
    skill_issued: bool = False
    physical_issue_authorized: bool = False
    product_l1_input_switched: bool = False

    def __post_init__(self) -> None:
        if (
            type(self.ticket) is not ResidentInferenceTicket
            or type(self.readback) is not R23DOriginalRejoinResultReadback
            or self.readback.ticket is not self.ticket
            or self.readback.preflight.work_ref != self.ticket.work_ref
            or self.readback.preflight.request_id != self.ticket.request_id
            or self.selection != self.readback.selection
            or self.selection not in ("ADOPT", "HOLD", "DECLINE", "UNRESOLVED")
            or self.original_job_submitted is not True
            or any((
                self.question_adopted,
                self.intent_committed,
                self.memory_written,
                self.skill_issued,
                self.physical_issue_authorized,
                self.product_l1_input_switched,
            ))
        ):
            raise R23EOriginalRejoinIssueHold(
                "original terminal Question result is not a commit or Action permit"
            )


async def issue_r23e_original_rejoin_question_once_dev(
    *, bridge, lane: ResidentLlamaInferenceLane,
    turn: R23CFrozenOriginalRejoinL1,
    timeout_s: float = 60.0,
) -> R23EOriginalRejoinQuestionOutcome:
    """Submit original registered reJOIN Question once; read, never consume.

    Fail closed before submission without fencing the other caller's existing
    ticket. Once lane.submit is ATTEMPTED, even a thrown/ambiguous submit,
    cancellation, timeout, stale Native/Paper/3Self Source or bad model result
    fences the original Self's GPU lane AND resident cognition under the
    existing Original Owner lock. No automatic replay and no adoption.
    """
    if type(timeout_s) not in (int, float) or not 0 < timeout_s <= 120:
        raise R23EOriginalRejoinIssueHold("bounded original model deadline required")
    if type(turn) is not R23CFrozenOriginalRejoinL1:
        raise R23EOriginalRejoinIssueHold("original frozen Question work required")
    if type(lane) is not ResidentLlamaInferenceLane:
        raise R23EOriginalRejoinIssueHold("original resident GPU lane required")
    resident = getattr(bridge, "cognitive_work", None)
    if (
        resident is None
        or getattr(bridge, "inference_lane", None) is not lane
        or lane.cognitive_work is not resident
        or resident.owners.get(turn.self_id) is not turn.owner
        or getattr(bridge, "owners", {}).get(turn.self_id) is not turn.owner
    ):
        raise R23EOriginalRejoinIssueHold(
            "original Owner, Bridge, lane and registered work must agree"
        )

    attempted_submit = False
    try:
        # Admission is guarded by the SAME Original Owner lock that guards
        # the full R2-3d source verification; no separate issuing Owner.
        with resident.lock:
            preflight = preflight_r23d_original_rejoin_cpu(
                bridge=bridge, lane=lane, turn=turn,
            )
            if (
                preflight.owner is not turn.owner
                or preflight.request_id != turn.request.request_id
                or preflight.work_ref != turn.work_ref
                or preflight.owner_scope != resident.current_scope(turn.self_id)
                or preflight.backend_ref != lane.backend_ref
            ):
                raise R23EOriginalRejoinIssueHold(
                    "original CPU preflight did not authorize registered request"
                )
            # Mark the boundary BEFORE submit. If the call raises after
            # enqueueing but before returning a ticket, admission is uncertain;
            # fail closed and fence only the attempting Self.
            attempted_submit = True
            ticket = lane.submit(
                turn.self_id,
                work_ref=turn.work_ref,
                request=turn.request,
                mode=CognitionMode.BOUNDED,
                # Reserve Question-only purpose in the same atomic lane
                # submit that creates the immutable ticket and job.
                purpose="original_rejoin_question",
            )

        # Do not wait for the single-slot worker under the Owner's RLock.
        # await_result shields the actual backend task from coroutine timeout.
        await lane.await_result(ticket, timeout_s=timeout_s)
        with resident.lock:
            readback = read_r23d_original_rejoin_result_cpu(
                bridge=bridge, lane=lane, turn=turn, ticket=ticket,
            )
            if (
                readback.preflight.request_id != preflight.request_id
                or readback.preflight.owner is not preflight.owner
                or readback.preflight.source_revision_refs
                != preflight.source_revision_refs
                or readback.preflight.source_pair_revision
                != preflight.source_pair_revision
                or readback.preflight.owner_scope != preflight.owner_scope
                or readback.submitted_request_sha256 == ""
                or readback.ticket is not ticket
            ):
                raise R23DOriginalRejoinSourceHold(
                    "original pre-submit and terminal Source mismatch"
                )
            outcome = R23EOriginalRejoinQuestionOutcome(
                ticket=ticket, readback=readback,
                selection=readback.selection,
            )
            if resident._rejoin_question_outcomes.get(turn.work_ref) is not None:
                raise R23EOriginalRejoinIssueHold(
                    "original reJOIN work already returned a decision"
                )
            resident._rejoin_question_outcomes[turn.work_ref] = outcome
            return outcome
    except BaseException:
        if attempted_submit:
            # This does NOT cancel llama-server. The existing lane tracks
            # unfinished work, and peer Self is not implicitly quarantined.
            with resident.lock:
                lane.fence_self(turn.self_id)
                resident.fence_self(turn.self_id)
        raise
