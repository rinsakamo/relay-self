"""#860: actual existing cognition owners behind an offline multi-Self cut."""
from __future__ import annotations

from pathlib import Path

import pytest

from relay_self.action_supervision import ActionSupervisor
from relay_self.checkpointed_cognitive_runtime_dev import (
    CheckpointedCognitiveOwner,
    CognitionOwnerCohort,
    CognitiveOwnerFiles,
    ExternalPhysicalFence,
    ExternalRejoin,
    LiveCognitionCheckpointError,
    staged_recover_cognition_cohort,
)
from relay_self.cognitive_minimal_dev import (
    Origin,
    PatternKind,
    Predicate,
    SchemaPattern,
    initial_patterns,
)
from relay_self.coordinated_autosave_runtime_dev import (
    AutosaveBarrierError,
    CoordinatedAutosaveRuntime,
    RestartedWorldReceipt,
    StoppedWorldReceipt,
    WorldRuntimeHooks,
)
from relay_self.coordinated_checkpoint_dev import (
    restore_generation,
)
from relay_self.intent import IntentCommitment
from relay_self.persistent_cognition import (
    IdentitySpecification,
    Memory,
    PersistentCognition,
)
from relay_self.physical_action_journal import PhysicalActionJournal
from relay_self.provenance import Provenance
from relay_self.self_owner_checkpoint_dev import PeerDelivery, verify_typed_generation


class RuntimeFixture:
    def __init__(self, tmp_path: Path):
        self.world_dir = tmp_path / "world"
        self.world_dir.mkdir()
        (self.world_dir / "level.dat").write_bytes(b"W100-simulated")
        (self.world_dir / "entities").mkdir()
        (self.world_dir / "entities" / "r.0.0.mca").write_bytes(b"zombie-A-alive")
        self.store = tmp_path / "store"
        self.store.mkdir()
        self.owners = []
        for sid in ("A", "B"):
            root = tmp_path / sid
            root.mkdir()
            wal = root / "physical-wal.json"
            PhysicalActionJournal.create(wal, self_id=sid)
            retained = PersistentCognition(
                IdentitySpecification(
                    sid, ("Identity unchanged across checkpoints.",),
                    Provenance("fixture", sid),
                ),
            )
            owner = CheckpointedCognitiveOwner(
                retained=retained, intent=IntentCommitment(),
                pattern_registry=initial_patterns(),
                native_session_id=f"native-before-{sid}",
                last_observed_tick=100,
                files=CognitiveOwnerFiles(root, root / "cognition.json", wal),
                physical_supervisor=ActionSupervisor(),
            )
            self.owners.append(owner)
        self.events = []
        self.gate_open = True
        self.session_id = "paper-start"
        self.session_sequence = 0
        self.fail_physical = False
        self.fail_rejoin_id = None
        self.external_fence_ref = None

        def external_close():
            self.events.append("external-stop-issue")
            self.gate_open = False
            if self.fail_physical:
                return ExternalPhysicalFence("fence", False, ())
            self.external_fence_ref = "fence-1"
            return ExternalPhysicalFence(self.external_fence_ref, True, ())

        def external_release(ref):
            assert not self.gate_open
            assert ref == self.external_fence_ref
            self.events.append("external-release-issue")
            self.gate_open = True

        def external_native_rejoin(sid, server_session, old):
            self.events.append("native-rejoin:" + sid)
            assert server_session == self.session_id
            assert old
            if self.fail_rejoin_id == sid:
                return ExternalRejoin("same-invalid", False, True, True)
            return ExternalRejoin(
                f"native-new-{sid}-{server_session}", True, True, True,
            )

        self.cohort = CognitionOwnerCohort(
            owners=tuple(self.owners),
            world_id="world-1", branch_id="source",
            external_close_physical=external_close,
            external_release_physical=external_release,
            external_native_rejoin=external_native_rejoin,
        )

        def stop_world():
            assert not self.gate_open
            self.events.append("stop-world")
            return StoppedWorldReceipt(
                "world-1", "source", self.session_id, 110,
                "test:world-tick", "test:clean-world-stop", 0, True,
            )

        def restart_world():
            assert not self.gate_open
            self.events.append("start-world")
            self.session_sequence += 1
            self.session_id = f"paper-new-{self.session_sequence}"
            return RestartedWorldReceipt(
                "world-1", "source", self.session_id, True,
            )

        self.runtime = CoordinatedAutosaveRuntime(
            source_world=self.world_dir,
            store=self.store,
            world_id="world-1",
            branch_id="source",
            participants=self.cohort.participant_hooks(),
            world=WorldRuntimeHooks(stop_world, restart_world),
            admission=self.cohort.admission_hooks(),
            strict_typed_owner_cut=True,
        )

    def baseline(self):
        for owner in self.owners:
            owner.commit_intent(
                "goal-" + owner.self_id, "DEFEND_SELF", 1000,
                Provenance("intent", owner.self_id),
            )
            owner.start_skill(
                "skill-" + owner.self_id, "ATTACK", 1010,
                Provenance("skill", owner.self_id),
            )
            owner.observe_world_tick(
                session_id=owner.native_session_id,
                world_tick=105,
            )
            owner.retain_memory(Memory(
                "pre-" + owner.self_id, "W100 Zombie was alive",
                Provenance("observation", owner.self_id),
                Provenance("integration", owner.self_id),
            ))
        self.cohort.delivered(PeerDelivery(
            "msg-pre", "A", "B", 101, 102, "payload:pre",
        ))


def test_existing_a_b_cognitive_owners_snapshot_and_whole_rollback(tmp_path):
    f = RuntimeFixture(tmp_path)
    f.baseline()
    first = f.runtime.run_if_due(0.0)
    assert first is not None and first.typed_owner_cut_validated
    assert len(verify_typed_generation(first.generation)) == 2
    assert first.saved_self_ids == ("A", "B")
    assert f.gate_open
    assert f.events == [
        "external-stop-issue", "stop-world", "start-world",
        "native-rejoin:A", "native-rejoin:B", "external-release-issue",
    ]
    assert f.runtime.run_if_due(59.99) is None

    (f.world_dir / "entities" / "r.0.0.mca").write_bytes(b"zombie-dead-later")
    # Actual old mutable owners learn and communicate AFTER the cut.
    for owner in f.owners:
        owner.observe_world_tick(session_id=owner.native_session_id, world_tick=120)
        owner.retain_memory(Memory(
            "future-" + owner.self_id, "Zombie was killed after autosave",
            Provenance("future", owner.self_id),
            Provenance("integration-future", owner.self_id),
        ))
    f.cohort.delivered(PeerDelivery(
        "msg-future", "B", "A", 118, 119, "payload:future",
    ))
    a = f.owners[0]
    a.accept_pattern(SchemaPattern(
        "future-exploration", 1, "homeostatic", PatternKind.GOAL,
        Predicate.HUNGRY, "HUNGER_RELIEF", "EAT", 1, "FOOD",
        Origin.LEARNED, Provenance("learned", "after-g0"),
    ), frozenset({("EAT", 1)}))
    assert a.pattern_registry.revision == 1

    # Recovery from the previously committed W100 checkpoint, not new history.
    restored_dir = tmp_path / "new-world-branch"
    receipt = restore_generation(first.generation, restored_dir, restore_id="rollback-A-B")
    recovered = staged_recover_cognition_cohort(first.generation, restored_dir)
    assert receipt["replay_performed"] is False
    assert receipt["physical_action_issue_authorized"] is False
    assert (restored_dir / "world" / "entities" / "r.0.0.mca").read_bytes() == (
        b"zombie-A-alive"
    )
    assert len(recovered) == 2
    for result in recovered:
        assert result.semantic.intent.current_intent.intent_id == "goal-" + result.self_id
        assert [m.memory_id for m in result.retained.memories] == ["pre-" + result.self_id]
        assert result.semantic.pattern_registry.revision == 0
        assert [p.message_id for p in result.semantic.cut.peer_deliveries] == ["msg-pre"]
        assert not result.native_session_bound
        assert result.fresh_worldbody_required
        assert not result.issue_authorized


def test_old_native_session_is_fenced_after_successful_restart(tmp_path):
    f = RuntimeFixture(tmp_path)
    f.baseline()
    assert f.runtime.run_if_due(0.0)
    with pytest.raises(LiveCognitionCheckpointError, match="old session"):
        f.owners[0].observe_world_tick(session_id="native-before-A", world_tick=111)
    with pytest.raises(LiveCognitionCheckpointError, match="fresh native WorldBody"):
        f.owners[0].retain_memory(Memory(
            "stale-result", "Old GPU result cannot update the owner",
            Provenance("old-model", "old-session"), Provenance("old", "result"),
        ))
    f.owners[0].observe_world_tick(
        session_id=f.owners[0].native_session_id, world_tick=111,
    )
    f.owners[0].retain_memory(Memory(
        "fresh-result", "Fresh WorldBody session can update owner",
        Provenance("fresh-model", "new-session"), Provenance("fresh", "result"),
    ))


def test_all_cognitive_mutations_fenced_during_external_checkpoint(tmp_path):
    f = RuntimeFixture(tmp_path)
    f.baseline()
    token = f.cohort.close().token
    with pytest.raises(LiveCognitionCheckpointError, match="fenced"):
        f.owners[0].retain_memory(Memory(
            "forbidden", "This must never be accepted while saving",
            Provenance("bad", "1"), Provenance("bad", "2"),
        ))
    with pytest.raises(LiveCognitionCheckpointError, match="fenced"):
        f.cohort.delivered(PeerDelivery("m-bad", "A", "B", 101, 102, "bad"))
    with pytest.raises(LiveCognitionCheckpointError, match="fenced"):
        f.owners[0].commit_intent("bad", "BAD", 9999, Provenance("bad", "intent"))
    f.cohort.release(token)
    assert f.gate_open


def test_no_external_physical_fence_blocks_all_saves(tmp_path):
    f = RuntimeFixture(tmp_path)
    f.baseline()
    f.fail_physical = True
    with pytest.raises(AutosaveBarrierError, match="admission must remain held"):
        f.runtime.run_if_due(0.0)
    assert f.runtime.held_after_failure
    assert not f.gate_open
    assert not f.runtime.store.joinpath("g-000000000000", "COMMITTED.json").exists()


def test_unqualified_native_rejoin_holds_after_committed_cut(tmp_path):
    f = RuntimeFixture(tmp_path)
    f.baseline()
    f.fail_rejoin_id = "B"
    with pytest.raises(AutosaveBarrierError, match="admission must remain held"):
        f.runtime.run_if_due(0.0)
    assert f.runtime.held_after_failure
    assert not f.gate_open
    assert f.runtime.last_verified() is not None
    assert f.events[-1] == "native-rejoin:B"
    assert "external-release-issue" not in f.events


def test_peer_deliveries_are_pairwise_and_duplicate_refused(tmp_path):
    f = RuntimeFixture(tmp_path)
    f.baseline()
    with pytest.raises(LiveCognitionCheckpointError, match="duplicate peer"):
        f.cohort.delivered(PeerDelivery(
            "msg-pre", "A", "B", 101, 102, "payload:pre",
        ))
    assert set(f.owners[0].peer_deliveries) == set(f.owners[1].peer_deliveries)


def test_old_owner_skill_not_automatically_reissued_by_recovery(tmp_path):
    f = RuntimeFixture(tmp_path)
    f.baseline()
    checkpoint = f.runtime.run_if_due(0.0)
    assert checkpoint is not None
    restored_dir = tmp_path / "branch2"
    restore_generation(checkpoint.generation, restored_dir, restore_id="r2")
    candidates = staged_recover_cognition_cohort(checkpoint.generation, restored_dir)
    assert all(c.semantic.skill_histories[0].state.value == "started" for c in candidates)
    assert all(not c.semantic.old_skill_resume_authorized for c in candidates)
    assert all(not c.semantic.new_physical_action_issue_authorized for c in candidates)



def test_peer_messages_wait_for_both_fresh_sessions(tmp_path):
    f = RuntimeFixture(tmp_path)
    f.baseline()
    assert f.runtime.run_if_due(0.0)
    # Both are rebound to new native sessions but still require new WorldBody facts.
    with pytest.raises(LiveCognitionCheckpointError, match="both peers"):
        f.cohort.delivered(PeerDelivery(
            "post-restart-peer", "A", "B", 108, 109, "new-message",
        ))
    f.owners[0].observe_world_tick(
        session_id=f.owners[0].native_session_id, world_tick=111,
    )
    with pytest.raises(LiveCognitionCheckpointError, match="both peers"):
        f.cohort.delivered(PeerDelivery(
            "post-restart-peer", "A", "B", 108, 109, "new-message",
        ))
    f.owners[1].observe_world_tick(
        session_id=f.owners[1].native_session_id, world_tick=111,
    )
    f.cohort.delivered(PeerDelivery(
        "post-restart-peer", "A", "B", 108, 109, "new-message",
    ))
    assert "post-restart-peer" in f.owners[0].peer_deliveries
    assert "post-restart-peer" in f.owners[1].peer_deliveries
