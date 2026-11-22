"""#860 owned Paper process adapter: actual local subprocess, synthetic Paper logs."""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

from relay_self.coordinated_autosave_runtime_dev import (
    AdmissionCloseReceipt,
    AdmissionHooks,
    CoordinatedAutosaveRuntime,
    ReboundSelfReceipt,
    SelfFrozenReceipt,
    SelfRuntimeHooks,
)
from relay_self.coordinated_checkpoint_dev import (
    SelfSnapshotSource,
    restore_generation,
    verify_generation,
)
from relay_self.owned_paper_world_dev import (
    OwnedPaperError,
    OwnedPaperWorld,
    PaperTickReceipt,
)
from relay_self.persistent_cognition import (
    IdentitySpecification,
    PersistentCognition,
    save_persistent_cognition,
)
from relay_self.physical_action_journal import PhysicalActionJournal
from relay_self.provenance import Provenance


def _server(tmp_path: Path, *, announce_save: bool = True):
    server = tmp_path / "paper-server"
    server.mkdir()
    world = server / "world"
    world.mkdir()
    (world / "level.dat").write_bytes(b"fake-minecraft-level")
    evidence = tmp_path / "evidence"
    evidence.mkdir()
    script = server / "paper_faux.py"
    script.write_text(
        "import sys\n"
        "print('Done (0.8s)! For help, type \"help\"', flush=True)\n"
        "for line in sys.stdin:\n"
        "    if line.strip() == 'save-all flush':\n"
        + ("        print('Saved the game', flush=True)\n" if announce_save else "        pass\n")
        + "    if line.strip() == 'stop':\n"
        "        print('Stopping server', flush=True)\n"
        "        sys.exit(0)\n",
        encoding="utf-8",
    )
    tick_reads: list[str] = []

    def tick_source(session: str) -> PaperTickReceipt:
        tick_reads.append(session)
        return PaperTickReceipt(session, 110 + len(tick_reads), "faux-server-tick")

    adapter = OwnedPaperWorld(
        server_dir=server, world_dir=world, evidence_dir=evidence,
        command=(sys.executable, "-u", str(script)),
        world_id="world-1", branch_id="source",
        tick_readback=tick_source, timeout_seconds=3.0,
    )
    return adapter, tick_reads, evidence


def test_owned_process_stops_saves_then_restarts_new_session(tmp_path):
    adapter, ticks, evidence = _server(tmp_path)
    first = adapter.start_owned()
    assert first.startswith("paper-owned-")
    assert adapter.owned_session_id == first
    receipt = adapter.runtime_hooks().stop_and_save()
    assert receipt.old_server_session_id == first
    assert receipt.process_exit_code == 0
    assert receipt.all_dimensions_saved
    assert receipt.logical_tick == 111
    assert receipt.tick_source_ref == "faux-server-tick"
    assert ticks == [first]
    assert adapter.owned_session_id is None
    assert not adapter.held_uncertain
    log = (evidence / (first + ".log")).read_text()
    assert "Saved the game" in log and "Stopping server" in log
    restarted = adapter.runtime_hooks().restart_same_source_world()
    assert restarted.server_started
    assert restarted.new_server_session_id != first
    second = adapter.stop_and_save()
    assert second.old_server_session_id == restarted.new_server_session_id
    assert second.logical_tick == 112


def test_missing_world_save_log_is_refused_and_fenced(tmp_path):
    adapter, _, _ = _server(tmp_path, announce_save=False)
    adapter.start_owned()
    try:
        with pytest.raises(OwnedPaperError, match="flush completion"):
            adapter.stop_and_save()
    finally:
        assert adapter._process is not None and adapter._process.stdin is not None
        adapter._process.stdin.write(b"stop\n")
        adapter._process.stdin.flush()
        adapter._process.wait(timeout=3)
        adapter._process.stdin.close()
    assert adapter.held_uncertain
    with pytest.raises(OwnedPaperError, match="uncertain"):
        adapter.restart_same_source_world()


def test_does_not_attach_or_launch_two_servers(tmp_path):
    adapter, _, _ = _server(tmp_path)
    adapter.start_owned()
    with pytest.raises(OwnedPaperError, match="duplicate"):
        adapter.start_owned()
    adapter.stop_and_save()


def test_start_failure_holds_without_issuing_save(tmp_path):
    adapter, _, _ = _server(tmp_path)
    adapter.command = (sys.executable, "-c", "raise SystemExit(7)")
    with pytest.raises(OwnedPaperError, match="exited before readiness"):
        adapter.start_owned()
    assert adapter.held_uncertain


def test_abnormal_exit_after_flush_is_not_clean_stop(tmp_path):
    adapter, _, _ = _server(tmp_path)
    adapter.command = (sys.executable, "-u", "-c", (
        "import sys\nprint('Done (',flush=True)\n"
        "for line in sys.stdin:\n"
        " if line.strip()=='save-all flush': print('Saved the game',flush=True)\n"
        " if line.strip()=='stop': print('Stopping server',flush=True); sys.exit(7)\n"
    ))
    adapter.start_owned()
    with pytest.raises(OwnedPaperError, match="clean save evidence"):
        adapter.stop_and_save()
    assert adapter.held_uncertain


def test_wrong_server_tick_session_cannot_stop(tmp_path):
    adapter, _, _ = _server(tmp_path)
    adapter.start_owned()
    adapter.tick_readback = lambda _session: PaperTickReceipt(
        "another-server-session", 105, "foreign-tick",
    )
    try:
        with pytest.raises(OwnedPaperError, match="server-qualified tick"):
            adapter.stop_and_save()
    finally:
        # Test cleanup only. Production never sends an unqualified stop.
        assert adapter._process is not None
        assert adapter._process.stdin is not None
        adapter._process.stdin.write(b"stop\n")
        adapter._process.stdin.flush()
        assert adapter._process.wait(timeout=3) == 0
        adapter._process.stdin.close()


def test_owned_process_end_to_end_two_self_checkpoint_control(tmp_path: Path):
    """Real subprocess lifecycle + simulated (not actual) two-Self owner hooks."""
    adapter, _, _ = _server(tmp_path)
    initial_paper_session = adapter.start_owned()
    root = tmp_path / "owner-files"
    root.mkdir()
    store = tmp_path / "store"
    store.mkdir()
    snapshots: dict[str, SelfSnapshotSource] = {}
    current_sessions: dict[str, str] = {}
    for sid in ("A", "B"):
        d = root / sid
        d.mkdir()
        cog = d / "cognition.json"
        save_persistent_cognition(
            cog,
            PersistentCognition(
                IdentitySpecification(
                    sid, ("Keep memory from last completed generation.",),
                    Provenance("fixture", sid),
                ),
            ),
        )
        wal = d / "physical-wal.json"
        PhysicalActionJournal.create(wal, self_id=sid)
        owner = d / "owner-state.json"
        owner.write_text('{"test_only":"opaque owner state"}')
        snapshots[sid] = SelfSnapshotSource(sid, cog, wal, owner)
        current_sessions[sid] = f"native-initial-{sid}"
    gate = {"closed": False}
    calls: list[str] = []

    def close() -> AdmissionCloseReceipt:
        assert not gate["closed"]
        gate["closed"] = True
        calls.append("close")
        return AdmissionCloseReceipt("gate-token", True, True, True)

    def release(token: str) -> None:
        assert gate["closed"] and token == "gate-token"
        calls.append("release")
        gate["closed"] = False

    def freeze(sid: str, generation: str) -> SelfFrozenReceipt:
        assert gate["closed"]
        calls.append("freeze:" + sid)
        return SelfFrozenReceipt(
            sid, snapshots[sid], current_sessions[sid],
            generation + ":" + sid, (), (), True, True, True,
        )

    def rebind(sid: str, paper_session: str) -> ReboundSelfReceipt:
        assert gate["closed"]
        calls.append("rebind:" + sid)
        current_sessions[sid] = f"native:{sid}:{paper_session}"
        return ReboundSelfReceipt(
            sid, current_sessions[sid], "world-1", "source",
            True, True, True, True,
        )

    runtime = CoordinatedAutosaveRuntime(
        source_world=adapter.world_dir, store=store,
        world_id="world-1", branch_id="source",
        participants=tuple(
            SelfRuntimeHooks(
                sid,
                lambda gen, sid=sid: freeze(sid, gen),
                lambda session, sid=sid: rebind(sid, session),
            )
            for sid in ("A", "B")
        ),
        world=adapter.runtime_hooks(),
        admission=AdmissionHooks(close, release),
    )
    try:
        first = runtime.run_if_due(0.0)
        assert first is not None
        assert first.sequence == 0
        assert verify_generation(first.generation)["roster"] == ["A", "B"]
        assert adapter.owned_session_id != initial_paper_session
        assert runtime.run_if_due(59.99) is None
        assert calls == [
            "close", "freeze:A", "freeze:B",
            "rebind:A", "rebind:B", "release",
        ]
        second = runtime.run_if_due(60.0)
        assert second is not None
        assert second.sequence == 1
        assert second.generation != first.generation
        assert calls.count("release") == 2
        assert not runtime.held_after_failure
        # Later changes must not affect the original committed generation.
        (adapter.world_dir / "level.dat").write_bytes(b"future-changed")
        restored = tmp_path / "new-fork"
        result = restore_generation(first.generation, restored, restore_id="rollback-1")
        assert result["replay_performed"] is False
        assert (restored / "world" / "level.dat").read_bytes() == b"fake-minecraft-level"
    finally:
        # Cleanup only our owned fake server, not any independently launched process.
        if adapter.owned_session_id is not None:
            adapter.stop_and_save()
