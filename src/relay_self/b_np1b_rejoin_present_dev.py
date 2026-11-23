"""Original resident Present source for a qualified post-reJOIN Composite receipt.

CPU/offline only. This is the same original Owner, registered Schema and
ThreeSelf projection, not a second cognitive owner or an Action admission.
The Stage28 first-JOIN verifier remains unchanged and exclusively handles
its own historical source family.
"""
from __future__ import annotations

from dataclasses import dataclass

from relay_self.b_np1b_continuing_b_composite_dev import build_continuing_b_composite_source
from relay_self.b_np1b_current_composite_source_dev import CompositeSourceReceipt
from relay_self.b_np1b_initial_source_dev import InitialSourceReceipt
from relay_self.b_np1b_rejoin_composite_source_dev import (
    RejoinedCompositeSourceReceipt,
    build_rejoined_composite_source,
)
from relay_self.bd1b_owner_present_dev import _build_present
from relay_self.bd1b_owner_source_dev import BD1bOwnerSource
from relay_self.owned_resident_physical_bridge_dev import OwnedResidentPhysicalBridge


@dataclass(frozen=True, slots=True)
class RejoinedOwnerSource(BD1bOwnerSource):
    """Present-compatible source with the *whole* current composite proof."""

    composite_receipt: CompositeSourceReceipt


def build_rejoined_owner_source(
    *, bridge: OwnedResidentPhysicalBridge,
    self_id: str,
    initial_receipts: tuple[InitialSourceReceipt, ...],
    historical_composite: CompositeSourceReceipt,
) -> RejoinedOwnerSource:
    """Revalidate the original current Native/Paper source, never use the old source."""
    if (self_id not in ("A", "B") or not isinstance(bridge, OwnedResidentPhysicalBridge)
            or bridge.cognitive_work is None):
        raise ValueError("qualified original rejoined A / continuing B only")
    with bridge.cognitive_work.lock:
        if self_id == "A":
            receipt = build_rejoined_composite_source(
                bridge=bridge, initial_receipts=initial_receipts,
                historical_composite=historical_composite,
            )
            if type(receipt) is not RejoinedCompositeSourceReceipt:
                raise ValueError("original A reJOIN composite unavailable")
        else:
            receipt = build_continuing_b_composite_source(
                bridge=bridge, initial_receipts=initial_receipts,
                historical_composite=historical_composite,
            )
        if receipt.self_id != self_id:
            raise ValueError("foreign composite Self")
        # The original verifier binds A/B initial receipts and retained logout
        # to the original live Owner; B additionally requires a post-reJOIN
        # Paper PRESENT from the unchanged original B native session.
        original = next(
            r for r in initial_receipts
            if type(r) is InitialSourceReceipt and r.self_id == self_id
        )
        return RejoinedOwnerSource(
            self_id=receipt.self_id, world_id=receipt.world_id,
            branch_id=receipt.branch_id, world_epoch=receipt.world_epoch,
            paper_session_id=receipt.paper_session_id,
            paper_boot_id=receipt.paper_boot_id,
            presence_boot_id=original.presence_boot_id,
            paper_tick_source_ref=receipt.paper_tick_ref,
            paper_log_sha256=receipt.paper_log_sha256,
            paper_actor_uuid=receipt.paper_actor_uuid,
            resident_epoch=receipt.resident_epoch,
            native_session_id=receipt.native_session_id,
            native_probe_ref=receipt.native_request_id,
            native_probe_seq=receipt.native_sequence,
            native_probe_source_ref=receipt.native_source_ref,
            native_world_time_tick=receipt.native_world_time,
            composite_receipt=receipt,
        )


def build_rejoined_owner_present(
    *, bridge: OwnedResidentPhysicalBridge,
    self_id: str,
    initial_receipts: tuple[InitialSourceReceipt, ...],
    historical_composite: CompositeSourceReceipt,
):
    """Use the existing (Schema/Need/ThreeSelf) projector with a new owned source.

    The projector re-reads this composite after projecting. Its lock is the
    original resident lock, not an independent reJOIN or cognition lock.
    """
    def current_source_reader(*, bridge, boot, world, links, self_id):
        return build_rejoined_owner_source(
            bridge=bridge, self_id=self_id,
            initial_receipts=initial_receipts,
            historical_composite=historical_composite,
        )

    return _build_present(
        bridge=bridge, boot=None, world=None, links=None, self_id=self_id,
        source_reader=current_source_reader,
    )
