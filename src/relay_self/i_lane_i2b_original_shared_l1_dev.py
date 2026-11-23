"""I2b DEV: source-bound exploration through the ORIGINAL shared B L1 lane.

Never rebootstrap a recovered Schema, install a Pattern, accept a Question,
commit Goal/Intent, persist a model result or authorize Physical Action.
The already-owned bridge must have attached the same ResidentLlamaInferenceLane.
All source hashes here are *local change detectors*, not authenticated receipts.
"""
from __future__ import annotations

import hashlib
from dataclasses import dataclass, field

from relay_self.i_lane_i2_original_exploration_handoff_dev import (
    I2OriginalGoalHandoff,
    I2OriginalGoalHold,
    verify_i2_original_goal_handoff,
)
from relay_self.relay_engine import (
    CognitionMode,
    DecisionStatus,
    ProviderDecision,
    RelayEngine,
)
from relay_self.resident_cognitive_work_owner_dev import ResidentCognitiveWorkOwner
from relay_self.resident_llama_inference_lane_dev import (
    ResidentInferenceTicket,
    ResidentLlamaInferenceLane,
)


class I2bSharedL1Hold(I2OriginalGoalHold):
    """Original shared L1 admission or result source has lost qualification."""


@dataclass(frozen=True, slots=True)
class I2bSharedL1Result:
    self_id: str
    request_id: str
    work_ref: str
    backend_ref: str
    request_sha256: str
    ticket: ResidentInferenceTicket
    selection_status: str
    model_invoked: bool = True
    question_adopted: bool = False
    goal_adopted: bool = False
    intent_committed: bool = False
    physical_action_authorized: bool = False


@dataclass(slots=True, eq=False)
class I2bSharedL1Submission:
    """Transient one-shot readback handle; NOT a second owner or durable ticket."""

    handoff: I2OriginalGoalHandoff
    ticket: ResidentInferenceTicket
    request_sha256: str
    work_ref: str
    consumed: bool = field(default=False, init=False)


def _request_sha(handoff: I2OriginalGoalHandoff) -> str:
    # A process-local frozen-request change detector, not a wire signature.
    return hashlib.sha256(repr(handoff.bounded_request).encode("utf-8")).hexdigest()


def _require_current(*, bridge, boot, world, links, handoff, lane) -> None:
    if (type(handoff) is not I2OriginalGoalHandoff
            or not isinstance(lane, ResidentLlamaInferenceLane)
            or getattr(bridge, "inference_lane", None) is not lane
            or getattr(bridge, "cognitive_work", None) is not lane.cognitive_work
            or handoff.status != "EXPLORATION_GOAL_UNRESOLVED_TARGET"
            or not handoff.goal_candidates or not handoff.need_signal_ref
            or not handoff.question_candidate_ref
            or handoff.model_invoked or handoff.goal_adopted
            or handoff.question_adopted or handoff.intent_committed
            or handoff.action_issue_authorized
            or handoff.bounded_request.think_allowed
            or tuple(c.description for c in handoff.bounded_request.choices)
            != ("ESCALATE_L2", "DEFER")
            or not bridge.physical.observation_only
            or bridge.physical.active_action_ids
            or lane.uncertain):
        raise I2bSharedL1Hold("qualified, nonmotor original shared L1 required")
    # The ordinary recovered Schema path must have *already* registered its
    # own valid snapshot. There is deliberately no implicit Schema activation.
    try:
        sid = handoff.self_id
        resident = bridge.cognitive_work
        scope = resident.current_scope(sid)
        schema = resident.present_schema(sid)
        owner = bridge.owners[sid]
        if (scope[0] != handoff.resident_epoch
                or scope[1] != handoff.native_session_id
                or schema.revision != handoff.registry_revision
                or owner.pattern_registry.revision != handoff.registry_revision
                or owner.supervisor.open_actions):
            raise I2bSharedL1Hold("restored Schema/Native/Owner scope stale")
        verify_i2_original_goal_handoff(
            bridge=bridge, boot=boot, world=world, links=links,
            handoff=handoff,
            i2b_read_attached_lane=True,
        )
    except (RuntimeError, ValueError, KeyError, AttributeError, TypeError) as exc:
        raise I2bSharedL1Hold("original B/E/Schema source no longer current") from exc


def _ticket_matches(submission: I2bSharedL1Submission, lane) -> bool:
    h = submission.handoff
    t = submission.ticket
    return (
        type(t) is ResidentInferenceTicket
        and t.self_id == h.self_id
        and t.request_id == h.bounded_request.request_id
        and t.work_ref == submission.work_ref
        and t.mode is CognitionMode.BOUNDED
        and t.backend_ref == lane.backend_ref
        and t.self_epoch == h.resident_epoch
        and t.native_session_id == h.native_session_id
        and t.action_issue_authorized is False
        and submission.request_sha256 == _request_sha(h)
    )


def submit_i2b_original_shared_l1(
    *, bridge, boot, world, links,
    handoff: I2OriginalGoalHandoff,
    lane: ResidentLlamaInferenceLane,
) -> I2bSharedL1Submission:
    """At most one real shared-lane submission for this frozen I2 request ID.

    The existing bridge must attach the lane before this call so logout can
    immediately fence in-flight work. A busy/uncertain slot is HOLD; no retry.
    """
    if (not isinstance(lane, ResidentLlamaInferenceLane)
            or not isinstance(lane.cognitive_work, ResidentCognitiveWorkOwner)):
        raise I2bSharedL1Hold("original shared lane/Owner required")
    with lane.cognitive_work.lock:
        _require_current(
            bridge=bridge, boot=boot, world=world, links=links,
            handoff=handoff, lane=lane,
        )
        # Serial lane lock and resident lock ensure another participating Self
        # cannot submit between the idle check and this ticket reservation.
        try:
            lane.require_world_idle()
        except (RuntimeError, ValueError, OSError) as exc:
            raise I2bSharedL1Hold("original shared GPU slot not idle") from exc
        _require_current(
            bridge=bridge, boot=boot, world=world, links=links,
            handoff=handoff, lane=lane,
        )
        work_ref = "i2b:" + handoff.bounded_request.request_id
        try:
            ticket = lane.submit(
                handoff.self_id, work_ref=work_ref,
                request=handoff.bounded_request, mode=CognitionMode.BOUNDED,
            )
        except (RuntimeError, ValueError) as exc:
            raise I2bSharedL1Hold("original shared L1 ticket not granted") from exc
        submission = I2bSharedL1Submission(
            handoff, ticket, _request_sha(handoff), work_ref,
        )
        if not _ticket_matches(submission, lane):
            # A bad ticket can never be a valid selection; no resubmission.
            raise I2bSharedL1Hold("issued original shared L1 ticket mismatch")
        return submission


def read_i2b_original_shared_l1_result(
    *, bridge, boot, world, links,
    submission: I2bSharedL1Submission,
    lane: ResidentLlamaInferenceLane,
) -> I2bSharedL1Result:
    """One-shot result readback; a numbered L1 choice never adopts cognition."""
    if (type(submission) is not I2bSharedL1Submission
            or not isinstance(lane, ResidentLlamaInferenceLane)):
        raise I2bSharedL1Hold("typed original submitted work required")
    with lane.cognitive_work.lock:
        if submission.consumed or not _ticket_matches(submission, lane):
            raise I2bSharedL1Hold("replayed or foreign L1 ticket/request")
        h = submission.handoff
        _require_current(
            bridge=bridge, boot=boot, world=world, links=links,
            handoff=h, lane=lane,
        )
        try:
            provider = lane.result(submission.ticket)
        except (RuntimeError, ValueError, KeyError) as exc:
            raise I2bSharedL1Hold("actual shared L1 result not terminal/current") from exc
        if type(provider) is not ProviderDecision:
            raise I2bSharedL1Hold("original L1 returned no bounded ProviderDecision")
        # Normalize the ALREADY obtained provider result. No second HTTP POST,
        # no implicit THINK escalation, no scripted choice substitution.
        decision = RelayEngine(
            lambda request, *, mode: provider,
        )(h.bounded_request)
        if decision.status is DecisionStatus.UNRESOLVED:
            selected = "UNRESOLVED"
        else:
            selected = dict(
                (choice.choice_id, choice.description)
                for choice in h.bounded_request.choices
            ).get(decision.choice_id, "UNRESOLVED")
        if selected not in ("ESCALATE_L2", "DEFER", "UNRESOLVED"):
            raise I2bSharedL1Hold("model response did not match frozen I2 choices")
        _require_current(
            bridge=bridge, boot=boot, world=world, links=links,
            handoff=h, lane=lane,
        )
        submission.consumed = True
        return I2bSharedL1Result(
            self_id=h.self_id, request_id=h.bounded_request.request_id,
            work_ref=submission.work_ref, backend_ref=submission.ticket.backend_ref,
            request_sha256=submission.request_sha256,
            ticket=submission.ticket, selection_status=selected,
        )


async def run_i2b_original_shared_l1(
    *, bridge, boot, world, links, handoff: I2OriginalGoalHandoff,
    lane: ResidentLlamaInferenceLane, timeout_s: float = 60.0,
) -> I2bSharedL1Result:
    """One original L1 provider call; timeout/retirement leaves explicit HOLD.

    A timeout does NOT cancel the provider thread or authorize a second try.
    """
    submitted = submit_i2b_original_shared_l1(
        bridge=bridge, boot=boot, world=world, links=links,
        handoff=handoff, lane=lane,
    )
    try:
        await lane.await_result(submitted.ticket, timeout_s=timeout_s)
    except (RuntimeError, ValueError, TimeoutError) as exc:
        raise I2bSharedL1Hold(
            "actual shared L1 result unresolved/timeout; no retry or adoption"
        ) from exc
    return read_i2b_original_shared_l1_result(
        bridge=bridge, boot=boot, world=world, links=links,
        submission=submitted, lane=lane,
    )
