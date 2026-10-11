"""E12 original-byte transport and exact Action3 S15/S16 tests, all fake pipes."""
from __future__ import annotations

import asyncio
import json
from dataclasses import replace

import pytest

import test_epistemic_e8_operator_calibration as e8_fixture
import test_postmain_local_recovery_action as s23
import test_postmain_second_action_closure as s20
from adapters.mineflayer.execution import build_mineflayer_command
from adapters.mineflayer.python_protocol import (
    MineflayerLaunchConfig,
    MineflayerObservation,
    encode_shutdown,
)
from experiments.epistemic_e12_native_owner import (
    E12Rejected,
    OneAvatarOriginalOwner,
    OriginalWireSession,
    run_issued_parent_action3,
)
from relay_self.action import ActionState
from relay_self.action_outcome import ActionOutcomeDisposition


def frame_set(session: str, *, position_x: float = 0.0, extra=None, exit_status=0):
    frames = e8_fixture.native_frames(suffix=True)
    out = [frames[0], frames[1], frames[-2], frames[-1]]
    for index, v in enumerate(out):
        v["session_id"] = session
        v["seq"] = index
    out[1]["snapshot"]["position"]["x"] = position_x
    if extra is not None:
        out.insert(2, extra)
        for i, v in enumerate(out):
            v["seq"] = i
    return out


class FakeOwnedProcess(e8_fixture.FakeProcess):
    def __init__(self, lines, *, exit_code=0):
        super().__init__(e8_fixture.line_bytes(lines))
        self.exit_code = exit_code
        self.terminated = False

    async def wait(self):
        self.wait_count += 1
        self.returncode = self.exit_code
        return self.returncode

    def terminate(self):
        self.terminated = True
        self.returncode = -15


def build_owner(tmp_path, processes, *, host="127.0.0.1"):
    calls = []
    async def spawn(*argv, **kwargs):
        calls.append((argv, kwargs))
        return processes.pop(0)
    cfg = MineflayerLaunchConfig(host=host, version="1.21.8")
    owner = OneAvatarOriginalOwner(
        cfg,
        parent_raw=tmp_path / "parent-original.jsonl",
        action_raw=tmp_path / "action4-original.jsonl",
        spawn=spawn,
    )
    return owner, calls


def run(value):
    return asyncio.run(value)


def test_two_original_sources_handoff_one_user_no_concurrent_client(tmp_path):
    parent_frames = frame_set("parent-1")
    child_frames = frame_set("child-2")
    processes = [FakeOwnedProcess(parent_frames), FakeOwnedProcess(child_frames)]
    originals = tuple(processes)
    owner, calls = build_owner(tmp_path, processes)
    async def scenario():
        p = await owner.start_parent()
        assert owner.phase == "PARENT"
        assert p.started.session_id == "parent-1"
        with pytest.raises(E12Rejected, match="overlap"):
            await owner.launch_action4()
        spawn = await p.receive()
        assert isinstance(spawn, MineflayerObservation)
        closed = await owner.close_parent(p)
        assert closed.session_id == "parent-1"
        assert closed.shutdown_ack.seq == 2
        assert closed.connection_end.seq == 3
        assert originals[0].wait_count == 1
        assert owner.phase == "PARENT_CLOSED"
        second = await owner.launch_action4()
        assert second.started.session_id == "child-2"
        assert owner.phase == "ACTION4"
        assert (await second.receive()).kind == "spawn"
        a = await second.close_original()
        assert a.shutdown_ack.seq == 2
        with pytest.raises(E12Rejected):
            await owner.start_parent()
        with pytest.raises(E12Rejected):
            await owner.launch_action4()
    run(scenario())
    assert len(calls) == 2
    assert all("--host" in argv and "127.0.0.1" in argv
               for argv, _ in calls)
    assert originals[0].stdin.writes == [encode_shutdown().encode()]
    assert originals[1].stdin.writes == [encode_shutdown().encode()]
    assert (tmp_path / "parent-original.jsonl").read_bytes() == e8_fixture.line_bytes(parent_frames)
    assert (tmp_path / "action4-original.jsonl").read_bytes() == e8_fixture.line_bytes(child_frames)


@pytest.mark.parametrize("host", ["0.0.0.0", "8.8.8.8", "::", "example.com"])
def test_external_host_is_rejected_without_any_child_or_evidence(tmp_path, host):
    called = []
    async def spawn(*args, **kw):
        called.append(True)
        raise AssertionError("must not launch")
    cfg = MineflayerLaunchConfig(host=host, version="1.21.8")
    with pytest.raises(E12Rejected, match="host|loopback"):
        OneAvatarOriginalOwner(
            cfg, parent_raw=tmp_path / "parent",
            action_raw=tmp_path / "action", spawn=spawn,
        )
    assert called == []


def test_existing_original_output_cannot_be_overwritten(tmp_path):
    x = tmp_path / "original.jsonl"
    x.write_bytes(b"IMMUTABLE")
    with pytest.raises(E12Rejected, match="replace"):
        OneAvatarOriginalOwner(
            MineflayerLaunchConfig(),
            parent_raw=x, action_raw=tmp_path / "new",
        )
    assert x.read_bytes() == b"IMMUTABLE"


@pytest.mark.parametrize("mutation", [
    "missing_ack", "wrong_session", "duplicate_ack", "before_ack_close",
    "bad_exit", "extra_after_ack", "sequence_gap",
])
def test_failed_parent_shutdown_preserves_raw_and_never_launches_next(tmp_path, mutation):
    frames = frame_set("parent-1")
    if mutation == "missing_ack":
        frames.pop(2)
    elif mutation == "wrong_session":
        frames[2]["session_id"] = "alien"
    elif mutation == "duplicate_ack":
        frames.insert(3, dict(frames[2]))
    elif mutation == "before_ack_close":
        frames[2], frames[3] = frames[3], frames[2]
    elif mutation == "extra_after_ack":
        frames.insert(3, dict(frames[1]))
        frames[3]["kind"] = "move"
    elif mutation == "sequence_gap":
        frames[2]["seq"] = 19
    if mutation in ("missing_ack", "duplicate_ack", "before_ack_close", "extra_after_ack"):
        for i, v in enumerate(frames):
            v["seq"] = i
    original = e8_fixture.line_bytes(frames)
    processes = [FakeOwnedProcess(frames, exit_code=7 if mutation == "bad_exit" else 0)]
    owner, called = build_owner(tmp_path, processes)
    async def scenario():
        p = await owner.start_parent()
        await p.receive()
        with pytest.raises((E12Rejected, ValueError)):
            await owner.close_parent(p)
        with pytest.raises(E12Rejected, match="overlap"):
            await owner.launch_action4()
    run(scenario())
    assert len(called) == 1
    preserved = (tmp_path / "parent-original.jsonl").read_bytes()
    assert preserved and preserved in original
    assert not (tmp_path / "action4-original.jsonl").exists()


def test_source_bytes_persist_even_on_invalid_json_and_no_node_retry(tmp_path):
    frames = frame_set("parent-1")
    raw = e8_fixture.line_bytes(frames[:1]) + b"invalid-json\n"
    class RawProcess(FakeOwnedProcess):
        def __init__(self):
            super().__init__(frames)
            self.stdout = e8_fixture.FakeStdout(raw)
    child = RawProcess()
    owner, called = build_owner(tmp_path, [child])
    async def scenario():
        session = await owner.start_parent()
        with pytest.raises(ValueError):
            await session.receive()
        await session.terminate()
    run(scenario())
    assert len(called) == 1
    assert (tmp_path / "parent-original.jsonl").read_bytes() == raw
    assert child.terminated


def test_startup_config_mismatch_stops_owner_and_keeps_original(tmp_path):
    frames = frame_set("parent-1")
    frames[0]["config"]["username"] = "intruder"
    child = FakeOwnedProcess(frames)
    owner, called = build_owner(tmp_path, [child])
    with pytest.raises(E12Rejected, match="config"):
        run(owner.start_parent())
    assert len(called) == 1 and child.terminated
    assert (tmp_path / "parent-original.jsonl").read_bytes() == e8_fixture.line_bytes(frames)


def test_actual_existing_action3_s15_s16_world_owner_through_fake_transport(monkeypatch):
    async def no_sleep(_seconds):
        return None
    monkeypatch.setattr("adapters.mineflayer.execution.asyncio.sleep", no_sleep)
    data, _failed, inputs = s23._prepare_recovery()
    proposed, binding, _ = s23._propose(inputs)
    _authorized, issued = s23._issue(data, proposed)
    command = build_mineflayer_command(issued, binding)
    frames = (
        replace(s20.s19.observation(1, 0.0), session_id=s23.SESSION3),
        replace(s20.s19.effect(2, s23.ACTION3, "set_control"), session_id=s23.SESSION3),
        replace(s20.s19.effect(3, command.cleanup_action_id, "clear_controls"), session_id=s23.SESSION3),
        replace(s20.s19.observation(4, 0.2), session_id=s23.SESSION3),
    )
    session = s23.RecoverySession(frames)
    result = run(run_issued_parent_action3(
        session, data["supervisor"], issued, binding,
        at_ns=lambda: 60, provenance=s23.p("Action3-issue"),
    ))
    assert result.parent_qualified
    assert result.action.state is ActionState.OUTCOME
    assert result.consequence.session_id == s23.SESSION3
    assert result.interpretation.disposition is ActionOutcomeDisposition.OUTCOME
    assert result.physically_authenticated is False


def test_unissued_action_cannot_launch_real_parent_transact(monkeypatch):
    data, _failed, inputs = s23._prepare_recovery()
    proposed, binding, _ = s23._propose(inputs)
    session = s23.RecoverySession(())
    with pytest.raises(E12Rejected, match="issued"):
        run(run_issued_parent_action3(
            session, data["supervisor"], proposed, binding,
            at_ns=lambda: 60, provenance=s23.p("Action3-issue"),
        ))
    assert session.sent == []
