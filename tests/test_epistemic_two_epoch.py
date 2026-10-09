"""Offline tests for AC Lane A post-D4 two-epoch information seeking fixture."""

from __future__ import annotations

from copy import deepcopy
from dataclasses import FrozenInstanceError, replace
from fractions import Fraction
from itertools import permutations

import pytest

from experiments import epistemic_two_epoch as a

EXPECTED_MEANS = {
    "NORMAL": (Fraction(14), Fraction(15), Fraction(15, 1), Fraction(31, 2)),
    "REVERSE": (Fraction(14), Fraction(15), Fraction(15, 1), Fraction(31, 2)),
    "ALWAYS_SAFE": (Fraction(18), Fraction(15), Fraction(18), Fraction(18)),
    "ALWAYS_RISK": (Fraction(10), Fraction(15), Fraction(15), Fraction(15)),
}


def test_manifest_frozen_and_exact_population():
    assert a.digest() == a.MANIFEST_SHA256
    a.verify_manifest()
    assert a.VERSION == "AC-A-EPISTEMIC-TWO-EPOCH-v1"
    assert len(a.cases()) == 8
    assert a.MANIFEST["paired_subjects"] == 8
    assert a.MANIFEST["reference_interventions"] == 32
    assert a.MANIFEST["scientific_model_calls"] == 0
    tampered = deepcopy(a.MANIFEST)
    tampered["observe"]["ticks"] = 0
    with pytest.raises(a.ContractError, match="drift"):
        a.verify_manifest(tampered)


def test_32_reset_reference_interventions_action_order_invariance_and_no_mutation():
    count = 0
    for case in a.cases():
        frozen = deepcopy(case)
        reference = a.four_world_interventions(case)
        assert len(reference) == 4
        for order in permutations(("DIRECT", "DETOUR", "SCOUT_SCRIPT", "REDECIDE")):
            assert a.four_world_interventions(case, order) == reference
        assert case == frozen
        for result in reference.values():
            assert result.utility == 20 - result.ticks - result.damage
            assert result.observation_count in (0, 1)
            assert result.epoch_count == 1 + result.observation_count
            assert (result.second_action is None) == (result.observation_count == 0)
            count += 1
    assert count == 32


def test_means_optimal_observation_and_deferred_second_epoch():
    for rule, (direct, detour, no_obs, adaptive) in EXPECTED_MEANS.items():
        assert a.expected_utility(rule, "DIRECT") == direct
        assert a.expected_utility(rule, "DETOUR") == detour
        assert a.expected_utility(rule, "NO_OBSERVE") == no_obs
        assert a.expected_utility(rule, "REDECIDE") == adaptive
        assert a.expected_utility(rule, "REDECIDE") == a.expected_utility(
            rule, "CHEAP_BAYES"
        )
    assert a.expected_utility("NORMAL", "SCOUT_SCRIPT") == Fraction(31, 2)
    assert a.expected_utility("REVERSE", "SCOUT_SCRIPT") == Fraction(23, 2)
    assert a.expected_utility("REVERSE", "REDECIDE") == Fraction(31, 2)
    assert a.expected_utility("NORMAL", "ORACLE") == Fraction(33, 2)
    assert a.expected_utility("REVERSE", "ORACLE") == Fraction(33, 2)
    assert sum(a.expected_utility(r, "REDECIDE") for r in EXPECTED_MEANS) / 4 == 16
    assert sum(a.expected_utility(r, "NO_OBSERVE") for r in EXPECTED_MEANS) / 4 == (
        Fraction(63, 4)
    )


def test_actual_observation_changes_choice_and_world_revision():
    for rule in ("NORMAL", "REVERSE"):
        chosen = {}
        for signal in (0, 1):
            case = a.Case(f"{rule}_{signal}", rule, signal)
            world = a.fresh_world(case, "REDECIDE")
            e0 = a.project(world)
            assert e0.observed_signal is None
            assert a.first_epoch(e0) == "OBSERVE"
            w1, e1 = a.observe(world, e0)
            assert w1.world_revision == 1
            assert e1.world_revision == 1
            assert e1.source_session == e0.source_session
            assert e1.observed_signal == signal
            assert e1.observation_event != e0.observation_event
            a.validate_source(w1, e1)
            chosen[signal] = a.second_epoch(e1)
            finished, _ = a.finish(w1, e1, chosen[signal])
            assert finished.terminal
            with pytest.raises(a.ContractError, match="terminal"):
                a.project(finished)
        assert chosen[0] != chosen[1]
    assert a.execute(a.cases()[0], "REDECIDE").epoch_count == 2


def test_observation_not_automatically_selected_when_useless():
    for rule, expected in (("ALWAYS_SAFE", "DIRECT"), ("ALWAYS_RISK", "DETOUR")):
        for signal in (0, 1):
            case = a.Case(f"{rule}_{signal}", rule, signal)
            r = a.execute(case, "REDECIDE")
            assert r.first_action == expected
            assert r.observation_count == 0
            assert r.epoch_count == 1


def test_wrong_session_stale_and_forged_source_fail_closed():
    case = a.cases()[0]
    world = a.fresh_world(case, "REDECIDE")
    e0 = a.project(world)
    wrong = replace(e0, source_session="forged-source")
    with pytest.raises(a.ContractError, match="source/revision"):
        a.validate_source(world, wrong)
    other_world = a.fresh_world(case, "REDECIDE")
    with pytest.raises(a.ContractError, match="source/revision"):
        a.validate_source(other_world, e0)
    tampered = replace(e0, episodes=(replace(e0.episodes[0], observed_hazard=1), e0.episodes[1]))
    with pytest.raises(a.ContractError, match="source/revision"):
        a.observe(world, tampered)
    with pytest.raises(a.ContractError, match="source/revision"):
        a.observe(world, replace(e0, observed_signal=0))
    w1, e1 = a.observe(world, e0)
    with pytest.raises(a.ContractError, match="source/revision"):
        a.finish(w1, e0, "DIRECT")
    with pytest.raises(a.ContractError, match="not a first epoch"):
        a.first_epoch(e1)
    with pytest.raises(a.ContractError, match="OBSERVE replay"):
        a.observe(w1, e1)
    with pytest.raises(a.ContractError, match="not second epoch"):
        a.second_epoch(e0)


def test_episode_conflict_missing_support_and_source_negative():
    case = a.cases()[0]
    world = a.fresh_world(case, "REDECIDE")
    e = a.project(world)
    with pytest.raises(a.ContractError, match="incomplete episode history"):
        a.first_epoch(replace(e, episodes=e.episodes[:1]))
    with pytest.raises(a.ContractError, match="insufficient or contradictory"):
        a.first_epoch(replace(e, episodes=(e.episodes[0], e.episodes[0])))
    with pytest.raises(a.ContractError, match="invalid source-bound episode"):
        a.first_epoch(replace(e, episodes=(replace(e.episodes[0], action="DETOUR"), e.episodes[1])))
    with pytest.raises(a.ContractError, match="source/revision"):
        a.validate_source(world, replace(e, world_revision=1, observed_signal=0))
    with pytest.raises(a.ContractError, match="only bounded"):
        a.finish(world, e, "OBSERVE")
    with pytest.raises(a.ContractError, match="bad signal"):
        a.hazard("NORMAL", True)


def test_result_immutable_and_preobserved_signal_never_read_from_case():
    case = a.Case("REVERSE_0", "REVERSE", 0)
    w = a.fresh_world(case, "REDECIDE")
    e = a.project(w)
    assert "REVERSE" not in e.source_session
    assert "REVERSE_0" not in e.source_session
    assert e.observed_signal is None
    assert "case_id" not in e.__dict__
    assert "test_signal" not in e.__dict__
    with pytest.raises(FrozenInstanceError):
        e.world_revision = 99


def test_first_epoch_evidence_same_for_both_hidden_signal_states_of_each_rule():
    for rule in EXPECTED_MEANS:
        prior_projections = []
        for signal in (0, 1):
            case = a.Case(f"{rule}_{signal}", rule, signal)
            world = a.fresh_world(case, "REDECIDE")
            e = a.project(world)
            prior_projections.append((tuple((ep.observed_signal, ep.observed_hazard) for ep in e.episodes), e.observed_signal))
        assert prior_projections[0] == prior_projections[1]
