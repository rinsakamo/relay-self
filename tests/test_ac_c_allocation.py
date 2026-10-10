"""Deterministic AC-C offline negative controls (no model / Minecraft / GPU)."""

import dataclasses

import pytest

from experiments.ac_c_allocation import (
    Evidence,
    LearningState,
    SyntheticWorld,
    canonical_hash,
    cases_for,
    choose,
    evaluate,
    manifest,
    oracle,
    run,
    viable,
)


def test_manifest_exact_and_train_heldout_separation():
    m = manifest()
    assert m["training_seeds"] == [11, 13, 17]
    assert set(m["training_seeds"]).isdisjoint(m["heldout_seeds"])
    assert canonical_hash(m) == "d444b96c40a5bec21603122298b3d138e4b0139ad77e027de80d190d2316a481"


def test_deterministic_paired_cases():
    assert cases_for(31, 64) == cases_for(31, 64)
    assert cases_for(31, 64) != cases_for(37, 64)
    assert len(cases_for(31, 64)) == 256


def test_selector_evidence_has_no_hidden_future_or_regime():
    case = cases_for(31, 64)[0]
    e = SyntheticWorld(case).evidence(fatigue=0)
    assert isinstance(e, Evidence)
    assert not hasattr(e, "phase")
    assert not hasattr(e, "target")
    assert not hasattr(e, "seed")


def test_wrong_source_stale_revision_and_duplicate_fail_closed():
    case = cases_for(37, 64)[0]
    world = SyntheticWorld(case)
    e = world.evidence(fatigue=0)
    for forged in (
        dataclasses.replace(e, session="wrong"),
        dataclasses.replace(e, revision=1),
        dataclasses.replace(e, cue=1 - e.cue),
        dataclasses.replace(e, observation=1),
    ):
        with pytest.raises(ValueError):
            world.execute(forged, "FAST")
    world.execute(e, "FAST")
    with pytest.raises(ValueError, match="DUPLICATE"):
        world.execute(e, "FAST")


def test_oracle_not_admitted_as_ordinary_selector():
    case = cases_for(41, 64)[0]
    e = SyntheticWorld(case).evidence(fatigue=0)
    with pytest.raises(ValueError, match="ORACLE"):
        choose(e, "ORACLE_UPPER_BOUND", "TIME_ONLY", LearningState())
    assert oracle(e, case, "TIME_ONLY") in ("FAST", "MEDIUM", "SLOW", "OBSERVE", "ABSTAIN")


def test_hard_viability_nonnegotiable():
    e = Evidence("s", 0, 4, 0, 1, 2, 2, True, False)
    assert not viable(e, "FAST", "TIME_ONLY")
    assert not viable(e, "SLOW", "TIME_ONLY")
    assert choose(e, "LEARNED", "TIME_ONLY", LearningState()) == "ABSTAIN"
    assert choose(e, "FIXED", "TIME_ONLY", LearningState()) == "ABSTAIN"


def test_no_synthetic_counterfactual_training_labels():
    state = LearningState()
    e = Evidence("s", 0, 1, 0, 7, 8, 16, False, True)
    state.update(e, "SLOW", True, bridge=False)
    assert not state.outcomes
    state.update(e, "FAST", False, bridge=False)
    assert state.outcomes[(0, "FAST")].count(False) == 1
    assert (0, "MEDIUM") not in state.outcomes


def test_chosen_outcome_success_then_shift_failure_changes_estimate():
    state = LearningState()
    e = Evidence("s", 0, 1, 0, 7, 8, 16, False, True)
    for _ in range(6):
        state.update(e, "FAST", True, bridge=False)
    assert state.estimate(0, "FAST") >= 0.75
    for _ in range(6):
        state.update(e, "FAST", False, bridge=False)
    assert state.estimate(0, "FAST") < 0.75
    assert (0, "MEDIUM") not in state.outcomes


def test_fatigue_bridge_is_simulator_only():
    e = Evidence("s", 0, 1, 0, 7, 8, 16, False, True)
    off, on = LearningState(), LearningState()
    for _ in range(4):
        off.update(e, "SLOW", True, bridge=False)
        on.update(e, "SLOW", True, bridge=True)
    assert off.fatigue == 0
    assert on.fatigue >= 8
    changed = dataclasses.replace(e, fatigue=on.fatigue)
    assert viable(changed, "SLOW", "FATIGUE_BRIDGE_OFF")
    assert not viable(changed, "SLOW", "FATIGUE_BRIDGE_ON")
    assert e.hunger == 16


def test_selector_overhead_negative_control():
    normal = evaluate(31, "LEARNED", "BODY_AWARE")
    costly = evaluate(31, "LEARNED", "HIGH_OVERHEAD")
    assert sum(p["selector_ops"] for p in costly["phases"].values()) > sum(
        p["selector_ops"] for p in normal["phases"].values()
    )
    assert all(p["violation"] == 0 for p in normal["phases"].values())


def test_frozen_result_and_viability_all_conditions():
    a, b = run(), run()
    assert a["result_sha256"] == b["result_sha256"]
    assert a["n_records"] == 8 * 6 * 5
    for record in a["records"]:
        for phase in ("unknown", "stable", "shift", "recovery"):
            p = record["phases"][phase]
            assert p["success"] + p["failure"] + p["abstain"] == 64
            assert p["violation"] == 0
