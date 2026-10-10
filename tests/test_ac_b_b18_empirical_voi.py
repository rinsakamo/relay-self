"""B18: genuinely issued offline trace cost/utility, native S10 and cheapest Q null."""
from __future__ import annotations

from dataclasses import replace
from fractions import Fraction

import pytest

from experiments.ac_b_b11_governed_habit import CONTEXTS, empty_repertoire
from experiments.ac_b_b18_empirical_voi import (
    OPTIONS,
    RISKS,
    B18TestGrant,
    InvalidB18Source,
    grant_experiment_only,
    heldout_episode,
    learn_empirical_table,
    retain_test_policy,
    run_b18_comparison,
    selected_s11_option,
    source_action,
    train_actual_s10_feedback,
    training_case,
)
from relay_self.habit import HabitRepertoire


def all_training_cases():
    return tuple(
        training_case(cue=cue, correlated=correlated)
        for correlated in (False, True) for cue in CONTEXTS
    )


def prepare():
    cases = all_training_cases()
    receipt = train_actual_s10_feedback(cases)
    receipt.verify()
    return cases, receipt


def test_pre_registered_full_actual_traces_native_s10_and_risk_tradeoff():
    report = run_b18_comparison()
    assert report["classification"] == "B18_BOUNDED_EMPIRICAL_VOI_WITH_CHEAP_Q_NULL"
    assert report["training_actual_sim_world_actions"] == 64
    assert report["actual_native_s10_training_commits"] == 8
    assert report["s10_final_scalar_values"] == (3, 3)
    assert report["s10_final_scalar_revisions"] == (3, 5)
    assert report["real_physical_source"] is False
    assert report["production_s11_authority"] is False
    assert report["l2_to_l1_autonomous"] is False
    assert report["actual_energy_cpu_latency_measured"] is False
    high, low = report["risk_runs"]
    assert [v["risk"] for v in (high, low)] == ["HIGH", "LOW"]
    assert high["learned_options"] == ("STOP", "QUERY_S")
    assert low["learned_options"] == ("STOP", "STOP")
    assert high["actual_world_actions_shared_Habit_and_cheap_Q"] == 42
    assert low["actual_world_actions_shared_Habit_and_cheap_Q"] == 32
    assert high["query_secondary_count"] == 5
    assert low["query_secondary_count"] == 0
    assert high["query_primary_count"] == low["query_primary_count"] == 0
    assert (high["correct"], high["wrong"], high["abstained"]) == (7, 0, 1)
    assert (low["correct"], low["wrong"], low["abstained"]) == (7, 1, 0)
    assert high["trained_policy_net_utility"] == 8
    assert low["trained_policy_net_utility"] == 14
    assert high["fixed_stop_counterfactual_net_utility"] == 4
    assert low["fixed_stop_counterfactual_net_utility"] == 14
    assert high["fixed_stop_counterfactual_actions"] == 32
    assert low["fixed_stop_counterfactual_actions"] == 32
    assert high["cheap_empirical_Q_net_utility"] == 8
    assert low["cheap_empirical_Q_net_utility"] == 14
    for v in (high, low):
        assert v["trained_votes"] == (0, 1)
        assert v["retained_s11_revision"] == 2
        assert v["retained_s11_rules"] == 2
        assert v["old_s11_owner_unmodified"] is True
        assert v["no_new_relevant_cues"] is True
        assert len(v["cases"]) == 8
        assert all(c["world_actions"] in (4, 6) for c in v["cases"])


def test_exact_empirical_means_not_hardcoded_high_low_policy():
    _, receipt = prepare()
    high = learn_empirical_table(receipt, risk="HIGH")
    low = learn_empirical_table(receipt, risk="LOW")
    assert high.trace_digest == low.trace_digest == receipt.trace_digest
    assert high.choices == ("STOP", "QUERY_S")
    assert low.choices == ("STOP", "STOP")
    hv0, hv1 = map(dict, high.mean_scores)
    lv0, lv1 = map(dict, low.mean_scores)
    assert hv0 == lv0 == {
        "STOP": Fraction(5),
        "ABSTAIN": Fraction(-1),
        "QUERY_P": Fraction(4),
        "QUERY_S": Fraction(3),
    }
    assert hv1 == {
        "STOP": Fraction(1),
        "ABSTAIN": Fraction(-1),
        "QUERY_P": Fraction(0),
        "QUERY_S": Fraction(9, 5),
    }
    assert lv1 == {
        "STOP": Fraction(3),
        "ABSTAIN": Fraction(-1),
        "QUERY_P": Fraction(2),
        "QUERY_S": Fraction(9, 5),
    }
    assert RISKS == {"HIGH": -15, "LOW": -5}
    assert OPTIONS == ("STOP", "ABSTAIN", "QUERY_P", "QUERY_S")


def test_eight_training_cases_have_original_four_world_actions_per_source():
    cases = all_training_cases()
    assert len(cases) == 8
    assert all(
        c.sources["P"].actions_executed == 6
        and c.sources["S"].actions_executed == 2
        for c in cases
    )
    assert len(set(c.digest for c in cases)) == 8
    assert [c.prefix_vote for c in cases].count(0) == 3
    assert [c.prefix_vote for c in cases].count(1) == 5
    # The training source identity is only in-process; not signed Mineflayer.
    assert all(c.sources["P"] is not c.sources["S"] for c in cases)


def test_correlated_source_paired_votes_and_secondary_disagreement():
    clean = training_case(cue=(0, 0), correlated=False)
    corrupt = training_case(cue=(0, 0), correlated=True)
    assert clean.prefix_vote == 0
    assert corrupt.prefix_vote == 1
    assert corrupt.first.pair.vote() == corrupt.second.pair.vote() == 1
    assert corrupt.optional_primary.pair.vote() == 1
    assert corrupt.optional_secondary.pair.vote() == 0
    assert source_action(1, "STOP") == 1
    assert source_action(1, "QUERY_S", third=0) is None
    assert source_action(1, "QUERY_P", third=1) == 1
    assert source_action(1, "ABSTAIN") is None
    assert source_action(None, "QUERY_S", third=1) is None


def test_incomplete_or_ambiguous_new_source_abstains():
    assert source_action(0, "QUERY_P", third=None) is None
    assert source_action(1, "QUERY_S", third=None) is None
    assert source_action(1, "QUERY_S", third=0) is None
    assert source_action(0, "QUERY_S", third=0) == 0
    with pytest.raises(InvalidB18Source, match="unknown"):
        source_action(0, "NOT_AN_ACTION")
    with pytest.raises(InvalidB18Source, match="HIGH/LOW"):
        learn_empirical_table(prepare()[1], risk="unfrozen")


def test_training_source_object_clone_and_cross_channel_fail_closed():
    case = training_case(cue=(0, 0), correlated=False)
    foreign = replace(case.first.pair.action0)
    cloned = replace(case, first=replace(
        case.first,
        pair=replace(case.first.pair, action0=foreign),
    ))
    with pytest.raises(InvalidB18Source, match="unissued"):
        cloned.verify()
    swapped = replace(case, optional_secondary=case.optional_primary)
    with pytest.raises(InvalidB18Source, match="wrong source channel"):
        swapped.verify()
    reused = replace(case, second=case.first)
    with pytest.raises(InvalidB18Source, match="wrong source channel"):
        reused.verify()


def test_replayed_receipt_rejected_even_same_owner_and_session():
    c = training_case(cue=(0, 0), correlated=False)
    p1 = c.second.pair
    old = c.first.pair
    altered = replace(c, second=replace(
        c.second, pair=replace(
            p1, action0=old.action0,
        ),
    ))
    with pytest.raises(InvalidB18Source, match="duplicate"):
        altered.verify()


def test_world_revision_stales_training_source_before_model_derivation():
    case = training_case(cue=(0, 0), correlated=False)
    case.sources["P"].change_rule(announce=True)
    with pytest.raises(InvalidB18Source, match="stale"):
        case.verify()


def test_owner_retention_requires_specific_training_table_and_extra_test_grant():
    _, receipt = prepare()
    table = learn_empirical_table(receipt, risk="HIGH")
    owner = empty_repertoire(label="b18-test-original")
    original = owner
    for not_valid in (
        None,
        {"granted": True, "target": owner.repertoire_id},
        replace(grant_experiment_only(owner, table, 0), granted=False),
        replace(grant_experiment_only(owner, table, 0), owner_id="other"),
        replace(grant_experiment_only(owner, table, 0), owner_revision=90),
        replace(grant_experiment_only(owner, table, 0), trace_digest="fake"),
        replace(grant_experiment_only(owner, table, 0), vote=1),
        replace(grant_experiment_only(owner, table, 0), option="QUERY_P"),
    ):
        with pytest.raises(InvalidB18Source, match="experimental Habit grant"):
            retain_test_policy(owner, receipt, table, 0, not_valid)
    updated = retain_test_policy(
        owner, receipt, table, 0,
        grant_experiment_only(owner, table, 0),
    )
    assert isinstance(updated, HabitRepertoire)
    assert updated.revision == 1 and len(updated.rules) == 1
    assert original.rules == () and original.revision == 0
    assert selected_s11_option(updated, 0, trial="new-nuisance") == "STOP"
    with pytest.raises(InvalidB18Source, match="experimental Habit grant"):
        retain_test_policy(
            updated, receipt, table, 0,
            grant_experiment_only(owner, table, 0),
        )


def test_native_s10_output_not_assumed_to_learn_exact_Q():
    _, receipt = prepare()
    high = learn_empirical_table(receipt, risk="HIGH")
    low = learn_empirical_table(receipt, risk="LOW")
    # Same exact native S10 training commits/scalars, DIFFERENT action
    # preferences because the external risk penalty changes the Q table.
    assert receipt.native_s10_final_values == (3, 3)
    assert high.choices != low.choices
    assert receipt.native_s10_final_revisions == (3, 5)


def test_plain_b18_test_grant_is_same_process_forgeable():
    _, receipt = prepare()
    table = learn_empirical_table(receipt, risk="LOW")
    owner = empty_repertoire()
    authentic = grant_experiment_only(owner, table, 0)
    fabricated = B18TestGrant(
        authentic.owner_id, authentic.owner_revision,
        authentic.trace_digest, authentic.vote, authentic.option, True,
    )
    assert fabricated == authentic and fabricated is not authentic
    updated = retain_test_policy(owner, receipt, table, 0, fabricated)
    assert updated.revision == 1  # deliberately EXPOSE nonproduction authority


def test_training_receipt_not_unforgeable_native_s10_owner_proof():
    _, receipt = prepare()
    # B18 receipt is typed in-process test evidence. Same data can be cloned.
    copied = replace(receipt)
    assert copied is not receipt and copied == receipt
    assert learn_empirical_table(copied, risk="HIGH").choices == (
        "STOP", "QUERY_S"
    )


def test_heldout_native_s11_and_cheap_table_same_source_budget():
    _, receipt = prepare()
    high = learn_empirical_table(receipt, risk="HIGH")
    owner = empty_repertoire()
    for vote in (0, 1):
        owner = retain_test_policy(
            owner, receipt, high, vote,
            grant_experiment_only(owner, high, vote),
        )
    result = heldout_episode(high, owner)
    assert result["actual_world_actions_shared_Habit_and_cheap_Q"] == 42
    assert result["cheap_empirical_Q_net_utility"] == 8
    assert result["correct"] == 7 and result["abstained"] == 1
    assert result["query_secondary_count"] == 5
