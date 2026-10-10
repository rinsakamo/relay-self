"""Predeclared AC-B offline B1/B2 gates. No network, model or Minecraft."""
from dataclasses import replace

import pytest

from experiments.ac_b_memory_distillation import (
    Cue,
    DeterministicWorld,
    EdgeKind,
    EvidenceError,
    MemoryView,
    RetrievalStatus,
    TypedEdge,
    apply_cheap,
    cheap_rule,
    distill,
    observe_split,
    run_fixture,
)


def fixture():
    world = DeterministicWorld()
    train, valid = observe_split(world, 0), observe_split(world, 1)
    return world, train, valid


def test_world_outcomes_are_observed_not_presumed():
    world = DeterministicWorld()
    true = world.act(Cue(1, 0, 0), 1)
    false = world.act(Cue(1, 0, 0), 0)
    assert true.success and not false.success
    assert true.kind == false.kind == "OBSERVED"
    assert true.outcome_ref != false.outcome_ref
    world.verify(true)
    with pytest.raises(EvidenceError):
        world.verify(replace(true, success=False))
    with pytest.raises(EvidenceError):
        world.verify(replace(true, kind="PREDICTED"))
    with pytest.raises(EvidenceError):
        world.verify(replace(true, evidence_digest="forged"))
    with pytest.raises(EvidenceError):
        cheap_rule(world, (replace(true, success=False),))


def test_retrieval_same_admissible_evidence_and_amortized_cost():
    world, train, valid = fixture()
    edges = tuple(
        TypedEdge(train[i].episode_id, train[i + 1].episode_id,
                  EdgeKind.ASSOCIATED_WITH)
        for i in range(0, 8, 2)
    )
    view = MemoryView(world, train + valid, session=world.session,
                      revision=0, edges=edges)
    result = {
        mode: tuple(view.search(a, b, mode) for a in (0, 1) for b in (0, 1))
        for mode in ("full_scan", "tags", "tags_typed_graph")
    }
    assert all(x.status is RetrievalStatus.FOUND for results in result.values()
               for x in results)
    assert tuple(x.episode_ids for x in result["full_scan"]) == tuple(
        x.episode_ids for x in result["tags"]
    ) == tuple(x.episode_ids for x in result["tags_typed_graph"])
    work = {
        name: sum(x.query_work for x in values) + values[0].build_work
        for name, values in result.items()
    }
    assert work["tags"] < work["full_scan"]
    assert work["tags_typed_graph"] > work["tags"]


def test_graph_edges_cannot_launder_hypothesis_into_world_evidence():
    world, train, _ = fixture()
    hypothesis = TypedEdge(train[0].episode_id, train[2].episode_id,
                           EdgeKind.CAUSAL_HYPOTHESIS)
    view = MemoryView(world, train, session=world.session, revision=0,
                      edges=(hypothesis,))
    assert view.search(0, 0, "tags").episode_ids == view.search(
        0, 0, "tags_typed_graph"
    ).episode_ids
    with pytest.raises(EvidenceError):
        MemoryView(world, train, session=world.session, revision=0,
                   edges=(TypedEdge(train[0].episode_id, "fake",
                                    EdgeKind.OBSERVED_TRANSITION),))
    with pytest.raises(EvidenceError):
        MemoryView(world, train, session=world.session, revision=0,
                   edges=(TypedEdge(train[1].episode_id, train[0].episode_id,
                                    EdgeKind.OBSERVED_TRANSITION),))


def test_wrong_session_stale_duplicate_unqualified_and_empty():
    world, train, valid = fixture()
    with pytest.raises(EvidenceError):
        MemoryView(world, train, session="other-session", revision=0)
    with pytest.raises(EvidenceError):
        MemoryView(world, train + (train[0],), session=world.session, revision=0)
    with pytest.raises(EvidenceError):
        MemoryView(world, train + (replace(train[0], action=1),),
                   session=world.session, revision=0)
    empty = MemoryView(world, (), session=world.session, revision=0)
    assert empty.search(0, 1, "tags").status is RetrievalStatus.UNKNOWN
    with pytest.raises(EvidenceError):
        empty.search(0, 1, "UNDECLARED")
    world.change_rule(announce=True)
    with pytest.raises(EvidenceError):
        MemoryView(world, valid, session=world.session, revision=1)


def test_real_same_revision_contradictions_fail_closed():
    world = DeterministicWorld()
    first = world.act(Cue(0, 0, 0), 0)
    world.change_rule(announce=False)
    second = world.act(Cue(0, 0, 0), 0)
    view = MemoryView(world, (first, second), session=world.session, revision=0)
    for mode in ("full_scan", "tags", "tags_typed_graph"):
        assert view.search(0, 0, mode).status is RetrievalStatus.CONFLICT


def test_distillation_requires_independent_qualified_outcomes():
    world, train, valid = fixture()
    policy = distill(world, train, valid, session=world.session, revision=0)
    assert len(policy.training_ids) == 8
    assert len(policy.validation_ids) == 8
    assert len(policy.mapping) == 4
    with pytest.raises(EvidenceError):
        distill(world, train, train, session=world.session, revision=0)
    with pytest.raises(EvidenceError):
        cheap_rule(world, train[:-1])
    with pytest.raises(EvidenceError):
        distill(world, train[:-1], valid, session=world.session, revision=0)
    with pytest.raises(EvidenceError):
        distill(world, train, valid[:-1] + (train[0],),
                session=world.session, revision=0)
    with pytest.raises(EvidenceError):
        distill(world, train, valid, session="wrong", revision=0)
    with pytest.raises(EvidenceError):
        distill(world, train, valid, session=world.session, revision=1)


def test_no_unobserved_action_assumption_or_l2_text_only_qualification():
    world, train, valid = fixture()
    counterfeit = replace(train[0], success=not train[0].success)
    with pytest.raises(EvidenceError):
        distill(world, (counterfeit,) + train[1:], valid,
                session=world.session, revision=0)
    world.change_rule(announce=False)
    contradictory_validation = observe_split(world, 1)
    with pytest.raises(EvidenceError):
        distill(world, train, contradictory_validation,
                session=world.session, revision=0)


def test_cheap_rule_matches_conditional_habit_on_unseen_full_cues():
    world, train, valid = fixture()
    candidate = distill(world, train, valid, session=world.session, revision=0)
    rule = cheap_rule(world, train)
    assert rule == ("xor", 0)
    for a in (0, 1):
        for b in (0, 1):
            query = Cue(a, b, 2)
            assert all(ep.cue != query for ep in train + valid)
            action = candidate.select(session=world.session, revision=0, cue=query)
            assert action == apply_cheap(rule, query)
            assert world.act(query, action).success
    assert candidate.select(session="other", revision=0, cue=Cue(0, 0, 2)) is None
    assert candidate.select(session=world.session, revision=1,
                            cue=Cue(0, 0, 2)) is None


def test_shift_reescalation_and_requalification_without_promoting_l0():
    world, train, valid = fixture()
    old = distill(world, train, valid, session=world.session, revision=0)
    world.change_rule(announce=True)
    assert old.select(session=world.session, revision=world.revision,
                      cue=Cue(1, 1, 2)) is None
    newer = distill(world, observe_split(world, 0), observe_split(world, 1),
                    session=world.session, revision=world.revision)
    assert newer.revision == 1
    assert newer.mapping != old.mapping
    assert all(world.act(Cue(a, b, 3), newer.select(
        session=world.session, revision=1, cue=Cue(a, b, 3)
    )).success for a in (0, 1) for b in (0, 1))
    assert not hasattr(newer, "issue_action")
    assert not hasattr(newer, "promote_l0")


def test_silent_regime_shift_requires_mismatch_quarantine():
    world, train, valid = fixture()
    candidate = distill(world, train, valid, session=world.session, revision=0)
    cue = Cue(0, 0, 2)
    old_choice = candidate.select(session=world.session, revision=0, cue=cue)
    world.change_rule(announce=False)
    mismatch = world.act(cue, old_choice)
    assert not mismatch.success
    stopped = candidate.reconsider_after_outcome(world, mismatch)
    assert stopped.quarantined
    assert stopped.select(session=world.session, revision=0, cue=cue) is None
    assert not candidate.quarantined  # immutable; no retroactive mutation


def test_predeclared_outcomes_and_grand_null():
    result = run_fixture()
    assert result["classification"] == "INDEX_ONLY_GAIN"
    assert result["heldout_4"] == {
        "no_retention": 2, "exact_case": 0, "cheap_rule": 4,
        "habit": 4, "expensive_probe": 4,
    }
    assert result["expensive_extra_probes"] == 6
    assert result["stale_abstentions_4"] == 4
    assert result["shift_recovery_training_validation_actions"] == 16
    assert result["shift_recovered_heldout_4"] == 4
    assert not result["graph_incremental_gain"]
    assert not result["habit_incremental_gain_over_cheap_rule"]


def test_identical_receipts_from_different_world_instances_do_not_cross_attest():
    # Same session/sequence/context/outcome/digest is NOT same source witness.
    owner = DeterministicWorld()
    foreign = DeterministicWorld()
    own = owner.act(Cue(0, 0, 0), 0)
    cross = foreign.act(Cue(0, 0, 0), 0)
    assert own == cross  # value equality exposes the former provenance loophole
    assert own is not cross
    owner.verify(own)
    with pytest.raises(EvidenceError):
        owner.verify(cross)
    with pytest.raises(EvidenceError):
        MemoryView(owner, (cross,), session=owner.session, revision=0)
