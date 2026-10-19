"""W4-PREPROBE offline owner callback contract: never starts actual World."""
from __future__ import annotations

import asyncio
import json
from dataclasses import asdict, replace

import pytest

from adapters.mineflayer.self_world_stage_w4_preprobe import (
    W4OwnerPreworldProbePort,
)
from adapters.mineflayer.self_world_stage_w4_preflight import W4PreworldBlocked
from test_self_world_stage_w4_window import TOKEN, _sample


def _sample_port(*, fake=None, minimum_seq=0):
    pre, _after, _commands, _kwargs, _closed = _sample()
    received = []
    owner = object()

    async def original_owner_reader(req: str):
        received.append(req)
        await asyncio.sleep(0)
        return pre if fake is None else fake(pre, req)

    port = W4OwnerPreworldProbePort(
        session_id=pre.session_id, owner=owner,
        native_probe=original_owner_reader, minimum_seq=minimum_seq,
    )
    return pre, owner, port, received


def _capture(port, owner, pre, **kwargs):
    return port.capture_pre_world(
        owner=owner, request_id=pre.request_id, slot=1, token=TOKEN, **kwargs,
    )


def test_one_owner_one_preplacement_probe_to_existing_w4_owner_gate():
    pre, owner, port, records = _sample_port()

    async def run():
        r = await _capture(port, owner, pre)
        assert port.phase == "PREWORLD_SOURCE_CAPTURED"
        assert port.handoff.phase == "AWAIT_MARKER"
        assert r.observation_seq == pre.seq
        assert r.observation_source == pre.provenance.reference
        assert r.candidate_commands.source_reference == pre.provenance.reference
        assert r.candidate_commands.slot == 1
        return r

    result = asyncio.run(run())
    assert records == [pre.request_id]
    assert not result.owner_attested
    assert not result.reader_exclusivity_attested
    assert not result.host_loop_not_started_attested
    assert not result.stage_world_not_started_attested
    assert not result.physical_run_permitted
    assert not result.s10_permission
    json.loads(json.dumps(asdict(result), allow_nan=False))


@pytest.mark.parametrize("bad", (
    "foreign_owner", "host_loop", "stage_started", "non_bool_host",
    "non_bool_stage", "stale_cursor", "wrong_request", "wrong_session",
    "wrong_seq", "post_event", "missing_orientation", "same_token_second",
))
def test_owner_port_rejects_bad_source_or_order(bad):
    def wrong(pre, _req):
        if bad == "wrong_request":
            return replace(pre, request_id="foreign")
        if bad == "wrong_session":
            return replace(pre, session_id="foreign")
        if bad == "wrong_seq":
            return replace(pre, seq=0)
        if bad == "post_event":
            return replace(pre, kind="entities", request_id=None)
        if bad == "missing_orientation":
            from dataclasses import fields

            from adapters.mineflayer.python_protocol import MineflayerSnapshot

            return replace(pre, snapshot=MineflayerSnapshot(**{
                f.name: getattr(pre.snapshot, f.name)
                for f in fields(MineflayerSnapshot)
            }))
        return pre

    pre, owner, port, received = _sample_port(
        fake=wrong, minimum_seq=2 if bad in ("stale_cursor", "wrong_seq") else 0,
    )
    overrides = {}
    if bad == "foreign_owner":
        overrides["owner"] = object()
    if bad == "host_loop":
        overrides["host_loop_started"] = True
    if bad == "stage_started":
        overrides["stage_world_started"] = True
    if bad == "non_bool_host":
        overrides["host_loop_started"] = 0
    if bad == "non_bool_stage":
        overrides["stage_world_started"] = 0

    async def run():
        if bad == "same_token_second":
            await _capture(port, owner, pre)
        with pytest.raises(W4PreworldBlocked):
            kw = dict(owner=owner, request_id=pre.request_id, slot=1, token=TOKEN)
            kw.update(overrides)
            await port.capture_pre_world(**kw)

    asyncio.run(run())
    assert port.phase == "BLOCKED"
    assert port.handoff.phase == "BLOCKED"
    assert len(received) <= 1


def test_two_tasks_cannot_enter_while_original_owner_probe_awaits():
    pre, owner, port, events = _sample_port()
    first_sent = asyncio.Event()
    release = asyncio.Event()
    calls = []

    async def read(req):
        calls.append(req)
        first_sent.set()
        await release.wait()
        return pre

    port = W4OwnerPreworldProbePort(
        session_id=pre.session_id, owner=owner, native_probe=read,
    )

    async def run():
        first = asyncio.create_task(_capture(port, owner, pre))
        await first_sent.wait()
        with pytest.raises(W4PreworldBlocked):
            await _capture(port, owner, pre)
        release.set()
        with pytest.raises(W4PreworldBlocked):
            await first

    asyncio.run(run())
    assert calls == [pre.request_id]
    assert port.phase == "BLOCKED"


def test_cancelled_original_owner_probe_blocks_future_reentry():
    pre, owner, _old, _ = _sample_port()
    entered = asyncio.Event()

    async def never_return(_req):
        entered.set()
        await asyncio.Future()

    port = W4OwnerPreworldProbePort(
        session_id=pre.session_id, owner=owner, native_probe=never_return,
    )

    async def run():
        task = asyncio.create_task(_capture(port, owner, pre))
        await entered.wait()
        task.cancel()
        with pytest.raises(asyncio.CancelledError):
            await task
        assert port.phase == "BLOCKED"
        with pytest.raises(W4PreworldBlocked):
            await _capture(port, owner, pre)

    asyncio.run(run())


def test_foreign_caller_cannot_close_other_owner_lease():
    pre, owner, port, _ = _sample_port()
    with pytest.raises(W4PreworldBlocked):
        port.abandon(owner=object())
    assert port.phase == "BLOCKED"
