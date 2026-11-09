"""D14 R12: native oxygen=-1 may not suppress 24k readback or grant Action."""
from __future__ import annotations

import asyncio
import json
from types import SimpleNamespace as NS
from unittest.mock import AsyncMock

import pytest

from adapters.mineflayer.process_session import MineflayerProcessSession
from adapters.mineflayer.python_protocol import parse_mineflayer_line
from adapters.mineflayer.self_world_stage_w3_capture import audit_w3_sealed_stdout
from test_d14_natural_active_s49 import make_controller, native_pair
from test_mineflayer_process_session import (
    FakeProcess,
    observation_line,
    started_line,
)


def _oxygen_frame(oxygen, *, seq=1):
    payload = json.loads(observation_line())
    payload["snapshot"]["oxygen_level"] = oxygen
    payload["seq"] = seq
    return (json.dumps(payload) + "\n").encode("utf8")


def _shutdown_ack(*, seq=2):
    return (
        json.dumps({"type": "shutdown_ack", "session_id": "session-1", "seq": seq})
        + "\n"
    ).encode("utf8")


@pytest.mark.parametrize("oxygen", [-2, -0.5, "-1", True, float("nan")])
def test_native_negative_other_than_exact_minus_one_is_still_rejected(oxygen):
    with pytest.raises(ValueError):
        parse_mineflayer_line(_oxygen_frame(oxygen).decode("utf8"))


def test_raw_native_exact_minus_one_decodes_as_unknown_not_full_or_zero():
    parsed = parse_mineflayer_line(_oxygen_frame(-1).decode("utf8"))
    assert parsed.snapshot.oxygen_level is None
    assert parse_mineflayer_line(_oxygen_frame(0).decode()).snapshot.oxygen_level == 0
    assert parse_mineflayer_line(_oxygen_frame(20).decode()).snapshot.oxygen_level == 20
    assert parse_mineflayer_line(_oxygen_frame(None).decode()).snapshot.oxygen_level is None


def test_w3_raw_minus_one_preserved_and_complete_session_replay(tmp_path):
    async def scenario():
        process = FakeProcess([
            started_line(), _oxygen_frame(-1), _shutdown_ack(),
        ])
        session = MineflayerProcessSession(process, raw_capture_root=tmp_path)
        await session.receive()
        readback = await session.receive()
        assert readback.snapshot.oxygen_level is None
        assert await session.shutdown(timeout_s=1) == 0
        receipt = session.raw_capture_receipt
        assert receipt["status"] == "COMPLETE_NODE_STDOUT"
        assert receipt["capture_fault"] is None
        assert receipt["shutdown_ack_count"] == 1
        assert '"oxygen_level": -1' in (
            tmp_path / "w3-node-stdout.raw.jsonl"
        ).read_text("utf8")
        assert audit_w3_sealed_stdout(tmp_path)["status"] == "COMPLETE_NODE_STDOUT"

    asyncio.run(scenario())


def test_bad_native_frame_keeps_w3_incomplete_but_shutdown_reaps(tmp_path):
    async def scenario():
        process = FakeProcess([started_line(), _oxygen_frame(-2)])
        session = MineflayerProcessSession(process, raw_capture_root=tmp_path)
        await session.receive()
        with pytest.raises(ValueError):
            await session.shutdown(timeout_s=1)
        assert process.terminated
        receipt = session.raw_capture_receipt
        assert receipt["status"] == "INCOMPLETE_UNQUALIFIED"
        assert receipt["capture_fault"] == "node_protocol_decode_failed"
        assert receipt["process_exit_code"] == -15

    asyncio.run(scenario())


def test_r11_unknown_oxygen_continues_observation_but_no_action(
    tmp_path, monkeypatch,
):
    loop, report = make_controller(tmp_path, monkeypatch)
    loop.r11_day = True
    previous, current = native_pair()
    previous.snapshot.oxygen_level = None
    current.snapshot.oxygen_level = None
    loop._read = AsyncMock(side_effect=[previous, current])
    loop.policy = NS(decide=lambda *args, **kwargs: NS(
        selected="DEFER", preferred="MOVE_AWAY", fallback="ATTACK",
        reason="ZOMBIE_PRESENT_NO_DEFENSE_ADMISSION",
    ))
    saved = []
    asyncio.run(loop.step(lambda kind, line, native=None: saved.append((kind, native))))
    assert loop.stopped is False
    assert len(report["life_decisions"]) == 1
    decision = report["life_decisions"][0]
    assert decision["r12_action_admission"] == (
        "DEFER_UNKNOWN_OXYGEN_NO_PHYSICAL_ISSUE"
    )
    assert decision["r12_oxygen_observed"] is False
    assert report["new_s49_actions"] == 0
    assert loop.nonmotion.actions == ()
    assert saved[0][0] == "LIFE_DECISION"
