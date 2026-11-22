"""E2 CPU/offline: only the ORIGINAL I2/B owner and dispatcher can publish SENSE.

All Paper/Native rows here are synthetic. No physical commands, Minecraft,
Memory owner, or alternate receive task is added by the E adapter.
"""
from __future__ import annotations

import asyncio
import json
import time

import pytest

from adapters.mineflayer.process_session import (
    MineflayerProcessSession,
    NativeReceiveContinuityHold,
)
from adapters.mineflayer.python_protocol import MINEFLAYER_VERSION
from test_bd1b_owner_present_dev import _configured
from test_bd1b_owner_source_dev import _files
from test_i_lane_e2c_original_present_dev import _args, _inject
from test_i_lane_i1_native_correlated_snapshot_dev import _matched_with_passive_after
from test_mineflayer_process_session import FakeProcess, observation_line


@pytest.mark.parametrize("reason", ["queue-hold", "passive-replaced", "blocked-now"])
def test_i2_original_a_sense_cannot_outlive_a_native_receive_continuity(
    tmp_path, monkeypatch, reason,
):
    case = _configured(tmp_path, monkeypatch, need=True)
    bridge, world = case[1], case[3]
    initial_files = _files(bridge)
    _inject(bridge, world, "A")
    b_sense = _inject(bridge, world, "B")
    matched, _ = _matched_with_passive_after(bridge, world, "A", 1)
    assert bridge.current_i1_correlated_sense("A") is matched
    assert bridge.current_sense("B") is b_sense

    native = bridge.sessions["A"]
    if reason == "queue-hold":
        native.native_continuity_hold = NativeReceiveContinuityHold(
            native.started.session_id, 7,
            "OWNER_QUEUE_FULL_UNKNOWN_PIPE_DELAY", time.monotonic(),
        )
    elif reason == "passive-replaced":
        # The actual ProcessSession summarises omitted sequence ranges; a
        # non-null summary is enough to make continuity uncertifiable.
        native.passive_aggregation = object()
    else:
        native.backpressure_hold = True

    assert bridge.current_sense("A") is None
    assert bridge.current_i1_correlated_sense("A") is None
    assert bridge.current_self_world("A") is None
    # B remains independently qualified and is not fenced by A's stream.
    assert bridge.current_sense("B") is b_sense
    assert bridge.cognitive_work.read_present_cpu(
        **_args(case, sid="B")
    ).present.three_self.scope.self_id == "B"
    a_present = bridge.cognitive_work.read_present_cpu(**_args(case))
    assert len(a_present.present.three_self.source_revision_refs) == 2
    assert a_present.present.three_self.self_world.read(
        "sense.position"
    ).status.value == "UNKNOWN"
    assert _files(bridge) == initial_files


@pytest.mark.parametrize("compact", [True, False])
def test_one_original_decoder_latches_queue_pressure_without_losing_effect_ack(compact):
    """Reader delay is UNKNOWN even when no passive row was replaced."""
    class QueueStdout:
        def __init__(self):
            self.queue = asyncio.Queue()

        async def readline(self):
            return await self.queue.get()

    def line(value):
        return (json.dumps(value) + "\n").encode("utf-8")

    def observation(seq, kind):
        raw = json.loads(observation_line())
        raw.update(type="observation", session_id="native-q", seq=seq, kind=kind)
        raw.pop("request_id", None)
        return line(raw)

    async def scenario():
        process = FakeProcess([])
        process.stdout = QueueStdout()
        process.stdout.queue.put_nowait(line({
            "type": "adapter_started", "session_id": "native-q", "seq": 0,
            "mineflayer_version": MINEFLAYER_VERSION,
            "config": {"host": "127.0.0.1", "port": 25565,
                       "username": "Self", "version": None},
        }))
        session = MineflayerProcessSession(process)
        session._started = await session.receive()
        observed = []
        observer_hold_at_event = []

        def observer(msg):
            observed.append(msg)
            observer_hold_at_event.append(session.native_continuity_hold)

        session.start_dispatcher(observer, capacity=1,
                                 compact_safe=lambda: compact)
        process.stdout.queue.put_nowait(observation(1, "move"))
        process.stdout.queue.put_nowait(observation(2, "entities"))
        process.stdout.queue.put_nowait(line({
            "type": "effect_result", "session_id": "native-q", "seq": 3,
            "action_id": "original-stop", "effect": "clear_controls",
            "result": "applied", "error": None,
        }))
        async with asyncio.timeout(2):
            while session.native_continuity_hold is None:
                await asyncio.sleep(0)
        receipt = session.native_continuity_hold
        assert receipt.source == "native-q"
        assert receipt.first_seq == 2
        assert receipt.reason == "OWNER_QUEUE_FULL_UNKNOWN_PIPE_DELAY"
        assert receipt.received_monotonic > 0
        if compact:
            assert session.passive_aggregation is not None
            assert session.passive_aggregation.replaced_count == 1
        else:
            assert session.passive_aggregation is None
        consumed = []
        while True:
            msg = await asyncio.wait_for(session.receive(), timeout=2)
            consumed.append(msg)
            if getattr(msg, "action_id", None) == "original-stop":
                break
        assert [msg.seq for msg in consumed] == ([2, 3] if compact else [1, 2, 3])
        assert consumed[-1].result == "applied"
        assert [msg.seq for msg in observed] == [1, 2, 3]
        # The observer must not see the pressured row BEFORE the HOLD
        # latch. Otherwise a concurrent original Present read can adopt it.
        assert observer_hold_at_event[0] is None
        assert observer_hold_at_event[1] is receipt
        assert observer_hold_at_event[2] is receipt
        assert session.native_continuity_hold is receipt
        await session.terminate()

    asyncio.run(scenario())
