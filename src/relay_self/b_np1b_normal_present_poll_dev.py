"""Original Bridge CPU caller: read the current A/B Present after A reJOIN.

This is a bounded synchronous *poll* that the original Bridge can invoke.
It does not install an autonomous timer, GPU scheduler, L1/L2 requester, or
new cognitive owner. Historical inputs are pinned once, never trusted alone:
every poll fully re-reads current original Owner/Native/Paper sources.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass

from relay_self.b_np1b_continuing_b_composite_dev import ContinuingCompositeSourceReceipt
from relay_self.b_np1b_current_composite_source_dev import CompositeSourceReceipt
from relay_self.b_np1b_initial_source_dev import InitialSourceReceipt, _revision
from relay_self.b_np1b_rejoin_composite_source_dev import RejoinedCompositeSourceReceipt
from relay_self.bd1b_coverage_inquiry_dev import CoverageInquiryProposal
from relay_self.bd1b_owner_present_dev import BD1bOwnerPresent
from relay_self.owned_resident_physical_bridge_dev import OwnedResidentPhysicalBridge


class NormalPresentPollHold(RuntimeError):
    """Normal CPU read is not qualified from the current original sources."""


@dataclass(frozen=True, slots=True)
class _RejoinSourceCut:
    bridge: OwnedResidentPhysicalBridge
    initial_receipts: tuple[InitialSourceReceipt, ...]
    historical_composite: CompositeSourceReceipt


@dataclass(frozen=True, slots=True)
class NormalPresentCpuPoll:
    """A/B readout from one verified Paper cut; no cross-clock simultaneity or lease."""

    a_present: BD1bOwnerPresent
    b_present: BD1bOwnerPresent
    a_inquiry: CoverageInquiryProposal | None
    b_inquiry: CoverageInquiryProposal | None
    source_pair_revision: str


def _frames(resident, cut: _RejoinSourceCut) -> tuple[BD1bOwnerPresent, BD1bOwnerPresent]:
    result = tuple(
        resident.read_present_cpu(
            bridge=cut.bridge, self_id=sid,
            initial_receipts=cut.initial_receipts,
            historical_composite=cut.historical_composite,
        )
        for sid in ("A", "B")
    )
    a, b = result
    ra, rb = a.source.composite_receipt, b.source.composite_receipt
    if (
        type(ra) is not RejoinedCompositeSourceReceipt
        or type(rb) is not ContinuingCompositeSourceReceipt
        or ra.self_id != "A" or rb.self_id != "B"
        or ra.native_session_id == rb.native_session_id
        or ra.paper_actor_uuid == rb.paper_actor_uuid
        or ra.paper_session_id != rb.paper_session_id
        or ra.paper_log_sha256 != rb.paper_log_sha256
        or ra.paper_tick_ref != rb.paper_tick_ref
        or ra.paper_tick != rb.paper_tick
        or ra.world_id != rb.world_id
        or ra.branch_id != rb.branch_id
        or ra.world_epoch != rb.world_epoch
        or rb.a_rejoin_composite_ref != _revision(asdict(ra))
        or rb.b_continuity_revision != ra.b_continuity_revision
        or b.source.native_session_id != rb.native_session_id
        or a.source.native_session_id != ra.native_session_id
    ):
        raise NormalPresentPollHold("current original A/B sources do not share a Paper cut")
    return a, b


def bind_normal_rejoin_source_cpu(
    *, resident, bridge: OwnedResidentPhysicalBridge,
    initial_receipts: tuple[InitialSourceReceipt, ...],
    historical_composite: CompositeSourceReceipt,
) -> None:
    """Bind *original* source history after current A and B were requalified.

    No cached receipt is permitted to override a later logout, log change,
    session swap or native update. A changed scope yields HOLD on each poll.
    """
    if not isinstance(bridge, OwnedResidentPhysicalBridge) or resident is not bridge.cognitive_work:
        raise NormalPresentPollHold("original resident Bridge required")
    with resident.lock:
        if getattr(resident, "_normal_rejoin_source_cut", None) is not None:
            raise NormalPresentPollHold("original source cut already bound")
        if (
            type(initial_receipts) is not tuple
            or len(initial_receipts) != 2
            or any(type(x) is not InitialSourceReceipt for x in initial_receipts)
            or type(historical_composite) is not CompositeSourceReceipt
        ):
            raise NormalPresentPollHold("immutable original A/B history required")
        cut = _RejoinSourceCut(bridge, initial_receipts, historical_composite)
        try:
            _frames(resident, cut)
        except (ValueError, RuntimeError, KeyError, TypeError, AttributeError, OSError) as exc:
            raise NormalPresentPollHold("original A/B reJOIN history not current") from exc
        # No side effects except an immutable historical selector on the
        # existing original resident. Never cache a current source qualification.
        resident._normal_rejoin_source_cut = cut


def poll_normal_present_cpu(*, resident, bridge: OwnedResidentPhysicalBridge) -> NormalPresentCpuPoll:
    """Original caller uses the newest requalified A/B sources, not old receipts."""
    if not isinstance(bridge, OwnedResidentPhysicalBridge) or resident is not bridge.cognitive_work:
        raise NormalPresentPollHold("foreign resident Bridge")
    try:
        with resident.lock:
            cut = getattr(resident, "_normal_rejoin_source_cut", None)
            if type(cut) is not _RejoinSourceCut or cut.bridge is not bridge:
                raise NormalPresentPollHold("original source history not bound")
            a, b = _frames(resident, cut)
            inquiries = tuple(
                resident.read_coverage_inquiry_cpu(
                    bridge=bridge, self_id=sid,
                    initial_receipts=cut.initial_receipts,
                    historical_composite=cut.historical_composite,
                )
                for sid in ("A", "B")
            )
            # No Paper or Owner source may change while the pair is projected.
            if _frames(resident, cut) != (a, b):
                raise NormalPresentPollHold("A/B source changed during normal CPU poll")
            for sid, frame, inquiry in zip(("A", "B"), (a, b), inquiries):
                if inquiry is not None and (
                    inquiry.self_id != sid
                    or inquiry.source_revision_refs != frame.present.three_self.source_revision_refs
                    or inquiry.world_id != frame.source.world_id
                    or inquiry.resident_epoch != frame.source.resident_epoch
                ):
                    raise NormalPresentPollHold("inquiry is not bound to current Present")
            ref = _revision(dict(
                a_composite=a.source.composite_receipt.composite_revision,
                b_composite=b.source.composite_receipt.composite_revision,
                a_native=a.source.composite_receipt.native_revision,
                b_native=b.source.composite_receipt.native_revision,
                paper_sha256=a.source.paper_log_sha256,
            ))
            return NormalPresentCpuPoll(a, b, inquiries[0], inquiries[1], ref)
    except NormalPresentPollHold:
        raise
    except (ValueError, RuntimeError, KeyError, TypeError, AttributeError, OSError) as exc:
        raise NormalPresentPollHold("current normal CPU source unavailable") from exc
