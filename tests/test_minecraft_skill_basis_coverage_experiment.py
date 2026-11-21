from experiments.minecraft_skill_basis_coverage import (
    BEHAVIOR_CORPUS,
    CANDIDATE_SKILL_BASIS,
    CANDIDATE_STATUS,
    CANDIDATE_WORLD_NEUTRAL_BASIS,
    MINECRAFT_AFFORDANCE_TO_WORLD_NEUTRAL_BASIS,
    MINECRAFT_NATIVE_AFFORDANCES,
    CandidateStatus,
    corpus_by_id,
    open_basis_usage,
    proposed_basis_usage,
    surviving_basis_usage,
    validate_corpus,
)


def test_minecraft_skill_basis_coverage_corpus_is_internally_consistent() -> None:
    assert validate_corpus() == ()



def test_minecraft_native_affordances_cannot_terminate_world_neutral_basis() -> None:
    basis = set(CANDIDATE_WORLD_NEUTRAL_BASIS)

    assert set(MINECRAFT_NATIVE_AFFORDANCES).isdisjoint(basis)
    assert "LOCOMOTE" in basis
    assert "MANIPULATE" in basis

    assert "LOCOMOTE" in MINECRAFT_AFFORDANCE_TO_WORLD_NEUTRAL_BASIS["MOVE"]
    assert MINECRAFT_AFFORDANCE_TO_WORLD_NEUTRAL_BASIS["BREAK"] == ("MANIPULATE",)
    assert MINECRAFT_AFFORDANCE_TO_WORLD_NEUTRAL_BASIS["PLACE"] == ("MANIPULATE",)
    assert MINECRAFT_AFFORDANCE_TO_WORLD_NEUTRAL_BASIS["CRAFT"] == ("MANIPULATE",)
    assert MINECRAFT_AFFORDANCE_TO_WORLD_NEUTRAL_BASIS["TRANSFER"] == ("MANIPULATE",)
    assert MINECRAFT_AFFORDANCE_TO_WORLD_NEUTRAL_BASIS["CONSUME"] == ("EAT",)
    assert MINECRAFT_AFFORDANCE_TO_WORLD_NEUTRAL_BASIS["ATTACK"] == ("FIGHT",)
    assert MINECRAFT_AFFORDANCE_TO_WORLD_NEUTRAL_BASIS["CHAT_DELIVERY"] == (
        "TALK",
    )


def test_every_native_affordance_used_by_the_corpus_has_portable_mapping_pressure() -> None:
    used = {
        primitive
        for case in BEHAVIOR_CORPUS
        for primitive in case.primitives
    }

    assert used <= set(MINECRAFT_NATIVE_AFFORDANCES)
    assert used <= set(MINECRAFT_AFFORDANCE_TO_WORLD_NEUTRAL_BASIS)


def test_candidate_vocabulary_is_separate_from_current_grand_null_status() -> None:
    proposed = proposed_basis_usage()

    assert set(proposed) == set(CANDIDATE_SKILL_BASIS)
    assert all(proposed[skill] for skill in CANDIDATE_SKILL_BASIS)
    assert CANDIDATE_STATUS["WAIT"] is CandidateStatus.REDUCED
    assert CANDIDATE_STATUS["CONTEMPLATE"] is CandidateStatus.REDUCED
    assert CANDIDATE_STATUS["SEEK"] is CandidateStatus.OPEN
    assert CANDIDATE_STATUS["EAT"] is CandidateStatus.SURVIVES_CURRENT_ATTACK
    assert CANDIDATE_STATUS["FIGHT"] is CandidateStatus.SURVIVES_CURRENT_ATTACK
    assert CANDIDATE_STATUS["FLEE"] is CandidateStatus.SURVIVES_CURRENT_ATTACK
    assert CANDIDATE_STATUS["TALK"] is CandidateStatus.REDUCED


def test_reduced_candidates_do_not_reappear_as_surviving_or_open_skills() -> None:
    surviving = surviving_basis_usage()
    open_ = open_basis_usage()

    assert surviving["WAIT"] == ()
    assert open_["WAIT"] == ()
    assert surviving["CONTEMPLATE"] == ()
    assert open_["CONTEMPLATE"] == ()
    assert surviving["TALK"] == ()
    assert open_["TALK"] == ()


def test_active_seek_pressure_is_open_but_known_navigation_does_not_require_seek() -> None:
    cases = corpus_by_id()

    remembered = cases["navigate_remembered_location"]
    unknown = cases["search_unknown_resource"]

    assert remembered.proposed_skills == ("SEEK",)
    assert remembered.surviving_candidates == ()
    assert remembered.open_candidates == ()

    assert unknown.proposed_skills == ("SEEK",)
    assert unknown.surviving_candidates == ()
    assert unknown.open_candidates == ("SEEK",)


def test_current_real_skill_surfaces_survive_without_claiming_irreducibility() -> None:
    surviving = surviving_basis_usage()

    assert "eat_available_food" in surviving["EAT"]
    assert "direct_combat" in surviving["FIGHT"]
    assert "escape_threat" in surviving["FLEE"]


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

    assert learning.proposed_skills == ()
    assert learning.surviving_candidates == ()
    assert learning.open_candidates == ()
    assert learning.primitives == ()
    assert "Experience Integration" in learning.owners


def test_internal_cognition_does_not_require_contemplate_by_label() -> None:
    cases = corpus_by_id()

    planning = cases["plan_multi_step_expedition"]
    novel = cases["create_novel_structure"]

    assert planning.proposed_skills == ("CONTEMPLATE",)
    assert planning.surviving_candidates == ()
    assert planning.open_candidates == ()

    assert "CONTEMPLATE" in novel.proposed_skills
    assert "CONTEMPLATE" not in novel.surviving_candidates
    assert "CONTEMPLATE" not in novel.open_candidates


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
        rejected_named_compounds.isdisjoint(case.proposed_skills)
        for case in BEHAVIOR_CORPUS
    )
