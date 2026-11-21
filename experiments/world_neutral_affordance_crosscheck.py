from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

from experiments.minecraft_skill_basis_coverage import (
    CANDIDATE_STATUS,
    CANDIDATE_WORLD_NEUTRAL_BASIS,
    MINECRAFT_AFFORDANCE_TO_WORLD_NEUTRAL_BASIS,
    MINECRAFT_NATIVE_AFFORDANCES,
    CandidateStatus,
    corpus_by_id,
)


class CrossWorldClassification(str, Enum):
    W0_MINECRAFT_SPECIFIC = "W0"
    W1_ONE_NEW_PORTABLE_FAMILY = "W1"
    W2_MULTIPLE_PORTABLE_FAMILIES = "W2"
    W3_GENERIC_BASIS_COLLAPSES = "W3"


@dataclass(frozen=True, slots=True)
class NativeAffordanceAccount:
    """Experiment-local accounting above one target-native affordance."""

    target: str
    native_affordance: str
    candidate_semantics: tuple[str, ...]
    binding: str
    applicability: str
    target_realization: str
    result_boundary: str

    def __post_init__(self) -> None:
        if not self.target.strip():
            raise ValueError("target must be non-empty")
        if not self.native_affordance.strip():
            raise ValueError("native_affordance must be non-empty")
        if not self.candidate_semantics:
            raise ValueError("candidate_semantics must not be empty")
        for value in (
            self.binding,
            self.applicability,
            self.target_realization,
            self.result_boundary,
        ):
            if not value.strip():
                raise ValueError("mapping metadata must be non-empty")


MINECRAFT_ACCOUNTS: tuple[NativeAffordanceAccount, ...] = (
    NativeAffordanceAccount(
        "minecraft",
        "MOVE",
        MINECRAFT_AFFORDANCE_TO_WORLD_NEUTRAL_BASIS["MOVE"],
        "desired Self/body location or pose relation",
        "the active objective requires changing Self/body location",
        "Mineflayer movement/path-control capability",
        "observed Self/body pose or target-relative distance change",
    ),
    NativeAffordanceAccount(
        "minecraft",
        "LOOK",
        MINECRAFT_AFFORDANCE_TO_WORLD_NEUTRAL_BASIS["LOOK"],
        "observation/orientation target",
        "the active parent controller requires directed observation",
        "Mineflayer look/orientation capability",
        "updated target-relative observation/orientation evidence",
    ),
    NativeAffordanceAccount(
        "minecraft",
        "EQUIP",
        MINECRAFT_AFFORDANCE_TO_WORLD_NEUTRAL_BASIS["EQUIP"],
        "held/equipped object relation",
        "an operative relation with an available object is required",
        "Mineflayer equip capability",
        "observed held/equipped relation change",
    ),
    NativeAffordanceAccount(
        "minecraft",
        "CONSUME",
        MINECRAFT_AFFORDANCE_TO_WORLD_NEUTRAL_BASIS["CONSUME"],
        "edible resource",
        "body/resource regulation selects consumption",
        "Mineflayer consume capability",
        "body/resource consequence after consumption",
    ),
    NativeAffordanceAccount(
        "minecraft",
        "ATTACK",
        MINECRAFT_AFFORDANCE_TO_WORLD_NEUTRAL_BASIS["ATTACK"],
        "grounded adverse target",
        "the selected antagonistic intervention is applicable",
        "Mineflayer attack capability",
        "target-relative combat consequence evidence",
    ),
    NativeAffordanceAccount(
        "minecraft",
        "BREAK",
        MINECRAFT_AFFORDANCE_TO_WORLD_NEUTRAL_BASIS["BREAK"],
        "external object/block plus removal affordance",
        "desired local external state requires removal/disassembly",
        "Minecraft block-break capability",
        "observed external object/block state change",
    ),
    NativeAffordanceAccount(
        "minecraft",
        "TAKE",
        MINECRAFT_AFFORDANCE_TO_WORLD_NEUTRAL_BASIS["TAKE"],
        "external resource plus acquisition relation",
        "desired local relation requires acquiring a resource",
        "Minecraft item-acquisition capability",
        "observed possession/location relation change",
    ),
    NativeAffordanceAccount(
        "minecraft",
        "PLACE",
        MINECRAFT_AFFORDANCE_TO_WORLD_NEUTRAL_BASIS["PLACE"],
        "external object/block plus placement relation",
        "desired local external state requires adding/positioning an object",
        "Minecraft block-place capability",
        "observed external object/block relation change",
    ),
    NativeAffordanceAccount(
        "minecraft",
        "USE",
        MINECRAFT_AFFORDANCE_TO_WORLD_NEUTRAL_BASIS["USE"],
        "external object plus available interaction affordance",
        "object affordance can produce the desired local state change",
        "Minecraft object activation/use capability",
        "observed local object/environment state change",
    ),
    NativeAffordanceAccount(
        "minecraft",
        "TRANSFER",
        MINECRAFT_AFFORDANCE_TO_WORLD_NEUTRAL_BASIS["TRANSFER"],
        "resource plus source/destination relation",
        "desired local relation requires moving a resource between holders",
        "Minecraft inventory/container transfer capability",
        "observed ownership/container relation change",
    ),
    NativeAffordanceAccount(
        "minecraft",
        "CRAFT",
        MINECRAFT_AFFORDANCE_TO_WORLD_NEUTRAL_BASIS["CRAFT"],
        "available materials plus constructible result",
        "desired object state is reachable through a crafting affordance",
        "Minecraft crafting capability",
        "observed material/result inventory relation change",
    ),
    NativeAffordanceAccount(
        "minecraft",
        "CHAT_DELIVERY",
        MINECRAFT_AFFORDANCE_TO_WORLD_NEUTRAL_BASIS["CHAT_DELIVERY"],
        "expression plus interlocutor/channel",
        "language coupling requires external delivery",
        "Minecraft chat-delivery capability",
        "delivery/observation boundary for emitted language",
    ),
)


# Deliberately synthetic and mechanically unlike Minecraft. This is a test
# surface only, not a robot adapter and not a universal cross-World protocol.
MOBILE_MANIPULATOR_ACCOUNTS: tuple[NativeAffordanceAccount, ...] = (
    NativeAffordanceAccount(
        "mobile_manipulator",
        "DRIVE_BASE",
        ("LOCOMOTE",),
        "desired chassis/body location or pose relation",
        "the active objective requires changing platform location",
        "mobile-base drive controller",
        "observed chassis/body pose or target-relative distance change",
    ),
    NativeAffordanceAccount(
        "mobile_manipulator",
        "GRASP",
        ("MANIPULATE",),
        "external object plus grasp relation",
        "desired local relation requires establishing physical control",
        "gripper close/contact controller",
        "observed grasp/contact relation change",
    ),
    NativeAffordanceAccount(
        "mobile_manipulator",
        "RELEASE",
        ("MANIPULATE",),
        "held object plus desired release relation",
        "desired local relation requires relinquishing physical control",
        "gripper release controller",
        "observed grasp/contact relation change",
    ),
    NativeAffordanceAccount(
        "mobile_manipulator",
        "PUSH",
        ("MANIPULATE",),
        "external object plus desired local displacement",
        "contact affordance can produce the desired object displacement",
        "arm/end-effector push controller",
        "observed external object pose relation change",
    ),
    NativeAffordanceAccount(
        "mobile_manipulator",
        "TURN",
        ("MANIPULATE",),
        "rotatable external control plus desired local state",
        "rotational affordance can produce the desired local state change",
        "arm/end-effector turn controller",
        "observed external control/object state change",
    ),
    NativeAffordanceAccount(
        "mobile_manipulator",
        "PRESS",
        ("MANIPULATE",),
        "pressable external control plus desired local state",
        "press affordance can produce the desired local state change",
        "arm/end-effector press controller",
        "observed external control/environment state change",
    ),
)


@dataclass(frozen=True, slots=True)
class CrossWorldBasisAnalysis:
    minecraft: tuple[NativeAffordanceAccount, ...]
    second_world: tuple[NativeAffordanceAccount, ...]

    @property
    def minecraft_is_fully_accounted(self) -> bool:
        by_native = {account.native_affordance: account for account in self.minecraft}
        if set(by_native) != set(MINECRAFT_NATIVE_AFFORDANCES):
            return False
        return all(
            account.candidate_semantics
            == MINECRAFT_AFFORDANCE_TO_WORLD_NEUTRAL_BASIS[native]
            for native, account in by_native.items()
        )

    @property
    def locomotion_survives_world_substitution(self) -> bool:
        minecraft_move = next(
            account for account in self.minecraft if account.native_affordance == "MOVE"
        )
        robot_drive = next(
            account
            for account in self.second_world
            if account.native_affordance == "DRIVE_BASE"
        )
        return (
            "LOCOMOTE" in minecraft_move.candidate_semantics
            and robot_drive.candidate_semantics == ("LOCOMOTE",)
            and minecraft_move.native_affordance != robot_drive.native_affordance
            and minecraft_move.target_realization != robot_drive.target_realization
        )

    @property
    def manipulation_survives_world_substitution(self) -> bool:
        minecraft_native = {
            account.native_affordance
            for account in self.minecraft
            if account.candidate_semantics == ("MANIPULATE",)
        }
        robot_native = {
            account.native_affordance
            for account in self.second_world
            if account.candidate_semantics == ("MANIPULATE",)
        }
        return (
            {"BREAK", "TAKE", "PLACE", "USE", "TRANSFER", "CRAFT"}
            <= minecraft_native
            and robot_native == {"GRASP", "RELEASE", "PUSH", "TURN", "PRESS"}
            and minecraft_native.isdisjoint(robot_native)
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
    def manipulation_is_not_talk_or_seek_alias(self) -> bool:
        transfer = corpus_by_id()["share_scarce_food"]
        return (
            transfer.primitives == ("TRANSFER",)
            and transfer.surviving_candidates == ()
            and transfer.open_candidates == ()
            and CANDIDATE_STATUS["TALK"] is CandidateStatus.REDUCED
        )

    @property
    def families_remain_non_generic(self) -> bool:
        move = next(
            account for account in self.minecraft if account.native_affordance == "MOVE"
        )
        transfer = next(
            account
            for account in self.minecraft
            if account.native_affordance == "TRANSFER"
        )
        return (
            "Self/body location" in move.binding
            and "resource" in transfer.binding
            and move.result_boundary != transfer.result_boundary
            and {"LOCOMOTE", "MANIPULATE"}
            <= set(CANDIDATE_WORLD_NEUTRAL_BASIS)
        )

    @property
    def classification(self) -> CrossWorldClassification:
        if not self.minecraft_is_fully_accounted:
            return CrossWorldClassification.W0_MINECRAFT_SPECIFIC
        if not self.manipulation_survives_world_substitution:
            return CrossWorldClassification.W0_MINECRAFT_SPECIFIC
        if not self.locomotion_survives_world_substitution:
            return CrossWorldClassification.W1_ONE_NEW_PORTABLE_FAMILY
        if not (
            self.locomotion_is_not_seek_alias
            and self.manipulation_is_not_talk_or_seek_alias
            and self.families_remain_non_generic
        ):
            return CrossWorldClassification.W3_GENERIC_BASIS_COLLAPSES
        return CrossWorldClassification.W2_MULTIPLE_PORTABLE_FAMILIES


def validate_cross_world_accounts() -> tuple[str, ...]:
    errors: list[str] = []

    minecraft_by_native: dict[str, NativeAffordanceAccount] = {}
    for account in MINECRAFT_ACCOUNTS:
        if account.native_affordance in minecraft_by_native:
            errors.append(
                f"duplicate Minecraft account: {account.native_affordance}"
            )
        minecraft_by_native[account.native_affordance] = account

    missing = set(MINECRAFT_NATIVE_AFFORDANCES) - set(minecraft_by_native)
    if missing:
        errors.append(
            "Minecraft affordances without detailed account: "
            + ",".join(sorted(missing))
        )

    unknown = set(minecraft_by_native) - set(MINECRAFT_NATIVE_AFFORDANCES)
    if unknown:
        errors.append(
            "unknown Minecraft affordance accounts: " + ",".join(sorted(unknown))
        )

    for native, candidates in MINECRAFT_AFFORDANCE_TO_WORLD_NEUTRAL_BASIS.items():
        account = minecraft_by_native.get(native)
        if account is not None and account.candidate_semantics != candidates:
            errors.append(
                f"{native}: detailed account disagrees with #313 candidate mapping"
            )

    basis = set(CANDIDATE_WORLD_NEUTRAL_BASIS)
    for account in (*MINECRAFT_ACCOUNTS, *MOBILE_MANIPULATOR_ACCOUNTS):
        unknown_candidates = set(account.candidate_semantics) - basis
        if unknown_candidates:
            errors.append(
                f"{account.target}:{account.native_affordance}: unknown candidates="
                + ",".join(sorted(unknown_candidates))
            )
        if {"DO", "ACT", "ACHIEVE"} & set(account.candidate_semantics):
            errors.append(
                f"{account.target}:{account.native_affordance}: generic basis collapse"
            )

    return tuple(errors)


def reference_cross_world_analysis() -> CrossWorldBasisAnalysis:
    return CrossWorldBasisAnalysis(
        minecraft=MINECRAFT_ACCOUNTS,
        second_world=MOBILE_MANIPULATOR_ACCOUNTS,
    )
