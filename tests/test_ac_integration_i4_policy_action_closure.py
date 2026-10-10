"""I4: source-issued test World outcomes after actual retained S11 candidate choice."""
from __future__ import annotations

import json
from dataclasses import replace

import pytest

from experiments import ac_integration_i4_policy_action_closure as i4
from experiments.ac_b_b11_governed_habit import CurrentWorld
from experiments.ac_b_b15_delayed_noise import DelayedEpisode


def _qualified_policies():
    world = CurrentWorld()
    episode = DelayedEpisode(world, 0, None, None)
    for tick in range(10):
        if tick < 8:
            episode.issue_at(tick)
        episode.release_at(tick)
    assert episode.command_count == 8
    assert episode.delivered_count == 8
    return world, episode


def test_frozen_manifest_is_exact_and_nonphysical():
    m = i4.freeze_readback()
    assert m["owner_issue"] == 511
    assert m["base_b15"] == "68f23eb7b51cf761c6f8eccc575fc2749a55755c"
    assert m["checkpoints"] == [0, 9]
    assert m["delays"] == [2, 0, 3, 1, 2, 0, 3, 1]
    assert m["physical_minecraft"] is False
    assert m["action_supervisor_issued"] is False
    assert m["eval_receipts_feed_training"] is False


def test_three_phases_actually_issue_frozen_world_outcomes_with_cheap_null():
    result = i4.run_i4_simulator_closure()
    assert result["classification"] == "I4_SIMULATOR_L1_ACTION_OUTCOME_CLOSED_CHEAP_PARITY"
    assert result["source_session"] == "b11-sim-world"
    assert result["source_revision"] == 0
    assert result["shared_training_world_actions"] == 24
    assert result["policy_chosen_world_actions"] == 38
    assert result["total_actual_simulator_world_actions"] == 62
    assert result["per_arm_world_actions"] == (19, 19)
    assert result["per_arm_success"] == (14, 14)
    assert all(
        result[name] is False
        for name in (
            "source_is_physical_minecraft", "action_supervisor_issued",
            "production_habit_owner", "actual_l2", "measured_resource_advantage",
            "production_go",
        )
    )
    reports = result["phase_reports"]
    assert tuple(p["followup_actions"] for p in reports) == (8, 16, 14)
    assert tuple(p["habit_world_success"] for p in reports) == (4, 4, 6)
    assert tuple(p["tag_world_success"] for p in reports) == (4, 4, 6)
    assert tuple(p["contradiction_tick"] for p in reports) == (None, 1, 2)
    assert all(p["source_training_actions"] == p["source_training_receipts"] == 8
               for p in reports)
    assert all(p["evaluation_released_to_training"] is False for p in reports)
    trials = result["trials"]
    assert len(trials) == 48
    issued = [t for t in trials if t.source_observation is not None]
    assert len(issued) == 38
    assert len({t.source_observation.event_id for t in issued}) == 38
    assert all(
        t.source_observation.action == t.selected_action
        and t.status == "SIMULATOR_WORLD_TERMINAL_OBSERVED"
        and t.source_observation.session == "b11-sim-world"
        and t.source_observation.kind == "OBSERVED_ACTION"
        and t.source_observation.success is t.success
        for t in issued
    )
    assert all(t.status == "ABSTAIN_NO_ACTION" and not t.success
               for t in trials if t.source_observation is None)


def test_same_world_actual_actions_expose_stale_habits_and_noisy_false_promotion():
    trials = i4.run_i4_simulator_closure()["trials"]
    lookup = {
        (t.phase, t.tick, t.a, t.b, t.arm): t
        for t in trials
    }
    # At time0 after unannounced change, four old Habits/tags execute and ALL FAIL.
    for a in (0, 1):
        for b in (0, 1):
            for arm in i4.ARMS:
                sample = lookup[(1, 0, a, b, arm)]
                assert sample.source_observation is not None
                assert sample.success is False
    # Before reported-noise release, the current correct policy acts successfully.
    for a in (0, 1):
        for b in (0, 1):
            for arm in i4.ARMS:
                sample = lookup[(2, 0, a, b, arm)]
                assert sample.success is True
    # After corrupt source: ambiguous reported (0,0) -> no Action; coherent but wrong
    # (1,1) -> actual terminal World FAIL in BOTH policies.
    for arm in i4.ARMS:
        assert lookup[(2, 9, 0, 0, arm)].source_observation is None
        assert lookup[(2, 9, 1, 1, arm)].source_observation is not None
        assert lookup[(2, 9, 1, 1, arm)].success is False
    assert all(
        a.selected_action == b.selected_action and a.success == b.success
        for a, b in zip(trials[::2], trials[1::2])
    )


def test_zero_evidence_means_abstain_without_new_simulator_action():
    world = CurrentWorld()
    engine = DelayedEpisode(world, 0, None, None)
    engine.issue_at(0)
    assert engine.release_at(0) == ()
    old = world.actions_executed
    permit = i4.mint_fixture_permit(
        world, engine.policies, phase=0, tick=0, a=0, b=0, arm="HABIT",
    )
    assert permit.selected_action is None
    spent = set()
    result = i4.run_scoped_simulator_action(world, engine.policies, permit, spent)
    assert result.status == "ABSTAIN_NO_ACTION"
    assert result.source_observation is None
    assert world.actions_executed == old
    assert spent == {permit.trial_id}
    assert engine.published == []
    with pytest.raises(i4.I4UnqualifiedTrial):
        i4.run_scoped_simulator_action(world, engine.policies, permit, spent)


@pytest.mark.parametrize("field,value", [
    ("granted", False),
    ("arm", "PHYSICAL_ACTION"),
    ("phase", 3),
    ("phase", True),
    ("tick", 5),
    ("tick", True),
    ("a", 2),
    ("b", True),
    ("source_session", "Minecraft-LIVE"),
    ("source_revision", 1),
    ("source_revision", True),
    ("source_world_identity", -1),
    ("owner_revision", 0),
    ("trial_id", "i4:0:9:0:0:OTHER"),
    ("selected_action", 3),
    ("selected_action", True),
])
def test_test_only_permit_scope_does_not_authorize_unknown_action(field, value):
    world, engine = _qualified_policies()
    permit = i4.mint_fixture_permit(
        world, engine.policies, phase=0, tick=9, a=0, b=0, arm="HABIT",
    )
    assert permit.selected_action in (0, 1)
    old_count = world.actions_executed
    changed = replace(permit, **{field: value})
    with pytest.raises(i4.I4UnqualifiedTrial):
        i4.run_scoped_simulator_action(world, engine.policies, changed, set())
    assert world.actions_executed == old_count


def test_explicit_test_permit_replay_fails_and_world_observation_cannot_be_copied():
    world, engine = _qualified_policies()
    before_owner = engine.policies.owner
    before_reports = tuple(engine.published)
    permit = i4.mint_fixture_permit(
        world, engine.policies, phase=0, tick=9, a=1, b=1, arm="CHEAP_TAG",
    )
    spent = set()
    receipt = i4.run_scoped_simulator_action(world, engine.policies, permit, spent)
    assert receipt.source_observation is not None
    assert world.observed(receipt.source_observation)
    assert not world.observed(replace(receipt.source_observation))
    assert engine.policies.owner is before_owner
    assert tuple(engine.published) == before_reports
    assert engine.delivered_count == 8
    with pytest.raises(i4.I4UnqualifiedTrial):
        i4.run_scoped_simulator_action(world, engine.policies, permit, spent)


def test_foreign_world_exact_identical_properties_not_source_qualification():
    world, engine = _qualified_policies()
    permit = i4.mint_fixture_permit(
        world, engine.policies, phase=0, tick=9, a=0, b=0, arm="HABIT",
    )
    other = CurrentWorld()
    assert (other.session, other.revision) == (world.session, world.revision)
    with pytest.raises(i4.I4UnqualifiedTrial):
        i4.run_scoped_simulator_action(other, engine.policies, permit, set())


def test_no_outcome_can_be_observed_before_it_is_world_executed():
    world, engine = _qualified_policies()
    permit = i4.mint_fixture_permit(
        world, engine.policies, phase=0, tick=9, a=0, b=1, arm="HABIT",
    )
    before = world.actions_executed
    assert len(engine.published) == 8
    result = i4.run_scoped_simulator_action(world, engine.policies, permit, set())
    assert result.source_observation is not None
    assert world.actions_executed == before + 1
    assert len(engine.published) == 8
    assert result.source_observation not in engine.published


def test_no_implicit_production_owner_or_s15_action_launch():
    with open(i4.__file__, encoding="utf-8") as stream:
        text = stream.read()
    for banned in (
        "ActionSupervisor(", "issue_bound_action(", "commit_learning_update(",
        "commit_experiment_habit(", "MineflayerProcessSession(", ".authorize(",
        "request_correlated_post_action_probe(", "asyncio.create_task(",
        "source_is_physical_minecraft=True", "production_go=True",
    ):
        assert banned not in text


def test_frozen_manifest_tamper_rejected(monkeypatch, tmp_path):
    manifest = i4.freeze_readback()
    manifest["expected_per_arm_successes"] = 99
    alternate = tmp_path / "fake-manifest.json"
    alternate.write_text(json.dumps(manifest), encoding="utf-8")
    monkeypatch.setattr(i4, "MANIFEST_PATH", alternate)
    with pytest.raises(i4.I4UnqualifiedTrial):
        i4.freeze_readback()
