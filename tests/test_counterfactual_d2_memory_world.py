"""Non-generative regression for #424 source-bound D2 episode World."""

from __future__ import annotations

from copy import deepcopy
from dataclasses import FrozenInstanceError
from fractions import Fraction
from itertools import permutations

import pytest

from experiments import counterfactual_d2_memory_world as d2


def test_exact_manifest_sha_and_defensive_copy():
    assert d2.MANIFEST_SHA256 == (
        "fddf90f049dc11d3737bde30ac3a2b50ec14cbe164dfe1e5bd2ac4207f726976"
    )
    assert d2.manifest_sha256() == d2.MANIFEST_SHA256
    f = d2.manifest()
    f["subject_count"] = 7
    with pytest.raises(d2.D2ContractError, match="drift"):
        d2.check_manifest(f)
    assert d2.manifest()["subject_count"] == 6
    d2.check_manifest()


def test_six_heldout_subjects_and_18_reset_interventions():
    assert d2.TEST_CUES == ((0, 1), (1, 0), (1, 1))
    assert (0, 0) not in d2.TEST_CUES
    assert d2.ACTIONS == ("DIRECT", "DETOUR", "INSPECT")
    subjects, actions = 0, 0
    all_orders = tuple(permutations(d2.ACTIONS))
    assert len(all_orders) == 6
    for theta in (0, 1):
        src = d2.session(theta)
        original = deepcopy(src)
        for cues in d2.TEST_CUES:
            subjects += 1
            baseline = d2.all_counterfactuals(src, cues)
            assert set(baseline) == set(d2.ACTIONS)
            assert src == original
            for order in all_orders:
                assert d2.all_counterfactuals(src, cues, order) == baseline
            for action, consequence in baseline.items():
                assert consequence == d2.intervene(src, cues, action)
                assert consequence.utility == (
                    20 - consequence.elapsed_ticks - consequence.health_loss
                )
                assert consequence.action == action
                actions += 1
    assert (subjects, actions) == (6, 18)


def test_source_grounded_episode_is_independently_bound():
    e0 = d2.grounded_episode(d2.session(0))
    e1 = d2.grounded_episode(d2.session(1))
    assert e0.health_loss == 0
    assert e1.health_loss == 12
    assert e0.action == e1.action == "DIRECT"
    assert e0.u == e0.v == e1.u == e1.v == 0
    assert e0.session_id != e1.session_id

    for theta in (0, 1):
        src = d2.session(theta)
        other = d2.grounded_episode(d2.session(1 - theta))
        with pytest.raises(d2.D2ContractError):
            d2.predictor_evidence(src, (0, 1), include_memory=True, episode=other)
        forged = d2.GroundedEpisode(
            session_id=src.session_id, u=0, v=0,
            action="DIRECT", health_loss=12 * (1 - theta),
        )
        with pytest.raises(d2.D2ContractError):
            d2.predictor_evidence(src, (0, 1), include_memory=True, episode=forged)


def test_same_present_only_history_changes_model_facing_evidence():
    for cues in d2.TEST_CUES:
        left, right = d2.session(0), d2.session(1)
        no_l = d2.predictor_evidence(left, cues, include_memory=False)
        no_r = d2.predictor_evidence(right, cues, include_memory=False)
        assert no_l == no_r
        yes_l = d2.predictor_evidence(
            left, cues, include_memory=True, episode=d2.grounded_episode(left),
        )
        yes_r = d2.predictor_evidence(
            right, cues, include_memory=True, episode=d2.grounded_episode(right),
        )
        assert yes_l["cues"] == yes_r["cues"] == no_l["cues"]
        assert {k: v for k, v in yes_l.items() if k != "priorEpisode"} == {
            k: v for k, v in no_l.items() if k != "priorEpisode"
        }
        assert yes_l["priorEpisode"] != yes_r["priorEpisode"]
        for view in (no_l, no_r, yes_l, yes_r):
            assert "theta" not in view
            assert "session_id" not in view
            assert "currentHazard" not in view
            assert "futureOutcome" not in view
            assert "oracleChoice" not in view
            assert "trainingRef" not in view


@pytest.mark.parametrize("field", [
    "theta", "currentHazard", "session_id", "futureOutcome",
    "oracleAction", "WorldTruth", "seed", "mapping", "treatmentArm",
    "executionIndex", "valueGradient", "hazardSourceId",
])
def test_hidden_world_or_experiment_metadata_injection_rejected(field):
    src = d2.session(1)
    cues = (0, 1)
    p = d2.predictor_evidence(
        src, cues, include_memory=True, episode=d2.grounded_episode(src),
    )
    p[field] = "leak"
    with pytest.raises(d2.D2ContractError, match="mismatch"):
        d2.validate_source_bound_evidence(src, cues, p, include_memory=True)


def test_type_exact_source_schema_and_nested_forgery_rejected():
    src = d2.session(1)
    cues = (0, 1)
    valid = d2.predictor_evidence(
        src, cues, include_memory=True, episode=d2.grounded_episode(src),
    )
    illegal_variants = []
    swapped_cues = deepcopy(valid)
    swapped_cues["cues"]["u"] = True  # Python True == 1; JSON identity must differ.
    illegal_variants.append(swapped_cues)
    forged_hist = deepcopy(valid)
    forged_hist["priorEpisode"]["observedHealthLoss"] = 0
    illegal_variants.append(forged_hist)
    changed_rule = deepcopy(valid)
    changed_rule["hypothesisFamily"] = "unknown mechanism"
    illegal_variants.append(changed_rule)
    added_gold = deepcopy(valid)
    added_gold["priorEpisode"]["theta"] = 1
    illegal_variants.append(added_gold)
    extra = deepcopy(valid)
    extra["objective"]["secret"] = "oracle"
    illegal_variants.append(extra)
    for payload in illegal_variants:
        with pytest.raises(d2.D2ContractError):
            d2.validate_source_bound_evidence(
                src, cues, payload, include_memory=True,
            )


@pytest.mark.parametrize("theta", [0, 1])
def test_memory_is_required_and_cannot_be_silently_added(theta):
    src = d2.session(theta)
    episode = d2.grounded_episode(src)
    with pytest.raises(d2.D2ContractError):
        d2.predictor_evidence(src, (0, 1), include_memory=True)
    with pytest.raises(d2.D2ContractError):
        d2.predictor_evidence(src, (0, 1), include_memory=False, episode=episode)
    prior = d2.predictor_evidence(src, (0, 1), include_memory=False)
    with pytest.raises(d2.D2ContractError):
        d2.validate_source_bound_evidence(
            src, (0, 1), prior, include_memory=True,
        )


def test_source_memory_makes_hazard_forecast_exact_and_choice_reverse():
    total_expected_benefit = Fraction()
    gain_rows = 0
    memory_utilities, blind_utilities = [], []
    no_memory_brier, memory_brier = [], []
    for cues in d2.TEST_CUES:
        decisions = []
        for theta in (0, 1):
            src = d2.session(theta)
            memory = d2.predictor_evidence(
                src, cues, include_memory=True,
                episode=d2.grounded_episode(src),
            )
            blind = d2.predictor_evidence(src, cues, include_memory=False)
            pm = d2.infer_hazard_probability(
                memory, source=src, cues=cues, include_memory=True,
            )
            p0 = d2.infer_hazard_probability(
                blind, source=src, cues=cues, include_memory=False,
            )
            true_hazard = cues[0] ^ cues[1] ^ theta
            assert pm == Fraction(true_hazard)
            assert p0 == Fraction(1, 2)
            memory_brier.append(d2.brier_score(pm, true_hazard))
            no_memory_brier.append(d2.brier_score(p0, true_hazard))
            chosen = d2.cheap_choice(
                memory, source=src, cues=cues, include_memory=True,
            )
            blind_chosen = d2.cheap_choice(
                blind, source=src, cues=cues, include_memory=False,
            )
            assert blind_chosen == "INSPECT"
            assert chosen == ("DIRECT" if true_hazard == 0 else "DETOUR")
            decisions.append(chosen)
            oracle = d2.all_counterfactuals(src, cues)
            memory_utility = oracle[chosen].utility
            blind_utility = oracle[blind_chosen].utility
            assert memory_utility == max(x.utility for x in oracle.values())
            assert memory_utility - blind_utility == 1
            total_expected_benefit += Fraction(memory_utility - blind_utility)
            memory_utilities.append(memory_utility)
            blind_utilities.append(blind_utility)
            gain_rows += 1
        assert len(set(decisions)) == 2  # same current cues, different memory
    assert gain_rows == 6
    assert total_expected_benefit / 6 == 1
    assert Fraction(sum(memory_utilities), 6) == Fraction(33, 2)
    assert Fraction(sum(blind_utilities), 6) == Fraction(31, 2)
    assert Fraction(sum(no_memory_brier), 6) == Fraction(1, 4)
    assert Fraction(sum(memory_brier), 6) == 0


@pytest.mark.parametrize("invalid", [-1, 2, "1", True, None, 0.0])
def test_invalid_world_parameter_fails_closed(invalid):
    with pytest.raises(d2.D2ContractError):
        d2.session(invalid)
    with pytest.raises(d2.D2ContractError):
        d2.session(0) if invalid == 0 else d2._bit(invalid, "cue")


@pytest.mark.parametrize("bad", [
    (0, 0), (1, 1, 1), [0, 1], (True, 1), (0, False),
])
def test_train_cues_and_nonfrozen_inputs_are_rejected(bad):
    with pytest.raises(d2.D2ContractError):
        d2.predictor_evidence(d2.session(0), bad, include_memory=False)


def test_forged_eval_world_and_intervention_orders_are_rejected():
    src = d2.session(0)
    bad = d2.EpisodeSession("source-T1", 0)
    with pytest.raises(d2.D2ContractError):
        d2.intervene(bad, (0, 1), "DIRECT")
    for invalid in (
        ("DIRECT", "DIRECT", "INSPECT"),
        ("DIRECT", "INSPECT"),
        ("DIRECT", "DETOUR", "INVALID"),
    ):
        with pytest.raises(d2.D2ContractError):
            d2.all_counterfactuals(src, (0, 1), invalid)
    for invalid in ("FLEE", "direct", None, 0):
        with pytest.raises(d2.D2ContractError):
            d2.intervene(src, (0, 1), invalid)


def test_evaluation_session_is_immutable_and_no_world_ticking():
    x = d2.session(0)
    with pytest.raises(FrozenInstanceError):
        x.theta = 1
    assert d2.intervene(x, (1, 1), "INSPECT").observed_hazard == 0
    assert d2.intervene(x, (1, 1), "DIRECT").utility == 18
    assert x == d2.session(0)


def test_strong_cheap_baseline_is_complete_grand_null_witness():
    assert d2.manifest()["model_call_budget"] == 0
    assert d2.expected_action_utilities(Fraction(1, 2)) == {
        "DIRECT": Fraction(12),
        "DETOUR": Fraction(15),
        "INSPECT": Fraction(31, 2),
    }
    assert d2.expected_action_utilities(Fraction(0))["DIRECT"] == 18
    assert d2.expected_action_utilities(Fraction(1))["DETOUR"] == 15
