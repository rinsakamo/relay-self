"""Bug-0: native food decision state in S49, offline only; NO World or EAT."""
from __future__ import annotations

import asyncio
import json
from dataclasses import replace

import pytest

import test_feature_s46_eat as s46
from adapters.mineflayer.normal_action import (
    NormalActionRejected,
    NormalFoodL0,
)
from adapters.mineflayer.python_protocol import MineflayerInventoryItem
from relay_self.eat_hunger import EatStatus


def reading(*, food=20.0, seq=None, inventory=None, nearby=()):
    original = s46.case()
    seq = original.seq if seq is None else seq
    if inventory is None:
        inventory = (MineflayerInventoryItem("bread", 3, 4),)
    snapshot = replace(
        original.snapshot,
        food=food,
        inventory=inventory,
        nearby_entities=nearby,
        nearby_entities_coverage=replace(
            original.snapshot.nearby_entities_coverage,
            candidate_count=len(nearby),
            truncated=False,
        ),
    )
    return replace(
        original, seq=seq, request_id=f"s49-food-l0-test-{seq}",
        snapshot=snapshot,
    )


def test_s49_food_l0_wait_eat_wait_from_native_observations():
    p0 = reading(food=20)
    l0 = NormalFoodL0(p0.session_id)
    a = l0.decide(p0)
    assert (a.selection, a.reason) == ("WAIT", "NOT_HUNGRY")
    hungry = reading(food=13, seq=p0.seq + 1)
    b = l0.decide(hungry)
    assert (b.selection, b.choice.status) == ("EAT", EatStatus.CANDIDATE)
    assert b.choice.item_name == "bread"
    # The next decision is based on a NEW observed Minecraft food value,
    # not a synthetic energy credit or the string OUTCOME.
    fed = reading(food=18, seq=p0.seq + 2, inventory=(
        MineflayerInventoryItem("bread", 2, 4),
    ))
    c = l0.decide(fed)
    assert (c.selection, c.reason, c.food) == ("WAIT", "NOT_HUNGRY", 18)
    assert l0.decisions == 3


def test_s49_food_l0_missing_food_or_observed_risk_never_requests_eat():
    base = reading(food=13)
    no_food = reading(food=13, seq=base.seq, inventory=())
    assert NormalFoodL0(base.session_id).decide(no_food).reason == "NO_INVENTORY_FOOD"
    neighbor = s46.case().snapshot.nearby_entities[0]
    risky = reading(food=13, seq=base.seq, nearby=(neighbor,))
    d = NormalFoodL0(base.session_id).decide(risky)
    assert (d.selection, d.reason) == ("WAIT", "NATIVE_OBSERVATION_RISK")


def test_s49_food_l0_rejects_foreign_or_stale_probe_and_unverified_ack():
    p = reading(food=13)
    l0 = NormalFoodL0(p.session_id)
    assert l0.decide(p).selection == "EAT"
    with pytest.raises(ValueError):
        l0.decide(p)
    with pytest.raises(NormalActionRejected):
        l0.decide(replace(p, session_id="other-session", seq=p.seq + 1))
    with pytest.raises(NormalActionRejected):
        l0.acknowledge_verified_eat(object())
    assert l0.decisions == 1


def test_s49_food_l0_dev_mode_requires_separate_env_before_java(tmp_path, monkeypatch):
    from adapters.mineflayer import s49_normal_session_real_ci as s49

    monkeypatch.setenv("S49_REAL_SERVER_CI", "1")
    monkeypatch.delenv("S49_BUG0_FOOD_LOOP_DEV_ONLY", raising=False)
    monkeypatch.delenv("NODE_OPTIONS", raising=False)
    monkeypatch.setattr(
        s49, "_fetch_official_server",
        lambda *_: (_ for _ in ()).throw(AssertionError("JAVA attempted")),
    )
    report = tmp_path / "gate.json"
    rc = asyncio.run(s49.qualify(
        report, tmp_path / "paper.log", bug0_food_loop_dev=True,
    ))
    data = json.loads(report.read_text())
    assert rc == 2 and data["status"] == "BLOCKED"
    assert data["actual_native_actions"] == []
    assert not (tmp_path / "paper.log").exists()


def test_s49_food_l0_invalid_mode_type_fails_before_java(tmp_path, monkeypatch):
    from adapters.mineflayer import s49_normal_session_real_ci as s49

    monkeypatch.setenv("S49_REAL_SERVER_CI", "1")
    monkeypatch.setenv("S49_BUG0_FOOD_LOOP_DEV_ONLY", "1")
    monkeypatch.delenv("NODE_OPTIONS", raising=False)
    monkeypatch.setattr(
        s49, "_fetch_official_server",
        lambda *_: (_ for _ in ()).throw(AssertionError("JAVA attempted")),
    )
    report = tmp_path / "invalid.json"
    rc = asyncio.run(s49.qualify(
        report, tmp_path / "paper.log", bug0_food_loop_dev="true",
    ))
    assert rc == 2
    assert json.loads(report.read_text())["status"] == "BLOCKED"
