"""B0 one-item forage observation: no item-type oracle, food reward or Action owner."""
from __future__ import annotations

import math
from dataclasses import dataclass

from adapters.mineflayer.python_protocol import MineflayerObservation, MineflayerPosition
from relay_self.provenance import Provenance
from relay_self.seek_waypoint import SeekWaypoint


class GroundRejected(ValueError):
    """Native source cannot establish a unique bounded item or pickup."""


@dataclass(frozen=True, slots=True)
class GroundTarget:
    session_id: str
    probe_seq: int
    request_id: str
    entity_id: int
    position: MineflayerPosition
    provenance: Provenance

    def waypoint(self) -> SeekWaypoint:
        return SeekWaypoint(
            f"b0-item-{self.entity_id}", self.position,
            tolerance_m=0.6, max_step_m=1.0,
        )


@dataclass(frozen=True, slots=True)
class PickupContrast:
    session_id: str
    item_entity_id: int
    before_seq: int
    after_seq: int
    rotten_flesh_inventory_delta: int
    evidence_kind: str = "ITEM_DISAPPEARED_AND_INVENTORY_ROSE_ONLY"


def _count(read: MineflayerObservation) -> int:
    return sum(x.count for x in read.snapshot.inventory if x.name == "rotten_flesh")


def select_ground_target(read: MineflayerObservation) -> GroundTarget:
    """Choose exactly one visible item entity; its actual contents are UNKNOWN."""
    if (
        not isinstance(read, MineflayerObservation)
        or read.kind != "probe" or not read.request_id
        or read.provenance.source != "mineflayer"
        or read.snapshot.nearby_entities_coverage.truncated
        or read.snapshot.nearby_entities_coverage.candidate_count
        != len(read.snapshot.nearby_entities)
    ):
        raise GroundRejected("complete fresh native item probe required")
    items = [e for e in read.snapshot.nearby_entities if e.name == "item"]
    if len(items) != 1:
        raise GroundRejected("exactly one native item entity required")
    e = items[0]
    pos = read.snapshot.position
    actual = math.dist(
        (pos.x, pos.y, pos.z),
        (e.position.x, e.position.y, e.position.z),
    )
    if (
        not math.isclose(actual, e.distance, rel_tol=0, abs_tol=1e-6)
        or not 0.1 <= actual <= 16
        or abs(e.position.y - pos.y) > 1
        or _count(read) != 0
    ):
        raise GroundRejected("invalid geometry or already holding rotten flesh")
    return GroundTarget(
        read.session_id, read.seq, read.request_id,
        e.entity_id, e.position, read.provenance,
    )


def compare_pickup(
    before: MineflayerObservation,
    after: MineflayerObservation,
    target: GroundTarget,
) -> PickupContrast:
    """Correlated consistent change, *not* proof item was zombie rotten flesh."""
    if (
        not isinstance(before, MineflayerObservation)
        or not isinstance(after, MineflayerObservation)
        or not isinstance(target, GroundTarget)
        or before.kind != "probe" or after.kind != "probe"
        or before.session_id != target.session_id
        or after.session_id != target.session_id
        or before.seq != target.probe_seq
        or before.request_id != target.request_id
        or before.provenance != target.provenance
        or after.seq <= before.seq
        or not after.request_id
        or after.provenance.source != "mineflayer"
        or after.snapshot.nearby_entities_coverage.truncated
        or _count(before) != 0
        or _count(after) <= _count(before)
        or any(e.entity_id == target.entity_id for e in after.snapshot.nearby_entities)
    ):
        raise GroundRejected("ground pickup not established")
    return PickupContrast(
        target.session_id, target.entity_id, before.seq, after.seq,
        _count(after) - _count(before),
    )
