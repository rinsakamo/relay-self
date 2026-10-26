"""DEV source-liveness gate: no next S49 Action after native disconnect."""
from __future__ import annotations

import asyncio
from collections import deque
from dataclasses import replace
from types import SimpleNamespace

import pytest

import test_t1f_t2_dev as t1f
from adapters.mineflayer.process_session import MineflayerProcessEnded
from adapters.mineflayer.python_protocol import (
    MineflayerAdapterErrorMessage,
    MineflayerCommandError,
    MineflayerConnectionEnd,
    MineflayerShutdownAck,
)
from adapters.mineflayer.t1f_continuation_dev import next_tick


class Stream:
    def __init__(self, frames):
        self.frames = deque(frames)
        self.started = SimpleNamespace(session_id="test-session")
        self.tick_owner = SimpleNamespace(failed=False)

    async def receive(self):
        if self.frames:
            item = self.frames.popleft()
            if isinstance(item, Exception):
                raise item
            return item
        await asyncio.sleep(10)


def run(session, timeout=0.02):
    return asyncio.run(next_tick(session, timeout=timeout))


@pytest.mark.parametrize("message", [
    MineflayerConnectionEnd("test-session", 20, "link lost"),
    MineflayerAdapterErrorMessage("test-session", 20, "adapter fault"),
    MineflayerCommandError("test-session", 20, "protocol fault"),
    MineflayerShutdownAck("test-session", 20),
])
def test_terminal_and_shutdown_frames_latch_owner_before_new_action(message):
    s = Stream([message, t1f.frame()])
    with pytest.raises(RuntimeError, match="T1g terminal native frame"):
        run(s)
    assert s.tick_owner.failed
    assert len(s.frames) == 1


def test_source_eof_latches_current_t2_owner():
    s = Stream([MineflayerProcessEnded("native stdout ended")])
    with pytest.raises(MineflayerProcessEnded):
        run(s)
    assert s.tick_owner.failed


def test_no_tick_timeout_latches_owner_instead_of_granting_wait():
    s = Stream([])
    with pytest.raises(TimeoutError):
        run(s)
    assert s.tick_owner.failed


def test_foreign_paper_session_rejects_without_consuming_an_epoch():
    s = Stream([replace(t1f.frame(), session_id="foreign")])
    with pytest.raises(RuntimeError, match="foreign T1g Paper session"):
        run(s)
    assert s.tick_owner.failed


def test_nonadmitted_source_latches_and_blocks_accounting():
    s = Stream([t1f.frame(status="STALE")])
    with pytest.raises(ValueError, match="T1f refusal"):
        run(s)
    assert s.tick_owner.failed


def test_admitted_real_paper_snapshot_can_resume_but_never_qualifies_stop():
    s = Stream([t1f.frame()])
    f = run(s)
    assert f.session_id == "test-session"
    assert not s.tick_owner.failed


def test_stale_old_seq_cannot_hide_a_later_disconnect():
    s = Stream([t1f.frame(seq=10), MineflayerConnectionEnd(
        "test-session", 20, "end"
    )])
    with pytest.raises(RuntimeError):
        asyncio.run(next_tick(s, after_seq=10, timeout=0.02))
    assert s.tick_owner.failed
