"""B23: ACTUAL offline World experiences to L1, with cheap flat rule null."""
from __future__ import annotations

import pytest

from experiments.ac_b_b11_governed_habit import (
    CONTEXTS,
    CurrentWorld,
    cue_for,
    empty_repertoire,
)
from experiments.ac_b_b23_cognitive_loop import (
    CognitiveAgent,
    InconsistentExperience,
    execute_arm,
    run_b23_comparison,
)
from relay_self.habit import HabitSelectionStatus, select_habit


def test_preregistered_all_three_arms_actual_actions_and_cheap_null():
    report = run_b23_comparison()
    assert report["classification"] == "B23_OFFLINE_EXPERIENCE_MEMORY_HABIT_LOOP"
    assert report["habit_and_cheap_exact_stepwise_parity"] is True
    assert report["same_exogenous_schedule_different_world_sources"] is True
    assert report["total_separately_executed_simulator_actions"] == 124
    assert report["generic_retention_actions_saved_vs_no_reuse"] == 10
    assert report["no_real_L2_or_Minecraft"] is True
    assert report["no_production_s11_owner"] is True
    assert report["no_B22_security_dependency"] is True
    expected = {
        "HABIT": (38, 6, 28, 8, 4, 8, 8, 4),
        "CHEAP_TABLE": (38, 6, 28, 8, 4, 8, 0, 0),
        "ALWAYS_RETHINK": (48, 16, 0, 32, 0, 0, 0, 0),
    }
    for arm, values in expected.items():
        r = report["arms"][arm]
        actual, failed, l1, thought, surprise, updates, rev, rules = values
        assert r["actual_world_actions"] == actual
        assert r["encounters"] == r["successful_encounters"] == 32
        assert r["failed_attempts"] == failed
        assert r["L1_selected_attempts"] == l1
        assert r["L2_like_deliberations"] == thought
        assert r["surprise_reconsiderations"] == surprise
        assert r["memory_events"] == actual
        assert r["learned_updates"] == updates
        assert r["retained_s11_revision"] == rev
        assert r["retained_s11_rules"] == rules
        assert r["world_revision"] == 0


def test_silent_flip_not_seen_until_actual_failed_action():
    world = CurrentWorld(session="b23-test-silent-flip")
    a = CognitiveAgent("HABIT", world, owner=empty_repertoire("b23-test-owner"))
    for r in range(1, 4):
        for cue in CONTEXTS:
            row = a.encounter(r, cue)
            assert not row.surprising_failure
    assert world.actions_executed == 14
    assert a.owner.revision == 4
    assert a.surprises == 0
    before = a.owner
    assert tuple(
        select_habit(before, cue_for(*cue, trial="before-flip")).selected_candidate_ref
        for cue in CONTEXTS
    ) == ("action:0", "action:1", "action:1", "action:0")
    world.change_rule(announce=False)
    assert world.revision == 0
    # No explicit rule or public revision announcement. The first
    # previously successful L1 action is actually tried and FAILS.
    row = a.encounter(4, (0, 0))
    assert row.first_action == 0
    assert row.attempted_actions == (0, 1)
    assert row.surprising_failure
    assert row.deliberated_L2_like
    assert a.memory[-2].succeeded is False
    assert a.memory[-1].succeeded is True
    assert a.memory[-1].action == 1
    assert a.owner.revision == 5
    assert select_habit(
        before, cue_for(0, 0, trial="old-copy")
    ).selected_candidate_ref == "action:0"
    assert select_habit(
        a.owner, cue_for(0, 0, trial="new-copy")
    ).selected_candidate_ref == "action:1"
    assert a.prior_owners[-1] is before
    assert a.surprises == 1


def test_all_rules_are_original_successful_world_action_provenance():
    a, result = execute_arm("HABIT")
    assert result.final_s11_revision == 8
    assert result.actual_world_actions == 38
    assert len(a.memory) == 38
    assert len({x.original_event_id for x in a.memory}) == 38
    assert a.owner.rules != ()
    assert len(a.owner.rules) == 4
    for row in a.owner.rules:
        assert row.provenance.source == "b23.original-world-action-success"
        winning = [
            x for x in a.memory
            if x.original_event_id == row.provenance.reference
        ]
        assert len(winning) == 1
        assert winning[0].succeeded is True
        assert row.candidate_ref == f"action:{winning[0].action}"
        assert a.world.observed(winning[0].original_outcome)
    assert all(
        a.world.observed(x.original_outcome)
        and x.original_outcome.success == x.succeeded
        for x in a.memory
    )
    assert len(a.prior_owners) == 8
    assert a.prior_owners[0].revision == 0
    assert a.prior_owners[-1].revision == 7
    assert a.prior_owners[0].rules == ()


def test_habit_and_cheap_exact_every_encounter_and_source_outcome():
    habit, h = execute_arm("HABIT")
    cheap, c = execute_arm("CHEAP_TABLE")
    assert h.matched_traces == c.matched_traces
    assert h.actual_world_actions == c.actual_world_actions == 38
    assert tuple(x.succeeded for x in habit.memory) == tuple(
        x.succeeded for x in cheap.memory
    )
    assert tuple((x.cue, x.action) for x in habit.memory) == tuple(
        (x.cue, x.action) for x in cheap.memory
    )
    for cue in CONTEXTS:
        selection = select_habit(
            habit.owner, cue_for(*cue, trial="post-eight-round-nuisance")
        )
        assert selection.status is HabitSelectionStatus.SELECTED
        assert selection.selected_candidate_ref == f"action:{cheap.cheap[cue]}"
        assert cheap.cheap[cue] == 1 - (cue[0] ^ cue[1])


def test_actual_action0_fails_before_action1_exploration_on_new_cue():
    world = CurrentWorld(session="b23-novel-cue")
    agent = CognitiveAgent("HABIT", world)
    first = agent.encounter(1, (0, 1))
    assert first.first_action == 0
    assert first.attempted_actions == (0, 1)
    assert first.deliberated_L2_like
    assert not first.used_L1
    assert not first.surprising_failure
    assert world.actions_executed == 2
    assert [x.succeeded for x in agent.memory] == [False, True]
    assert agent.owner.revision == 1
    again = agent.encounter(2, (0, 1))
    assert again.first_action == 1
    assert again.attempted_actions == (1,)
    assert again.used_L1
    assert not again.deliberated_L2_like
    assert world.actions_executed == 3
    assert agent.owner.revision == 1


def test_no_reuse_control_actually_executes_worse_action_every_time():
    agent, result = execute_arm("ALWAYS_RETHINK")
    assert result.actual_world_actions == 48
    assert result.failed_attempts == 16
    assert result.L2_like_deliberations == 32
    assert result.L1_selected_attempts == 0
    assert result.final_retained_rule_count == 0
    assert agent.cheap == {}
    assert agent.owner.rules == ()
    for row in agent.encounters:
        assert not row.used_L1
        assert row.first_action == 0
        assert row.attempted_actions in ((0,), (0, 1))


def test_surprise_only_after_retained_prediction_actually_fails():
    agent, _ = execute_arm("HABIT")
    surprising = [e for e in agent.encounters if e.surprising_failure]
    assert len(surprising) == 4
    assert {e.round_id for e in surprising} == {4}
    assert {e.cue for e in surprising} == set(CONTEXTS)
    for encounter in surprising:
        matching = [
            x for x in agent.memory
            if x.round_id == encounter.round_id and x.cue == encounter.cue
        ]
        assert len(matching) == 2
        assert matching[0].succeeded is False
        assert matching[1].succeeded is True
        assert matching[0].action != matching[1].action
    assert all(not e.surprising_failure for e in agent.encounters if e.round_id != 4)


def test_never_consults_scoring_oracle_before_acting(monkeypatch):
    def never_call_hidden_truth(*_args, **_kwargs):
        raise AssertionError("hidden scoring oracle used during inference")
    monkeypatch.setattr(CurrentWorld, "heldout_score", never_call_hidden_truth)
    for arm, expected in (
        ("HABIT", 38), ("CHEAP_TABLE", 38), ("ALWAYS_RETHINK", 48)
    ):
        _, r = execute_arm(arm)
        assert r.actual_world_actions == expected
        assert r.confirmed_successful_encounters == 32


def test_failed_action_never_compiles_retained_success():
    world = CurrentWorld(session="b23-no-false-positives")
    agent = CognitiveAgent("HABIT", world)
    failed = agent.actually_try(1, (0, 1), 0, "BOUNDED_FRESH_THOUGHT")
    assert not failed.success
    with pytest.raises(InconsistentExperience, match="successful"):
        agent._retain((0, 1), failed)
    assert agent.owner.revision == 0 and agent.owner.rules == ()
    assert agent.learned_updates == 0
    genuine = agent.actually_try(1, (0, 1), 1, "FRESH_ALTERNATIVE")
    assert genuine.success
    agent._retain((0, 1), genuine)
    assert agent.owner.revision == 1


def test_unexecuted_foreign_world_outcome_cannot_create_memory_rule():
    world = CurrentWorld(session="b23-current")
    other = CurrentWorld(session="b23-unrelated")
    original_other = other.act(0, 0, 0)
    agent = CognitiveAgent("HABIT", world)
    with pytest.raises(InconsistentExperience, match="unexecuted"):
        agent._retain((0, 0), original_other)
    assert not agent.memory and not agent.owner.rules
    with pytest.raises(InconsistentExperience, match="invalid actual"):
        agent.actually_try(1, (0, 0), 4, "BOUNDED_FRESH_THOUGHT")


def test_memory_preserves_no_mutation_of_old_retained_owner_after_drift():
    agent, _ = execute_arm("HABIT")
    assert tuple(r.revision for r in agent.prior_owners) == tuple(range(8))
    for prev in agent.prior_owners:
        assert prev.revision < agent.owner.revision
    assert agent.prior_owners[3].revision == 3
    assert agent.prior_owners[4].revision == 4
    for cue in CONTEXTS:
        before = select_habit(
            agent.prior_owners[4],
            cue_for(*cue, trial="pre-revision-copy"),
        )
        after = select_habit(
            agent.owner, cue_for(*cue, trial="post-revision-copy"),
        )
        assert before.status is after.status is HabitSelectionStatus.SELECTED
        assert before.selected_candidate_ref != after.selected_candidate_ref


def test_result_step_count_matches_world_original_event_count():
    for arm in ("HABIT", "CHEAP_TABLE", "ALWAYS_RETHINK"):
        agent, report = execute_arm(arm)
        assert sum(len(e.actual_event_ids) for e in agent.encounters) == (
            report.actual_world_actions
        )
        assert agent.world.actions_executed == len(agent.memory)
        ids = tuple(
            event_id for trace in agent.encounters
            for event_id in trace.actual_event_ids
        )
        assert ids == tuple(x.original_event_id for x in agent.memory)
        assert all(not x.unexpected_world_revision for x in agent.encounters)
