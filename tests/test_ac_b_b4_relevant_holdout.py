"""AC-B B4 prospectively frozen source-safe relevant-cue and Grand Null gates."""
from dataclasses import replace

import pytest

from experiments.ac_b_b4_relevant_holdout import (
    FAMILIES,
    HELDOUT,
    TRAIN,
    VALIDATE,
    Cue,
    ResetWorld,
    Rule,
    UnqualifiedEvidence,
    cheap_analytic_rule,
    compile_habit,
    exact_full_cue_replay,
    observe,
    run_fixture,
    version_space,
)


def evidence(family="PARITY3", flip=0):
    world = ResetWorld(family, flip)
    train = observe(world, TRAIN)
    validation = observe(world, VALIDATE)
    return world, train, validation


@pytest.mark.parametrize("family", FAMILIES)
@pytest.mark.parametrize("flip", (0, 1))
def test_train_is_ambiguous_but_independent_validation_identifies_family(family, flip):
    world, train, validation = evidence(family, flip)
    assert world.count == 10
    assert len(train) == 8
    assert len(validation) == 2
    assert len(version_space(world, train)) == 2
    assert version_space(world, train, validation) == (Rule(family, flip),)
    policy = compile_habit(world, train, validation)
    assert policy is not None
    assert policy.rule == Rule(family, flip)
    assert cheap_analytic_rule(world, train, validation) == policy.rule
    assert set(policy.training_ids).isdisjoint(policy.qualification_ids)
    assert policy.select(world.session, world.revision, Cue(0, 1, 1)) in (0, 1)


@pytest.mark.parametrize("family", FAMILIES)
@pytest.mark.parametrize("flip", (0, 1))
def test_relevant_combination_holdout_and_cheap_baseline_grand_null(family, flip):
    world, train, validation = evidence(family, flip)
    candidate = compile_habit(world, train, validation)
    cheap = cheap_analytic_rule(world, train, validation)
    assert candidate is not None and cheap is not None
    for bits in HELDOUT:
        cue = Cue(*bits)
        assert bits not in TRAIN + VALIDATE
        assert exact_full_cue_replay(train, cue) is None
        predicted = candidate.select(world.session, world.revision, cue)
        assert predicted == cheap.select(cue)
        receipt = world.act(cue, predicted)
        assert receipt.success
        world.verify(receipt)
        assert receipt.receipt_id not in candidate.training_ids
        assert receipt.receipt_id not in candidate.qualification_ids


@pytest.mark.parametrize("bad", (
    "forged_digest", "forged_success", "predicted", "wrong_session",
    "wrong_revision", "different_context", "duplicate", "missing_action",
))
def test_evidence_negative_controls_fail_closed(bad):
    world, train, validation = evidence()
    malformed = train
    if bad == "forged_digest":
        malformed = (replace(train[0], digest="0" * 64),) + train[1:]
    elif bad == "forged_success":
        malformed = (replace(train[0], success=not train[0].success),) + train[1:]
    elif bad == "predicted":
        malformed = (replace(train[0], kind="PREDICTED"),) + train[1:]
    elif bad == "wrong_session":
        malformed = (replace(train[0], session="other"),) + train[1:]
    elif bad == "wrong_revision":
        malformed = (replace(train[0], revision=1),) + train[1:]
    elif bad == "different_context":
        malformed = (replace(train[0], cue=Cue(1, 1, 1)),) + train[1:]
    elif bad == "duplicate":
        malformed = train[:-1] + (train[0],)
    elif bad == "missing_action":
        malformed = train[:-1]
    with pytest.raises(UnqualifiedEvidence):
        compile_habit(world, malformed, validation)
    with pytest.raises(UnqualifiedEvidence):
        cheap_analytic_rule(world, malformed, validation)


def test_cross_session_and_stale_world_never_admitted():
    world, train, validation = evidence()
    outsider, other_train, _ = evidence("OR3")
    with pytest.raises(UnqualifiedEvidence):
        compile_habit(world, other_train, validation)
    with pytest.raises(UnqualifiedEvidence):
        compile_habit(outsider, train, validation)
    old = compile_habit(world, train, validation)
    assert old is not None
    assert old.select("wrong", 0, Cue(0, 1, 1)) is None
    world.flip_rule(announce_revision=True)
    assert old.select(world.session, world.revision, Cue(0, 1, 1)) is None
    with pytest.raises(UnqualifiedEvidence):
        compile_habit(world, train, validation)
    with pytest.raises(UnqualifiedEvidence):
        cheap_analytic_rule(world, train, validation)


def test_cross_split_reuse_and_ambiguous_no_optimism():
    world, train, validation = evidence()
    assert len(version_space(world, train)) == 2
    # Caller must not promote a training-only ambiguous version space.
    assert len(version_space(world, train)) != 1
    with pytest.raises(UnqualifiedEvidence):
        compile_habit(world, train, train[:2])
    with pytest.raises(UnqualifiedEvidence):
        compile_habit(world, train, validation[:-1] + (train[1],))
    with pytest.raises(UnqualifiedEvidence):
        cheap_analytic_rule(world, train, validation[:-1])


def test_exact_qualified_contradiction_is_not_promoted():
    world, train, validation = evidence()
    world.flip_rule(announce_revision=False)
    newer = observe(world, TRAIN)
    with pytest.raises(UnqualifiedEvidence):
        compile_habit(world, train + newer, validation)
    with pytest.raises(UnqualifiedEvidence):
        cheap_analytic_rule(world, train + newer, validation)


def test_silent_flip_quarantines_with_one_actual_mismatch():
    world, train, validation = evidence("MAJORITY3", 1)
    initial = compile_habit(world, train, validation)
    assert initial is not None
    cue = Cue(*HELDOUT[0])
    action = initial.select(world.session, world.revision, cue)
    world.flip_rule(announce_revision=False)
    mismatch = world.act(cue, action)
    assert not mismatch.success
    world.verify(mismatch)
    next_candidate = initial.reconsider(world, mismatch)
    assert next_candidate.quarantined
    assert next_candidate.select(world.session, world.revision, cue) is None
    assert not initial.quarantined
    # A mismatching action cannot be reported as a successful observation.
    with pytest.raises(UnqualifiedEvidence):
        initial.reconsider(world, replace(mismatch, success=True))


def test_revision_shift_explicit_retraining_world_actions():
    world, train, validation = evidence("AND3", 0)
    old = compile_habit(world, train, validation)
    assert old is not None
    world.flip_rule(announce_revision=True)
    assert all(old.select(world.session, world.revision, Cue(*bits)) is None
               for bits in HELDOUT)
    before = world.count
    next_train = observe(world, TRAIN)
    next_validation = observe(world, VALIDATE)
    assert world.count - before == 10
    renewed = compile_habit(world, next_train, next_validation)
    assert renewed is not None
    assert renewed.rule == Rule("AND3", 1)
    assert all(world.act(Cue(*bits), renewed.select(
        world.session, world.revision, Cue(*bits)
    )).success for bits in HELDOUT)


def test_invalid_rule_cue_and_actions_fail_closed():
    with pytest.raises(UnqualifiedEvidence):
        Cue(1, 2, 0)
    with pytest.raises(UnqualifiedEvidence):
        Cue(True, 0, 1)
    with pytest.raises(UnqualifiedEvidence):
        Rule("unknown", 0)
    with pytest.raises(UnqualifiedEvidence):
        Rule("OR3", True)
    world = ResetWorld("PARITY3", 0)
    with pytest.raises(UnqualifiedEvidence):
        world.act(Cue(0, 0, 0), 2)
    with pytest.raises(UnqualifiedEvidence):
        world.act(Cue(0, 0, 0), True)


def test_public_fixture_reports_actual_measured_result():
    results = run_fixture()
    assert results["classification"] == "CHEAP_RULE_SUFFICIENT_FOR_RELEVANT_HOLDOUT"
    assert results["heldout"] == {
        "no_retention": {"success": 12, "coverage": 24},
        "exact_full_cue": {"success": 0, "coverage": 0},
        "cheap_rule": {"success": 24, "coverage": 24},
        "compiled_habit": {"success": 24, "coverage": 24},
    }
    assert results["world_families"] == 8
    assert results["heldout_contexts_per_world"] == 3
    assert results["train_only_hypothesis_sizes"] == [2] * 8
    assert results["stale_abstentions"] == 24
    assert results["fresh_requalification_actions"] == 80
    assert results["recovered_successes"] == 24
    assert results["silent_mismatch_quarantines"] == 8
