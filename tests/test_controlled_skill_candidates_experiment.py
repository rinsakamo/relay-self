from adapters.mineflayer.python_protocol import (
    MINEFLAYER_NEARBY_ENTITY_MAX_DISTANCE,
    MINEFLAYER_NEARBY_ENTITY_MAX_ENTITIES,
    MINEFLAYER_NEARBY_ENTITY_SOURCE_SCOPE,
    MineflayerEntityFact,
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
    decide_skill,
)
from experiments.controlled_skill_candidates import (
    project_controlled_skill_candidates,
)
from relay_self.provenance import Provenance


def provenance(reference: str) -> Provenance:
    return Provenance(source="controlled-skill-candidate-test", reference=reference)


def scenario() -> ControlledScenario:
    return ControlledScenario(
        hazard_entity_names=frozenset({"zombie"}),
        food_threshold=10,
        edible_item_names=("bread", "cooked_beef"),
        destinations=(
            ControlledDestination(
                destination_id="cave",
                position=MineflayerPosition(x=10, y=64, z=0),
                description="controlled cave",
                provenance=provenance("destination:cave"),
            ),
        ),
    )


def zombie() -> MineflayerEntityFact:
    return MineflayerEntityFact(
        entity_id=7,
        name="zombie",
        entity_type="mob",
        distance=3,
        position=MineflayerPosition(x=3, y=64, z=0),
    )


def cow() -> MineflayerEntityFact:
    return MineflayerEntityFact(
        entity_id=8,
        name="cow",
        entity_type="mob",
        distance=3,
        position=MineflayerPosition(x=3, y=64, z=0),
    )


def bread() -> MineflayerInventoryItem:
    return MineflayerInventoryItem(name="bread", count=2, slot=9)


def observation(
    *,
    food: float = 20,
    inventory: tuple[MineflayerInventoryItem, ...] = (),
    entities: tuple[MineflayerEntityFact, ...] = (),
) -> MineflayerObservation:
    return MineflayerObservation(
        session_id="candidate-session",
        seq=1,
        kind="health",
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


def test_ordinary_state_projects_wait_and_selector_agrees() -> None:
    current = observation()
    projection = project_controlled_skill_candidates(current, scenario())
    selected = decide_skill(current, scenario(), intent_id="intent-survive")

    assert projection.candidates == (ControlledSkill.WAIT,)
    assert selected.skill is ControlledSkill.WAIT


def test_low_food_with_edible_projects_eat_and_selector_agrees() -> None:
    current = observation(food=10, inventory=(bread(),))
    projection = project_controlled_skill_candidates(current, scenario())
    selected = decide_skill(current, scenario(), intent_id="intent-survive")

    assert projection.candidates == (ControlledSkill.EAT,)
    assert selected.skill is ControlledSkill.EAT
    assert selected.item_name == "bread"


def test_hazard_projects_flee_and_selector_agrees() -> None:
    current = observation(entities=(zombie(),))
    projection = project_controlled_skill_candidates(current, scenario())
    selected = decide_skill(current, scenario(), intent_id="intent-survive")

    assert projection.candidates == (ControlledSkill.FLEE,)
    assert selected.skill is ControlledSkill.FLEE
    assert selected.destination is not None
    assert selected.destination.destination_id == "cave"


def test_hazard_and_low_food_expose_two_real_candidates_before_priority_selection() -> None:
    current = observation(
        food=10,
        inventory=(bread(),),
        entities=(zombie(),),
    )
    projection = project_controlled_skill_candidates(current, scenario())
    selected = decide_skill(current, scenario(), intent_id="intent-survive")

    assert projection.candidates == (
        ControlledSkill.FLEE,
        ControlledSkill.EAT,
    )
    assert projection.admits(ControlledSkill.FLEE)
    assert projection.admits(ControlledSkill.EAT)
    assert not projection.admits(ControlledSkill.WAIT)

    # Existing controlled selector priority remains unchanged.
    assert selected.skill is ControlledSkill.FLEE


def test_non_hazard_entity_does_not_create_flee_candidate() -> None:
    current = observation(
        food=10,
        inventory=(bread(),),
        entities=(cow(),),
    )
    projection = project_controlled_skill_candidates(current, scenario())
    selected = decide_skill(current, scenario(), intent_id="intent-survive")

    assert projection.candidates == (ControlledSkill.EAT,)
    assert selected.skill is ControlledSkill.EAT


def test_low_food_without_configured_edible_falls_back_to_wait() -> None:
    current = observation(food=10)
    projection = project_controlled_skill_candidates(current, scenario())
    selected = decide_skill(current, scenario(), intent_id="intent-survive")

    assert projection.candidates == (ControlledSkill.WAIT,)
    assert selected.skill is ControlledSkill.WAIT
