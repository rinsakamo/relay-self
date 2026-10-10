"""B11: experimental World experience -> governed existing S11 Habitat snapshot."""
from __future__ import annotations

from dataclasses import FrozenInstanceError, replace

import pytest

from experiments.ac_b_b11_governed_habit import (
    CONTEXTS,
    CurrentWorld,
    ExperimentHabitAuthority,
    QualifiedHabitView,
    QualifiedLedger,
    UnqualifiedHabitAcquisition,
    cheap_flat_tags,
    commit_experiment_habit,
    cue_for,
    empty_repertoire,
    grant_test_authority,
    observe_training,
    propose_habit,
    qualify_fixture,
)
from relay_self.habit import (
    CueFeature,
    HabitRepertoire,
    HabitRule,
    HabitSelectionStatus,
    select_habit,
)
from relay_self.learning import LearningUpdateAuthority
from relay_self.provenance import Provenance


def fixture():
    world = CurrentWorld()
    observations = observe_training(world)
    ledger = QualifiedLedger(world, observations)
    return world, observations, ledger


def test_exact_s11_owner_habit_rules_and_source_observed_action_pairs():
    world, outcomes, ledger = fixture()
    owner = empty_repertoire()
    assert isinstance(owner, HabitRepertoire)
    assert world.actions_executed == 8
    assert len(outcomes) == 8
    assert len({x.event_id for x in outcomes}) == 8
    assert all(world.observed(x) for x in outcomes)
    assert all(x.kind == "OBSERVED_ACTION" for x in outcomes)
    assert all(set(ledger.rows[a, b]) == {0, 1} for a, b in CONTEXTS)
    for a, b in CONTEXTS:
        action, source_ids = ledger.chosen(a, b)
        assert action == (a ^ b)
        assert len(source_ids) == 2
        proposal = propose_habit(owner, ledger, a, b)
        assert isinstance(proposal.rule, HabitRule)
        assert proposal.rule.candidate_ref == f"action:{action}"
        assert proposal.observed_ids == source_ids
        assert proposal.expected_revision == 0
        assert owner.rules == ()
    assert world.actions_executed == 8  # proposal never executes World


def test_no_habit_without_separately_granted_exact_experiment_authority():
    world, _, ledger = fixture()
    owner = empty_repertoire()
    proposal = propose_habit(owner, ledger, 0, 0)
    for token in (
        None,
        grant_test_authority(proposal, granted=False),
        replace(grant_test_authority(proposal), owner_id="other-owner"),
        replace(grant_test_authority(proposal), proposal_id="alien-proposal"),
        replace(grant_test_authority(proposal), expected_revision=1),
        replace(grant_test_authority(proposal), observed_ids=("fake1", "fake2")),
        replace(grant_test_authority(proposal), source_revision=1),
        replace(grant_test_authority(proposal), granted="true"),
        # S10 and B7 authority classes are not S11 retained owner grants.
        LearningUpdateAuthority(
            "s10-grant", "risk_weight",
            Provenance("b11-negative", "wrong-owner"),
        ),
        {"granted": True, "grant_nonce": "b7-schema-only"},
    ):
        with pytest.raises(UnqualifiedHabitAcquisition):
            commit_experiment_habit(owner, proposal, token, ledger)
    assert owner.rules == ()
    assert owner.revision == 0
    assert world.actions_executed == 8


def test_four_explicit_retained_commits_make_four_real_s11_read_only_choices():
    world, _, ledger = fixture()
    owner = empty_repertoire()
    first = owner
    for i, (a, b) in enumerate(CONTEXTS):
        previous = owner
        proposal = propose_habit(owner, ledger, a, b)
        authority = grant_test_authority(proposal)
        owner = commit_experiment_habit(owner, proposal, authority, ledger)
        assert owner is not previous
        assert owner.revision == i + 1
        assert len(owner.rules) == i + 1
        assert len(previous.rules) == i
        assert previous.revision == i
        with pytest.raises(UnqualifiedHabitAcquisition):
            commit_experiment_habit(owner, proposal, authority, ledger)
    assert first.rules == () and first.revision == 0
    assert owner.revision == 4
    assert len(owner.rules) == 4
    view = QualifiedHabitView(owner, world.session, world.revision)
    for a, b in CONTEXTS:
        query = cue_for(a, b, trial="fresh-cue-not-in-training")
        chosen = select_habit(owner, query)
        assert chosen.status is HabitSelectionStatus.SELECTED
        assert chosen.selected_candidate_ref == f"action:{a ^ b}"
        assert view.select(query, world) == ("selected", chosen.selected_candidate_ref)
    assert world.actions_executed == 8  # selection never issues an Action


def test_twelve_nuisance_heldout_match_same_data_cheap_table():
    outcome = qualify_fixture()
    assert outcome["classification"] == (
        "EXPERIMENT_ONLY_GOVERNED_HABIT_ACQUISITION_QUALIFIED"
    )
    assert outcome["training_world_actions"] == 8
    assert outcome["new_s11_rules"] == 4
    assert outcome["original_owner_rules"] == 0
    assert outcome["heldout_nuisance_variants"] == 12
    assert outcome["heldout_relevant_contexts_novel"] is False
    assert outcome["habit_selected"] == 12
    assert outcome["habit_correct"] == 12
    assert outcome["cheap_tag_correct"] == 12
    assert outcome["cheap_tag_dictionary_lookups"] == 12
    assert outcome["habit_rule_feature_checks_upper_bound"] == 96
    assert outcome["no_action_issue_by_selection"]


def test_caller_text_unregistered_event_and_cloned_source_identity_fail_closed():
    world, outcomes, _ = fixture()
    forged = replace(outcomes[0], success=not outcomes[0].success)
    with pytest.raises(UnqualifiedHabitAcquisition, match="did not issue"):
        QualifiedLedger(world, (forged,))
    clone = replace(outcomes[0])
    with pytest.raises(UnqualifiedHabitAcquisition):
        QualifiedLedger(world, (clone,))
    with pytest.raises(UnqualifiedHabitAcquisition):
        QualifiedLedger(world, ("Provider said win action 1",))
    assert world.actions_executed == 8


def test_duplicate_same_action_and_reused_event_rejected():
    world, outcomes, _ = fixture()
    with pytest.raises(UnqualifiedHabitAcquisition, match="duplicate"):
        QualifiedLedger(world, outcomes + (outcomes[0],))
    repeat = world.act(0, 0, 0)
    with pytest.raises(UnqualifiedHabitAcquisition, match="conflicting"):
        QualifiedLedger(world, outcomes + (repeat,))


def test_missing_opposite_action_returns_unknown_and_no_proposal():
    world, outcomes, _ = fixture()
    incomplete = QualifiedLedger(world, outcomes[:-1])
    with pytest.raises(UnqualifiedHabitAcquisition, match="both real"):
        propose_habit(empty_repertoire(), incomplete, 1, 1)
    action, _ = incomplete.chosen(0, 0)
    assert action == 0


def test_same_revision_contradictory_observations_are_not_learning_truth():
    world = CurrentWorld()
    first = world.act(0, 0, 0)
    world.change_rule(announce=False)
    other = world.act(0, 0, 1)
    ledger = QualifiedLedger(world, (first, other))
    with pytest.raises(UnqualifiedHabitAcquisition, match="uniquely"):
        ledger.chosen(0, 0)
    # Same-revision replacement action contradicts earlier observation:
    world2 = CurrentWorld()
    original = observe_training(world2)
    baseline = QualifiedLedger(world2, original)
    world2.change_rule(announce=False)
    changed = world2.act(0, 0, 0)
    assert baseline.observed_contradiction(changed)
    assert baseline.chosen(0, 0)[0] == 0  # no pre-observation clairvoyance


def test_announced_world_shift_stales_guarded_habit_but_not_raw_s11():
    world, _, ledger = fixture()
    owner = empty_repertoire()
    for a, b in CONTEXTS:
        p = propose_habit(owner, ledger, a, b)
        owner = commit_experiment_habit(owner, p, grant_test_authority(p), ledger)
    old_view = QualifiedHabitView(owner, world.session, world.revision)
    old_cue = cue_for(0, 0, trial="relevant-stable")
    assert old_view.select(old_cue, world) == ("selected", "action:0")
    world.change_rule(announce=True)
    assert old_view.select(old_cue, world) == ("STALE", None)
    # Existing raw S11 selector has no revision gate: production promotion
    # without a separately scoped source authority would be unsafe.
    assert select_habit(owner, old_cue).selected_candidate_ref == "action:0"
    with pytest.raises(UnqualifiedHabitAcquisition, match="stale"):
        ledger.chosen(0, 0)
    new_ledger = QualifiedLedger(world, observe_training(world))
    new_owner = empty_repertoire(label="b11-r1-explicit-reset")
    for a, b in CONTEXTS:
        p = propose_habit(new_owner, new_ledger, a, b)
        new_owner = commit_experiment_habit(
            new_owner, p, grant_test_authority(p), new_ledger,
        )
    new_view = QualifiedHabitView(new_owner, world.session, world.revision)
    for a, b in CONTEXTS:
        assert new_view.select(cue_for(a, b, trial="rev1"), world) == (
            "selected", f"action:{a ^ b ^ 1}"
        )
    assert world.actions_executed == 16
    assert owner.revision == 4 and new_owner.revision == 4  # distinct owners


def test_preexisting_rule_collision_never_implicitly_overwritten():
    world, _, ledger = fixture()
    conflict = HabitRule(
        "existing-safety",
        (CueFeature("a", 0),),
        "action:1", priority=11,
        provenance=Provenance("b11.retained", "prior"),
    )
    owner = HabitRepertoire(
        "b11-retained-habit", 7, (conflict,),
        provenance=Provenance("b11.retained", "owner"),
    )
    p = propose_habit(owner, ledger, 0, 0)
    with pytest.raises(UnqualifiedHabitAcquisition, match="preexisting Habit"):
        commit_experiment_habit(owner, p, grant_test_authority(p), ledger)
    assert owner.rules == (conflict,)
    assert select_habit(owner, cue_for(0, 0, trial="collision")).selected_candidate_ref == (
        "action:1"
    )


def test_s11_tied_rules_never_imply_action_authority():
    first = HabitRule(
        "tie-A", (CueFeature("a", 0),), "action:0", 8,
        provenance=Provenance("b11-existing", "tie-a"),
    )
    second = HabitRule(
        "tie-B", (CueFeature("b", 0),), "action:1", 8,
        provenance=Provenance("b11-existing", "tie-b"),
    )
    owner = HabitRepertoire(
        "b11-tied-owner", 1, (first, second),
        provenance=Provenance("b11-existing", "tie-owner"),
    )
    choice = select_habit(owner, cue_for(0, 0, trial="tie-test"))
    assert choice.status is HabitSelectionStatus.TIED
    assert choice.selected_candidate_ref is None
    assert not hasattr(choice, "issue_action")
    assert not hasattr(choice, "commit_learning_update")


def test_repertoire_and_derived_index_cannot_be_mutated():
    world, _, ledger = fixture()
    flat = cheap_flat_tags(ledger)
    assert flat[0, 1] == 1
    with pytest.raises(TypeError):
        flat[0, 1] = 0
    owner = empty_repertoire()
    with pytest.raises(FrozenInstanceError):
        owner.revision = 1
    with pytest.raises(TypeError):
        ledger.rows[0, 0] = {}  # type: ignore[index]
    assert world.actions_executed == 8


def test_source_session_and_epoch_and_proposal_splice_fail_closed():
    world, outcomes, ledger = fixture()
    owner = empty_repertoire()
    p = propose_habit(owner, ledger, 1, 1)
    for bad in (
        replace(p, observed_ids=("other:0", "other:1")),
        replace(p, rule=replace(p.rule, candidate_ref="action:1")),
        replace(p, source_session="foreign"),
        replace(p, expected_revision=9),
        replace(p, proposal_id="new-id"),
    ):
        with pytest.raises(UnqualifiedHabitAcquisition, match="mismatch"):
            commit_experiment_habit(
                owner, bad, grant_test_authority(bad), ledger,
            )
    first = outcomes[0]
    alien = replace(first, session="other-world")
    with pytest.raises(UnqualifiedHabitAcquisition, match="did not issue"):
        QualifiedLedger(world, (alien,))


def test_b11_experiment_authority_is_not_authenticated_production_token():
    world, _, ledger = fixture()
    owner = empty_repertoire()
    p = propose_habit(owner, ledger, 0, 0)
    from_dataclass = ExperimentHabitAuthority(
        authority_id="attacker-can-construct-same-format",
        owner_id=p.owner_id, expected_revision=p.expected_revision,
        proposal_id=p.proposal_id, observed_ids=p.observed_ids,
        source_session=p.source_session, source_revision=p.source_revision,
        granted=True, provenance=Provenance("b11-untrusted", "forged"),
    )
    # B11 only models explicit authority *shape*; forging a typed approval
    # is possible if caller controls this Python space. Do not call it secure.
    accepted = commit_experiment_habit(owner, p, from_dataclass, ledger)
    assert len(accepted.rules) == 1
    assert owner.rules == ()
    assert world.actions_executed == 8
