"""#860 N=2/10/100 offline bounded full-roster STOP/freeze/rejoin regression.

Tests use actual typed cognition owners/WAL/world generations, but Mineflayer
observations and World stop/restart are SYNTHETIC. Not real Minecraft evidence.
"""
from __future__ import annotations

import asyncio
import time
from pathlib import Path
from types import SimpleNamespace

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
from relay_self.checkpoint_stop_neutralization_dev import StopParticipant
from relay_self.checkpointed_cognitive_runtime_dev import (
    CheckpointedCognitiveOwner,
    CognitionOwnerCohort,
    CognitiveOwnerFiles,
    ExternalRejoin,
)
from relay_self.cognitive_minimal_dev import initial_patterns
from relay_self.coordinated_autosave_runtime_dev import (
    AutosaveBarrierError,
    CoordinatedAutosaveRuntime,
    RestartedWorldReceipt,
    SelfRuntimeHooks,
    StoppedWorldReceipt,
    WorldRuntimeHooks,
)
from relay_self.coordinated_checkpoint_host_dev import (
    CheckpointHostError,
    CoordinatedCheckpointHost,
)
from relay_self.intent import IntentCommitment
from relay_self.persistent_cognition import (
    IdentitySpecification,
    PersistentCognition,
)
from relay_self.physical_action_journal import PhysicalActionJournal
from relay_self.physical_issue_admission_dev import PhysicalIssueAdmission
from relay_self.provenance import Provenance
from relay_self.self_owner_checkpoint_dev import verify_typed_generation


class SyntheticNative:
    """A different native socket-like process per Self. NOT real Mineflayer."""

    def __init__(self, sid: str, native: str, gate, *, fault=None, gauge=None):
        self.self_id = sid
        self.gauge = gauge
        self.started = SimpleNamespace(session_id=native)
        self.gate = gate
        self.fault = fault
        self.messages = []
        self.seq = 0
        self.observations = 0
        self.stops = 0

    def _seq(self):
        self.seq += 1
        return self.seq

    async def send_clear_controls(self, action_id):
        self.gate.require_native_effect(
            self_id=self.self_id, native_session_id=self.started.session_id,
            effect="clear_controls", action_id=action_id,
        )
        self.stops += 1
        self.messages.append(MineflayerEffectResult(
            self.started.session_id, self._seq(), action_id,
            "clear_controls", "applied", None,
        ))
        # This is a source-shaped stub. Verify actual asynchronous overlap,
        # not simply the number of submitted worker tasks.
        if self.gauge is not None:
            self.gauge["active"] += 1
            self.gauge["max"] = max(
                self.gauge["max"], self.gauge["active"],
            )
        try:
            await asyncio.sleep(0.002)
        finally:
            if self.gauge is not None:
                self.gauge["active"] -= 1

    async def send_observe(self, request_id=None):
        self.observations += 1
        tick = 100 + 8 * (self.observations - 1)
        self.messages.append(MineflayerObservation(
            self.started.session_id, self._seq(), "probe",
            MineflayerSnapshot(
                health=20, food=12, food_saturation=5, oxygen_level=20,
                position=MineflayerPosition(
                    1.0 + (self.observations if self.fault == "drift" else 0),
                    64.0, 2.0,
                ),
                time=MineflayerTime(tick, 0, True),
                inventory=(), nearby_entities=(),
                nearby_entities_coverage=MineflayerNearbyEntitiesCoverage(
                    MINEFLAYER_NEARBY_ENTITY_SOURCE_SCOPE,
                    MINEFLAYER_NEARBY_ENTITY_MAX_DISTANCE,
                    MINEFLAYER_NEARBY_ENTITY_MAX_ENTITIES,
                    0, False,
                ),
            ),
            ("foreign" if self.fault == "wrong_probe" else request_id),
        ))

    async def receive(self):
        if self.messages:
            return self.messages.pop(0)
        raise EOFError("missing synthetic native event")


class NFixture:
    def __init__(
        self, root: Path, count: int, *,
        fault_stop: str | None = None,
        fault_rejoin: str | None = None,
        freeze_workers: int = 8,
        parallel_workers: int = 16,
    ):
        self.root = root
        self.names = tuple(f"S{i:03d}" for i in range(count))
        self.world = root / "world"
        self.world.mkdir()
        (self.world / "level.dat").write_bytes(b"offline-no-paper")
        self.store = root / "store"
        self.store.mkdir()
        self.owners = []
        for sid in self.names:
            folder = root / ("owner-" + sid)
            folder.mkdir()
            wal = folder / "physical-wal.json"
            PhysicalActionJournal.create(wal, self_id=sid)
            self.owners.append(CheckpointedCognitiveOwner(
                retained=PersistentCognition(IdentitySpecification(
                    sid, ("N Self identity invariant",),
                    Provenance("synthetic", sid),
                )),
                intent=IntentCommitment(),
                pattern_registry=initial_patterns(),
                native_session_id="old-" + sid,
                last_observed_tick=100,
                files=CognitiveOwnerFiles(folder, folder / "cognition.json", wal),
                physical_supervisor=ActionSupervisor(),
            ))
        self.physical = PhysicalIssueAdmission(
            {sid: "old-" + sid for sid in self.names},
            require_neutral_stop=True,
        )
        self.stop_parallel = {"active": 0, "max": 0}
        self.native = {
            sid: SyntheticNative(
                sid, "old-" + sid, self.physical,
                fault=(fault_stop if sid == self.names[-1] else None),
                gauge=self.stop_parallel,
            ) for sid in self.names
        }
        self.rejoin_fault = fault_rejoin
        self.close_count = 0
        self.stop_count = 0
        self.restart_count = 0
        self.next_paper = 0
        self.inflight_rejoin = 0
        self.max_inflight_rejoin = 0
        self.fence = None

        def close():
            self.close_count += 1
            self.fence = self.physical.close()
            return self.fence

        def release(fence):
            assert self.fence is not None and fence == self.fence.fence_ref
            self.physical.release(fence)

        def rebind(sid, paper, old):
            assert self.fence is not None
            new = self.native[sid].started.session_id
            self.physical.rotate_native_session(
                fence_ref=self.fence.fence_ref, self_id=sid,
                old_session_id=old, new_session_id=new,
            )
            return ExternalRejoin(new, True, True, True)

        self.cohort = CognitionOwnerCohort(
            owners=tuple(self.owners), world_id="n-world", branch_id="source",
            external_close_physical=close,
            external_release_physical=release,
            external_native_rejoin=rebind,
        )
        self.paper_session = "paper-initial"

        def stop_world():
            assert self.physical.closed
            self.stop_count += 1
            return StoppedWorldReceipt(
                "n-world", "source", self.paper_session,
                120 + self.stop_count * 40,
                "synthetic:tick", "synthetic:stopped", 0, True,
            )

        def restart():
            self.restart_count += 1
            self.paper_session = f"paper-next-{self.restart_count}"
            return RestartedWorldReceipt(
                "n-world", "source", self.paper_session, True,
            )

        self.runtime = CoordinatedAutosaveRuntime(
            source_world=self.world, store=self.store,
            world_id="n-world", branch_id="source",
            participants=self.cohort.participant_hooks(),
            world=WorldRuntimeHooks(stop_world, restart),
            admission=self.cohort.admission_hooks(),
            strict_typed_owner_cut=True, freeze_workers=freeze_workers,
        )
        self.host = CoordinatedCheckpointHost(
            runtime=self.runtime, physical=self.physical,
            cognitive_cohort=self.cohort,
            participants_now=lambda: tuple(
                StopParticipant(sid, self.native[sid])
                for sid in self.names
            ),
            stop_audit_dir=root, stop_parallel_workers=parallel_workers,
            rejoin_parallel_workers=parallel_workers,
            prepare_native_rejoin=self.prepare_native,
            stop_timeout_s=2.0,
        )

    async def prepare_native(self, sid, paper, old):
        assert paper == self.paper_session
        assert self.physical.closed
        self.inflight_rejoin += 1
        self.max_inflight_rejoin = max(
            self.max_inflight_rejoin, self.inflight_rejoin,
        )
        try:
            await asyncio.sleep(0.001)
            if self.rejoin_fault == "last_fails" and sid == self.names[-1]:
                raise ConnectionError("simulated last Self native rejoin failure")
            if self.rejoin_fault == "duplicates":
                fresh = "all-shared-session"
            else:
                fresh = f"native-{sid}-{paper}"
            self.native[sid] = SyntheticNative(
                sid, fresh, self.physical, gauge=self.stop_parallel,
            )
            return fresh
        finally:
            self.inflight_rejoin -= 1

    def observe_new_worldbody(self):
        for owner in self.owners:
            owner.observe_world_tick(
                session_id=owner.native_session_id,
                world_tick=owner.last_observed_tick + 1,
            )


@pytest.mark.parametrize("count", [2, 10, 100])
def test_n_self_bounded_stop_freeze_rejoin_two_generations(tmp_path, count):
    f = NFixture(tmp_path, count)
    t0 = time.monotonic()
    async def exercise():
        first = await f.host.cycle_if_due(0.0)
        assert first is not None and first.saved.sequence == 0
        assert len(first.stop.receipt_files) == count
        assert first.stop.verified_self_ids == f.names
        assert len(verify_typed_generation(first.saved.generation)) == count
        assert not f.physical.closed
        f.observe_new_worldbody()
        assert await f.host.cycle_if_due(59.9) is None
        second = await f.host.cycle_if_due(60.0)
        assert second is not None and second.saved.sequence == 1
        assert len(second.stop.receipt_files) == count
        assert len(verify_typed_generation(second.saved.generation)) == count
        assert not second.historical_replay_performed
        assert not f.physical.closed
        assert f.max_inflight_rejoin > 1
        assert f.stop_parallel["max"] > 1
        assert f.stop_parallel["active"] == 0
    asyncio.run(exercise())
    assert f.stop_count == f.restart_count == f.close_count == 2
    assert f.runtime.timer.last_success_monotonic == 60.0
    assert len(list(f.store.glob("g-*/COMMITTED.json"))) == 2
    # A soft guard, not a real-world latency claim: 100 synthetic actors
    # should not serialize 100 independent ~0.1-second STOP windows.
    assert time.monotonic() - t0 < 30.0


@pytest.mark.parametrize("count", [2, 10, 100])
def test_one_bad_n_self_stop_cannot_commit_world_or_any_owner(
    tmp_path, count,
):
    f = NFixture(tmp_path, count, fault_stop="wrong_probe")
    with pytest.raises(Exception):
        asyncio.run(f.host.cycle_if_due(0.0))
    assert f.physical.closed and f.host.held_after_failure
    assert f.stop_count == f.restart_count == f.close_count == 0
    assert not list(f.store.glob("g-*/COMMITTED.json"))
    with pytest.raises(Exception):
        asyncio.run(f.host.cycle_if_due(60.0))


@pytest.mark.parametrize("count", [2, 10, 100])
def test_one_bad_n_self_rejoin_preserves_complete_inert_generation(
    tmp_path, count,
):
    f = NFixture(tmp_path, count, fault_rejoin="last_fails")
    with pytest.raises(AutosaveBarrierError, match="async native rejoin failed"):
        asyncio.run(f.host.cycle_if_due(0.0))
    assert f.physical.closed and f.host.held_after_failure
    assert f.stop_count == f.restart_count == f.close_count == 1
    assert f.runtime.timer.last_success_monotonic is None
    committed = list(f.store.glob("g-*/COMMITTED.json"))
    assert len(committed) == 1
    assert len(verify_typed_generation(committed[0].parent)) == count


def test_n_self_duplicate_native_ids_rejected_before_any_physical_release(tmp_path):
    f = NFixture(tmp_path, 10, fault_rejoin="duplicates")
    with pytest.raises(AutosaveBarrierError, match="reused session identity"):
        asyncio.run(f.host.cycle_if_due(0.0))
    assert f.physical.closed and f.host.held_after_failure
    assert f.stop_count == f.restart_count == 1
    assert f.runtime.timer.last_success_monotonic is None


def test_n_self_missing_member_holds_before_stop(tmp_path):
    f = NFixture(tmp_path, 100)
    f.host.participants_now = lambda: tuple(
        StopParticipant(sid, f.native[sid]) for sid in f.names[:-1]
    )
    with pytest.raises(CheckpointHostError, match="roster"):
        asyncio.run(f.host.cycle_if_due(0.0))
    assert f.physical.closed and f.host.held_after_failure
    assert f.stop_count == 0
    assert all(native.stops == 0 for native in f.native.values())


def test_n_self_freeze_failure_cannot_save_world(tmp_path):
    f = NFixture(tmp_path, 10)
    old = f.runtime.participants
    def reject(_generation):
        raise RuntimeError("unqualified frozen Self")
    last = old[-1]
    f.runtime.participants = old[:-1] + (
        SelfRuntimeHooks(last.self_id, reject, last.rebind_after_world_restart),
    )
    with pytest.raises(AutosaveBarrierError, match="async native rejoin failed"):
        asyncio.run(f.host.cycle_if_due(0.0))
    assert f.physical.closed and f.host.held_after_failure
    assert f.stop_count == f.restart_count == 0
    assert not list(f.store.glob("g-*/COMMITTED.json"))



def test_n_self_actual_owner_freeze_file_io_overlaps_under_one_fence(
    tmp_path, monkeypatch,
):
    import threading

    import relay_self.checkpointed_cognitive_runtime_dev as owner_module

    f = NFixture(tmp_path, 10, freeze_workers=8)
    original = owner_module.save_self_owner_cut
    lock = threading.Lock()
    tracker = {"active": 0, "peak": 0}

    def delayed_write(path, cut):
        assert f.physical.closed and f.cohort.closed
        with lock:
            tracker["active"] += 1
            tracker["peak"] = max(tracker["active"], tracker["peak"])
        try:
            # A synthetic IO delay proves that independent file flushes are
            # actually outside the global cognition lock, not merely queued.
            time.sleep(0.025)
            return original(path, cut)
        finally:
            with lock:
                tracker["active"] -= 1

    monkeypatch.setattr(owner_module, "save_self_owner_cut", delayed_write)
    first = asyncio.run(f.host.cycle_if_due(0.0))
    assert first is not None
    assert tracker["active"] == 0
    assert tracker["peak"] >= 2
    assert not f.physical.closed
    assert len(verify_typed_generation(first.saved.generation)) == 10


def test_n_self_owner_fsync_failure_joins_threads_and_holds_before_world(
    tmp_path, monkeypatch,
):
    import relay_self.checkpointed_cognitive_runtime_dev as owner_module

    f = NFixture(tmp_path, 10, freeze_workers=8)
    original = owner_module.save_self_owner_cut
    completed = []

    def failed_owner_write(path, cut):
        time.sleep(0.005)
        if cut.self_id == f.names[-1]:
            raise OSError("simulated durable owner file error")
        original(path, cut)
        completed.append(cut.self_id)

    monkeypatch.setattr(owner_module, "save_self_owner_cut", failed_owner_write)
    with pytest.raises(AutosaveBarrierError, match="async native rejoin failed") as err:
        asyncio.run(f.host.cycle_if_due(0.0))
    assert err.value.__cause__ is not None
    assert "durable owner file" in str(err.value.__cause__)
    assert len(completed) > 0
    assert f.cohort._freeze_failed
    assert not f.cohort._freeze_active
    assert f.physical.closed and f.host.held_after_failure
    assert f.stop_count == f.restart_count == 0
    assert not list(f.store.glob("g-*/COMMITTED.json"))



@pytest.mark.parametrize("overlap", ["identical", "nested"])
def test_n_self_parallel_owner_roots_must_be_physically_disjoint(
    tmp_path, overlap,
):
    from relay_self.checkpointed_cognitive_runtime_dev import (
        LiveCognitionCheckpointError,
    )

    f = NFixture(tmp_path, 2)
    a, b = f.owners
    a.cohort = None
    b.cohort = None
    root = a.files.self_root
    if overlap == "nested":
        root = root / "nested"
    b.files = CognitiveOwnerFiles(
        root, b.files.cognition_file, b.files.physical_wal_file,
    )
    with pytest.raises(LiveCognitionCheckpointError, match="roots overlap"):
        CognitionOwnerCohort(
            owners=(a, b), world_id="n-world", branch_id="source",
            external_close_physical=lambda: f.physical.close(),
            external_release_physical=f.physical.release,
            external_native_rejoin=lambda sid, paper, old: ExternalRejoin(
                "new-" + sid, True, True, True,
            ),
        )
    assert not f.physical.closed
