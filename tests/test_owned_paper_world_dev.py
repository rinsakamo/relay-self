"""#860 owned Paper process adapter: actual local subprocess, synthetic Paper logs."""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

from relay_self.owned_paper_world_dev import (
    OwnedPaperError,
    OwnedPaperWorld,
    PaperTickReceipt,
)


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
        + ("        print('Saving worlds', flush=True)\n" if announce_save else "")
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
    assert "Saving worlds" in log and "Stopping server" in log
    restarted = adapter.runtime_hooks().restart_same_source_world()
    assert restarted.server_started
    assert restarted.new_server_session_id != first
    second = adapter.stop_and_save()
    assert second.old_server_session_id == restarted.new_server_session_id
    assert second.logical_tick == 112


def test_missing_world_save_log_is_refused_and_fenced(tmp_path):
    adapter, _, _ = _server(tmp_path, announce_save=False)
    adapter.start_owned()
    with pytest.raises(OwnedPaperError, match="clean save evidence"):
        adapter.stop_and_save()
    assert adapter.held_uncertain
    with pytest.raises(OwnedPaperError, match="uncertain"):
        adapter.restart_same_source_world()


def test_does_not_attach_or_launch_two_servers(tmp_path):
    adapter, _, _ = _server(tmp_path)
    adapter.start_owned()
    with pytest.raises(OwnedPaperError, match="duplicate"):
        adapter.start_owned()
    adapter.stop_and_save()


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
