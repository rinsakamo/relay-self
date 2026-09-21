from __future__ import annotations

from dataclasses import dataclass
from typing import Callable

from adapters.mineflayer.python_protocol import MineflayerObservation
from experiments.controlled_minecraft_vertical import (
    ControlledScenario,
    ControlledScenarioError,
    ControlledSkill,
    ScenarioDecision,
    build_flee_destination_request,
)
from experiments.controlled_skill_candidates import (
    project_controlled_skill_candidates,
)
from relay_self.persistent_cognition import Memory
from relay_self.relay_engine import (
    BoundedChoice,
    BoundedChoiceRequest,
    CognitionDatum,
    DecisionStatus,
    RelayEngineResult,
)

RelayEngineCallable = Callable[[BoundedChoiceRequest], RelayEngineResult]


@dataclass(frozen=True, slots=True)
class FightOrFlightResult:
    arbitration_result: RelayEngineResult
    decision: ScenarioDecision | None
    flee_binding_result: RelayEngineResult | None = None


def build_fight_or_flight_request(
    observation: MineflayerObservation,
    scenario: ControlledScenario,
    *,
    intent_id: str,
    retained_memories: tuple[Memory, ...] = (),
) -> BoundedChoiceRequest:
    """Build one finite Skill arbitration over already-grounded candidates."""

    if not isinstance(observation, MineflayerObservation):
        raise ControlledScenarioError(
            "fight-or-flight arbitration requires MineflayerObservation"
        )
    if not isinstance(scenario, ControlledScenario):
        raise ControlledScenarioError(
            "fight-or-flight arbitration requires ControlledScenario"
        )
    if not isinstance(intent_id, str) or not intent_id.strip():
        raise ControlledScenarioError("intent_id must be non-empty text")
    if not isinstance(retained_memories, tuple) or not all(
        isinstance(memory, Memory)
        for memory in retained_memories
    ):
        raise ControlledScenarioError(
            "retained_memories must be a tuple of Memory values"
        )

    candidates = project_controlled_skill_candidates(
        observation,
        scenario,
    ).candidates
    if (
        ControlledSkill.FIGHT not in candidates
        or ControlledSkill.FLEE not in candidates
    ):
        raise ControlledScenarioError(
            "fight-or-flight arbitration requires grounded FIGHT and FLEE candidates"
        )
    if scenario.fight_max_distance is None:
        raise ControlledScenarioError(
            "fight-or-flight arbitration requires enabled fight capability"
        )

    snapshot = observation.snapshot
    evidence = observation.provenance
    context: list[CognitionDatum] = [
        CognitionDatum.from_value(
            "health",
            snapshot.health,
            evidence,
        ),
        CognitionDatum.from_value(
            "food",
            snapshot.food,
            evidence,
        ),
        CognitionDatum.from_value(
            "position",
            {
                "x": snapshot.position.x,
                "y": snapshot.position.y,
                "z": snapshot.position.z,
            },
            evidence,
        ),
        CognitionDatum.from_value(
            "inventory",
            [
                {
                    "name": item.name,
                    "count": item.count,
                    "slot": item.slot,
                }
                for item in snapshot.inventory
            ],
            evidence,
        ),
        CognitionDatum.from_value(
            "configured_hazards",
            [
                {
                    "entity_id": entity.entity_id,
                    "name": entity.name,
                    "type": entity.entity_type,
                    "distance": entity.distance,
                    "position": {
                        "x": entity.position.x,
                        "y": entity.position.y,
                        "z": entity.position.z,
                    },
                }
                for entity in snapshot.nearby_entities
                if entity.name in scenario.hazard_entity_names
            ],
            evidence,
        ),
        CognitionDatum.from_value(
            "fight_max_distance",
            scenario.fight_max_distance,
            evidence,
        ),
    ]

    for destination in scenario.destinations:
        context.append(
            CognitionDatum.from_value(
                f"destination:{destination.destination_id}",
                {
                    "position": {
                        "x": destination.position.x,
                        "y": destination.position.y,
                        "z": destination.position.z,
                    },
                    "description": destination.description,
                },
                destination.provenance,
            )
        )

    for memory in retained_memories:
        context.append(
            CognitionDatum.from_value(
                f"memory:{memory.memory_id}",
                {
                    "semantic_type": "Memory",
                    "content": memory.content,
                    "source_provenance": {
                        "source": memory.source_provenance.source,
                        "reference": memory.source_provenance.reference,
                    },
                },
                memory.integration_provenance,
            )
        )

    return BoundedChoiceRequest(
        request_id=(
            f"controlled-fight-or-flight:"
            f"{observation.session_id}:{observation.seq}"
        ),
        instruction=(
            "Choose which currently grounded controlled Skill to use for this "
            "encounter. Treat current Mineflayer facts as current evidence and "
            "retained Memory only as prior experience, not fresh World truth."
        ),
        intent_id=intent_id,
        focus="FIGHT_OR_FLEE",
        choices=(
            BoundedChoice(
                ControlledSkill.FIGHT.value,
                (
                    "Engage one currently observed configured hazard within "
                    "the enabled fight range."
                ),
            ),
            BoundedChoice(
                ControlledSkill.FLEE.value,
                "Disengage toward a configured controlled destination.",
            ),
        ),
        context=tuple(context),
        soft_wall_time_budget_s=scenario.cognition_soft_wall_time_budget_s,
        think_allowed=scenario.cognition_think_allowed,
    )


def arbitrate_fight_or_flight(
    observation: MineflayerObservation,
    scenario: ControlledScenario,
    *,
    intent_id: str,
    relay_engine: RelayEngineCallable,
    retained_memories: tuple[Memory, ...] = (),
) -> FightOrFlightResult:
    """Resolve Skill arbitration, then bind only the selected Skill's parameter."""

    request = build_fight_or_flight_request(
        observation,
        scenario,
        intent_id=intent_id,
        retained_memories=retained_memories,
    )
    result = relay_engine(request)
    if (
        result.status is not DecisionStatus.RESOLVED
        or result.choice_id is None
    ):
        return FightOrFlightResult(
            arbitration_result=result,
            decision=None,
        )

    if result.choice_id == ControlledSkill.FIGHT.value:
        assert scenario.fight_max_distance is not None
        targets = tuple(
            entity
            for entity in observation.snapshot.nearby_entities
            if (
                entity.name in scenario.hazard_entity_names
                and entity.distance <= scenario.fight_max_distance
            )
        )
        if not targets:
            raise ControlledScenarioError(
                "resolved FIGHT has no currently grounded target"
            )
        target = min(
            targets,
            key=lambda entity: (entity.distance, entity.entity_id),
        )
        return FightOrFlightResult(
            arbitration_result=result,
            decision=ScenarioDecision(
                skill=ControlledSkill.FIGHT,
                reason=(
                    "RelayEngine selected FIGHT from the finite grounded "
                    "fight-or-flight candidate set"
                ),
                target_entity_id=target.entity_id,
                cognition_result=result,
            ),
        )

    if result.choice_id != ControlledSkill.FLEE.value:
        raise ControlledScenarioError(
            "RelayEngine resolved outside FIGHT/FLEE arbitration"
        )

    if not scenario.destinations:
        return FightOrFlightResult(
            arbitration_result=result,
            decision=ScenarioDecision(
                skill=ControlledSkill.FLEE,
                reason=(
                    "RelayEngine selected FLEE but no controlled destination "
                    "is currently available"
                ),
                cognition_result=result,
            ),
        )

    if len(scenario.destinations) == 1:
        return FightOrFlightResult(
            arbitration_result=result,
            decision=ScenarioDecision(
                skill=ControlledSkill.FLEE,
                reason=(
                    "RelayEngine selected FLEE and exactly one controlled "
                    "destination is available"
                ),
                destination=scenario.destinations[0],
                cognition_result=result,
            ),
        )

    flee_request = build_flee_destination_request(
        observation,
        scenario,
        intent_id=intent_id,
        retained_memories=retained_memories,
    )
    flee_result = relay_engine(flee_request)
    destination = None
    if (
        flee_result.status is DecisionStatus.RESOLVED
        and flee_result.choice_id is not None
    ):
        destination = next(
            (
                candidate
                for candidate in scenario.destinations
                if candidate.destination_id == flee_result.choice_id
            ),
            None,
        )
        if destination is None:
            raise ControlledScenarioError(
                "FLEE parameter binding resolved outside configured destinations"
            )

    return FightOrFlightResult(
        arbitration_result=result,
        decision=ScenarioDecision(
            skill=ControlledSkill.FLEE,
            reason=(
                "RelayEngine selected FLEE; destination binding remained a "
                "separate Skill-local bounded decision"
            ),
            destination=destination,
            cognition_result=flee_result,
        ),
        flee_binding_result=flee_result,
    )
