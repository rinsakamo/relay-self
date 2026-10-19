"""W4-PREHOST original-session stream accounting; synthetic only."""
from __future__ import annotations

import asyncio
from collections import deque
from dataclasses import replace

import pytest

from adapters.mineflayer.self_world_stage_w4_prehost import W4PrehostOwnerBridge
from adapters.mineflayer.self_world_stage_w4_preflight import W4PreworldBlocked
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


def _capture(bridge, owner, pre, **overrides):
    kwargs = dict(
        owner=owner, request_id=pre.request_id, slot=1, token=TOKEN,
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
        zombie = pre.snapshot.nearby_entities
        if not zombie:
            _other, closed = __import__(
                "test_self_world_stage_w4", fromlist=["_oriented_closed"]
            )._oriented_closed()
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
    pre, owner, source, bridge = _build([pre])

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
