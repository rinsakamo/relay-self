"""S51 EAT transport refuses unauthorized or replayable Action inputs."""
import asyncio
from dataclasses import replace

import pytest

import test_feature_s46_eat as s46
from adapters.mineflayer.eat_execution import (
    EatingExecutionRejected,
    IssuedEatingExecutor,
    verify_eating_subactions,
)
from adapters.mineflayer.python_protocol import (
    MineflayerEffectResult,
    MineflayerInventoryItem,
)
from relay_self.eat_hunger import EatCursor


def test_eating_never_begins_without_issued_current_action():
    executor = IssuedEatingExecutor()
    with pytest.raises(EatingExecutionRejected):
        asyncio.run(executor.execute(None, None, None, None, None))
    assert executor._attempted == set()



def test_deduped_child_commands_are_distinct_and_native_food_delta_required():
    before = s46.case()
    choice = EatCursor(before.session_id).choose(before)
    equip = MineflayerEffectResult(
        before.session_id, before.seq + 1, "parent-equip",
        "equip_item", "applied", None,
    )
    consume = MineflayerEffectResult(
        before.session_id, before.seq + 2, "parent-consume",
        "consume_held", "applied", None,
    )
    after = replace(
        before, seq=before.seq + 3, request_id="after-real-child-effects",
        snapshot=replace(
            before.snapshot, food=12.0,
            inventory=(MineflayerInventoryItem("bread", 1, 4),),
        ),
    )
    witnessed = verify_eating_subactions(
        "parent", choice, before, equip, consume, after,
    )
    assert witnessed.action_id == "parent" and witnessed.count_after == 1
    with pytest.raises(EatingExecutionRejected):
        verify_eating_subactions(
            "parent", choice, before, equip,
            replace(consume, action_id="parent-equip"), after,
        )
    with pytest.raises(EatingExecutionRejected):
        verify_eating_subactions(
            "parent", choice, before, equip, consume,
            replace(after, snapshot=replace(after.snapshot, food=7.0)),
        )
