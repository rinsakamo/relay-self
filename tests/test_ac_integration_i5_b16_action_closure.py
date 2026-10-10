"""I5: genuine B11 source-issued simulator outcomes after B16 learned choices."""
from __future__ import annotations

import json
from dataclasses import replace

import pytest

from experiments import ac_integration_i5_b16_action_closure as i5
from experiments.ac_b_b11_governed_habit import CurrentWorld, empty_repertoire
from experiments.ac_b_b16_quorum import (
    BatchLedger,
    QuorumNotQualified,
    commit_test_quorum_habit,
    initial_state,
    issue_observed_trial,
    issue_test_authority,
    native_s10_commit,
    propose_quorum_habit,
)
from relay_self.learning import (
    LearningUpdateAuthority,
    MissingLearningAuthority,
)
from relay_self.provenance import Provenance


def _early():
    world = CurrentWorld(session="b16-offline-clean")
    pair = issue_observed_trial(world, 0, 0, 0, noisy=False)
    batch = BatchLedger(world, 0, 0, (pair,))
    owner = empty_repertoire(label="i5-test-owner")
    permit = i5.mint_test_permit(
        world, batch, owner, arm="ONE_SHOT", checkpoint=i5.EARLY,
    )
    return world, batch, owner, permit


def test_prospective_manifest_immutable_and_synthetic():
    m = i5.frozen_manifest()
    assert m["owner_issue"] == 515
    assert m["total_training_actions"] == 80
    assert m["expected_total_extra_actions"] == 21
    assert m["expected_total_world_actions"] == 101
    assert m["early_training_checkpoint"] == 8
    assert m["late_training_checkpoint"] == 40
    assert m["evaluation_receipts_are_training"] is False
    assert m["native_s16_s17_world_join"] is False
    assert m["real_minecraft"] is False
    assert m["s11_production_owner"] is False
    assert m["production_go"] is False


def test_actual_b16_policy_issued_simulator_world_closed_to_terminal_and_cheap_null():
    result = i5.run_i5_closure()
    assert result["classification"] == (
        "I5_B16_QUORUM_SIMULATOR_ACTION_CLOSURE_CHEAP_COUNT_PARITY"
    )
    assert result["training_actions"] == 80
    assert result["followup_actions"] == 21
    assert result["all_simulator_actions"] == 101
    assert result["arm_results"] == {
        "ONE_SHOT": (7, 4), "S11_QUORUM": (7, 6), "CHEAP_COUNT": (7, 6),
    }
    assert result["quorum_benefit_is_not_s10_specific"] is True
    assert result["cheap_count_matches_s11"] is True
    for key in (
        "native_minecraft", "native_s16_s17_world_join",
        "production_habit_owner", "measured_resource_advantage", "actual_l2",
        "production_go",
    ):
        assert result[key] is False
    clean, noisy = result["episodes"]
    assert (clean["episode"], noisy["episode"]) == ("clean", "adversarial")
    assert clean["training_actions"] == noisy["training_actions"] == 40
    assert (clean["followup_actions"], noisy["followup_actions"]) == (12, 9)
    assert (clean["total_world_actions"], noisy["total_world_actions"]) == (52, 49)
    assert clean["counts"] == {
        "ONE_SHOT": (4, 4), "S11_QUORUM": (4, 4), "CHEAP_COUNT": (4, 4),
    }
    assert noisy["counts"] == {
        "ONE_SHOT": (3, 0), "S11_QUORUM": (3, 2), "CHEAP_COUNT": (3, 2),
    }
    assert clean["native_s10_commits"] == clean["separate_s11_test_grants"] == 4
    assert noisy["native_s10_commits"] == noisy["separate_s11_test_grants"] == 3
    assert clean["new_owner_revision"] == 4
    assert noisy["new_owner_revision"] == 3
    assert clean["original_owner_revision"] == noisy["original_owner_revision"] == 0
    for episode in (clean, noisy):
        closures = episode["closures"]
        assert len(closures) == 12
        assert len({row.trial_id for row in closures}) == 12
        for trial in closures:
            assert trial.release_to_learning is False
            assert trial.s15_action_issued is False
            assert trial.native_world_attested is False
            assert trial.production_go is False
            if trial.source_event is not None:
                assert trial.terminal == "SIMULATOR_SOURCE_ACTION_TERMINAL"
                assert trial.source_event.kind == "OBSERVED_ACTION"
                assert trial.source_event.success is trial.success
                assert trial.source_event.action == trial.selected_action
            else:
                assert trial.terminal == "ABSTAIN_NO_SOURCE_ACTION"
                assert trial.selected_action is None and not trial.success


def test_noisy_one_shot_source_corruption_leads_real_wrong_actions():
    result = i5.run_i5_closure()
    noisy = result["episodes"][1]
    early = [x for x in noisy["closures"] if x.arm == "ONE_SHOT"]
    assert len(early) == 4
    assert sum(x.source_event is not None for x in early) == 3
    assert sum(x.success for x in early) == 0
    assert all(not x.success for x in early)
    # 3/5 corrupt pair refuses quorum; 5/5 consistent corruption gives a
    # confidently WRONG Habit and count result in both late arms.
    for arm in ("S11_QUORUM", "CHEAP_COUNT"):
        late = [x for x in noisy["closures"] if x.arm == arm]
        assert len(late) == 4
        assert sum(x.source_event is not None for x in late) == 3
        missing = next(x for x in late if (x.a, x.b) == (1, 0))
        wrong = next(x for x in late if (x.a, x.b) == (1, 1))
        assert missing.source_event is None and not missing.success
        assert wrong.source_event is not None and not wrong.success


def test_one_shot_actual_action_changes_world_count_and_is_not_training():
    world, ledger, owner, permit = _early()
    before = world.actions_executed
    original = tuple(ledger.trials)
    spent = set()
    closed = i5.execute_scoped_test_action(world, ledger, owner, permit, spent)
    assert world.actions_executed == before + 1
    assert closed.source_event is not None
    assert world.observed(closed.source_event)
    assert not world.observed(replace(closed.source_event))
    assert closed.source_event.event_id not in ledger.evidence_ids
    assert ledger.trials == original
    assert ledger.first_shot() == 0
    assert owner.revision == 0 and owner.rules == ()
    with pytest.raises(i5.I5Rejected):
        i5.execute_scoped_test_action(world, ledger, owner, permit, spent)


@pytest.mark.parametrize(("field", "value"), [
    ("granted", False),
    ("arm", "PRODUCTION_S15"),
    ("arm", "CHEAP_COUNT"),
    ("checkpoint", i5.LATE),
    ("session", "foreign-session"),
    ("source_revision", 1),
    ("source_revision", True),
    ("source_world_id", 0),
    ("source_world_id", True),
    ("a", 1),
    ("a", True),
    ("b", 1),
    ("b", True),
    ("owner_id", "stale-Habit"),
    ("owner_revision", 1),
    ("owner_revision", True),
    ("trial_id", "unknown-ID"),
    ("selected_action", 1),
    ("selected_action", True),
])
def test_malformed_or_cross_grant_cannot_issue_even_test_world_action(field, value):
    world, ledger, owner, permit = _early()
    before = world.actions_executed
    altered = replace(permit, **{field: value})
    with pytest.raises(i5.I5Rejected):
        i5.execute_scoped_test_action(world, ledger, owner, altered, set())
    assert world.actions_executed == before


def test_cross_world_even_identical_session_and_revision_is_denied():
    world, ledger, owner, permit = _early()
    clone = CurrentWorld(session=world.session)
    assert clone.session == world.session and clone.revision == world.revision
    with pytest.raises(i5.I5Rejected):
        i5.execute_scoped_test_action(clone, ledger, owner, permit, set())


def test_no_full_quorum_from_first_pair_or_premature_cheap_count():
    world, ledger, owner, _ = _early()
    with pytest.raises(i5.I5Rejected):
        i5.mint_test_permit(world, ledger, owner, arm="S11_QUORUM", checkpoint=i5.LATE)
    with pytest.raises(i5.I5Rejected):
        i5.mint_test_permit(world, ledger, owner, arm="CHEAP_COUNT", checkpoint=i5.LATE)


def test_actual_s10_permission_and_independent_s11_test_grant_are_distinct():
    world = CurrentWorld(session="b16-offline-clean")
    batch = BatchLedger(
        world, 0, 0,
        tuple(issue_observed_trial(world, 0, 0, idx, noisy=False)
              for idx in range(5)),
    )
    with pytest.raises((QuorumNotQualified, MissingLearningAuthority)):
        native_s10_commit(batch, None)
    state = initial_state(batch)
    authority = LearningUpdateAuthority(
        authority_id="i5-explicit-native-S10",
        target_id=state.target_id,
        provenance=Provenance("i5-test-authority", batch.digest),
    )
    actual = native_s10_commit(batch, authority)
    owner = empty_repertoire(label="i5-authority-test")
    draft = propose_quorum_habit(batch, owner, actual)
    with pytest.raises(QuorumNotQualified):
        commit_test_quorum_habit(batch, owner, actual, draft, None)
    denied = replace(issue_test_authority(draft), granted=False)
    with pytest.raises(QuorumNotQualified):
        commit_test_quorum_habit(batch, owner, actual, draft, denied)
    updated = commit_test_quorum_habit(
        batch, owner, actual, draft, issue_test_authority(draft),
    )
    assert owner.revision == 0 and updated.revision == 1
    with pytest.raises(QuorumNotQualified):
        commit_test_quorum_habit(
            batch, updated, actual, draft, issue_test_authority(draft),
        )


def test_replay_history_is_caller_local_not_production_durable():
    world, ledger, owner, permit = _early()
    spent = {permit.trial_id}
    with pytest.raises(i5.I5Rejected):
        i5.execute_scoped_test_action(world, ledger, owner, permit, spent)
    # This is precisely why local permit identity cannot be promoted to product.
    fresh_spent: set[str] = set()
    a = i5.execute_scoped_test_action(world, ledger, owner, permit, fresh_spent)
    assert a.source_event is not None


def test_test_only_source_does_not_automatically_become_s16_minecraft():
    text = open(i5.__file__, encoding="utf-8").read()
    for forbidden in (
        "execute_mineflayer_command(", "ActionSupervisor(", ".authorize(",
        "start_and_propose_bound_execution(", "interpret_action_outcome_as_learning_feedback(",
        "heldout_score(", "asyncio.create_task(", "production_go=True",
        "native_world_attested=True",
    ):
        assert forbidden not in text


def test_frozen_data_tamper_rejected_before_execution(monkeypatch, tmp_path):
    manifest = i5.frozen_manifest()
    manifest["expected_total_world_actions"] = 999
    path = tmp_path / "tampered.json"
    path.write_text(json.dumps(manifest), encoding="utf-8")
    monkeypatch.setattr(i5, "MANIFEST", path)
    with pytest.raises(i5.I5Rejected):
        i5.frozen_manifest()
