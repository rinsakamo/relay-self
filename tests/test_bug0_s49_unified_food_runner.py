"""Original S49 food runner smoke: exercise actual shared priority object boundary.

Offline only: injected handoff raises BEFORE any Action or Mineflayer command.
This catches API-shape errors which pure L0 tests cannot detect.
"""
from __future__ import annotations

import asyncio
from dataclasses import replace
from types import SimpleNamespace

import pytest

import test_bug0_s49_food_refusal_priority as cases
from adapters.mineflayer import s49_food_loop_dev as runner
from adapters.mineflayer.normal_action import NormalSessionActionExecutor
from relay_self.intent import IntentCommitment
from relay_self.provenance import Provenance


class OfflineHandoffReached(RuntimeError):
    """The real DEV issuance boundary was reached, but MUST NOT issue."""


def test_original_s49_shared_food_cursor_reaches_scoped_handoff_without_io(monkeypatch):
    full = cases.sample(food=20, bread=3, seq=110)
    hungry = cases.sample(food=13, bread=3, seq=111)
    fresh = cases.sample(food=13, bread=3, seq=112)
    readings = iter((full, hungry, fresh))
    intent = IntentCommitment()
    intent.commit(
        "escape-threat", objective="original mixed EAT then zombie MOVE",
        at_ns=1, provenance=Provenance("offline-fixture", "intent"),
    )
    owner = NormalSessionActionExecutor(full.session_id, intent)

    class FakeStdin:
        async def drain(self):
            pass

    fake_server = SimpleNamespace(stdin=FakeStdin())
    fake_session = SimpleNamespace(started=SimpleNamespace(
        session_id=full.session_id,
    ))
    staged_commands = []
    verified_handoff = []

    def stage(_server, command):
        staged_commands.append(command)

    async def observe(_session, _request_id):
        return next(readings)

    async def no_delay(_):
        pass

    async def must_stop_before_action(
        actual_owner, actual_session, earlier, current, shadow,
        propose, issue,
    ):
        assert actual_owner is owner
        assert actual_session is fake_session
        assert earlier is hungry and current is fresh
        assert shadow.candidate_item == "bread"
        assert propose.action_id == issue.action_id
        assert propose.probe_seq == current.seq
        assert issue.probe_request_id == current.request_id
        assert owner._count == 0 and not owner.supervisor.open_actions
        verified_handoff.append(current.seq)
        raise OfflineHandoffReached("typed DEV boundary reached; no native Action")

    monkeypatch.setattr(runner, "_command", stage)
    monkeypatch.setattr(runner, "_correlated_observe", observe)
    monkeypatch.setattr(runner.asyncio, "sleep", no_delay)
    monkeypatch.setattr(
        runner, "handoff_authorized_first_eat", must_stop_before_action,
    )
    report = {}
    with pytest.raises(OfflineHandoffReached):
        asyncio.run(runner.run_s49_food_loop(
            fake_session, fake_server, owner, report,
        ))
    assert verified_handoff == [112]
    assert [x["selected"] for x in report["food_l0_trace"]] == [
        "WAIT", "EAT", "EAT",
    ]
    assert report["action_terminal"] == "NOT_ISSUED"
    assert report["actual_native_actions"] == []
    assert report["real_model_calls"] == 0
    assert report["m_energy_credited"] is False
    assert report["learning_in_world"] is False
    assert not owner._dispatched and not owner.supervisor.open_actions
    assert "effect clear RelaySelf minecraft:hunger" in staged_commands
    assert staged_commands[:3] == [
        "gamerule doMobSpawning false",
        "kill @e[type=!minecraft:player]",
        "gamemode survival RelaySelf",
    ]
    assert report["food_risk_policy_unchanged"] is True
    assert report["initial_nonplayer_clear_command"] == (
        "kill @e[type=!minecraft:player]"
    )
    assert all(row["native_nearby"] == [] for row in report["food_l0_trace"])


def test_original_s49_runner_retains_unqualified_native_entity_refusal(monkeypatch):
    # The operator's clear command is not authority to ignore a subsequently
    # observed unknown mob. Same-session native source must still veto EAT.
    infected = cases.sample(food=20, bread=3, seq=110, zombie=True)
    witness = infected.snapshot.nearby_entities[0]
    infected = replace(infected, snapshot=replace(
        infected.snapshot,
        nearby_entities=(replace(witness, name="cow"),),
    ))
    intent = IntentCommitment()
    intent.commit(
        "escape-threat", objective="no unknown food risk",
        at_ns=1, provenance=Provenance("offline-fixture", "intent"),
    )
    owner = NormalSessionActionExecutor(infected.session_id, intent)
    fake_session = SimpleNamespace(started=SimpleNamespace(
        session_id=infected.session_id,
    ))

    class FakeStdin:
        async def drain(self):
            pass

    fake_server = SimpleNamespace(stdin=FakeStdin())
    commands = []

    async def no_delay(_):
        pass

    async def read(_session, _id):
        return infected

    monkeypatch.setattr(runner, "_command", lambda _, c: commands.append(c))
    monkeypatch.setattr(runner, "_correlated_observe", read)
    monkeypatch.setattr(runner.asyncio, "sleep", no_delay)
    report = {}
    with pytest.raises(runner.S49FoodLoopRejected, match="UNQUALIFIED_NEARBY_ENTITY"):
        asyncio.run(runner.run_s49_food_loop(
            fake_session, fake_server, owner, report,
        ))
    assert report["food_l0_trace"][0]["native_nearby"][0]["name"] == "cow"
    assert report["food_l0_trace"][0]["selected"] == "DEFER"
    assert "kill @e[type=!minecraft:player]" in commands
    assert owner._count == 0
    assert not owner._dispatched
    assert not owner.supervisor.open_actions
    assert report["actual_native_actions"] == []
