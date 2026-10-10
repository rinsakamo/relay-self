"""B25: original novel Action evidence discriminates only a GIVEN hypothesis bank."""
from __future__ import annotations

from dataclasses import replace

import pytest

from experiments.ac_b_b11_governed_habit import empty_repertoire
from experiments.ac_b_b24_structural_transfer import (
    ANCHORS,
    HELDOUT,
    InvalidStructuralExperience,
    StructuralAgent,
    StructuralWorld,
    _habit_cue,
)
from experiments.ac_b_b25_discrimination import (
    ARMS,
    CANDIDATES,
    FIRST_PROBE,
    WORLDS,
    B25CognitiveArm,
    InvalidHypothesisEvidence,
    execute_arm,
    known_residual,
    predict,
    run_b25_comparison,
)
from relay_self.habit import HabitSelectionStatus, select_habit

EXPECTED_COEFFS = (0, 1, 1, 1, 1, 1, 0, 0, 0, 0, 0)


def test_all_eight_matched_arms_and_source_action_counts():
    report = run_b25_comparison()
    assert report["classification"] == (
        "B25_CONDITIONAL_SOURCE_DISCRIMINATION_CHEAP_ONE_BIT_NULL"
    )
    assert report["total_independent_sim_world_actions"] == 220
    assert report["training_experiences_identical_between_worlds"] is True
    assert report["full_hypothesis_and_cheap_bit_exact_source_parity"] is True
    assert report["candidate_bank_exogenously_gifted"] is True
    assert report["actual_LLM_L2_run"] is False
    assert report["physical_Minecraft_or_S17"] is False
    assert report["production_S11_acquired"] is False
    assert report["security_B22_used"] is False
    expected = {
        ("NORMAL", "FULL_HYPOTHESIS_S11"): (26, 5, 5, 5),
        ("NORMAL", "CHEAP_HYPOTHESIS_BIT"): (26, 5, 5, 5),
        ("NORMAL", "FIXED_DEG2"): (26, 5, 5, 5),
        ("NORMAL", "FLAT_TAG"): (29, 2, 8, 5),
        ("TWIN", "FULL_HYPOTHESIS_S11"): (27, 4, 6, 5),
        ("TWIN", "CHEAP_HYPOTHESIS_BIT"): (27, 4, 6, 5),
        ("TWIN", "FIXED_DEG2"): (31, 0, 10, 5),
        ("TWIN", "FLAT_TAG"): (28, 3, 7, 5),
    }
    assert set(report["reports"]) == set(expected)
    for (world, policy), (actions, first_right, novel_actions, replay) in expected.items():
        row = report["reports"][world, policy]
        assert row["actual_world_actions"] == actions
        assert row["training_action_attempts"] == 16
        assert row["first_novel_correct"] == first_right
        assert row["first_novel_actions"] == novel_actions
        assert row["replay_actions"] == replay
        assert row["completed_successful_encounters"] == 21
        assert row["memory_events"] == actions
        assert row["reused_cached_L1_on_replay"] is True
        assert row["coefficients"] == (
            EXPECTED_COEFFS if policy != "FLAT_TAG" else None
        )
        assert row["native_S11_revision"] == (
            16 if policy == "FULL_HYPOTHESIS_S11" else 0
        )
        assert row["native_S11_rules"] == (
            16 if policy == "FULL_HYPOTHESIS_S11" else 0
        )
        assert row["first_novel_choices"] == (
            report["reports"][world, "FULL_HYPOTHESIS_S11"][
                "first_novel_choices"
            ] if policy == "CHEAP_HYPOTHESIS_BIT" else row["first_novel_choices"]
        )


@pytest.mark.parametrize("world", WORLDS)
def test_one_actual_novel_probe_discriminates_model_and_cheap_bit_equally(world):
    rich, result = execute_arm(world, "FULL_HYPOTHESIS_S11")
    cheap, plain = execute_arm(world, "CHEAP_HYPOTHESIS_BIT")
    expect = "H1_HIGHER_ORDER" if world == "TWIN" else "H0_DEG2"
    assert rich.hypotheses.candidates == (expect,)
    assert cheap.cheap_mode == expect
    assert result["surviving_structural_candidates"] == (expect,)
    assert plain["cheap_one_bit_selection"] == expect
    assert len(rich.hypotheses.updates) == (
        6 if world == "TWIN" else 5
    )
    assert rich.hypotheses.updates[0].before == CANDIDATES
    assert rich.hypotheses.updates[0].after == (expect,)
    assert rich.hypotheses.updates[0].cue == FIRST_PROBE
    assert rich.hypotheses.updates[0].event_id == rich.discriminating_event
    assert result["source_discriminating_event"] == rich.discriminating_event
    assert plain["source_discriminating_event"] == cheap.discriminating_event
    assert result["first_probe_correct"] == (world == "NORMAL")
    assert plain["first_probe_correct"] == (world == "NORMAL")
    first = tuple(e for e in rich.agent.memory if e.phase == "NOVEL")[0]
    assert first.original_action.event_id == rich.discriminating_event
    assert rich.agent.world.observed(first.original_action)
    assert first.original_action.succeeded == (world == "NORMAL")
    assert result["decision_trace"] == plain["decision_trace"]
    assert result["first_novel_choices"] == plain["first_novel_choices"]


def test_same_complete_train_data_cannot_discriminate_worlds_before_probe():
    normal, n = execute_arm("NORMAL", "FULL_HYPOTHESIS_S11")
    twin, t = execute_arm("TWIN", "FULL_HYPOTHESIS_S11")
    assert n["trained_examples"] == t["trained_examples"]
    assert n["coefficients"] == t["coefficients"] == EXPECTED_COEFFS
    assert n["first_novel_choices"][0] == t["first_novel_choices"][0]
    assert n["first_novel_truth"][0] is True
    assert t["first_novel_truth"][0] is False
    assert n["first_novel_choices"][1:] != t["first_novel_choices"][1:]
    assert tuple(
        (e.cue, e.original_action.action, e.original_action.succeeded)
        for e in normal.agent.memory if e.phase == "TRAIN"
    ) == tuple(
        (e.cue, e.original_action.action, e.original_action.succeeded)
        for e in twin.agent.memory if e.phase == "TRAIN"
    )


def test_hypothesis_bank_disagrees_only_on_unseen_relevant_contexts():
    assert len(ANCHORS) == 11 and len(HELDOUT) == 5
    assert all(known_residual(cue) == 0 for cue in ANCHORS)
    assert all(known_residual(cue) == 1 for cue in HELDOUT)
    assert CANDIDATES == ("H0_DEG2", "H1_HIGHER_ORDER")
    assert ARMS == (
        "FULL_HYPOTHESIS_S11", "CHEAP_HYPOTHESIS_BIT",
        "FIXED_DEG2", "FLAT_TAG",
    )
    assert WORLDS == ("NORMAL", "TWIN")
    for cue in ANCHORS:
        assert predict(EXPECTED_COEFFS, cue, CANDIDATES[0]) == predict(
            EXPECTED_COEFFS, cue, CANDIDATES[1]
        )
    for cue in HELDOUT:
        assert predict(EXPECTED_COEFFS, cue, CANDIDATES[0]) != predict(
            EXPECTED_COEFFS, cue, CANDIDATES[1]
        )


def test_model_revision_improves_twin_but_not_beyond_cheap_bits():
    reports = run_b25_comparison()["reports"]
    for policy in ("FULL_HYPOTHESIS_S11", "CHEAP_HYPOTHESIS_BIT"):
        assert reports["TWIN", policy]["first_novel_correct"] == 4
        assert reports["TWIN", policy]["first_novel_actions"] == 6
        assert reports["TWIN", policy]["actual_world_actions"] == 27
        assert reports["NORMAL", policy]["first_novel_correct"] == 5
        assert reports["NORMAL", policy]["actual_world_actions"] == 26
    assert reports["TWIN", "FIXED_DEG2"]["first_novel_correct"] == 0
    assert reports["TWIN", "FIXED_DEG2"]["actual_world_actions"] == 31
    assert reports["TWIN", "FLAT_TAG"]["first_novel_correct"] == 3
    assert reports["TWIN", "FLAT_TAG"]["actual_world_actions"] == 28
    assert reports["NORMAL", "FLAT_TAG"]["first_novel_correct"] == 2
    assert reports["NORMAL", "FLAT_TAG"]["actual_world_actions"] == 29


def test_source_retained_s11_rules_bound_to_actual_successful_memory():
    runner, r = execute_arm("TWIN", "FULL_HYPOTHESIS_S11")
    native = runner.agent
    assert native.owner.revision == 16
    assert len(native.owner.rules) == 16
    assert len(native.historical_owners) == 16
    assert native.historical_owners[0].revision == 0
    for cue in ANCHORS + HELDOUT:
        item = select_habit(native.owner, _habit_cue(cue, "new-nuisance"))
        assert item.status is HabitSelectionStatus.SELECTED
        rule = item.selected_rule
        assert rule.provenance.source == "b24.original-success-memory"
        matches = [
            entry.original_action for entry in native.memory
            if entry.original_action.event_id == rule.provenance.reference
        ]
        assert len(matches) == 1
        observed = matches[0]
        assert native.world.observed(observed)
        assert observed.succeeded
        assert observed.cue == cue
        assert rule.candidate_ref == f"action:{observed.action}"
    assert r["reused_cached_L1_on_replay"] is True
    assert native.historical_owners[0].rules == ()
    assert len(native.historical_owners[-1].rules) == 15


def test_phantom_or_cloned_report_cannot_discriminate():
    world = StructuralWorld("b25-original-only", twin=True)
    agent = StructuralAgent(
        "STRUCTURAL_S11", world,
        owner=empty_repertoire("b25-owner-actual-only"),
    )
    rich = B25CognitiveArm("FULL_HYPOTHESIS_S11", agent)
    rich.learn_from_world()
    choice = rich._select_novel(FIRST_PROBE)
    result = world.act(FIRST_PROBE, choice)
    with pytest.raises(InvalidHypothesisEvidence, match="latest original"):
        rich.hypotheses.observe(agent, result)
    cloned = replace(result)
    agent._remember("NOVEL", FIRST_PROBE, "probe", result)
    with pytest.raises(InvalidHypothesisEvidence, match="latest original"):
        rich.hypotheses.observe(agent, cloned)
    with pytest.raises(InvalidHypothesisEvidence, match="latest actual Memory"):
        rich._update_after_source(FIRST_PROBE, cloned)
    update = rich.hypotheses.observe(agent, result)
    assert update.after == ("H1_HIGHER_ORDER",)
    assert rich.hypotheses.candidates == ("H1_HIGHER_ORDER",)


def test_cheap_bit_does_not_switch_before_real_probe_or_outside_first_cue():
    world = StructuralWorld("b25-cheap-source-only", twin=True)
    agent = StructuralAgent(
        "CHEAP_DEG2", world,
        owner=empty_repertoire("b25-cheap-source-only"),
    )
    cheap = B25CognitiveArm("CHEAP_HYPOTHESIS_BIT", agent)
    cheap.learn_from_world()
    assert cheap.cheap_mode is None
    initial = cheap._select_novel(FIRST_PROBE)
    assert initial == predict(agent.model, FIRST_PROBE, "H0_DEG2")
    assert world.actions_executed == 16
    with pytest.raises(InvalidHypothesisEvidence, match="latest actual Memory"):
        cheap._update_after_source(
            FIRST_PROBE, world.act(FIRST_PROBE, initial),
        )
    assert cheap.cheap_mode is None
    cheap.novel_encounter(FIRST_PROBE, 0)
    assert cheap.cheap_mode == "H1_HIGHER_ORDER"


def test_partial_training_does_not_allow_hypothesis_selection():
    world = StructuralWorld("b25-not-full-train", twin=False)
    runner = B25CognitiveArm(
        "FULL_HYPOTHESIS_S11", StructuralAgent(
            "STRUCTURAL_S11", world,
            owner=empty_repertoire("b25-partial-s11"),
        ),
    )
    for i, cue in enumerate(ANCHORS[:10]):
        runner.agent.encounter(cue, "TRAIN", f"partial-{i}")
    with pytest.raises(InvalidHypothesisEvidence, match="unseen relevant hypothesis cue"):
        runner._select_novel(FIRST_PROBE)
    with pytest.raises(Exception):
        runner.agent.learn_structure()
    assert len(runner.hypotheses.updates) == 0


def test_predictions_do_not_call_world_truth_or_oracle_before_source_action():
    native = StructuralAgent(
        "STRUCTURAL_S11",
        StructuralWorld("b25-knowledge-boundary", twin=False),
        owner=empty_repertoire("b25-knowledge-boundary"),
    )
    rich = B25CognitiveArm("FULL_HYPOTHESIS_S11", native)
    rich.learn_from_world()
    source_before = native.world.actions_executed
    original_world = native.world
    class NoKnowledgeWorld:
        def __getattribute__(self, _name):
            raise AssertionError("model prediction accessed World before Action")
    native.world = NoKnowledgeWorld()
    prediction = rich._select_novel(FIRST_PROBE)
    assert prediction == predict(native.model, FIRST_PROBE, "H0_DEG2")
    native.world = original_world
    assert native.world.actions_executed == source_before
    assert rich.hypotheses.candidates == CANDIDATES


def test_original_event_chronology_exactly_matches_memory():
    for world in WORLDS:
        for policy in ARMS:
            runner, report = execute_arm(world, policy)
            memory = runner.agent.memory
            assert runner.agent.world.actions_executed == len(memory)
            ids = tuple(x.original_action.event_id for x in memory)
            assert len(set(ids)) == len(ids)
            assert all(runner.agent.world.observed(x.original_action) for x in memory)
            assert ids == tuple(
                event_id for e in runner.agent.episodes
                for event_id in e.original_event_ids
            )
            assert report["memory_events"] == len(memory)
            assert report["completed_successful_encounters"] == 21


def test_unfamiliar_arm_or_candidate_and_invalid_source_fail_closed():
    with pytest.raises(InvalidHypothesisEvidence, match="candidate"):
        predict(EXPECTED_COEFFS, FIRST_PROBE, "CLAIRVOYANT")
    with pytest.raises(InvalidHypothesisEvidence, match="frozen"):
        execute_arm("UNKNOWN_WORLD", "FULL_HYPOTHESIS_S11")
    with pytest.raises(InvalidHypothesisEvidence, match="frozen"):
        execute_arm("NORMAL", "REAL_L2_WAS_QUALIFIED")
    with pytest.raises(InvalidStructuralExperience):
        known_residual((0, 1, 2, 0))
