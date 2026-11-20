import asyncio
import json
from dataclasses import replace

import pytest

from adapters.mineflayer.process_session import MineflayerProcessSession
from relay_self.checkpoint_stop_neutralization_dev import _receive_matched
from test_mineflayer_process_session import FakeProcess, observation_line
from test_p0d_resident_physical_issuer_dev import ResidentFixture


@pytest.mark.parametrize("enabled", [True, False])
def test_resident_login_dispatches_same_stream_to_owner_and_sense(tmp_path, monkeypatch, enabled):
    fixture = ResidentFixture(tmp_path, 1, enable_sense=enabled)
    sid = fixture.names[0]
    config = fixture.configs[sid]
    session_id = "native-integration"

    def row(value):
        return (json.dumps(value) + "\n").encode()

    def observation(seq, kind, x, request_id=None):
        value = json.loads(observation_line())
        value.update(session_id=session_id, seq=seq, kind=kind)
        value["snapshot"]["position"]["x"] = x
        if request_id is not None:
            value["request_id"] = request_id
        return row(value)

    class Stream:
        def __init__(self):
            self.queue = asyncio.Queue()

        async def readline(self):
            return await self.queue.get()

    async def scenario():
        process = FakeProcess([])
        process.stdout = Stream()
        process.stdout.queue.put_nowait(row({
            "type": "adapter_started", "session_id": session_id, "seq": 0,
            "mineflayer_version": "4.39.0",
            "config": {"host": config.host, "port": config.port,
                       "username": config.username, "version": config.version},
        }))
        process.stdout.queue.put_nowait(observation(1, "spawn", 1))
        original_write = process.stdin.write

        def write(data):
            original_write(data)
            command = json.loads(data)
            if command["type"] == "observe":
                process.stdout.queue.put_nowait(observation(2, "probe", 1, command["request_id"]))

        process.stdin.write = write
        session = MineflayerProcessSession(process)
        session._started = await session.receive()

        async def launch(_config):
            return session

        fixture.bridge.launch = launch
        await fixture.bridge.login(sid)
        assert fixture.bridge.current_sense(sid) is None
        if not enabled:
            assert session._dispatch_task is None
            process.stdout.queue.put_nowait(observation(3, "move", 3))
            assert (await session.receive()).seq == 3
            assert fixture.bridge.current_sense(sid) is None
            await fixture.bridge.logout(sid)
            return
        for value in (
            observation(3, "move", 3),
            observation(4, "probe", 4, "owner-probe"),
            row({"type": "effect_result", "session_id": session_id, "seq": 5,
                 "action_id": "stop-1", "effect": "clear_controls", "result": "applied", "error": None}),
        ):
            process.stdout.queue.put_nowait(value)
        probe = await _receive_matched(session, session_id=session_id, kind="probe",
                                       identity="owner-probe", timeout_s=1)
        assert probe.seq == 4
        assert fixture.bridge.current_sense(sid).position.x == 3
        ack = await _receive_matched(session, session_id=session_id, kind="stop_ack",
                                     identity="stop-1", timeout_s=1)
        assert ack.seq == 5
        assert fixture.bridge.current_sense(sid).position.x == 3
        process.stdout.queue.put_nowait(observation(6, "move", 6))
        last = await session.receive()
        assert last.seq == 6
        frame = fixture.bridge.current_sense(sid)
        assert frame.position.x == 6 and frame.nearby_entities == ()
        session._dispatch_observer(replace(last, session_id="foreign", seq=7))
        assert fixture.bridge.current_sense(sid) == frame
        monkeypatch.setattr("relay_self.owned_resident_physical_bridge_dev.sense_from_native",
                            lambda *args, **kwargs: (_ for _ in ()).throw(RuntimeError("callback")))
        process.stdout.queue.put_nowait(observation(7, "move", 7))
        assert (await session.receive()).seq == 7
        assert isinstance(session.observer_error, RuntimeError)
        assert fixture.bridge.current_sense(sid) == frame
        await fixture.bridge.logout(sid)
        assert fixture.bridge.current_sense(sid) is None

    try:
        asyncio.run(scenario())
    finally:
        fixture.stop_paper()
