from experiments.minecraft_skill_basis_coverage import TARGET_PRIMITIVES
from experiments.world_neutral_skill_basis import (
    LOCOMOTE,
    MANIPULATE,
    MINECRAFT_AFFORDANCE_MAPPINGS,
    MOBILE_MANIPULATOR_AFFORDANCE_MAPPINGS,
    PortableMappingKind,
    WorldNeutralClassification,
    reference_world_neutral_analysis,
    validate_mapping_surface,
)


def _minecraft_mapping(native: str):
    return next(
        mapping
        for mapping in MINECRAFT_AFFORDANCE_MAPPINGS
        if mapping.native_affordance == native
    )


def test_every_minecraft_native_leaf_has_explicit_world_neutral_accounting() -> None:
    assert validate_mapping_surface() == ()

    mapped = {
        mapping.native_affordance
        for mapping in MINECRAFT_AFFORDANCE_MAPPINGS
    }
    assert mapped == set(TARGET_PRIMITIVES)

    analysis = reference_world_neutral_analysis()
    assert analysis.minecraft_native_leaves_all_accounted_for


def test_known_navigation_forces_locomotion_without_turning_seek_into_go() -> None:
    analysis = reference_world_neutral_analysis()
    move = _minecraft_mapping("MOVE")

    assert move.kind is PortableMappingKind.BASIS_FAMILY
    assert move.portable_semantic == LOCOMOTE
    assert "Self/body location" in move.binding
    assert analysis.locomotion_is_not_seek_alias


def test_external_state_transformation_forces_bounded_manipulation_family() -> None:
    analysis = reference_world_neutral_analysis()

    for native in ("EQUIP", "BREAK", "TAKE", "PLACE", "USE", "TRANSFER", "CRAFT"):
        mapping = _minecraft_mapping(native)
        assert mapping.kind is PortableMappingKind.BASIS_FAMILY
        assert mapping.portable_semantic == MANIPULATE

    assert analysis.manipulation_is_not_seek_or_talk_alias


def test_existing_semantic_families_remain_distinct_from_generic_manipulation() -> None:
    assert _minecraft_mapping("CONSUME").portable_semantic == "EAT"
    assert _minecraft_mapping("ATTACK").portable_semantic == "FIGHT"
    assert _minecraft_mapping("CHAT_DELIVERY").portable_semantic == "TALK"

    look = _minecraft_mapping("LOOK")
    assert look.kind is PortableMappingKind.EXISTING_OWNER_OR_CONTROL
    assert look.portable_semantic == "Perception / parent-local orientation"


def test_materially_different_target_reuses_same_locomotion_semantics() -> None:
    analysis = reference_world_neutral_analysis()

    robot = {
        mapping.native_affordance: mapping
        for mapping in MOBILE_MANIPULATOR_AFFORDANCE_MAPPINGS
    }
    assert robot["DRIVE_BASE"].portable_semantic == LOCOMOTE
    assert robot["DRIVE_BASE"].target_realization == "mobile-base drive controller"

    minecraft = _minecraft_mapping("MOVE")
    assert minecraft.native_affordance != robot["DRIVE_BASE"].native_affordance
    assert minecraft.target_realization != robot["DRIVE_BASE"].target_realization
    assert minecraft.portable_semantic == robot["DRIVE_BASE"].portable_semantic

    assert analysis.cross_world_locomotion_survives


def test_materially_different_target_reuses_same_manipulation_semantics() -> None:
    analysis = reference_world_neutral_analysis()

    robot_manipulation = {
        mapping.native_affordance
        for mapping in MOBILE_MANIPULATOR_AFFORDANCE_MAPPINGS
        if mapping.portable_semantic == MANIPULATE
    }
    assert robot_manipulation == {"GRASP", "RELEASE", "PUSH", "TURN", "PRESS"}

    minecraft_manipulation = {
        mapping.native_affordance
        for mapping in MINECRAFT_AFFORDANCE_MAPPINGS
        if mapping.portable_semantic == MANIPULATE
    }
    assert "BREAK" in minecraft_manipulation
    assert "CRAFT" in minecraft_manipulation
    assert "TRANSFER" in minecraft_manipulation

    assert robot_manipulation.isdisjoint(minecraft_manipulation)
    assert analysis.cross_world_manipulation_survives


def test_locomotion_and_manipulation_do_not_collapse_into_generic_do() -> None:
    analysis = reference_world_neutral_analysis()

    assert analysis.new_families_do_not_collapse_into_generic_do

    basis_names = {
        mapping.portable_semantic
        for mapping in (
            *MINECRAFT_AFFORDANCE_MAPPINGS,
            *MOBILE_MANIPULATOR_AFFORDANCE_MAPPINGS,
        )
        if mapping.kind is PortableMappingKind.BASIS_FAMILY
    }
    assert not {"DO", "ACT", "ACHIEVE"} & basis_names


def test_world_neutral_basis_attack_classifies_as_multiple_portable_families() -> None:
    analysis = reference_world_neutral_analysis()

    assert analysis.classification is (
        WorldNeutralClassification.W2_MULTIPLE_PORTABLE_FAMILIES
    )
