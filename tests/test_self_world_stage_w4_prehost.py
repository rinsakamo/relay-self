"""W4-PREHOST original-session stream accounting; synthetic only."""
from __future__ import annotations

import asyncio
from collections import deque
from dataclasses import replace
from functools import lru_cache

import pytest

from adapters.mineflayer.self_world_stage_w4_preflight import W4PreworldBlocked
from adapters.mineflayer.self_world_stage_w4_prehost import W4PrehostOwnerBridge
from test_self_world_stage_w4 import _oriented_closed
from test_self_world_stage_w4_window import TOKEN, _sample


class FakeOriginalSession:
    def __init__(self, frames):
        self.frames = deque(frames)
        self.requests = []
        self.read_calls = 0

    async def send_observe(self, request_id):
        self.requests.append(request_id)

    async def receive(self):
        self.read_calls += 1
        await asyncio.sleep(0)
        if not self.frames:
            raise RuntimeError("fixture stream exhausted")
        return self.frames.popleft()


def _build(frames=None):
    pre, _post, _, _, _ = _sample()
    # Existing owner may see an unrelated non-zombie entities frame before
    # the exact correlated preworld orientation probe. Keep original seq order.
    entities = replace(pre, seq=0, kind="entities", request_id=None)
    source = FakeOriginalSession([entities, pre] if frames is None else frames)
    owner = object()
    bridge = W4PrehostOwnerBridge(
        session=source, session_id=pre.session_id, owner=owner,
    )
    return pre, owner, source, bridge


def _capture(bridge, default_owner, pre, **overrides):
    kwargs = dict(
        owner=default_owner, request_id=pre.request_id, slot=1, token=TOKEN,
    )
    kwargs.update(overrides)
    return bridge.capture(**kwargs)


def test_one_same_stream_reader_preserves_preplacement_unsolicited_frames():
    pre, owner, source, bridge = _build()

    async def run():
        result = await _capture(bridge, owner, pre)
        assert result.observation_source == pre.provenance.reference
        assert result.candidate_commands.session_id == pre.session_id
        assert not result.physical_run_permitted
        assert bridge.state == "AWAIT_PREWORLD_LEDGER"
        ledger = bridge.take_pre_world_ledger(owner=owner)
        assert ledger.session_id == pre.session_id
        assert ledger.first_seq == 0 and ledger.last_seq == pre.seq
        assert len(ledger.buffered_frames) == 1
        assert ledger.buffered_frames[0].kind == "entities"
        assert ledger.buffered_frames[0].seq == 0
        assert ledger.delivery_scope == "PREWORLD_EVIDENCE_ONLY_NOT_L0_STIMULUS"
        assert not ledger.original_reader_lease_attested
        assert not ledger.physical_run_permitted
        assert bridge.state == "HANDED_OFF"

    asyncio.run(run())
    assert source.requests == [pre.request_id]
    assert source.read_calls == 2


@pytest.mark.parametrize("corruption", (
    "other_session", "out_of_order", "other_probe", "premature_host",
    "premature_world", "foreign_owner", "wrong_target", "unknown_kind",
    "missing_probe", "bad_token", "duplicate_capture",
))
def test_prehost_fail_closed_and_never_relabels_stale_frames(corruption):
    pre, owner, source, bridge = _build()
    entity = replace(pre, seq=0, kind="entities", request_id=None)
    if corruption == "other_session":
        source.frames = deque([replace(entity, session_id="foreign"), pre])
    elif corruption == "out_of_order":
        source.frames = deque([replace(entity, seq=pre.seq), pre])
    elif corruption == "other_probe":
        source.frames = deque([replace(pre, request_id="other")])
    elif corruption == "wrong_target":
        _other, closed = _oriented_closed()
        zombie = closed.original_probe.snapshot.nearby_entities
        bad = replace(entity, snapshot=replace(
            entity.snapshot, nearby_entities=zombie,
            nearby_entities_coverage=replace(
                entity.snapshot.nearby_entities_coverage,
                candidate_count=len(zombie),
            ),
        ))
        source.frames = deque([bad, pre])
    elif corruption == "unknown_kind":
        source.frames = deque([replace(pre, kind="spawn", request_id=None), pre])
    elif corruption == "missing_probe":
        source.frames = deque([entity] * 33)

    async def run():
        opts = {}
        if corruption == "premature_host":
            opts["host_loop_started"] = True
        elif corruption == "premature_world":
            opts["stage_world_started"] = True
        elif corruption == "foreign_owner":
            opts["owner"] = object()
        elif corruption == "bad_token":
            opts["token"] = "invalid"
        elif corruption == "duplicate_capture":
            await _capture(bridge, owner, pre)
        with pytest.raises((W4PreworldBlocked, TimeoutError, RuntimeError)):
            await _capture(bridge, owner, pre, **opts)
        assert bridge.state == "BLOCKED"

    asyncio.run(run())


def test_ledger_transfer_is_single_use_and_other_owner_cannot_steal_it():
    pre, owner, _source, bridge = _build()

    async def run():
        await _capture(bridge, owner, pre)
        with pytest.raises(W4PreworldBlocked):
            bridge.take_pre_world_ledger(owner=object())

    asyncio.run(run())
    assert bridge.state == "BLOCKED"


def test_no_real_second_reader_or_minecraft_process_is_spawned():
    pre, owner, source, bridge = _build()
    source.frames = deque([pre])

    async def run():
        await _capture(bridge, owner, pre)
        ledger = bridge.take_pre_world_ledger(owner=owner)
        assert not ledger.buffered_frames
        assert source.read_calls == 1
        assert source.requests == [pre.request_id]
        with pytest.raises(W4PreworldBlocked):
            bridge.take_pre_world_ledger(owner=owner)

    asyncio.run(run())


def test_cancelled_owner_task_blocks_reentry():
    pre, owner, _source, bridge = _build()
    started = asyncio.Event()

    async def slow_receive():
        started.set()
        await asyncio.Future()

    bridge._session.receive = slow_receive

    async def run():
        task = asyncio.create_task(_capture(bridge, owner, pre))
        await started.wait()
        task.cancel()
        with pytest.raises(asyncio.CancelledError):
            await task
        assert bridge.state == "BLOCKED"
        with pytest.raises(W4PreworldBlocked):
            await _capture(bridge, owner, pre)

    asyncio.run(run())


def _wire(frame, seq, *, kind=None):
    import json
    from dataclasses import asdict

    payload = dict(type="observation", session_id=frame.session_id, seq=seq,
                   kind=kind or frame.kind, snapshot=asdict(frame.snapshot))
    for entity in payload["snapshot"]["nearby_entities"]:
        entity["id"] = entity.pop("entity_id")
        entity["type"] = entity.pop("entity_type")
    if payload["kind"] == "probe":
        payload["request_id"] = frame.request_id
    return (json.dumps(payload) + "\n").encode()


@lru_cache(maxsize=1)
def _offline_lines():
    import json

    from test_mineflayer_process_session import started_line

    pre, post, _, _, _ = _sample()
    start = json.loads(started_line())
    start["session_id"] = pre.session_id
    return pre, post, (
        (json.dumps(start) + "\n").encode(),
        _wire(pre, 1, kind="spawn"),
        _wire(pre, 2, kind="entities"),
        _wire(pre, 3),
        _wire(post, 4, kind="entities"),
        _wire(post, 5),
    )


def test_offline_real_decoder_spawn_filter_and_correlated_probe():
    from adapters.mineflayer.self_world_stage_w4_prehost import W4OfflineS49Owner

    pre, post, lines = _offline_lines()
    owner = object()
    seam = W4OfflineS49Owner(lines, owner=owner)

    async def run():
        await seam.start(owner=owner)
        receipt, ledger = await seam.preworld(
            owner=owner, request_id=pre.request_id, slot=1, token=TOKEN,
        )
        assert receipt.observation_source == f"{pre.session_id}:3"
        assert [x.seq for x in ledger.buffered_frames] == [2]
        seam.begin_staging(owner=owner)
        _fixture_handoff(seam, owner)
        event = await seam.host_receive(owner=owner)
        reading = await seam.host_probe(owner=owner, request_id=post.request_id)
        assert event.seq == 4 and reading.seq == 5
        assert [x.seq for x in seam.host_deliveries] == [4]
        assert [(phase, f.seq) for phase, f in seam.audit] == [
            ("STARTUP", 0), ("STARTUP", 1), ("PREHOST", 2),
            ("PREHOST", 3), ("HOST", 4), ("HOST", 5),
        ]
        assert len(seam.commands) == 2
        assert all(b'"observe"' in x for x in seam.commands)
        seam.close(owner=owner)

    asyncio.run(run())


@pytest.mark.parametrize("bad", (
    "gap", "duplicate", "reverse", "foreign_session", "foreign_request",
    "unknown", "eof", "preexisting_zombie", "probe_zombie", "foreign_owner", "foreign_task",
    "after_staging", "after_host", "handoff_twice", "direct_reader", "token_reuse",
))
def test_offline_real_stream_rejects_corruptions_and_phase_conflicts(bad):
    import json

    from adapters.mineflayer.process_session import MineflayerProcessEnded
    from adapters.mineflayer.python_protocol import MineflayerAdapterProtocolError
    from adapters.mineflayer.self_world_stage_w4_prehost import W4OfflineS49Owner

    pre, post, lines = _offline_lines()
    lines = list(lines)
    if bad in {"gap", "duplicate", "reverse", "foreign_session", "foreign_request", "unknown"}:
        payload = json.loads(lines[3])
        if bad in {"gap", "duplicate", "reverse"}:
            payload["seq"] = {"gap": 4, "duplicate": 2, "reverse": 1}[bad]
        elif bad == "foreign_session":
            payload["session_id"] = "foreign"
        elif bad == "foreign_request":
            payload["request_id"] = "foreign"
        else:
            payload["type"] = "unknown"
        lines[3] = (json.dumps(payload) + "\n").encode()
    elif bad == "eof":
        lines = lines[:3]
    elif bad == "preexisting_zombie":
        lines[2] = _wire(post, 2, kind="entities")
    elif bad == "probe_zombie":
        lines[3] = _wire(replace(post, request_id=pre.request_id), 3)
    owner = object()
    seam = W4OfflineS49Owner(tuple(lines), owner=owner)

    async def capture(who=owner):
        return await seam.preworld(owner=who, request_id=pre.request_id, slot=1, token=TOKEN)

    async def run():
        await seam.start(owner=owner)
        with pytest.raises((W4PreworldBlocked, MineflayerAdapterProtocolError, MineflayerProcessEnded)):
            if bad == "foreign_owner":
                await capture(object())
            elif bad == "foreign_task":
                await asyncio.create_task(capture())
            elif bad == "direct_reader":
                await seam.receive()
            elif bad in {"after_staging", "after_host", "handoff_twice", "token_reuse"}:
                await capture()
                seam.begin_staging(owner=owner)
                if bad in {"after_host", "handoff_twice"}:
                    _fixture_handoff(seam, owner)
                if bad == "handoff_twice":
                    _fixture_handoff(seam, owner)
                else:
                    await capture()
            else:
                await capture()
        assert seam.phase == "BLOCKED"
        with pytest.raises(W4PreworldBlocked):
            await capture()

    asyncio.run(run())


def test_offline_original_host_loop_wait_has_no_action_or_outcome():
    import test_postmain_s42_world_contrast as s42
    from adapters.mineflayer.normal_action import NormalWorldL0
    from adapters.mineflayer.self_world_stage_w4_prehost import W4OfflineS49Owner

    pre, _post, lines = _offline_lines()
    retained, _, far, _, _ = s42._pair()
    # Native packets keep one session/strict contiguous seq. Far geometry is
    # the existing original S49 WAIT fixture; no grant or executor is installed.
    far_probe = replace(far.observation, session_id=pre.session_id)
    owner = object()
    seam = W4OfflineS49Owner(lines[:4] + (
        _wire(far_probe, 4, kind="entities"), _wire(far_probe, 5),
    ), owner=owner)

    async def run():
        await seam.start(owner=owner)
        await seam.preworld(owner=owner, request_id=pre.request_id, slot=1, token=TOKEN)
        seam.begin_staging(owner=owner)
        _fixture_handoff(seam, owner)
        host = NormalWorldL0(pre.session_id, "escape-threat", retained,
                             max_events=1, max_action_requests=1)
        trace = await seam.run_host(host, owner=owner, request_id=far_probe.request_id)
        assert len(trace) == 1 and trace[0].choice.selection.value == "WAIT"
        assert not trace[0].asks_for_action
        assert host.action_requests == 0
        assert [f.seq for f in seam.host_deliveries] == [4]
        assert [f.seq for _, f in seam.audit] == list(range(6))
        seam.close(owner=owner)

    asyncio.run(run())


@pytest.mark.parametrize("ending", ("competition", "cancel", "timeout"))
def test_offline_inflight_reader_lease_is_terminal_on_interrupt(ending):
    from adapters.mineflayer.self_world_stage_w4_prehost import W4OfflineS49Owner

    pre, _, lines = _offline_lines()
    owner = object()
    seam = W4OfflineS49Owner(lines, owner=owner)
    entered = asyncio.Event()

    async def stalled_receive():
        entered.set()
        await asyncio.Future()

    async def owning_task():
        await seam.start(owner=owner)
        seam._session.receive = stalled_receive
        await seam.preworld(owner=owner, request_id=pre.request_id, slot=1, token=TOKEN)

    async def run():
        task = asyncio.create_task(owning_task())
        await entered.wait()
        if ending == "competition":
            with pytest.raises(W4PreworldBlocked, match="competing reader"):
                await seam.receive()
        if ending == "timeout":
            with pytest.raises(TimeoutError):
                await task
        else:
            task.cancel()
            with pytest.raises(asyncio.CancelledError):
                await task
        assert seam.phase == "BLOCKED" and not seam._busy
        with pytest.raises(W4PreworldBlocked):
            await seam.preworld(owner=owner, request_id=pre.request_id, slot=1, token=TOKEN)
        assert len(seam.raw_audit) == 2

    asyncio.run(run())


def test_offline_original_server_collector_and_world_command_window(monkeypatch, tmp_path):
    import time
    from types import SimpleNamespace

    from adapters.mineflayer.s31a_real_server_ci import _command, _ready_server
    from adapters.mineflayer.self_world_stage_w4_logtap import (
        capture_w4_collector_cursor,
        marker_as_w4_window_event,
        wait_for_w4_collector_marker,
    )
    from adapters.mineflayer.self_world_stage_w4_prehost import W4OfflineS49Owner
    from adapters.mineflayer.self_world_stage_w4_window import (
        W4WindowEvent,
        join_w4_window_and_s16_offline,
        reconcile_w4_window_offline,
    )

    pre, post, lines = _offline_lines()
    owner = object()
    seam = W4OfflineS49Owner(lines, owner=owner)
    events = []
    writes = []
    launches = []
    _, _, _, _, synthetic_closure_fixture = _sample()

    async def run():
        await seam.start(owner=owner)
        receipt, ledger = await seam.preworld(
            owner=owner, request_id=pre.request_id, slot=1, token=TOKEN,
        )
        before = seam.audit[-1][1]
        commands = receipt.candidate_commands
        gate = seam._bridge._handoff
        assert gate.phase == "AWAIT_MARKER" and gate._commands == commands
        assert ledger.captured_frames[-1] == before
        stream = asyncio.StreamReader()
        stream.feed_data(b'[00:00:00] [Server thread/INFO]: Done (1s)! For help\n')

        class FakeServerInput:
            def write(inner, raw):
                writes.append(raw)
                if raw == (commands.confirm_command + "\n").encode():
                    stream.feed_data(("[19:00:00] [Server thread/INFO]: "
                                      + commands.expected_log_suffix + "\n").encode())

            async def drain(inner):
                return None

        server = SimpleNamespace(stdin=FakeServerInput(), stdout=stream,
                                 returncode=None, pid=4242)

        async def never_launch(*args, **kwargs):
            assert args[0] == "java"
            launches.append(args)
            return server

        # This test invokes the ORIGINAL collector closure with fake pipes.
        # No fallback delegates to a real subprocess, even on unexpected argv.
        monkeypatch.setattr(asyncio, "create_subprocess_exec", never_launch)
        log = tmp_path / "original-collector.log"
        original_server, collector, _ = await _ready_server(tmp_path, tmp_path / "fake.jar", log)
        try:
            def record(name, content, server_event=False):
                events.append(W4WindowEvent(
                    name, len(events) + 1, time.monotonic_ns(),
                    "existing_world_experimenter" if server_event else "sole_native_reader",
                    content, server_pid=4242 if server_event else None,
                ))

            record("native_before_probe", before.provenance.reference)
            cursor = capture_w4_collector_cursor(log)
            seam.begin_staging(owner=owner)
            for label, command, digest in (
                ("summon", commands.summon_command, commands.summon_sha256),
                ("confirm", commands.confirm_command, commands.confirm_sha256),
            ):
                _command(original_server, command)
                record(f"server_{label}_write", digest, True)
                await original_server.stdin.drain()
                record(f"server_{label}_drain", digest, True)
            marker = await wait_for_w4_collector_marker(cursor, commands, timeout_s=0.2, poll_s=0.001)
            events.append(marker_as_w4_window_event(marker, order=len(events) + 1, server_pid=4242))
            seam.handoff_host(owner=owner, marker=marker)
            event = await seam.host_receive(owner=owner)
            after = await seam.host_probe(owner=owner, request_id=post.request_id)
            record("native_after_probe", after.provenance.reference)
            readback = gate.after_world(after, owner=owner, request_id=post.request_id)
            window = reconcile_w4_window_offline(
                before, after, expected_session=pre.session_id,
                before_request_id=pre.request_id, after_request_id=post.request_id,
                minimum_seq=3, slot=1, one_time_token=TOKEN,
                events=tuple(events), seen_tokens=frozenset(),
            )
            assert window["observed_zombie_id"] == event.snapshot.nearby_entities[0].entity_id
            # Construct a NEW offline closure fixture, never alter frozen W3
            # evidence or emit a physical S16. Align the fixture's sequence
            # namespace with the startup/interleaved frames in this transport.
            synthetic_closed = synthetic_closure_fixture
            consequence = synthetic_closed.consequence
            shifted = replace(consequence, **{
                name: replace(getattr(consequence, name), seq=getattr(consequence, name).seq + 3)
                for name in ("before_observation", "after_observation",
                             "dispatch_receipt", "cleanup_receipt")
            })
            synthetic_closed = replace(synthetic_closed, original_probe=after, consequence=shifted)
            joined = join_w4_window_and_s16_offline(
                before, synthetic_closed, expected_session=pre.session_id,
                before_request_id=pre.request_id, minimum_seq=3, slot=1,
                one_time_token=TOKEN, events=tuple(events), seen_tokens=frozenset(),
            )
            assert joined["original_s16_stage_s"]["stage_s_direction"] == "hold"
            assert not joined["physical_run_permitted"]
            assert not readback.physical_run_permitted
            assert writes == [(commands.summon_command + "\n").encode(),
                              (commands.confirm_command + "\n").encode()]
            assert len(launches) == 1
            assert [f.seq for f in seam.host_deliveries] == [4]
            seam.close(owner=owner)
        finally:
            stream.feed_eof()
            await collector

    asyncio.run(run())


def _fixture_handoff(seam, owner):
    # Lower-level reader/host tests use explicit synthetic marker content.
    # The collector integration above obtains it from the ORIGINAL collector.
    import hashlib
    from pathlib import Path

    from adapters.mineflayer.self_world_stage_w4_logtap import W4CollectorCursor, W4CollectorMarker

    commands = seam._bridge._handoff._commands
    line = f"[19:00] [Server thread/INFO]: {commands.expected_log_suffix}"
    raw = (line + "\n").encode()
    marker = W4CollectorMarker(W4CollectorCursor(Path("/synthetic/log"), 1, 2, 0),
                               line, 0, len(raw), hashlib.sha256(raw).hexdigest(), 200)
    seam.handoff_host(owner=owner, marker=marker)


@pytest.mark.parametrize("marker", (None, "forged-console-text", object()))
def test_offline_handoff_requires_original_gate_marker(marker):
    from adapters.mineflayer.self_world_stage_w4_prehost import W4OfflineS49Owner

    pre, _, lines = _offline_lines()
    owner = object()
    seam = W4OfflineS49Owner(lines, owner=owner)

    async def run():
        await seam.start(owner=owner)
        await seam.preworld(owner=owner, request_id=pre.request_id, slot=1, token=TOKEN)
        seam.begin_staging(owner=owner)
        with pytest.raises(W4PreworldBlocked, match="collector content"):
            seam.handoff_host(owner=owner, marker=marker)
        assert seam.phase == "BLOCKED"
        assert not seam.host_deliveries
        assert len(seam.audit) == 4

    asyncio.run(run())
