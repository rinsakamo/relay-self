"""AC-B B5 prospective relational retrieval checks: Grand Null and fail-closed."""
from dataclasses import replace

import pytest

from experiments.ac_b_b5_relational_retrieval import (
    ACTIONS,
    MODES,
    STATES,
    Claim,
    ClaimKind,
    Corpus,
    EvidenceError,
    Query,
    ReadOnlyIndex,
    ResetWorld,
    Status,
    evaluate,
    make_claims,
    queries,
    run_fixture,
    sample_world,
)


def qualified():
    world = ResetWorld()
    receipts = sample_world(world)
    claims = make_claims()
    corpus = Corpus(
        world, receipts, claims, session=world.session, revision=world.revision
    )
    return world, receipts, claims, corpus


def test_frozen_sources_queries_and_claim_overlay():
    world, receipts, claims, corpus = qualified()
    assert len(receipts) == STATES * len(ACTIONS) == 32
    assert len(claims) == 64
    assert corpus.common_validation_work == 96
    assert len(queries()) == 32
    assert len(set((q.start, q.actions) for q in queries())) == 32
    assert set(c.kind for c in claims) == {
        ClaimKind.ASSOCIATED_WITH, ClaimKind.CAUSAL_HYPOTHESIS
    }
    assert len(corpus.validated) == 32
    assert world.action_count == 32
    assert all(r.kind == "OBSERVED_TRANSITION" for r in receipts)


def test_each_method_uses_same_source_witnesses_and_correct_two_hop_world():
    world, receipts, _, corpus = qualified()
    views = {mode: ReadOnlyIndex(corpus, mode) for mode in MODES}
    for query in queries():
        outcomes = {
            mode: view.query(query, session=world.session, revision=0)
            for mode, view in views.items()
        }
        assert all(x.status is Status.FOUND for x in outcomes.values())
        assert len(set(x.final_state for x in outcomes.values())) == 1
        assert len(set(x.receipt_ids for x in outcomes.values())) == 1
        assert len(outcomes["tags"].receipt_ids) == 2
        assert all(witness in {r.receipt_id for r in receipts}
                   for witness in outcomes["tags"].receipt_ids)
        actual = world.rollout(query.start, query.actions)
        assert actual[0].target_state == actual[1].source_state
        assert outcomes["tags"].final_state == actual[-1].target_state
        assert all(actual_step.receipt_id not in {
            r.receipt_id for r in receipts
        } for actual_step in actual)
    assert world.action_count == 32 + 64


def test_cost_includes_build_and_strong_index_comparators():
    world, _, _, corpus = qualified()
    output = evaluate(world, corpus)
    assert output["classification"] == "GRAPH_NOT_JUSTIFIED"
    assert output["common_validation_work"] == 96
    assert output["equal_provenance_paths"]
    assert output["world_rollout_actions"] == 64
    totals = output["arm_results"]
    assert all(totals[m]["correct"] == 32 and totals[m]["found"] == 32
               and totals[m]["wrong"] == 0 and totals[m]["unknown"] == 0
               for m in MODES)
    assert totals["full_scan"]["total_work"] == 2048
    assert totals["tags"]["total_work"] == 96
    assert totals["flat"]["total_work"] == 96
    assert totals["typed_graph"]["total_work"] > 96
    assert totals["typed_graph"]["lookup_work"] > totals["tags"]["lookup_work"]


def test_untrusted_relation_claims_are_not_laundered_as_world_outcomes():
    world = ResetWorld()
    claims = make_claims()
    corpus = Corpus(world, (), claims, session=world.session, revision=0)
    q = Query(0, (0, 1))
    for mode in MODES:
        result = ReadOnlyIndex(corpus, mode).query(
            q, session=world.session, revision=0
        )
        assert result.status is Status.UNKNOWN
        assert result.final_state is None
        assert result.receipt_ids == ()
    with pytest.raises(EvidenceError):
        Claim("made_up_observation", "OBSERVED_TRANSITION", 0, 0, 1)
    with pytest.raises(EvidenceError):
        Claim("out_of_range", ClaimKind.CAUSAL_HYPOTHESIS, 0, 0, STATES)


def test_missing_second_hop_returns_unknown_without_fabrication():
    world = ResetWorld()
    only_first = (world.act(0, 0),)
    corpus = Corpus(world, only_first, make_claims(),
                    session=world.session, revision=0)
    for mode in MODES:
        r = ReadOnlyIndex(corpus, mode).query(
            Query(0, (0, 0)), session=world.session, revision=0
        )
        assert r.status is Status.UNKNOWN
        assert r.final_state is None
        assert r.receipt_ids == (only_first[0].receipt_id,)


def test_claims_do_not_create_alternate_directional_shortcuts():
    world, _, _, corpus = qualified()
    assert any(claim.target_state != corpus.validated[
        (claim.source_state, claim.action)
    ].target_state for claim in corpus.claims)
    first = ReadOnlyIndex(corpus, "typed_graph").query(
        Query(0, (0, 1)), session=world.session, revision=0
    )
    assert first.status is Status.FOUND
    assert first.final_state == (5 * (5 * 0 + 1) + 1 + 3) % 16
    assert all(e.startswith(world.session + ":step:")
               for e in first.receipt_ids)


def test_wrong_world_instance_cross_session_and_forged_receipt_rejected():
    world, receipts, claims, _ = qualified()
    second_world = ResetWorld()
    second_receipts = sample_world(second_world)
    assert receipts[0] == second_receipts[0]  # equal VALUE, not same source
    assert receipts[0] is not second_receipts[0]
    with pytest.raises(EvidenceError):
        Corpus(world, second_receipts, claims, session=world.session, revision=0)
    with pytest.raises(EvidenceError):
        Corpus(world, receipts, claims, session="unrelated", revision=0)
    with pytest.raises(EvidenceError):
        Corpus(world, (replace(receipts[0], digest="forged"),),
               claims, session=world.session, revision=0)
    with pytest.raises(EvidenceError):
        Corpus(world, (replace(receipts[0], kind="CAUSAL_HYPOTHESIS"),),
               claims, session=world.session, revision=0)


def test_duplicate_receipts_and_duplicate_claim_ids_fail_closed():
    world, receipts, claims, _ = qualified()
    with pytest.raises(EvidenceError):
        Corpus(world, receipts + (receipts[0],),
               claims, session=world.session, revision=0)
    with pytest.raises(EvidenceError):
        Corpus(world, receipts, claims + (claims[0],),
               session=world.session, revision=0)
    # Even a distinct trusted receipt for the same (state,action) key does
    # not silently replace or strengthen a previous observation.
    repeated = world.act(0, 0)
    with pytest.raises(EvidenceError):
        Corpus(world, receipts + (repeated,),
               claims, session=world.session, revision=0)


def test_stale_after_construction_even_if_caller_passes_old_revision():
    world, _, _, corpus = qualified()
    views = [ReadOnlyIndex(corpus, m) for m in MODES]
    world.change_regime(announce=True)
    for view in views:
        assert view.query(queries()[0], session=world.session, revision=0).status is Status.STALE
        assert view.query(queries()[0], session=world.session, revision=1).status is Status.STALE
    with pytest.raises(EvidenceError):
        Corpus(world, corpus.receipts, corpus.claims,
               session=world.session, revision=1)


def test_silent_shift_real_conflict_and_local_quarantine():
    world, receipts, claims, corpus = qualified()
    world.change_regime(announce=False)
    contradictory = world.act(0, 0)
    assert contradictory.target_state != corpus.validated[(0, 0)].target_state
    with pytest.raises(EvidenceError):
        Corpus(world, receipts + (contradictory,), claims,
               session=world.session, revision=0)
    for mode in MODES:
        original = ReadOnlyIndex(corpus, mode)
        stopped = original.reconsider_after_observation(contradictory)
        assert stopped.quarantined
        assert stopped.query(queries()[0], session=world.session,
                             revision=0).status is Status.QUARANTINED
        assert not original.quarantined
        with pytest.raises(EvidenceError):
            original.reconsider_after_observation(
                replace(contradictory, target_state=0)
            )


def test_invalid_query_and_revision_fail_closed():
    world, _, _, corpus = qualified()
    for value in (-1, STATES, True, 2.0):
        with pytest.raises(EvidenceError):
            Query(value, (0, 0))
    for actions in ((0,), (0, 2), (0, True), [0, 1]):
        with pytest.raises(EvidenceError):
            Query(0, actions)
    with pytest.raises(EvidenceError):
        ReadOnlyIndex(corpus, "unknown")
    with pytest.raises(EvidenceError):
        ReadOnlyIndex(corpus, "tags").query("not_query", session=world.session,
                                           revision=world.revision)
    assert ReadOnlyIndex(corpus, "tags").query(
        queries()[0], session="other", revision=world.revision
    ).status is Status.STALE


def test_b5_announced_shift_recovery_and_silent_quarantine_in_full_fixture():
    result = run_fixture()
    initial, recovered = result["initial"], result["recovery"]
    assert result["qualified_one_step_receipts"] == 32
    assert result["claim_edge_count"] == 64
    assert result["announced_shift_stale_views"] == 4
    assert result["shift_training_actions"] == 32
    assert result["silent_shift_quarantined_views"] == 4
    for run in (initial, recovered):
        assert run["classification"] == "GRAPH_NOT_JUSTIFIED"
        assert run["equal_provenance_paths"]
        assert run["queries"] == 32
        assert run["world_rollout_actions"] == 64
        assert run["arm_results"]["flat"]["correct"] == 32
        assert run["arm_results"]["tags"]["total_work"] == 96
        assert run["arm_results"]["typed_graph"]["total_work"] > 96
