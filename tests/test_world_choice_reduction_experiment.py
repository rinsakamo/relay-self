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
from experiments.world_choice_reduction import capture_fight_or_flight_reduction
from relay_self.persistent_cognition import Memory
from relay_self.provenance import Provenance
from relay_self.relay_engine import CognitionMode, ProviderDecision, RelayEngine


def provenance(reference: str) -> Provenance:
    return Provenance(
        source="world-choice-reduction-test",
        reference=reference,
    )


def destination(destination_id: str, *, x: float, z: float) -> ControlledDestination:
    return ControlledDestination(
        destination_id=destination_id,
        position=MineflayerPosition(x=x, y=64, z=z),
        description=f"controlled destination {destination_id}",
        provenance=provenance(f"destination:{destination_id}"),
    )


def scenario(
    *,
    fight_max_distance: float | None = 3.0,
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
        fight_max_distance=fight_max_distance,
    )


def observation(
    *,
    session_id: str = "world-choice-reduction",
    entity_id: int = 7,
    entity_x: float = 2,
    irrelevant_item_name: str = "dirt",
) -> MineflayerObservation:
    return MineflayerObservation(
        session_id=session_id,
        seq=1,
        kind="entities",
        snapshot=MineflayerSnapshot(
            health=12,
            food=20,
            food_saturation=4,
            oxygen_level=20,
            position=MineflayerPosition(x=0, y=64, z=0),
            time=None,
            inventory=(
                MineflayerInventoryItem(
                    name=irrelevant_item_name,
                    count=1,
                    slot=9,
                ),
            ),
            nearby_entities=(
                MineflayerEntityFact(
                    entity_id=entity_id,
                    name="zombie",
                    entity_type="mob",
                    distance=2,
                    position=MineflayerPosition(x=entity_x, y=64, z=0),
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


def memory(*, outcome: str, source_reference: str, integration_reference: str) -> Memory:
    return Memory(
        memory_id="prior-encounter",
        content=outcome,
        source_provenance=Provenance(
            source="mineflayer",
            reference=source_reference,
        ),
        integration_provenance=provenance(integration_reference),
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


def _datum_signature(request, *, include_memory: bool) -> tuple[tuple[str, str, str, str], ...]:
    return tuple(
        (
            datum.key,
            datum.value_json,
            datum.provenance.source,
            datum.provenance.reference,
        )
        for datum in request.context
        if include_memory == datum.key.startswith("memory:")
    )


def test_a_different_world_inputs_preserve_fight_or_flight_topology() -> None:
    first = observation(
        session_id="world-a",
        entity_id=7,
        entity_x=2,
        irrelevant_item_name="dirt",
    )
    second = observation(
        session_id="world-b",
        entity_id=91,
        entity_x=-2,
        irrelevant_item_name="stone",
    )
    controlled = scenario()

    first_trace = capture_fight_or_flight_reduction(
        first,
        controlled,
        intent_id="intent-survive",
    )
    second_trace = capture_fight_or_flight_reduction(
        second,
        controlled,
        intent_id="intent-survive",
    )

    assert first_trace.observation_reference != second_trace.observation_reference
    assert first_trace.topology_signature == second_trace.topology_signature
    assert first_trace.topology_signature == (
        (ControlledSkill.FIGHT.value, ControlledSkill.FLEE.value),
        "FIGHT_OR_FLEE",
        (ControlledSkill.FIGHT.value, ControlledSkill.FLEE.value),
    )

    first_request = build_fight_or_flight_request(
        first,
        controlled,
        intent_id="intent-survive",
    )
    second_request = build_fight_or_flight_request(
        second,
        controlled,
        intent_id="intent-survive",
    )
    assert first_request.context != second_request.context
    assert tuple(datum.key for datum in first_request.context) == tuple(
        datum.key for datum in second_request.context
    )


def test_b_same_world_changes_reduction_when_existing_fight_capability_changes() -> None:
    current = observation()
    fight_enabled = capture_fight_or_flight_reduction(
        current,
        scenario(fight_max_distance=3.0),
        intent_id="intent-survive",
    )
    fight_unavailable = capture_fight_or_flight_reduction(
        current,
        scenario(fight_max_distance=None),
        intent_id="intent-survive",
    )

    assert fight_enabled.observation_reference == fight_unavailable.observation_reference
    assert fight_enabled.candidate_ids == (
        ControlledSkill.FIGHT.value,
        ControlledSkill.FLEE.value,
    )
    assert fight_enabled.focus == "FIGHT_OR_FLEE"
    assert fight_unavailable.candidate_ids == (ControlledSkill.FLEE.value,)
    assert fight_unavailable.focus is None
    assert fight_unavailable.choice_ids == ()


def test_b_same_world_projects_different_memory_without_claiming_selection_effect() -> None:
    current = observation()
    controlled = scenario()
    prior_success = memory(
        outcome="A prior FIGHT attempt produced a grounded successful consequence.",
        source_reference="older-session:success",
        integration_reference="memory:success",
    )
    prior_failure = memory(
        outcome="A prior FIGHT attempt produced a grounded bad consequence.",
        source_reference="older-session:failure",
        integration_reference="memory:failure",
    )

    success_trace = capture_fight_or_flight_reduction(
        current,
        controlled,
        intent_id="intent-survive",
        retained_memories=(prior_success,),
    )
    failure_trace = capture_fight_or_flight_reduction(
        current,
        controlled,
        intent_id="intent-survive",
        retained_memories=(prior_failure,),
    )

    assert success_trace.observation_reference == failure_trace.observation_reference
    assert success_trace.topology_signature == failure_trace.topology_signature
    assert success_trace.retained_memory_refs != failure_trace.retained_memory_refs

    success_request = build_fight_or_flight_request(
        current,
        controlled,
        intent_id="intent-survive",
        retained_memories=(prior_success,),
    )
    failure_request = build_fight_or_flight_request(
        current,
        controlled,
        intent_id="intent-survive",
        retained_memories=(prior_failure,),
    )

    assert _datum_signature(success_request, include_memory=False) == _datum_signature(
        failure_request,
        include_memory=False,
    )
    assert _datum_signature(success_request, include_memory=True) != _datum_signature(
        failure_request,
        include_memory=True,
    )


def test_c_same_candidate_set_allows_different_downstream_binding_geometry() -> None:
    current = observation()
    one_destination = scenario(
        destinations=(destination("cave", x=10, z=0),),
    )
    two_destinations = scenario(
        destinations=(
            destination("cave", x=10, z=0),
            destination("ridge", x=0, z=-10),
        ),
    )

    one_trace = capture_fight_or_flight_reduction(
        current,
        one_destination,
        intent_id="intent-survive",
    )
    two_trace = capture_fight_or_flight_reduction(
        current,
        two_destinations,
        intent_id="intent-survive",
    )
    assert one_trace.topology_signature == two_trace.topology_signature

    direct_provider = RecordingProvider(
        [ProviderDecision.resolved(ControlledSkill.FLEE.value)]
    )
    bounded_provider = RecordingProvider(
        [
            ProviderDecision.resolved(ControlledSkill.FLEE.value),
            ProviderDecision.resolved("ridge"),
        ]
    )

    direct = arbitrate_fight_or_flight(
        current,
        one_destination,
        intent_id="intent-survive",
        relay_engine=RelayEngine(direct_provider),
    )
    bounded = arbitrate_fight_or_flight(
        current,
        two_destinations,
        intent_id="intent-survive",
        relay_engine=RelayEngine(bounded_provider),
    )

    assert direct.decision is not None
    assert bounded.decision is not None
    assert direct.decision.skill is bounded.decision.skill is ControlledSkill.FLEE
    assert direct.decision.destination is not None
    assert bounded.decision.destination is not None
    assert direct.decision.destination.destination_id == "cave"
    assert bounded.decision.destination.destination_id == "ridge"

    assert direct.flee_binding_result is None
    assert bounded.flee_binding_result is not None
    assert direct_provider.modes == [CognitionMode.BOUNDED]
    assert bounded_provider.modes == [
        CognitionMode.BOUNDED,
        CognitionMode.BOUNDED,
    ]
    assert tuple(
        choice.choice_id
        for choice in bounded_provider.requests[1].choices
    ) == ("cave", "ridge")
