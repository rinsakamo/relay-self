"""R2-3d: ORIGINAL first-reJOIN L1/GPU seam source fence (CPU DEV).

This is *not* a new issuer. It verifies the original R2-3c registered request
while the existing real ResidentLlamaInferenceLane is attached, and can read a
terminal ORIGINAL lane job without adopting the result. No submission, retry,
Question/Intent/Memory write, GPU task or physical Action originates here.
"""
from __future__ import annotations

from dataclasses import dataclass

from relay_self.r2_3c_original_rejoin_frozen_l1_dev import (
    R23CFrozenOriginalRejoinL1,
    R23COriginalRejoinL1Comparison,
    compare_r23c_registered_l1_context,
)
from relay_self.relay_engine import (
    CognitionMode,
    DecisionStatus,
    ProviderCallFacts,
    RelayEngine,
)
from relay_self.resident_llama_inference_lane_dev import (
    ResidentInferenceTicket,
    ResidentLlamaInferenceLane,
    _request_sha256,
)


class R23DOriginalRejoinSourceHold(RuntimeError):
    """Original request/lane/current source or completed job is unqualified."""


@dataclass(frozen=True, slots=True)
class R23DOriginalRejoinPreflight:
    """A CPU snapshot, not a GPU admission/reservation or prompt switch."""

    self_id: str
    owner: object
    request_id: str
    work_ref: str
    request_sha256: str
    candidate_ids: tuple[str, ...]
    question_ref: str
    need_signal_ref: str
    source_revision_refs: tuple[str, str, str]
    source_pair_revision: str
    owner_scope: tuple[int, str, int]
    backend_ref: str
    gpu_issued: bool = False
    product_l1_input_switched: bool = False
    memory_written: bool = False
    physical_issue_authorized: bool = False


@dataclass(frozen=True, slots=True)
class R23DOriginalRejoinResultReadback:
    """Read-only actual registered terminal lane decision; no adoption permit."""

    preflight: R23DOriginalRejoinPreflight
    ticket: ResidentInferenceTicket
    submitted_request_sha256: str
    selection: str
    decision_status: DecisionStatus
    choice_id: str | None
    decision_reason: str
    call_facts: ProviderCallFacts
    question_adopted: bool = False
    intent_committed: bool = False
    memory_written: bool = False
    physical_issue_authorized: bool = False
    product_l1_input_switched: bool = False


def _attached(*, bridge, lane, turn) -> object:
    resident = getattr(bridge, "cognitive_work", None)
    if (
        type(turn) is not R23CFrozenOriginalRejoinL1
        or type(lane) is not ResidentLlamaInferenceLane
        or resident is None
        or lane.cognitive_work is not resident
        or getattr(bridge, "inference_lane", None) is not lane
        or not getattr(bridge.physical, "observation_only", False)
        or bridge.physical.active_action_ids
        or getattr(bridge, "owners", {}).get(turn.self_id) is not turn.owner
        or resident.owners.get(turn.self_id) is not turn.owner
        or getattr(lane.witness, "backend_ref", None) != lane.backend_ref
    ):
        raise R23DOriginalRejoinSourceHold(
            "Original Owner and attached existing lane required"
        )
    return resident


def _source(*, bridge, lane, turn) -> tuple[R23COriginalRejoinL1Comparison, R23DOriginalRejoinPreflight]:
    resident = _attached(bridge=bridge, lane=lane, turn=turn)
    # Caller owns both Original RLock and lane._lock.
    before = compare_r23c_registered_l1_context(
        bridge=bridge, turn=turn, lane=lane,
    )
    scope = resident.current_scope(turn.self_id)
    if (
        scope != turn.cohort_scopes[("A", "B").index(turn.self_id)]
        or before.original_owner is not turn.owner
        or before.request_id != turn.request.request_id
        or before.request_sha256 != turn.request_sha256
        or before.source_revision_refs != turn.source.current.source_revision_refs
        or before.need_signal_ref != turn.source.original_inquiry.need_signal_ref
        or lane.uncertain
        or turn.self_id in lane._fenced
    ):
        raise R23DOriginalRejoinSourceHold("Original request/Scope/backend fenced")
    result = R23DOriginalRejoinPreflight(
        self_id=turn.self_id,
        owner=turn.owner,
        request_id=turn.request.request_id,
        work_ref=turn.work_ref,
        request_sha256=turn.request_sha256,
        candidate_ids=before.choice_ids,
        question_ref=before.question_ref,
        need_signal_ref=before.need_signal_ref,
        source_revision_refs=before.source_revision_refs,
        source_pair_revision=turn.source.source_pair_revision,
        owner_scope=scope,
        backend_ref=lane.backend_ref,
    )
    after = compare_r23c_registered_l1_context(
        bridge=bridge, turn=turn, lane=lane,
    )
    if after != before or resident.current_scope(turn.self_id) != scope:
        raise R23DOriginalRejoinSourceHold(
            "Source changed during attached original reJOIN CPU read"
        )
    return before, result


def preflight_r23d_original_rejoin_cpu(*, bridge, lane,
                                     turn: R23CFrozenOriginalRejoinL1
                                     ) -> R23DOriginalRejoinPreflight:
    """Read before submit; does not claim atomicity with any later submit.

    A future issuer MUST run this and lane.submit under the same original lock,
    then fence both per-Self owners after any uncertain submitted operation.
    """
    resident = _attached(bridge=bridge, lane=lane, turn=turn)
    try:
        with resident.lock, lane._lock:
            before, readout = _source(bridge=bridge, lane=lane, turn=turn)
            if (
                (turn.self_id, turn.work_ref) in lane._jobs
                or before.choice_ids != ("1", "2", "3")
                or before.question_ref != turn.source.original_inquiry.question_ref
            ):
                raise R23DOriginalRejoinSourceHold(
                    "work already submitted or original Question choices changed"
                )
            return readout
    except (RuntimeError, ValueError, TypeError, KeyError, AttributeError, OSError) as exc:
        raise R23DOriginalRejoinSourceHold(
            "pre-submit reJOIN Original Owner source HOLD"
        ) from exc


def read_r23d_original_rejoin_result_cpu(*, bridge, lane,
                                        turn: R23CFrozenOriginalRejoinL1,
                                        ticket: ResidentInferenceTicket
                                        ) -> R23DOriginalRejoinResultReadback:
    """Recheck current Source around original terminal job; never consume it.

    The lane must already contain an actually submitted bounded request.
    This module cannot create a ticket or call lane.submit. In tests, that
    existing lane is backed only by a CPU synthetic provider.
    """
    resident = _attached(bridge=bridge, lane=lane, turn=turn)
    try:
        with resident.lock, lane._lock:
            _, before = _source(bridge=bridge, lane=lane, turn=turn)
            if (
                type(ticket) is not ResidentInferenceTicket
                or ticket.self_id != turn.self_id
                or ticket.work_ref != turn.work_ref
                or ticket.request_id != turn.request.request_id
                or ticket.mode is not CognitionMode.BOUNDED
                or (ticket.self_epoch, ticket.native_session_id, ticket.world_epoch)
                != before.owner_scope
                or ticket.backend_ref != lane.backend_ref
                or ticket.action_issue_authorized
            ):
                raise R23DOriginalRejoinSourceHold(
                    "ticket is not the original prepared Question work"
                )
            job = lane._require_current_job(ticket)
            if (
                job.ticket is not ticket
                or job.request is not turn.request
                or job.question_adoption_state != "unused"
                or job.question_adoption_binding is not None
                or job.result_adopted
            ):
                raise R23DOriginalRejoinSourceHold(
                    "original issued job absent, altered or consumed"
                )
            decision = lane.verify_submitted_bounded_request(ticket, turn.request)
            actual_digest = _request_sha256(turn.request, ticket.mode)
            if (
                job.request_sha256 != actual_digest
                or job.request_sha256 != _request_sha256(job.request, ticket.mode)
            ):
                raise R23DOriginalRejoinSourceHold("submitted job hash mismatch")
            # Existing RelayEngine normalizes the *completed* provider response
            # only; this lambda cannot submit any new inference work.
            normalized = RelayEngine(lambda request, mode: decision)(turn.request)
            selection = {"1": "ADOPT", "2": "HOLD", "3": "DECLINE"}.get(
                normalized.choice_id, "UNRESOLVED"
            )
            reread_decision = lane.verify_submitted_bounded_request(
                ticket, turn.request,
            )
            _, after = _source(bridge=bridge, lane=lane, turn=turn)
            if (
                after != before or reread_decision != decision
                or lane._require_current_job(ticket) is not job
                or job.ticket is not ticket
                or job.question_adoption_state != "unused"
                or job.question_adoption_binding is not None
                or job.result_adopted
            ):
                raise R23DOriginalRejoinSourceHold(
                    "Source or terminal model readback changed during CPU check"
                )
            return R23DOriginalRejoinResultReadback(
                preflight=after,
                ticket=ticket,
                submitted_request_sha256=actual_digest,
                selection=selection,
                decision_status=decision.status,
                choice_id=decision.choice_id,
                decision_reason=decision.reason,
                call_facts=decision.call_facts,
            )
    except (RuntimeError, ValueError, TypeError, KeyError, AttributeError, OSError) as exc:
        raise R23DOriginalRejoinSourceHold(
            "original reJOIN terminal job/source CPU readback HOLD"
        ) from exc
