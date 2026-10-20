"""Actual S49/S16 wait_for paths on one deterministic stdout; DEV ONLY."""
from __future__ import annotations

import asyncio
import contextvars
import hashlib
import json
import sys
from dataclasses import asdict, replace
from pathlib import Path

import pytest

from adapters.mineflayer.process_session import MineflayerProcessEnded, MineflayerProcessSession
from adapters.mineflayer.python_protocol import MineflayerLaunchConfig
from adapters.mineflayer.s31a_real_server_ci import _await_spawn, _correlated_observe
from adapters.mineflayer.self_world_stage_w4_lease import (
    W4DevLeasedSession,
    W4DevNativeObservationPort,
)
from adapters.mineflayer.self_world_stage_w4_logtap import W4CollectorCursor, W4CollectorMarker
from adapters.mineflayer.self_world_stage_w4_preflight import W4PreworldBlocked
from test_mineflayer_process_session import FakeProcess
from test_self_world_stage_w4_prehost import _offline_lines, _wire
from test_self_world_stage_w4_window import TOKEN


@pytest.fixture(autouse=True, scope="module")
def prepare_synchronous_original_fixture():
    _offline_lines()


class Transport:
    def __init__(self, lines):
        self.lines = list(lines)
        self.reads = []
        self.entered = asyncio.Event()
        self.pause = False
        self.cancelled = False

    async def readline(self):
        self.entered.set()
        try:
            if self.pause:
                await asyncio.Future()
            await asyncio.sleep(0)
            raw = self.lines.pop(0) if self.lines else b""
            self.reads.append(raw)
            return raw
        except asyncio.CancelledError:
            self.cancelled = True
            raise


async def launch(monkeypatch, *, lines=None, raw_root=None):
    pre, _, defaults = _offline_lines()
    process = FakeProcess([])
    process.stdout = Transport(defaults if lines is None else lines)

    async def fake_create(*args, **kwargs):
        # The inherited launch path runs, but no OS child or socket exists.
        assert str(args[1]).endswith("bridge.mjs")
        assert kwargs["stdout"] == asyncio.subprocess.PIPE
        return process

    monkeypatch.setattr(asyncio, "create_subprocess_exec", fake_create)
    session = await W4DevLeasedSession.launch(
        MineflayerLaunchConfig(version="1.21.8"), w4_native_orientation_dev=True,
        raw_capture_root=raw_root,
    )
    assert isinstance(session, MineflayerProcessSession)
    owner = session.owner_token()
    await _await_spawn(session)  # EXACT original _new_session's spawn component.
    return session, owner, process, pre


async def preworld(session, owner, pre):
    session.advance(owner=owner, phase="PREWORLD", binding=pre.request_id)
    receipt = await session.capture_preworld(
        owner=owner, request_id=pre.request_id, slot=1, token=TOKEN,
    )
    ledger = session.take_preworld_ledger(owner=owner)
    assert [x.seq for x in ledger.captured_frames] == [2, 3]
    assert [x.seq for x in ledger.buffered_frames] == [2]
    assert ledger.delivery_scope == "PREWORLD_EVIDENCE_ONLY_NOT_L0_STIMULUS"
    assert not receipt.physical_run_permitted
    return receipt, ledger


def marker_for(receipt):
    line = f"[19:00] [Server thread/INFO]: {receipt.candidate_commands.expected_log_suffix}"
    raw = (line + "\n").encode()
    return W4CollectorMarker(W4CollectorCursor(Path('/synthetic/log'), 1, 2, 0),
                             line, 0, len(raw), hashlib.sha256(raw).hexdigest(), 200)


async def host_ready(session, owner, pre):
    receipt, ledger = await preworld(session, owner, pre)
    session.advance(owner=owner, phase="WORLD_WINDOW", binding="fixture-window")
    session.world_marker(owner=owner, marker=marker_for(receipt))
    op = session.advance(owner=owner, phase="HOST", binding="host-1")
    return op, ledger


def test_inherited_startup_wait_for_and_original_spawn(monkeypatch):
    async def run():
        s, _, p, _ = await launch(monkeypatch)
        reads = [a for a in s.audit if a.event == "READ"]
        assert (reads[0].issuer != reads[0].reader) == (sys.version_info < (3, 12))
        assert (reads[1].issuer != reads[1].reader) == (sys.version_info < (3, 12))
        assert len(p.stdout.reads) == 2
        assert [a.seq for a in s.audit if a.event == "DELIVER"] == [0, 1]
    asyncio.run(run())


def test_original_host_wait_for_filter_and_correlated_probe(monkeypatch):
    import test_postmain_s42_world_contrast as s42
    from adapters.mineflayer.normal_action import NormalWorldL0

    retained, _, far, _, _ = s42._pair()

    async def run():
        pre, _, lines = _offline_lines()
        probe = replace(far.observation, session_id=pre.session_id)
        s, owner, p, _ = await launch(monkeypatch, lines=lines[:4] + (
            _wire(probe, 4, kind="entities"), _wire(probe, 5),
        ))
        op, ledger = await host_ready(s, owner, pre)
        host = NormalWorldL0(pre.session_id, "escape-threat", retained, max_events=1, max_action_requests=1)
        port = W4DevNativeObservationPort(s, owner=owner)

        def reprobe(event):
            s.bind_probe(owner=owner, request_id=probe.request_id)
            return s.delegate(owner=owner, operation=s._operation,
                              invoke=lambda: _correlated_observe(s, probe.request_id))

        async def no_action(step):
            raise AssertionError("WAIT fixture must not issue Action")

        trace = await asyncio.wait_for(s.delegate(
            owner=owner, operation=op,
            invoke=lambda: host.run_session(port, probe=reprobe, grant=lambda *_: None,
                                             on_action_request=no_action),
        ), timeout=95)
        assert len(trace) == 1 and trace[0].choice.selection.value == "WAIT"
        assert host.action_requests == 0 and host.events == 1
        assert [a.seq for a in s.audit if a.event == "DELIVER"] == list(range(6))
        assert [x.seq for x in ledger.buffered_frames] == [2]
        assert port.original.ignored_non_target_entities == 0
        assert len(p.stdout.reads) == 6
        assert s._actor is asyncio.current_task() and s._delegated == 0
        s.advance(owner=owner, phase="QUIESCE", binding="quiesce")
        s.advance(owner=owner, phase="SHUTDOWN", binding="shutdown")
        assert await s.shutdown() == 0 and s.phase == "CLOSED"
    asyncio.run(run())


@pytest.mark.parametrize("attack", (
    "foreign_task", "copied_context", "competing_calls", "foreign_owner",
    "stale_epoch", "foreign_operation", "action_before_host", "preworld_reader",
    "window_reader", "untransferred_ledger", "ledger_replay", "no_marker",
    "shutdown_order", "owner_replay", "wrapped_capability", "reserved_handoff",
))
def test_negative_authority_rejected_before_stream_read(monkeypatch, attack):
    async def run():
        s, owner, p, pre = await launch(monkeypatch)
        count = len(p.stdout.reads)
        saved = s._operation
        pending = None

        async def foreign():
            await s.receive()

        with pytest.raises(W4PreworldBlocked):
            if attack == "foreign_task":
                await asyncio.create_task(foreign())
            elif attack == "copied_context":
                token = contextvars.ContextVar('apparent-owner')
                token.set(owner)
                await asyncio.create_task(foreign(), context=contextvars.copy_context())
            elif attack == "competing_calls":
                pending = s.receive()
                s.receive()
            elif attack == "foreign_owner":
                s.advance(owner=object(), phase="PREWORLD", binding="x")
            elif attack == "action_before_host":
                s.advance(owner=owner, phase="ACTION_READ", binding="x")
            elif attack == "preworld_reader":
                s.advance(owner=owner, phase="PREWORLD", binding="x")
                await asyncio.create_task(foreign())
            elif attack == "untransferred_ledger":
                s.advance(owner=owner, phase="PREWORLD", binding=pre.request_id)
                await s.capture_preworld(owner=owner, request_id=pre.request_id, slot=1, token=TOKEN)
                count = len(p.stdout.reads)
                s.advance(owner=owner, phase="WORLD_WINDOW", binding="x")
            elif attack in {"window_reader", "no_marker"}:
                await preworld(s, owner, pre)
                s.advance(owner=owner, phase="WORLD_WINDOW", binding="x")
                count = len(p.stdout.reads)
                if attack == "window_reader":
                    await s.receive()
                else:
                    s.advance(owner=owner, phase="HOST", binding="x")
            elif attack == "ledger_replay":
                await preworld(s, owner, pre)
                count = len(p.stdout.reads)
                s.take_preworld_ledger(owner=owner)
            elif attack == "shutdown_order":
                await s.shutdown()
            else:
                await host_ready(s, owner, pre)
                count = len(p.stdout.reads)
                if attack == "owner_replay":
                    other, other_owner, _, _ = await launch(monkeypatch)
                    assert other_owner is not owner
                    s.advance(owner=other_owner, phase="QUIESCE", binding="x")
                elif attack == "foreign_operation":
                    other, _, _, _ = await launch(monkeypatch)
                    s.delegate(owner=owner, operation=other._operation, invoke=foreign)
                elif attack == "stale_epoch":
                    s.delegate(owner=owner, operation=saved, invoke=foreign)
                elif attack == "reserved_handoff":
                    pending = s.delegate(owner=owner, operation=s._operation, invoke=foreign)
                    s.receive()
                else:
                    pending = s.receive()
                    async def thief():
                        return await pending
                    await asyncio.create_task(thief())
        assert len(p.stdout.reads) == count
        assert s.phase == "BLOCKED"
        if pending is not None:
            pending.close()
        with pytest.raises(W4PreworldBlocked):
            s.receive()
    asyncio.run(run())


@pytest.mark.parametrize("failure", ("cancel", "timeout", "competition", "handoff"))
def test_active_receive_is_drained_and_cannot_be_reused(monkeypatch, failure):
    async def run():
        s, owner, p, pre = await launch(monkeypatch)
        op, _ = await host_ready(s, owner, pre)
        p.stdout.pause = True
        p.stdout.entered.clear()
        coro = s.receive()
        task = asyncio.create_task(coro)
        await p.stdout.entered.wait()
        if failure == "competition":
            with pytest.raises(W4PreworldBlocked):
                s.receive()
        elif failure == "handoff":
            with pytest.raises(W4PreworldBlocked):
                s.advance(owner=owner, phase="QUIESCE", binding="x")
        if failure == "timeout":
            with pytest.raises(TimeoutError):
                await asyncio.wait_for(task, timeout=.001)
        else:
            task.cancel()
            with pytest.raises(asyncio.CancelledError):
                await task
        assert task.done() and p.stdout.cancelled and not s._active
        assert s.phase == "BLOCKED" and len(p.stdout.reads) == 4
        with pytest.raises(W4PreworldBlocked):
            s.delegate(owner=owner, operation=op, invoke=lambda: None)
    asyncio.run(run())


@pytest.mark.parametrize("bad", ("partial", "malformed", "eof", "exit", "session",
                                   "stale_probe", "gap", "wrong_kind"))
def test_decode_and_preworld_failures_are_terminal(monkeypatch, bad):
    async def run():
        pre, _, lines = _offline_lines()
        raw = lines[3]
        if bad == "partial":
            raw = raw.rstrip(b'\n')
        elif bad == "malformed":
            raw = b'{broken}\n'
        elif bad in {"eof", "exit"}:
            raw = b''
        else:
            obj = json.loads(raw)
            if bad == "session":
                obj['session_id'] = 'foreign'
            elif bad == "stale_probe":
                obj['request_id'] = 'foreign-request'
            elif bad == "gap":
                obj['seq'] += 1
            elif bad == "wrong_kind":
                obj['kind'] = 'health'
                obj.pop('request_id')
            raw = (json.dumps(obj) + '\n').encode()
        s, owner, p, _ = await launch(monkeypatch, lines=lines[:3] + (raw,))
        if bad == 'exit':
            p.returncode = 1
        with pytest.raises((W4PreworldBlocked, MineflayerProcessEnded, ValueError)):
            await preworld(s, owner, pre)
        assert s.phase == 'BLOCKED'
        with pytest.raises(W4PreworldBlocked):
            s.receive()
    asyncio.run(run())


def test_no_action_authority_is_created_by_read_epoch(monkeypatch):
    async def run():
        s, owner, p, pre = await launch(monkeypatch)
        await host_ready(s, owner, pre)
        s.advance(owner=owner, phase="ACTION_READ", binding="unissued")
        n = len(p.stdin.writes)
        with pytest.raises(W4PreworldBlocked):
            await s.send_set_control("unissued", control="back", state=True)
        assert len(p.stdin.writes) == n
        assert s.phase == "BLOCKED"
    asyncio.run(run())


@pytest.mark.parametrize("raw_capture", (False, True))
def test_shutdown_eof_and_closed_reopen_rejection(monkeypatch, tmp_path, raw_capture):
    async def run():
        s, owner, p, pre = await launch(monkeypatch, raw_root=tmp_path if raw_capture else None)
        await host_ready(s, owner, pre)
        # No postworld frames consumed in this shutdown-only fixture.
        p.stdout.lines.clear()
        s.advance(owner=owner, phase="QUIESCE", binding="quiet")
        s.advance(owner=owner, phase="SHUTDOWN", binding="stop")
        assert await s.shutdown() == 0
        assert s.phase == "CLOSED"
        if raw_capture:
            assert s.raw_capture_receipt is not None
            assert any(a.event == "EOF" for a in s.audit)
        with pytest.raises(W4PreworldBlocked):
            s.advance(owner=owner, phase="HOST", binding="reopen")
    asyncio.run(run())


@pytest.mark.parametrize("authority", ("issued", "missing_propose", "missing_issue"))
def test_original_host_to_normal_executor_and_s16_receive_until(monkeypatch, authority):
    import test_action_feedback_qualification as s17
    import test_postmain_s42_world_contrast as s42
    from adapters.mineflayer.normal_action import (
        NormalActionAuthorization,
        NormalActionRejected,
        NormalActionStage,
        NormalSessionActionExecutor,
        NormalWorldL0,
    )
    from adapters.mineflayer.s34_native_world_cognition_ci import _native_epoch_two, _native_threat
    from relay_self.action_supervision import ActionSupervisor
    from relay_self.execution_binding import ExecutionBinding, resolve_execution_binding
    from relay_self.intent import IntentCommitment
    from relay_self.provenance import Provenance
    from relay_self.reactive_l0 import L0ActionGrant

    retained, near, _, _, _ = s42._pair()
    pre, _, lines = _offline_lines()
    probe_template = replace(near.observation, session_id=pre.session_id, request_id="fixture-host-probe")
    action_id = "fixture-native-move-4"
    frames = []
    for seq, x in ((6, 0.), (9, .2)):
        legacy = json.loads(_wire(replace(s17.observation(seq, x, 0.), session_id=pre.session_id), seq))
        legacy.pop('request_id')
        frames.append((json.dumps(legacy) + '\n').encode())
    def effect(seq, name, aid):
        data = asdict(s17.effect(seq, aid, name))
        data.update(type="effect_result", session_id=pre.session_id)
        return (json.dumps(data) + '\n').encode()
    all_lines = lines[:4] + (_wire(probe_template, 4, kind="entities"),
                            _wire(probe_template, 5), frames[0],
                            effect(7, 'set_control', action_id),
                            effect(8, 'clear_controls', action_id + '-s15-clear'), frames[1])

    async def run():
        s, owner, p, _ = await launch(monkeypatch, lines=all_lines)
        op, _ = await host_ready(s, owner, pre)
        intent = IntentCommitment()
        intent.commit("escape-threat", objective="escape near zombie", at_ns=1,
                      provenance=Provenance("fixture-operator", "intent"))
        executor = NormalSessionActionExecutor(pre.session_id, intent)
        host = NormalWorldL0(pre.session_id, "escape-threat", retained,
                             max_events=1, max_action_requests=1)
        port = W4DevNativeObservationPort(s, owner=owner)
        probes = []
        receipts = []

        async def original_probe():
            probe = await _correlated_observe(s, probe_template.request_id)
            probes.append(probe)
            return probe

        def reprobe(event):
            s.bind_probe(owner=owner, request_id=probe_template.request_id)
            return s.delegate(owner=owner, operation=s._operation, invoke=original_probe)

        def grant(choice, event_seq):
            return L0ActionGrant("fixture-l0", action_id, "escape-threat", pre.session_id,
                                 event_seq, choice.probe_seq, choice.entity_id, True,
                                 Provenance("fixture-operator", "l0"))

        async def on_action(step):
            probe = probes[-1]
            values, _ = _native_epoch_two(
                ActionSupervisor(), intent, retained, retained, expected_revision=1,
                native=_native_threat(probe, probe.request_id,
                                      expected_entity_id=step.choice.entity_id),
            )
            binding = ExecutionBinding(
                binding_id="fixture-binding", candidate_ref="MOVE_AWAY",
                required_intent_id="escape-threat", skill_execution_id="fixture-skill",
                skill_ref="escape-movement", action_id=action_id, action_ref="MOVE_BACKWARD",
                provenance=Provenance("fixture-operator", "binding"),
            )
            bound = resolve_execution_binding(
                values['admission'], values['control'], values['route'], intent,
                values['policies'][-2], binding,
                provenance=Provenance("fixture-operator", "admitted"),
            )
            def auth(stage):
                if authority == 'missing_' + stage.value.lower():
                    return None
                return NormalActionAuthorization(
                    stage, 'fixture-' + stage.value, 'escape-threat', pre.session_id,
                    action_id, step.event_seq, probe.seq, step.choice.entity_id, True,
                    Provenance('fixture-operator', stage.value),
                )
            s.advance(owner=owner, phase="ACTION_READ", binding=action_id,
                      supervisor=executor.supervisor)
            receipts.append(await executor.execute(
                s, step, bound, probe, auth(NormalActionStage.PROPOSE), auth(NormalActionStage.ISSUE),
            ))
            assert receipts[-1].consequence.error is None, receipts[-1].consequence.error
            s.advance(owner=owner, phase="HOST", binding="host-return")

        async def original_host():
            return await host.run_session(port, probe=reprobe, grant=grant,
                                          on_action_request=on_action)

        operation = s.delegate(owner=owner, operation=op, invoke=original_host)
        if authority != 'issued':
            with pytest.raises(NormalActionRejected):
                await asyncio.wait_for(operation, timeout=95)
            assert len(p.stdout.reads) == 6
            assert len(p.stdin.writes) == 2  # only preworld + reprobe
            assert not executor.supervisor.open_actions
            assert s.phase == 'BLOCKED'
            return
        trace = await asyncio.wait_for(operation, timeout=95)
        assert trace[0].asks_for_action and len(receipts) == 1
        receipt = receipts[0]
        assert receipt.terminal.state.value == 'outcome'
        assert receipt.consequence.status.value == 'executed'
        assert receipt.consequence.cleanup_attempted
        assert receipt.consequence.before_observation.seq == 6
        assert receipt.consequence.dispatch_receipt.seq == 7
        assert receipt.consequence.cleanup_receipt.seq == 8
        assert receipt.consequence.after_observation.seq == 9
        assert not executor.supervisor.open_actions
        reads = [a for a in s.audit if a.event == 'READ' and a.phase == 'ACTION_READ']
        assert len(reads) == 4
        if sys.version_info < (3, 12):
            assert all(a.issuer != a.reader for a in reads)
            assert len({a.reader for a in reads}) == 4
        assert [a.seq for a in s.audit if a.event == 'DELIVER'] == list(range(10))
        assert s.phase == 'HOST' and s._delegated == 0 and s._pending is None
        assert host.retained is retained  # no S10 handoff/write
        s.advance(owner=owner, phase="QUIESCE", binding="quiet")
        s.advance(owner=owner, phase="SHUTDOWN", binding="stop")
        assert await s.shutdown() == 0
    asyncio.run(run())


@pytest.mark.parametrize('failure', ('host_cancel', 'host_timeout', 'stale_child',
                                    'repeated_request', 'shutdown_exit', 'shutdown_timeout'))
def test_delegation_and_terminal_order_negatives(monkeypatch, failure):
    async def run():
        s, owner, p, pre = await launch(monkeypatch)
        op, _ = await host_ready(s, owner, pre)
        if failure.startswith('shutdown'):
            s.advance(owner=owner, phase='QUIESCE', binding='quiet')
            s.advance(owner=owner, phase='SHUTDOWN', binding='stop')
            if failure == 'shutdown_exit':
                p.returncode = 1
            else:
                async def stalled_wait():
                    if not p.terminated:
                        await asyncio.Future()
                    return p.returncode
                p.wait = stalled_wait
            with pytest.raises((W4PreworldBlocked, MineflayerProcessEnded)):
                await s.shutdown(timeout_s=.001)
            assert s.phase == 'BLOCKED'
            return
        if failure == 'repeated_request':
            s.bind_probe(owner=owner, request_id='probe-repeat')
            with pytest.raises(W4PreworldBlocked):
                s.bind_probe(owner=owner, request_id='probe-repeat')
            assert len(p.stdout.reads) == 4
            return
        entered = asyncio.Event()
        release = asyncio.Event()
        children = []
        async def foreign_after_return():
            await release.wait()
            await s.receive()
        async def work():
            entered.set()
            if failure == 'stale_child':
                children.append(asyncio.create_task(foreign_after_return()))
                return
            await asyncio.Future()
        task = asyncio.create_task(s.delegate(owner=owner, operation=op, invoke=work))
        await entered.wait()
        if failure == 'stale_child':
            await asyncio.wait_for(task, timeout=95)
            s.advance(owner=owner, phase='QUIESCE', binding='quiet')
            release.set()
            with pytest.raises(W4PreworldBlocked):
                await children[0]
        elif failure == 'host_cancel':
            task.cancel()
            with pytest.raises(asyncio.CancelledError):
                await task
        else:
            with pytest.raises(TimeoutError):
                await asyncio.wait_for(task, timeout=.001)
        assert s.phase == 'BLOCKED' and s._delegated == 0
        assert len(p.stdout.reads) == 4
        with pytest.raises(W4PreworldBlocked):
            s.receive()
    asyncio.run(run())


@pytest.mark.parametrize("attempt_handoff", (False, True))
def test_cancellation_resistant_read_cannot_handoff_or_deliver(monkeypatch, attempt_handoff):
    async def run():
        s, owner, p, pre = await launch(monkeypatch)
        await host_ready(s, owner, pre)
        entered, cancelled, release = asyncio.Event(), asyncio.Event(), asyncio.Event()
        original_read = p.stdout.readline
        async def resistant():
            entered.set()
            try:
                await asyncio.Future()
            except asyncio.CancelledError:
                cancelled.set()
                await release.wait()
            return await original_read()
        p.stdout.readline = resistant
        task = asyncio.create_task(s.receive())
        await entered.wait()
        task.cancel()
        await cancelled.wait()
        assert not task.done() and s._active
        if attempt_handoff:
            with pytest.raises(W4PreworldBlocked):
                s.advance(owner=owner, phase='QUIESCE', binding='illegal-handoff')
        assert s._active
        release.set()
        with pytest.raises(W4PreworldBlocked):
            await task
        assert not s._active and task.done() and s.phase == 'BLOCKED'
        assert [a.seq for a in s.audit if a.event == 'DELIVER'] == [0, 1, 2, 3]
        assert [a.seq for a in s.audit if a.event == 'DECODED'] == [0, 1, 2, 3, 4]
    asyncio.run(run())


def test_unknown_shutdown_delegation_target_is_denied_before_read(monkeypatch):
    async def run():
        s, owner, p, pre = await launch(monkeypatch)
        op, _ = await host_ready(s, owner, pre)
        async def work():
            await s.receive()
        capability = s.delegate(owner=owner, operation=op, invoke=work)
        async def thief():
            await capability
        with pytest.raises(W4PreworldBlocked):
            await asyncio.create_task(thief())
        assert len(p.stdout.reads) == 4 and s.phase == 'BLOCKED'
    asyncio.run(run())


PROTECTED_BLOBS = {'adapters/mineflayer/s49_normal_session_real_ci.py': 'fd2b06e9dbed17be0e35b3a1bbd0ed423b9af258', 'adapters/mineflayer/s34_native_world_cognition_ci.py': 'eaecb117ad26059d6d2abb2c12bca61b2dce1f01', 'adapters/mineflayer/s31a_real_server_ci.py': '7ee3e95af66e1b981f72509a3dd661d79ef95744', 'adapters/mineflayer/process_session.py': '6eec8f80621c581d47154f7c76e72303e00c04f0', 'adapters/mineflayer/normal_action.py': '0ded8fa296c92076a643de08cd6fc360061e1d08', 'adapters/mineflayer/execution.py': '2af25bc6808f8a4199fe2ee500d1c1dfbea25de2', 'adapters/mineflayer/action_outcome.py': '502a14304c8ab9f5e37bff4a054cf2a21730d294', 'src/relay_self/intent.py': 'f4ef9500cd7941e5e9e07fd41ac2b6e4b4d5ac25', 'src/relay_self/skill.py': '61885956810b4125721f685d449b361262b71120', 'src/relay_self/action.py': '869e761cfa2646f48f12e5e8088375ae64f04607', 'src/relay_self/action_supervision.py': '3320caab19d05afa74f046e3e0f143bc1aad5821', 'src/relay_self/learning.py': '9fd949e94e91ded1c070d359378833f354fba577', 'src/relay_self/habit.py': 'edc8904753421ef836843ae736f194f5a3a39168', 'src/relay_self/action_feedback.py': '8ae84e2e555550128a59a23c342f67a032a0c859', 'src/relay_self/action_outcome.py': 'd28bbc1745104bcd7872061bef2fe6222ceccb2a', 'docs/postmain-architecture.json': 'e8419c55b5535d451346fd2a9a3c42326a80aa29', 'docs/postmain-architecture.md': '62b8e807d1b35a7f06d15b61e411434f57fe111d', 'tests/test_postmain_architecture_freeze.py': 'd343aa052541b4ee9d2ce3e00653cc1a56d681ce', 'src/relay_self/persistent_cognition.py': '5d4fff3fa10bad78f98118758c8a22d53e8390fb'}


def test_s18_and_original_default_routes_are_blob_identical():
    import subprocess

    from adapters.mineflayer import s34_native_world_cognition_ci as s34
    from adapters.mineflayer import s49_normal_session_real_ci as s49

    root = Path(__file__).resolve().parents[1]
    for path, expected in PROTECTED_BLOBS.items():
        actual = subprocess.check_output(['git', 'hash-object', str(root / path)], text=True).strip()
        assert actual == expected, path
    assert s34.MineflayerProcessSession is MineflayerProcessSession
    assert s49._new_session is s34._new_session
    for path in ('adapters/mineflayer/s49_normal_session_real_ci.py',
                 'adapters/mineflayer/s34_native_world_cognition_ci.py'):
        assert 'self_world_stage_w4_lease' not in (root / path).read_text()
    assert MineflayerProcessSession.receive.__module__ == 'adapters.mineflayer.process_session'


def test_lease_world_handoff_uses_original_server_collector(monkeypatch, tmp_path):
    from types import SimpleNamespace

    from adapters.mineflayer.s31a_real_server_ci import _command, _ready_server
    from adapters.mineflayer.self_world_stage_w4_logtap import (
        capture_w4_collector_cursor,
        wait_for_w4_collector_marker,
    )

    async def run():
        s, owner, p, pre = await launch(monkeypatch)
        receipt, ledger = await preworld(s, owner, pre)
        commands = receipt.candidate_commands
        stream = asyncio.StreamReader()
        stream.feed_data(b'[00:00] [Server thread/INFO]: Done (1s)! For help\n')
        writes = []
        class Sink:
            def write(self, raw):
                writes.append(raw)
                if raw == (commands.confirm_command + '\n').encode():
                    stream.feed_data(('[19:00] [Server thread/INFO]: '
                                      + commands.expected_log_suffix + '\n').encode())
            async def drain(self):
                return None
        server = SimpleNamespace(stdin=Sink(), stdout=stream, pid=4242, returncode=None)
        async def fixture_java(*args, **kwargs):
            assert args[0] == 'java'
            return server  # NEVER forwards to the OS
        monkeypatch.setattr(asyncio, 'create_subprocess_exec', fixture_java)
        log = tmp_path / 'original-server.log'
        original, collector, _ = await _ready_server(tmp_path, tmp_path / 'fake.jar', log)
        try:
            cursor = capture_w4_collector_cursor(log)
            s.advance(owner=owner, phase='WORLD_WINDOW', binding='fixture-staging')
            for command in (commands.summon_command, commands.confirm_command):
                _command(original, command)
                await original.stdin.drain()
            marker = await wait_for_w4_collector_marker(cursor, commands, timeout_s=.2, poll_s=.001)
            s.world_marker(owner=owner, marker=marker)
            op = s.advance(owner=owner, phase='HOST', binding='host-after-collector')
            _, post, _ = _offline_lines()
            async def work():
                event = await W4DevNativeObservationPort(s, owner=owner).receive()
                s.bind_probe(owner=owner, request_id=post.request_id)
                after = await _correlated_observe(s, post.request_id)
                readback = s._bridge._handoff.after_world(after, owner=owner,
                                                         request_id=post.request_id)
                assert event.seq == 4 and after.seq == 5
                assert not readback.physical_run_permitted
            await asyncio.wait_for(s.delegate(owner=owner, operation=op, invoke=work), timeout=95)
            assert len(writes) == 2 and len(p.stdout.reads) == 6
            assert [f.seq for f in ledger.captured_frames] == [2, 3]
            assert not marker.external_source_qualified
        finally:
            stream.feed_eof()
            await collector
    asyncio.run(run())


@pytest.mark.parametrize('kind', ('adapter_error', 'command_error', 'connection_end', 'foreign_effect'))
def test_terminal_or_foreign_readback_is_not_delivered(monkeypatch, kind):
    async def run():
        pre, _, lines = _offline_lines()
        if kind == 'foreign_effect':
            payload = dict(type='effect_result', action_id='foreign', effect='set_control',
                           result='applied', error=None)
        else:
            payload = dict(type=kind)
            payload['reason' if kind == 'connection_end' else 'message'] = 'fixture-terminal'
        payload.update(seq=4, session_id=pre.session_id)
        s, owner, p, _ = await launch(monkeypatch, lines=lines[:4] + (
            (json.dumps(payload) + '\n').encode(),
        ))
        await host_ready(s, owner, pre)
        with pytest.raises(W4PreworldBlocked):
            await asyncio.wait_for(s.receive(), timeout=2)
        assert s.phase == 'BLOCKED' and len(p.stdout.reads) == 5
        assert [a.seq for a in s.audit if a.event == 'DELIVER'] == [0, 1, 2, 3]
        assert [a.seq for a in s.audit if a.event == 'DECODED'] == [0, 1, 2, 3, 4]
    asyncio.run(run())


def test_closed_phase_cannot_replace_original_process_shutdown(monkeypatch):
    async def run():
        s, owner, p, pre = await launch(monkeypatch)
        await host_ready(s, owner, pre)
        s.advance(owner=owner, phase='QUIESCE', binding='quiet')
        s.advance(owner=owner, phase='SHUTDOWN', binding='stop')
        with pytest.raises(W4PreworldBlocked):
            s.advance(owner=owner, phase='CLOSED', binding='forged-close')
        assert p.returncode is None and p.wait_count == 0
        assert s.phase == 'BLOCKED'
    asyncio.run(run())
