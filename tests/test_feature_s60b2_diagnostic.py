"""Synthetic HTTP only; bodies/prompts remain ephemeral fixture memory."""
import asyncio
import json
import time
from types import SimpleNamespace

import pytest

from adapters.mineflayer.s60b1_loopback_adapter import (
    LoopbackTransportConfig,
    TransportUnconfirmed,
)
from adapters.mineflayer.s60b2_offline_diagnostic import OfflineDiagnosticTransport
from adapters.mineflayer.s60b2_owned_backend_probe import FINGERPRINT, MeasuredTransport
from relay_self.best_effort_displacement import BestEffortDisplacement
from test_feature_s60b1_adapter import CONTEXT, SOURCE, FakeHTTP, envelope, payload, response


def stock():
    value = envelope()
    value['system_fingerprint'] = FINGERPRINT
    return value


def rig(port, kind=OfflineDiagnosticTransport):
    adapter = kind(LoopbackTransportConfig('offline-model', port, read_s=.05),
                   lambda request: payload(), SimpleNamespace(start=time.monotonic()))
    owner = BestEffortDisplacement(CONTEXT, 'admission', adapter.start,
                                  adapter.cancel, lambda: 0.)
    adapter.bind(owner)
    request = owner.admit(CONTEXT, 'L2', 1, 20, 5, SOURCE)
    owner.submit(request)
    return adapter, owner, request


def cases():
    yield response(json.dumps(stock()).encode()), None
    yield response(json.dumps(stock()).encode(), chunked=True), None
    yield response(b'{private /secret/path'), 'JSON_DECODE_FAILURE'
    yield response(b'{"model":1,"model":2}'), 'JSON_DECODE_FAILURE'
    yield response(b'NaN'), 'JSON_DECODE_FAILURE'
    yield response(b'[]'), 'SCHEMA_UNCONFIRMED'
    for field in ('model', 'system_fingerprint'):
        value = stock()
        value[field] = 'private /secret/path'
        yield response(json.dumps(value).encode()), 'MODEL_OR_FINGERPRINT_MISMATCH'
    value = stock()
    value['usage'] = None
    yield response(json.dumps(value).encode()), 'USAGE_ENVELOPE_UNCONFIRMED'
    for field, content in [('content', ''), ('content', []), ('tool_calls', [])]:
        value = stock()
        value['choices'][0]['message'][field] = content
        yield response(json.dumps(value).encode()), 'SCHEMA_UNCONFIRMED'
    value = stock()
    value['usage']['total_tokens'] = 99
    yield response(json.dumps(value).encode()), 'SCHEMA_UNCONFIRMED'
    yield response(status=500), 'HTTP_READ_OR_FRAMING_UNCONFIRMED'
    yield b'HTTP/1.1 200 OK\r\n', 'HTTP_READ_OR_FRAMING_UNCONFIRMED'
    yield response()[:-2], 'HTTP_READ_OR_FRAMING_UNCONFIRMED'
    yield None, 'HTTP_READ_OR_FRAMING_UNCONFIRMED'


@pytest.mark.parametrize('wire,stage', list(cases()), ids=lambda _: 'synthetic')
def test_exact_transport_negative_controls_and_frozen_equivalence(wire, stage):
    async def run(kind):
        async with FakeHTTP() as server:
            server.responses = [wire]
            adapter, owner, request = rig(server.port, kind)
            await server.next_post()
            server.release[0].set()
            attempt = adapter._attempt
            await asyncio.wait_for(attempt.task, 2)
            await asyncio.sleep(0)
            if stage:
                assert isinstance(attempt.future.exception(), TransportUnconfirmed)
                assert owner.active is request  # failure never releases lease
                assert adapter.completions == 0
            else:
                assert attempt.future.result() == 'transient-output'
                assert adapter.completions == 1
            if kind is OfflineDiagnosticTransport:
                receipts = adapter.diagnostics
                assert [r.stage for r in receipts] == ([stage] if stage else [])
                assert all(r.generation == request.generation and
                           0 <= r.elapsed_ms <= 86_400_000 for r in receipts)
                assert not any(s in repr(receipts) for s in
                               ('private', '/secret', 'transient-output', 'offline-model'))
            result = adapter.receipts
            await adapter.aclose()
            return result
    assert asyncio.run(run(OfflineDiagnosticTransport)) == asyncio.run(run(MeasuredTransport))


@pytest.mark.parametrize('future_cancel', [False, True])
def test_cancel_and_foreign_provenance_and_bounded_unknown(future_cancel):
    async def run():
        async with FakeHTTP() as server:
            server.responses = [None]
            adapter, owner, request = rig(server.port)
            await server.next_post()
            attempt = adapter._attempt
            adapter._observe('private', object(), task_required=False)
            adapter._validate_response(json.dumps(stock()).encode(), 32)
            assert not adapter.diagnostics
            for _ in range(100):
                adapter._observe('private /secret', attempt, task_required=False)
            assert len(adapter.diagnostics) == 64
            assert all(r.stage == 'TRANSPORT_STAGE_UNKNOWN' for r in adapter.diagnostics)
            if future_cancel:
                attempt.future.cancel()
                await asyncio.sleep(0)
            else:
                adapter.cancel(request)
            await asyncio.gather(attempt.task, return_exceptions=True)
            assert adapter.diagnostics[-1].stage == 'CLIENT_CANCEL_OR_UNKNOWN'
            assert owner.active is request and adapter.completions == 0
            await adapter.aclose()
    asyncio.run(run())


def test_pre_response_refusal_is_unknown():
    async def run():
        server = await asyncio.start_server(lambda r, w: w.close(), '127.0.0.1', 0)
        port = server.sockets[0].getsockname()[1]
        server.close()
        await server.wait_closed()
        adapter, owner, request = rig(port)
        await adapter._attempt.task
        assert [r.stage for r in adapter.diagnostics] == ['TRANSPORT_PRE_RESPONSE_UNKNOWN']
        assert owner.active is request and adapter.posts == adapter.completions == 0
        await adapter.aclose()
    asyncio.run(run())
