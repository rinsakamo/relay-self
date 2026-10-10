"""Exact frozen offline E2 tests: main typed seam; no S18 runtime or model claims."""

from __future__ import annotations

from copy import deepcopy
from dataclasses import FrozenInstanceError, replace
from fractions import Fraction
from itertools import permutations

import pytest

from experiments import epistemic_e2_main_seam as e2
from experiments.present_skill_epoch import projection_is_current
from relay_self.action import ActionLifecycle, ActionState, InvalidTransition
from relay_self.action_supervision import DuplicateSupervisedAction
from relay_self.provenance import Provenance
from relay_self.skill import SkillExecution

EXPECTED = {
    "NORMAL": (Fraction(14), Fraction(15), Fraction(15), Fraction(31, 2)),
    "REVERSE": (Fraction(14), Fraction(15), Fraction(15), Fraction(31, 2)),
    "ALWAYS_SAFE": (Fraction(18), Fraction(15), Fraction(18), Fraction(18)),
    "ALWAYS_RISK": (Fraction(10), Fraction(15), Fraction(15), Fraction(15)),
}
HISTORY = (
    ActionState.PROPOSED,
    ActionState.AUTHORIZED,
    ActionState.ISSUED,
    ActionState.OUTCOME,
)
ARMS = ("DIRECT", "DETOUR", "SCOUT_SCRIPT", "REDECIDE")


def test_manifest_freeze_and_population():
    assert e2.manifest_digest() == e2.MANIFEST_SHA256
    e2.verify_manifest()
    assert e2.MANIFEST["base_main"] == "4348a614900c1d0828581a8eec2c523ba5ae237f"
    assert e2.MANIFEST["e1_head"] == "f013d1b407dccff8d927899a98ba7dbfc9e40a4b"
    assert e2.MANIFEST["model_calls"] == 0
    assert e2.MANIFEST["physical_minecraft_actions"] == 0
    assert len(e2.cases()) == 8
    tampered = deepcopy(e2.MANIFEST)
    tampered["observe"]["ticks"] = 0
    assert e2.manifest_digest(tampered) != e2.MANIFEST_SHA256


def test_32_paired_world_interventions_and_all_24_arm_orders():
    count = 0
    for case in e2.cases():
        original = deepcopy(case)
        baseline = {arm: e2.run(case, arm).utility for arm in ARMS}
        for order in permutations(ARMS):
            assert {arm: e2.run(case, arm).utility for arm in order} == baseline
        assert case == original
        for arm in ARMS:
            result = e2.run(case, arm)
            assert result.utility == 20 - result.ticks - result.damage
            assert result.action_history == HISTORY
            assert result.open_actions_after == 0
            assert result.model_calls == 0
            assert result.epoch_count == 1 + result.observation_count
            assert (result.second_action is None) == (result.observation_count == 0)
            assert result.source_revision_at_action == result.observation_count
            count += 1
    assert count == 32


def test_expected_results_grand_null_and_fixed_script_failure():
    for rule, (direct, detour, no_observe, redecide) in EXPECTED.items():
        assert e2.expected_utility(rule, "DIRECT") == direct
        assert e2.expected_utility(rule, "DETOUR") == detour
        assert e2.expected_utility(rule, "NO_OBSERVE") == no_observe
        assert e2.expected_utility(rule, "REDECIDE") == redecide
        assert e2.expected_utility(rule, "CHEAP_BAYES") == redecide
    assert e2.expected_utility("NORMAL", "SCOUT_SCRIPT") == Fraction(31, 2)
    assert e2.expected_utility("REVERSE", "SCOUT_SCRIPT") == Fraction(23, 2)
    assert sum(e2.expected_utility(r, "REDECIDE") for r in EXPECTED) / 4 == 16
    assert sum(e2.expected_utility(r, "NO_OBSERVE") for r in EXPECTED) / 4 == (
        Fraction(63, 4)
    )
    assert e2.expected_utility("REVERSE", "REDECIDE") - e2.expected_utility(
        "REVERSE", "SCOUT_SCRIPT"
    ) == 4


def test_information_value_and_no_unnecessary_observation():
    for rule in EXPECTED:
        world = e2.FixtureWorld(e2.Case(rule, 0))
        initial = world.project()
        expected = Fraction(1, 2) if rule in ("NORMAL", "REVERSE") else -1
        assert e2.expected_information_value(initial) == expected
        decision = e2.choose_first(initial)
        assert (decision.action == "OBSERVE") == (expected > 0)
        assert world.observe_count == 0
        actual = e2.run(e2.Case(rule, 0), "REDECIDE")
        assert actual.observation_count == int(expected > 0)


def test_new_revision_changes_reconsidered_action_without_e0_gold():
    for rule in ("NORMAL", "REVERSE"):
        actions = set()
        for signal in (0, 1):
            w = e2.FixtureWorld(e2.Case(rule, signal))
            e0 = w.project()
            assert e0.fact("observed_signal") is None
            assert e0.fact("observation_event") is None
            assert w.session.startswith("e2/")
            assert rule not in w.session
            d0 = e2.choose_first(e0)
            assert d0.action == "OBSERVE"
            assert len(w.supervisor.open_actions) == 0
            e1 = w.observe(e0)
            assert e1.source_revision == 1
            assert e1.fact("observed_signal").value == signal
            assert e1.fact("observation_event").provenance.reference.endswith("/event")
            assert not projection_is_current(e0, current_source_revision=w.revision)
            d1 = e2.choose_second(e1)
            assert d1.action in ("DIRECT", "DETOUR")
            actions.add(d1.action)
            with pytest.raises(e2.ContractError, match="stale"):
                w.execute_terminal(e1, e2.Decision(d1.action, w.session, 0))
            assert not w.supervisor.open_actions
            ticks, damage, history = w.execute_terminal(e1, d1)
            assert (ticks, damage) in ((2, 0), (2, 8), (5, 0))
            assert history == HISTORY
            assert not w.supervisor.open_actions
        assert actions == {"DIRECT", "DETOUR"}


def test_wrong_source_stale_revision_forged_history_and_missing_event_fail_closed():
    w = e2.FixtureWorld(e2.Case("REVERSE", 0))
    e0 = w.project()
    w_other = e2.FixtureWorld(e2.Case("REVERSE", 0))
    with pytest.raises(e2.ContractError, match="stale or forged"):
        w_other.validate(e0)
    with pytest.raises(e2.ContractError, match="stale or forged"):
        w.validate(replace(e0, facts=e0.facts[:-1]))
    for replacement in (0, True, "fake"):
        modified = list(e0.facts)
        i = next(i for i, fact in enumerate(modified) if fact.key == "history:0")
        modified[i] = replace(modified[i], value=replacement)
        with pytest.raises(
            e2.ContractError, match="stale or forged|insufficient source history"
        ):
            w.observe(replace(e0, facts=tuple(modified)))
    e1 = w.observe(e0)
    with pytest.raises(e2.ContractError, match="stale or forged"):
        w.validate(e0)
    with pytest.raises(e2.ContractError, match="stale or forged"):
        w.validate(replace(e1, source_revision=0))
    with pytest.raises(e2.ContractError, match="stale or forged"):
        w.validate(replace(e1, facts=e1.facts[:-1]))
    with pytest.raises(e2.ContractError, match="stale or forged"):
        w.validate(replace(e1, facts=e1.facts + e0.facts[-1:]))
    with pytest.raises(e2.ContractError, match="duplicate OBSERVE"):
        w.observe(e1)
    with pytest.raises(e2.ContractError, match="second epoch"):
        e2.choose_second(e0)
    # bool==1 must not launder a forged revision or observed signal.
    w1 = e2.FixtureWorld(e2.Case("NORMAL", 1))
    fresh = w1.observe(w1.project())
    with pytest.raises(e2.ContractError, match="stale or forged"):
        w1.validate(replace(fresh, source_revision=True))
    values = list(fresh.facts)
    signal_index = next(i for i, fact in enumerate(values) if fact.key == "observed_signal")
    values[signal_index] = replace(values[signal_index], value=True)
    with pytest.raises(e2.ContractError, match="source integer"):
        w1.validate(replace(fresh, facts=tuple(values)))


def test_forecast_horizon_brier_and_hidden_outcome_separation():
    for case in e2.cases():
        w = e2.FixtureWorld(case)
        e0 = w.project()
        f0 = e2.forecast(e0)
        assert tuple(f.action for f in f0) == ("DIRECT", "DETOUR", "OBSERVE")
        assert tuple(f.horizon for f in f0) == (1, 1, 2)
        assert f0[2].probability_hazard is None  # OBSERVE is not a route
        p0 = f0[0].probability_hazard
        if case.rule in ("NORMAL", "REVERSE"):
            assert p0 == Fraction(1, 2)
        else:
            assert p0 in (0, 1)
        assert w.revision == 0
        e1 = w.observe(e0)
        f1 = e2.forecast(e1)
        assert tuple(f.action for f in f1) == ("DIRECT", "DETOUR")
        assert f1[0].probability_hazard == e2.hazard(case.rule, case.signal)
        result = e2.run(case, "REDECIDE")
        assert result.prediction_brier_e0 == (p0 - e2.hazard(case.rule, case.signal)) ** 2
        assert result.prediction_brier_e0 in (0, Fraction(1, 4))
        assert result.prediction_brier_e1 in (None, 0)


def test_existing_action_requires_authorization_and_supervisor_rejects_duplicates():
    w = e2.FixtureWorld(e2.Case("ALWAYS_SAFE", 0))
    proof = Provenance("fixture.test", "policy-bound")
    skill = SkillExecution.start(
        "test-skill", skill_id="test", intent_commitment=w.intent,
        at_ns=2, provenance=proof,
    )
    proposed = ActionLifecycle.propose(
        "test-action", skill_execution=skill, intent_commitment=w.intent,
        at_ns=3, provenance=proof,
    )
    with pytest.raises(InvalidTransition, match="proposed to issued"):
        proposed.issue(at_ns=4, deadline_ns=20, provenance=proof)
    assert len(w.supervisor.open_actions) == 0
    authorized = proposed.authorize(
        at_ns=4, authority="explicit-test", provenance=proof,
    )
    issued = w.supervisor.issue(authorized, at_ns=5, deadline_ns=20, provenance=proof)
    assert issued.state is ActionState.ISSUED
    with pytest.raises(DuplicateSupervisedAction):
        w.supervisor.issue(authorized, at_ns=6, deadline_ns=20, provenance=proof)
    final = w.supervisor.record_outcome("test-action", at_ns=7, provenance=proof)
    assert final.state is ActionState.OUTCOME
    with pytest.raises(InvalidTransition, match="outcome to outcome"):
        w.supervisor.record_outcome("test-action", at_ns=8, provenance=proof)


def test_evaluator_only_result_and_read_only_lane_handoff_no_unobserved_hazard():
    r = e2.run(e2.Case("REVERSE", 0), "REDECIDE")
    episode = e2.exported_episode(r)
    assert episode.source == r.source_session
    assert episode.world_revision == 1
    assert episode.information_acquired
    assert episode.selected_action == "DETOUR"
    assert episode.prediction_error is None
    assert episode.observed_outcome == (5, 0)
    assert episode.total_world_ticks == 6
    assert episode.observe_ticks == 1
    assert episode.model_calls == 0
    assert "rule" not in episode.__dataclass_fields__
    assert "test_signal" not in episode.__dataclass_fields__
    assert "rule" not in (f.key for f in episode.observed_present)
    with pytest.raises(FrozenInstanceError):
        episode.source = "tampered"
    direct = e2.run(e2.Case("ALWAYS_SAFE", 0), "DIRECT")
    assert e2.exported_episode(direct).prediction_error == 0
    with pytest.raises(e2.ContractError, match="source-bound"):
        e2.exported_episode(replace(r, source_session="forged"))


def test_physical_and_cognitive_costs_are_not_conflated():
    for case in e2.cases():
        r = e2.run(case, "REDECIDE")
        assert r.model_calls == r.handoff.model_calls == 0
        assert r.handoff.total_world_ticks == r.ticks
        assert r.handoff.observe_ticks == r.observation_count
        assert r.handoff.uncertainty in (0, Fraction(1, 4))


def test_malformed_signal_and_terminal_world_are_not_success():
    for signal in (True, -1, 2, "0"):
        with pytest.raises(e2.ContractError, match="invalid signal"):
            e2.hazard("NORMAL", signal)
    with pytest.raises(e2.ContractError, match="unregistered"):
        e2.FixtureWorld(e2.Case("BOGUS", 0))
    w = e2.FixtureWorld(e2.Case("NORMAL", 0))
    e0 = w.project()
    w.execute_terminal(e0, e2.Decision("DIRECT", w.session, 0))
    with pytest.raises(e2.ContractError, match="terminal World"):
        w.project()
    with pytest.raises(e2.ContractError, match="terminal World"):
        w.execute_terminal(e0, e2.Decision("DIRECT", w.session, 0))
