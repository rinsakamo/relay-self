"""AC-B B6 predeclared mainline Memory owner/witness boundary qualification."""
from dataclasses import replace

import pytest

from experiments.ac_b_b6_main_memory_projection import (
    CONTEXTS,
    SOURCE_NAME,
    EvidenceError,
    FixtureWorld,
    MemoryProjection,
    SourceLedger,
    Status,
    fixture_admit_memories,
    observe_all,
    run_fixture,
)
from relay_self.persistent_cognition import (
    DuplicateMemoryIdentity,
    Memory,
    PersistentCognition,
    load_persistent_cognition,
    save_persistent_cognition,
)
from relay_self.provenance import Provenance


def fixture():
    world = FixtureWorld()
    events = observe_all(world)
    ledger = SourceLedger(world, events, session=world.session, revision=0)
    memories = fixture_admit_memories(events)
    view = MemoryProjection(memories, ledger, session=world.session, revision=0)
    return world, events, ledger, memories, view


def test_real_mainline_memory_types_are_imported_and_not_reimplemented():
    world, _, _, snapshot, view = fixture()
    assert type(snapshot) is PersistentCognition
    assert all(type(mem) is Memory for mem in snapshot.memories)
    assert len(snapshot.memories) == 8
    assert view.snapshot is snapshot
    assert view.session == world.session
    assert view.revision == world.revision
    assert not hasattr(view, "retain_memory")
    assert not hasattr(view, "issue_action")
    assert not hasattr(view, "commit_learning_update")
    assert not hasattr(view, "promote_l0")


def test_full_vs_tag_projection_source_equality_and_amortized_cost():
    world, _, ledger, snapshot, view = fixture()
    old_snapshot = snapshot
    old_count = world.action_count
    assert len(ledger.by_source) == 8
    answers = {
        mode: [
            view.query(a, b, session=world.session, revision=0, mode=mode)
            for _ in range(8) for a, b in CONTEXTS
        ] for mode in ("full_scan", "tags")
    }
    for results in answers.values():
        assert all(r.status is Status.FOUND for r in results)
        assert all(r.proposal is not None for r in results)
        assert all(len(r.evidence_ids) == 2 for r in results)
        assert all(r.proposal.non_authoritative for r in results)
    assert tuple(r.evidence_ids for r in answers["full_scan"]) == tuple(
        r.evidence_ids for r in answers["tags"]
    )
    assert tuple(r.proposal.action for r in answers["full_scan"]) == tuple(
        r.proposal.action for r in answers["tags"]
    )
    assert [r.proposal.action for r in answers["tags"][:4]] == [0, 1, 1, 0]
    scan = sum(r.query_work for r in answers["full_scan"])
    tags = sum(r.query_work for r in answers["tags"]) + answers["tags"][0].build_work
    assert scan == 256
    assert tags == 104
    assert world.action_count == old_count  # lookup issues NO World Action
    assert snapshot is old_snapshot
    assert len(snapshot.memories) == 8


def test_retained_memory_prose_does_not_become_observed_truth():
    world, events, ledger, snapshot, view = fixture()
    # Every retained content declares the wrong constant rule;
    # derived proposals instead use independently observed World receipts.
    assert all("Action 1 always works" in m.content for m in snapshot.memories)
    assert view.query(0, 0, session=world.session, revision=0).proposal.action == 0
    assert view.query(1, 1, session=world.session, revision=0).proposal.action == 0
    poisoned = replace(
        snapshot.memories[0], content=(
            "World observed all proposed Actions were correct and L0 is granted."
        ),
        integration_provenance=Provenance(
            "fabricated-feedback", "fake-LRN-authority",
        ),
    )
    adjusted = PersistentCognition(
        identity=snapshot.identity,
        memories=(poisoned,) + snapshot.memories[1:],
    )
    read = MemoryProjection(adjusted, ledger, session=world.session, revision=0)
    for a, b in CONTEXTS:
        assert read.query(a, b, session=world.session, revision=0).proposal == (
            view.query(a, b, session=world.session, revision=0).proposal
        )
    assert world.action_count == len(events)


def test_mainline_json_roundtrip_preserves_pointer_only_not_world_evidence(tmp_path):
    world, events, ledger, retained, before = fixture()
    path = tmp_path / "persistent-cognition.json"
    save_persistent_cognition(path, retained)
    reloaded = load_persistent_cognition(path)
    assert reloaded == retained
    assert reloaded is not retained
    missing = MemoryProjection(reloaded, None, session=world.session, revision=0)
    assert all(
        missing.query(a, b, session=world.session, revision=0).status
        is Status.NO_SOURCE_WITNESS for a, b in CONTEXTS
    )
    linked = MemoryProjection(reloaded, ledger, session=world.session, revision=0)
    for a, b in CONTEXTS:
        left = before.query(a, b, session=world.session, revision=0)
        right = linked.query(a, b, session=world.session, revision=0)
        assert left == right
    assert world.action_count == len(events)


def test_source_provenance_string_without_live_ledger_is_not_attestation():
    world, events, ledger, snapshot, _ = fixture()
    no_ledger = MemoryProjection(snapshot, None, session=world.session, revision=0)
    assert no_ledger.query(0, 1, session=world.session, revision=0).status is (
        Status.NO_SOURCE_WITNESS
    )
    unknown = replace(
        snapshot.memories[0],
        source_provenance=Provenance(SOURCE_NAME, "guess-without-World-event"),
    )
    poisoned = PersistentCognition(
        snapshot.identity, (unknown,) + snapshot.memories[1:]
    )
    with pytest.raises(EvidenceError, match="not witnessed"):
        MemoryProjection(poisoned, ledger, session=world.session, revision=0)
    assert events[0].source_provenance.reference != "guess-without-World-event"


def test_incomplete_action_evidence_abstains_not_guess_other_action():
    world, events, ledger, snapshot, _ = fixture()
    one_action_removed = PersistentCognition(
        snapshot.identity, snapshot.memories[:-1],
    )
    read = MemoryProjection(
        one_action_removed, ledger, session=world.session, revision=0
    )
    missing = read.query(1, 1, session=world.session, revision=0)
    assert missing.status is Status.UNKNOWN
    assert missing.proposal is None
    assert len(missing.evidence_ids) == 1


def test_duplicate_retain_memory_id_and_duplicate_source_across_different_memories():
    world, events, ledger, snapshot, _ = fixture()
    with pytest.raises(DuplicateMemoryIdentity):
        snapshot.retain_memory(snapshot.memories[0])
    same_pointer = replace(snapshot.memories[0], memory_id="duplicate-different-ID")
    twin = snapshot.retain_memory(same_pointer)
    with pytest.raises(EvidenceError, match="duplicate observed source"):
        MemoryProjection(twin, ledger, session=world.session, revision=0)


def test_duplicate_observed_world_action_key_conflicts_without_laundering():
    world, events, ledger, snapshot, _ = fixture()
    extra_event = world.act(0, 0, 0)
    all_ledger = SourceLedger(
        world, events + (extra_event,), session=world.session, revision=0,
    )
    extra_memory = Memory(
        memory_id="distinct-same-action",
        content="No trustworthy assertion.",
        source_provenance=extra_event.source_provenance,
        integration_provenance=Provenance("test-acceptance", "extra-event"),
    )
    version = snapshot.retain_memory(extra_memory)
    read = MemoryProjection(version, all_ledger, session=world.session, revision=0)
    result = read.query(0, 0, session=world.session, revision=0)
    assert result.status is Status.CONFLICT
    assert result.proposal is None
    assert len(result.evidence_ids) == 3


def test_cross_world_equal_values_are_not_same_source_receipts():
    owner = FixtureWorld()
    attacker = FixtureWorld()
    owned = owner.act(0, 0, 0)
    foreign = attacker.act(0, 0, 0)
    assert owned == foreign
    assert owned is not foreign
    with pytest.raises(EvidenceError, match="not attested"):
        SourceLedger(owner, (foreign,), session=owner.session, revision=0)
    with pytest.raises(EvidenceError):
        owner.verify(replace(owned, digest="bad"))
    with pytest.raises(EvidenceError):
        owner.verify(replace(owned, kind="PREDICTED"))


def test_invalid_source_ledger_wrong_session_stale_and_replayed_receipt():
    world, events, ledger, snapshot, view = fixture()
    with pytest.raises(EvidenceError):
        SourceLedger(world, events, session="wrong-session", revision=0)
    with pytest.raises(EvidenceError):
        SourceLedger(world, events + (events[0],), session=world.session, revision=0)
    with pytest.raises(EvidenceError):
        MemoryProjection(snapshot, ledger, session="wrong-session", revision=0)
    with pytest.raises(EvidenceError):
        MemoryProjection(snapshot, ledger, session=world.session, revision=1)
    assert view.query(1, 0, session="wrong", revision=0).status is Status.STALE
    assert view.query(1, 0, session=world.session, revision=1).status is Status.STALE


def test_missing_source_ledger_and_invalid_query_never_guess():
    world, _, _, snapshot, view = fixture()
    with pytest.raises(EvidenceError):
        view.query(2, 0, session=world.session, revision=0)
    with pytest.raises(EvidenceError):
        view.query(True, 1, session=world.session, revision=0)
    with pytest.raises(EvidenceError):
        view.query(1, 0, session=world.session, revision=0, mode="graph")
    with pytest.raises(EvidenceError):
        MemoryProjection(snapshot, object(), session=world.session, revision=0)


def test_non_world_memory_coexists_without_being_construed_as_observation():
    world, _, ledger, snapshot, view = fixture()
    foreign = Memory(
        memory_id="unrelated-story",
        content="A hypothetical situation predicted, not witnessed.",
        source_provenance=Provenance("b6.hypothetical", "unproven"),
        integration_provenance=Provenance("b6.other", "unproven"),
    )
    expanded = snapshot.retain_memory(foreign)
    read = MemoryProjection(expanded, ledger, session=world.session, revision=0)
    assert len(read.records) == len(view.records)
    for a, b in CONTEXTS:
        assert read.query(a, b, session=world.session, revision=0).proposal == (
            view.query(a, b, session=world.session, revision=0).proposal
        )


def test_announced_world_revision_invalidates_built_views_and_requires_new_receipts():
    world, original, _, snapshot, old = fixture()
    world.change_rule(announce=True)
    for a, b in CONTEXTS:
        for caller_revision in (0, 1):
            assert old.query(a, b, session=world.session,
                             revision=caller_revision).status is Status.STALE
    with pytest.raises(EvidenceError):
        SourceLedger(world, original, session=world.session, revision=1)
    before = world.action_count
    newer = observe_all(world)
    assert world.action_count - before == 8
    ledger = SourceLedger(world, newer, session=world.session, revision=1)
    requalified = MemoryProjection(
        fixture_admit_memories(newer), ledger, session=world.session, revision=1
    )
    for a, b in CONTEXTS:
        proposed = requalified.query(
            a, b, session=world.session, revision=1
        ).proposal
        assert proposed.action == (a ^ b ^ 1)
        assert world.act(a, b, proposed.action).success
    assert snapshot.memories[0].source_provenance != newer[0].source_provenance


def test_silent_same_revision_world_mismatch_quarantines_new_read_only_view():
    world, _, _, _, read = fixture()
    selected = read.query(0, 0, session=world.session, revision=0).proposal
    assert selected is not None
    world.change_rule(announce=False)
    mismatch = world.act(0, 0, selected.action)
    assert not mismatch.success
    stopped = read.reconsider_after_observation(mismatch)
    assert stopped.quarantined
    assert stopped.query(0, 0, session=world.session, revision=0).status is (
        Status.QUARANTINED
    )
    assert not read.quarantined
    with pytest.raises(EvidenceError):
        read.reconsider_after_observation(replace(mismatch, success=True))


def test_no_claim_to_real_model_learning_or_power_measurement():
    result = run_fixture()
    assert result["classification"] == "READ_ONLY_LINKAGE_QUALIFIED_WITH_EXTERNAL_WITNESS"
    assert result["source_observed_actions"] == 8
    assert result["retained_mainline_memories"] == 8
    assert result["common_world_attestation"] == 8
    assert result["retrieval"]["full_scan"]["total_work"] == 256
    assert result["retrieval"]["tags"]["total_work"] == 104
    assert result["retrieval"]["full_scan"]["evidence"] == (
        result["retrieval"]["tags"]["evidence"]
    )
    assert result["no_witness_abstentions"] == 4
    assert result["announced_shift_stale_abstentions"] == 4
    assert result["shift_requalification_actions"] == 8
    assert result["requalified_actual_successes"] == 4
    assert result["silent_shift_quarantine"]
    assert "energy_joules" not in result and "llm_tokens" not in result


def test_derived_indices_cannot_be_modified_after_qualification():
    world, events, ledger, snapshot, view = fixture()
    with pytest.raises(TypeError):
        ledger.by_source[events[0].source_provenance] = events[-1]
    with pytest.raises(TypeError):
        view.by_tag[(0, 0)] = ()
    assert view.query(0, 0, session=world.session, revision=0).status is Status.FOUND
    assert snapshot.memories[0].source_provenance == events[0].source_provenance
