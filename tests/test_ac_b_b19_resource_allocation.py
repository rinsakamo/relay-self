"""B19: preregistered mock-body allocation, true source actions and cheap Q null."""
from __future__ import annotations

from dataclasses import replace
from fractions import Fraction

import pytest

from experiments.ac_b_b11_governed_habit import CONTEXTS, empty_repertoire
from experiments.ac_b_b17_source_value import execute_trial
from experiments.ac_b_b18_empirical_voi import (
    grant_experiment_only,
    learn_empirical_table,
    retain_test_policy,
    sources_for,
    train_actual_s10_feedback,
    training_case,
)
from experiments.ac_b_b19_resource_allocation import (
    ARMS,
    PROFILES,
    InvalidB19Allocation,
    Resource,
    candidate_expected_net_Q,
    choose,
    qualify_reported_pair,
    recompute_same_public_Q,
    run_b19_comparison,
    score_arm,
)
from relay_self.learning import (
    InvalidLearningAuthority,
    LearningFeedback,
    LearningPreferenceState,
    LearningUpdateAuthority,
    LearningUpdateRule,
    commit_learning_update,
    propose_learning_update,
)
from relay_self.provenance import Provenance


def prepare():
    cases = tuple(
        training_case(cue=cue, correlated=correlated)
        for correlated in (False, True) for cue in CONTEXTS
    )
    receipt = train_actual_s10_feedback(cases)
    high = learn_empirical_table(receipt, risk="HIGH")
    low = learn_empirical_table(receipt, risk="LOW")
    owners = {}
    for name, table in (("HIGH", high), ("LOW", low)):
        owner = empty_repertoire(label=f"b19-test-{name}")
        for vote in (0, 1):
            owner = retain_test_policy(
                owner, receipt, table, vote,
                grant_experiment_only(owner, table, vote),
            )
        owners[name] = owner
    return receipt, high, low, owners


def test_prespecified_24_runs_all_source_actions_and_native_owner_null():
    r = run_b19_comparison()
    assert r["classification"] == (
        "B19_BOUNDED_RESOURCE_ALLOCATION_SAME_INFORMATION_NULL"
    )
    assert r["actual_offline_training_world_actions"] == 64
    assert r["existing_native_s10_history_commits"] == 8
    assert r["existing_test_only_s11_rules_per_risk"] == 2
    for key in (
        "physical_L2_inference", "physical_source_independence",
        "physical_body_or_energy_measurement",
        "native_s10_calculates_Q", "native_s11_production_retention",
    ):
        assert r[key] is False
    rows = {
        (x["risk"], x["profile"], x["arm"]): x
        for x in r["heldout_runs"]
    }
    assert len(rows) == 2 * 3 * 4 == 24
    for risk in ("HIGH", "LOW"):
        for profile in PROFILES:
            for arm in ARMS:
                result = rows[risk, profile, arm]
                assert len(result["cases"]) == 8
                assert result["actual_s11_equals_cheap_Q_all_cases"] is True
                assert result["deadline_violations"] == 0
                assert sum(c["source_actions"] for c in result["cases"]) == (
                    result["actual_world_actions"]
                )
                assert sum(c["source_query"] for c in result["cases"]) == (
                    result["secondary_queries"]
                )
                assert result["actual_world_actions"] == (
                    32 + 2 * result["secondary_queries"]
                )
                assert result["source_pairs_cost"] == (
                    16 + 2 * result["secondary_queries"]
                )
                assert sum(
                    (result[k] for k in ("correct", "wrong", "abstained"))
                ) == 8
                assert result["net_symbolic_utility"] == str(
                    _scored_result(result)
                )
    assert rows["HIGH", "OPEN", "L1_STOP"]["net_symbolic_utility"] == "-2"
    assert rows["HIGH", "OPEN", "B18_CHEAP_Q"]["net_symbolic_utility"] == "-3"
    assert rows["HIGH", "OPEN", "ALWAYS_THINK"]["net_symbolic_utility"] == "-25"
    assert rows["HIGH", "OPEN", "VALUE_GATE"]["net_symbolic_utility"] == "-6"
    assert rows["LOW", "OPEN", "L1_STOP"]["net_symbolic_utility"] == "8"
    assert rows["LOW", "OPEN", "B18_CHEAP_Q"]["net_symbolic_utility"] == "8"
    assert rows["LOW", "OPEN", "ALWAYS_THINK"]["net_symbolic_utility"] == "-14"
    assert rows["LOW", "OPEN", "VALUE_GATE"]["net_symbolic_utility"] == "4"
    for restricted in ("TIGHT", "HUNGRY"):
        for risk in ("HIGH", "LOW"):
            for arm in ARMS:
                x = rows[risk, restricted, arm]
                assert x["actual_world_actions"] == 32
                assert x["secondary_queries"] == 0
                assert x["correct"] == 7 and x["wrong"] == 1
                assert x["abstained"] == 0
                assert x["decision_tick_units"] == 8
                assert x["decision_work_units"] == 8
                assert x["net_symbolic_utility"] == (
                    "-6" if arm == "VALUE_GATE" and risk == "HIGH"
                    else "4" if arm == "VALUE_GATE"
                    else "-2" if risk == "HIGH"
                    else "8"
                )


def _scored_result(r):
    reward = (
        5 * r["correct"]
        + (-15 if r["risk"] == "HIGH" else -5) * r["wrong"]
        - r["abstained"]
    )
    return (
        Fraction(reward - r["source_pairs_cost"])
        - Fraction(r["decision_work_units"] + r["selector_work_units"], 2)
        - Fraction(r["decision_tick_units"], 4)
    )


def test_high_open_same_world_cues_paid_secondary_and_think_vs_cheap():
    r = run_b19_comparison()["heldout_runs"]
    x = {
        (v["risk"], v["profile"], v["arm"]): v for v in r
    }
    cheap = x["HIGH", "OPEN", "B18_CHEAP_Q"]
    think = x["HIGH", "OPEN", "ALWAYS_THINK"]
    stopped = x["HIGH", "OPEN", "L1_STOP"]
    gate = x["HIGH", "OPEN", "VALUE_GATE"]
    assert (cheap["correct"], cheap["wrong"], cheap["abstained"]) == (7, 0, 1)
    assert (stopped["correct"], stopped["wrong"], stopped["abstained"]) == (
        7, 1, 0,
    )
    assert (gate["correct"], gate["wrong"], gate["abstained"]) == (7, 1, 0)
    assert cheap["secondary_queries"] == think["secondary_queries"] == 5
    assert stopped["secondary_queries"] == gate["secondary_queries"] == 0
    assert cheap["actual_world_actions"] == think["actual_world_actions"] == 42
    assert think["decision_work_units"] == cheap["decision_work_units"] + 32
    assert think["decision_tick_units"] == cheap["decision_tick_units"] + 24
    assert gate["selector_work_units"] == 8
    assert cheap["selector_work_units"] == 0
    assert gate["decision_work_units"] == stopped["decision_work_units"]


def test_feasibility_without_hidden_world_truth():
    assert PROFILES == {
        "OPEN": (6, 6, 7),
        "TIGHT": (6, 6, 1),
        "HUNGRY": (3, 1, 7),
    }
    high = prepare()[1]
    open_res = Resource(*PROFILES["OPEN"])
    tight = Resource(*PROFILES["TIGHT"])
    hungry = Resource(*PROFILES["HUNGRY"])
    assert open_res.stop_allowed() and open_res.query_allowed()
    assert open_res.think_allowed() and open_res.think_query_allowed()
    for limited in (tight, hungry):
        assert limited.stop_allowed()
        assert not limited.query_allowed()
        assert not limited.think_allowed()
        assert not limited.think_query_allowed()
        assert choose(high, 1, limited, "B18_CHEAP_Q").chosen_candidate == "STOP"
        assert choose(high, 1, limited, "ALWAYS_THINK").mode == "STOP"
    assert choose(high, 1, open_res, "B18_CHEAP_Q").chosen_candidate == "QUERY_S"
    assert choose(high, 1, open_res, "ALWAYS_THINK").mode == "THINK_QUERY_S"
    assert choose(high, 1, open_res, "VALUE_GATE").mode == "STOP"
    assert candidate_expected_net_Q(high, 1, "STOP", open_res) == Fraction(1, 4)
    assert candidate_expected_net_Q(high, 1, "QUERY_S", open_res) == Fraction(1, 20)
    assert candidate_expected_net_Q(high, 1, "THINK_STOP", open_res) < Fraction(1, 4)
    assert candidate_expected_net_Q(
        high, 1, "THINK_QUERY_S", open_res,
    ) < Fraction(1, 20)
    assert candidate_expected_net_Q(high, 1, "QUERY_S", hungry) is None
    assert candidate_expected_net_Q(high, 1, "THINK_STOP", tight) is None


def test_native_s11_and_cheap_Q_same_public_vote_allocation_unchanged():
    _, high, low, owners = prepare()
    assert high.choices == ("STOP", "QUERY_S")
    assert low.choices == ("STOP", "STOP")
    for risk, table in (("HIGH", high), ("LOW", low)):
        x = score_arm(table, owners[risk], "OPEN", "B18_CHEAP_Q")
        assert x["actual_s11_equals_cheap_Q_all_cases"]
        assert all(case["native_s11_choice"] == case["cheap_q_choice"]
                   for case in x["cases"])
    assert recompute_same_public_Q(high, 1) == "QUERY_S"
    assert recompute_same_public_Q(high, 0) == "STOP"
    assert recompute_same_public_Q(low, 1) == "STOP"


def test_no_actual_L2_deliberation_or_extra_evidence_from_think():
    _, high, _, owners = prepare()
    cheap = score_arm(high, owners["HIGH"], "OPEN", "B18_CHEAP_Q")
    think = score_arm(high, owners["HIGH"], "OPEN", "ALWAYS_THINK")
    assert tuple((x["vote"], x["chosen"]) for x in cheap["cases"]) == tuple(
        (x["vote"], x["chosen"]) for x in think["cases"]
    )
    assert think["secondary_queries"] == cheap["secondary_queries"]
    assert think["actual_world_actions"] == cheap["actual_world_actions"]
    assert think["decision_work_units"] > cheap["decision_work_units"]
    assert think["decision_tick_units"] > cheap["decision_tick_units"]


def test_same_source_registry_rejects_cloned_and_cross_channel_receipts():
    world = sources_for("b19-clone-negative")
    cue = (0, 0)
    p = execute_trial(world, cue, 0, "P", correlated=False)
    assert qualify_reported_pair(p, world, cue, "P", 0) == 0
    corrupted = replace(
        p, pair=replace(
            p.pair, action0=replace(p.pair.action0)
        )
    )
    with pytest.raises(InvalidB19Allocation, match="unissued"):
        qualify_reported_pair(corrupted, world, cue, "P", 0)
    with pytest.raises(InvalidB19Allocation, match="source channel"):
        qualify_reported_pair(p, world, cue, "S", 0)
    with pytest.raises(InvalidB19Allocation, match="source channel"):
        qualify_reported_pair(p, world, cue, "P", 1)
    with pytest.raises(InvalidB19Allocation, match="unissued"):
        qualify_reported_pair(p, world, (0, 1), "P", 0)
    world["P"].change_rule(announce=True)
    with pytest.raises(InvalidB19Allocation, match="unissued"):
        qualify_reported_pair(p, world, cue, "P", 0)


def test_missing_second_action_or_early_sourceS_report_is_not_admissible():
    world = sources_for("b19-premature")
    p = execute_trial(world, (1, 1), 0, "P", correlated=False)
    partial = replace(p, pair=replace(p.pair, action1=p.pair.action0))
    with pytest.raises(InvalidB19Allocation, match="unissued"):
        qualify_reported_pair(partial, world, (1, 1), "P", 0)
    assert world["S"].actions_executed == 0
    assert world["S"]._issued == {}
    assert source_action(1, "QUERY_S", None) is None


def test_resource_type_unknown_vote_and_unsupported_allocation_fail_closed():
    with pytest.raises(InvalidB19Allocation, match="nonnegative"):
        Resource(-1, 2, 3)
    with pytest.raises(InvalidB19Allocation, match="nonnegative"):
        Resource(True, 2, 3)
    _, high, _, _ = prepare()
    with pytest.raises(InvalidB19Allocation, match="frozen arm"):
        choose(high, 1, Resource(6, 6, 7), "EVALUATOR_ORACLE")
    with pytest.raises(InvalidB19Allocation, match="frozen arm"):
        choose(high, 2, Resource(6, 6, 7), "B18_CHEAP_Q")
    with pytest.raises(InvalidB19Allocation, match="public vote"):
        recompute_same_public_Q(high, 2)
    assert choose(high, 0, Resource(2, 5, 7), "VALUE_GATE") is None


def test_frozen_native_s10_requires_separate_learning_authority():
    # Reusing actual S10 owner contract: an arbitrary or denied grant cannot
    # masquerade as independently approved World-learning feedback.
    state = LearningPreferenceState(
        target_id="b19-test-s10", value=1, minimum=0, maximum=2,
        revision=0,
        origin_provenance=Provenance("b19-test", "historical"),
    )
    feedback = LearningFeedback(
        feedback_id="b19-feedback-1", target_id=state.target_id,
        direction="increase",
        provenance=Provenance("b19-test", "source"),
        consequence_ref="test-only-not-physical",
    )
    from relay_self.learning import FeedbackDirection

    feedback = replace(feedback, direction=FeedbackDirection.INCREASE)
    rule = LearningUpdateRule("b19-step", version=1, step=1)
    proposal = propose_learning_update(state, feedback, rule)
    with pytest.raises(InvalidLearningAuthority):
        commit_learning_update(
            state, proposal,
            LearningUpdateAuthority(
                authority_id="b19-denied",
                target_id=state.target_id, granted=False,
                provenance=Provenance("b19-test", "denied"),
            ),
            provenance=Provenance("b19-test", "native-denied"),
        )


def test_b18_experiment_only_s11_grant_forgeable_not_production_authority():
    from experiments.ac_b_b18_empirical_voi import B18TestGrant
    receipt, high, _, _ = prepare()
    owner = empty_repertoire()
    legit = grant_experiment_only(owner, high, 0)
    fabricated = B18TestGrant(
        owner_id=legit.owner_id, owner_revision=legit.owner_revision,
        trace_digest=legit.trace_digest, vote=legit.vote,
        option=legit.option, granted=legit.granted,
    )
    assert fabricated == legit and fabricated is not legit
    assert retain_test_policy(owner, receipt, high, 0, fabricated).revision == 1
