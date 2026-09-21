from experiments.world_neutral_affordance_crosscheck import (
    MINECRAFT_ACCOUNTS,
    MOBILE_MANIPULATOR_ACCOUNTS,
    CrossWorldClassification,
    reference_cross_world_analysis,
    validate_cross_world_accounts,
)


def _account(accounts, native_affordance):
    return next(
        item for item in accounts if item.native_affordance == native_affordance
    )


def test_every_minecraft_native_affordance_has_detailed_portable_accounting() -> None:
    analysis = reference_cross_world_analysis()

    assert validate_cross_world_accounts() == ()
    assert analysis.minecraft_is_fully_accounted


def test_locomotion_survives_materially_different_world_substitution() -> None:
    analysis = reference_cross_world_analysis()
    minecraft = _account(MINECRAFT_ACCOUNTS, "MOVE")
    robot = _account(MOBILE_MANIPULATOR_ACCOUNTS, "DRIVE_BASE")

    assert "LOCOMOTE" in minecraft.candidate_semantics
    assert robot.candidate_semantics == ("LOCOMOTE",)
    assert minecraft.native_affordance != robot.native_affordance
    assert minecraft.target_realization != robot.target_realization
    assert analysis.locomotion_survives_world_substitution


def test_manipulation_survives_materially_different_world_substitution() -> None:
    analysis = reference_cross_world_analysis()

    minecraft = {
        item.native_affordance
        for item in MINECRAFT_ACCOUNTS
        if item.candidate_semantics == ("MANIPULATE",)
    }
    robot = {
        item.native_affordance
        for item in MOBILE_MANIPULATOR_ACCOUNTS
        if item.candidate_semantics == ("MANIPULATE",)
    }

    assert {"BREAK", "TAKE", "PLACE", "USE", "TRANSFER", "CRAFT"} <= minecraft
    assert robot == {"GRASP", "RELEASE", "PUSH", "TURN", "PRESS"}
    assert minecraft.isdisjoint(robot)
    assert analysis.manipulation_survives_world_substitution


def test_known_target_navigation_prevents_locomotion_from_collapsing_into_seek() -> None:
    analysis = reference_cross_world_analysis()

    assert analysis.locomotion_is_not_seek_alias


def test_decided_transfer_prevents_manipulation_from_collapsing_into_talk_or_seek() -> None:
    analysis = reference_cross_world_analysis()

    assert analysis.manipulation_is_not_talk_or_seek_alias


def test_locomotion_and_manipulation_retain_distinct_bindings_and_result_boundaries() -> None:
    analysis = reference_cross_world_analysis()
    move = _account(MINECRAFT_ACCOUNTS, "MOVE")
    transfer = _account(MINECRAFT_ACCOUNTS, "TRANSFER")

    assert move.binding != transfer.binding
    assert move.applicability != transfer.applicability
    assert move.result_boundary != transfer.result_boundary
    assert analysis.families_remain_non_generic


def test_cross_world_attack_classifies_as_multiple_portable_families() -> None:
    analysis = reference_cross_world_analysis()

    assert analysis.classification is (
        CrossWorldClassification.W2_MULTIPLE_PORTABLE_FAMILIES
    )


def test_second_target_is_only_a_deterministic_capability_surface() -> None:
    targets = {item.target for item in MOBILE_MANIPULATOR_ACCOUNTS}
    native = {item.native_affordance for item in MOBILE_MANIPULATOR_ACCOUNTS}

    assert targets == {"mobile_manipulator"}
    assert native == {"DRIVE_BASE", "GRASP", "RELEASE", "PUSH", "TURN", "PRESS"}
    assert "MOVE" not in native
    assert "BREAK" not in native
    assert "PLACE" not in native
    assert "CRAFT" not in native
