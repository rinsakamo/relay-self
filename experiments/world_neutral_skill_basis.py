from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

from experiments.minecraft_skill_basis_coverage import (
    BEHAVIOR_CORPUS,
    TARGET_PRIMITIVES,
    corpus_by_id,
)


class PortableMappingKind(str, Enum):
    """How one target-native affordance is accounted for above the adapter."""

    BASIS_FAMILY = "basis_family"
    EXISTING_OWNER_OR_CONTROL = "existing_owner_or_control"


class WorldNeutralClassification(str, Enum):
    """Bounded #312 classifications."""

    W0_MINECRAFT_SPECIFIC = "W0"
    W1_ONE_NEW_PORTABLE_FAMILY = "W1"
    W2_MULTIPLE_PORTABLE_FAMILIES = "W2"
    W3_GENERIC_BASIS_COLLAPSES = "W3"


@dataclass(frozen=True, slots=True)
class AffordanceMapping:
    """One target-native realization mapped to portable Self-side meaning."""

    target: str
    native_affordance: str
    kind: PortableMappingKind
    portable_semantic: str
    binding: str
    applicability: str
    target_realization: str
    result_boundary: str

    def __post_init__(self) -> None:
        for field_name in (
            "target",
            "native_affordance",
            "portable_semantic",
            "binding",
            "applicability",
            "target_realization",
            "result_boundary",
        ):
            value = getattr(self, field_name)
            if not isinstance(value, str) or not value.strip():
                raise ValueError(f"{field_name} must be a non-empty string")


# These are experiment-local semantic families, not production Skill ids.
LOCOMOTE = "LOCOMOTE"
MANIPULATE = "MANIPULATE"


MINECRAFT_AFFORDANCE_MAPPINGS: tuple[AffordanceMapping, ...] = (
    AffordanceMapping(
        target="minecraft",
        native_affordance="MOVE",
        kind=PortableMappingKind.BASIS_FAMILY,
        portable_semantic=LOCOMOTE,
        binding="desired Self/body location or pose relation",
        applicability="a committed objective requires changing Self/body location",
        target_realization="Mineflayer movement/path-control primitive",
        result_boundary="observed Self/body pose or distance change",
    ),
    AffordanceMapping(
        target="minecraft",
        native_affordance="LOOK",
        kind=PortableMappingKind.EXISTING_OWNER_OR_CONTROL,
        portable_semantic="Perception / parent-local orientation",
        binding="observation or orientation target",
        applicability="the active controller requires directed observation/orientation",
        target_realization="Mineflayer look/orientation primitive",
        result_boundary="updated target-relative observation/orientation evidence",
    ),
    AffordanceMapping(
        target="minecraft",
        native_affordance="EQUIP",
        kind=PortableMappingKind.BASIS_FAMILY,
        portable_semantic=MANIPULATE,
        binding="held/equipped object relation",
        applicability="an available object must be brought into an operative relation",
        target_realization="Mineflayer equip primitive",
        result_boundary="observed held/equipped relation change",
    ),
    AffordanceMapping(
        target="minecraft",
        native_affordance="CONSUME",
        kind=PortableMappingKind.BASIS_FAMILY,
        portable_semantic="EAT",
        binding="edible resource",
        applicability="body/resource regulation selects consumption of an edible resource",
        target_realization="Mineflayer consume primitive",
        result_boundary="body/resource consequence after consumption",
    ),
    AffordanceMapping(
        target="minecraft",
        native_affordance="ATTACK",
        kind=PortableMappingKind.BASIS_FAMILY,
        portable_semantic="FIGHT",
        binding="grounded adverse target",
        applicability="the selected antagonistic intervention is applicable to the target",
        target_realization="Mineflayer attack primitive",
        result_boundary="target-relative combat consequence evidence",
    ),
    AffordanceMapping(
        target="minecraft",
        native_affordance="BREAK",
        kind=PortableMappingKind.BASIS_FAMILY,
        portable_semantic=MANIPULATE,
        binding="external object/block plus break affordance",
        applicability="a desired local external-state change requires removal/disassembly",
        target_realization="Minecraft block-break capability",
        result_boundary="observed external object/block state change",
    ),
    AffordanceMapping(
        target="minecraft",
        native_affordance="TAKE",
        kind=PortableMappingKind.BASIS_FAMILY,
        portable_semantic=MANIPULATE,
        binding="external item/resource plus acquisition affordance",
        applicability="a desired local relation requires moving an external resource into possession",
        target_realization="Minecraft item acquisition capability",
        result_boundary="observed possession/location relation change",
    ),
    AffordanceMapping(
        target="minecraft",
        native_affordance="PLACE",
        kind=PortableMappingKind.BASIS_FAMILY,
        portable_semantic=MANIPULATE,
        binding="external object/block plus placement relation",
        applicability="a desired local external-state change requires adding/positioning an object",
        target_realization="Minecraft block-place capability",
        result_boundary="observed external object/block relation change",
    ),
    AffordanceMapping(
        target="minecraft",
        native_affordance="USE",
        kind=PortableMappingKind.BASIS_FAMILY,
        portable_semantic=MANIPULATE,
        binding="external object plus available interaction affordance",
        applicability="a desired local external-state change is exposed by an object affordance",
        target_realization="Minecraft object activation/use capability",
        result_boundary="observed local object/environment state change",
    ),
    AffordanceMapping(
        target="minecraft",
        native_affordance="TRANSFER",
        kind=PortableMappingKind.BASIS_FAMILY,
        portable_semantic=MANIPULATE,
        binding="resource plus source/destination ownership relation",
        applicability="a desired local relation requires moving a resource between holders/containers",
        target_realization="Minecraft inventory/container transfer capability",
        result_boundary="observed ownership/container relation change",
    ),
    AffordanceMapping(
        target="minecraft",
        native_affordance="CRAFT",
        kind=PortableMappingKind.BASIS_FAMILY,
        portable_semantic=MANIPULATE,
        binding="available materials plus constructible result",
        applicability="a desired local external/object state is reachable through a crafting affordance",
        target_realization="Minecraft crafting capability",
        result_boundary="observed material/result inventory relation change",
    ),
    AffordanceMapping(
        target="minecraft",
        native_affordance="CHAT_DELIVERY",
        kind=PortableMappingKind.BASIS_FAMILY,
        portable_semantic="TALK",
        binding="expression plus interlocutor/channel",
        applicability="language coupling requires external delivery to an Other",
        target_realization="Minecraft chat delivery capability",
        result_boundary="delivery/observation boundary for externally emitted language",
    ),
)


# A deliberately small, materially different deterministic target. It is not a
# production robot adapter or a proposal for a universal cross-World protocol.
MOBILE_MANIPULATOR_AFFORDANCE_MAPPINGS: tuple[AffordanceMapping, ...] = (
    AffordanceMapping(
        target="mobile_manipulator",
        native_affordance="DRIVE_BASE",
        kind=PortableMappingKind.BASIS_FAMILY,
        portable_semantic=LOCOMOTE,
        binding="desired chassis/body location or pose relation",
        applicability="the committed objective requires changing platform location",
        target_realization="mobile-base drive controller",
        result_boundary="observed chassis/body pose or distance change",
    ),
    AffordanceMapping(
        target="mobile_manipulator",
        native_affordance="CAMERA_AIM",
        kind=PortableMappingKind.EXISTING_OWNER_OR_CONTROL,
        portable_semantic="Perception / parent-local orientation",
        binding="observation or orientation target",
        applicability="the active controller requires directed sensor orientation",
        target_realization="pan/tilt camera controller",
        result_boundary="updated target-relative observation/orientation evidence",
    ),
    AffordanceMapping(
        target="mobile_manipulator",
        native_affordance="GRASP",
        kind=PortableMappingKind.BASIS_FAMILY,
        portable_semantic=MANIPULATE,
        binding="external object plus grasp affordance",
        applicability="a desired local relation requires establishing physical control of an object",
        target_realization="gripper close/contact controller",
        result_boundary="observed grasp/contact relation change",
    ),
    AffordanceMapping(
        target="mobile_manipulator",
        native_affordance="RELEASE",
        kind=PortableMappingKind.BASIS_FAMILY,
        portable_semantic=MANIPULATE,
        binding="held object plus desired release relation",
        applicability="a desired local relation requires relinquishing physical control of an object",
        target_realization="gripper release controller",
        result_boundary="observed grasp/contact relation change",
    ),
    AffordanceMapping(
        target="mobile_manipulator",
        native_affordance="PUSH",
        kind=PortableMappingKind.BASIS_FAMILY,
        portable_semantic=MANIPULATE,
        binding="external object plus desired local displacement",
        applicability="an available contact affordance can produce the desired object displacement",
        target_realization="arm/end-effector push controller",
        result_boundary="observed external object pose relation change",
    ),
    AffordanceMapping(
        target="mobile_manipulator",
        native_affordance="TURN",
        kind=PortableMappingKind.BASIS_FAMILY,
        portable_semantic=MANIPULATE,
        binding="rotatable external control plus desired local state",
        applicability="a rotational affordance can produce the desired external-state change",
        target_realization="arm/end-effector turn controller",
        result_boundary="observed external control/object state change",
    ),
    AffordanceMapping(
        target="mobile_manipulator",
        native_affordance="PRESS",
        kind=PortableMappingKind.BASIS_FAMILY,
        portable_semantic=MANIPULATE,
        binding="pressable external control plus desired local state",
        applicability="a press affordance can produce the desired external-state change",
        target_realization="arm/end-effector press controller",
        result_boundary="observed external control/environment state change",
    ),
)


@dataclass(frozen=True, slots=True)
class WorldNeutralBasisAnalysis:
    """Bounded deterministic analysis over the #304 corpus and second target."""

    minecraft_mappings: tuple[AffordanceMapping, ...]
    second_target_mappings: tuple[AffordanceMapping, ...]

    @property
    def minecraft_native_leaves_all_accounted_for(self) -> bool:
        mapped = {mapping.native_affordance for mapping in self.minecraft_mappings}
        corpus_primitives = {
            primitive
            for case in BEHAVIOR_CORPUS
            for primitive in case.primitives
        }
        return mapped == set(TARGET_PRIMITIVES) == corpus_primitives

    @property
    def cross_world_locomotion_survives(self) -> bool:
        minecraft = {
            mapping.native_affordance
            for mapping in self.minecraft_mappings
            if mapping.portable_semantic == LOCOMOTE
        }
        other = {
            mapping.native_affordance
            for mapping in self.second_target_mappings
            if mapping.portable_semantic == LOCOMOTE
        }
        return minecraft == {"MOVE"} and other == {"DRIVE_BASE"}

    @property
    def cross_world_manipulation_survives(self) -> bool:
        minecraft = {
            mapping.native_affordance
            for mapping in self.minecraft_mappings
            if mapping.portable_semantic == MANIPULATE
        }
        other = {
            mapping.native_affordance
            for mapping in self.second_target_mappings
            if mapping.portable_semantic == MANIPULATE
        }
        return (
            {"EQUIP", "BREAK", "TAKE", "PLACE", "USE", "TRANSFER", "CRAFT"}
            <= minecraft
            and {"GRASP", "RELEASE", "PUSH", "TURN", "PRESS"} <= other
        )

    @property
    def locomotion_is_not_seek_alias(self) -> bool:
        remembered = corpus_by_id()["navigate_remembered_location"]
        return (
            remembered.primitives == ("MOVE",)
            and remembered.surviving_candidates == ()
            and remembered.open_candidates == ()
            and "Known target location" in remembered.pressure
        )

    @property
    def manipulation_is_not_seek_or_talk_alias(self) -> bool:
        transfer = corpus_by_id()["share_scarce_food"]
        return (
            transfer.primitives == ("TRANSFER",)
            and transfer.surviving_candidates == ()
            and transfer.open_candidates == ()
            and "already-decided transfer" in transfer.pressure
        )

    @property
    def new_families_do_not_collapse_into_generic_do(self) -> bool:
        locomotion = next(
            mapping
            for mapping in self.minecraft_mappings
            if mapping.portable_semantic == LOCOMOTE
        )
        manipulation = next(
            mapping
            for mapping in self.minecraft_mappings
            if mapping.portable_semantic == MANIPULATE
        )
        return (
            locomotion.binding != manipulation.binding
            and locomotion.applicability != manipulation.applicability
            and locomotion.result_boundary != manipulation.result_boundary
        )

    @property
    def classification(self) -> WorldNeutralClassification:
        if not self.minecraft_native_leaves_all_accounted_for:
            return WorldNeutralClassification.W0_MINECRAFT_SPECIFIC
        if not (
            self.cross_world_locomotion_survives
            and self.cross_world_manipulation_survives
        ):
            return WorldNeutralClassification.W3_GENERIC_BASIS_COLLAPSES
        if not (
            self.locomotion_is_not_seek_alias
            and self.manipulation_is_not_seek_or_talk_alias
            and self.new_families_do_not_collapse_into_generic_do
        ):
            return WorldNeutralClassification.W3_GENERIC_BASIS_COLLAPSES
        return WorldNeutralClassification.W2_MULTIPLE_PORTABLE_FAMILIES


def validate_mapping_surface() -> tuple[str, ...]:
    errors: list[str] = []

    minecraft_by_native: dict[str, list[AffordanceMapping]] = {}
    for mapping in MINECRAFT_AFFORDANCE_MAPPINGS:
        minecraft_by_native.setdefault(mapping.native_affordance, []).append(mapping)

    for native in sorted(TARGET_PRIMITIVES):
        mappings = minecraft_by_native.get(native, [])
        if len(mappings) != 1:
            errors.append(
                f"Minecraft native affordance {native} must have exactly one portable mapping"
            )

    unknown_minecraft = sorted(set(minecraft_by_native) - set(TARGET_PRIMITIVES))
    if unknown_minecraft:
        errors.append(
            "unknown Minecraft native affordances: " + ",".join(unknown_minecraft)
        )

    corpus_primitives = {
        primitive
        for case in BEHAVIOR_CORPUS
        for primitive in case.primitives
    }
    unmapped_corpus = sorted(corpus_primitives - set(minecraft_by_native))
    if unmapped_corpus:
        errors.append(
            "corpus escapes through unmapped native affordances: "
            + ",".join(unmapped_corpus)
        )

    for mappings in (
        MINECRAFT_AFFORDANCE_MAPPINGS,
        MOBILE_MANIPULATOR_AFFORDANCE_MAPPINGS,
    ):
        seen: set[tuple[str, str]] = set()
        for mapping in mappings:
            key = (mapping.target, mapping.native_affordance)
            if key in seen:
                errors.append(
                    f"duplicate target-native mapping: {mapping.target}:{mapping.native_affordance}"
                )
            seen.add(key)

            if mapping.kind is PortableMappingKind.BASIS_FAMILY:
                if mapping.portable_semantic in {"DO", "ACT", "ACHIEVE"}:
                    errors.append(
                        f"generic basis collapse: {mapping.portable_semantic}"
                    )

    return tuple(errors)


def reference_world_neutral_analysis() -> WorldNeutralBasisAnalysis:
    return WorldNeutralBasisAnalysis(
        minecraft_mappings=MINECRAFT_AFFORDANCE_MAPPINGS,
        second_target_mappings=MOBILE_MANIPULATOR_AFFORDANCE_MAPPINGS,
    )
