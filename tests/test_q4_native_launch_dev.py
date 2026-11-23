"""Q4 opt-in Native launch and forced termination; CPU fake Node only."""
from __future__ import annotations

import asyncio

import pytest

from adapters.mineflayer.process_session import (
    MineflayerProcessIOError,
    MineflayerProcessSession,
)
from adapters.mineflayer.python_protocol import MineflayerLaunchConfig
from test_mineflayer_process_session import FakeProcess, started_line


def test_q4_only_explicit_launch_controls_native_child_env(monkeypatch, tmp_path):
    bridge = tmp_path / "bridge.mjs"
    bridge.write_text("// fake")
    kwargs_seen = []
    monkeypatch.setenv("RELAY_Q4_BOUNDED_PLACE_DEV", "1")

    async def fake_create(*args, **kwargs):
        kwargs_seen.append(kwargs)
        return FakeProcess([started_line()])

    monkeypatch.setattr(asyncio, "create_subprocess_exec", fake_create)

    async def run():
        await MineflayerProcessSession.launch(
            MineflayerLaunchConfig(), bridge_path=bridge,
        )
        await MineflayerProcessSession.launch(
            MineflayerLaunchConfig(), bridge_path=bridge,
            enable_q4_bounded_place_dev=True,
        )
        with pytest.raises(Exception, match="explicit boolean"):
            await MineflayerProcessSession.launch(
                MineflayerLaunchConfig(), bridge_path=bridge,
                enable_q4_bounded_place_dev=1,
            )

    asyncio.run(run())
    assert "RELAY_Q4_BOUNDED_PLACE_DEV" not in kwargs_seen[0]["env"]
    assert kwargs_seen[1]["env"]["RELAY_Q4_BOUNDED_PLACE_DEV"] == "1"


class StubbornProcess(FakeProcess):
    def __init__(self, *, kill_exits=True):
        super().__init__([started_line()])
        self.kill_exits = kill_exits
        self.kill_count = 0

    def terminate(self):
        self.terminated = True

    async def wait(self):
        if self.returncode is not None:
            return self.returncode
        await asyncio.sleep(5)
        return self.returncode

    def kill(self):
        self.kill_count += 1
        if self.kill_exits:
            self.returncode = -9


def test_q4_bounded_term_escalates_to_kill_on_timeout():
    process = StubbornProcess()
    session = MineflayerProcessSession(process)
    result = asyncio.run(session.force_terminate_owned(timeout_s=0.01))
    assert result == -9
    assert process.terminated
    assert process.kill_count == 1
    assert session.process_returncode == -9


def test_q4_force_termination_without_exit_is_explicit_hold():
    process = StubbornProcess(kill_exits=False)
    session = MineflayerProcessSession(process)
    with pytest.raises(MineflayerProcessIOError, match="not confirmed"):
        asyncio.run(session.force_terminate_owned(timeout_s=0.01))
    assert process.terminated
    assert process.kill_count == 1
    assert session.process_returncode is None
