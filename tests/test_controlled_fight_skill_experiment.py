import asyncio

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
from experiments.controlled_minecraft_vertical import (
    ControlledDestination,
    ControlledScenario,
    ControlledSkill,
    ScenarioDecision,
    decide_skill,
    execute_decision,
)
from experiments.controlled_skill_candidates import (
    project_controlled_skill_candidates,
)
from relay_self.action import ActionState
from relay_self.action_supervision import ActionSupervisor
from relay_self.intent import IntentCommitment
from relay_self.provenance import Provenance
from relay_self.skill import SkillState


def provenance(reference: str) -> Provenance:
    return Provenance(
        source="controlled-fight-test",
        reference=reference,
    )


def zombie(*, distance: float = 2.0) -> MineflayerEntityFact:
    return MineflayerEntityFact(
        entity_id=7,
        name="zombie",
        entity_type="mob",
        distance=distance,
        position=MineflayerPosition(x=distance, y=64, z=0),
    )


def bread() -> MineflayerInventoryItem:
    return MineflayerInventoryItem(
        name="bread",
        count=2,
        slot=9,
    )


def observation(
    *,
    seq: int = 1,
    food: float = 20,
    inventory: tuple[MineflayerInventoryItem, ...] = (),
    entities: tuple[MineflayerEntityFact, ...] = (),
) -> MineflayerObservation:
    return MineflayerObservation(
        session_id="fight-session",
        seq=seq,
        kind="entities",
        snapshot=MineflayerSnapshot(
            health=20,
            food=food,
            food_saturation=5,
            oxygen_level=20,
            position=MineflayerPosition(x=0, y=64, z=0),
            time=None,
            inventory=inventory,
            nearby_entities=entities,
            nearby_entities_coverage=MineflayerNearbyEntitiesCoverage(
                source_scope=MINEFLAYER_NEARBY_ENTITY_SOURCE_SCOPE,
                max_distance=MINEFLAYER_NEARBY_ENTITY_MAX_DISTANCE,
                max_entities=MINEFLAYER_NEARBY_ENTITY_MAX_ENTITIES,
                candidate_count=len(entities),
                truncated=False,
            ),
        ),
    )


def scenario(*, fight_max_distance: float | None = 3.0) -> ControlledScenario:
    return ControlledScenario(
        hazard_entity_names=frozenset({"zombie"}),
        food_threshold=10,
        edible_item_names=("bread",),
        destinations=(
            ControlledDestination(
                destination_id="cave",
                position=MineflayerPosition(x=10, y=64, z=0),
                description="controlled cave",
                provenance=provenance("destination:cave"),
            ),
        ),
        fight_max_distance=fight_max_distance,
        evidence_timeout_s=0.01,
    )


def intent() -> IntentCommitment:
    commitment = IntentCommitment()
    commitment.commit(
        "intent-survive-fight",
        objective="survive the controlled encounter",
        at_ns=1,
        provenance=provenance("intent"),
    )
    return commitment


def attack_result(
    *,
    result: str = "applied",
    error: str | None = None,
) -> MineflayerEffectResult:
    return MineflayerEffectResult(
        session_id="fight-session",
        seq=2,
        action_id="skill:fight:fight-session:1:attack",
        effect="attack_entity",
        result=result,
        error=error,
    )


def hurt(
    *,
    entity_id: int = 7,
    source_entity_id: int | None = 1,
    actor_entity_id: int = 1,
    seq: int = 3,
) -> MineflayerEntityHurt:
    return MineflayerEntityHurt(
        session_id="fight-session",
        seq=seq,
        entity_id=entity_id,
        source_entity_id=source_entity_id,
        actor_entity_id=actor_entity_id,
    )


class FightSession:
    def __init__(self, messages) -> None:
        self.messages = list(messages)
        self.sent = []

    async def receive(self):
        if self.messages:
            return self.messages.pop(0)
        await asyncio.sleep(3600)
        raise AssertionError("unreachable")

    async def send_attack_entity(self, action_id, *, entity_id):
        self.sent.append(("attack_entity", action_id, entity_id))


def fight_decision() -> ScenarioDecision:
    return ScenarioDecision(
        skill=ControlledSkill.FIGHT,
        reason="explicit deterministic FIGHT test",
        target_entity_id=7,
    )


def test_close_hazard_admits_real_fight_and_flee_candidates() -> None:
    current = observation(entities=(zombie(distance=2),))
    projection = project_controlled_skill_candidates(current, scenario())
    selected = decide_skill(
        current,
        scenario(),
        intent_id="intent-survive-fight",
    )

    assert projection.candidates == (
        ControlledSkill.FIGHT,
        ControlledSkill.FLEE,
    )
    assert selected.skill is ControlledSkill.FLEE


def test_close_hazard_with_hunger_exposes_fight_flee_and_eat() -> None:
    current = observation(
        food=10,
        inventory=(bread(),),
        entities=(zombie(distance=2),),
    )
    projection = project_controlled_skill_candidates(current, scenario())

    assert projection.candidates == (
        ControlledSkill.FIGHT,
        ControlledSkill.FLEE,
        ControlledSkill.EAT,
    )


def test_distant_hazard_keeps_flee_without_fight() -> None:
    current = observation(entities=(zombie(distance=5),))
    projection = project_controlled_skill_candidates(current, scenario())

    assert projection.candidates == (ControlledSkill.FLEE,)


def test_fight_success_requires_matching_self_sourced_hurt_consequence() -> None:
    current = observation(entities=(zombie(distance=2),))
    session = FightSession(
        [
            hurt(seq=2),
            MineflayerEffectResult(
                session_id="fight-session",
                seq=3,
                action_id="skill:fight:fight-session:1:attack",
                effect="attack_entity",
                result="applied",
                error=None,
            ),
        ]
    )
    supervisor = ActionSupervisor()

    result = asyncio.run(
        execute_decision(
            session,
            current,
            scenario(),
            fight_decision(),
            intent_commitment=intent(),
            supervisor=supervisor,
        )
    )

    assert result is not None
    assert result.skill_execution.state is SkillState.SUCCEEDED
    assert [action.state for action in result.actions] == [ActionState.OUTCOME]
    assert session.sent == [
        (
            "attack_entity",
            "skill:fight:fight-session:1:attack",
            7,
        )
    ]
    assert supervisor.open_actions == ()


def test_fight_attack_ack_without_self_sourced_hurt_fails_skill() -> None:
    current = observation(entities=(zombie(distance=2),))
    session = FightSession(
        [
            attack_result(),
            hurt(source_entity_id=9, actor_entity_id=1),
        ]
    )
    supervisor = ActionSupervisor()

    owner = intent()
    result = asyncio.run(
        execute_decision(
            session,
            current,
            scenario(),
            fight_decision(),
            intent_commitment=owner,
            supervisor=supervisor,
        )
    )

    assert result is not None
    assert result.skill_execution.state is SkillState.FAILED
    assert [action.state for action in result.actions] == [ActionState.OUTCOME]
    assert supervisor.open_actions == ()
    assert owner.current_intent is not None
    assert owner.current_intent.intent_id == "intent-survive-fight"


def test_fight_rejected_attack_fails_without_claiming_hurt() -> None:
    current = observation(entities=(zombie(distance=2),))
    session = FightSession(
        [
            attack_result(result="rejected", error="entity_not_found"),
        ]
    )

    result = asyncio.run(
        execute_decision(
            session,
            current,
            scenario(),
            fight_decision(),
            intent_commitment=intent(),
            supervisor=ActionSupervisor(),
        )
    )

    assert result is not None
    assert result.skill_execution.state is SkillState.FAILED
    assert [action.state for action in result.actions] == [ActionState.OUTCOME]
