from __future__ import annotations

from dataclasses import dataclass

from adapters.mineflayer.python_protocol import MineflayerObservation
from experiments.controlled_minecraft_vertical import (
    ControlledScenario,
    ControlledScenarioError,
    ControlledSkill,
)


@dataclass(frozen=True, slots=True)
class ControlledSkillCandidateProjection:
    """Experiment-local candidate set before controlled Skill selection."""

    candidates: tuple[ControlledSkill, ...]

    def __post_init__(self) -> None:
        if not self.candidates:
            raise ControlledScenarioError(
                "controlled Skill candidate projection cannot be empty"
            )
        if len(set(self.candidates)) != len(self.candidates):
            raise ControlledScenarioError(
                "controlled Skill candidate projection cannot contain duplicates"
            )

    def admits(self, skill: ControlledSkill) -> bool:
        return skill in self.candidates


def project_controlled_skill_candidates(
    observation: MineflayerObservation,
    scenario: ControlledScenario,
) -> ControlledSkillCandidateProjection:
    """Project real controlled-Minecraft candidates without selecting a winner."""

    if not isinstance(observation, MineflayerObservation):
        raise ControlledScenarioError(
            "candidate projection requires MineflayerObservation"
        )
    if not isinstance(scenario, ControlledScenario):
        raise ControlledScenarioError(
            "candidate projection requires ControlledScenario"
        )

    snapshot = observation.snapshot
    candidates: list[ControlledSkill] = []

    hazards = tuple(
        entity
        for entity in snapshot.nearby_entities
        if entity.name in scenario.hazard_entity_names
    )
    if (
        scenario.fight_max_distance is not None
        and any(
            entity.distance <= scenario.fight_max_distance
            for entity in hazards
        )
    ):
        candidates.append(ControlledSkill.FIGHT)

    if hazards:
        candidates.append(ControlledSkill.FLEE)

    if snapshot.food <= scenario.food_threshold:
        inventory_names = {
            item.name
            for item in snapshot.inventory
            if item.count > 0
        }
        if any(
            item_name in inventory_names
            for item_name in scenario.edible_item_names
        ):
            candidates.append(ControlledSkill.EAT)

    if not candidates:
        candidates.append(ControlledSkill.WAIT)

    return ControlledSkillCandidateProjection(tuple(candidates))
