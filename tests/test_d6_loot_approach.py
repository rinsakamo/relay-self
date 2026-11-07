"""D6-A native item -> bounded MOVE_BACKWARD read-only candidate negatives.

No additional physical MOVE, no S49 grant/issuer and no EAT.
"""
from __future__ import annotations

import math
from dataclasses import fields, replace

import pytest

import test_bug0_s49_food_refusal_priority as old
from adapters.mineflayer.d6_loot_approach import (
    D6LootApproachRejected,
    source_qualified_loot_approach,
)
from adapters.mineflayer.python_protocol import (
    MineflayerEntityFact,
    MineflayerNativeOrientation,
    MineflayerOrientedSnapshot,
    MineflayerPosition,
    MineflayerSnapshot,
)


def pair():
    original = old.sample(food=15, bread=0, zombie=False, seq=300)
    base = original.snapshot
    origin = base.position
    item = MineflayerEntityFact(
        entity_id=42, name="item", entity_type="other",
        position=MineflayerPosition(origin.x + 2.2, origin.y, origin.z),
        distance=2.2,
    )
    common = {
        f.name: getattr(base, f.name)
        for f in fields(MineflayerSnapshot)
    }
    common["nearby_entities"] = (item,)
    common["nearby_entities_coverage"] = replace(
        base.nearby_entities_coverage, candidate_count=1, truncated=False,
    )
    native_yaw = MineflayerNativeOrientation(
        source="mineflayer_bot_entity",
        yaw_rad=math.pi / 2, pitch_rad=0.0,
    )
    snapshot = MineflayerOrientedSnapshot(
        **common, native_orientation=native_yaw,
    )
    previous = replace(original, snapshot=snapshot, request_id="d6-item-before")
    current = replace(
        original, snapshot=snapshot, seq=301, request_id="d6-item-current",
    )
    return previous, current


def test_native_single_item_behind_bot_yields_readonly_back_candidate():
    a, b = pair()
    result = source_qualified_loot_approach(a, b, item_entity_id=42)
    assert result.session_id == a.session_id
    assert result.before_seq == 300 and result.decision_seq == 301
    assert result.native_source_ref == b.provenance.reference
    assert result.item_entity_id == 42
    assert result.candidate_action_ref == "MOVE_BACKWARD"
    assert result.candidate_control == "back"
    assert result.backward_direction_error_rad == pytest.approx(0.0, abs=1e-8)
    assert result.item_distance_m == pytest.approx(2.2, abs=1e-8)
    assert result.item_identity_verified_as_rotten_flesh is False
    assert result.authority_granted is False
    assert result.pickup_verified is False
    assert result.action_issued is False


@pytest.mark.parametrize("mutation", [
    "foreign_session", "same_request", "stale_source", "distant_source",
    "no_orientation", "wrong_yaw", "yaw_changed", "wrong_target_id",
    "replaced_item", "zombie", "extra_entity", "missing_item",
    "moving_item", "moving_self", "close_item", "far_item",
    "unhealthy", "no_air", "truncated",
])
def test_source_unqualified_never_mints_approach(mutation):
    a, b = pair()
    item = b.snapshot.nearby_entities[0]
    cov = b.snapshot.nearby_entities_coverage
    snap = b.snapshot
    if mutation == "foreign_session":
        b = replace(b, session_id="foreign")
    elif mutation == "same_request":
        b = replace(b, request_id=a.request_id)
    elif mutation == "stale_source":
        b = replace(b, seq=a.seq)
    elif mutation == "distant_source":
        b = replace(b, seq=a.seq + 33)
    elif mutation == "no_orientation":
        snap = MineflayerSnapshot(**{
            f.name: getattr(snap, f.name)
            for f in fields(MineflayerSnapshot)
        })
    elif mutation == "wrong_yaw":
        snap = replace(snap, native_orientation=replace(
            snap.native_orientation, yaw_rad=-math.pi / 2,
        ))
    elif mutation == "yaw_changed":
        snap = replace(snap, native_orientation=replace(
            snap.native_orientation, yaw_rad=math.pi / 2 + 0.7,
        ))
    elif mutation == "wrong_target_id":
        b = replace(b, snapshot=replace(
            snap, nearby_entities=(replace(item, entity_id=45),),
        ))
    elif mutation == "replaced_item":
        b = replace(b, snapshot=replace(
            snap, nearby_entities=(replace(item, entity_id=43),),
        ))
    elif mutation == "zombie":
        snap = replace(snap, nearby_entities=(replace(item, name="zombie"),))
    elif mutation == "extra_entity":
        snap = replace(snap, nearby_entities=(item, replace(item, entity_id=43)),
                       nearby_entities_coverage=replace(cov, candidate_count=2))
    elif mutation == "missing_item":
        snap = replace(snap, nearby_entities=(),
                       nearby_entities_coverage=replace(cov, candidate_count=0))
    elif mutation == "moving_item":
        snap = replace(snap, nearby_entities=(replace(
            item, position=replace(item.position, x=item.position.x + 0.4),
        ),))
    elif mutation == "moving_self":
        snap = replace(snap, position=replace(snap.position, x=snap.position.x + 0.1))
    elif mutation == "close_item":
        snap = replace(snap, nearby_entities=(replace(
            item, position=replace(item.position, x=snap.position.x + 0.7),
            distance=0.7,
        ),))
    elif mutation == "far_item":
        snap = replace(snap, nearby_entities=(replace(
            item, position=replace(item.position, x=snap.position.x + 5.0),
            distance=5.0,
        ),))
    elif mutation == "unhealthy":
        snap = replace(snap, health=0)
    elif mutation == "no_air":
        snap = replace(snap, oxygen_level=0)
    elif mutation == "truncated":
        snap = replace(
            snap,
            nearby_entities=tuple(
                replace(item, entity_id=100 + i)
                for i in range(cov.max_entities)
            ),
            nearby_entities_coverage=replace(
                cov, candidate_count=cov.max_entities + 1, truncated=True,
            ),
        )
    with pytest.raises(D6LootApproachRejected):
        source_qualified_loot_approach(a, replace(b, snapshot=snap), item_entity_id=42)


def test_reject_missing_or_bool_target_id():
    a, b = pair()
    for bad in (None, True, "42", -1, 43):
        with pytest.raises(D6LootApproachRejected):
            source_qualified_loot_approach(a, b, item_entity_id=bad)


def test_item_name_never_claimed_from_native_entity():
    a, b = pair()
    assert b.snapshot.nearby_entities[0].name == "item"
    candidate = source_qualified_loot_approach(a, b, item_entity_id=42)
    assert not candidate.item_identity_verified_as_rotten_flesh
    assert not candidate.pickup_verified
