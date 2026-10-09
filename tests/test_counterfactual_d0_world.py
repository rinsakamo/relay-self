"""Zero-model qualification tests for the frozen #421 D0 reference fixture."""

from __future__ import annotations

from copy import deepcopy
from dataclasses import FrozenInstanceError
from fractions import Fraction
from itertools import permutations

import pytest

from experiments import counterfactual_d0_world as d0


def test_exact_frozen_manifest_and_defensive_copy():
    assert d0.manifest_sha256() == d0.EXPECTED_MANIFEST_SHA256
    assert d0.EXPECTED_MANIFEST_SHA256 == (
        "44d4f46d7deb42bd36f9706c87ba1374ab8fbc2656a80236bdcafa59693b5506"
    )
    d0.assert_manifest_identity()
    copy = d0.manifest()
    copy["goal_reward"] = 99
    with pytest.raises(d0.FixtureContractError, match="drift"):
        d0.assert_manifest_identity(copy)
    assert d0.manifest()["goal_reward"] == 20
    assert d0.manifest_sha256() == d0.EXPECTED_MANIFEST_SHA256


@pytest.mark.parametrize("field", [
    "seed", "latent_hazard", "hazard", "oracle_action",
    "outcome", "utilityByAction", "goldAction", "futureEvidence",
    "resetTrace", "mapping", "arm", "result", "executionIndex",
])
def test_gold_and_ledger_information_cannot_leak(field):
    payload = d0.predictor_evidence(10)
    payload[field] = "oracle"
    with pytest.raises(d0.FixtureContractError, match="leakage"):
        d0.validate_predictor_evidence(payload)


def test_nested_hidden_world_injection_and_source_drift_fail_closed():
    for key, value in [
        ("future", {"hazard": 1}),
        ("total", 40),
        ("hazardCount", 20),
    ]:
        payload = d0.predictor_evidence(10)
        if key == "future":
            payload["prior"][key] = value
        else:
            payload["prior"][key] = value
        with pytest.raises(d0.FixtureContractError):
            d0.validate_predictor_evidence(payload)

    for mutation in [
        lambda p: p["actions"]["DIRECT"].update({"elapsedTicks": 999}),
        lambda p: p["actions"]["INSPECT"]["followUp"].update(
            {"hazardAbsent": "DETOUR"}
        ),
        lambda p: p["utility"].update({"healthLossPenalty": 0}),
    ]:
        payload = d0.predictor_evidence(10)
        mutation(payload)
        with pytest.raises(d0.FixtureContractError):
            d0.validate_predictor_evidence(payload)


def test_all_100_subjects_have_exact_hidden_class_hazard_counts():
    assert d0.CLASS_COUNTS == (0, 5, 10, 15, 20)
    assert d0.SEEDS_PER_CLASS == 20
    assert d0.ACTIONS == ("DIRECT", "DETOUR", "INSPECT")
    cases = 0
    for k in d0.CLASS_COUNTS:
        observed = [d0.initial_state(k, s).latent_hazard for s in range(20)]
        assert sum(observed) == k
        assert set(observed) <= {0, 1}
        for seed in range(20):
            cases += 1
            assert d0.validate_predictor_evidence(d0.predictor_evidence(k)) == k
            # Same class/source evidence for all distinct hidden World subjects.
            assert d0.predictor_evidence(k) == d0.predictor_evidence(k)
            assert "seed" not in d0.predictor_evidence(k)
            assert "latent_hazard" not in d0.predictor_evidence(k)
    assert cases == 100


def test_all_300_interventions_replay_independent_and_order_invariant():
    total = 0
    all_orders = tuple(permutations(d0.ACTIONS))
    assert len(all_orders) == 6
    for k in d0.CLASS_COUNTS:
        for seed in range(d0.SEEDS_PER_CLASS):
            base = d0.initial_state(k, seed)
            before = deepcopy(base)
            expected = d0.controlled_counterfactuals(k, seed)
            assert set(expected) == set(d0.ACTIONS)
            for order in all_orders:
                assert d0.controlled_counterfactuals(k, seed, order) == expected
            assert base == before
            for a in d0.ACTIONS:
                value = expected[a]
                assert value == d0.intervene(base, a)
                assert value.goal_reached is True
                assert value.utility == 20 - value.elapsed_ticks - value.health_loss
                total += 1
            assert expected["DIRECT"].health_loss == 12 * base.latent_hazard
            assert expected["DETOUR"].health_loss == 0
            assert expected["INSPECT"].health_loss == 0
            assert expected["INSPECT"].observed_hazard == base.latent_hazard
            assert expected["DIRECT"].observed_hazard is None
            assert expected["DETOUR"].observed_hazard is None
            assert expected["INSPECT"].elapsed_ticks == (
                6 if base.latent_hazard else 3
            )
    assert total == 300


@pytest.mark.parametrize(("k", "scores", "winner", "margin"), [
    (0, (18, 15, 17), "DIRECT", Fraction(1)),
    (5, (15, 15, Fraction(65, 4)), "INSPECT", Fraction(5, 4)),
    (10, (12, 15, Fraction(31, 2)), "INSPECT", Fraction(1, 2)),
    (15, (9, 15, Fraction(59, 4)), "DETOUR", Fraction(1, 4)),
    (20, (6, 15, 14), "DETOUR", Fraction(1)),
])
def test_expected_utilities_match_full_counterfactual_20_seed_oracle(
    k, scores, winner, margin
):
    evidence = d0.predictor_evidence(k)
    expected = d0.expected_utility_from_evidence(evidence)
    assert tuple(expected.values()) == scores
    actual = {
        a: Fraction(
            sum(d0.intervene(d0.initial_state(k, seed), a).utility
                for seed in range(20)), 20
        )
        for a in d0.ACTIONS
    }
    assert actual == expected
    assert d0.cheap_decision(evidence) == winner
    ranked = sorted(actual.values(), reverse=True)
    assert ranked[0] - ranked[1] == margin


def test_brier_prior_heldout_score_equals_one_eighth_over_100_states():
    total = Fraction(0)
    n = 0
    for k in d0.CLASS_COUNTS:
        p = Fraction(k, 20)
        for seed in range(20):
            truth = d0.initial_state(k, seed).latent_hazard
            total += d0.hazard_brier_score(p, truth)
            n += 1
    assert n == 100
    assert total / n == Fraction(1, 8)


@pytest.mark.parametrize("bad", [-1, 1, 4, 6, 21, True, None, "10", 10.0])
def test_invalid_frozen_classes_fail_closed(bad):
    with pytest.raises(d0.FixtureContractError):
        d0.predictor_evidence(bad)
    with pytest.raises(d0.FixtureContractError):
        d0.initial_state(bad, 0)


@pytest.mark.parametrize("bad", [-1, 20, 21, True, None, 1.0, "0"])
def test_invalid_seed_values_fail_closed(bad):
    with pytest.raises(d0.FixtureContractError):
        d0.initial_state(10, bad)


@pytest.mark.parametrize("bad", ["FLY", "direct", None, 1, "", True])
def test_unknown_action_incorrect_world_state_and_order_fail_closed(bad):
    source = d0.initial_state(5, 0)
    with pytest.raises(d0.FixtureContractError):
        d0.intervene(source, bad)
    with pytest.raises(d0.FixtureContractError):
        d0.controlled_counterfactuals(5, 0, ("DIRECT", "DIRECT", "DETOUR"))
    with pytest.raises(d0.FixtureContractError):
        d0.controlled_counterfactuals(5, 0, ("DIRECT", "DETOUR"))
    with pytest.raises(d0.FixtureContractError):
        d0.intervene(
            d0.WorldState(source.class_k, source.seed, 1 - source.latent_hazard),
            "DIRECT",
        )


def test_frozen_world_state_disallows_in_place_mutation():
    source = d0.initial_state(10, 0)
    with pytest.raises(FrozenInstanceError):
        source.latent_hazard = 1 - source.latent_hazard


@pytest.mark.parametrize("bad", [
    -1, 2, "0.5", None, True, float("nan"), float("inf"), -0.1, 1.01,
])
def test_invalid_probabilities_and_gold_scores_fail_closed(bad):
    with pytest.raises(d0.FixtureContractError):
        d0.hazard_brier_score(bad, 0)
    with pytest.raises(d0.FixtureContractError):
        d0.hazard_brier_score(Fraction(1, 2), bad)


def test_no_new_semantic_authority_or_model_transport_in_reference_fixture():
    # The source is a pure deterministic environment. The test must never
    # import a live experiment launcher, GPU engine, or model client.
    assert d0.manifest()["manifest_version"] == "CF-D0-TOY-v1"
    assert d0.cheap_decision(d0.predictor_evidence(0)) == "DIRECT"
    assert d0.cheap_decision(d0.predictor_evidence(10)) == "INSPECT"
    assert d0.cheap_decision(d0.predictor_evidence(20)) == "DETOUR"
