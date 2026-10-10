"""B17 preregistered bounded decision value, correlated source reports and cost."""
from __future__ import annotations

from dataclasses import replace

import pytest

from experiments.ac_b_b11_governed_habit import CurrentWorld, empty_repertoire
from experiments.ac_b_b17_source_value import (
    PLANS,
    B17TestHabitGrant,
    ChannelTrial,
    InvalidB17Evidence,
    MixedSourceLedger,
    RULE,
    commit_native_s10,
    execute_trial,
    expected_s10_feedback,
    expected_s10_state,
    propose_s11_rule,
    retain_experiment_s11,
    run_b17_comparison,
    run_scenario,
    test_grant as issue_test_grant,
)
from relay_self.habit import HabitSelectionStatus, select_habit
from relay_self.learning import (
    FeedbackDirection,
    InvalidLearningAuthority,
    LearningUpdateAuthority,
    MissingLearningAuthority,
    commit_learning_update,
    propose_learning_update,
)
from relay_self.provenance import Provenance
from experiments.ac_b_b11_governed_habit import cue_for


def sources(label="b17-test"):
    return {
        "P": CurrentWorld(session=f"{label}-P"),
        "S": CurrentWorld(session=f"{label}-S"),
    }


def native_grant(ledger, *, granted=True):
    return LearningUpdateAuthority(
        authority_id="b17-unit-test-native-S10-owner",
        target_id=expected_s10_state(ledger).target_id,
        provenance=Provenance("b17.unit-test-grant", ledger.fingerprint),
        granted=granted,
    )


def complete_ledger(
    *, correlated=False, diversified=False, cue=(0, 0), n=4, label="b17-unit",
):
    w = sources(label)
    plan = PLANS["DIVERSIFIED" if diversified else "SINGLE"]
    records = tuple(
        execute_trial(w, cue, index, plan[index], correlated=correlated)
        for index in range(n)
    )
    return w, MixedSourceLedger(w, plan, *cue, records)


def test_all_eight_preset_matched_reports():
    r = run_b17_comparison()
    assert r["terminal"] == "B17_BOUNDED_EXPERIMENT_ONLY_DECISION_VALUE_AND_SOURCE_VARIETY"
    assert r["matched_exogenous_source_schedule"] is True
    assert r["adaptive_S10_S11_and_cheap_count_share_exact_source_actions"] is True
    assert r["fixed_five_uses_separate_matched_source_world_instances"] is True
    assert r["no_production_Habit_owner"]
    assert r["no_autonomous_L2_to_L1"]
    x = r["reports"]
    assert len(x) == 8
    expected = {
        "clean-single-adaptive": (32, 16, 4, 0, 0),
        "clean-single-fixed": (40, 20, 4, 0, 0),
        "clean-diversified-adaptive": (32, 20, 4, 0, 0),
        "clean-diversified-fixed": (40, 28, 4, 0, 0),
        "correlated-single-adaptive": (32, 16, 3, 1, 0),
        "correlated-single-fixed": (40, 20, 3, 1, 0),
        "correlated-diversified-adaptive": (34, 22, 3, 0, 1),
        "correlated-diversified-fixed": (40, 28, 3, 0, 1),
    }
    for name, (actions, cost, correct, wrong, abstained) in expected.items():
        data = x[name]
        assert data["scenario"] == name
        assert data["actual_world_action_executions"] == actions
        assert data["source_pair_cost_units"] == cost
        assert data["correct"] == correct
        assert data["wrong"] == wrong
        assert data["abstained"] == abstained
        assert data["covered"] == 4 - abstained
        assert data["retained_s11_rules"] == data["covered"]
        assert data["actual_native_s10_commits"] == data["covered"]
        assert data["separate_s11_test_grants"] == data["covered"]
        assert data["s10_s11_control_units_extra"] == data["covered"]
        assert data["old_owner_unmodified"] is True
        assert data["habit_matches_cheap_adaptive_or_fixed_count"] is True
        assert data["new_relevant_cues"] is False
        assert data["physical_source_independence_qualified"] is False
        assert data["no_actual_energy_latency_measurements"] is True
        assert data["source_paired_trials"] * 2 == actions
        assert data["source_net_utility_units"] == (
            5 * correct - 5 * wrong - cost
        )
        assert data["s10_s11_net_utility_with_control_units"] == (
            data["source_net_utility_units"] - data["covered"]
        )


def test_costly_diversification_prevents_wrong_but_not_necessarily_net_better():
    x = run_b17_comparison()["reports"]
    one = x["correlated-single-adaptive"]
    diversified = x["correlated-diversified-adaptive"]
    assert (one["correct"], one["wrong"]) == (3, 1)
    assert (diversified["correct"], diversified["wrong"]) == (3, 0)
    assert diversified["abstained"] == 1
    assert diversified["source_net_utility_units"] == -7
    assert one["source_net_utility_units"] == -6
    # The source cost offsets the avoided wrong answer in the fixed
    # prespecified *symbolic* utility function.
    assert diversified["source_net_utility_units"] < one["source_net_utility_units"]
    assert diversified["trials_per_cue"]["00"] == 5
    assert one["trials_per_cue"]["00"] == 4
    assert diversified["votes_per_cue"]["00"] == (1, 1, 1, 0, 0)
    assert one["votes_per_cue"]["00"] == (1, 1, 1, 1)


def test_clean_quorum_decision_known_after_four_not_before():
    w = sources()
    trials = []
    for t in range(5):
        trials.append(execute_trial(w, (0, 0), t, "P", correlated=False))
        ledger = MixedSourceLedger(w, PLANS["SINGLE"], 0, 0, tuple(trials))
        assert ledger.decision() == ((t >= 3), (0 if t >= 3 else None))
    assert sum(w[c].actions_executed for c in ("P", "S")) == 10


def test_correlated_diverse_t4_must_request_fifth_to_exclude_wrong_quorum():
    w = sources()
    trials = []
    for t, channel in enumerate(PLANS["DIVERSIFIED"]):
        trials.append(execute_trial(w, (0, 0), t, channel, correlated=True))
        ledger = MixedSourceLedger(
            w, PLANS["DIVERSIFIED"], 0, 0, tuple(trials)
        )
        if t == 3:
            assert ledger.votes == (1, 1, 1, 0)
            assert ledger.decision() == (False, None)
        if t == 4:
            assert ledger.votes == (1, 1, 1, 0, 0)
            assert ledger.decision() == (True, None)
    assert w["P"].actions_executed == 6
    assert w["S"].actions_executed == 4


def test_two_ambiguous_early_votes_can_make_quorum_impossible():
    w = sources()
    entries = []
    for t in range(2):
        e = execute_trial(w, (0, 0), t, "P", correlated=False)
        # Synthetic local report must be re-registered, not called true.
        wrong_report = replace(e.pair.action1, success=True)
        w["P"]._issued[wrong_report.event_id] = wrong_report
        e = replace(e, pair=replace(e.pair, action1=wrong_report))
        entries.append(e)
        ledger = MixedSourceLedger(w, PLANS["SINGLE"], 0, 0, tuple(entries))
        assert ledger.decision() == ((t == 1), None)
    assert sum(x.actions_executed for x in w.values()) == 4


def test_source_owned_tuple_required_cross_world_clone_replay_wrong_channel():
    w, ledger = complete_ledger()
    rec = ledger.trials
    clone = replace(
        rec[0], pair=replace(
            rec[0].pair, action0=replace(rec[0].pair.action0)
        )
    )
    with pytest.raises(InvalidB17Evidence, match="unissued"):
        MixedSourceLedger(w, PLANS["SINGLE"], 0, 0, (clone,))
    other = sources("other-world")
    with pytest.raises(InvalidB17Evidence, match="trial/channel"):
        MixedSourceLedger(other, PLANS["SINGLE"], 0, 0, rec)
    mismatch = replace(rec[0], channel="S")
    with pytest.raises(InvalidB17Evidence, match="trial/channel"):
        MixedSourceLedger(w, PLANS["SINGLE"], 0, 0, (mismatch,))
    duplicate = replace(rec[1], pair=replace(
        rec[1].pair, action0=rec[0].pair.action0,
    ))
    with pytest.raises(InvalidB17Evidence, match="replayed"):
        MixedSourceLedger(
            w, PLANS["SINGLE"], 0, 0,
            (rec[0], duplicate),
        )
    assert w["P"].actions_executed == 8


def test_missing_action_fails_before_any_s10_or_s11():
    w = sources()
    e = execute_trial(w, (0, 0), 0, "P", correlated=False)
    incomplete = replace(e, pair=replace(
        e.pair, action1=e.pair.action0,
    ))
    with pytest.raises(InvalidB17Evidence, match="unissued"):
        MixedSourceLedger(w, PLANS["SINGLE"], 0, 0, (incomplete,))


def test_source_epoch_change_stales_ledger_native_s10_and_selection():
    w, ledger = complete_ledger()
    assert ledger.decision() == (True, 0)
    state = expected_s10_state(ledger)
    commit = commit_native_s10(ledger, native_grant(ledger))
    owner = empty_repertoire()
    draft = propose_s11_rule(ledger, owner, commit)
    new_owner = retain_experiment_s11(
        ledger, owner, commit, draft, issue_test_grant(draft),
    )
    assert select_habit(
        new_owner, cue_for(0, 0, trial="before-change")
    ).status is HabitSelectionStatus.SELECTED
    w["P"].change_rule(announce=True)
    with pytest.raises(InvalidB17Evidence, match="stale"):
        ledger.decision()
    with pytest.raises(InvalidB17Evidence, match="stale"):
        commit_native_s10(ledger, native_grant_stale(state.target_id))


def native_grant_stale(target):
    return LearningUpdateAuthority(
        "b17-irrelevant-authority", target,
        Provenance("b17.test", "stale"),
    )


def test_separate_real_s10_and_experiment_s11_owner_gates():
    w, ledger = complete_ledger()
    assert sum(x.actions_executed for x in w.values()) == 8
    with pytest.raises(MissingLearningAuthority):
        commit_native_s10(ledger, None)
    with pytest.raises(InvalidLearningAuthority):
        commit_native_s10(ledger, native_grant(ledger, granted=False))
    owner = empty_repertoire()
    with pytest.raises(InvalidB17Evidence, match="actual S10"):
        propose_s11_rule(ledger, owner, None)
    c = commit_native_s10(ledger, native_grant(ledger))
    draft = propose_s11_rule(ledger, owner, c)
    for token in (
        None,
        native_grant(ledger),
        replace(issue_test_grant(draft), granted=False),
        replace(issue_test_grant(draft), repertoire_id="foreign"),
        replace(issue_test_grant(draft), expected_revision=2),
        replace(issue_test_grant(draft), source_fingerprint="tampered"),
        replace(issue_test_grant(draft), winner=1),
    ):
        with pytest.raises(InvalidB17Evidence, match="separate exact"):
            retain_experiment_s11(ledger, owner, c, draft, token)
    assert owner.rules == ()
    updated = retain_experiment_s11(
        ledger, owner, c, draft, issue_test_grant(draft),
    )
    assert updated.revision == 1 and owner.revision == 0
    with pytest.raises(InvalidB17Evidence, match="proposal mismatch"):
        retain_experiment_s11(
            ledger, updated, c, draft, issue_test_grant(draft),
        )


def test_wrong_native_s10_feedback_direction_does_not_create_s11():
    _, ledger = complete_ledger()
    state = expected_s10_state(ledger)
    correct_feedback = expected_s10_feedback(ledger)
    assert correct_feedback.direction is FeedbackDirection.DECREASE
    for wrong in (FeedbackDirection.HOLD, FeedbackDirection.INCREASE):
        changed = replace(correct_feedback, direction=wrong)
        p = propose_learning_update(state, changed, RULE)
        wrong_commit = commit_learning_update(
            state, p, native_grant(ledger),
            provenance=Provenance("b17.wrong", "native-owner"),
        )
        with pytest.raises(InvalidB17Evidence, match="mismatch"):
            propose_s11_rule(ledger, empty_repertoire(), wrong_commit)


def test_same_process_experiment_grant_is_forgeable_success_witness():
    _, ledger = complete_ledger()
    owner = empty_repertoire()
    c = commit_native_s10(ledger, native_grant(ledger))
    draft = propose_s11_rule(ledger, owner, c)
    # Plain dataclass, arbitrary caller can independently construct the
    # matching TEST approval. Production S11 authority is NOT qualified.
    forged = B17TestHabitGrant(
        draft.repertoire_id, draft.expected_revision,
        draft.source_fingerprint, draft.cue, draft.winner, True,
    )
    assert retain_experiment_s11(ledger, owner, c, draft, forged).revision == 1
