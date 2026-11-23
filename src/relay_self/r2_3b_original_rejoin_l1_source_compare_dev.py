"""R2-3b: read-only ORIGINAL first-reJOIN Inquiry ↔ 3Self CURRENT seam.

Original post-reJOIN CPU polling creates Present and CoverageInquiryProposal,
NOT a registered BoundedChoiceRequest. This module cannot manufacture a
post-reJOIN L1 request, choices, target bindings, ticket or authority.
"""
from __future__ import annotations

from dataclasses import dataclass

from relay_self.b_np1b_normal_present_poll_dev import (
    NormalPresentCpuPoll,
    _RejoinSourceCut,
)
from relay_self.bd1b_coverage_inquiry_dev import CoverageInquiryProposal
from relay_self.r2_3_rejoin_composite_context_dev import (
    R23RejoinedContextComparison,
    R23RejoinedCurrent,
    r23_rejoined_context_is_live,
)


class R23BOriginalL1SourceHold(RuntimeError):
    """The existing reJOIN Inquiry/CURRENT is absent, foreign, or stale."""


@dataclass(frozen=True, slots=True)
class R23BOriginalL1SourceComparison:
    """Diagnostic only: post-reJOIN L1 Request is NOT registered yet."""

    self_id: str
    original_owner: object
    original_inquiry: CoverageInquiryProposal
    current: R23RejoinedCurrent
    source_pair_revision: str
    original_l1_request_id: None = None
    original_choice_ids: tuple[()] = ()
    l1_request_registered: bool = False
    model_invoked: bool = False
    l1_input_switched: bool = False
    intent_committed: bool = False
    memory_written: bool = False
    physical_action_issued: bool = False

    def __post_init__(self) -> None:
        if (
            self.self_id not in ("A", "B")
            or type(self.original_inquiry) is not CoverageInquiryProposal
            or type(self.current) is not R23RejoinedCurrent
            or self.current.self_id != self.self_id
            or self.original_inquiry.self_id != self.self_id
            or self.original_inquiry.source_revision_refs
            != self.current.source_revision_refs
            or self.original_inquiry.schema_revision != self.current.schema.revision
            or self.original_inquiry.resident_epoch != self.current.owner_epoch
            or self.original_inquiry.need_signal_ref not in self.current.need_refs
            or not self.source_pair_revision
            or self.original_l1_request_id is not None
            or self.original_choice_ids != ()
            or any((
                self.l1_request_registered, self.model_invoked,
                self.l1_input_switched, self.intent_committed,
                self.memory_written, self.physical_action_issued,
            ))
        ):
            raise R23BOriginalL1SourceHold(
                "Inquiry-only compatibility is not a registered L1 request"
            )


def compare_r23b_original_rejoin_inquiry_context(
    *, bridge, self_id: str,
) -> R23BOriginalL1SourceComparison:
    """Compare *already registered* original first-reJOIN source cut.

    Do not bind a source cut, prepare a CoverageAdoptionTurn, register an L1
    request or invoke any GPU, Memory, Intent, Skill, Physical or WAL method.
    A/B are sampled by the existing original paired CPU poll under its lock.
    """
    resident = getattr(bridge, "cognitive_work", None)
    owners = getattr(bridge, "owners", None)
    if (
        type(self_id) is not str or self_id not in ("A", "B")
        or resident is None or not isinstance(owners, dict)
        or not isinstance(getattr(resident, "owners", None), dict)
        or owners.get(self_id) is None
        or resident.owners.get(self_id) is not owners[self_id]
    ):
        raise R23BOriginalL1SourceHold("original resident A/B Owner required")
    with resident.lock:
        try:
            cut = getattr(resident, "_normal_rejoin_source_cut", None)
            if (
                type(cut) is not _RejoinSourceCut or cut.bridge is not bridge
                or getattr(resident, "_normal_second_rejoin_cut", None) is not None
            ):
                raise R23BOriginalL1SourceHold(
                    "first reJOIN original A/B source cut not registered"
                )
            before = resident.poll_normal_present_cpu(bridge=bridge)
            if type(before) is not NormalPresentCpuPoll:
                raise R23BOriginalL1SourceHold("original paired CPU poll required")
            present = before.a_present if self_id == "A" else before.b_present
            inquiry = before.a_inquiry if self_id == "A" else before.b_inquiry
            owner = owners[self_id]
            probe = owner.current_worldbody_observation
            intent_events = owner.intent.events
            retained = owner.retained
            read = resident.read_rejoined_context_shadow_cpu(
                bridge=bridge, self_id=self_id,
                initial_receipts=cut.initial_receipts,
                historical_composite=cut.historical_composite,
            )
            if type(read) is not R23RejoinedContextComparison:
                raise R23BOriginalL1SourceHold("original R2-3a comparison absent")
            current = read.current
            if (
                type(inquiry) is not CoverageInquiryProposal
                or read.original_owner is not owner
                or current.source != present.source
                or current.schema != present.schema
                or current.signals != present.present.signals
                or current.source_revision_refs
                != present.present.three_self.source_revision_refs
                or current.need_refs != present.present.need_refs
                or current.attention_refs != present.present.attention_refs
                or present.exploration_need is None
                or current.need_refs != (inquiry.need_signal_ref,)
                or present.exploration_need.signal.envelope.event_id
                != inquiry.need_signal_ref
                or inquiry.source_revision_refs != current.source_revision_refs
                or inquiry.schema_revision != current.schema.revision
                or inquiry.world_id != current.source.world_id
                or inquiry.branch_id != current.source.branch_id
                or inquiry.world_epoch != current.source.world_epoch
                or inquiry.resident_epoch != current.owner_epoch
                or inquiry.coverage_claim_ref
                != present.exploration_need.basis[0].present_ref
                or resident.current_scope(self_id) != (
                    current.owner_epoch, current.source.native_session_id,
                    current.source.world_epoch,
                )
                or owner.intent.events != intent_events
                or owner.retained is not retained
            ):
                raise R23BOriginalL1SourceHold(
                    "original reJOIN Inquiry/Need/Source not matched to 3Self CURRENT"
                )
            # Paper changes outside this lock. Require independent original
            # A/B re-poll and original tri-source requalification at return.
            if (
                resident.poll_normal_present_cpu(bridge=bridge) != before
                or not r23_rejoined_context_is_live(
                    read, bridge=bridge,
                    initial_receipts=cut.initial_receipts,
                    historical_composite=cut.historical_composite,
                )
                or owners.get(self_id) is not owner
                or resident.owners.get(self_id) is not owner
                or owner.current_worldbody_observation is not probe
                or owner.intent.events != intent_events
                or owner.retained is not retained
            ):
                raise R23BOriginalL1SourceHold(
                    "original reJOIN cut or Owner changed during read"
                )
            return R23BOriginalL1SourceComparison(
                self_id, owner, inquiry, current, before.source_pair_revision,
            )
        except (RuntimeError, ValueError, TypeError, KeyError, AttributeError, OSError) as exc:
            raise R23BOriginalL1SourceHold(
                "original post-reJOIN L1 source compatibility HOLD"
            ) from exc


def r23b_original_rejoin_inquiry_is_live(
    report: R23BOriginalL1SourceComparison, *, bridge,
) -> bool:
    """A cached diagnostic is never a GPU/L1/Intent/Physical admission."""
    if type(report) is not R23BOriginalL1SourceComparison:
        return False
    try:
        fresh = compare_r23b_original_rejoin_inquiry_context(
            bridge=bridge, self_id=report.self_id,
        )
        return fresh == report and fresh.original_owner is report.original_owner
    except (RuntimeError, ValueError, TypeError, KeyError, AttributeError, OSError):
        return False
