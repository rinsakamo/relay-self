from __future__ import annotations

from dataclasses import dataclass

from adapters.mineflayer.python_protocol import MineflayerObservation
from experiments.controlled_minecraft_vertical import ControlledScenario, ControlledSkill
from experiments.controlled_skill_candidates import project_controlled_skill_candidates
from experiments.fight_or_flight_arbitration import build_fight_or_flight_request
from relay_self.persistent_cognition import Memory


@dataclass(frozen=True, slots=True)
class FightOrFlightReductionTrace:
    """Experiment-local trace of the pre-execution FIGHT/FLEE reduction surface."""

    observation_source: str
    observation_reference: str
    candidate_ids: tuple[str, ...]
    retained_memory_refs: tuple[tuple[str, str, str], ...]
    focus: str | None
    choice_ids: tuple[str, ...]
    context_keys: tuple[str, ...]

    @property
    def topology_signature(self) -> tuple[tuple[str, ...], str | None, tuple[str, ...]]:
        """Return only the bounded choice topology, excluding raw World/history values."""

        return self.candidate_ids, self.focus, self.choice_ids


def capture_fight_or_flight_reduction(
    observation: MineflayerObservation,
    scenario: ControlledScenario,
    *,
    intent_id: str,
    retained_memories: tuple[Memory, ...] = (),
) -> FightOrFlightReductionTrace:
    """Capture the smallest provenance-bearing reduction trace needed by #292 A-C."""

    projection = project_controlled_skill_candidates(observation, scenario)
    candidate_ids = tuple(skill.value for skill in projection.candidates)

    focus: str | None = None
    choice_ids: tuple[str, ...] = ()
    context_keys: tuple[str, ...] = ()

    if (
        ControlledSkill.FIGHT in projection.candidates
        and ControlledSkill.FLEE in projection.candidates
    ):
        request = build_fight_or_flight_request(
            observation,
            scenario,
            intent_id=intent_id,
            retained_memories=retained_memories,
        )
        focus = request.focus
        choice_ids = tuple(choice.choice_id for choice in request.choices)
        context_keys = tuple(datum.key for datum in request.context)

    return FightOrFlightReductionTrace(
        observation_source=observation.provenance.source,
        observation_reference=observation.provenance.reference,
        candidate_ids=candidate_ids,
        retained_memory_refs=tuple(
            (
                memory.memory_id,
                memory.source_provenance.reference,
                memory.integration_provenance.reference,
            )
            for memory in retained_memories
        ),
        focus=focus,
        choice_ids=choice_ids,
        context_keys=context_keys,
    )
