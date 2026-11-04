"""Bug-0 mixed S49 EAT -> MOVE priority and exclusive World gate (offline).

This test never launches Java, Node, native Action or a second issuer.
Actual World evidence must be supplied by the explicit one-shot workflow.
"""
from __future__ import annotations

import asyncio
import json
from dataclasses import replace

import pytest

import test_bug0_s49_food_refusal_priority as samples
from adapters.mineflayer.s49_basic_priority_l0 import S49BasicPriorityL0


def test_one_priority_owner_orders_food_rest_then_close_zombie_defense():
    base = samples.sample(food=20, seq=100)
    policy = S49BasicPriorityL0(base.session_id, max_decisions=10)
    full = policy.decide(base)
    hunger = policy.decide(samples.sample(food=13, seq=101))
    # This is a decision-only trace; a genuine EAT terminal is separately
    # necessary before it can count as completed nutrition.
    restored = policy.decide(
        samples.sample(food=18, seq=102, bread=2), rest_requested=True,
    )
    far = samples.sample(food=18, seq=103, zombie=True, bread=2)
    witness = far.snapshot.nearby_entities[0]
    far = replace(
        far, snapshot=replace(
            far.snapshot,
            nearby_entities=(replace(witness, distance=10.0),),
        ),
    )
    watch = policy.decide(far)
    near = policy.decide(samples.sample(
        food=18, seq=104, zombie=True, bread=2,
    ))
    assert (full.selected, full.reason) == ("WAIT", "NOT_HUNGRY")
    assert (hunger.selected, hunger.candidate_item) == ("EAT", "bread")
    assert hunger.candidate_slot is not None
    assert (restored.selected, restored.preferred) == ("DEFER", "REST")
    assert restored.reason == "REST_EXECUTOR_NOT_CONNECTED"
    assert (watch.selected, watch.reason) == (
        "WAIT", "DISTANT_ZOMBIE_MONITOR",
    )
    assert (near.selected, near.preferred, near.fallback) == (
        "DEFER", "MOVE_AWAY", "ATTACK",
    )
    assert not any(x.action_issued or x.permission_granted for x in (
        full, hunger, restored, watch, near,
    ))


@pytest.mark.parametrize("case", (
    "missing-gate", "food-loop-conflict", "refusal-conflict",
    "shadow-conflict", "invalid-switch",
))
def test_unified_mode_fails_before_world_when_not_exclusively_approved(
    case, tmp_path, monkeypatch,
):
    from adapters.mineflayer import s49_normal_session_real_ci as s49

    monkeypatch.setenv("S49_REAL_SERVER_CI", "1")
    monkeypatch.setenv("S49_BUG0_UNIFIED_SURVIVAL_DEV_ONLY", "1")
    monkeypatch.delenv("NODE_OPTIONS", raising=False)
    monkeypatch.setattr(
        s49, "_fetch_official_server",
        lambda *_: (_ for _ in ()).throw(AssertionError("java started")),
    )
    kw = {"bug0_unified_survival_dev": True}
    if case == "missing-gate":
        monkeypatch.delenv("S49_BUG0_UNIFIED_SURVIVAL_DEV_ONLY")
    elif case == "food-loop-conflict":
        kw["bug0_food_loop_dev"] = True
    elif case == "refusal-conflict":
        kw["bug0_food_refusal_dev"] = True
    elif case == "shadow-conflict":
        kw["bug0_eat_shadow"] = True
    else:
        kw["bug0_unified_survival_dev"] = "true"
    out = tmp_path / f"{case}.json"
    result = asyncio.run(s49.qualify(
        out, tmp_path / "paper.log", **kw,
    ))
    report = json.loads(out.read_text())
    assert result == 2 and report["status"] == "BLOCKED"
    assert report["actual_native_actions"] == []
    assert not (tmp_path / "paper.log").exists()
