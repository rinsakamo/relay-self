from experiments.minecraft_skill_basis_coverage import (
    BEHAVIOR_CORPUS,
    CANDIDATE_ABLATION_WITNESSES,
    CANDIDATE_SKILL_BASIS,
    basis_usage,
    corpus_by_id,
    validate_corpus,
)


def test_minecraft_skill_basis_coverage_corpus_is_internally_consistent() -> None:
    assert validate_corpus() == ()


def test_every_candidate_basis_skill_has_usage_and_ablation_pressure() -> None:
    usage = basis_usage()

    assert set(usage) == set(CANDIDATE_SKILL_BASIS)
    assert set(CANDIDATE_ABLATION_WITNESSES) == set(CANDIDATE_SKILL_BASIS)
    assert all(usage[skill] for skill in CANDIDATE_SKILL_BASIS)


def test_hard_counterexample_families_are_present() -> None:
    cases = corpus_by_id()

    required = {
        "build_shelter_before_night",
        "mine_and_craft_upgrade",
        "farm_renewable_food",
        "navigate_remembered_location",
        "search_unknown_resource",
        "escort_companion",
        "rescue_companion_under_attack",
        "coordinate_two_agent_attack",
        "share_scarce_food",
        "trade_resources",
        "ambush_player",
        "retreat_and_regroup",
        "scout_and_report",
        "construct_operate_mechanism",
        "recover_after_respawn",
        "learn_from_failed_route_or_fight",
        "plan_multi_step_expedition",
        "deceive_other_through_language",
        "create_novel_structure",
    }

    assert required <= set(cases)


def test_missing_adapter_primitives_are_kept_separate_from_skill_vocabulary() -> None:
    cases = corpus_by_id()

    assert cases["eat_available_food"].missing_current_primitives() == ()
    assert cases["direct_combat"].missing_current_primitives() == ()
    assert cases["escape_threat"].missing_current_primitives() == ()

    assert "PLACE" in cases["build_shelter_before_night"].missing_current_primitives()
    assert "BREAK" in cases["mine_and_craft_upgrade"].missing_current_primitives()
    assert "CRAFT" in cases["mine_and_craft_upgrade"].missing_current_primitives()
    assert "TRANSFER" in cases["share_scarce_food"].missing_current_primitives()
    assert "CHAT_DELIVERY" in cases[
        "coordinate_two_agent_attack"
    ].missing_current_primitives()


def test_not_every_meaningful_adaptation_is_forced_into_a_skill() -> None:
    learning = corpus_by_id()["learn_from_failed_route_or_fight"]

    assert learning.skills == ()
    assert learning.primitives == ()
    assert "Experience Integration" in learning.owners


def test_named_compounds_do_not_enter_the_candidate_basis() -> None:
    rejected_named_compounds = {
        "BUILD",
        "MINE",
        "FARM",
        "FOLLOW",
        "GIVE",
        "TRADE",
        "COOPERATE",
        "ROLE",
        "RESCUE",
        "AMBUSH",
        "SCOUT",
        "NEGOTIATE",
        "DECEIVE",
    }

    assert rejected_named_compounds.isdisjoint(CANDIDATE_SKILL_BASIS)
    assert all(
        rejected_named_compounds.isdisjoint(case.skills)
        for case in BEHAVIOR_CORPUS
    )
