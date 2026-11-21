"""I1 original single decoder active read-only SENSE, no real World or GPU."""
import asyncio
import json
from types import SimpleNamespace

import pytest

from adapters.mineflayer.process_session import MineflayerProcessSession
from adapters.mineflayer.python_protocol import MINEFLAYER_VERSION
from relay_self.owned_resident_physical_bridge_dev import OwnedResidentBridgeError
from test_bd1b_owner_present_dev import _configured
from test_bd1b_owner_source_dev import _files
from test_mineflayer_process_session import FakeProcess, observation_line


def _line(value):
    return (json.dumps(value) + "\n").encode()


def _observation(session, seq, kind, request_id=None):
    row = json.loads(observation_line())
    row.update(session_id=session, seq=seq, kind=kind)
    if request_id is not None:
        row["request_id"] = request_id
    return _line(row)


@pytest.mark.parametrize("wrong_reply", [False, True])
def test_original_native_read_only_probe_is_matched_and_source_fenced(
    tmp_path, monkeypatch, wrong_reply,
):
    case = _configured(tmp_path, monkeypatch, need=True)
    bridge, world = case[1], case[3]
    files = _files(bridge)
    config = bridge.configs["A"]
    native = bridge.sessions["A"].started.session_id

    class Stream:
        def __init__(self):
            self.queue = asyncio.Queue()

        async def readline(self):
            return await self.queue.get()

    async def scenario():
        process = FakeProcess([])
        process.pid = 7000
        process.stdout = Stream()
        process.stdout.queue.put_nowait(_line({
            "type": "adapter_started", "session_id": native, "seq": 0,
            "mineflayer_version": MINEFLAYER_VERSION,
            "config": {"host": config.host, "port": config.port,
                       "username": config.username, "version": config.version},
        }))
        session = MineflayerProcessSession(process)
        session._started = await session.receive()
        process.stdout.queue.put_nowait(_observation(native, 1, "spawn"))
        original_request = bridge.last_login_observations["A"].request_id
        process.stdout.queue.put_nowait(
            _observation(native, 2, "probe", original_request),
        )
        observed = 2
        write = process.stdin.write

        def reply(data):
            nonlocal observed
            write(data)
            command = json.loads(data)
            assert command["type"] == "observe"  # never a Physical effect
            observed += 1
            req = ("forged" if wrong_reply else command["request_id"])
            process.stdout.queue.put_nowait(
                _observation(native, observed, "probe", req),
            )

        process.stdin.write = reply
        bridge.sessions["A"] = session
        bridge.enable_sense = True
        bridge._sense = {}
        bridge._sense_received_at = {}
        bridge._sense_refreshing = set()
        bridge._i1_correlated_sense = {}
        bridge._i1_correlated_received_at = {}
        bridge._start_sense("A", session, SimpleNamespace(world=world))
        assert bridge._sense["A"].source_revision_ref == f"mineflayer:{native}:2"
        for _ in range(2):
            await asyncio.wait_for(session.receive(), 1)
        if wrong_reply:
            with pytest.raises(Exception):
                await bridge.refresh_i1_read_only_sense("A", timeout_s=0.3)
            assert bridge._sense["A"].observation.seq == 2
            assert bridge.current_i1_correlated_sense("A") is None
        else:
            first = await bridge.refresh_i1_read_only_sense("A", timeout_s=0.8)
            assert first.observation.seq == 3
            assert first.source_revision_ref == f"mineflayer:{native}:3"
            assert bridge.current_i1_correlated_sense("A") is first
            next_frame = await bridge.refresh_i1_read_only_sense("A", timeout_s=0.8)
            assert next_frame.observation.seq == 4
            assert bridge.current_sense("A") is next_frame
            assert bridge.current_i1_correlated_sense("A") is next_frame
            assert bridge._sense_refreshing == set()
            bridge.cognitive_work.fence_self("A")
            assert bridge.current_sense("A") is None
            assert bridge.current_i1_correlated_sense("A") is None
            with pytest.raises((OwnedResidentBridgeError, RuntimeError)):
                await bridge.refresh_i1_read_only_sense("A", timeout_s=0.3)
        await session.terminate()

    asyncio.run(scenario())
    assert _files(bridge) == files
