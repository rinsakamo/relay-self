"""K3-F 4-v-10 mock capacity comparison: historical budgets stay unchanged."""

from __future__ import annotations

import copy
import json
from pathlib import Path

import pytest

from experiments.skill_crystallization_dev import (
    WorldTrial,
    cue_for,
    run_skill,
    skill_json_schema,
    validate_skill,
)
from experiments.skill_crystallization_k3f_budget_dev import (
    EXPLORATORY_SEED,
    PROTECTED_SEEDS,
    budget10_schema,
    compare_action_budgets,
    paired_trials,
    run_budget10_shadow,
    validate_budget10_shadow,
)


@pytest.fixture
def first():
    path = (Path(__file__).resolve().parents[1] /
            "evidence/l431-gemma-20261108/first-report.json")
    return json.loads(path.read_text(encoding="utf-8"))


@pytest.fixture
def source(first):
    old = first["candidate_raw"]
    evidence = {row["experience_id"] for row in first["training"]}
    validate_skill(old, evidence)
    return old, evidence


def test_historical_wire_schema_and_validator_remain_bounded_four(source):
    old, evidence = source
    assert old["max_actions"] == 4
    assert skill_json_schema()["properties"]["max_actions"]["enum"] == [1, 2, 3, 4]
    widened = {**old, "max_actions": 10}
    with pytest.raises(ValueError, match="ACTION_BUDGET_INVALID"):
        validate_skill(widened, evidence)
    assert validate_skill(old, evidence)["max_actions"] == 4


def test_optin_schema_includes_ten_without_global_mutation():
    shadow = budget10_schema()
    assert shadow["properties"]["max_actions"]["enum"] == list(range(1, 11))
    assert skill_json_schema()["properties"]["max_actions"]["enum"] == [1, 2, 3, 4]


@pytest.mark.parametrize("invalid", [0, 11, True, 2.5, "10", None])
def test_invalid_shadow_budgets_rejected(source, invalid):
    old, evidence = source
    with pytest.raises(ValueError, match="SHADOW_ACTION_BUDGET_INVALID"):
        validate_budget10_shadow({**old, "max_actions": invalid}, evidence)


def test_shadow_preserves_independent_evidence_validator(source):
    old, evidence = source
    with pytest.raises(ValueError, match="EVIDENCE_NOT_TRAINING_SOURCED"):
        validate_budget10_shadow({
            **old, "max_actions": 10, "evidence_ids": ["unknown-future"]
        }, evidence)


def test_shadow_needs_all_ten_synthetic_outcomes_before_action(source):
    old, evidence = source
    insufficient = WorldTrial("normal", 2.4, (0.2,) * 5, "short")
    with pytest.raises(ValueError, match="PHYSICAL_EFFECT_SEQUENCE_TOO_SHORT"):
        run_budget10_shadow({**old, "max_actions": 10},
                            insufficient, evidence_ids=evidence)
    assert run_skill(old, insufficient, cue_for(insufficient))["action_count"] == 4


def test_goal_early_stop_no_ten_action_forcing(source):
    old, evidence = source
    trial = WorldTrial("normal", 2.4, (0.65,) * 10, "early-stop")
    four = run_skill(old, trial, cue_for(trial))
    ten = run_budget10_shadow({**old, "max_actions": 10},
                              trial, evidence_ids=evidence)
    assert four == ten
    assert ten["success"]
    assert ten["action_count"] == 2


def test_four_failure_rescued_by_extra_actions(source):
    old, evidence = source
    trial = WorldTrial("normal", 2.4, (0.19,) * 10, "slow-motion")
    four = run_skill(old, trial, cue_for(trial))
    ten = run_budget10_shadow({**old, "max_actions": 10},
                              trial, evidence_ids=evidence)
    assert not four["success"]
    assert four["action_count"] == 4
    assert ten["success"]
    assert ten["action_count"] == 5
    assert ten["trace"][:len(four["trace"])] == four["trace"]


def test_trials_paired_and_ten_effects_from_fresh_seed(source):
    old, _ = source
    x = paired_trials(old, seed=EXPLORATORY_SEED, n=16)
    y = paired_trials(old, seed=EXPLORATORY_SEED, n=16)
    assert x == y
    assert len(x) == 16
    assert [regime for regime, _ in x].count("changed") == 8
    assert [regime for regime, _ in x].count("slow") == 8
    assert all(len(t.effects) == 10 for _, t in x)
    assert all(old["min_distance"] <= t.start < old["max_distance"] for _, t in x)


@pytest.mark.parametrize("seed", sorted(PROTECTED_SEEDS))
def test_protected_existing_holdouts_unavailable(source, seed):
    old, _ = source
    with pytest.raises(ValueError, match="PROTECTED_OR_INVALID_SEED"):
        paired_trials(old, seed=seed, n=2)


@pytest.mark.parametrize("invalid", [0, 1, 3, 1025, True])
def test_odd_or_out_of_range_trial_counts_rejected(source, invalid):
    old, _ = source
    with pytest.raises(ValueError, match="PAIRED_TRIAL_COUNT_INVALID"):
        paired_trials(old, seed=EXPLORATORY_SEED, n=invalid)


def test_compare_is_paired_and_never_overrides_old_skill(first):
    initial = copy.deepcopy(first)
    report = compare_action_budgets(first)
    assert first == initial
    assert report["trials"] == 64
    assert report["seed"] == EXPLORATORY_SEED
    assert report["old_skill_modified"] is False
    assert report["gemma_posts"] == report["real_worlds"] == report["native_s49_actions"] == 0
    assert report["previous_holdout_20261126"] == "UNOPENED"
    assert report["k3e_probe_20261205"] == "UNOPENED"
    assert len(report["paired_trials"]) == 64
    for regime, stats in report["summary"].items():
        assert regime in ("changed", "slow")
        assert stats["n"] == 32
        assert stats["budget10_success"] >= stats["budget4_success"]
        assert stats["budget10_exhausted_and_failed"] <= stats["budget4_exhausted_and_failed"]
        assert stats["extra_actions_on_successful_budget4"] == 0
        assert stats["budget10_actions"] <= 10 * stats["n"]
        assert stats["rescued_by_extra_actions"] == (
            stats["budget10_success"] - stats["budget4_success"]
        )
        frontier = report["budget_frontier"][regime]
        assert sorted(frontier) == [4, 5, 6, 8, 10]
        assert frontier[4]["goal_success"] == stats["budget4_success"]
        assert frontier[10]["goal_success"] == stats["budget10_success"]
        assert frontier[4]["actions"] == stats["budget4_actions"]
        assert frontier[10]["actions"] == stats["budget10_actions"]
        assert list(x["goal_success"] for x in frontier.values()) == sorted(
            x["goal_success"] for x in frontier.values()
        )


def test_budget10_is_shadow_only_and_no_implicit_postfailure_fallback(source):
    old, evidence = source
    trial = WorldTrial("normal", 2.4, (0.01,) * 10, "too-slow")
    result = run_budget10_shadow({**old, "max_actions": 10},
                                 trial, evidence_ids=evidence)
    assert result["action_count"] == 10
    assert not result["success"]
    assert len(result["trace"]) == 11
    # The shadow runner returns a terminal observation; it never grants an
    # additional L0/S49 fallback Action after exhausting its explicit budget.
