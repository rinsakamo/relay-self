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
)
from experiments.fight_or_flight_arbitration import (
    arbitrate_fight_or_flight,
    build_fight_or_flight_request,
)
from relay_self.persistent_cognition import Memory
from relay_self.provenance import Provenance
from relay_self.relay_engine import (
    CognitionMode,
    ProviderDecision,
    RelayEngine,
)


def provenance(reference: str) -> Provenance:
    return Provenance(
        source="fight-or-flight-test",
        reference=reference,
    )


def destination(
    destination_id: str,
    *,
    x: float,
    z: float,
) -> ControlledDestination:
    return ControlledDestination(
        destination_id=destination_id,
        position=MineflayerPosition(x=x, y=64, z=z),
        description=f"controlled destination {destination_id}",
        provenance=provenance(f"destination:{destination_id}"),
    )


def scenario(
    *,
    destinations: tuple[ControlledDestination, ...] | None = None,
) -> ControlledScenario:
    return ControlledScenario(
        hazard_entity_names=frozenset({"zombie"}),
        food_threshold=10,
        edible_item_names=("bread",),
        destinations=(
            (destination("cave", x=10, z=0),)
            if destinations is None
            else destinations
        ),
        fight_max_distance=3.0,
    )


def observation() -> MineflayerObservation:
    return MineflayerObservation(
        session_id="fight-or-flight-session",
        seq=1,
        kind="entities",
        snapshot=MineflayerSnapshot(
            health=12,
            food=9,
            food_saturation=4,
            oxygen_level=20,
            position=MineflayerPosition(x=0, y=64, z=0),
            time=None,
            inventory=(
                MineflayerInventoryItem(
                    name="bread",
                    count=2,
                    slot=9,
                ),
            ),
            nearby_entities=(
                MineflayerEntityFact(
                    entity_id=7,
                    name="zombie",
                    entity_type="mob",
                    distance=2,
                    position=MineflayerPosition(x=2, y=64, z=0),
                ),
            ),
            nearby_entities_coverage=MineflayerNearbyEntitiesCoverage(
                source_scope=MINEFLAYER_NEARBY_ENTITY_SOURCE_SCOPE,
                max_distance=MINEFLAYER_NEARBY_ENTITY_MAX_DISTANCE,
                max_entities=MINEFLAYER_NEARBY_ENTITY_MAX_ENTITIES,
                candidate_count=1,
                truncated=False,
            ),
        ),
    )


def memory() -> Memory:
    return Memory(
        memory_id="prior-encounter",
        content="A prior controlled encounter ended after disengaging.",
        source_provenance=Provenance(
            source="mineflayer",
            reference="older-session:44",
        ),
        integration_provenance=provenance("memory-integration"),
    )


class RecordingProvider:
    def __init__(self, decisions: list[ProviderDecision]) -> None:
        self.decisions = list(decisions)
        self.requests = []
        self.modes = []

    def __call__(self, request, *, mode):
        self.requests.append(request)
        self.modes.append(mode)
        return self.decisions.pop(0)


def test_request_is_closed_fight_or_flight_without_affect_labels() -> None:
    request = build_fight_or_flight_request(
        observation(),
        scenario(),
        intent_id="intent-survive",
        retained_memories=(memory(),),
    )

    assert tuple(choice.choice_id for choice in request.choices) == (
        ControlledSkill.FIGHT.value,
        ControlledSkill.FLEE.value,
    )
    assert request.focus == "FIGHT_OR_FLEE"
    assert request.think_allowed is True

    rendered = " ".join(
        [request.instruction]
        + [choice.description for choice in request.choices]
        + [datum.value_json for datum in request.context]
    ).lower()
    assert "fear" not in rendered
    assert "aggression" not in rendered

    memory_datum = next(
        datum
        for datum in request.context
        if datum.key == "memory:prior-encounter"
    )
    assert memory_datum.provenance.reference == "memory-integration"
    assert '"semantic_type":"Memory"' in memory_datum.value_json


def test_bounded_fight_selection_maps_to_grounded_nearest_target() -> None:
    provider = RecordingProvider(
        [ProviderDecision.resolved(ControlledSkill.FIGHT.value)]
    )
    result = arbitrate_fight_or_flight(
        observation(),
        scenario(),
        intent_id="intent-survive",
        relay_engine=RelayEngine(provider),
    )

    assert result.decision is not None
    assert result.decision.skill is ControlledSkill.FIGHT
    assert result.decision.target_entity_id == 7
    assert result.flee_binding_result is None
    assert provider.modes == [CognitionMode.BOUNDED]


def test_unresolved_bounded_arbitration_escalates_same_request_to_think() -> None:
    provider = RecordingProvider(
        [
            ProviderDecision.unresolved(reason="bounded uncertainty"),
            ProviderDecision.resolved(ControlledSkill.FLEE.value),
        ]
    )
    result = arbitrate_fight_or_flight(
        observation(),
        scenario(),
        intent_id="intent-survive",
        relay_engine=RelayEngine(provider),
    )

    assert result.decision is not None
    assert result.decision.skill is ControlledSkill.FLEE
    assert result.decision.destination is not None
    assert result.decision.destination.destination_id == "cave"
    assert provider.modes == [
        CognitionMode.BOUNDED,
        CognitionMode.THINK,
    ]
    assert provider.requests[0] is provider.requests[1]
    assert tuple(
        choice.choice_id
        for choice in provider.requests[0].choices
    ) == ("FIGHT", "FLEE")


def test_flee_destination_binding_remains_a_separate_bounded_problem() -> None:
    provider = RecordingProvider(
        [
            ProviderDecision.resolved(ControlledSkill.FLEE.value),
            ProviderDecision.resolved("ridge"),
        ]
    )
    result = arbitrate_fight_or_flight(
        observation(),
        scenario(
            destinations=(
                destination("cave", x=10, z=0),
                destination("ridge", x=0, z=-10),
            )
        ),
        intent_id="intent-survive",
        relay_engine=RelayEngine(provider),
    )

    assert result.decision is not None
    assert result.decision.skill is ControlledSkill.FLEE
    assert result.decision.destination is not None
    assert result.decision.destination.destination_id == "ridge"
    assert result.flee_binding_result is not None
    assert provider.modes == [
        CognitionMode.BOUNDED,
        CognitionMode.BOUNDED,
    ]
    assert tuple(
        choice.choice_id
        for choice in provider.requests[0].choices
    ) == ("FIGHT", "FLEE")
    assert tuple(
        choice.choice_id
        for choice in provider.requests[1].choices
    ) == ("cave", "ridge")
    assert provider.requests[0] is not provider.requests[1]
