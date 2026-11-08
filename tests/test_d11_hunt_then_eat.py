"""D11 offline STOP/S51 integration boundaries, forged evidence negatives.

No Minecraft, native Action, food injection or model calls.
"""
from __future__ import annotations

import asyncio
from copy import deepcopy

import pytest

from tools.bug0_d11_hunt_then_eat_post import audit_d11
from tools.bug0_d6_multigen_post import MultigenAuditRejected
from tools.bug0_d4_oneworld import run


def sample(*, first_positive=False):
    gen = 1 if first_positive else 2
    counts = [1] if first_positive else [0, 2]
    rotten = counts[-1]
    sid = "session-uuid"
    return {
        "report": {
            "d11_hunt_then_eat_dev": True,
            "d10_until_drop_dev": True,
            "d7f_live_eat_optin": True,
            "self_eat": True,
            "d11_eat_outcome": {
                "consumed_item": "rotten_flesh", "session_id": sid,
                "count_before": rotten, "count_after": rotten-1,
                "food_before": 11, "food_after": 15,
            },
            "d7f_live_natural_stop": {
                "session_id": sid,
                "classification": "D7_F_DEV_LIVE_NATURAL_BODY_STEADY_SOURCE",
                "paper_pickup_tick": 500,
                "server_effective_original_clear_tick": "NOT_CAUSALLY_ATTESTED",
            },
            "d11_live_natural_stop": {
                "session_id": sid,
                "classification": "D7_F_DEV_LIVE_NATURAL_BODY_STEADY_SOURCE",
                "paper_pickup_tick": 1500,
                "server_effective_original_clear_tick": "NOT_CAUSALLY_ATTESTED",
            },
        },
        "audit": {
            "status": "PASS_DEV",
            "classification": "D10_TRUE_NATURAL_DROP_AND_ORIGINAL_S49_PICKUP_PASS",
            "completed_original_s49_kill_generations": len(counts),
            "natural_counts": counts,
            "hunt_goal_first_true_natural_drop_picked": True,
            "d11_first_real_eat_verified": True,
            "no_eat_after_move": False,
            "d10_dev_safety_limit_not_product_policy": 12,
            "original_attack_count": len(counts),
            "same_supervisor_retained": True,
            "natural_item_uuid": "paper-uuid",
            "original_move_count": 2,
            "d11_eat_generation": gen,
            "d11_eat_action_id": f"eat-{gen}",
            "session_id": sid,
        },
    }


def run_audit(monkeypatch, tmp_path, fixture):
    from tools import bug0_d11_hunt_then_eat_post as post
    seen = []
    def fake(*args, **kw):
        seen.append((
            kw.get("d10_hunt_until_drop_dev"),
            kw.get("d11_hunt_then_eat_dev"),
        ))
        return fixture["audit"]
    monkeypatch.setattr(post, "audit", fake)
    result = audit_d11(
        "", fixture["report"],
        nonmotion_path=tmp_path/"fence",
        motion_path=tmp_path/"motion",
        s50_sidecar="S50_DEV_NATIVE_READBACK_V1",
    )
    assert seen == [(True, True)]
    return result


@pytest.mark.parametrize("first_positive", [False, True])
def test_d11_first_genuine_food_after_any_zero_eaten(
    monkeypatch, tmp_path, first_positive,
):
    fixture = sample(first_positive=first_positive)
    result = run_audit(monkeypatch, tmp_path, fixture)
    assert result["status"] == "PASS_DEV"
    assert result["genuine_s51_eat"] is True
    assert result["d11_eat_generation"] == (
        1 if first_positive else 2
    )
    assert result["long_term_survival_proven"] is False


@pytest.mark.parametrize("mutation", [
    lambda d: d["report"].update(d11_hunt_then_eat_dev=False),
    lambda d: d["report"].update(d7f_live_eat_optin=False),
    lambda d: d["report"]["d11_eat_outcome"].update(count_before=0),
    lambda d: d["report"]["d11_eat_outcome"].update(count_after=2),
    lambda d: d["report"]["d11_eat_outcome"].update(food_after=8),
    lambda d: d["report"]["d11_eat_outcome"].update(consumed_item="bread"),
    lambda d: d["report"]["d11_live_natural_stop"].update(
        server_effective_original_clear_tick="FORGED_ATTESTED",
    ),
    lambda d: d["audit"].update(d11_eat_generation=1),
    lambda d: d["audit"].update(natural_counts=[0, 0, 2]),
    lambda d: d["audit"].update(original_move_count=0),
    lambda d: d["audit"].update(d11_first_real_eat_verified=False),
    lambda d: d["audit"].update(no_eat_after_move=True),
    lambda d: d["audit"].update(same_supervisor_retained=False),
])
def test_d11_rejects_forged_eat_or_source(monkeypatch, tmp_path, mutation):
    fixture = sample()
    mutation(fixture)
    with pytest.raises(MultigenAuditRejected):
        run_audit(monkeypatch, tmp_path, fixture)


def test_d11_twelve_real_zero_drops_never_invent_eat(monkeypatch, tmp_path):
    fixture = sample()
    fixture["audit"].update(
        status="NOT_EXERCISED",
        completed_original_s49_kill_generations=12,
        natural_counts=[0]*12,
        original_attack_count=12,
        original_move_count=0,
        hunt_goal_first_true_natural_drop_picked=False,
        d11_first_real_eat_verified=False,
        d11_eat_generation=None,
        d11_eat_action_id=None,
        natural_item_uuid=None,
        no_eat_after_move=True,
    )
    fixture["report"].update(self_eat=False)
    result = run_audit(monkeypatch, tmp_path, fixture)
    assert result["status"] == "NOT_EXERCISED"
    assert result["genuine_s51_eat"] is False
    bad = deepcopy(fixture)
    bad["audit"]["natural_counts"][-1] = 1
    with pytest.raises(MultigenAuditRejected):
        run_audit(monkeypatch, tmp_path, bad)


def test_d11_without_world_grant_fails_before_world(monkeypatch, tmp_path):
    for key in (
        "S49_REAL_SERVER_CI", "BUG0_S49_D4_ONE_WORLD_ONLY",
        "S49_D5_NONMOTION_FENCE_DEV_ONLY",
        "D6_NATURAL_DROP_MOVE_WORLD_ONLY",
        "D6_NATURAL_MULTIGEN_WORLD_ONLY",
        "D10_HUNT_UNTIL_DROP_WORLD_ONLY",
        "D11_HUNT_THEN_S51_EAT_WORLD_ONLY",
        "D7_PASSIVE_CONTROLS_WORLD_ONLY",
        "D7F_NATURAL_S49_S51_WORLD_ONLY",
    ):
        monkeypatch.delenv(key, raising=False)
    result = asyncio.run(run(
        tmp_path/"report.json", tmp_path/"paper.log",
        nonmotion_fence_path=tmp_path/"nonmotion.json",
        motion_fence_path=tmp_path/"motion.json",
        d7_native_controls_path=tmp_path/"s50.jsonl",
        post_death_loot_move_dev=lambda *a, **kw: None,
        post_respawn_dev=lambda *a, **kw: None,
        d7f_natural_eat_dev=lambda *a, **kw: None,
        d6_multigen_dev=True,
        d10_hunt_until_drop_dev=True,
        d11_hunt_then_eat_dev=True,
    ))
    assert result != 0
    assert not (tmp_path/"paper.log").exists()
    assert not (tmp_path/"nonmotion.json").exists()
    assert not (tmp_path/"motion.json").exists()
