"""Native-shaped B0 tests: evidence and near-target L0 only."""
from dataclasses import replace

import pytest

import test_feature_s46_eat as s46
from adapters.mineflayer.b0_energy_bridge import B0EnergyLedger
from adapters.mineflayer.b0_ground_foraging import (
    GroundRejected,
    compare_pickup,
    select_ground_target,
)
from adapters.mineflayer.b0_ground_runner import (
    _admit_native_l0_seek,
    nonforcing_ground_decision,
)
from experiments.metabolism_viability import Interoception, MetabolismConfig
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
        nearby_entities=p.snapshot.nearby_entities * 16,
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


def test_native_ground_seek_requires_real_l0_selection_not_operator_override():
    from dataclasses import replace

    p = _ground()
    p = replace(p, snapshot=replace(p.snapshot, food=20.0))
    target = select_ground_target(p)
    ledger = B0EnergyLedger(p.session_id)
    # A full-food L0 does not choose SEEK. Operator may not force one.
    with pytest.raises(GroundRejected, match="L0 did not choose"):
        _admit_native_l0_seek(ledger, p, target)

    hungry = replace(p, seq=p.seq + 1, request_id="hungry-ground-native",
                     snapshot=replace(p.snapshot, food=13.0))
    admitted = _admit_native_l0_seek(ledger, hungry, target)
    assert admitted["l0_kind"] == "SEEK"
    assert admitted["entity_id"] == 70
    assert admitted["probe_seq"] == hungry.seq
    assert admitted["issued_action"] is False
    assert ledger.body.tick == 0 and ledger.credit_count == 0


def test_ground_seek_native_source_refuses_stale_or_foreign_target():
    from dataclasses import replace

    p = _ground()
    hungry = replace(p, snapshot=replace(p.snapshot, food=13.0))
    ledger = B0EnergyLedger(p.session_id)
    target = select_ground_target(hungry)
    _admit_native_l0_seek(ledger, hungry, target)
    with pytest.raises(Exception):
        _admit_native_l0_seek(ledger, hungry, target)

    next_probe = replace(hungry, seq=hungry.seq + 1, request_id="other-probe")
    with pytest.raises(GroundRejected, match="L0 did not choose"):
        _admit_native_l0_seek(ledger, next_probe, replace(target, entity_id=999))


def test_nonforcing_wait_then_seek_same_item_source_no_action():
    p = _ground()
    p = replace(p, snapshot=replace(p.snapshot, food=13.0))
    item = select_ground_target(p)
    ledger = B0EnergyLedger(p.session_id, forage_policy="sensor_gate")
    observed = []
    for i in range(9):
        read = replace(p, seq=p.seq + i, request_id=f"nonforcing-{i}")
        row = nonforcing_ground_decision(ledger, read, item)
        observed.append(row["kind"])
        assert row["issued_action"] is False
    assert observed == ["WAIT"] * 8 + ["SEEK"]
    assert ledger.body.energy == 8 and ledger.body.tick == 8
    assert ledger.credit_count == 0


def test_nonforcing_masked_wait_records_true_m0_terminal():
    p = _ground()
    p = replace(p, snapshot=replace(p.snapshot, food=13.0))
    item = select_ground_target(p)
    ledger = B0EnergyLedger(
        p.session_id, forage_policy="sensor_gate",
        sensor=Interoception(gain=0, bias=12),
        config=MetabolismConfig(initial_energy=2),
    )
    rows = []
    for i in range(4):
        read = replace(p, seq=p.seq + i, request_id=f"masked-{i}")
        rows.append(nonforcing_ground_decision(ledger, read, item))
    assert [r["kind"] for r in rows] == ["WAIT"] * 4
    assert [r["m0_energy_after"] for r in rows] == [1.5, 1, 0.5, 0]
    assert [r["m0_terminal_now"] for r in rows] == [False, False, False, True]
    assert ledger.body.terminal and ledger.credit_count == 0


def test_nonforcing_rejects_replay_or_entity_switch_without_extra_charge():
    p = _ground()
    p = replace(p, snapshot=replace(p.snapshot, food=13.0))
    item = select_ground_target(p)
    ledger = B0EnergyLedger(
        p.session_id, forage_policy="sensor_gate",
        sensor=Interoception(gain=0, bias=12),
    )
    nonforcing_ground_decision(ledger, p, item)
    with pytest.raises(Exception):
        nonforcing_ground_decision(ledger, p, item)
    swapped = replace(
        p, seq=p.seq + 1, request_id="switched",
        snapshot=replace(
            p.snapshot,
            nearby_entities=(replace(p.snapshot.nearby_entities[0], entity_id=72),),
        ),
    )
    with pytest.raises(GroundRejected, match="changed"):
        nonforcing_ground_decision(ledger, swapped, item)
    assert ledger.body.tick == 1 and ledger.body.energy == 11.5
