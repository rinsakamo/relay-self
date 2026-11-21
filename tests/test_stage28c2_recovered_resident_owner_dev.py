"""Stage28c2a: strict original A/B offline reattachment (no real World)."""
from __future__ import annotations

import pytest

from relay_self.checkpointed_cognitive_runtime_dev import (
    LiveCognitionCheckpointError,
)
from relay_self.cognitive_minimal_dev import initial_patterns
from relay_self.persistent_cognition import (
    Memory,
    save_persistent_cognition,
)
from relay_self.physical_issue_admission_dev import PhysicalIssueFenceError
from relay_self.provenance import Provenance
from relay_self.resident_cognitive_work_owner_dev import (
    ResidentCognitiveWorkError,
)
from relay_self.stage28c2_recovered_resident_owner_dev import (
    Stage28c2OwnerHold,
    prepare_recovered_a_b_resident_owners,
)
from test_stage28b_retired_typed_cut_dev import _setup
from test_stage28c1_inert_restore_dev import _prepare, _source


def _context(tmp_path, monkeypatch):
    generation = _source(tmp_path, monkeypatch)
    restored = tmp_path / "new-fork"
    prepared = _prepare(generation, restored)
    return generation, restored, prepared


def _reattach(generation, restored, prepared, **overrides):
    args = {
        "expected_world_id": "world-1",
        "expected_source_branch_id": "source",
        "expected_committed_sha256": prepared.source_commit_sha256,
        "expected_fork_branch_id": prepared.restored_branch_id,
    }
    args.update(overrides)
    return prepare_recovered_a_b_resident_owners(
        generation, restored, **args,
    )


def test_stage28c2a_real_schema_original_a_b_preserved_offline_and_no_issue(
    tmp_path, monkeypatch,
):
    generation, restored, prepared = _context(tmp_path, monkeypatch)
    recovered = _reattach(generation, restored, prepared)
    assert tuple(sorted(recovered.owners)) == ("A", "B")
    assert recovered.receipt.generation_id == "g-000000000000"
    assert recovered.receipt.fork_branch_id == prepared.restored_branch_id
    assert recovered.receipt.source_cut_ticks == (("A", 105), ("B", 105))
    assert len(recovered.receipt.verified_self_file_sha256) == 6
    assert recovered.physical.all_residents_offline
    assert recovered.physical.active_action_ids == ()
    for sid in ("A", "B"):
        owner = recovered.owners[sid]
        assert owner.retained.identity.self_id == sid
        assert owner.native_session_id == "native-retired-" + sid
        assert owner.last_observed_tick == 105
        assert owner.fresh_native_observation_required
        assert owner.pattern_registry.revision == 0
        # Stage28 must restore original source Registry; never silently
        # fabricate an oxygen pattern during recovery.
        assert owner.pattern_registry == initial_patterns()
        assert owner.cohort is recovered.cognitive_work
        assert not owner.supervisor.open_actions
        with pytest.raises(ResidentCognitiveWorkError, match="not online"):
            recovered.cognitive_work.current_scope(sid)
        with pytest.raises(LiveCognitionCheckpointError, match="fenced"):
            owner.retain_memory(Memory(
                "new", "forbidden offline", Provenance("test", sid),
                Provenance("test", sid),
            ))
        with pytest.raises(LiveCognitionCheckpointError, match="fenced"):
            owner.observe_world_tick(
                session_id=owner.native_session_id, world_tick=500,
            )
    assert recovered.receipt.active_native_rejoined is False
    assert recovered.receipt.real_paper_started is False
    assert recovered.receipt.fresh_worldbody_observed is False
    assert recovered.receipt.old_skill_replayed is False
    assert recovered.receipt.old_l1_decision_reused is False
    assert recovered.receipt.physical_action_issue_authorized is False
    assert recovered.receipt.l1_reevaluation_eligible is False


def test_stage28c2a_preserves_actual_nonempty_original_memory_and_intent(
    tmp_path, monkeypatch,
):
    bridge, paper, store, evidence = _setup(tmp_path, monkeypatch)
    for name in ("world_nether", "world_the_end"):
        dimension = tmp_path / name
        dimension.mkdir()
        (dimension / "region").mkdir()
        (dimension / "region" / "r.0.0.mca").write_bytes(b"saved")
    a = bridge.owners["A"]
    a.retained = a.retained.retain_memory(Memory(
        "original-memory", "saw a tree", Provenance("original", "A"),
        Provenance("original", "A"),
    ))
    save_persistent_cognition(a.files.cognition_file, a.retained)
    a.intent.commit(
        "original-intent", objective="EXPLORE",
        at_ns=1000, provenance=Provenance("original", "A"),
    )
    from relay_self.stage28b_retired_resident_typed_cut_dev import (
        capture_retired_resident_typed_world,
    )

    generation = capture_retired_resident_typed_world(
        bridge=bridge, paper=paper, store=store, evidence_dir=evidence,
    ).generation
    restored = tmp_path / "restored-nonempty"
    prepared = _prepare(generation, restored)
    recovered = _reattach(generation, restored, prepared)
    actual = recovered.owners["A"]
    assert actual.retained == a.retained
    assert actual.intent.events == a.intent.events
    assert len(actual.retained.memories) == 1
    assert actual.intent.current_intent.intent_id == "original-intent"
    assert recovered.physical.all_residents_offline
    with pytest.raises(LiveCognitionCheckpointError):
        actual.commit_intent(
            "another", "EXPLORE", 2000, Provenance("test", "A"),
        )


@pytest.mark.parametrize("failure", [
    "world", "source-branch", "committed", "fork-branch",
    "mutated-a-cognition", "mutated-b-wal", "mutated-a-owner",
])
def test_stage28c2a_refuses_foreign_or_changed_original_state(
    tmp_path, monkeypatch, failure,
):
    generation, restored, prepared = _context(tmp_path, monkeypatch)
    overrides = {}
    if failure == "world":
        overrides["expected_world_id"] = "wrong-world"
    elif failure == "source-branch":
        overrides["expected_source_branch_id"] = "wrong-branch"
    elif failure == "committed":
        overrides["expected_committed_sha256"] = "0" * 64
    elif failure == "fork-branch":
        overrides["expected_fork_branch_id"] = "fork-foreign"
    else:
        sid, file = {
            "mutated-a-cognition": ("A", "cognition.json"),
            "mutated-b-wal": ("B", "physical-wal.json"),
            "mutated-a-owner": ("A", "owner-state.json"),
        }[failure]
        (restored / "selves" / sid / file).write_bytes(b"tampered")
    with pytest.raises(Stage28c2OwnerHold):
        _reattach(generation, restored, prepared, **overrides)


def test_stage28c2a_stale_world_cannot_reuse_duplicate_owner_handles(
    tmp_path, monkeypatch,
):
    generation, restored, prepared = _context(tmp_path, monkeypatch)
    prepared_owners = _reattach(generation, restored, prepared)
    with pytest.raises(ResidentCognitiveWorkError, match="unattached"):
        type(prepared_owners.cognitive_work)(prepared_owners.owners)


def test_observation_only_remains_fenced_after_resident_login(tmp_path, monkeypatch):
    generation, restored, prepared = _context(tmp_path, monkeypatch)
    recovered = _reattach(generation, restored, prepared, observation_only=True)
    recovered.physical.admit_resident_login(
        self_id="A", former_native_session_id="native-retired-A",
        fresh_native_session_id="new-A", source_world_epoch_validated=True,
        physical_wal_file=recovered.owners["A"].files.physical_wal_file,
    )
    assert recovered.physical.resident_states["A"] == "ONLINE"
    with pytest.raises(PhysicalIssueFenceError, match="observation-only"):
        with recovered.physical.lease(
            self_id="A", native_session_id="new-A", action_id="eat",
            effect_family="EAT",
        ):
            pytest.fail("physical action admitted")
    with pytest.raises(PhysicalIssueFenceError, match="observation-only"):
        recovered.physical.require_native_effect(
            self_id="A", native_session_id="new-A", effect="consume_held",
            action_id="eat",
        )
