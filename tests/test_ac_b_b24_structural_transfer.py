"""B24: novel RELEVANT states, strong cheap polynomial null, impossible twin."""
from __future__ import annotations

import pytest

from experiments.ac_b_b11_governed_habit import empty_repertoire
from experiments.ac_b_b24_structural_transfer import (
    ANCHORS,
    ARMS,
    HELDOUT,
    WORLDS,
    InvalidStructuralExperience,
    StructuralAgent,
    StructuralWorld,
    _habit_cue,
    apply_degree2,
    execute_arm,
    infer_degree2_cheap,
    infer_degree2_gaussian,
    run_b24_comparison,
)
from relay_self.habit import HabitSelectionStatus, select_habit

EXPECTED_COEFFICIENTS = (0, 1, 1, 1, 1, 1, 0, 0, 0, 0, 0)


def test_full_pre_registered_six_matched_arm_comparison():
    result = run_b24_comparison()
    assert result["classification"] == (
        "B24_CONDITIONAL_NOVEL_CUE_TRANSFER_AND_UNDERDETERMINATION"
    )
    assert result["total_separate_sim_world_actions"] == 171
    assert result["identical_training_outcomes_across_worlds"] is True
    assert result["native_S11_and_cheap_degree2_exact_match_both_worlds"] is True
    for key in (
        "no_actual_LLM_L2", "no_real_Minecraft",
        "no_production_S11_owner", "B22_security_sibling_not_used",
    ):
        assert result[key] is True
    expected = {
        ("NORMAL", "STRUCTURAL_S11"): (26, 5, 5, 5, 5),
        ("NORMAL", "CHEAP_DEG2"): (26, 5, 5, 5, 5),
        ("NORMAL", "FLAT_TAG"): (29, 2, 8, 0, 5),
        ("TWIN", "STRUCTURAL_S11"): (31, 0, 10, 5, 5),
        ("TWIN", "CHEAP_DEG2"): (31, 0, 10, 5, 5),
        ("TWIN", "FLAT_TAG"): (28, 3, 7, 0, 5),
    }
    for key, (total, novel_right, novel_actions, novel_models, replay) in expected.items():
        r = result["reports"][key]
        assert r["actual_source_actions"] == total
        assert r["training_source_actions"] == 16
        assert r["novel_first_correct"] == novel_right
        assert r["novel_source_actions"] == novel_actions
        assert r["novel_predictions"] == novel_models
        assert r["replay_source_actions"] == replay
        assert r["total_encounters"] == r["confirmed_successful_encounters"] == 21
        assert r["original_memory_events"] == total
        assert len(r["training_examples"]) == 11
        assert len(r["novel_first_actions"]) == 5
        assert len(r["first_actions_replayed"]) == 5
        assert r["cached_reuse"] == 5
        assert r["S11_revision"] == (16 if key[1] == "STRUCTURAL_S11" else 0)
        assert r["S11_rules"] == (16 if key[1] == "STRUCTURAL_S11" else 0)
        assert r["learned_coefficients"] == (
            EXPECTED_COEFFICIENTS if key[1] != "FLAT_TAG" else None
        )


def test_exact_source_anchor_set_and_true_heldout_relevant_state_novelty():
    assert len(ANCHORS) == 11
    assert len(HELDOUT) == 5
    assert len(set(ANCHORS) | set(HELDOUT)) == 16
    assert set(ANCHORS).isdisjoint(HELDOUT)
    assert all(sum(x) <= 2 for x in ANCHORS)
    assert all(sum(x) >= 3 for x in HELDOUT)
    assert HELDOUT == (
        (0, 1, 1, 1), (1, 0, 1, 1),
        (1, 1, 0, 1), (1, 1, 1, 0), (1, 1, 1, 1),
    )
    assert WORLDS == ("NORMAL", "TWIN")
    assert ARMS == ("STRUCTURAL_S11", "CHEAP_DEG2", "FLAT_TAG")


def test_worlds_identical_on_all_training_inputs_opposite_all_unseen():
    normal = StructuralWorld("b24-twin-control-normal", twin=False)
    twin = StructuralWorld("b24-twin-control-twin", twin=True)
    for cue in ANCHORS:
        for action in (0, 1):
            n, t = normal.act(cue, action), twin.act(cue, action)
            assert n.succeeded == t.succeeded
            assert (n.cue, n.action) == (t.cue, t.action)
            assert normal.observed(n) and twin.observed(t)
    assert normal.actions_executed == twin.actions_executed == 22
    for cue in HELDOUT:
        x, y = normal.act(cue, 0), twin.act(cue, 0)
        assert x.succeeded != y.succeeded
    assert normal.actions_executed == twin.actions_executed == 27


def test_generic_gaussian_and_cheap_direct_algebra_same_training_inputs():
    a, r = execute_arm("NORMAL", "STRUCTURAL_S11")
    examples = a.completed_training_examples()
    gaussian = infer_degree2_gaussian(examples)
    cheap = infer_degree2_cheap(examples)
    assert gaussian == cheap == EXPECTED_COEFFICIENTS
    assert r["learned_coefficients"] == gaussian
    assert all(apply_degree2(gaussian, cue) == target for cue, target in examples)
    assert tuple(apply_degree2(gaussian, c) for c in HELDOUT) == (
        1, 1, 0, 0, 1
    )
    # All source training examples are actual SUCCESS Memory Action records.
    for cue, action in examples:
        confirmed = [
            v for v in a.memory if v.phase == "TRAIN"
            and v.cue == cue and v.original_action.succeeded
        ]
        assert len(confirmed) == 1
        assert a.world.observed(confirmed[0].original_action)
        assert confirmed[0].original_action.action == action


def test_indistinguishable_training_supports_wrong_heldout_alternative():
    normal, n = execute_arm("NORMAL", "STRUCTURAL_S11")
    twin, t = execute_arm("TWIN", "STRUCTURAL_S11")
    assert n["training_examples"] == t["training_examples"]
    assert n["learned_coefficients"] == t["learned_coefficients"]
    assert n["novel_first_actions"] == t["novel_first_actions"]
    assert n["novel_first_results"] == (True,) * 5
    assert t["novel_first_results"] == (False,) * 5
    assert tuple((v.cue, v.original_action.action, v.original_action.succeeded)
                 for v in normal.memory if v.phase == "TRAIN") == tuple(
        (v.cue, v.original_action.action, v.original_action.succeeded)
        for v in twin.memory if v.phase == "TRAIN"
    )


def test_flat_tag_stronger_than_wrong_structure_in_twin_but_weaker_in_normal():
    n = run_b24_comparison()["reports"]
    assert n["NORMAL", "FLAT_TAG"]["novel_first_correct"] == 2
    assert n["NORMAL", "CHEAP_DEG2"]["novel_first_correct"] == 5
    assert n["TWIN", "FLAT_TAG"]["novel_first_correct"] == 3
    assert n["TWIN", "CHEAP_DEG2"]["novel_first_correct"] == 0
    assert n["NORMAL", "FLAT_TAG"]["actual_source_actions"] == 29
    assert n["NORMAL", "CHEAP_DEG2"]["actual_source_actions"] == 26
    assert n["TWIN", "FLAT_TAG"]["actual_source_actions"] == 28
    assert n["TWIN", "CHEAP_DEG2"]["actual_source_actions"] == 31


@pytest.mark.parametrize("kind", WORLDS)
def test_original_frozen_S11_readonly_selects_source_confirmed_rule_on_replay(kind):
    agent, report = execute_arm(kind, "STRUCTURAL_S11")
    assert agent.owner.revision == 16
    assert len(agent.owner.rules) == 16
    assert len(agent.historical_owners) == 16
    assert agent.historical_owners[0].revision == 0
    assert agent.historical_owners[-1].revision == 15
    assert agent.historical_owners[0].rules == ()
    for cue in ANCHORS + HELDOUT:
        match = select_habit(agent.owner, _habit_cue(cue, "fresh-nuisance"))
        assert match.status is HabitSelectionStatus.SELECTED
        rule = match.selected_rule
        assert rule.provenance.source == "b24.original-success-memory"
        selected = [
            e for e in agent.memory
            if e.original_action.event_id == rule.provenance.reference
        ]
        assert len(selected) == 1
        event = selected[0].original_action
        assert agent.world.observed(event)
        assert event.succeeded and event.cue == cue
        assert rule.candidate_ref == f"action:{event.action}"
    assert all(
        e.used_cached_L1
        for e in agent.episodes if e.phase == "REPLAY"
    )
    assert all(
        e.first_correct
        for e in agent.episodes if e.phase == "REPLAY"
    )
    assert report["replay_source_actions"] == 5


def test_actual_novel_success_must_be_in_memory_before_retaining_rule():
    world = StructuralWorld("b24-memory-required", twin=False)
    agent = StructuralAgent("STRUCTURAL_S11", world)
    source_success = world.act((0, 0, 0, 0), 0)
    assert source_success.succeeded
    with pytest.raises(InvalidStructuralExperience, match="latest real Memory"):
        agent._retain((0, 0, 0, 0), source_success)
    assert agent.owner.revision == 0
    agent._remember("TRAIN", (0, 0, 0, 0), "ingested-source", source_success)
    agent._retain((0, 0, 0, 0), source_success)
    assert agent.owner.revision == 1
    different = agent.world.act((1, 0, 0, 0), 1)
    agent._remember("TRAIN", (1, 0, 0, 0), "more-recent", different)
    with pytest.raises(InvalidStructuralExperience, match="latest real Memory"):
        agent._retain((0, 0, 0, 0), source_success)
    assert agent.owner.revision == 1


def test_no_ghost_memory_event_or_implicit_other_action_success():
    world = StructuralWorld("b24-ghost", twin=False)
    foreign = StructuralWorld("b24-other", twin=False)
    agent = StructuralAgent("STRUCTURAL_S11", world)
    other = foreign.act((1, 0, 0, 0), 1)
    with pytest.raises(InvalidStructuralExperience, match="invented"):
        agent._remember("TRAIN", (1, 0, 0, 0), "foreign", other)
    with pytest.raises(InvalidStructuralExperience, match="latest real Memory"):
        agent._retain((1, 0, 0, 0), other)
    assert world.actions_executed == 0
    assert agent.owner.rules == ()


def test_cannot_infer_from_missing_duplicate_or_fabricated_training_winners():
    agent, _ = execute_arm("NORMAL", "CHEAP_DEG2")
    examples = agent.completed_training_examples()
    bad_sets = (
        examples[:10],
        examples[:10] + (examples[0],),
        examples[:10] + (((0, 0, 0, 0), 0),),
    )
    for values in bad_sets:
        with pytest.raises(InvalidStructuralExperience):
            infer_degree2_gaussian(values)
        with pytest.raises(InvalidStructuralExperience):
            infer_degree2_cheap(values)
    changed = examples[:10] + ((examples[10][0], True),)
    with pytest.raises(InvalidStructuralExperience, match="binary"):
        infer_degree2_gaussian(changed)
    with pytest.raises(InvalidStructuralExperience, match="binary"):
        infer_degree2_cheap(changed)


def test_partial_experiences_must_not_generate_unseen_model():
    agent = StructuralAgent(
        "STRUCTURAL_S11", StructuralWorld("b24-partial", twin=False),
        owner=empty_repertoire("b24-partial-original"),
    )
    for i, cue in enumerate(ANCHORS[:10]):
        agent.encounter(cue, "TRAIN", f"only-{i}")
    assert agent.model is None
    with pytest.raises(InvalidStructuralExperience, match="11"):
        agent.learn_structure()
    assert agent.model is None
    # Without a complete model a new relevant cue cannot receive a
    # privileged structural prediction. It only actually tries action0.
    e = agent.encounter(HELDOUT[0], "NOVEL", "untrained")
    assert e.first_action == 0
    assert len(e.attempts) in (1, 2)


def test_inference_is_from_memory_winners_not_extra_world_oracle():
    agent = StructuralAgent(
        "STRUCTURAL_S11", StructuralWorld("b24-source-only", twin=False)
    )
    for i, cue in enumerate(ANCHORS):
        agent.encounter(cue, "TRAIN", f"a-{i}")
    verified_examples = agent.completed_training_examples()
    class WorldWithoutFutureAccess:
        def __getattribute__(self, _name):
            raise AssertionError("structural solver read World during inference")
    agent.world = WorldWithoutFutureAccess()
    # Source eligibility was separately established before inference;
    # the actual model solver consumes ONLY copied successful experiences.
    assert infer_degree2_gaussian(verified_examples) == EXPECTED_COEFFICIENTS
    assert infer_degree2_cheap(verified_examples) == EXPECTED_COEFFICIENTS


@pytest.mark.parametrize("arm", ARMS)
def test_every_action_is_independently_issued_and_memory_ordered(arm):
    for kind in WORLDS:
        agent, result = execute_arm(kind, arm)
        assert agent.world.actions_executed == len(agent.memory)
        ids = tuple(e.original_action.event_id for e in agent.memory)
        assert len(set(ids)) == len(ids)
        assert all(agent.world.observed(e.original_action) for e in agent.memory)
        flattened = tuple(
            id for episode in agent.episodes for id in episode.original_event_ids
        )
        assert flattened == ids
        assert len(agent.episodes) == 21
        assert len(agent.memory) == result["actual_source_actions"]
        assert all(e.confirmed_success for e in agent.episodes)


def test_learning_does_not_mutate_previous_native_S11_snapshots():
    agent, _ = execute_arm("NORMAL", "STRUCTURAL_S11")
    assert tuple(x.revision for x in agent.historical_owners) == tuple(range(16))
    for prior in agent.historical_owners:
        assert prior.revision < agent.owner.revision
        assert len(prior.rules) == prior.revision
    for cue in HELDOUT:
        previous = agent.historical_owners[11]
        before = select_habit(previous, _habit_cue(cue, "before-heldout"))
        current = select_habit(agent.owner, _habit_cue(cue, "after-heldout"))
        assert before.status is HabitSelectionStatus.NO_MATCH
        assert current.status is HabitSelectionStatus.SELECTED


def test_wrong_source_structural_input_and_invalid_arm_fail_closed():
    for cue in ((0, 1, 0), (0, 0, 0, 2), (True, 0, 0, 0)):
        with pytest.raises(InvalidStructuralExperience):
            StructuralWorld("b24-invalid", twin=False).act(cue, 0)
    with pytest.raises(InvalidStructuralExperience):
        StructuralWorld("b24-invalid", twin=False).act(ANCHORS[0], 3)
    with pytest.raises(InvalidStructuralExperience):
        StructuralWorld("b24-invalid", twin="not bool")
    with pytest.raises(InvalidStructuralExperience):
        execute_arm("CLAIRVOYANT", "STRUCTURAL_S11")
    with pytest.raises(InvalidStructuralExperience):
        execute_arm("NORMAL", "ACTUAL_ORACLE")
    with pytest.raises(InvalidStructuralExperience):
        apply_degree2((1,) * 10, HELDOUT[0])
