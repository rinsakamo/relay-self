import asyncio
import json
from pathlib import Path

import pytest

from adapters.mineflayer.process_session import (
    MineflayerProcessEnded,
    MineflayerProcessSession,
    MineflayerProcessStartError,
)
from adapters.mineflayer.python_protocol import (
    MINEFLAYER_VERSION,
    MineflayerLaunchConfig,
    MineflayerObservation,
)


def started_line() -> bytes:
    return (
        json.dumps(
            {
                "type": "adapter_started",
                "session_id": "session-1",
                "seq": 0,
                "mineflayer_version": MINEFLAYER_VERSION,
                "config": {
                    "host": "127.0.0.1",
                    "port": 25565,
                    "username": "RelaySelf",
                    "version": None,
                },
            }
        )
        + "\n"
    ).encode()


def observation_line() -> bytes:
    return (
        json.dumps(
            {
                "type": "observation",
                "session_id": "session-1",
                "seq": 1,
                "kind": "health",
                "snapshot": {
                    "health": 12,
                    "food": 7,
                    "oxygen_level": 20,
                    "position": {"x": 1, "y": 64, "z": 2},
                    "time": {
                        "time_of_day": 13000,
                        "day": 2,
                        "is_day": False,
                    },
                    "inventory": [
                        {"name": "bread", "count": 3, "slot": 10},
                    ],
                    "nearby_entities": [],
                    "nearby_entities_coverage": {
                        "source_scope": "mineflayer_entity_registry",
                        "max_distance": 16,
                        "max_entities": 16,
                        "candidate_count": 0,
                        "truncated": False,
                    },
                },
            }
        )
        + "\n"
    ).encode()


class FakeStdin:
    def __init__(self) -> None:
        self.writes: list[bytes] = []
        self.drain_count = 0

    def write(self, value: bytes) -> None:
        self.writes.append(value)

    async def drain(self) -> None:
        self.drain_count += 1


class FakeStdout:
    def __init__(self, lines: list[bytes]) -> None:
        self.lines = list(lines)

    async def readline(self) -> bytes:
        if not self.lines:
            return b""
        return self.lines.pop(0)


class FakeProcess:
    def __init__(self, lines: list[bytes]) -> None:
        self.stdin = FakeStdin()
        self.stdout = FakeStdout(lines)
        self.returncode: int | None = None
        self.terminated = False
        self.wait_count = 0

    async def wait(self) -> int:
        self.wait_count += 1
        if self.returncode is None:
            self.returncode = 0
        return self.returncode

    def terminate(self) -> None:
        self.terminated = True
        self.returncode = -15


def test_launch_uses_target_local_bridge_and_consumes_started_message(
    monkeypatch,
    tmp_path: Path,
) -> None:
    bridge = tmp_path / "bridge.mjs"
    bridge.write_text("// fixture", encoding="utf-8")
    process = FakeProcess([started_line()])
    calls: list[tuple[object, ...]] = []

    async def fake_create(*args, **kwargs):
        calls.append((*args, kwargs))
        return process

    monkeypatch.setattr(asyncio, "create_subprocess_exec", fake_create)

    async def scenario() -> None:
        session = await MineflayerProcessSession.launch(
            MineflayerLaunchConfig(),
            bridge_path=bridge,
            node_executable="node-test",
        )

        assert session.started.session_id == "session-1"
        assert session.process_returncode is None
        assert calls[0][0:2] == ("node-test", str(bridge))
        assert calls[0][-1]["stdin"] is asyncio.subprocess.PIPE
        assert calls[0][-1]["stdout"] is asyncio.subprocess.PIPE
        assert calls[0][-1]["stderr"] is None

    asyncio.run(scenario())


def test_send_effects_use_existing_target_local_protocol(monkeypatch, tmp_path: Path) -> None:
    bridge = tmp_path / "bridge.mjs"
    bridge.write_text("// fixture", encoding="utf-8")
    process = FakeProcess([started_line()])

    async def fake_create(*_args, **_kwargs):
        return process

    monkeypatch.setattr(asyncio, "create_subprocess_exec", fake_create)

    async def scenario() -> None:
        session = await MineflayerProcessSession.launch(
            MineflayerLaunchConfig(),
            bridge_path=bridge,
        )
        await session.send_set_control(
            "action-forward",
            control="forward",
            state=True,
        )
        await session.send_clear_controls("action-stop")
        await session.send_equip_item(
            "action-equip",
            item_name="bread",
        )
        await session.send_consume_held("action-consume")
        await session.send_look(
            "action-look",
            yaw=1.5,
            pitch=0.0,
        )

        assert [json.loads(value) for value in process.stdin.writes] == [
            {
                "type": "effect",
                "action_id": "action-forward",
                "effect": "set_control",
                "control": "forward",
                "state": True,
            },
            {
                "type": "effect",
                "action_id": "action-stop",
                "effect": "clear_controls",
            },
            {
                "type": "effect",
                "action_id": "action-equip",
                "effect": "equip_item",
                "item_name": "bread",
            },
            {
                "type": "effect",
                "action_id": "action-consume",
                "effect": "consume_held",
            },
            {
                "type": "effect",
                "action_id": "action-look",
                "effect": "look",
                "yaw": 1.5,
                "pitch": 0.0,
            },
        ]
        assert process.stdin.drain_count == 5

    asyncio.run(scenario())


def test_receive_decodes_next_message_with_session_provenance(
    monkeypatch,
    tmp_path: Path,
) -> None:
    bridge = tmp_path / "bridge.mjs"
    bridge.write_text("// fixture", encoding="utf-8")
    process = FakeProcess([started_line(), observation_line()])

    async def fake_create(*_args, **_kwargs):
        return process

    monkeypatch.setattr(asyncio, "create_subprocess_exec", fake_create)

    async def scenario() -> None:
        session = await MineflayerProcessSession.launch(
            MineflayerLaunchConfig(),
            bridge_path=bridge,
        )
        message = await session.receive()

        assert isinstance(message, MineflayerObservation)
        assert message.kind == "health"
        assert message.provenance.reference == "session-1:1"

    asyncio.run(scenario())


def test_eof_is_explicit_and_does_not_invent_connection_outcome(
    monkeypatch,
    tmp_path: Path,
) -> None:
    bridge = tmp_path / "bridge.mjs"
    bridge.write_text("// fixture", encoding="utf-8")
    process = FakeProcess([started_line()])

    async def fake_create(*_args, **_kwargs):
        return process

    monkeypatch.setattr(asyncio, "create_subprocess_exec", fake_create)

    async def scenario() -> None:
        session = await MineflayerProcessSession.launch(
            MineflayerLaunchConfig(),
            bridge_path=bridge,
        )
        with pytest.raises(MineflayerProcessEnded, match="stdout ended"):
            await session.receive()

    asyncio.run(scenario())


def test_launch_fails_before_spawn_when_bridge_path_is_missing(tmp_path: Path) -> None:
    async def scenario() -> None:
        with pytest.raises(MineflayerProcessStartError, match="bridge does not exist"):
            await MineflayerProcessSession.launch(
                MineflayerLaunchConfig(),
                bridge_path=tmp_path / "missing.mjs",
            )

    asyncio.run(scenario())


def test_invalid_first_message_terminates_child_without_retry(
    monkeypatch,
    tmp_path: Path,
) -> None:
    bridge = tmp_path / "bridge.mjs"
    bridge.write_text("// fixture", encoding="utf-8")
    bad = (
        json.dumps(
            {
                "type": "observation",
                "session_id": "session-1",
                "seq": 0,
                "kind": "health",
                "snapshot": {
                    "health": 12,
                    "food": 7,
                    "oxygen_level": 20,
                    "position": {"x": 1, "y": 64, "z": 2},
                    "time": None,
                    "inventory": [],
                    "nearby_entities": [],
                    "nearby_entities_coverage": {
                        "source_scope": "mineflayer_entity_registry",
                        "max_distance": 16,
                        "max_entities": 16,
                        "candidate_count": 0,
                        "truncated": False,
                    },
                },
            }
        )
        + "\n"
    ).encode()
    process = FakeProcess([bad])
    launch_count = 0

    async def fake_create(*_args, **_kwargs):
        nonlocal launch_count
        launch_count += 1
        return process

    monkeypatch.setattr(asyncio, "create_subprocess_exec", fake_create)

    async def scenario() -> None:
        with pytest.raises(ValueError, match="first bridge message"):
            await MineflayerProcessSession.launch(
                MineflayerLaunchConfig(),
                bridge_path=bridge,
            )

        assert launch_count == 1
        assert process.terminated is True
        assert process.wait_count == 1

    asyncio.run(scenario())


def test_clean_shutdown_sends_one_shutdown_and_waits(
    monkeypatch,
    tmp_path: Path,
) -> None:
    bridge = tmp_path / "bridge.mjs"
    bridge.write_text("// fixture", encoding="utf-8")
    process = FakeProcess([started_line()])

    async def fake_create(*_args, **_kwargs):
        return process

    monkeypatch.setattr(asyncio, "create_subprocess_exec", fake_create)

    async def scenario() -> None:
        session = await MineflayerProcessSession.launch(
            MineflayerLaunchConfig(),
            bridge_path=bridge,
        )
        returncode = await session.shutdown()

        assert returncode == 0
        assert [json.loads(value) for value in process.stdin.writes] == [
            {"type": "shutdown"}
        ]
        assert process.wait_count == 1
        assert process.terminated is False

    asyncio.run(scenario())
