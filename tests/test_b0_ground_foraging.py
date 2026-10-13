"""Native-shaped B0 tests: evidence and near-target L0 only."""
from dataclasses import replace

import pytest

import test_feature_s46_eat as s46
from adapters.mineflayer.b0_ground_foraging import (
    GroundRejected,
    compare_pickup,
    select_ground_target,
)
from adapters.mineflayer.python_protocol import (
    MineflayerEntityFact,
    MineflayerInventoryItem,
    MineflayerPosition,
)


def _ground():
    p = s46.case()
    pos = p.snapshot.position
    e = MineflayerEntityFact(
        70, "item", "other", 2.5,
        MineflayerPosition(pos.x + 2.5, pos.y, pos.z),
    )
    coverage = replace(
        p.snapshot.nearby_entities_coverage,
        candidate_count=1, truncated=False,
    )
    return replace(p, snapshot=replace(
        p.snapshot, inventory=(), nearby_entities=(e,),
        nearby_entities_coverage=coverage,
    ))


def _after(before):
    return replace(
        before, seq=before.seq + 1, request_id="after-ground",
        snapshot=replace(
            before.snapshot, nearby_entities=(),
            nearby_entities_coverage=replace(
                before.snapshot.nearby_entities_coverage, candidate_count=0,
            ),
            inventory=(MineflayerInventoryItem("rotten_flesh", 1, 5),),
        ),
    )


def test_one_source_item_is_a_local_waypoint_not_known_food():
    p = _ground()
    x = select_ground_target(p)
    assert x.entity_id == 70
    assert x.waypoint().goal_id == "b0-item-70"
    z = compare_pickup(p, _after(p), x)
    assert z.rotten_flesh_inventory_delta == 1
    assert z.evidence_kind == "ITEM_DISAPPEARED_AND_INVENTORY_ROSE_ONLY"


def test_fail_closed_without_inventory_during_pickup():
    p = _ground()
    after = _after(p)
    with pytest.raises(GroundRejected):
        compare_pickup(p, replace(after, snapshot=replace(
            after.snapshot, inventory=(),
        )), select_ground_target(p))
    with pytest.raises(GroundRejected):
        compare_pickup(p, replace(after, seq=p.seq), select_ground_target(p))
    with pytest.raises(GroundRejected):
        compare_pickup(p, replace(after, snapshot=replace(
            after.snapshot,
            nearby_entities=p.snapshot.nearby_entities,
            nearby_entities_coverage=p.snapshot.nearby_entities_coverage,
        )), select_ground_target(p))


def test_no_item_ambiguous_item_incomplete_coverage_are_denied():
    p = _ground()
    empty = replace(p, snapshot=replace(
        p.snapshot, nearby_entities=(),
        nearby_entities_coverage=replace(
            p.snapshot.nearby_entities_coverage, candidate_count=0,
        ),
    ))
    with pytest.raises(GroundRejected):
        select_ground_target(empty)
    crowded = replace(p, snapshot=replace(
        p.snapshot, nearby_entities=p.snapshot.nearby_entities * 2,
        nearby_entities_coverage=replace(
            p.snapshot.nearby_entities_coverage, candidate_count=2,
        ),
    ))
    with pytest.raises(GroundRejected):
        select_ground_target(crowded)
    truncated = replace(p, snapshot=replace(
        p.snapshot,
        nearby_entities_coverage=replace(
            p.snapshot.nearby_entities_coverage,
            candidate_count=17, truncated=True,
        ),
    ))
    with pytest.raises(GroundRejected):
        select_ground_target(truncated)


def test_wrong_distance_and_unreachable_height_denied():
    p = _ground()
    e = p.snapshot.nearby_entities[0]
    wrong = replace(p, snapshot=replace(
        p.snapshot, nearby_entities=(replace(e, distance=0.5),),
    ))
    with pytest.raises(GroundRejected):
        select_ground_target(wrong)
    high = replace(e, position=replace(e.position, y=e.position.y + 2),
                   distance=(2.5**2 + 2**2) ** 0.5)
    wrong = replace(p, snapshot=replace(
        p.snapshot, nearby_entities=(high,),
    ))
    with pytest.raises(GroundRejected):
        select_ground_target(wrong)
