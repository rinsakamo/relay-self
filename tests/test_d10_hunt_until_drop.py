"""Offline DEV D10: hunt genuine World zombies past D6 four zero samples.

No Paper World, no native Action/LLM, no loot manipulation.
"""
from __future__ import annotations

import asyncio

import pytest

from adapters.mineflayer.normal_action import (
    NormalActionRejected,
    NormalSessionActionExecutor,
)
from relay_self.intent import IntentCommitment
from relay_self.provenance import Provenance
from tools.bug0_d4_oneworld import run
from tools.bug0_d6_multigen_post import MultigenAuditRejected
from tools.bug0_d10_hunt_until_drop_post import audit_d10


def owner(*, extended=False, count=4):
    intent = IntentCommitment()
    intent.commit(
        "escape-threat", objective="source-qualified hunting",
        at_ns=1, provenance=Provenance("d10-offline-test", "original"),
    )
    return NormalSessionActionExecutor(
        "d10-native-session", intent, max_intent_epochs=count,
        dev_hunt_extended_epochs=extended,
    )


def test_d10_extended_epoch_grant_has_no_effect_on_d6_default():
    assert owner()._max_intent_epochs == 4
    assert owner(extended=True, count=12)._max_intent_epochs == 12
    with pytest.raises(NormalActionRejected):
        owner(count=12)
    with pytest.raises(NormalActionRejected):
        owner(extended=True, count=4)
    with pytest.raises(NormalActionRejected):
        owner(extended=True, count=13)


def test_d10_world_without_grant_prevents_world_or_ledgers(monkeypatch, tmp_path):
    for key in (
        "S49_REAL_SERVER_CI", "BUG0_S49_D4_ONE_WORLD_ONLY",
        "S49_D5_NONMOTION_FENCE_DEV_ONLY",
        "D6_NATURAL_DROP_MOVE_WORLD_ONLY",
        "D6_NATURAL_MULTIGEN_WORLD_ONLY",
        "D10_HUNT_UNTIL_DROP_WORLD_ONLY",
    ):
        monkeypatch.delenv(key, raising=False)
    result = asyncio.run(run(
        tmp_path/"report.json", tmp_path/"paper.log",
        nonmotion_fence_path=tmp_path/"nonmotion.json",
        motion_fence_path=tmp_path/"motion.json",
        d6_multigen_dev=True,
        d10_hunt_until_drop_dev=True,
        post_respawn_dev=lambda *a, **kw: None,
        post_death_loot_move_dev=lambda *a, **kw: None,
    ))
    assert result != 0
    assert not (tmp_path/"paper.log").exists()
    assert not (tmp_path/"nonmotion.json").exists()
    assert not (tmp_path/"motion.json").exists()


def source(*, counts, status="PASS_DEV", move=2):
    return {
        "status": status,
        "classification": "D10_TRUE_NATURAL_DROP_AND_ORIGINAL_S49_PICKUP_PASS"
        if status == "PASS_DEV" else
        "D10_DEV_SAFETY_LIMIT_REACHED_NO_DROP_NOT_EXERCISED",
        "completed_original_s49_kill_generations": len(counts),
        "natural_counts": counts,
        "hunt_goal_first_true_natural_drop_picked": status == "PASS_DEV",
        "d10_dev_safety_limit_not_product_policy": 12,
        "original_attack_count": len(counts),
        "original_move_count": move,
        "no_eat_after_move": True,
        "first_positive_generation": len(counts) if status == "PASS_DEV" else None,
        "natural_item_uuid": "abc" if status == "PASS_DEV" else None,
    }


def invoke(monkeypatch, tmp_path, result, *, d10=True):
    from tools import bug0_d10_hunt_until_drop_post as post
    seen = []
    def fake(*a, **kw):
        seen.append(kw.get("d10_hunt_until_drop_dev"))
        return result
    monkeypatch.setattr(post, "audit", fake)
    answer = audit_d10(
        "", {"d10_until_drop_dev": d10},
        nonmotion_path=tmp_path/"nonmotion",
        motion_path=tmp_path/"motion",
    )
    assert seen == [True]
    return answer


def test_d10_first_positive_ends_hunt(monkeypatch, tmp_path):
    for counts in ([1], [0, 1], [0, 0, 0, 1], [0]*11+[2]):
        result = invoke(monkeypatch, tmp_path, source(counts=counts))
        assert result["status"] == "PASS_DEV"
        assert result["first_positive_generation"] == len(counts)


def test_d10_all_zero_is_exhaustion_not_success(monkeypatch, tmp_path):
    result = invoke(monkeypatch, tmp_path, source(
        counts=[0]*12, status="NOT_EXERCISED", move=0,
    ))
    assert result["status"] == "NOT_EXERCISED"
    assert not result["hunt_goal_first_true_natural_drop_picked"]


@pytest.mark.parametrize("counts,status,move", [
    ([0, 0, 1, 0], "PASS_DEV", 1),
    ([0]*11, "NOT_EXERCISED", 0),
    ([0]*12, "PASS_DEV", 1),
    ([0, 1], "PASS_DEV", 0),
    ([0]*11 + [1], "NOT_EXERCISED", 0),
])
def test_d10_rejects_false_first_positive_or_budget(
    monkeypatch, tmp_path, counts, status, move,
):
    data = source(counts=counts, status=status, move=move)
    with pytest.raises(MultigenAuditRejected):
        invoke(monkeypatch, tmp_path, data)


def test_d10_no_origin_can_be_promoted(monkeypatch, tmp_path):
    with pytest.raises(MultigenAuditRejected):
        invoke(monkeypatch, tmp_path, source(counts=[0, 1]), d10=False)
