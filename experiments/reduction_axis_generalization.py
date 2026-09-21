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
)
from experiments.reduction_recurrence import (
    ReductionEpisodeTrace,
    capture_appraisal_reduction,
)
from relay_self.appraisal import (
    AppraisalAspect,
    AppraisalBias,
    AppraisalDisposition,
    AppraisalTargetKind,
)
from relay_self.persistent_cognition import (
    IdentitySpecification,
    PersistentCognition,
)
from relay_self.provenance import Provenance


@dataclass(frozen=True, slots=True)
class ReductionAxisGeneralization:
    """Deterministic multi-axis reference matrix for #300."""

    harm_satiated: ReductionEpisodeTrace
    harm_hungry: ReductionEpisodeTrace
    experienced_hungry: ReductionEpisodeTrace
    experienced_satiated: ReductionEpisodeTrace
    affiliation_controls: tuple[ReductionEpisodeTrace, ...]
    mixed_harm_override: ReductionEpisodeTrace
    mixed_affiliation_override: ReductionEpisodeTrace

    @property
    def multi_skill_matrix_survives(self) -> bool:
        return (
            self.harm_satiated.selected_skill == ControlledSkill.FLEE.value
            and self.harm_hungry.selected_skill == ControlledSkill.FLEE.value
            and self.experienced_hungry.selected_skill == ControlledSkill.EAT.value
            and self.experienced_satiated.selected_skill == ControlledSkill.WAIT.value
        )

    @property
    def same_hungry_world_history_changes_skill(self) -> bool:
        return (
            self.harm_hungry.world_signature
            == self.experienced_hungry.world_signature
            and self.harm_hungry.raw_body_signature
            == self.experienced_hungry.raw_body_signature
            and self.harm_hungry.selected_skill == ControlledSkill.FLEE.value
            and self.experienced_hungry.selected_skill == ControlledSkill.EAT.value
        )

    @property
    def affiliation_is_non_consumed_control(self) -> bool:
        return (
            len(self.affiliation_controls) == len(AppraisalBias)
            and all(
                trace.selected_skill == ControlledSkill.FLEE.value
                for trace in self.affiliation_controls
            )
            and len(
                {
                    trace.appraisal_structure
                    for trace in self.affiliation_controls
                }
            )
            == len(AppraisalBias)
        )

    @property
    def mixed_projection_is_aspect_local(self) -> bool:
        harm = dict(
            (aspect, bias)
            for _, aspect, bias in self.mixed_harm_override.appraisal_structure
        )
        affiliation = dict(
            (aspect, bias)
            for _, aspect, bias in self.mixed_affiliation_override.appraisal_structure
        )
        return (
            harm[AppraisalAspect.HARM_LIKELIHOOD.value]
            == AppraisalBias.NEUTRAL.value
            and harm[AppraisalAspect.AFFILIATION_LIKELIHOOD.value]
            == AppraisalBias.DOWN.value
            and affiliation[AppraisalAspect.HARM_LIKELIHOOD.value]
            == AppraisalBias.UP.value
            and affiliation[AppraisalAspect.AFFILIATION_LIKELIHOOD.value]
            == AppraisalBias.UP.value
            and self.mixed_harm_override.selected_skill == ControlledSkill.EAT.value
            and self.mixed_affiliation_override.selected_skill
            == ControlledSkill.FLEE.value
        )


def reference_axis_generalization() -> ReductionAxisGeneralization:
    """Run the strongest natural generalization surface without provider calls."""

    controlled = _scenario()
    satiated = _observation(
        session_id="axis-generalization",
        entity_id=7,
        food=20,
        bread=True,
    )
    hungry = _observation(
        session_id="axis-generalization",
        entity_id=7,
        food=8,
        bread=True,
    )

    harm_only = _class_cognition()
    experienced = _with_instance_disposition(
        harm_only,
        session_id="axis-generalization",
        entity_id=7,
        aspect=AppraisalAspect.HARM_LIKELIHOOD,
        bias=AppraisalBias.NEUTRAL,
        source_reference="history:entity-7:harmless",
        integration_reference="integration:entity-7:harm-neutral",
    )

    affiliation_controls = tuple(
        capture_appraisal_reduction(
            episode_id=f"affiliation-{bias.value.lower()}",
            observation=hungry,
            scenario=controlled,
            cognition=_class_cognition(affiliation_bias=bias),
            intent_id="intent-survive",
        )
        for bias in AppraisalBias
    )

    mixed_base = _class_cognition(
        affiliation_bias=AppraisalBias.DOWN,
    )
    mixed_harm_override_cognition = _with_instance_disposition(
        mixed_base,
        session_id="axis-generalization",
        entity_id=7,
        aspect=AppraisalAspect.HARM_LIKELIHOOD,
        bias=AppraisalBias.NEUTRAL,
        source_reference="history:entity-7:harmless:mixed",
        integration_reference="integration:entity-7:harm-neutral:mixed",
    )
    mixed_affiliation_override_cognition = _with_instance_disposition(
        mixed_base,
        session_id="axis-generalization",
        entity_id=7,
        aspect=AppraisalAspect.AFFILIATION_LIKELIHOOD,
        bias=AppraisalBias.UP,
        source_reference="history:entity-7:affiliation-up",
        integration_reference="integration:entity-7:affiliation-up",
    )

    return ReductionAxisGeneralization(
        harm_satiated=capture_appraisal_reduction(
            episode_id="harm-satiated",
            observation=satiated,
            scenario=controlled,
            cognition=harm_only,
            intent_id="intent-survive",
        ),
        harm_hungry=capture_appraisal_reduction(
            episode_id="harm-hungry",
            observation=hungry,
            scenario=controlled,
            cognition=harm_only,
            intent_id="intent-survive",
        ),
        experienced_hungry=capture_appraisal_reduction(
            episode_id="experienced-hungry",
            observation=hungry,
            scenario=controlled,
            cognition=experienced,
            intent_id="intent-survive",
        ),
        experienced_satiated=capture_appraisal_reduction(
            episode_id="experienced-satiated",
            observation=satiated,
            scenario=controlled,
            cognition=experienced,
            intent_id="intent-survive",
        ),
        affiliation_controls=affiliation_controls,
        mixed_harm_override=capture_appraisal_reduction(
            episode_id="mixed-harm-override",
            observation=hungry,
            scenario=controlled,
            cognition=mixed_harm_override_cognition,
            intent_id="intent-survive",
        ),
        mixed_affiliation_override=capture_appraisal_reduction(
            episode_id="mixed-affiliation-override",
            observation=hungry,
            scenario=controlled,
            cognition=mixed_affiliation_override_cognition,
            intent_id="intent-survive",
        ),
    )


def _class_cognition(
    *,
    affiliation_bias: AppraisalBias | None = None,
) -> PersistentCognition:
    identity = IdentitySpecification(
        self_id="axis-generalization-self",
        directives=("Preserve continued agency.",),
        provenance=_provenance("identity"),
    )
    cognition = PersistentCognition(identity=identity)
    cognition = cognition.seed_appraisal_disposition(
        AppraisalDisposition(
            target_kind=AppraisalTargetKind.ENTITY_CLASS,
            target_key="zombie",
            aspect=AppraisalAspect.HARM_LIKELIHOOD,
            bias=AppraisalBias.UP,
            source_provenance=identity.provenance,
            integration_provenance=_provenance("soul-seed:harm"),
        )
    )
    if affiliation_bias is not None:
        cognition = cognition.seed_appraisal_disposition(
            AppraisalDisposition(
                target_kind=AppraisalTargetKind.ENTITY_CLASS,
                target_key="zombie",
                aspect=AppraisalAspect.AFFILIATION_LIKELIHOOD,
                bias=affiliation_bias,
                source_provenance=identity.provenance,
                integration_provenance=_provenance(
                    f"soul-seed:affiliation:{affiliation_bias.value.lower()}"
                ),
            )
        )
    return cognition


def _with_instance_disposition(
    cognition: PersistentCognition,
    *,
    session_id: str,
    entity_id: int,
    aspect: AppraisalAspect,
    bias: AppraisalBias,
    source_reference: str,
    integration_reference: str,
) -> PersistentCognition:
    return cognition.integrate_appraisal_disposition(
        AppraisalDisposition(
            target_kind=AppraisalTargetKind.ENTITY_INSTANCE,
            target_key=f"{session_id}:entity-{entity_id}",
            aspect=aspect,
            bias=bias,
            source_provenance=_provenance(source_reference),
            integration_provenance=_provenance(integration_reference),
        )
    )


def _scenario() -> ControlledScenario:
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
    food: float,
    bread: bool,
) -> MineflayerObservation:
    inventory = (
        (
            MineflayerInventoryItem(
                name="bread",
                count=2,
                slot=9,
            ),
        )
        if bread
        else ()
    )
    return MineflayerObservation(
        session_id=session_id,
        seq=1,
        kind="entities",
        snapshot=MineflayerSnapshot(
            health=12,
            food=food,
            food_saturation=4,
            oxygen_level=20,
            position=MineflayerPosition(x=0, y=64, z=0),
            time=None,
            inventory=inventory,
            nearby_entities=(
                MineflayerEntityFact(
                    entity_id=entity_id,
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


def _provenance(reference: str) -> Provenance:
    return Provenance(
        source="reduction-axis-generalization-experiment",
        reference=reference,
    )
