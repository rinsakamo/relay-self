"""Read-only proof of newly acquired rotten_flesh in one native SelfBody source.

This is not a Skill/Action issuer. A native inventory delta alone cannot prove
which World item caused it. Independent Paper item identity audit is separate.
"""
from __future__ import annotations

from dataclasses import dataclass

from adapters.mineflayer.python_protocol import MineflayerObservation


class LootPickupReadbackRejected(ValueError):
    """Native inventory delta not attributable to a fresh source window."""


@dataclass(frozen=True, slots=True)
class LootInventoryGain:
    session_id: str
    before_probe_seq: int
    after_probe_seq: int
    before_count: int
    after_count: int
    item_name: str
    before_source: str
    after_source: str
    outcome_scope: str = "NATIVE_INVENTORY_DELTA_ONLY"


def _count(read: MineflayerObservation, item_name: str) -> int:
    return sum(
        item.count for item in read.snapshot.inventory
        if item.name == item_name
    )


def read_rotten_flesh_gain(
    before: MineflayerObservation,
    after: MineflayerObservation,
) -> LootInventoryGain:
    """Require strictly ordered same-session real Mineflayer correlated probes.

    This reports an inventory fact, not a death, drop, playerCollect event,
    World-side loot ownership or permission to issue any Action.
    """
    if (
        not isinstance(before, MineflayerObservation)
        or not isinstance(after, MineflayerObservation)
        or before.kind != "probe" or after.kind != "probe"
        or not before.request_id or not after.request_id
        or before.request_id == after.request_id
        or before.session_id != after.session_id
        or before.provenance.source != "mineflayer"
        or after.provenance.source != "mineflayer"
        or before.seq >= after.seq
        or before.snapshot.health <= 0 or after.snapshot.health <= 0
    ):
        raise LootPickupReadbackRejected(
            "fresh alive native same-session inventory window required"
        )
    old = _count(before, "rotten_flesh")
    current = _count(after, "rotten_flesh")
    if current != old + 1:
        raise LootPickupReadbackRejected(
            "exactly one real rotten_flesh inventory addition required"
        )
    return LootInventoryGain(
        session_id=before.session_id,
        before_probe_seq=before.seq,
        after_probe_seq=after.seq,
        before_count=old,
        after_count=current,
        item_name="rotten_flesh",
        before_source=before.provenance.reference,
        after_source=after.provenance.reference,
    )
