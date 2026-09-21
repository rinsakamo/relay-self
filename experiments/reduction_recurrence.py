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
from relay_self.appraisal import (
    AppraisalAspect,
    AppraisalBias,
    AppraisalDisposition,
    AppraisalTargetKind,
    project_entity_appraisal,
)
from relay_self.persistent_cognition import (
    IdentitySpecification,
    PersistentCognition,
)
from relay_self.provenance import Provenance


@dataclass(frozen=True, slots=True)
class AppraisalDispositionTrace:
    """Full provenance-bearing appraisal input used by one reduction episode."""

    target_kind: str
    target_key: str
    aspect: str
    bias: str
    source_reference: str
    integration_reference: str

    @property
    def structural_signature(self) -> tuple[str, str, str]:
        """Drop only episode identity/provenance, not appraisal semantics."""

        return self.target_kind, self.aspect, self.bias


@dataclass(frozen=True, slots=True)
class WorldSignature:
    """Exact current observation facts used by the deterministic baseline."""

    session_id: str
    seq: int
    health: float
    food: float
    food_saturation: float
    oxygen_level: float
    position: tuple[float, float, float]
    inventory: tuple[tuple[str, int, int], ...]
    entities: tuple[
        tuple[int, str | None, str | None, float, tuple[float, float, float]],
        ...,
    ]


@dataclass(frozen=True, slots=True)
class ReductionEpisodeTrace:
    """Experiment-local World/history -> choice-space trace for #297."""

    episode_id: str
    observation_reference: str
    world_signature: WorldSignature
    raw_body_signature: tuple[float, float, float, float]
    active_appraisal: tuple[AppraisalDispositionTrace, ...]
    selected_skill: str
    parameter_topology: str

    @property
    def appraisal_structure(self) -> tuple[tuple[str, str, str], ...]:
        return tuple(
            disposition.structural_signature
            for disposition in self.active_appraisal
        )

    @property
    def reduction_signature(
        self,
    ) -> tuple[tuple[tuple[str, str, str], ...], str, str]:
        """Exact structural equivalence class; no embedding or similarity threshold."""

        return (
            self.appraisal_structure,
            self.selected_skill,
            self.parameter_topology,
        )


@dataclass(frozen=True, slots=True)
class ReductionRecurrenceAnalysis:
    class_prior_a: ReductionEpisodeTrace
    class_prior_b: ReductionEpisodeTrace
    experienced_a: ReductionEpisodeTrace
    experienced_b: ReductionEpisodeTrace

    @property
    def different_world_same_reduction(self) -> bool:
        return (
            self.class_prior_a.world_signature
            != self.class_prior_b.world_signature
            and self.class_prior_a.reduction_signature
            == self.class_prior_b.reduction_signature
        )

    @property
    def same_world_history_changes_reduction(self) -> bool:
        return (
            self.class_prior_a.world_signature
            == self.experienced_a.world_signature
            and self.class_prior_a.active_appraisal
            != self.experienced_a.active_appraisal
            and self.class_prior_a.reduction_signature
            != self.experienced_a.reduction_signature
        )

    @property
    def history_shaped_reduction_recurs(self) -> bool:
        return (
            self.experienced_a.world_signature
            != self.experienced_b.world_signature
            and self.experienced_a.active_appraisal
            != self.experienced_b.active_appraisal
            and self.experienced_a.reduction_signature
            == self.experienced_b.reduction_signature
        )

    @property
    def current_state_only_falsified(self) -> bool:
        return (
            self.class_prior_a.world_signature
            == self.experienced_a.world_signature
            and self.class_prior_a.selected_skill
            != self.experienced_a.selected_skill
        )

    @property
    def raw_body_only_falsified(self) -> bool:
        return (
            self.class_prior_a.raw_body_signature
            == self.experienced_a.raw_body_signature
            and self.class_prior_a.selected_skill
            != self.experienced_a.selected_skill
        )

    @property
    def recurring_structure_has_downstream_skill_relevance(self) -> bool:
        return (
            self.class_prior_a.appraisal_structure
            == self.class_prior_b.appraisal_structure
            and self.experienced_a.appraisal_structure
            == self.experienced_b.appraisal_structure
            and self.class_prior_a.appraisal_structure
            != self.experienced_a.appraisal_structure
            and self.class_prior_a.selected_skill
            == self.class_prior_b.selected_skill
            == ControlledSkill.FLEE.value
            and self.experienced_a.selected_skill
            == self.experienced_b.selected_skill
            == ControlledSkill.WAIT.value
        )


def capture_appraisal_reduction(
    *,
    episode_id: str,
    observation: MineflayerObservation,
    scenario: ControlledScenario,
    cognition: PersistentCognition,
    intent_id: str,
) -> ReductionEpisodeTrace:
    """Capture one exact appraisal-conditioned controlled decision epoch."""

    if len(observation.snapshot.nearby_entities) != 1:
        raise ValueError("reference reduction requires exactly one nearby entity")

    entity = observation.snapshot.nearby_entities[0]
    entity_class = entity.name or entity.entity_type
    if entity_class is None:
        raise ValueError("reference entity requires a class/name")

    entity_instance = f"{observation.session_id}:entity-{entity.entity_id}"
    appraisal = project_entity_appraisal(
        entity_class=entity_class,
        entity_instance=entity_instance,
        observation_provenance=observation.provenance,
        dispositions=cognition.appraisal_dispositions,
    )
    decision = decide_skill(
        observation,
        scenario,
        intent_id=intent_id,
        persistent_cognition=cognition,
    )

    return ReductionEpisodeTrace(
        episode_id=episode_id,
        observation_reference=observation.provenance.reference,
        world_signature=_world_signature(observation),
        raw_body_signature=(
            observation.snapshot.health,
            observation.snapshot.food,
            observation.snapshot.food_saturation,
            observation.snapshot.oxygen_level,
        ),
        active_appraisal=tuple(
            AppraisalDispositionTrace(
                target_kind=disposition.target_kind.value,
                target_key=disposition.target_key,
                aspect=disposition.aspect.value,
                bias=disposition.bias.value,
                source_reference=disposition.source_provenance.reference,
                integration_reference=disposition.integration_provenance.reference,
            )
            for disposition in appraisal.active_dispositions
        ),
        selected_skill=decision.skill.value,
        parameter_topology=_parameter_topology(decision),
    )


def reference_analysis() -> ReductionRecurrenceAnalysis:
    """Run the bounded exact-recurrence reference surface with zero provider calls."""

    first = _observation(
        session_id="reduction-a",
        entity_id=7,
        entity_x=2,
        irrelevant_item_name="dirt",
    )
    second = _observation(
        session_id="reduction-b",
        entity_id=91,
        entity_x=-2,
        irrelevant_item_name="stone",
    )
    controlled = _scenario_without_world_hazards()
    class_prior = _self_with_class_harm_prior()
    experienced_first = _with_instance_neutral_experience(
        class_prior,
        instance_key="reduction-a:entity-7",
        source_reference="history:reduction-a:entity-7",
        integration_reference="integration:reduction-a:entity-7",
    )
    experienced_second = _with_instance_neutral_experience(
        class_prior,
        instance_key="reduction-b:entity-91",
        source_reference="history:reduction-b:entity-91",
        integration_reference="integration:reduction-b:entity-91",
    )

    return ReductionRecurrenceAnalysis(
        class_prior_a=capture_appraisal_reduction(
            episode_id="class-prior-a",
            observation=first,
            scenario=controlled,
            cognition=class_prior,
            intent_id="intent-survive",
        ),
        class_prior_b=capture_appraisal_reduction(
            episode_id="class-prior-b",
            observation=second,
            scenario=controlled,
            cognition=class_prior,
            intent_id="intent-survive",
        ),
        experienced_a=capture_appraisal_reduction(
            episode_id="experienced-a",
            observation=first,
            scenario=controlled,
            cognition=experienced_first,
            intent_id="intent-survive",
        ),
        experienced_b=capture_appraisal_reduction(
            episode_id="experienced-b",
            observation=second,
            scenario=controlled,
            cognition=experienced_second,
            intent_id="intent-survive",
        ),
    )


def _self_with_class_harm_prior() -> PersistentCognition:
    identity = IdentitySpecification(
        self_id="reduction-self",
        directives=("Preserve continued agency.",),
        provenance=_provenance("identity"),
    )
    prior = AppraisalDisposition(
        target_kind=AppraisalTargetKind.ENTITY_CLASS,
        target_key="zombie",
        aspect=AppraisalAspect.HARM_LIKELIHOOD,
        bias=AppraisalBias.UP,
        source_provenance=identity.provenance,
        integration_provenance=_provenance("soul-seed"),
    )
    return PersistentCognition(
        identity=identity,
    ).seed_appraisal_disposition(prior)


def _with_instance_neutral_experience(
    cognition: PersistentCognition,
    *,
    instance_key: str,
    source_reference: str,
    integration_reference: str,
) -> PersistentCognition:
    return cognition.integrate_appraisal_disposition(
        AppraisalDisposition(
            target_kind=AppraisalTargetKind.ENTITY_INSTANCE,
            target_key=instance_key,
            aspect=AppraisalAspect.HARM_LIKELIHOOD,
            bias=AppraisalBias.NEUTRAL,
            source_provenance=_provenance(source_reference),
            integration_provenance=_provenance(integration_reference),
        )
    )


def _scenario_without_world_hazards() -> ControlledScenario:
    return ControlledScenario(
        hazard_entity_names=frozenset(),
        food_threshold=10,
        edible_item_names=("bread",),
        destinations=(
            ControlledDestination(
                destination_id="cave",
                position=MineflayerPosition(x=10, y=64, z=0),
                description="controlled destination cave",
                provenance=_provenance("destination:cave"),
            ),
        ),
    )


def _observation(
    *,
    session_id: str,
    entity_id: int,
    entity_x: float,
    irrelevant_item_name: str,
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
                    position=MineflayerPosition(
                        x=entity_x,
                        y=64,
                        z=0,
                    ),
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


def _world_signature(observation: MineflayerObservation) -> WorldSignature:
    snapshot = observation.snapshot
    return WorldSignature(
        session_id=observation.session_id,
        seq=observation.seq,
        health=snapshot.health,
        food=snapshot.food,
        food_saturation=snapshot.food_saturation,
        oxygen_level=snapshot.oxygen_level,
        position=(
            snapshot.position.x,
            snapshot.position.y,
            snapshot.position.z,
        ),
        inventory=tuple(
            (item.name, item.count, item.slot)
            for item in snapshot.inventory
        ),
        entities=tuple(
            (
                entity.entity_id,
                entity.name,
                entity.entity_type,
                entity.distance,
                (
                    entity.position.x,
                    entity.position.y,
                    entity.position.z,
                ),
            )
            for entity in snapshot.nearby_entities
        ),
    )


def _parameter_topology(decision: ScenarioDecision) -> str:
    if decision.skill is ControlledSkill.WAIT:
        return "NO_PARAMETER"
    if decision.skill is ControlledSkill.EAT:
        return "DIRECT_ITEM" if decision.item_name is not None else "UNRESOLVED_ITEM"
    if decision.skill is ControlledSkill.FIGHT:
        return (
            "DIRECT_TARGET"
            if decision.target_entity_id is not None
            else "UNRESOLVED_TARGET"
        )
    if decision.skill is ControlledSkill.FLEE:
        if decision.destination is None:
            return "UNRESOLVED_DESTINATION"
        if decision.cognition_result is None:
            return "DIRECT_DESTINATION"
        return "COGNITIVE_DESTINATION"
    raise AssertionError("unexpected controlled Skill")


def _provenance(reference: str) -> Provenance:
    return Provenance(
        source="reduction-recurrence-experiment",
        reference=reference,
    )
