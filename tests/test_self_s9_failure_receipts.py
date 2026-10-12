"""S9 prospective exceptional-retention receipts; fake process boundaries only.

Exercises retained S3 state after a failed owned World session. Never launches
Minecraft/Node, requests an Action, or reconstructs consumed S8 physical bytes.
"""
from __future__ import annotations

import asyncio
import json
from types import SimpleNamespace

import pytest

from adapters.mineflayer import self_s1_runtime as s1
from adapters.mineflayer.self_continuous_host import SessionBudget
from relay_self.persistent_cognition import load_persistent_cognition
from relay_self.reactive_l0 import ReactiveL0Rejected
from test_self_s3_experience import fixture as qualified_synthetic_receipt


def _fake_failed_run(tmp_path, monkeypatch):
    receipt, probe = qualified_synthetic_receipt()
    output = tmp_path / "empty-external"
    output.mkdir()
    original_experience = s1.S3ReadOnlyExperience

    class PreloadedExperience(original_experience):
        def __init__(self, session_id):
            super().__init__(session_id)
            assert session_id == probe.session_id
            self.observe_original(
                receipt, correlated_probe=probe,
                expected_action_id=receipt.terminal.action_id,
            )

    class FakeSession:
        started = SimpleNamespace(session_id=probe.session_id)

        async def shutdown(self, **kwargs):
            return 0

    class FakeDriver:
        def __init__(self, host, session, budget, sink):
            self.sink = sink

        async def run(self, **kwargs):
            self.sink.write("session_failed", reason="ReactiveL0Rejected", no_replay=True)
            self.sink.close()
            raise ReactiveL0Rejected("fresh uniquely identified zombie not evidenced")

        def stop(self):
            pass

    fake_server = SimpleNamespace(returncode=None)

    async def fake_ready(*args):
        return fake_server, None, None

    async def fake_shutdown(*args):
        fake_server.returncode = 0

    async def fake_launch(*args, **kwargs):
        return FakeSession()

    async def fake_spawn(*args):
        return None

    monkeypatch.setattr(s1, "S3ReadOnlyExperience", PreloadedExperience)
    monkeypatch.setattr(s1, "BoundedSessionDriver", FakeDriver)
    monkeypatch.setattr(s1, "prepare_stopped_world", lambda *a, **k: None)
    monkeypatch.setattr(s1, "_ready_server", fake_ready)
    monkeypatch.setattr(s1, "_shutdown_server", fake_shutdown)
    monkeypatch.setattr(s1, "_await_spawn", fake_spawn)
    monkeypatch.setattr(s1.MineflayerProcessSession, "launch", fake_launch)

    async def run():
        return await s1.run_physical(
            object(), output,
            SessionBudget(max_events=2, max_actions=1,
                          max_frames=4, max_seconds=2),
        )

    return run, output


def test_exception_retains_only_current_in_memory_s3_and_preserves_primary_error(
    tmp_path, monkeypatch,
):
    run, output = _fake_failed_run(tmp_path, monkeypatch)
    with pytest.raises(ReactiveL0Rejected, match="fresh uniquely"):
        asyncio.run(run())
    partial = output / "s9_partial_observed_memory_on_failure.json"
    assert partial.is_file()
    assert len(load_persistent_cognition(partial).memories) == 1
    assert not (output / "s3_observed_memory.json").exists()
    cleanup = json.loads((output / "owned_cleanup.json").read_text())
    assert cleanup["node_exit"] == cleanup["server_exit"] == 0
    assert cleanup["native_stop_ack"] is False
    assert not (output / "s9_partial_memory_save_failure.json").exists()


def test_failed_partial_memory_write_cannot_mask_original_world_exception(
    tmp_path, monkeypatch,
):
    run, output = _fake_failed_run(tmp_path, monkeypatch)

    def fail_save(*args):
        raise OSError("synthetic partial receipt storage failure")

    monkeypatch.setattr(s1, "save_persistent_cognition", fail_save)
    with pytest.raises(ReactiveL0Rejected, match="fresh uniquely"):
        asyncio.run(run())
    assert not (output / "s9_partial_observed_memory_on_failure.json").exists()
    failure = json.loads(
        (output / "s9_partial_memory_save_failure.json").read_text()
    )
    assert failure["reason_type"] == "OSError"
    assert failure["primary_reason_type"] == "ReactiveL0Rejected"
    assert failure["retained_observation_count"] == 1
    assert json.loads((output / "owned_cleanup.json").read_text())["server_exit"] == 0
