"""D6-A: source-bound, read-only COLLECT_LOOT approach candidate.

Only an item entity's presence/position and actual Mineflayer yaw are sensed.
The item name is NOT disclosed by native entity geometry; native inventory
change and the independent Paper item UUID are separate later proofs.

No ActionSupervisor.issue, S15, movement, authority, Learning or EAT occurs here.
A physical D6 MOVE requires its OWN original S49 admission and pre-ISSUE fence.
"""
from __future__ import annotations

import math
from dataclasses import dataclass

from adapters.mineflayer.python_protocol import (
    MineflayerObservation,
    MineflayerOrientedSnapshot,
    mineflayer_yaw_to_target,
)


class D6LootApproachRejected(ValueError):
    """Insufficient actual native evidence for even a movement candidate."""


@dataclass(frozen=True, slots=True)
class D6LootApproach:
    session_id: str
    before_seq: int
    decision_seq: int
    decision_request_id: str
    native_source_ref: str
    item_entity_id: int
    item_distance_m: float
    target_x: float
    target_z: float
    original_native_yaw_rad: float
    backward_direction_error_rad: float
    candidate_action_ref: str = "MOVE_BACKWARD"
    candidate_control: str = "back"
    item_identity_verified_as_rotten_flesh: bool = False
    action_issued: bool = False
    authority_granted: bool = False
    pickup_verified: bool = False


def source_qualified_loot_approach(
    previous: MineflayerObservation,
    current: MineflayerObservation,
    *,
    item_entity_id: int,
    allow_experience_orbs: bool = False,
) -> D6LootApproach:
    """Select only a geometrically safe BACKWARD candidate toward one native item.

    The existing S15 action is 0.20s of backward control. This computes
    direction from a W4 opt-in *native orientation*, never assumes bot yaw.
    Even a valid readback does not authorize that S15 action.
    """
    if (
        not isinstance(previous, MineflayerObservation)
        or not isinstance(current, MineflayerObservation)
        or previous.kind != "probe" or current.kind != "probe"
        or not previous.request_id or not current.request_id
        or previous.request_id == current.request_id
        or previous.session_id != current.session_id
        or not previous.seq < current.seq <= previous.seq + 32
        or previous.provenance.source != "mineflayer"
        or current.provenance.source != "mineflayer"
        or previous.provenance.reference != f"{previous.session_id}:{previous.seq}"
        or current.provenance.reference != f"{current.session_id}:{current.seq}"
        or not isinstance(previous.snapshot, MineflayerOrientedSnapshot)
        or not isinstance(current.snapshot, MineflayerOrientedSnapshot)
        or type(item_entity_id) is not int or item_entity_id < 0
        or type(allow_experience_orbs) is not bool
        or current.snapshot.health <= 0
        or current.snapshot.oxygen_level == 0
    ):
        raise D6LootApproachRejected("fresh same-session native oriented probes required")
    for observation in (previous, current):
        coverage = observation.snapshot.nearby_entities_coverage
        entities = observation.snapshot.nearby_entities
        if coverage.truncated or coverage.candidate_count != len(entities):
            raise D6LootApproachRejected("complete native entity registry required")
        items = [e for e in entities if e.name == "item"]
        extras = [e for e in entities if e.name != "item"]
        # Real zombie death may spawn one or two vanilla XP orbs.
        # This scoped allowance is read-only, NOT proof of global safety;
        # any zombie, other entity, second item or truncated registry blocks.
        if (
            len(items) != 1 or items[0].entity_id != item_entity_id
            or (not allow_experience_orbs and extras)
            or (allow_experience_orbs and (
                len(extras) > 2
                or any(e.name not in ("experience_orb", "xp_orb") for e in extras)
            ))
        ):
            raise D6LootApproachRejected("one identical item and only allowed XP orbs required")
    pos0 = previous.snapshot.position
    pos1 = current.snapshot.position
    for axis in ("x", "y", "z"):
        if abs(getattr(pos1, axis) - getattr(pos0, axis)) > 0.05:
            raise D6LootApproachRejected("pre-ISSUE Self body not stationary")
    old = next(
        e for e in previous.snapshot.nearby_entities
        if e.name == "item"
    )
    target = next(
        e for e in current.snapshot.nearby_entities
        if e.name == "item"
    )
    if (
        abs(target.position.x - old.position.x) > 0.3
        or abs(target.position.z - old.position.z) > 0.3
        or abs(target.position.y - old.position.y) > 0.5
    ):
        raise D6LootApproachRejected("native item moved/disappeared across probes")
    horizontal = math.hypot(target.position.x - pos1.x, target.position.z - pos1.z)
    if (
        not 1.2 <= horizontal <= 4.0
        or not 1.2 <= target.distance <= 4.5
        or abs(target.distance - horizontal) > 0.8
        or abs(target.distance - old.distance) > 0.4
    ):
        raise D6LootApproachRejected("item not within bounded approach corridor")
    yaw = current.snapshot.native_orientation.yaw_rad
    prior_yaw = previous.snapshot.native_orientation.yaw_rad
    delta_yaw = math.atan2(math.sin(yaw - prior_yaw), math.cos(yaw - prior_yaw))
    target_yaw = mineflayer_yaw_to_target(pos1, target.position)
    back_yaw = yaw + math.pi
    error = math.atan2(math.sin(back_yaw - target_yaw),
                       math.cos(back_yaw - target_yaw))
    if abs(delta_yaw) > 0.2 or abs(error) > 0.40:
        raise D6LootApproachRejected("existing MOVE_BACKWARD is not directed toward item")
    return D6LootApproach(
        session_id=current.session_id,
        before_seq=previous.seq,
        decision_seq=current.seq,
        decision_request_id=current.request_id,
        native_source_ref=current.provenance.reference,
        item_entity_id=item_entity_id,
        item_distance_m=horizontal,
        target_x=target.position.x,
        target_z=target.position.z,
        original_native_yaw_rad=yaw,
        backward_direction_error_rad=error,
    )
