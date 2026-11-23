"""R2-3f DEV: original R2-3e Question ADOPT -> original persistence, once.

Never accept a free-floating caller-supplied ADOPT or reconstruct a GPU job.
R2-3e must have issued and returned the exact original outcome, weakly held
by the ORIGINAL ResidentCognitiveWorkOwner. This module rechecks that
actual terminal job and uses the existing BD1b original Question storage
primitive; it does NOT create a new persistence format, cognition owner,
Skill/Target selector or physical issuer.
"""
from __future__ import annotations

import json
from dataclasses import dataclass

from relay_self.bd1b_question_store_dev import QuestionStoreHold, _store_current_inquiry
from relay_self.provenance import Provenance
from relay_self.r2_3c_original_rejoin_frozen_l1_dev import R23CFrozenOriginalRejoinL1
from relay_self.r2_3d_original_rejoin_gpu_fence_dev import (
    _source,
    read_r23d_original_rejoin_result_cpu,
)
from relay_self.r2_3e_original_rejoin_question_issuer_dev import (
    R23EOriginalRejoinQuestionOutcome,
)
from relay_self.resident_llama_inference_lane_dev import (
    ResidentInferenceTicket,
    ResidentLlamaInferenceLane,
)


class R23FOriginalRejoinCommitHold(RuntimeError):
    """Question decision not original, already used, or source not current."""


@dataclass(frozen=True, slots=True)
class R23FOriginalRejoinQuestionCommit:
    """Only the original Question was persisted; no Skill/Physical authority."""

    ticket: ResidentInferenceTicket
    selection: str
    question_ref: str
    question_adopted: bool
    persisted_continuity_revision: int | None
    intent_committed: bool = False
    memory_written: bool = False
    skill_issued: bool = False
    physical_issue_authorized: bool = False
    product_l1_input_switched: bool = False

    def __post_init__(self) -> None:
        if (
            type(self.ticket) is not ResidentInferenceTicket
            or self.selection not in ("ADOPT", "HOLD", "DECLINE", "UNRESOLVED")
            or not self.question_ref
            or (self.selection == "ADOPT") != self.question_adopted
            or (
                (type(self.persisted_continuity_revision) is int
                 and self.persisted_continuity_revision > 0)
                != self.question_adopted
            )
            or any((
                self.intent_committed, self.memory_written, self.skill_issued,
                self.physical_issue_authorized, self.product_l1_input_switched,
            ))
        ):
            raise R23FOriginalRejoinCommitHold(
                "only an original Question adoption receipt is supported"
            )


def commit_r23f_original_rejoin_question_dev(
    *, bridge, lane: ResidentLlamaInferenceLane,
    turn: R23CFrozenOriginalRejoinL1,
    outcome: R23EOriginalRejoinQuestionOutcome,
) -> R23FOriginalRejoinQuestionCommit:
    """Apply an authenticated original R2-3e ADOPT exactly once.

    The original resident lock brackets the readback and the complete
    original persistence transaction. Existing Question store performs
    before/after-disk revalidation. Any uncertain genuine ADOPT result
    fences *only* this Self and marks its original job failed; no retry.
    A foreign/copy outcome never gains access to the commit transaction.
    """
    if (
        type(turn) is not R23CFrozenOriginalRejoinL1
        or type(outcome) is not R23EOriginalRejoinQuestionOutcome
        or type(lane) is not ResidentLlamaInferenceLane
    ):
        raise R23FOriginalRejoinCommitHold(
            "typed original frozen turn, issuer outcome and lane required"
        )
    resident = getattr(bridge, "cognitive_work", None)
    if (
        resident is None
        or getattr(bridge, "inference_lane", None) is not lane
        or lane.cognitive_work is not resident
        or resident.owners.get(turn.self_id) is not turn.owner
        or bridge.owners.get(turn.self_id) is not turn.owner
    ):
        raise R23FOriginalRejoinCommitHold("original Owner/lane mismatch")

    with resident.lock, lane._lock:
        # This is *producer identity*, not caller-supplied equality. The
        # resident uses a weak map, so R2-3e's actual outcome must still be
        # strongly held by the caller during this original transaction.
        if (
            resident._coverage_adoption_turns.get(turn.work_ref) is not turn
            or resident._rejoin_question_outcomes.get(turn.work_ref) is not outcome
            or outcome.ticket is not outcome.readback.ticket
            or outcome.ticket.work_ref != turn.work_ref
            or outcome.ticket.self_id != turn.self_id
            or outcome.ticket.request_id != turn.request.request_id
        ):
            raise R23FOriginalRejoinCommitHold(
                "unregistered or substituted original issuer result"
            )
        ticket = outcome.ticket
        job = lane._require_current_job(ticket)
        if (
            job.ticket is not ticket
            or job.question_adoption_state != "unused"
            or job.question_adoption_binding is not None
            or job.result_adopted
        ):
            raise R23FOriginalRejoinCommitHold(
                "original Question job has already been consumed"
            )

        try:
            # The actual registered terminal provider result and the full
            # FIRST A-reJOIN/B-continuing original source, not the result
            # supplied by the caller, are the authority for the choice.
            current = read_r23d_original_rejoin_result_cpu(
                bridge=bridge, lane=lane, turn=turn, ticket=ticket,
            )
            if (
                current != outcome.readback
                or current.ticket is not ticket
                or current.preflight.owner is not turn.owner
                or current.preflight.source_pair_revision
                != turn.source.source_pair_revision
                or current.preflight.request_sha256 != turn.request_sha256
                or current.preflight.question_ref
                != turn.source.original_inquiry.question_ref
            ):
                raise R23FOriginalRejoinCommitHold(
                    "original issuer result and current Source disagree"
                )
            if current.selection != "ADOPT":
                # HOLD/DECLINE/UNRESOLVED: strictly read-only. The original
                # job remains terminal and cannot be resubmitted.
                return R23FOriginalRejoinQuestionCommit(
                    ticket=ticket,
                    selection=current.selection,
                    question_ref=current.preflight.question_ref,
                    question_adopted=False,
                    persisted_continuity_revision=None,
                )
            if (
                current.choice_id != "1"
                or current.decision_status.value != "resolved"
            ):
                raise R23FOriginalRejoinCommitHold(
                    "only completed original resolved ADOPT is storable"
                )

            owner = turn.owner
            continuity = owner.retained.exploration_continuity
            if continuity is not None and any(
                q.question_ref == turn.source.original_inquiry.question_ref
                for q in continuity.questions
            ):
                raise QuestionStoreHold("original Question already exists")

            # The existing Stage28 Question job single-use binding is reused,
            # not a separate issuer or persistence capability.
            binding = (
                ticket, turn.work_ref, current.submitted_request_sha256,
                turn.request_sha256, current.preflight.owner_scope,
            )
            job.question_adoption_binding = binding
            job.question_adoption_state = "committing"
            origin = Provenance("issuer-adopt", json.dumps({
                "work_ref": ticket.work_ref,
                "request_id": ticket.request_id,
                "choice_id": current.choice_id,
                "source_pair_revision": current.preflight.source_pair_revision,
            }, sort_keys=True, separators=(",", ":")))

            def revalidate() -> None:
                # Used both *before* writing and *after* disk readback.
                # Original owner.retained is unchanged until store succeeds.
                _, preflight = _source(bridge=bridge, lane=lane, turn=turn)
                if (
                    preflight != current.preflight
                    or resident._rejoin_question_outcomes.get(turn.work_ref)
                    is not outcome
                    or lane._require_current_job(ticket) is not job
                    or job.ticket is not ticket
                    or job.question_adoption_state != "committing"
                    or job.question_adoption_binding != binding
                    or job.result_adopted
                ):
                    raise QuestionStoreHold(
                        "original Question adoption Source/job changed"
                    )
                decision = lane.verify_submitted_bounded_request(
                    ticket, turn.request,
                )
                if (
                    decision.status != current.decision_status
                    or decision.choice_id != current.choice_id
                    or decision.reason != current.decision_reason
                    or decision.call_facts != current.call_facts
                ):
                    raise QuestionStoreHold("original provider result changed")

            _store_current_inquiry(
                resident, owner=owner, self_id=turn.self_id,
                inquiry=turn.source.original_inquiry,
                expected_revision=turn.continuity_revision,
                origin=origin,
                revalidate=revalidate,
            )
            job.question_adoption_state = "committed"
            return R23FOriginalRejoinQuestionCommit(
                ticket=ticket,
                selection="ADOPT",
                question_ref=turn.source.original_inquiry.question_ref,
                question_adopted=True,
                persisted_continuity_revision=turn.continuity_revision + 1,
            )
        except BaseException:
            # Failed original post-issuer source, store or disk readback
            # makes this completed job permanently unusable. A partially
            # written disk is NOT claimed rolled back; Original cognition
            # and this Self's GPU lane are closed until later recovery.
            job.question_adoption_state = "failed"
            lane.fence_self(turn.self_id)
            resident.fence_self(turn.self_id)
            raise
