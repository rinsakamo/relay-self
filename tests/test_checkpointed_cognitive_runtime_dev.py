"""#860: actual existing cognition owners behind an offline multi-Self cut."""
from __future__ import annotations

import asyncio
import sys
from pathlib import Path

import pytest

from adapters.mineflayer.python_protocol import (
    MINEFLAYER_NEARBY_ENTITY_MAX_DISTANCE,
    MINEFLAYER_NEARBY_ENTITY_MAX_ENTITIES,
    MINEFLAYER_NEARBY_ENTITY_SOURCE_SCOPE,
    MineflayerEffectResult,
    MineflayerNearbyEntitiesCoverage,
    MineflayerObservation,
    MineflayerPosition,
    MineflayerSnapshot,
    MineflayerTime,
)
from relay_self.action_supervision import ActionSupervisor
from relay_self.checkpoint_stop_neutralization_dev import (
    StopParticipant,
    prepare_stop_before_autosave,
)
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
from relay_self.coordinated_checkpoint_host_dev import (
    CheckpointHostError,
    CoordinatedCheckpointHost,
)
from relay_self.intent import IntentCommitment
from relay_self.owned_paper_world_dev import OwnedPaperWorld, PaperTickReceipt
from relay_self.persistent_cognition import (
    IdentitySpecification,
    Memory,
    PersistentCognition,
)
from relay_self.physical_action_journal import PhysicalActionJournal
from relay_self.physical_issue_admission_dev import PhysicalIssueAdmission
from relay_self.provenance import Provenance
from relay_self.self_owner_checkpoint_dev import PeerDelivery, verify_typed_generation


class RuntimeFixture:
    def __init__(self, tmp_path: Path, *, paper_layout: bool = False):
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
            paper_layout=paper_layout,
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


def test_owner_rejects_duplicate_pending_questions_before_set_conversion(tmp_path):
    fixture = RuntimeFixture(tmp_path)
    owner = fixture.owners[0]
    with pytest.raises(LiveCognitionCheckpointError, match="duplicate pending Question"):
        CheckpointedCognitiveOwner(
            retained=owner.retained, intent=owner.intent,
            pattern_registry=owner.pattern_registry,
            native_session_id=owner.native_session_id,
            last_observed_tick=owner.last_observed_tick, files=owner.files,
            physical_supervisor=owner.supervisor, pending_questions=("q", "q"),
        )


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
    assert not list(restored_dir.rglob("physical-wal.json.lock"))
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



def _connect_actual_physical_issue_admission(f):
    """One shared cohort gate; external native authenticity remains a fixture."""
    physical = PhysicalIssueAdmission({
        owner.self_id: owner.native_session_id for owner in f.owners
    })

    def close():
        f.gate_open = False
        f.events.append("physical-lease-stop")
        return physical.close()

    def release(token):
        physical.release(token)
        f.events.append("physical-lease-release")
        f.gate_open = True

    def rejoin(sid, paper_session, previous_session):
        assert f.cohort.fence is not None
        new = f"new-{sid}-{paper_session}"
        physical.rotate_native_session(
            fence_ref=f.cohort.fence.fence_ref,
            self_id=sid, old_session_id=previous_session,
            new_session_id=new,
        )
        return ExternalRejoin(new, True, True, True)

    f.cohort.external_close_physical = close
    f.cohort.external_release_physical = release
    f.cohort.external_native_rejoin = rejoin
    return physical


def test_actual_issuer_lease_fences_cognition_cut_and_new_session(tmp_path):
    f = RuntimeFixture(tmp_path)
    f.baseline()
    physical = _connect_actual_physical_issue_admission(f)
    first = f.runtime.run_if_due(0.0)
    assert first is not None
    assert first.typed_owner_cut_validated
    assert not physical.closed
    assert f.gate_open
    assert f.owners[0].native_session_id == f"new-A-{f.session_id}"
    # First session cannot issue a new physical action after Paper rejoin.
    with pytest.raises(Exception, match="stale or foreign"):
        with physical.lease(
            self_id="A", native_session_id="native-before-A",
            action_id="stale-attack",
        ):
            pytest.fail("old physical epoch entered")
    with physical.lease(
        self_id="A", native_session_id=f.owners[0].native_session_id,
        action_id="fresh-eat",
    ):
        assert physical.active_action_ids == ("fresh-eat",)


def test_active_physical_action_prevents_world_and_all_self_save(tmp_path):
    f = RuntimeFixture(tmp_path)
    f.baseline()
    physical = _connect_actual_physical_issue_admission(f)
    with physical.lease(
        self_id="A", native_session_id="native-before-A",
        action_id="native-attack-inflight",
    ):
        with pytest.raises(AutosaveBarrierError, match="admission must remain held"):
            f.runtime.run_if_due(0.0)
    assert f.runtime.held_after_failure
    assert physical.closed
    assert f.cohort.closed
    assert not (f.store / "g-000000000000" / "COMMITTED.json").exists()
    assert "stop-world" not in f.events



def test_actual_a_b_cognition_cut_only_after_both_neutral_stop_proofs(tmp_path):
    """Old physical Action owners and actual cognition facade use one gate."""
    from types import SimpleNamespace

    f = RuntimeFixture(tmp_path)
    f.baseline()
    gate = PhysicalIssueAdmission({
        owner.self_id: owner.native_session_id for owner in f.owners
    }, require_neutral_stop=True)

    def physical_close():
        f.gate_open = False
        f.events.append("stop-complete-physical-close")
        return gate.close()

    def physical_release(token):
        gate.release(token)
        f.gate_open = True
        f.events.append("all-rebound-physical-release")

    def native_rejoin(sid, paper_sid, old_sid):
        new = f"native-new-{sid}-{paper_sid}"
        gate.rotate_native_session(
            fence_ref=f.cohort.fence.fence_ref,
            self_id=sid, old_session_id=old_sid, new_session_id=new,
        )
        return ExternalRejoin(new, True, True, True)

    f.cohort.external_close_physical = physical_close
    f.cohort.external_release_physical = physical_release
    f.cohort.external_native_rejoin = native_rejoin

    class LocalStopSession:
        def __init__(self, self_id, native_id):
            self.self_id = self_id
            self.started = SimpleNamespace(session_id=native_id)
            self.seq = 0
            self.count = 0
            self.queued = []

        async def send_clear_controls(self, action_id):
            gate.require_native_effect(
                self_id=self.self_id, native_session_id=self.started.session_id,
                effect="clear_controls", action_id=action_id,
            )
            self.seq += 1
            self.queued.append(MineflayerEffectResult(
                self.started.session_id, self.seq, action_id,
                "clear_controls", "applied", None,
            ))

        async def send_observe(self, request_id=None):
            self.count += 1
            self.seq += 1
            self.queued.append(MineflayerObservation(
                self.started.session_id, self.seq, "probe",
                MineflayerSnapshot(
                    20, 12, 5, 20, MineflayerPosition(1.0, 64.0, 2.0),
                    MineflayerTime(100 + 10 * (self.count - 1), 0, True),
                    (), (),
                    MineflayerNearbyEntitiesCoverage(
                        MINEFLAYER_NEARBY_ENTITY_SOURCE_SCOPE,
                        MINEFLAYER_NEARBY_ENTITY_MAX_DISTANCE,
                        MINEFLAYER_NEARBY_ENTITY_MAX_ENTITIES,
                        0, False,
                    ),
                ),
                request_id,
            ))

        async def receive(self):
            return self.queued.pop(0)

    participants = tuple(StopParticipant(
        owner.self_id, LocalStopSession(owner.self_id, owner.native_session_id),
    ) for owner in f.owners)
    ready = asyncio.run(prepare_stop_before_autosave(
        gate, participants=participants, audit_dir=tmp_path,
    ))
    assert ready.verified_self_ids == ("A", "B")
    assert gate.neutralization_complete

    result = f.runtime.run_if_due(0.0)
    assert result is not None and result.typed_owner_cut_validated
    assert len(verify_typed_generation(result.generation)) == 2
    assert not f.runtime.held_after_failure
    assert not gate.closed
    assert f.gate_open
    assert f.events.index("stop-complete-physical-close") < f.events.index("stop-world")
    assert f.events.index("stop-world") < f.events.index("start-world")
    assert f.events.index("start-world") < f.events.index("all-rebound-physical-release")



class HostNativeStopSession:
    """Fake native per-Self session; STOP readbacks are synthetic typed events."""

    def __init__(self, self_id, session_id, gate, *, fault=None):
        from types import SimpleNamespace

        self.self_id = self_id
        self.started = SimpleNamespace(session_id=session_id)
        self.gate = gate
        self.fault = fault
        self.seq = 0
        self.probes = 0
        self.writes = []
        self.messages = []

    async def send_clear_controls(self, action_id):
        self.gate.require_native_effect(
            self_id=self.self_id, native_session_id=self.started.session_id,
            effect="clear_controls", action_id=action_id,
        )
        self.writes.append(action_id)
        self.seq += 1
        self.messages.append(MineflayerEffectResult(
            self.started.session_id, self.seq, action_id, "clear_controls",
            "applied", None,
        ))

    async def send_observe(self, request_id=None):
        self.seq += 1
        self.probes += 1
        x = 3.0 if self.fault != "drift" else 3.0 + self.probes / 4
        self.messages.append(MineflayerObservation(
            self.started.session_id, self.seq, "probe",
            MineflayerSnapshot(
                20, 12, 4, 20,
                MineflayerPosition(x, 64, 2),
                MineflayerTime(100 + 10 * (self.probes - 1), 0, True),
                (), (),
                MineflayerNearbyEntitiesCoverage(
                    MINEFLAYER_NEARBY_ENTITY_SOURCE_SCOPE,
                    MINEFLAYER_NEARBY_ENTITY_MAX_DISTANCE,
                    MINEFLAYER_NEARBY_ENTITY_MAX_ENTITIES,
                    0, False,
                ),
            ),
            request_id,
        ))

    async def receive(self):
        return self.messages.pop(0)


def _owned_host_fixture(tmp_path, *, failure_b=None, paper=True):
    """Actual existing owner/typed generation and real Python child OS process.

    The child only *mimics* Paper's console. This is not Minecraft.
    """
    f = RuntimeFixture(tmp_path, paper_layout=paper)
    f.baseline()
    physical = PhysicalIssueAdmission(
        {o.self_id: o.native_session_id for o in f.owners},
        require_neutral_stop=True,
    )
    sessions = {
        o.self_id: HostNativeStopSession(
            o.self_id, o.native_session_id, physical,
            fault=failure_b if o.self_id == "B" else None,
        ) for o in f.owners
    }

    def close():
        f.events.append("physical-close")
        f.gate_open = False
        return physical.close()

    def release(token):
        physical.release(token)
        f.events.append("physical-release")
        f.gate_open = True

    def rejoin(sid, paper_session, old):
        new = f"native-{sid}-after-{paper_session}"
        physical.rotate_native_session(
            fence_ref=f.cohort.fence.fence_ref,
            self_id=sid, old_session_id=old, new_session_id=new,
        )
        sessions[sid] = HostNativeStopSession(sid, new, physical)
        f.events.append("rebind-real-cohort:" + sid)
        return ExternalRejoin(new, True, True, True)

    f.cohort.external_close_physical = close
    f.cohort.external_release_physical = release
    f.cohort.external_native_rejoin = rejoin
    owned = None
    if paper:
        script = tmp_path / "fake_paper_console.py"
        script.write_text(
            "import sys\n"
            "print('Done (0.1s)', flush=True)\n"
            "for line in sys.stdin:\n"
            "    if line.strip() == 'save-all flush':\n"
            "        print('Saved the game', flush=True)\n"
            "    if line.strip() == 'stop':\n"
            "        print('Stopping server', flush=True)\n"
            "        sys.exit(0)\n",
            encoding="utf-8",
        )
        evidence = tmp_path / "evidence"
        evidence.mkdir()
        ticks = {"count": 0}

        def tick_readback(current_session):
            ticks["count"] += 1
            return PaperTickReceipt(
                current_session, 110 + 60 * ticks["count"], "fake:server-tick",
            )

        owned = OwnedPaperWorld(
            server_dir=tmp_path, world_dir=f.world_dir,
            evidence_dir=evidence,
            command=(sys.executable, "-u", str(script)),
            world_id="world-1", branch_id="source",
            tick_readback=tick_readback, timeout_seconds=3.0,
        )
        owned.start_owned()
        f.runtime.world = owned.runtime_hooks()
    clock = {"value": 0.0}

    async def fake_sleep(_seconds):
        clock["value"] += 30.0
        for owner in f.owners:
            if owner.fresh_native_observation_required:
                owner.observe_world_tick(
                    session_id=owner.native_session_id,
                    world_tick=owner.last_observed_tick + 1,
                )

    host = CoordinatedCheckpointHost(
        runtime=f.runtime, physical=physical, cognitive_cohort=f.cohort,
        participants_now=lambda: tuple(
            StopParticipant(sid, sessions[sid]) for sid in sorted(sessions)
        ),
        stop_audit_dir=tmp_path, owned_paper=owned,
        stop_timeout_s=0.5,
        monotonic_clock=lambda: clock["value"],
        sleep=fake_sleep,
    )
    return f, host, physical, sessions, owned, clock


def test_bounded_host_two_60s_generations_with_owned_process_and_fresh_a_b(tmp_path):
    f, host, physical, sessions, owned, clock = _owned_host_fixture(tmp_path)
    assert owned is not None
    first_paper = owned.owned_session_id
    try:
        cycles = asyncio.run(host.run_bounded(
            max_cycles=2, max_polls=3, poll_seconds=1.0,
        ))
        assert len(cycles) == 2
        assert [c.saved.sequence for c in cycles] == [0, 1]
        assert all(c.saved.typed_owner_cut_validated for c in cycles)
        assert all(c.stop.verified_self_ids == ("A", "B") for c in cycles)
        assert cycles[0].previous_paper_session == first_paper
        assert cycles[0].next_paper_session != first_paper
        assert cycles[1].previous_paper_session == cycles[0].next_paper_session
        assert cycles[1].next_paper_session == owned.owned_session_id
        assert cycles[1].next_paper_session != cycles[1].previous_paper_session
        assert host.runtime.timer.last_success_monotonic == 60.0
        assert clock["value"] == 60.0
        assert not host.held_after_failure and not physical.closed
        assert not f.cohort.closed
        for cycle in cycles:
            assert len(verify_typed_generation(cycle.saved.generation)) == 2
            assert not cycle.historical_replay_performed
            assert cycle.stop.receipt_files
        assert f.events.count("physical-release") == 2
    finally:
        if owned.owned_session_id is not None:
            owned.stop_and_save()


def test_host_rejects_unobserved_new_worldbody_before_next_save(tmp_path):
    f, host, physical, sessions, owned, clock = _owned_host_fixture(tmp_path)
    try:
        assert asyncio.run(host.cycle_if_due(0.0)) is not None
        assert asyncio.run(host.cycle_if_due(59.99)) is None
        # A/B were rebound but the new native WorldBody has not been observed.
        with pytest.raises(CheckpointHostError, match="current WorldBody"):
            asyncio.run(host.cycle_if_due(60.0))
        assert host.held_after_failure
        assert physical.closed
        assert f.runtime.last_verified() is not None
        assert len(list(f.store.glob("g-*/COMMITTED.json"))) == 1
        assert owned.owned_session_id is not None
    finally:
        if owned.owned_session_id is not None:
            owned.stop_and_save()


def test_host_missing_b_held_before_stop_or_world_save(tmp_path):
    f, host, physical, sessions, owned, clock = _owned_host_fixture(tmp_path)
    host.participants_now = lambda: (StopParticipant("A", sessions["A"]),)
    try:
        with pytest.raises(CheckpointHostError, match="roster"):
            asyncio.run(host.cycle_if_due(0.0))
        assert host.held_after_failure and physical.closed
        assert not sessions["A"].writes
        assert not f.runtime.last_verified()
        assert owned.owned_session_id is not None
    finally:
        if owned.owned_session_id is not None:
            owned.stop_and_save()


def test_host_b_drifts_so_no_partial_generation_and_global_hold(tmp_path):
    f, host, physical, sessions, owned, clock = _owned_host_fixture(
        tmp_path, failure_b="drift",
    )
    try:
        with pytest.raises(Exception, match="settled|STOP"):
            asyncio.run(host.cycle_if_due(0.0))
        assert host.held_after_failure and physical.closed
        assert sessions["A"].writes and sessions["B"].writes
        assert f.runtime.last_verified() is None
        assert owned.owned_session_id is not None
    finally:
        if owned.owned_session_id is not None:
            owned.stop_and_save()


def test_host_polls_without_premature_stop_between_60s_windows(tmp_path):
    f, host, physical, sessions, owned, clock = _owned_host_fixture(tmp_path)
    try:
        assert asyncio.run(host.cycle_if_due(0.0))
        old_b = sessions["B"]
        assert asyncio.run(host.cycle_if_due(10.0)) is None
        assert asyncio.run(host.cycle_if_due(59.5)) is None
        assert sessions["B"] is old_b
        assert not sessions["B"].writes
        assert len(list(f.store.glob("g-*/COMMITTED.json"))) == 1
    finally:
        if owned.owned_session_id is not None:
            owned.stop_and_save()



class _OwnedNativeCohortForCognitionTest:
    """Injected native process-shaped adapter; no real Node/Paper/GPU here."""

    def __init__(self, sessions, physical, *, fail_self=None, mismatch=False,
                 stale_clock=False):
        from relay_self.owned_native_rejoin_cohort_dev import NativePreparedRejoin

        self.receipt_type = NativePreparedRejoin
        self.sessions = sessions
        self.physical = physical
        self.fail_self = fail_self
        self.mismatch = mismatch
        self.stale_clock = stale_clock
        self.prepared = {}
        self.epoch = 0

    def participants_now(self):
        return tuple(
            StopParticipant(sid, self.sessions[sid])
            for sid in sorted(self.sessions)
        )

    async def prepare_rejoin(self, sid, paper, old):
        if sid == self.fail_self:
            raise ConnectionError("simulated missing owned native process " + sid)
        assert self.sessions[sid].started.session_id == old
        assert self.physical.closed
        self.epoch += 1
        new = f"owned-native-{sid}-{paper}-{self.epoch}"
        self.sessions[sid] = HostNativeStopSession(sid, new, self.physical)
        self.prepared[sid] = self.receipt_type(
            sid, paper, old, new, 1, 2, "native-probe-" + sid,
            probe_world_tick=(
                10 if self.stale_clock and sid == "B"
                else 100 + self.epoch * 50
            ),
        )
        return ("swapped-native" if self.mismatch and sid == "B" else new)

    def prepared_receipt(self, sid, paper, old):
        row = self.prepared[sid]
        assert row.paper_session_id == paper and row.old_native_session_id == old
        return row


def _owned_native_cognitive_bridge_fixture(
    tmp_path, *, failure_b=False, mismatch=False, stale_clock=False,
):
    from relay_self.owned_cognitive_native_rejoin_dev import (
        InertScopedWorkEpoch,
        OwnedCognitiveNativeBridge,
    )

    f, host, physical, sessions, paper, clock = _owned_host_fixture(tmp_path)
    native = _OwnedNativeCohortForCognitionTest(
        sessions, physical,
        fail_self="B" if failure_b else None,
        mismatch=mismatch,
        stale_clock=stale_clock,
    )
    work = InertScopedWorkEpoch(physical.current_native_sessions)
    bridge = OwnedCognitiveNativeBridge(
        native=native, physical=physical, work=work,
        cognition=f.cohort,
    )
    f.cohort.external_close_physical = bridge.close
    f.cohort.external_release_physical = bridge.release
    f.cohort.external_native_rejoin = bridge.external_native_rejoin
    host.participants_now = native.participants_now
    host.prepare_native_rejoin = bridge.prepare_native_rejoin
    return f, host, physical, native, work, bridge, paper, clock


def test_async_native_work_bridge_two_real_owner_generations_without_replay(tmp_path):
    """Actual cognition owners + work epoch + OS fake Paper and native test IO."""
    f, host, physical, native, work, bridge, paper, clock = (
        _owned_native_cognitive_bridge_fixture(tmp_path)
    )

    fenced_observed = []
    old_admit = f.cohort.observe_fenced_rejoin_world_tick

    def admit_while_held(*, self_id, native_session_id, world_tick):
        assert physical.closed and f.cohort.closed and work.closed
        fenced_observed.append((self_id, native_session_id, world_tick))
        return old_admit(
            self_id=self_id, native_session_id=native_session_id,
            world_tick=world_tick,
        )

    f.cohort.observe_fenced_rejoin_world_tick = admit_while_held

    async def scenario():
        first = await host.cycle_if_due(0.0)
        assert first is not None
        assert first.saved.typed_owner_cut_validated
        assert first.stop.verified_self_ids == ("A", "B")
        assert not physical.closed and not work.closed
        assert all(not o.fresh_native_observation_required for o in f.owners)
        assert [sid for sid, _, _ in fenced_observed] == ["A", "B"]
        with pytest.raises(Exception, match="stale or foreign"):
            with physical.lease(
                self_id="A", native_session_id="native-before-A",
                action_id="replayed-A",
            ):
                pytest.fail("stale owner gained physical authority")
        assert await host.cycle_if_due(59.99) is None
        second = await host.cycle_if_due(60.0)
        assert second is not None and second.saved.sequence == 1
        assert second.previous_paper_session == first.next_paper_session
        assert second.stop.verified_self_ids == ("A", "B")
        assert [sid for sid, _, _ in fenced_observed] == ["A", "B", "A", "B"]
        assert all(not o.fresh_native_observation_required for o in f.owners)
        assert first.saved.sequence == 0
        assert not work.closed and not physical.closed
        assert f.runtime.timer.last_success_monotonic == 60.0
        assert len(verify_typed_generation(first.saved.generation)) == 2
        assert len(verify_typed_generation(second.saved.generation)) == 2
        assert not first.saved.historical_replay_performed
        assert not second.saved.historical_replay_performed

    try:
        asyncio.run(scenario())
    finally:
        if paper.owned_session_id is not None:
            paper.stop_and_save()


@pytest.mark.parametrize(("fault", "match"), [
    ("missing-b", "simulated missing owned native process"),
    ("mismatched-receipt", "native process receipt mismatch"),
    ("gpu-work", "external GPU work attempted"),
    ("peer-message", "external transport attempted"),
])
def test_native_work_bridge_faults_never_release_physical(
    tmp_path, fault, match,
):
    from relay_self.owned_cognitive_native_rejoin_dev import OwnedWorkRejoinError

    f, host, physical, native, work, bridge, paper, clock = (
        _owned_native_cognitive_bridge_fixture(
            tmp_path, failure_b=fault == "missing-b",
            mismatch=fault == "mismatched-receipt",
        )
    )
    if fault == "gpu-work":
        with pytest.raises(OwnedWorkRejoinError, match="GPU"):
            work.register_external_gpu_task("A", "native-before-A", "unfenced-gpu")
    if fault == "peer-message":
        with pytest.raises(OwnedWorkRejoinError, match="peer"):
            work.queue_peer_message("B", "native-before-B", "unfenced-peer")
    try:
        with pytest.raises(AutosaveBarrierError, match="async native rejoin failed") as err:
            asyncio.run(host.cycle_if_due(0.0))
        assert err.value.__cause__ is not None
        assert match in str(err.value.__cause__)
        assert physical.closed and host.held_after_failure
        assert f.cohort.closed
        if fault in {"gpu-work", "peer-message"}:
            assert f.runtime.last_verified() is None
        else:
            assert f.runtime.last_verified() is not None
            assert f.runtime.timer.last_success_monotonic is None
        with pytest.raises(Exception):
            asyncio.run(host.cycle_if_due(60.0))
    finally:
        if paper.owned_session_id is not None:
            paper.stop_and_save()


def test_native_work_bridge_stale_b_probe_rejects_release(tmp_path):
    """B's native process rejoined, but its World clock is older than its owner."""
    f, host, physical, native, work, bridge, paper, clock = (
        _owned_native_cognitive_bridge_fixture(tmp_path, stale_clock=True)
    )
    try:
        with pytest.raises(AutosaveBarrierError, match="async native rejoin failed") as err:
            asyncio.run(host.cycle_if_due(0.0))
        assert err.value.__cause__ is not None
        assert "fenced new WorldBody proof stale" in str(err.value.__cause__)
        assert host.held_after_failure
        assert physical.closed
        assert f.cohort.closed
        assert f.runtime.last_verified() is not None
        assert f.runtime.timer.last_success_monotonic is None
        assert all(o.fresh_native_observation_required for o in f.owners)
        # Original physical owner is globally held even after both native
        # session processes started; no lease can issue a post-cut Action.
        with pytest.raises(Exception):
            with physical.lease(
                self_id="A", native_session_id=native.sessions["A"].started.session_id,
                action_id="post-save-false-grant",
            ):
                pytest.fail("stale B granted A's physical issue")
    finally:
        if paper.owned_session_id is not None:
            paper.stop_and_save()


def test_exploration_schema4_is_bound_to_original_owner_cut(tmp_path):
    import hashlib
    import json
    from dataclasses import replace

    from relay_self.exploration_continuity_dev import ExplorationContinuity, QuestionRecord
    from relay_self.persistent_cognition import load_persistent_cognition
    from relay_self.self_owner_checkpoint_dev import load_self_owner_cut

    f = RuntimeFixture(tmp_path)
    owner = f.owners[0]
    state = ExplorationContinuity(owner.self_id, 1, (QuestionRecord("q", Provenance("probe", "p")),))
    owner.retained = replace(owner.retained, exploration_continuity=state)
    owner.pending_questions.update(("q", "other-valid-question"))
    f.cohort.close()
    receipt = f.cohort.freeze(owner.self_id, "g-000000000001")
    cut = load_self_owner_cut(receipt.snapshot.owner_state_file)
    data = owner.files.cognition_file.read_bytes()
    assert json.loads(data)["schema_version"] == 4
    assert load_persistent_cognition(owner.files.cognition_file).exploration_continuity == state
    assert cut.cognition_sha256 == hashlib.sha256(data).hexdigest()
    assert set(cut.pending_question_refs) == {"q", "other-valid-question"}


def test_schema4_attempt_digest_tampering_is_rejected(tmp_path):
    import json
    from dataclasses import replace

    from relay_self.exploration_continuity_dev import (
        AttemptPhase,
        AttemptRecord,
        ExplorationContinuity,
        QuestionRecord,
        _attempt_ref,
    )
    from relay_self.persistent_cognition import (
        InvalidPersistentCognitionData,
        load_persistent_cognition,
        save_persistent_cognition,
    )
    f = RuntimeFixture(tmp_path)
    owner = f.owners[0]
    digest = "a" * 64
    state = ExplorationContinuity(owner.self_id, 2, (QuestionRecord("q", Provenance("probe", "p")),), (
        AttemptRecord(_attempt_ref(owner.self_id, "q", digest), "q", digest,
                      AttemptPhase.RESERVED, Provenance("owner", "A")),))
    path = owner.files.cognition_file
    save_persistent_cognition(path, replace(owner.retained, exploration_continuity=state))
    assert load_persistent_cognition(path).exploration_continuity == state
    payload = json.loads(path.read_text())
    payload["exploration_continuity"]["attempts"][0]["evidence_digest"] = "b" * 64
    path.write_text(json.dumps(payload))
    with pytest.raises(InvalidPersistentCognitionData):
        load_persistent_cognition(path)
