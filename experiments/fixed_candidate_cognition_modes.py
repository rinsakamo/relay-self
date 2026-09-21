from __future__ import annotations

from dataclasses import dataclass

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
    ScenarioDecision,
    decide_skill,
)
from experiments.controlled_skill_candidates import (
    ControlledSkillCandidateProjection,
    project_controlled_skill_candidates,
)
from relay_self.provenance import Provenance
from relay_self.relay_engine import (
    BoundedChoiceRequest,
    CognitionMode,
    DecisionStatus,
    ProviderDecision,
    RelayEngine,
)


@dataclass(frozen=True, slots=True)
class FixedCandidateModeObservation:
    candidates: ControlledSkillCandidateProjection
    decision: ScenarioDecision
    provider_modes: tuple[CognitionMode, ...]
    provider_requests: tuple[BoundedChoiceRequest, ...]


class RecordingProvider:
    def __init__(
        self,
        *,
        bounded_choice: str | None,
        think_choice: str | None,
    ) -> None:
        self.bounded_choice = bounded_choice
        self.think_choice = think_choice
        self.calls: list[tuple[BoundedChoiceRequest, CognitionMode]] = []

    def __call__(
        self,
        request: BoundedChoiceRequest,
        *,
        mode: CognitionMode,
    ) -> ProviderDecision:
        self.calls.append((request, mode))
        if mode is CognitionMode.BOUNDED:
            if self.bounded_choice is None:
                return ProviderDecision.unresolved(
                    reason="bounded fixture unresolved",
                )
            return ProviderDecision.resolved(
                self.bounded_choice,
                reason="bounded fixture resolved",
            )
        if mode is CognitionMode.THINK:
            if self.think_choice is None:
                return ProviderDecision.unresolved(
                    reason="think fixture unresolved",
                )
            return ProviderDecision.resolved(
                self.think_choice,
                reason="think fixture resolved",
            )
        raise AssertionError("fixed-candidate fixture must not invoke OPEN")


def _provenance(reference: str) -> Provenance:
    return Provenance(
        source="fixed-candidate-mode-fixture",
        reference=reference,
    )


def _destination(
    destination_id: str,
    *,
    x: float,
    z: float,
) -> ControlledDestination:
    return ControlledDestination(
        destination_id=destination_id,
        position=MineflayerPosition(x=x, y=64, z=z),
        description=f"controlled destination {destination_id}",
        provenance=_provenance(f"destination:{destination_id}"),
    )


def _scenario(
    *,
    destinations: tuple[ControlledDestination, ...],
) -> ControlledScenario:
    return ControlledScenario(
        hazard_entity_names=frozenset({"zombie"}),
        food_threshold=10,
        edible_item_names=("bread",),
        destinations=destinations,
    )


def shared_candidate_observation() -> MineflayerObservation:
    """Return one grounded state that simultaneously admits FLEE and EAT."""

    zombie = MineflayerEntityFact(
        entity_id=7,
        name="zombie",
        entity_type="mob",
        distance=3,
        position=MineflayerPosition(x=3, y=64, z=0),
    )
    bread = MineflayerInventoryItem(
        name="bread",
        count=2,
        slot=9,
    )
    return MineflayerObservation(
        session_id="fixed-candidate-session",
        seq=1,
        kind="health",
        snapshot=MineflayerSnapshot(
            health=20,
            food=10,
            food_saturation=5,
            oxygen_level=20,
            position=MineflayerPosition(x=0, y=64, z=0),
            time=None,
            inventory=(bread,),
            nearby_entities=(zombie,),
            nearby_entities_coverage=MineflayerNearbyEntitiesCoverage(
                source_scope=MINEFLAYER_NEARBY_ENTITY_SOURCE_SCOPE,
                max_distance=MINEFLAYER_NEARBY_ENTITY_MAX_DISTANCE,
                max_entities=MINEFLAYER_NEARBY_ENTITY_MAX_ENTITIES,
                candidate_count=1,
                truncated=False,
            ),
        ),
    )


def direct_no_model_case() -> FixedCandidateModeObservation:
    observation = shared_candidate_observation()
    scenario = _scenario(
        destinations=(
            _destination("cave", x=10, z=0),
        ),
    )
    candidates = project_controlled_skill_candidates(observation, scenario)
    decision = decide_skill(
        observation,
        scenario,
        intent_id="intent-survive",
    )
    return FixedCandidateModeObservation(
        candidates=candidates,
        decision=decision,
        provider_modes=(),
        provider_requests=(),
    )


def closed_system_one_case() -> FixedCandidateModeObservation:
    observation = shared_candidate_observation()
    scenario = _scenario(
        destinations=(
            _destination("cave", x=10, z=0),
            _destination("ridge", x=0, z=10),
        ),
    )
    candidates = project_controlled_skill_candidates(observation, scenario)
    provider = RecordingProvider(
        bounded_choice="cave",
        think_choice=None,
    )
    decision = decide_skill(
        observation,
        scenario,
        intent_id="intent-survive",
        relay_engine=RelayEngine(provider),
    )
    return FixedCandidateModeObservation(
        candidates=candidates,
        decision=decision,
        provider_modes=tuple(mode for _, mode in provider.calls),
        provider_requests=tuple(request for request, _ in provider.calls),
    )


def closed_system_two_case() -> FixedCandidateModeObservation:
    observation = shared_candidate_observation()
    scenario = _scenario(
        destinations=(
            _destination("cave", x=10, z=0),
            _destination("ridge", x=0, z=10),
        ),
    )
    candidates = project_controlled_skill_candidates(observation, scenario)
    provider = RecordingProvider(
        bounded_choice=None,
        think_choice="cave",
    )
    decision = decide_skill(
        observation,
        scenario,
        intent_id="intent-survive",
        relay_engine=RelayEngine(provider),
    )
    return FixedCandidateModeObservation(
        candidates=candidates,
        decision=decision,
        provider_modes=tuple(mode for _, mode in provider.calls),
        provider_requests=tuple(request for request, _ in provider.calls),
    )


def reference_cases() -> tuple[FixedCandidateModeObservation, ...]:
    cases = (
        direct_no_model_case(),
        closed_system_one_case(),
        closed_system_two_case(),
    )
    for case in cases:
        if case.candidates.candidates != (
            ControlledSkill.FLEE,
            ControlledSkill.EAT,
        ):
            raise AssertionError(
                "reference cases must preserve the same real candidate set"
            )
        if case.decision.skill is not ControlledSkill.FLEE:
            raise AssertionError(
                "current controlled selector must preserve FLEE priority"
            )
    return cases
