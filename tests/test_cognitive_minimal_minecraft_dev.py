"""Native Mineflayer -> CPU Schema -> L1 -> existing supervised executor.

These are fake decoded native messages and scripted L1 decisions: OFFLINE DEV,
NOT an actual Minecraft World, Gemma or S49 runtime qualification.
"""
from __future__ import annotations

import asyncio
import threading

import pytest

from adapters.mineflayer.python_protocol import (
    MINEFLAYER_NEARBY_ENTITY_MAX_DISTANCE,
    MINEFLAYER_NEARBY_ENTITY_MAX_ENTITIES,
    MINEFLAYER_NEARBY_ENTITY_SOURCE_SCOPE,
    MineflayerEffectResult,
    MineflayerEntityFact,
    MineflayerEntityHurt,
    MineflayerInventoryItem,
    MineflayerNearbyEntitiesCoverage,
    MineflayerObservation,
    MineflayerPosition,
    MineflayerSnapshot,
)
from experiments.cognitive_minimal_minecraft_dev import (
    execute_one_cognitive_world_turn,
    native_schema_percept,
)
from experiments.controlled_minecraft_vertical import ControlledScenario
from relay_self.action import ActionState
from relay_self.action_supervision import ActionSupervisor
from relay_self.cognitive_minimal_dev import (
    MinimalCognitionError,
    cpu_schema_epoch,
    initial_patterns,
)
from relay_self.intent import IntentCommitment
from relay_self.relay_engine import CognitionMode, ProviderDecision, RelayEngine
from relay_self.skill import SkillState

SKILLS = frozenset({("EAT", 1), ("ATTACK", 1)})


def scenario(*, attack_range: float | None = 4) -> ControlledScenario:
    return ControlledScenario(
        hazard_entity_names=frozenset({"zombie"}),
        food_threshold=10,
        edible_item_names=("bread",),
        destinations=(),
        fight_max_distance=attack_range,
        evidence_timeout_s=1,
        max_evidence_messages=8,
    )


def bread() -> MineflayerInventoryItem:
    return MineflayerInventoryItem("bread", 2, 9)


def zombie(*, distance: float = 2, entity_id: int = 7) -> MineflayerEntityFact:
    return MineflayerEntityFact(
        entity_id, "zombie", "mob", distance,
        MineflayerPosition(distance, 64, 0),
    )


def observation(
    seq: int,
    *,
    kind: str = "probe",
    food: float = 7,
    inventory: tuple[MineflayerInventoryItem, ...] = (),
    entities: tuple[MineflayerEntityFact, ...] = (),
    session_id: str = "session-1",
) -> MineflayerObservation:
    return MineflayerObservation(
        session_id, seq, kind,
        MineflayerSnapshot(
            health=20, food=food, food_saturation=5, oxygen_level=None,
            position=MineflayerPosition(0, 64, 0),
            time=None, inventory=inventory, nearby_entities=entities,
            nearby_entities_coverage=MineflayerNearbyEntitiesCoverage(
                source_scope=MINEFLAYER_NEARBY_ENTITY_SOURCE_SCOPE,
                max_distance=MINEFLAYER_NEARBY_ENTITY_MAX_DISTANCE,
                max_entities=MINEFLAYER_NEARBY_ENTITY_MAX_ENTITIES,
                candidate_count=len(entities), truncated=False,
            ),
        ),
    )


def effect(seq: int, action_id: str, kind: str, *,
           status: str = "applied", error: str | None = None) -> MineflayerEffectResult:
    return MineflayerEffectResult(
        "session-1", seq, action_id, kind, status, error,
    )


class FakeNativeSession:
    def __init__(self, messages):
        self.messages = list(messages)
        self.sent = []

    async def receive(self):
        if not self.messages:
            raise AssertionError("unexpected native read")
        return self.messages.pop(0)

    async def send_observe(self):
        self.sent.append(("observe",))

    async def send_equip_item(self, action_id, *, item_name):
        self.sent.append(("equip_item", action_id, item_name))

    async def send_consume_held(self, action_id):
        self.sent.append(("consume_held", action_id))

    async def send_attack_entity(self, action_id, *, entity_id):
        self.sent.append(("attack_entity", action_id, entity_id))


def engine_with_choice(choice_id: str) -> RelayEngine:
    def provider(request, *, mode):
        assert mode is CognitionMode.BOUNDED
        assert request.think_allowed is False
        return ProviderDecision.resolved(choice_id)

    return RelayEngine(provider)


def turn(
    session: FakeNativeSession,
    initial: MineflayerObservation,
    *,
    choice: str = "1",
    config: ControlledScenario | None = None,
    grant: bool = True,
):
    owner = IntentCommitment()
    supervisor = ActionSupervisor()
    result = asyncio.run(execute_one_cognitive_world_turn(
        session, initial, scenario() if config is None else config,
        self_id="self-A", intent_id="intent-1", registry=initial_patterns(),
        relay_engine=engine_with_choice(choice), intent_owner=owner,
        supervisor=supervisor, grant_real_world=grant, issue_native=True,
    ))
    return result, owner, supervisor


def test_d1_native_inventory_to_l1_eat_and_original_action_outcomes() -> None:
    initial = observation(1, kind="inventory", inventory=(bread(),))
    prefix = "skill:eat:session-1:2"
    session = FakeNativeSession([
        observation(2, inventory=(bread(),)),
        effect(3, prefix + ":equip", "equip_item"),
        effect(4, prefix + ":consume", "consume_held"),
        observation(5, kind="health", food=13),
    ])
    result, owner, supervisor = turn(session, initial)
    assert result.status == "ACTION_ATTEMPTED"
    assert result.selection.option.target_ref == "inventory:bread"
    assert result.run.skill_execution.state is SkillState.SUCCEEDED
    assert result.actual_action_outcomes == 2
    assert all(a.state is ActionState.OUTCOME for a in result.run.actions)
    assert owner.current_intent.intent_id == "intent-1"
    assert supervisor.open_actions == ()
    assert session.sent == [
        ("observe",),
        ("equip_item", prefix + ":equip", "bread"),
        ("consume_held", prefix + ":consume"),
    ]


def test_d2_native_both_goals_l1_defense_uses_original_fight_outcome() -> None:
    initial = observation(1, kind="entities", inventory=(bread(),),
                          entities=(zombie(),))
    prefix = "skill:fight:session-1:2"
    session = FakeNativeSession([
        observation(2, entities=(zombie(),), inventory=(bread(),)),
        effect(3, prefix + ":attack", "attack_entity"),
        MineflayerEntityHurt("session-1", 4, 7, 1, 1),
    ])
    result, owner, supervisor = turn(session, initial, choice="2")
    assert {g.goal_id for g in result.initial_frame.goals} == {
        "HUNGER_RELIEF", "DEFEND_SELF",
    }
    assert result.selection.option.target_ref == "entity:7"
    assert result.run.skill_execution.state is SkillState.SUCCEEDED
    assert result.actual_action_outcomes == 1
    assert session.sent == [
        ("observe",), ("attack_entity", prefix + ":attack", 7),
    ]
    assert owner.current_intent.objective == "DEFEND_SELF"
    assert supervisor.open_actions == ()


def test_d3_native_hungry_no_item_retains_goal_and_requests_l2_without_action() -> None:
    initial = observation(1, kind="health")
    session = FakeNativeSession([])
    result, owner, supervisor = turn(session, initial)
    assert result.status == "ESCALATE_L2"
    assert result.initial_frame.goals[0].unresolved
    assert not result.initial_frame.options
    assert result.run is None and result.current_frame is None
    assert owner.current_intent is None and supervisor.open_actions == ()
    assert not session.sent


def test_d4_native_target_disappears_after_l1_no_owner_or_action() -> None:
    initial = observation(1, kind="inventory", inventory=(bread(),))
    session = FakeNativeSession([observation(2, inventory=())])
    result, owner, supervisor = turn(session, initial)
    assert result.status == "REJECTED"
    assert result.run is None
    assert session.sent == [("observe",)]
    assert owner.current_intent is None and supervisor.open_actions == ()


def test_d8_unrelated_native_entity_update_does_not_cancel_eat() -> None:
    initial = observation(1, kind="inventory", inventory=(bread(),))
    prefix = "skill:eat:session-1:2"
    session = FakeNativeSession([
        observation(2, inventory=(bread(),), entities=(zombie(distance=9),)),
        effect(3, prefix + ":equip", "equip_item"),
        effect(4, prefix + ":consume", "consume_held"),
        observation(5, food=13),
    ])
    result, _, _ = turn(session, initial)
    assert result.status == "ACTION_ATTEMPTED"
    assert result.run.skill_execution.state is SkillState.SUCCEEDED
    assert {g.goal_id for g in result.current_frame.goals} == {
        "HUNGER_RELIEF", "DEFEND_SELF",
    }
    assert result.current_frame.goals[1].unresolved


def test_d5_cpu_remains_callable_while_l1_network_thread_is_blocked() -> None:
    started = threading.Event()
    release = threading.Event()
    initial = observation(1, kind="inventory", inventory=(bread(),))
    session = FakeNativeSession([])
    owner = IntentCommitment()

    def blocked_provider(request, *, mode):
        started.set()
        assert release.wait(timeout=3)
        return ProviderDecision.resolved("3")  # DEFER after EAT and ESCALATE_L2.

    async def run():
        task = asyncio.create_task(execute_one_cognitive_world_turn(
            session, initial, scenario(), self_id="self-A", intent_id="intent-1",
            registry=initial_patterns(), relay_engine=RelayEngine(blocked_provider),
            intent_owner=owner, supervisor=ActionSupervisor(),
            grant_real_world=True, issue_native=False,
        ))
        for _ in range(100):
            if started.is_set():
                break
            await asyncio.sleep(0.005)
        assert started.is_set()
        # Same event loop is free to run the L0 CPU epoch while L1 is blocked.
        native = native_schema_percept(
            observation(2, entities=(zombie(),), food=20),
            scenario(), self_id="self-A",
        )
        fast = cpu_schema_epoch(
            native, initial_patterns(), epoch=2,
            allowed_skills=SKILLS, hunger_threshold=10,
        )
        assert fast.fast_cues == ("ZOMBIE_NEAR",)
        release.set()
        return await task

    try:
        receipt = asyncio.run(run())
    finally:
        release.set()
    assert receipt.status == "DEFER" and session.sent == []


def test_native_unactionable_distant_zombie_retains_unresolved_defensive_goal() -> None:
    p = native_schema_percept(
        observation(1, kind="entities", food=20, entities=(zombie(distance=9),)),
        scenario(), self_id="self-A",
    )
    f = cpu_schema_epoch(
        p, initial_patterns(), epoch=1,
        allowed_skills=SKILLS, hunger_threshold=10,
    )
    assert f.fast_cues == ("ZOMBIE_NEAR",)
    assert [g.goal_id for g in f.goals] == ["DEFEND_SELF"]
    assert f.goals[0].unresolved
    assert not f.options


def test_unknown_fatigue_sensor_is_not_invented_as_goal_less_constraint() -> None:
    p = native_schema_percept(observation(1, food=20), scenario(), self_id="self-A")
    assert p.fatigue_high is None
    f = cpu_schema_epoch(p, initial_patterns(), epoch=1, allowed_skills=SKILLS)
    assert f.constraints == ()


def test_disallowed_world_grant_fails_without_probe_or_owner_mutation() -> None:
    initial = observation(1, inventory=(bread(),))
    session = FakeNativeSession([])
    with pytest.raises(MinimalCognitionError, match="explicit grant"):
        turn(session, initial, grant=False)
    assert session.sent == []


def test_probe_wrong_session_never_commits_original_owner() -> None:
    initial = observation(1, inventory=(bread(),))
    session = FakeNativeSession([
        observation(2, inventory=(bread(),), session_id="different"),
    ])
    with pytest.raises(MinimalCognitionError, match="session changed"):
        turn(session, initial)
    assert session.sent == [("observe",)]


def test_native_rejected_equip_is_known_action_outcome_not_skill_success() -> None:
    initial = observation(1, inventory=(bread(),))
    prefix = "skill:eat:session-1:2"
    session = FakeNativeSession([
        observation(2, inventory=(bread(),)),
        effect(3, prefix + ":equip", "equip_item",
               status="rejected", error="not available"),
    ])
    result, _, supervisor = turn(session, initial)
    assert result.status == "ACTION_ATTEMPTED"
    assert result.run.skill_execution.state is SkillState.FAILED
    assert result.actual_action_outcomes == 1
    assert supervisor.open_actions == ()
    assert session.sent == [
        ("observe",), ("equip_item", prefix + ":equip", "bread"),
    ]


def test_unknown_hunger_fractional_does_not_invent_current_need() -> None:
    p = native_schema_percept(observation(1, food=10.5), scenario(), self_id="self-A")
    assert p.hunger is None
    assert not cpu_schema_epoch(
        p, initial_patterns(), epoch=1, allowed_skills=SKILLS,
        hunger_threshold=10,
    ).goals


def test_default_live_probe_never_issues_without_explicit_native_switch() -> None:
    async def run():
        initial = observation(1, inventory=(bread(),))
        session = FakeNativeSession([observation(2, inventory=(bread(),))])
        owner = IntentCommitment()
        supervisor = ActionSupervisor()
        receipt = await execute_one_cognitive_world_turn(
            session, initial, scenario(), self_id="self-A", intent_id="intent-1",
            registry=initial_patterns(), relay_engine=engine_with_choice("1"),
            intent_owner=owner, supervisor=supervisor, grant_real_world=True,
        )
        assert receipt.status == "READY_NO_ISSUE"
        assert receipt.run is None
        assert owner.current_intent is None and not owner.events
        assert supervisor.open_actions == ()
        assert session.sent == [("observe",)]
    asyncio.run(run())
