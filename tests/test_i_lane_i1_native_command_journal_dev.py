"""I1 original Mineflayer stdin bytes journal; no World or second sender."""
from __future__ import annotations

import asyncio
import json

import pytest

from adapters.mineflayer.process_session import (
    MineflayerProcessIOError,
    MineflayerProcessSession,
)
from test_mineflayer_process_session import FakeProcess, started_line


def test_i1_raw_original_stdin_audit_records_only_successfully_drained_bytes(tmp_path):
    async def scenario():
        process = FakeProcess([started_line()])
        session = MineflayerProcessSession(process)
        with pytest.raises(MineflayerProcessIOError):
            session.start_raw_command_audit(tmp_path / "early.jsonl")
        session._started = await session.receive()
        journal = tmp_path / "commands.jsonl"
        session.start_raw_command_audit(journal)
        with pytest.raises(MineflayerProcessIOError):
            session.start_raw_command_audit(tmp_path / "second.jsonl")
        await session.send_observe("p0d-rejoin-0123456789abcdef0123456789abcdef")
        await session.send_observe("i1-original-sense-0123456789abcdef0123456789abcdef")
        session.finish_raw_command_audit()
        assert journal.read_bytes() == b"".join(process.stdin.writes)
        assert [json.loads(x) for x in journal.read_bytes().splitlines()] == [
            {"type": "observe", "request_id": "p0d-rejoin-0123456789abcdef0123456789abcdef"},
            {"type": "observe", "request_id": "i1-original-sense-0123456789abcdef0123456789abcdef"},
        ]
        with pytest.raises(MineflayerProcessIOError):
            session.finish_raw_command_audit()
        with pytest.raises(MineflayerProcessIOError):
            session.start_raw_command_audit(tmp_path / "after.jsonl")
    asyncio.run(scenario())


def test_i1_original_stdin_journal_cannot_record_failed_pipe_write(tmp_path):
    async def scenario():
        process = FakeProcess([started_line()])
        session = MineflayerProcessSession(process)
        session._started = await session.receive()
        path = tmp_path / "undelivered.jsonl"
        session.start_raw_command_audit(path)

        async def fail_drain():
            raise BrokenPipeError("original Mineflayer pipe closed")

        process.stdin.drain = fail_drain
        with pytest.raises(MineflayerProcessIOError, match="stdin"):
            await session.send_observe("i1-original-sense-0123456789abcdef0123456789abcdef")
        session.finish_raw_command_audit()
        assert path.read_bytes() == b""
    asyncio.run(scenario())


def test_i1_original_stdin_journal_write_failure_fails_closed(tmp_path, monkeypatch):
    async def scenario():
        process = FakeProcess([started_line()])
        session = MineflayerProcessSession(process)
        session._started = await session.receive()
        path = tmp_path / "transcript.jsonl"
        session.start_raw_command_audit(path)
        from adapters.mineflayer import process_session as native

        real_write = native.os.write

        def truncated(fd, raw):
            if fd == session._raw_command_audit_fd:
                return 0
            return real_write(fd, raw)

        monkeypatch.setattr(native.os, "write", truncated)
        with pytest.raises(MineflayerProcessIOError, match="command evidence"):
            await session.send_observe("i1-original-sense-0123456789abcdef0123456789abcdef")
        assert process.stdin.writes  # a possibly delivered request MUST become HOLD
        monkeypatch.setattr(native.os, "write", real_write)
        session.finish_raw_command_audit()
        assert path.read_bytes() == b""
    asyncio.run(scenario())
