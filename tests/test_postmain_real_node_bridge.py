"""S30: *real Node subprocess* executes unchanged bridge with test-only bot shim.

No Minecraft TCP server, physical bot or Mineflayer package is used. Test
fixture enters ONLY the Node child via NODE_OPTIONS --require and does not
modify production bridge code or install a new runtime path.
"""
from __future__ import annotations

import asyncio
import json
import os
import shutil
from pathlib import Path

import pytest

from adapters.mineflayer.process_session import (
    MineflayerProcessEnded,
    MineflayerProcessSession,
)
from adapters.mineflayer.python_protocol import (
    MineflayerCommandError,
    MineflayerLaunchConfig,
    MineflayerObservation,
    MineflayerShutdownAck,
    encode_observe,
)

ROOT = Path(__file__).resolve().parents[1]
BRIDGE = ROOT / "adapters/mineflayer/bridge.mjs"
PRELOAD = ROOT / "adapters/mineflayer/s30_test_only_preload.cjs"
REQ1 = "s30-probe:one.1"
REQ2 = "s30-probe:two.2"


def _injected(monkeypatch, *, distance: str = "0.2", suppress_spawn: bool = False):
    assert BRIDGE.is_file()
    assert PRELOAD.is_file()
    assert shutil.which("node") is not None, "Node 22 must be installed for S30"
    # NODE_OPTIONS is inherited only by subprocesses started under this test.
    assert not os.environ.get("NODE_OPTIONS"), "S30 requires isolated Node options"
    monkeypatch.setenv("NODE_OPTIONS", f"--require={PRELOAD}")
    monkeypatch.setenv("S30_THREAT_DISTANCE_M", distance)
    monkeypatch.setenv("S30_SUPPRESS_SPAWN", "1" if suppress_spawn else "0")


async def _launch(*, spawn: bool = True):
    session = await MineflayerProcessSession.launch(
        MineflayerLaunchConfig(),
        bridge_path=BRIDGE,
        startup_timeout_s=5,
    )
    assert session.started.session_id
    assert session.started.seq == 0
    if spawn:
        message = await asyncio.wait_for(session.receive(), timeout=5)
        assert isinstance(message, MineflayerObservation)
        assert message.kind == "spawn"
        assert message.seq == 1
        assert message.session_id == session.started.session_id
    return session


async def _recv(session: MineflayerProcessSession):
    return await asyncio.wait_for(session.receive(), timeout=4)


def test_real_node_bridge_echoes_two_separate_ids_and_retains_legacy(monkeypatch):
    _injected(monkeypatch)
    async def scenario():
        session = await _launch()
        try:
            await session.send_observe(REQ1)
            first = await _recv(session)
            await session.send_observe(REQ2)
            second = await _recv(session)
            await session.send_observe()
            legacy = await _recv(session)
            for num, message, rid in (
                (2, first, REQ1), (3, second, REQ2), (4, legacy, None),
            ):
                assert isinstance(message, MineflayerObservation)
                assert message.seq == num
                assert message.session_id == session.started.session_id
                assert message.kind == "probe"
                assert message.request_id == rid
                target = message.snapshot.nearby_entities
                assert len(target) == 1
                assert target[0].entity_id == 42
                assert target[0].name == "zombie"
                assert target[0].distance == 0.2
                assert target[0].position.x == 0.2
                assert not message.snapshot.nearby_entities_coverage.truncated
            assert first.provenance.reference == f"{session.started.session_id}:2"
            assert session.process_returncode is None
        finally:
            ret = await session.shutdown(timeout_s=5)
            assert ret == 0
    asyncio.run(scenario())
    doc = json.loads((ROOT / "docs/postmain-s30-process-trace.json").read_text())
    assert doc["request1"]["seq"] == 2
    assert doc["request2"]["seq"] == 3
    assert doc["legacy"]["request_id"] is None


def test_real_node_bridge_duplicate_id_rejected_without_probe(monkeypatch):
    _injected(monkeypatch)
    async def scenario():
        session = await _launch()
        try:
            await session.send_observe(REQ1)
            first = await _recv(session)
            assert isinstance(first, MineflayerObservation) and first.seq == 2

            await session.send_observe(REQ1)
            duplicate = await _recv(session)
            assert isinstance(duplicate, MineflayerCommandError)
            assert duplicate.seq == 3
            assert duplicate.message == "duplicate_probe_request_id"

            await session.send_observe(REQ2)
            next_probe = await _recv(session)
            assert isinstance(next_probe, MineflayerObservation)
            assert next_probe.request_id == REQ2 and next_probe.seq == 4
        finally:
            await session.shutdown(timeout_s=5)
    asyncio.run(scenario())


def test_real_node_bridge_other_distance_and_exact_session_provenance(monkeypatch):
    _injected(monkeypatch, distance="1.8")
    async def scenario():
        session = await _launch()
        try:
            await session.send_observe(REQ1)
            message = await _recv(session)
            assert isinstance(message, MineflayerObservation)
            assert message.request_id == REQ1
            assert message.snapshot.nearby_entities[0].distance == 1.8
            assert message.snapshot.nearby_entities[0].position.x == 1.8
            assert message.provenance.reference == f"{session.started.session_id}:2"
        finally:
            await session.shutdown(timeout_s=5)
    asyncio.run(scenario())


def test_real_bridge_invalid_or_malformed_command_yields_command_error(monkeypatch):
    _injected(monkeypatch)
    async def scenario():
        session = await _launch()
        try:
            # Deliberately bypass Python encoder solely in this fail-closed
            # real-process test to exercise Node's own parseCommand guard.
            for seq, raw, expected in (
                (2, '{"type":"observe","request_id":"bad space"}\n', "request_id"),
                (3, '{"type":"observe","request_id":null}\n', "request_id"),
                (4, 'not-json\n', "invalid_json"),
            ):
                await session._send(raw)
                result = await _recv(session)
                assert isinstance(result, MineflayerCommandError)
                assert result.seq == seq and expected in result.message
            await session.send_observe(REQ1)
            valid = await _recv(session)
            assert valid.seq == 5 and valid.request_id == REQ1
        finally:
            await session.shutdown(timeout_s=5)
    asyncio.run(scenario())


def test_real_bridge_before_spawn_never_fabricates_probe(monkeypatch):
    _injected(monkeypatch, suppress_spawn=True)
    async def scenario():
        session = await _launch(spawn=False)
        try:
            await session.send_observe(REQ1)
            reply = await _recv(session)
            assert isinstance(reply, MineflayerCommandError)
            assert reply.seq == 1
            assert reply.message == "observe_before_spawn"
            assert session.process_returncode is None
        finally:
            await session.shutdown(timeout_s=5)
    asyncio.run(scenario())


def test_real_bridge_explicit_shutdown_ack_and_terminal_eof(monkeypatch):
    _injected(monkeypatch)
    async def scenario():
        session = await _launch()
        await session.send_observe(REQ1)
        assert isinstance(await _recv(session), MineflayerObservation)
        ret = await session.shutdown(timeout_s=5)
        assert ret == 0
        # The shutdown protocol does not silently launch another child.
        ack = await _recv(session)
        assert isinstance(ack, MineflayerShutdownAck)
        assert ack.seq == 3
        ending = await _recv(session)
        assert ending.seq == 4
        with pytest.raises(MineflayerProcessEnded):
            await _recv(session)
        with pytest.raises(MineflayerProcessEnded):
            await session.send_observe(REQ2)
    asyncio.run(scenario())


def test_forced_process_termination_fails_closed_no_relaunch(monkeypatch):
    _injected(monkeypatch)
    async def scenario():
        session = await _launch()
        code = await session.terminate()
        assert code != 0
        with pytest.raises(MineflayerProcessEnded):
            await _recv(session)
        with pytest.raises(MineflayerProcessEnded):
            await session.send_observe(REQ1)
    asyncio.run(scenario())


def test_request_id_reuse_only_across_distinct_process_sessions(monkeypatch):
    _injected(monkeypatch)
    async def scenario():
        seen_sessions = []
        for _ in range(2):
            session = await _launch()
            try:
                await session.send_observe(REQ1)
                observation = await _recv(session)
                assert observation.request_id == REQ1
                seen_sessions.append(session.started.session_id)
            finally:
                await session.shutdown(timeout_s=5)
        assert seen_sessions[0] != seen_sessions[1]
    asyncio.run(scenario())


def test_process_receipt_never_claims_real_minecraft():
    receipt = json.loads((ROOT / "docs/postmain-s30-receipt.json").read_text())
    assert receipt["base_head"] == "5424669a09a69eb364da559e38b9999fee7b6680"
    assert receipt["classification"] == "CORRELATED_REAL_NODE_BRIDGE_PROCESS_TEST_SHIM_QUALIFIED"
    assert receipt["real_node_process"] is True
    assert receipt["mineflayer_implementation"] == "TEST_ONLY_SUBSTITUTION"
    assert receipt["live_minecraft"] == "NOT_RUN"
    assert receipt["physical_world_provenance_verified"] is False


def test_legacy_encoder_unmodified():
    assert json.loads(encode_observe()) == {"type": "observe"}
    assert json.loads(encode_observe(REQ1)) == {
        "type": "observe", "request_id": REQ1,
    }
