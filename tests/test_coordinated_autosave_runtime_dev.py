"""#860 staged autosave barrier: synthetic callbacks, NEVER a live Paper trial."""
from __future__ import annotations

import asyncio
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
        old_native = (
            f"native-before-{sid}" if self.session_no == 0
            else f"native-after-{sid}-{self.session_no}"
        )
        receipt = SelfFrozenReceipt(
            sid, self.snapshots[sid], old_native,
            f"frozen:{sid}:{generation}", (), (), True, True, True,
        )
        if self.bad_frozen == sid:
            return replace(receipt, undelivered_message_ids=("msg-undelivered",))
        if self.bad_frozen == "stale_" + sid:
            return replace(receipt, old_native_session_id="stale-unqualified-session")
        return receipt

    def stop(self) -> StoppedWorldReceipt:
        self.events.append("world-stop")
        assert self.events[-3:-1] == ["freeze:A", "freeze:B"]
        old_server = "paper-old" if self.session_no == 0 else f"paper-new-{self.session_no}"
        return StoppedWorldReceipt(
            "world-1", "source", old_server, 100 + self.session_no,
            "paper:tick-100", "paper:clean-stop", 0, True,
        )

    def restart(self) -> RestartedWorldReceipt:
        self.events.append("world-restart")
        if self.fail_restart:
            raise RuntimeError("Paper did not return")
        self.session_no += 1
        return RestartedWorldReceipt(
            "world-1", "source", f"paper-new-{self.session_no}", True,
        )

    def rebind(self, sid: str, session: str) -> ReboundSelfReceipt:
        self.events.append("rebind:" + sid)
        assert session == f"paper-new-{self.session_no}"
        receipt = ReboundSelfReceipt(
            sid, f"native-after-{sid}-{self.session_no}", "world-1", "source",
            True, True, True, True,
        )
        if self.bad_rebind == sid:
            return replace(receipt, old_session_invalidated=False)
        return receipt

    def runner(self, *, paper_layout: bool = False) -> CoordinatedAutosaveRuntime:
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
            paper_layout=paper_layout,
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


def test_previous_self_session_is_required_at_next_generation(tmp_path: Path):
    runtime = FakeRuntime(tmp_path)
    runner = runtime.runner()
    assert runner.run_if_due(0.0) is not None
    runtime.bad_frozen = "stale_B"
    with pytest.raises(AutosaveBarrierError, match="session changed"):
        runner.run_if_due(60.0)
    assert runner.held_after_failure
    assert "release" not in runtime.events[8:]
    assert next_generation_sequence(runtime.store) == 1


def test_paper_two_generation_dimension_roster_is_pinned_before_commit(tmp_path: Path):
    runtime = FakeRuntime(tmp_path)
    paper = tmp_path / "world"
    runtime.world.rename(paper)
    runtime.world = paper
    for name in ("world_nether", "world_the_end"):
        directory = tmp_path / name
        directory.mkdir()
        (directory / "level.dat").write_bytes(("first-" + name).encode())
    runner = runtime.runner(paper_layout=True)
    first = runner.run_if_due(0.0)
    assert first is not None
    assert verify_generation(first.generation)["schema"] == 2
    assert runner.run_if_due(30.0) is None
    (tmp_path / "world_the_end" / "level.dat").write_bytes(b"second-end")
    second = runner.run_if_due(60.0)
    assert second is not None
    assert verify_generation(second.generation)["schema"] == 2
    assert set(verify_generation(second.generation)["paper_dimensions"]) == {
        "world_nether", "world_the_end"
    }
    # A disappearing dimension must not become a newer committed cut.
    import shutil

    shutil.rmtree(tmp_path / "world_nether")
    with pytest.raises(AutosaveBarrierError, match="dimension roster changed"):
        runner.run_if_due(120.0)
    assert runner.held_after_failure
    assert runner.last_verified() == second.generation
    assert not (runtime.store / "g-000000000002" / "COMMITTED.json").exists()


def test_async_native_rejoin_waits_for_both_before_release(tmp_path: Path):
    runtime = FakeRuntime(tmp_path)
    runner = runtime.runner()
    events = []

    async def prepare(sid: str, paper: str, old: str) -> str:
        assert paper == "paper-new-1"
        assert old == f"native-before-{sid}"
        assert runtime.events[-1] in {"world-restart", "rebind:A"}
        events.append("prepared:" + sid)
        await asyncio.sleep(0)
        assert "release" not in runtime.events
        return f"native-after-{sid}-1"

    result = asyncio.run(runner.run_if_due_async(0.0, prepare_rejoin=prepare))
    assert result is not None
    assert events == ["prepared:A", "prepared:B"]
    assert runner.timer.last_success_monotonic == 0.0
    assert runner.last_verified() == result.generation
    assert runtime.events[-3:] == ["rebind:A", "rebind:B", "release"]


def test_async_native_rejoin_failure_keeps_gate_closed_with_committed_cut(tmp_path: Path):
    runtime = FakeRuntime(tmp_path)
    runner = runtime.runner()
    async def prepare(sid: str, paper: str, old: str) -> str:
        assert old == f"native-before-{sid}"
        if sid == "B":
            raise ConnectionError("native B never respawned")
        return "native-after-A-1"

    with pytest.raises(AutosaveBarrierError, match="rejoin failed"):
        asyncio.run(runner.run_if_due_async(0.0, prepare_rejoin=prepare))
    assert runner.held_after_failure
    assert runtime.events[-1] == "world-restart"
    assert runner.timer.last_success_monotonic is None
    assert runner.last_verified() == runtime.store / "g-000000000000"


def test_async_native_rejoin_rejects_mismatched_owner_and_duplicate(tmp_path: Path):
    runtime = FakeRuntime(tmp_path)
    runner = runtime.runner()
    async def prepare(sid: str, paper: str, old: str) -> str:
        return "not-owner-session" if sid == "A" else "native-after-B-1"

    with pytest.raises(AutosaveBarrierError, match="owner rebind differs"):
        asyncio.run(runner.run_if_due_async(0.0, prepare_rejoin=prepare))
    assert runner.held_after_failure
    assert "release" not in runtime.events


def test_async_native_rejoin_cancellation_holds_without_implicit_retry(tmp_path: Path):
    runtime = FakeRuntime(tmp_path)
    runner = runtime.runner()
    async def prepare(sid: str, paper: str, old: str) -> str:
        raise asyncio.CancelledError()

    with pytest.raises(AutosaveBarrierError, match="rejoin failed"):
        asyncio.run(runner.run_if_due_async(0.0, prepare_rejoin=prepare))
    assert runner.held_after_failure
    assert runner.timer.last_success_monotonic is None
    assert "release" not in runtime.events


def test_async_native_rejoin_timeout_holds_without_release(tmp_path: Path):
    runtime = FakeRuntime(tmp_path)
    runner = runtime.runner()

    async def stalled(sid: str, paper: str, old: str) -> str:
        await asyncio.Event().wait()
        return "never"

    with pytest.raises(AutosaveBarrierError, match="rejoin failed"):
        asyncio.run(runner.run_if_due_async(
            0.0, prepare_rejoin=stalled, native_rejoin_timeout_s=0.02,
        ))
    assert runner.held_after_failure
    assert runner.timer.last_success_monotonic is None
    assert "release" not in runtime.events
