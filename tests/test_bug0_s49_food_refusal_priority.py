"""Bug-0 S49-native food refusal and MOVE/EAT/REST/ATTACK candidate priority.

All fixtures offline. They prove deterministic policy ordering and fail-closed
authority, not physical combat, movement, food consumption, or survival.
"""
from __future__ import annotations

import asyncio
import json
from dataclasses import replace
from types import SimpleNamespace

import pytest

import test_bug0_s49_food_l0 as food_cases
import test_feature_s46_eat as s46
from adapters.mineflayer.normal_action import NormalSessionActionExecutor
from adapters.mineflayer.python_protocol import MineflayerInventoryItem
from adapters.mineflayer.s49_basic_priority_l0 import S49BasicPriorityL0
from adapters.mineflayer.s49_food_refusal_dev import (
    S49FoodRefusalFailure,
    run_s49_food_refusal_matrix,
)
from relay_self.intent import IntentCommitment
from relay_self.provenance import Provenance


def sample(*, food=20, seq=100, bread=3, zombie=False, truncated=False):
    mob = (s46.case().snapshot.nearby_entities[0],) if zombie else ()
    p = food_cases.reading(
        food=food, seq=seq, nearby=mob,
        inventory=(MineflayerInventoryItem("bread", bread, 4),)
        if bread else (),
    )
    if truncated:
        # Adapter pins its coverage max_entities to exactly 16. A genuinely
        # truncated snapshot must provide 16 reported and >=17 candidates.
        witness = s46.case().snapshot.nearby_entities[0]
        p = replace(
            p, snapshot=replace(
                p.snapshot,
                nearby_entities=tuple(
                    replace(witness, entity_id=witness.entity_id + i)
                    for i in range(16)
                ),
                nearby_entities_coverage=replace(
                    p.snapshot.nearby_entities_coverage,
                    candidate_count=17,
                    truncated=True,
                ),
            ),
        )
    return p


def test_priority_native_full_no_food_and_nearby_zombie_are_not_eat():
    p = sample()
    policy = S49BasicPriorityL0(p.session_id)
    full = policy.decide(p)
    no_food = policy.decide(sample(food=13, bread=0, seq=p.seq + 1))
    danger = policy.decide(sample(food=13, zombie=True, seq=p.seq + 2))
    assert (full.selected, full.reason) == ("WAIT", "NOT_HUNGRY")
    assert (no_food.selected, no_food.reason) == ("WAIT", "NO_INVENTORY_FOOD")
    assert (danger.selected, danger.reason) == (
        "DEFER", "ZOMBIE_PRESENT_NO_DEFENSE_ADMISSION",
    )
    assert (danger.preferred, danger.fallback) == ("MOVE_AWAY", "ATTACK")
    assert not any(x.action_issued or x.permission_granted for x in (
        full, no_food, danger,
    ))


def test_priority_hungry_safe_eat_candidate_never_issues_action():
    p = sample(food=13)
    d = S49BasicPriorityL0(p.session_id).decide(p)
    assert d.selected == "EAT" and d.preferred == "EAT"
    assert d.action_issued is False and d.permission_granted is False


def test_priority_rest_is_candidate_only_and_native_risk_takes_precedence():
    p = sample(food=20)
    policy = S49BasicPriorityL0(p.session_id)
    rest = policy.decide(p, rest_requested=True)
    threat = policy.decide(sample(food=13, seq=p.seq + 1, zombie=True), rest_requested=True)
    assert (rest.selected, rest.preferred, rest.reason) == (
        "REST", "REST", "REST_INTENT_ONLY_P1_WAIT_UNATTESTED",
    )
    assert (threat.selected, threat.preferred, threat.fallback) == (
        "DEFER", "MOVE_AWAY", "ATTACK",
    )
    assert not rest.action_issued and not threat.action_issued


def test_priority_truncated_source_fails_closed_and_stale_rejected():
    p = sample(truncated=True)
    policy = S49BasicPriorityL0(p.session_id)
    assert policy.decide(p).reason == "COVERAGE_INCOMPLETE"
    with pytest.raises(ValueError):
        policy.decide(p)
    with pytest.raises(ValueError):
        S49BasicPriorityL0(p.session_id).decide(p, rest_requested="yes")


def test_s49_original_owner_native_refusal_matrix_scripted_without_action(monkeypatch):
    from adapters.mineflayer import s49_food_refusal_dev as runner

    p = sample(food=20, seq=110)
    samples = (
        p,
        sample(food=13, bread=0, seq=111),
        sample(food=13, seq=112, zombie=True),
    )
    intent = IntentCommitment()
    intent.commit(
        "eat-when-hungry", objective="bounded DEV refusal decisions", at_ns=1,
        provenance=Provenance("test-offline", "intent"),
    )
    owner = NormalSessionActionExecutor(p.session_id, intent)

    class FakeStdin:
        async def drain(self):
            pass

    fake_session = SimpleNamespace(started=SimpleNamespace(session_id=p.session_id))
    fake_server = SimpleNamespace(stdin=FakeStdin())
    staged = []
    reads = iter(samples)
    monkeypatch.setattr(runner, "_command", lambda server, c: staged.append(c))

    async def no_sleep(_):
        pass

    async def read(_session, _id):
        return next(reads)

    monkeypatch.setattr(runner.asyncio, "sleep", no_sleep)
    monkeypatch.setattr(runner, "_correlated_observe", read)
    report = {}
    asyncio.run(run_s49_food_refusal_matrix(fake_session, fake_server, owner, report))
    assert report["refusal_outcomes"]["no_s49_action_or_native_eat"] is True
    assert report["refusal_outcomes"]["native_probe_seqs"] == [110, 111, 112]
    assert report["actual_native_actions"] == []
    assert report["food_commands_issued"] == 0
    assert report["m_energy_credited"] is False
    assert report["learning_in_world"] is False
    assert report["real_model_calls"] == 0
    assert not owner.supervisor.open_actions and owner._count == 0
    assert staged.count("give RelaySelf minecraft:bread 3") == 2
    assert any("summon minecraft:zombie" in x for x in staged)
    assert [x["selected"] for x in report["refusal_trace"]] == [
        "WAIT", "WAIT", "DEFER",
    ]


def test_refusal_runner_rejects_preissued_owner():
    p = sample()
    intent = IntentCommitment()
    intent.commit(
        "eat-when-hungry", objective="no prior action", at_ns=1,
        provenance=Provenance("test-offline", "intent"),
    )
    owner = NormalSessionActionExecutor(p.session_id, intent)
    owner._count = 1
    session = SimpleNamespace(started=SimpleNamespace(session_id=p.session_id))
    server = SimpleNamespace(stdin=SimpleNamespace())
    with pytest.raises(S49FoodRefusalFailure):
        asyncio.run(run_s49_food_refusal_matrix(session, server, owner, {}))


@pytest.mark.parametrize("mode", ["missing-gate", "conflict-food-loop", "wrong-type"])
def test_refusal_mode_blocks_before_java(tmp_path, monkeypatch, mode):
    from adapters.mineflayer import s49_normal_session_real_ci as s49

    monkeypatch.setenv("S49_REAL_SERVER_CI", "1")
    monkeypatch.delenv("NODE_OPTIONS", raising=False)
    monkeypatch.setenv("S49_BUG0_FOOD_REFUSAL_DEV_ONLY", "1")
    monkeypatch.setenv("S49_BUG0_FOOD_LOOP_DEV_ONLY", "1")
    monkeypatch.setattr(
        s49, "_fetch_official_server",
        lambda *_: (_ for _ in ()).throw(AssertionError("No Java allowed")),
    )
    params = {"bug0_food_refusal_dev": True}
    if mode == "missing-gate":
        monkeypatch.delenv("S49_BUG0_FOOD_REFUSAL_DEV_ONLY")
    elif mode == "conflict-food-loop":
        params["bug0_food_loop_dev"] = True
    else:
        params["bug0_food_refusal_dev"] = "yes"
    output = tmp_path / f"{mode}.json"
    result = asyncio.run(s49.qualify(
        output, tmp_path / "paper.log", **params,
    ))
    assert result == 2
    report = json.loads(output.read_text())
    assert report["status"] == "BLOCKED"
    assert report["actual_native_actions"] == []
