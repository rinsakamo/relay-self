import asyncio
import json
from pathlib import Path

import pytest

from adapters.mineflayer.process_session import (
    MineflayerEffectAdmissionError,
    MineflayerProcessEnded,
    MineflayerProcessSession,
    MineflayerProcessStartError,
)
from adapters.mineflayer.python_protocol import (
    MINEFLAYER_VERSION,
    MineflayerLaunchConfig,
    MineflayerObservation,
)
from relay_self.physical_issue_admission_dev import (
    PhysicalIssueAdmission,
    PhysicalIssueFenceError,
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
                    "food_saturation": 5,
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
        await session.send_attack_entity(
            "action-attack",
            entity_id=7,
        )
        await session.send_observe()

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
            {
                "type": "effect",
                "action_id": "action-attack",
                "effect": "attack_entity",
                "entity_id": 7,
            },
            {"type": "observe"},
        ]
        assert process.stdin.drain_count == 7

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
                    "food_saturation": 5,
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


def test_correlated_observe_is_one_read_only_command_without_action_id(
    monkeypatch, tmp_path: Path,
) -> None:
    bridge = tmp_path / "bridge.mjs"
    bridge.write_text("// fixture", encoding="utf-8")
    process = FakeProcess([started_line()])

    async def fake_create(*_args, **_kwargs):
        return process

    monkeypatch.setattr(asyncio, "create_subprocess_exec", fake_create)

    async def scenario() -> None:
        session = await MineflayerProcessSession.launch(
            MineflayerLaunchConfig(), bridge_path=bridge,
        )
        await session.send_observe("cognitive-abcdef")
        assert [json.loads(x) for x in process.stdin.writes] == [{
            "type": "observe", "request_id": "cognitive-abcdef",
        }]
        assert process.stdin.drain_count == 1

    asyncio.run(scenario())



def test_native_process_stdin_effects_require_exact_active_skill_lease(
    monkeypatch, tmp_path: Path,
) -> None:
    """Actual _send() checks commands, not only higher-level send_* wrappers."""
    bridge = tmp_path / "bridge.mjs"
    bridge.write_text("// fixture", encoding="utf-8")
    proc = FakeProcess([started_line()])

    async def fake_create(*_args, **_kwargs):
        return proc

    monkeypatch.setattr(asyncio, "create_subprocess_exec", fake_create)

    async def scenario():
        session = await MineflayerProcessSession.launch(
            MineflayerLaunchConfig(), bridge_path=bridge,
        )
        gate = PhysicalIssueAdmission({"A": session.started.session_id})
        session.install_effect_admission(
            lambda session_id, effect, action_id: gate.require_native_effect(
                self_id="A", native_session_id=session_id,
                effect=effect, action_id=action_id,
            )
        )
        with pytest.raises(MineflayerEffectAdmissionError, match="only be installed once"):
            session.install_effect_admission(lambda *_: None)
        with pytest.raises(PhysicalIssueFenceError, match="active capability-scoped"):
            await session.send_equip_item("no-lease-equip", item_name="bread")
        with pytest.raises(PhysicalIssueFenceError, match="active capability-scoped"):
            await session.send_attack_entity("no-lease-attack", entity_id=7)
        assert proc.stdin.writes == []

        with gate.lease(
            self_id="A", native_session_id="session-1",
            action_id="meal-parent", effect_family="EAT",
        ):
            await session.send_equip_item("meal-parent-equip", item_name="bread")
            await session.send_consume_held("meal-parent-consume")
            with pytest.raises(PhysicalIssueFenceError, match="capability-scoped"):
                await session.send_attack_entity("wrong-family", entity_id=7)
            with pytest.raises(PhysicalIssueFenceError, match="capability-scoped"):
                await session.send_set_control("old-l0-move", control="forward", state=True)
            with pytest.raises(PhysicalIssueFenceError, match="capability-scoped"):
                await session.send_clear_controls("old-l0-stop")
            with pytest.raises(PhysicalIssueFenceError, match="capability-scoped"):
                await session.send_look("old-l0-look", yaw=0, pitch=0)

        with pytest.raises(PhysicalIssueFenceError, match="capability-scoped"):
            await session.send_equip_item("after-release", item_name="bread")
        with gate.lease(
            self_id="A", native_session_id="session-1",
            action_id="attack-parent", effect_family="ATTACK",
        ):
            await session.send_attack_entity("attack-parent-attack", entity_id=7)
            with pytest.raises(PhysicalIssueFenceError, match="capability-scoped"):
                await session.send_consume_held("wrong-family-eat")

        assert [json.loads(v)["effect"] for v in proc.stdin.writes] == [
            "equip_item", "consume_held", "attack_entity",
        ]
        fence = gate.close()
        await session.send_observe("probe-fenced")
        with pytest.raises(PhysicalIssueFenceError, match="blocked by checkpoint"):
            await session.send_attack_entity("blocked-by-save", entity_id=7)
        assert json.loads(proc.stdin.writes[-1]) == {
            "type": "observe", "request_id": "probe-fenced",
        }
        gate.rotate_native_session(
            fence_ref=fence.fence_ref, self_id="A",
            old_session_id="session-1", new_session_id="new-session-A",
        )
        gate.release(fence.fence_ref)
        with pytest.raises(PhysicalIssueFenceError, match="stale/foreign"):
            await session.send_attack_entity("old-session-after-rebind", entity_id=7)

    asyncio.run(scenario())


def test_native_effect_admission_denies_direct_low_level_effect_bypass(
    monkeypatch, tmp_path: Path,
) -> None:
    bridge = tmp_path / "bridge.mjs"
    bridge.write_text("// fixture", encoding="utf-8")
    proc = FakeProcess([started_line()])

    async def fake_create(*_args, **_kwargs):
        return proc

    monkeypatch.setattr(asyncio, "create_subprocess_exec", fake_create)

    async def scenario():
        session = await MineflayerProcessSession.launch(
            MineflayerLaunchConfig(), bridge_path=bridge,
        )
        gate = PhysicalIssueAdmission({"A": "session-1"})
        session.install_effect_admission(
            lambda sid, effect, action_id: gate.require_native_effect(
                self_id="A", native_session_id=sid,
                effect=effect, action_id=action_id,
            )
        )
        with pytest.raises(PhysicalIssueFenceError, match="active capability-scoped"):
            await session._send(
                '{"type":"effect","effect":"attack_entity","action_id":"bypass","entity_id":7}\n'
            )
        with pytest.raises(MineflayerEffectAdmissionError, match="unknown native command"):
            await session._send('{"type":"execute-arbitrary"}\n')
        with pytest.raises(MineflayerEffectAdmissionError, match="invalid command"):
            await session._send("not JSON\n")
        assert proc.stdin.writes == []
        # No physical grant needed for source-qualified read-only observation.
        await session.send_observe("allowed-read")
        assert len(proc.stdin.writes) == 1

    asyncio.run(scenario())



def test_real_python_native_send_allows_exact_precheckpoint_stop_only(
    monkeypatch, tmp_path: Path,
):
    """The final Mineflayer stdin guard permits only the scoped STOP action ID."""
    bridge = tmp_path / "bridge.mjs"
    bridge.write_text("// fixture", encoding="utf-8")
    proc = FakeProcess([started_line()])

    async def fake_create(*_args, **_kwargs):
        return proc

    monkeypatch.setattr(asyncio, "create_subprocess_exec", fake_create)

    async def exercise():
        session = await MineflayerProcessSession.launch(
            MineflayerLaunchConfig(), bridge_path=bridge,
        )
        physical = PhysicalIssueAdmission(
            {"A": session.started.session_id}, require_neutral_stop=True,
        )
        session.install_effect_admission(
            lambda sess, effect, action_id: physical.require_native_effect(
                self_id="A", native_session_id=sess, effect=effect,
                action_id=action_id,
            )
        )
        token = physical.begin_neutralization()
        with physical.stop_lease(
            fence_ref=token, self_id="A",
            native_session_id=session.started.session_id, stop_action_id="stop-A",
        ):
            with pytest.raises(PhysicalIssueFenceError, match="blocked"):
                await session.send_clear_controls("forged-other-stop")
            with pytest.raises(PhysicalIssueFenceError, match="blocked"):
                await session.send_set_control(
                    "unsafe-move", control="forward", state=True,
                )
            with pytest.raises(PhysicalIssueFenceError, match="blocked"):
                await session.send_attack_entity("unsafe-attack", entity_id=42)
            await session.send_clear_controls("stop-A")
        assert [json.loads(x) for x in proc.stdin.writes] == [{
            "type": "effect", "effect": "clear_controls", "action_id": "stop-A",
        }]
        # Without the matching ACK and delayed settle observations, STOP is
        # PREPARED_UNRESOLVED and the cohort must never be committed.
        with pytest.raises(PhysicalIssueFenceError, match="HOLD"):
            physical.close()
        assert physical.closed

    asyncio.run(exercise())


def test_u17_same_owned_stdin_audit_spans_two_actions_without_restarting(
    monkeypatch, tmp_path: Path,
) -> None:
    """Buffer records are not fabricated Native ACK or process exit evidence."""
    bridge = tmp_path / "bridge.mjs"
    bridge.write_text("// fixture", encoding="utf-8")
    proc = FakeProcess([started_line()])

    async def fake_create(*_args, **_kwargs):
        return proc

    monkeypatch.setattr(asyncio, "create_subprocess_exec", fake_create)

    async def scenario() -> None:
        session = await MineflayerProcessSession.launch(
            MineflayerLaunchConfig(), bridge_path=bridge,
        )
        stdout = tmp_path / "native-stdout.jsonl"
        stdin = tmp_path / "native-stdin.jsonl"
        session.start_raw_source_audit(stdout)
        session.start_raw_stdin_audit(stdin)
        session.install_effect_admission(lambda *_: None)
        session.install_atomic_effect_sender(lambda _sid, _effect, _aid, write: write())
        for parent in ("first-fresh", "second-fresh"):
            await session.send_look(parent + "-look", yaw=0.0, pitch=0.0)
            await session.send_set_control(
                parent + "-start", control="forward", state=True,
            )
            await session.send_clear_controls(parent + "-stop")
        # One continuous byte sequence; no source restart between parents.
        assert stdin.read_bytes() == b"".join(proc.stdin.writes)
        assert len(stdin.read_bytes().splitlines()) == 6
        assert [json.loads(v)["action_id"] for v in proc.stdin.writes] == [
            suffix for parent in ("first-fresh", "second-fresh")
            for suffix in (parent + "-look", parent + "-start", parent + "-stop")
        ]
        session.finish_raw_stdin_audit()
        session.finish_raw_source_audit()
        assert stdin.read_bytes() == b"".join(proc.stdin.writes)
        with pytest.raises(Exception, match="stdin audit"):
            session.start_raw_stdin_audit(tmp_path / "replayed.jsonl")
        with pytest.raises(Exception, match="not active"):
            session.finish_raw_stdin_audit()

    asyncio.run(scenario())


def test_u17_stdin_capture_does_not_record_denied_or_foreign_commands(
    monkeypatch, tmp_path: Path,
) -> None:
    bridge = tmp_path / "bridge.mjs"
    bridge.write_text("// fixture", encoding="utf-8")
    proc = FakeProcess([started_line()])

    async def fake_create(*_args, **_kwargs):
        return proc

    monkeypatch.setattr(asyncio, "create_subprocess_exec", fake_create)

    async def scenario() -> None:
        session = await MineflayerProcessSession.launch(
            MineflayerLaunchConfig(), bridge_path=bridge,
        )
        with pytest.raises(Exception, match="stdout"):
            session.start_raw_stdin_audit(tmp_path / "premature.jsonl")
        session.start_raw_source_audit(tmp_path / "stdout.jsonl")
        (tmp_path / "symlink").symlink_to(tmp_path, target_is_directory=True)
        with pytest.raises(Exception, match="stdout"):
            session.start_raw_stdin_audit(tmp_path / "symlink" / "bad.jsonl")
        target = tmp_path / "stdin.jsonl"
        session.start_raw_stdin_audit(target)

        def deny(_sid, _effect, _action_id):
            raise MineflayerEffectAdmissionError("original physical gate denied")

        session.install_effect_admission(deny)
        with pytest.raises(MineflayerEffectAdmissionError, match="denied"):
            await session.send_set_control(
                "reused-start", control="forward", state=True,
            )
        assert target.read_bytes() == b""
        assert proc.stdin.writes == []
        await session.send_observe("safe-read")
        assert target.read_bytes() == b"".join(proc.stdin.writes)
        session.finish_raw_stdin_audit()
        session.finish_raw_source_audit()

    asyncio.run(scenario())


def test_u17_stdout_source_contains_exact_startup_prefix_and_continuous_probes(
    monkeypatch, tmp_path: Path,
) -> None:
    """Independent decoder can replay original seq=0 after late audit start."""
    from adapters.mineflayer.python_protocol import MineflayerStreamDecoder

    bridge = tmp_path / "bridge.mjs"
    bridge.write_text("// fixture", encoding="utf-8")
    proc = FakeProcess([started_line(), observation_line()])

    async def fake_create(*_args, **_kwargs):
        return proc

    monkeypatch.setattr(asyncio, "create_subprocess_exec", fake_create)

    async def scenario() -> None:
        session = await MineflayerProcessSession.launch(
            MineflayerLaunchConfig(), bridge_path=bridge,
        )
        # This actual observation precedes opening the raw stdout audit.
        await session.receive()
        path = tmp_path / "complete-original-stdout.jsonl"
        session.start_raw_source_audit(path)
        assert path.read_bytes() == started_line() + observation_line()
        session.finish_raw_source_audit()
        decoder = MineflayerStreamDecoder()
        decoded = [
            decoder.decode(raw.decode("utf-8"))
            for raw in path.read_bytes().splitlines()
        ]
        assert decoder.session_id == session.started.session_id
        assert [item.seq for item in decoded] == [0, 1]
        with pytest.raises(Exception, match="already used"):
            session.start_raw_source_audit(tmp_path / "replayed.jsonl")

    asyncio.run(scenario())
