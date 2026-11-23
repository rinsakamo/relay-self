"""I0: one coherent, read-only original-resident CPU cognition readout.

This does not install an event loop or become a new Owner. B's qualified
Native/Paper sources and Owner remain authoritative for currentness.
"""
from __future__ import annotations

from dataclasses import dataclass

from relay_self.bd1b_coverage_inquiry_dev import (
    CoverageInquiryProposal,
    build_coverage_inquiry,
)
from relay_self.bd1b_owner_present_dev import BD1bOwnerPresent
from relay_self.resident_cognitive_work_owner_dev import ResidentCognitiveWorkOwner


class I0OwnerCPUHold(RuntimeError):
    """A coherent current original-owner readout could not be established."""


@dataclass(frozen=True, slots=True)
class I0OwnerCPUReadout:
    """Ephemeral Present + optional Question *proposal*, never an adoption."""

    present: BD1bOwnerPresent
    coverage_inquiry: CoverageInquiryProposal | None
    source_revision_refs: tuple[str, ...]
    action_issue_authorized: bool = False
    model_invoked: bool = False


def read_i0_owner_cpu(*, bridge, boot, world, links, self_id: str,
                      i1_complete_paper_prefix: bool = False,
                      i1_require_correlated_sense: bool = False) -> I0OwnerCPUReadout:
    """Bundle B's original Present and inquiry at one guarded source revision.

    All source checks and projections go through the original resident. A
    second Present read must still match after the inquiry is formed. Caller
    must revalidate before using the returned snapshot for *later* decisions.
    This entry does not admit a model task, write memory or choose an Action.
    """
    resident = getattr(bridge, "cognitive_work", None)
    if not isinstance(resident, ResidentCognitiveWorkOwner):
        raise I0OwnerCPUHold("original resident cognitive owner required")
    with resident.lock:
        before = resident.read_present_cpu(
            bridge=bridge, boot=boot, world=world, links=links, self_id=self_id,
            i1_complete_paper_prefix=i1_complete_paper_prefix,
            i1_require_correlated_sense=i1_require_correlated_sense,
        )
        inquiry = build_coverage_inquiry(
            bridge=bridge, boot=boot, world=world, links=links,
            self_id=self_id, readout=before,
            **({
                "i1_complete_paper_prefix": True,
                "i1_require_correlated_sense": i1_require_correlated_sense,
            } if i1_complete_paper_prefix else {}),
        )
        after = resident.read_present_cpu(
            bridge=bridge, boot=boot, world=world, links=links, self_id=self_id,
            i1_complete_paper_prefix=i1_complete_paper_prefix,
            i1_require_correlated_sense=i1_require_correlated_sense,
        )
        revisions = before.present.three_self.source_revision_refs
        if (
            before != after
            or before.source.self_id != self_id
            or before.present.three_self.scope.self_id != self_id
            or type(revisions) is not tuple
            or not revisions
            or (inquiry is not None and (
                inquiry.self_id != self_id
                or inquiry.source_revision_refs != revisions
                or before.exploration_need is None
                or inquiry.need_signal_ref != before.exploration_need.signal.envelope.event_id
            ))
        ):
            raise I0OwnerCPUHold("source or inquiry changed during CPU readout")
        return I0OwnerCPUReadout(before, inquiry, revisions)
