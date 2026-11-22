"""E1 original I2 Native terrain admission: synthetic CPU/JSONL only, no World."""
from __future__ import annotations

import asyncio
import json
from types import SimpleNamespace

import pytest

from adapters.mineflayer.process_session import (
    MineflayerProcessSession,
    NativeReceiveContinuityHold,
)
from adapters.mineflayer.python_protocol import MINEFLAYER_VERSION
from relay_self.owned_resident_physical_bridge_dev import OwnedResidentBridgeError
from test_bd1b_owner_present_dev import _configured
from test_bd1b_owner_source_dev import _files
from test_mineflayer_process_session import FakeProcess, observation_line
from test_sense_terrain_e1 import packet


def _line(raw):
    return (json.dumps(raw) + "\n").encode("utf-8")


def _observation(native, seq, kind, request_id=None):
    row = json.loads(observation_line())
    row.update(session_id=native, seq=seq, kind=kind)
    if request_id is not None:
        row["request_id"] = request_id
    return _line(row)


@pytest.mark.parametrize("reply", ["correct", "foreign-request", "effect-ack"])
def test_i2_original_owner_terrain_one_native_decoder_source_and_unknown_route(
    tmp_path, monkeypatch, reply,
):
    case = _configured(tmp_path, monkeypatch, need=True)
    bridge, world = case[1], case[3]
    initial_files = _files(bridge)
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
            "config": {
                "host": config.host, "port": config.port,
                "username": config.username, "version": config.version,
            },
        }))
        session = MineflayerProcessSession(process)
        session._started = await session.receive()
        original_probe = bridge.last_login_observations["A"]
        process.stdout.queue.put_nowait(_observation(native, 1, "spawn"))
        process.stdout.queue.put_nowait(
            _observation(native, 2, "probe", original_probe.request_id),
        )
        old_write = process.stdin.write
        submitted = []

        def reply_to_terrain(data):
            old_write(data)
            command = json.loads(data)
            submitted.append(command)
            assert command["type"] == "sense_terrain"
            assert "action_id" not in command and "effect" not in command
            if reply == "effect-ack":
                process.stdout.queue.put_nowait(_line({
                    "type": "effect_result", "session_id": native,
                    "seq": 3, "action_id": "unmatched-stop",
                    "effect": "clear_controls", "result": "applied", "error": None,
                }))
            else:
                row = packet()
                row.update(
                    session_id=native, seq=3,
                    request_id=(
                        command["request_id"] if reply == "correct"
                        else "unexpected-terrain-request"
                    ),
                )
                process.stdout.queue.put_nowait(_line(row))

        process.stdin.write = reply_to_terrain
        bridge.sessions["A"] = session
        bridge.enable_sense = True
        bridge._sense = {}
        bridge._sense_received_at = {}
        bridge._sense_refreshing = set()
        bridge._e1_terrain = {}
        bridge._e1_terrain_received_at = {}
        bridge._i1_correlated_sense = {}
        bridge._i1_correlated_received_at = {}
        bridge._start_sense("A", session, SimpleNamespace(world=world))
        for _ in range(2):
            await asyncio.wait_for(session.receive(), 1)

        assert bridge.current_sense("A") is not None
        if reply == "correct":
            frame = await bridge.refresh_e1_read_only_terrain("A", timeout_s=0.7)
            assert frame.observation.session_id == native
            assert frame.observation.seq == 3
            assert frame.observation.request_id == submitted[0]["request_id"]
            assert frame.terrain.known_cells == 100
            assert len(frame.terrain.cells) == 100
            assert frame.terrain.body_pose == "standing"
            assert bridge.current_e1_terrain("A") is frame
            l0 = bridge.current_e1_terrain_for_l0("A")
            assert l0.route_status == "UNKNOWN"
            assert len(l0.cells) == 100
            claims = bridge.current_e1_terrain_self_world_claims("A")
            assert claims[0].claim_key == "sense.terrain.local"
            assert claims[0].source_revision_refs == (frame.source_revision_ref,)
            # Expiry applies to the original B Present too: no permission
            # or fictional World fact survives A's source continuity loss.
            session.native_continuity_hold = NativeReceiveContinuityHold(
                native, 4, "OWNER_QUEUE_FULL_UNKNOWN_PIPE_DELAY", 0.1,
            )
            assert bridge.current_e1_terrain("A") is None
            assert bridge.current_e1_terrain_for_l0("A") is None
            assert bridge.current_e1_terrain_self_world_claims("A") == ()
        else:
            with pytest.raises(OwnedResidentBridgeError, match="conflicting|mismatch"):
                await bridge.refresh_e1_read_only_terrain("A", timeout_s=0.7)
            assert bridge.current_e1_terrain("A") is None
        assert len(submitted) == 1
        assert bridge._sense_refreshing == set()
        await session.terminate()

    asyncio.run(scenario())
    assert _files(bridge) == initial_files
