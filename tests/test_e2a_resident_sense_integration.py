import asyncio
import json
from dataclasses import replace

import pytest

from adapters.mineflayer.process_session import MineflayerProcessSession
from relay_self.checkpoint_stop_neutralization_dev import _receive_matched
from relay_self.common_io import ScopeRef
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
                seq = 4 if command["request_id"] == "owner-probe" else 2
                process.stdout.queue.put_nowait(observation(seq, "probe", seq, command["request_id"]))

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
        process.stdout.queue.put_nowait(observation(3, "move", 3))
        await session.send_observe("owner-probe")
        process.stdout.queue.put_nowait(row({
            "type": "effect_result", "session_id": session_id, "seq": 5,
            "action_id": "stop-1", "effect": "clear_controls", "result": "applied", "error": None,
        }))
        probe = await _receive_matched(session, session_id=session_id, kind="probe",
                                       identity="owner-probe", timeout_s=1)
        assert probe.seq == 4
        assert fixture.bridge.current_sense(sid).position.x == 3
        lens = fixture.bridge.current_self_world(sid)
        assert lens.read("sense.position").value_ref.endswith(":3:position")
        assert lens.read("sense.terrain_collision").status.value == "UNKNOWN"
        ack = await _receive_matched(session, session_id=session_id, kind="stop_ack",
                                     identity="stop-1", timeout_s=1)
        assert ack.seq == 5
        assert fixture.bridge.current_sense(sid).position.x == 3
        process.stdout.queue.put_nowait(observation(6, "move", 6))
        last = await session.receive()
        assert last.seq == 6
        frame = fixture.bridge.current_sense(sid)
        assert frame.position.x == 6 and frame.nearby_entities == ()
        for forged in (
            replace(frame, scope=ScopeRef("foreign", frame.scope.world_session_id)),
            replace(frame, source_revision_ref="mineflayer:foreign:6"),
            replace(frame, observation=replace(frame.observation, session_id="foreign")),
        ):
            fixture.bridge._sense[sid] = forged
            assert fixture.bridge.current_sense(sid) is None
        fixture.bridge._sense[sid] = frame
        assert fixture.bridge.current_self_world(sid).source_revision_refs != lens.source_revision_refs
        assert fixture.bridge.current_sense(sid, max_age_s=0.000000001) is None
        session._dispatch_observer(replace(last, session_id="foreign", seq=7))
        assert fixture.bridge.current_sense(sid) == frame
        monkeypatch.setattr("relay_self.owned_resident_physical_bridge_dev.sense_from_native",
                            lambda *args, **kwargs: (_ for _ in ()).throw(RuntimeError("callback")))
        process.stdout.queue.put_nowait(observation(7, "move", 7))
        assert (await session.receive()).seq == 7
        assert isinstance(session.observer_error, RuntimeError)
        assert fixture.bridge.current_sense(sid) is None
        await fixture.bridge.logout(sid)
        assert fixture.bridge.current_sense(sid) is None

    try:
        asyncio.run(scenario())
    finally:
        fixture.stop_paper()


def test_resident_stalled_owner_coalesces_then_preserves_stop(tmp_path):
    fixture = ResidentFixture(tmp_path, 1, enable_sense=True)
    sid = fixture.names[0]
    config = fixture.configs[sid]
    session_id = "native-flood"

    def row(value):
        return (json.dumps(value) + "\n").encode()

    def observation(seq, kind, request_id=None):
        value = json.loads(observation_line())
        value.update(session_id=session_id, seq=seq, kind=kind)
        value["snapshot"]["position"]["x"] = seq
        if request_id:
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
        process.stdout.queue.put_nowait(observation(1, "spawn"))
        original_write = process.stdin.write

        def write(data):
            original_write(data)
            command = json.loads(data)
            if command["type"] == "observe" and command["request_id"] != "after-flood":
                process.stdout.queue.put_nowait(observation(2, "probe", command["request_id"]))

        process.stdin.write = write
        session = MineflayerProcessSession(process)
        session._started = await session.receive()
        async def launch(_config):
            return session
        fixture.bridge.launch = launch
        await fixture.bridge.login(sid)
        for seq in range(3, 1003):
            process.stdout.queue.put_nowait(observation(seq, "move"))
        while session._decoder.next_seq < 1003:
            await asyncio.sleep(0)
        assert session._dispatch_queue.qsize() == 256
        # The observer may see the latest event, but the owned receive
        # queue has irrecoverably compacted intermediate observations.
        # Neither L0 nor Present may call that a continuous current stream.
        assert fixture.bridge.current_sense(sid) is None
        agg = session.passive_aggregation
        assert agg.source == session_id and agg.replaced_count == 744
        assert (agg.first_replaced_seq, agg.last_replaced_seq, agg.latest_seq) == (258, 1001, 1002)
        assert agg.first_received_monotonic <= agg.latest_received_monotonic

        await session.send_observe("after-flood")
        process.stdout.queue.put_nowait(observation(1003, "probe", "after-flood"))
        process.stdout.queue.put_nowait(row({
            "type": "effect_result", "session_id": session_id, "seq": 1004,
            "action_id": "stop", "effect": "clear_controls", "result": "applied", "error": None,
        }))
        await asyncio.sleep(0)
        assert session.backpressure_hold
        probe = await _receive_matched(session, session_id=session_id, kind="probe",
                                       identity="after-flood", timeout_s=2)
        ack = await _receive_matched(session, session_id=session_id, kind="stop_ack",
                                     identity="stop", timeout_s=2)
        assert (probe.seq, ack.seq) == (1003, 1004)
        with fixture.physical.lease(self_id=sid, native_session_id=session_id,
                                    action_id="action-evidence", effect_family="NONE"):
            for seq in range(1005, 1262):
                process.stdout.queue.put_nowait(observation(seq, "move"))
            while session._decoder.next_seq < 1262:
                await asyncio.sleep(0)
            assert session.backpressure_hold
            assert session.passive_aggregation == agg
            assert [(await session.receive()).seq for _ in range(257)] == list(range(1005, 1262))
        process.stdout.queue.put_nowait(observation(1262, "probe", "settle"))
        settle = await _receive_matched(session, session_id=session_id, kind="probe",
                                        identity="settle", timeout_s=2)
        assert settle.seq == 1262
        old_world = fixture.lifecycle.world
        fixture.lifecycle._world = replace(old_world, epoch=old_world.epoch + 1)
        assert fixture.bridge.current_sense(sid) is None
        fixture.lifecycle._world = old_world
        await fixture.bridge.logout(sid)
    try:
        asyncio.run(scenario())
    finally:
        fixture.stop_paper()


def test_two_residents_rejoin_and_stream_failure_invalidate_sense(tmp_path):
    fixture = ResidentFixture(tmp_path, 2, enable_sense=True)
    processes = {}
    generation = 0

    def row(value):
        return (json.dumps(value) + "\n").encode()

    def observation(native, seq, kind, request_id=None):
        value = json.loads(observation_line())
        value.update(session_id=native, seq=seq, kind=kind)
        value["snapshot"]["position"]["x"] = seq
        if request_id:
            value["request_id"] = request_id
        return row(value)

    class Stream:
        def __init__(self):
            self.queue = asyncio.Queue()

        async def readline(self):
            return await self.queue.get()

    async def launch(config):
        nonlocal generation
        generation += 1
        native = f"{config.username}-{generation}"
        process = FakeProcess([])
        process.stdout = Stream()
        process.stdout.queue.put_nowait(row({
            "type": "adapter_started", "session_id": native, "seq": 0,
            "mineflayer_version": "4.39.0",
            "config": {"host": config.host, "port": config.port,
                       "username": config.username, "version": config.version},
        }))
        process.stdout.queue.put_nowait(observation(native, 1, "spawn"))
        original_write = process.stdin.write

        def write(data):
            original_write(data)
            command = json.loads(data)
            if command["type"] == "observe":
                process.stdout.queue.put_nowait(observation(native, 2, "probe", command["request_id"]))

        process.stdin.write = write
        session = MineflayerProcessSession(process)
        session._started = await session.receive()
        processes[config.username] = (process, session, native)
        return session

    async def wait_until(predicate):
        async with asyncio.timeout(2):
            while not predicate():
                await asyncio.sleep(0)

    async def scenario():
        fixture.bridge.launch = launch
        a, b = fixture.names
        await fixture.bridge.login(a)
        await fixture.bridge.login(b)
        pa, sa, na = processes[a]
        pb, sb, nb = processes[b]
        pa.stdout.queue.put_nowait(observation(na, 3, "move"))
        pb.stdout.queue.put_nowait(observation(nb, 3, "entities"))
        await wait_until(lambda: fixture.bridge.current_sense(a) is not None
                         and fixture.bridge.current_sense(b) is not None)
        frame_a = fixture.bridge.current_sense(a)
        frame_b = fixture.bridge.current_sense(b)
        assert frame_a.scope.self_id == a and frame_b.scope.self_id == b
        assert frame_a.observation.session_id == na and frame_b.observation.session_id == nb
        await fixture.bridge.logout(a)
        assert fixture.bridge.current_sense(a) is None
        assert fixture.bridge.current_sense(b) == frame_b
        await fixture.bridge.login(a)
        pa2, sa2, na2 = processes[a]
        assert na2 != na and fixture.bridge.current_sense(a) is None
        sa._dispatch_observer(frame_a.observation)
        assert fixture.bridge.current_sense(a) is None
        pa2.stdout.queue.put_nowait(observation(na2, 3, "move"))
        await wait_until(lambda: fixture.bridge.current_sense(a) is not None)
        new_frame = fixture.bridge.current_sense(a)
        sa._dispatch_observer(frame_a.observation)
        assert fixture.bridge.current_sense(a) == new_frame
        pa2.stdout.queue.put_nowait(observation(na2, 5, "move"))
        await wait_until(lambda: sa2._dispatch_error is not None)
        assert fixture.bridge.current_sense(a) is None
        assert fixture.bridge.current_sense(b) == frame_b
        pb.stdout.queue.put_nowait(b"")
        await wait_until(lambda: sb._dispatch_error is not None)
        assert fixture.bridge.current_sense(b) is None
        await fixture.bridge.logout(a)
        await fixture.bridge.logout(b)
    try:
        asyncio.run(scenario())
    finally:
        fixture.stop_paper()
