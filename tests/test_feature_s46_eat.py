"""S46 EAT candidates and actual receipt adjudication; no physical run."""
from __future__ import annotations

from dataclasses import replace

import pytest

import test_postmain_s42_world_contrast as s42
from adapters.mineflayer.python_protocol import (
    MineflayerEffectResult,
    MineflayerInventoryItem,
)
from relay_self.eat_hunger import (
    EatCursor,
    EatRejected,
    EatStatus,
    verify_eating_effect,
)


def case():
    _, near, _, _, _ = s42._pair()
    probe = near.observation
    probe = replace(
        probe, snapshot=replace(
            probe.snapshot, food=7.0,
            inventory=(MineflayerInventoryItem("bread", 2, 4),),
        ),
    )
    return probe


def test_eat_choice_depends_on_fresh_hunger_and_known_food():
    p = case()
    c = EatCursor(p.session_id)
    x = c.choose(p)
    assert x.status is EatStatus.CANDIDATE and x.item_name == "bread"
    with pytest.raises(EatRejected):
        c.choose(p)
    no_food = replace(p, snapshot=replace(p.snapshot, inventory=()))
    assert EatCursor(p.session_id).choose(no_food).status is EatStatus.NO_FOOD
    fed = replace(p, snapshot=replace(p.snapshot, food=19))
    assert EatCursor(p.session_id).choose(fed).status is EatStatus.NOT_HUNGRY


def test_measured_eating_requires_applied_equip_consume_and_food_inventory_delta():
    p = case()
    choice = EatCursor(p.session_id).choose(p)
    equip = MineflayerEffectResult(p.session_id, p.seq + 1, "eat-1", "equip_item", "applied", None)
    consume = MineflayerEffectResult(p.session_id, p.seq + 2, "eat-1", "consume_held", "applied", None)
    after = replace(
        p, seq=p.seq + 3, request_id="after-eating-probe",
        snapshot=replace(
            p.snapshot, food=12, inventory=(MineflayerInventoryItem("bread", 1, 4),),
        ),
    )
    result = verify_eating_effect(choice, p, equip, consume, after)
    assert result.food_after == 12 and result.count_after == 1
    with pytest.raises(EatRejected):
        verify_eating_effect(
            choice, p, equip, consume,
            replace(after, snapshot=replace(after.snapshot, food=7)),
        )
    with pytest.raises(EatRejected):
        verify_eating_effect(choice, p, replace(equip, result="rejected", error="denied"), consume, after)
