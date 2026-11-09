"""R9 offline: original S49 combat first, without disabling STOP fences."""
from __future__ import annotations

import asyncio
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from adapters.mineflayer.attack_execution import AttackActionReceipt
from adapters.mineflayer.eat_execution import EatingActionReceipt
from adapters.mineflayer.python_protocol import (
    MINEFLAYER_NEARBY_ENTITY_MAX_DISTANCE,
    MINEFLAYER_NEARBY_ENTITY_MAX_ENTITIES,
    MINEFLAYER_NEARBY_ENTITY_SOURCE_SCOPE,
    MineflayerInventoryItem,
    MineflayerNearbyEntitiesCoverage,
    MineflayerObservation,
    MineflayerPosition,
    MineflayerSnapshot,
)
from relay_self.action import ActionState
from relay_self.eat_hunger import EatingOutcome
from test_d14_natural_motion_r6 import controller, observation
from tools.bug0_d14_natural_life import (
    R9_COMBAT_GRANT,
    NaturalLifeLoop,
    NaturalLifeRejected,
    admissible_natural_attack,
)


def _grants(monkeypatch):
    for key in (
        "D14_R4_NATURAL_S49_ONEWORLD_ONLY",
        "D14_R5_LOCAL_ONEWORLD_ONLY",
        "D14_R6_NATURAL_MOTION_ONEWORLD_ONLY",
        "D14_R7_NATIVE_EVIDENCE_ONEWORLD_ONLY",
        "D7_PASSIVE_CONTROLS_WORLD_ONLY",
        R9_COMBAT_GRANT,
    ):
        monkeypatch.setenv(key, "1")


def _decision():
    return SimpleNamespace(
        selected="DEFER", preferred="MOVE_AWAY", fallback="ATTACK",
        reason="ZOMBIE_PRESENT_NO_DEFENSE_ADMISSION",
    )


def test_r9_requires_explicit_evidence_and_move_grants_before_ledger(
    tmp_path, monkeypatch,
):
    monkeypatch.setenv("D14_R4_NATURAL_S49_ONEWORLD_ONLY", "1")
    monkeypatch.setenv(R9_COMBAT_GRANT, "1")
    session = SimpleNamespace(started=SimpleNamespace(session_id="native-session"))
    with pytest.raises(NaturalLifeRejected, match="R9_COMBAT_REQUIRES"):
        NaturalLifeLoop(session, tmp_path, {})
    assert list(tmp_path.iterdir()) == []


def test_r9_first_native_zombie_attack_preempts_valid_move(
    tmp_path, monkeypatch,
):
    _grants(monkeypatch)
    loop, report = controller(tmp_path, monkeypatch)
    assert loop.combat_first
    assert loop.motion is not None
    previous, current = observation(5), observation(6)
    loop._read = AsyncMock(side_effect=[previous, current])
    loop.policy = SimpleNamespace(decide=lambda *_a, **_k: _decision())
    # Even a valid native MOVE source must not win over a stable close zombie.
    loop.motion.current_candidate = lambda *_: observation(4, kind="entities")
    loop.motion.issue_original_move = AsyncMock(
        side_effect=AssertionError("MOVE must not issue before admissible ATTACK")
    )
    loop.owner.execute_attack = AsyncMock(return_value=AttackActionReceipt(
        terminal=SimpleNamespace(state=ActionState.OUTCOME),
        effect=SimpleNamespace(seq=11, result="applied"),
        after_probe=observation(12), target_entity_id=7,
        observed_target_hurt=True,
        observed_hurt_source_entity_ids=(None,),
        target_missing_in_native_view=False,
    ))
    records = []
    asyncio.run(loop.step(
        lambda kind, line, native=None: records.append((kind, native))
    ))
    loop.motion.issue_original_move.assert_not_awaited()
    loop.owner.execute_attack.assert_awaited_once()
    assert loop.owner.execute_attack.await_args.args[3] == 7
    assert report["life_decisions"][0]["r9_priority"] == (
        "ATTACK_BEFORE_MOVE_NATIVE_PAIR"
    )
    assert report["life_decisions"][0]["admission"] == "ORIGINAL_S49_GRANTED"
    assert report["life_action_outcomes"][0]["kind"] == "ATTACK"
    assert report["life_action_outcomes"][0]["original_s49_native_attack_ack_seq"] == 11
    assert report["life_action_outcomes"][0]["native_target_hurt_event_seen"]
    assert report["life_action_outcomes"][0]["damage_attested"] is False
    assert report["life_action_outcomes"][0]["zombie_kill_attested"] is False
    assert records[-1][0] == "LIFE_ACTION"
    assert loop.motion.fence.actions == ()


def test_r9_unstable_or_distant_zombie_does_not_gain_attack_authority(
    tmp_path, monkeypatch,
):
    _grants(monkeypatch)
    loop, report = controller(tmp_path, monkeypatch)
    assert loop.motion is not None
    previous, current = observation(5, distance=1.5), observation(6, distance=3.5)
    assert admissible_natural_attack(previous, current) is None
    loop._read = AsyncMock(side_effect=[previous, current])
    loop.policy = SimpleNamespace(decide=lambda *_a, **_k: _decision())
    loop.motion.current_candidate = lambda *_: observation(4, kind="entities")
    loop.motion.issue_original_move = AsyncMock(
        side_effect=AssertionError("R9 must wait, not enter the MOVE STOP trap")
    )
    loop.owner.execute_attack = AsyncMock(
        side_effect=AssertionError("unstable target cannot attack")
    )
    asyncio.run(loop.step(lambda *_a, **_k: None))
    loop.motion.issue_original_move.assert_not_awaited()
    loop.owner.execute_attack.assert_not_awaited()
    assert report["life_decisions"][0]["r9_priority"] == (
        "WAIT_FOR_NATIVE_ATTACK_ADMISSION"
    )
    assert report["life_action_outcomes"] == []
    assert loop.motion.fence.actions == ()


def test_r9_never_attacks_after_move_without_stop(
    tmp_path, monkeypatch,
):
    _grants(monkeypatch)
    loop, report = controller(tmp_path, monkeypatch)
    assert loop.motion is not None
    loop.owner._post_move_settling_unqualified = True
    loop._read = AsyncMock(side_effect=[observation(5), observation(6)])
    loop.policy = SimpleNamespace(decide=lambda *_a, **_k: _decision())
    loop.motion.current_candidate = lambda *_: None
    loop.owner.execute_attack = AsyncMock(
        side_effect=AssertionError("physical STOP not attested")
    )
    asyncio.run(loop.step(lambda *_a, **_k: None))
    loop.owner.execute_attack.assert_not_awaited()
    assert report["life_decisions"][0]["admission"] == (
        "DEFER_ORIGINAL_S49_REFUSED"
    )
    assert report["life_action_outcomes"] == []
    assert loop.motion.fence.actions == ()


def food_probe(seq: int, *, with_zombie: bool = False) -> MineflayerObservation:
    template = observation(seq)
    zombie = template.snapshot.nearby_entities if with_zombie else ()
    coverage = MineflayerNearbyEntitiesCoverage(
        source_scope=MINEFLAYER_NEARBY_ENTITY_SOURCE_SCOPE,
        max_distance=MINEFLAYER_NEARBY_ENTITY_MAX_DISTANCE,
        max_entities=MINEFLAYER_NEARBY_ENTITY_MAX_ENTITIES,
        candidate_count=len(zombie), truncated=False,
    )
    snapshot = MineflayerSnapshot(
        health=20, food=10, food_saturation=0, oxygen_level=20,
        position=MineflayerPosition(0.0, 64.0, 0.0),
        time=None,
        inventory=(MineflayerInventoryItem("rotten_flesh", 1, 36),),
        nearby_entities=zombie, nearby_entities_coverage=coverage,
    )
    return MineflayerObservation(
        session_id="native-session", seq=seq, kind="probe",
        snapshot=snapshot, request_id=f"eat-{seq}",
    )


def test_r9_original_s49_eat_remains_reachable_without_prior_move(
    tmp_path, monkeypatch,
):
    _grants(monkeypatch)
    loop, report = controller(tmp_path, monkeypatch)
    assert loop.motion is not None
    loop._read = AsyncMock(side_effect=[food_probe(5), food_probe(6)])
    loop.motion.issue_original_move = AsyncMock(
        side_effect=AssertionError("food does not require MOVE")
    )
    loop.owner.execute_eat = AsyncMock(return_value=EatingActionReceipt(
        terminal=SimpleNamespace(state=ActionState.OUTCOME),
        outcome=EatingOutcome(
            session_id="native-session", action_id="offline-eat",
            food_before=10, food_after=14, consumed_item="rotten_flesh",
            count_before=1, count_after=0, after_probe_seq=9,
            provenance=food_probe(9).provenance,
        ),
    ))
    # The real S51 receipt validation is covered by its own tests;
    # this mock checks only selection and original S49 admission.
    loop.policy.acknowledge_verified_eat = lambda receipt: None
    asyncio.run(loop.step(lambda *_a, **_k: None))
    loop.motion.issue_original_move.assert_not_awaited()
    loop.owner.execute_eat.assert_awaited_once()
    assert report["life_action_outcomes"][0]["kind"] == "EAT"
    assert report["life_action_outcomes"][0]["original_s51_food_after"] == 14
    assert report["life_action_outcomes"][0]["original_s51_inventory_after"] == 0
    assert loop.owner._post_move_settling_unqualified is False
    assert loop.motion.fence.actions == ()
    assert report["c1_intent_experiences"] == 0


def test_r9_attack_only_world_keeps_w3_s50_without_false_foreign_session(
    tmp_path,
):
    # R9 may attack without any prior MOVE. A zero-row MOVE fence has no
    # action-bound session and must not mislabel genuine W3/S50 as foreign.
    from relay_self.c1_physical_action_fence import OriginalS49PhysicalFence
    from test_d14_r7_native_evidence import make_s50, make_w3
    from tools.bug0_d14_r7_evidence_post import inspect_r7_source_only

    OriginalS49PhysicalFence.create(
        tmp_path / "original_s49_motion_fence.json",
        self_id="s49-original-self",
    )
    make_w3(tmp_path)
    make_s50(tmp_path)
    forensic = inspect_r7_source_only(tmp_path)
    assert forensic["actions"] == []
    assert forensic["w3_received_node_stdout_scope"] == (
        "INCOMPLETE_SAME_PROCESS_NODE_STDOUT_ONLY"
    )
    assert forensic["s50_same_client_scope"] == "SAME_CLIENT_READBACK_ONLY"
    assert forensic["paper_tick_aligned_stop_attested"] is False
    assert forensic["learning_authorized"] is False


def test_r9_wait_for_reach_then_original_s49_attack_same_session(
    tmp_path, monkeypatch,
):
    _grants(monkeypatch)
    loop, report = controller(tmp_path, monkeypatch)
    assert loop.motion is not None
    loop.policy = SimpleNamespace(decide=lambda *_a, **_k: _decision())
    loop.motion.current_candidate = lambda *_: observation(4, kind="entities")
    loop.motion.issue_original_move = AsyncMock(
        side_effect=AssertionError("no MOVE before or after reach")
    )
    loop.owner.execute_attack = AsyncMock(return_value=SimpleNamespace(
        terminal=SimpleNamespace(state=ActionState.OUTCOME),
    ))
    loop._read = AsyncMock(side_effect=[
        observation(5, distance=3.5), observation(6, distance=3.5),
        observation(7, distance=1.5), observation(8, distance=1.5),
    ])
    asyncio.run(loop.step(lambda *_a, **_k: None))
    assert loop.owner.execute_attack.await_count == 0
    assert report["life_decisions"][0]["r9_priority"] == (
        "WAIT_FOR_NATIVE_ATTACK_ADMISSION"
    )
    asyncio.run(loop.step(lambda *_a, **_k: None))
    assert loop.owner.execute_attack.await_count == 1
    loop.motion.issue_original_move.assert_not_awaited()
    assert report["life_decisions"][1]["r9_priority"] == (
        "ATTACK_BEFORE_MOVE_NATIVE_PAIR"
    )
    assert report["life_action_outcomes"][0]["kind"] == "ATTACK"
    assert loop.motion.fence.actions == ()


def test_original_r6_move_behavior_unchanged_without_r9(
    tmp_path, monkeypatch,
):
    _grants(monkeypatch)
    monkeypatch.delenv(R9_COMBAT_GRANT)
    loop, report = controller(tmp_path, monkeypatch)
    assert not loop.combat_first
    assert loop.motion is not None
    loop._read = AsyncMock(side_effect=[
        observation(5, distance=3.5),
        observation(6, distance=3.5),
    ])
    loop.policy = SimpleNamespace(decide=lambda *_a, **_k: _decision())
    loop.motion.current_candidate = lambda *_: observation(4, kind="entities")
    loop.motion.issue_original_move = AsyncMock(return_value={
        "action_id": "offline-move-stub", "kind": "MOVE_AWAY",
        "terminal": "outcome", "effective_physical_stop": "UNATTESTED",
    })
    asyncio.run(loop.step(lambda *_a, **_k: None))
    loop.motion.issue_original_move.assert_awaited_once()
    assert "r9_priority" not in report["life_decisions"][0]
