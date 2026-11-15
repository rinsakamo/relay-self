"""#860 staged autosave barrier: synthetic callbacks, NEVER a live Paper trial."""
from __future__ import annotations

from dataclasses import replace
from pathlib import Path

import pytest

from relay_self.coordinated_autosave_runtime_dev import (
    AdmissionCloseReceipt,
    AdmissionHooks,
    AutosaveBarrierError,
    CoordinatedAutosaveRuntime,
    ReboundSelfReceipt,
    RestartedWorldReceipt,
    SelfFrozenReceipt,
    SelfRuntimeHooks,
    StoppedWorldReceipt,
    WorldRuntimeHooks,
    next_generation_sequence,
)
from relay_self.coordinated_checkpoint_dev import (
    SelfSnapshotSource,
    latest_verified_generation,
    restore_generation,
    verify_generation,
)
from relay_self.persistent_cognition import (
    IdentitySpecification,
    PersistentCognition,
    save_persistent_cognition,
)
from relay_self.physical_action_journal import PhysicalActionJournal
from relay_self.provenance import Provenance


class FakeRuntime:
    def __init__(self, tmp_path: Path):
        self.events: list[str] = []
        self.world = tmp_path / "source-world"
        self.world.mkdir()
        (self.world / "level.dat").write_bytes(b"minecraft-W100")
        (self.world / "entities").mkdir()
        (self.world / "entities" / "r.0.0.mca").write_bytes(b"Z1-is-alive")
        self.store = tmp_path / "checkpoint-store"
        self.store.mkdir()
        self.snapshots: dict[str, SelfSnapshotSource] = {}
        for sid in ("A", "B"):
            root = tmp_path / sid
            root.mkdir()
            cognition = root / "cognition.json"
            save_persistent_cognition(
                cognition,
                PersistentCognition(IdentitySpecification(
                    self_id=sid,
                    directives=("Keep continuity.",),
                    provenance=Provenance("fixture", sid),
                )),
            )
            wal = root / "wal.json"
            PhysicalActionJournal.create(wal, self_id=sid)
            owner = root / "owner-state.json"
            owner.write_text('{"kind":"OPAQUE_TEST_FIXTURE"}')
            self.snapshots[sid] = SelfSnapshotSource(
                sid, cognition, wal, owner,
            )
        self.bad_frozen: str | None = None
        self.bad_rebind: str | None = None
        self.fail_restart = False
        self.close_count = 0
        self.session_no = 0

    def close(self) -> AdmissionCloseReceipt:
        self.events.append("close")
        self.close_count += 1
        return AdmissionCloseReceipt(f"token-{self.close_count}", True, True, True)

    def release(self, token: str) -> None:
        assert token.startswith("token-")
        assert self.events[-1] == "rebind:B"
        self.events.append("release")

    def freeze(self, sid: str, generation: str) -> SelfFrozenReceipt:
        self.events.append("freeze:" + sid)
        assert generation.startswith("g-")
        receipt = SelfFrozenReceipt(
            sid, self.snapshots[sid], f"native-before-{sid}",
            f"frozen:{sid}:{generation}", (), (), True, True, True,
        )
        if self.bad_frozen == sid:
            return replace(receipt, undelivered_message_ids=("msg-undelivered",))
        return receipt

    def stop(self) -> StoppedWorldReceipt:
        self.events.append("world-stop")
        assert self.events[-3:-1] == ["freeze:A", "freeze:B"]
        return StoppedWorldReceipt(
            "world-1", "source", "paper-old", 100,
            "paper:tick-100", "paper:clean-stop", 0, True,
        )

    def restart(self) -> RestartedWorldReceipt:
        self.events.append("world-restart")
        if self.fail_restart:
            raise RuntimeError("Paper did not return")
        return RestartedWorldReceipt("world-1", "source", "paper-new", True)

    def rebind(self, sid: str, session: str) -> ReboundSelfReceipt:
        self.events.append("rebind:" + sid)
        assert session == "paper-new"
        receipt = ReboundSelfReceipt(
            sid, f"native-after-{sid}", "world-1", "source",
            True, True, True, True,
        )
        if self.bad_rebind == sid:
            return replace(receipt, old_session_invalidated=False)
        return receipt

    def runner(self) -> CoordinatedAutosaveRuntime:
        cohort = tuple(
            SelfRuntimeHooks(
                sid,
                lambda gen, sid=sid: self.freeze(sid, gen),
                lambda session, sid=sid: self.rebind(sid, session),
            )
            for sid in ("A", "B")
        )
        return CoordinatedAutosaveRuntime(
            source_world=self.world, store=self.store,
            world_id="world-1", branch_id="source",
            participants=cohort,
            world=WorldRuntimeHooks(self.stop, self.restart),
            admission=AdmissionHooks(self.close, self.release),
        )


def test_complete_two_self_save_and_60_second_tick(tmp_path: Path):
    runtime = FakeRuntime(tmp_path)
    runner = runtime.runner()
    result = runner.run_if_due(0.0)
    assert result is not None
    assert result.sequence == 0
    assert result.saved_self_ids == ("A", "B")
    assert result.physical_action_issue_authorized is False
    assert result.historical_replay_performed is False
    assert result.live_owner_restoration_attested is False
    assert runtime.events == [
        "close", "freeze:A", "freeze:B", "world-stop",
        "world-restart", "rebind:A", "rebind:B", "release",
    ]
    assert verify_generation(result.generation)["roster"] == ["A", "B"]
    assert runner.run_if_due(59.999) is None
    assert len(runtime.events) == 8
    second = runner.run_if_due(60.0)
    assert second is not None and second.sequence == 1
    assert runner.last_verified() == second.generation
    assert not runner.held_after_failure


def test_late_future_is_discarded_on_restore_not_replayed(tmp_path: Path):
    runtime = FakeRuntime(tmp_path)
    runner = runtime.runner()
    checkpoint = runner.run_if_due(0.0)
    assert checkpoint is not None
    (runtime.world / "entities" / "r.0.0.mca").write_bytes(b"Z1-killed-after-checkpoint")
    runtime.snapshots["B"].owner_state_file.write_text("learned-post-checkpoint")
    restored = tmp_path / "restored-new-branch"
    rec = restore_generation(checkpoint.generation, restored, restore_id="rollback-1")
    assert rec["replay_performed"] is False
    assert rec["physical_action_issue_authorized"] is False
    assert (restored / "world" / "entities" / "r.0.0.mca").read_bytes() == b"Z1-is-alive"
    assert (restored / "selves" / "B" / "owner-state.json").read_text() != (
        runtime.snapshots["B"].owner_state_file.read_text()
    )


def test_inter_self_inflight_message_blocks_save_and_keeps_fence(tmp_path: Path):
    runtime = FakeRuntime(tmp_path)
    runtime.bad_frozen = "B"
    runner = runtime.runner()
    with pytest.raises(AutosaveBarrierError, match="fully frozen"):
        runner.run_if_due(0.0)
    assert runtime.events == ["close", "freeze:A", "freeze:B"]
    assert runner.held_after_failure
    assert latest_verified_generation(runtime.store) is None
    with pytest.raises(AutosaveBarrierError, match="held"):
        runner.run_if_due(60.0)


def test_late_rebind_failure_leaves_gate_closed_but_completed_generation(tmp_path: Path):
    runtime = FakeRuntime(tmp_path)
    runtime.bad_rebind = "B"
    runner = runtime.runner()
    with pytest.raises(AutosaveBarrierError, match="new native session"):
        runner.run_if_due(0.0)
    assert "release" not in runtime.events
    assert runner.held_after_failure
    assert runner.timer.last_success_monotonic is None
    assert latest_verified_generation(runtime.store) == runtime.store / "g-000000000000"


def test_paper_restart_failure_does_not_release_old_actions(tmp_path: Path):
    runtime = FakeRuntime(tmp_path)
    runtime.fail_restart = True
    runner = runtime.runner()
    with pytest.raises(AutosaveBarrierError, match="admission must remain held"):
        runner.run_if_due(0.0)
    assert "release" not in runtime.events
    assert runner.held_after_failure
    assert latest_verified_generation(runtime.store) == runtime.store / "g-000000000000"


def test_incomplete_generation_name_is_not_reused(tmp_path: Path):
    runtime = FakeRuntime(tmp_path)
    (runtime.store / "g-000000000002").mkdir()
    assert next_generation_sequence(runtime.store) == 3
    runner = runtime.runner()
    saved = runner.run_if_due(0.0)
    assert saved is not None and saved.sequence == 3
    assert (runtime.store / "g-000000000002").is_dir()
    assert latest_verified_generation(runtime.store) == saved.generation


def test_wrong_world_and_stale_session_fail_closed(tmp_path: Path):
    runtime = FakeRuntime(tmp_path)
    original = runtime.stop

    def wrong_world() -> StoppedWorldReceipt:
        return replace(original(), world_id="foreign")

    runtime.stop = wrong_world
    runner = runtime.runner()
    with pytest.raises(AutosaveBarrierError, match="stopped World receipt"):
        runner.run_if_due(0.0)
    assert latest_verified_generation(runtime.store) is None
    assert runner.held_after_failure
