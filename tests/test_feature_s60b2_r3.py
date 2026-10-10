"""R3 real measure path, synthetic stock HTTP only; never launch a model."""
import asyncio
import json
import threading
from dataclasses import replace
from types import SimpleNamespace

import pytest

from adapters.mineflayer import s60b2_owned_backend_probe as probe
from adapters.mineflayer.s60b2_offline_diagnostic import STAGES, DiagnosticReceipt
from adapters.mineflayer.s60b2_r3_diagnostic import R3DiagnosticTransport
from test_feature_s60b2_diagnostic import cases, rig
from test_feature_s60b2_preflight import FakeStock, config, stock_slot


class StockWire(FakeStock):
    """Keep backend progress independent of client failure and EOF."""
    def __init__(self, cfg, wire):
        super().__init__(cfg)
        self.wire = wire

    async def handle(self, reader, writer):
        self.tasks.add(asyncio.current_task())
        self.writers.add(writer)
        try:
            head = await reader.readuntil(b'\r\n\r\n')
            if head.startswith(b'POST '):
                length = next(int(x.split(b':')[1]) for x in head.split(b'\r\n')
                              if x.startswith(b'Content-Length:'))
                await reader.readexactly(length)
                self.posts.append(head)
                self.busy = True
                self.release.append(asyncio.Event())
                await self.release[-1].wait()
                self.busy = False
                if self.wire is None:
                    await reader.read()  # no response: caller timeout/cancellation
                    self.disconnected.set()
                else:
                    writer.write(self.wire)
                    await writer.drain()
            else:
                from test_feature_s60b1_adapter import response
                assert head.startswith(b'GET /slots ')
                body = json.dumps([stock_slot(self.cfg, self.busy, len(self.posts))]).encode()
                writer.write(response(body))
                await writer.drain()
        except (ConnectionError, asyncio.IncompleteReadError):
            pass
        finally:
            writer.close()
            self.writers.discard(writer)
            self.tasks.discard(asyncio.current_task())


@pytest.mark.parametrize('wire,stage', [*cases(), (None, 'timeout')],
                         ids=lambda _: 'synthetic')
def test_measure_diagnostic_and_baseline_equivalence(tmp_path, monkeypatch, wire, stage):
    async def scenario(kind, root):
        async with StockWire(config(tmp_path), wire) as server:
            journal = probe.Journal(root)
            original = journal.emit
            foreground = threading.get_ident()
            loop = asyncio.get_running_loop()
            measure_task = None
            def emit(phase, **facts):
                assert threading.get_ident() != foreground
                original(phase, **facts)
                if phase == 'L0_CALLBACK_RETURN' or (
                    phase == 'NEW_INFERENCE_STARTED' and facts['generation'] > 1):
                    loop.call_soon_threadsafe(server.release[-1].set)
                    if wire is None and stage != 'timeout':
                        loop.call_soon_threadsafe(measure_task.cancel)
            monkeypatch.setattr(journal, 'emit', emit)
            checks = []
            witness = SimpleNamespace(verify=lambda: checks.append(server.busy))
            kwargs = {} if kind is None else dict(diagnostic_adapter=kind)
            measure_task = asyncio.create_task(probe.measure(server.cfg, witness, journal, **kwargs))
            try:
                result = await asyncio.wait_for(measure_task, .75 if stage == 'timeout' else 5)
                terminal = 'success'
            except (probe.ProbeRejected, asyncio.CancelledError, TimeoutError) as exc:
                result = None
                terminal = type(exc).__name__
            journal.close()
            rows = [json.loads(x) for x in (root / 'events.jsonl').read_text().splitlines()]
            diagnostics = [r for r in rows if r['phase'].startswith('DIAG_')]
            if kind:
                expected = 'CLIENT_CANCEL_OR_UNKNOWN' if wire is None else stage
                assert [r['phase'] for r in diagnostics] == (
                    ['DIAG_' + expected] * (2 if wire is None else 1) if expected else [])
                for row in diagnostics:
                    assert set(row) == {'phase', 'generation', 'monotonic_elapsed_s',
                                        'observed_elapsed_s'}
                    assert row['generation'] == 1
                    assert 0 <= row['observed_elapsed_s'] <= row['monotonic_elapsed_s']
            else:
                assert not diagnostics
            assert not any(s in json.dumps(rows) for s in
                           ('private', '/secret', 'transient-output', 'offline-model'))
            phases = [r['phase'] for r in rows if not r['phase'].startswith('DIAG_')]
            assert 'L0_CALLBACK_ENTER' in phases and 'L0_CALLBACK_RETURN' in phases
            assert len(server.posts) == (1 if stage else 2)
            assert journal.accounting['complete_responses'] == (0 if stage else 2)
            assert checks and journal.file.closed
            # Socket completion can cross a sampling boundary during durable I/O.
            # Compare acceptance/accounting semantics, not identical scheduling.
            sampling = {'BACKEND_BUSY_OBSERVED', 'SAME_PROCESS_SLOT_IDLE_OBSERVED'}
            samples = journal.accounting['slot_samples']
            assert 1 <= sum(p in sampling for p in phases) <= samples <= 120
            assert checks[0] is False and any(checks)
            assert 2 <= len(checks) <= 2 * samples
            if result is not None:
                assert result['slot_samples'] == samples
            semantic_result = None if result is None else {
                k: v for k, v in result.items() if k != 'slot_samples'}
            semantic_accounting = {k: v for k, v in journal.accounting.items()
                                   if k != 'slot_samples'}
            summary = (terminal, semantic_result, [p for p in phases if p not in sampling],
                       semantic_accounting)
        assert not server.tasks and not server.writers
        return summary
    baseline = asyncio.run(scenario(None, tmp_path / 'baseline'))
    observed = asyncio.run(scenario(R3DiagnosticTransport, tmp_path / 'diagnostic'))
    assert observed == baseline


@pytest.mark.parametrize('arm', ['B', 'C'])
def test_cross_arm_rejected_before_any_work(tmp_path, arm):
    async def scenario():
        with pytest.raises(probe.ProbeRejected, match='offline Arm A'):
            await probe.measure(config(tmp_path, arm), None, None,
                                diagnostic_adapter=R3DiagnosticTransport)
    asyncio.run(scenario())


def test_arbitrary_injection_rejected(tmp_path):
    with pytest.raises(probe.ProbeRejected):
        asyncio.run(probe.measure(config(tmp_path), None, None,
                                  diagnostic_adapter=probe.MeasuredTransport))


def test_one_time_drain_bounds_redaction_and_malformed_receipts(tmp_path):
    async def scenario():
        from test_feature_s60b1_adapter import FakeHTTP
        async with FakeHTTP() as server:
            server.responses = [None]
            adapter, owner, request = rig(server.port, R3DiagnosticTransport)
            journal = probe.Journal(tmp_path / 'receipt')
            adapter._config = replace(adapter.config, read_s=10)
            adapter.journal = journal
            adapter._diagnostic_start = journal.start
            await server.next_post()
            for _ in range(64):
                adapter._observe('private /secret', adapter._attempt, task_required=False)
            assert len(adapter.diagnostics) == 64
            await adapter.drain()
            count = journal.count
            await adapter.drain()
            assert journal.count == count
            adapter._observe('private', object(), task_required=False)
            assert not adapter.diagnostics
            adapter._observe('private', adapter._attempt, task_required=False)
            with pytest.raises(probe.ProbeRejected, match='buffer exhausted'):
                await adapter.drain()
            assert adapter._diagnostic_overflow and not adapter.diagnostics
            adapter._diagnostic_overflow = False  # fixture-only malformed input gate
            adapter._diagnostics.append(DiagnosticReceipt('private /secret', 1, 0))
            with pytest.raises(probe.ProbeRejected, match='receipt unconfirmed'):
                await adapter.drain()
            assert len(adapter.diagnostics) == 1  # never silently discarded
            assert owner.active is request and adapter.completions == 0
            await adapter.aclose()
            journal.close()
            rows = [json.loads(x) for x in (journal.root / 'events.jsonl').read_text().splitlines()]
            assert all(r['phase'][5:] in STAGES for r in rows if r['phase'].startswith('DIAG_'))
    asyncio.run(scenario())


def test_r3_direct_read_timeout_and_pre_response_refusal():
    async def scenario():
        from test_feature_s60b1_adapter import FakeHTTP
        async with FakeHTTP() as server:
            server.responses = [None]
            adapter, owner, request = rig(server.port, R3DiagnosticTransport)
            await server.next_post()
            server.release[0].set()
            await adapter._attempt.task
            assert adapter.diagnostics[0].stage == 'HTTP_READ_OR_FRAMING_UNCONFIRMED'
            assert owner.active is request and adapter.completions == 0
            await adapter.aclose()
        adapter, owner, request = rig(server.port, R3DiagnosticTransport)
        await adapter._attempt.task
        assert adapter.diagnostics[0].stage == 'TRANSPORT_PRE_RESPONSE_UNKNOWN'
        assert owner.active is request and adapter.posts == adapter.completions == 0
        await adapter.aclose()
    asyncio.run(scenario())


def test_live_api_keeps_adapter_injection_private():
    import inspect
    assert 'diagnostic_adapter' not in inspect.signature(probe.run).parameters
    assert 'diagnostic_arm_a' in inspect.signature(probe.run).parameters
    assert 'diagnostic_grant_bytes' in inspect.signature(probe.run).parameters


def test_frozen_manifest_and_predecessor_separation():
    import hashlib
    from pathlib import Path
    root = Path(__file__).resolve().parents[1]
    assert hashlib.sha256((root / 'docs/s60b2-r3/manifest.md').read_bytes()).hexdigest() == (
        '2710acc4809ebc3a2bc8f55d250396de091cbd44061637b5f38de4a241cbaa4a')
    assert probe.git(root, 'rev-parse', 'e0fad49:docs/s60b2-r3/manifest.md') == (
        'bf1a267a9ec0c8600ba186f035168de6b46d8964')
    for file in ('s60b2_offline_diagnostic.py', 's60b1_loopback_adapter.py'):
        path = 'adapters/mineflayer/' + file
        assert probe.git(root, 'show', '66afcc2:' + path) == (root / path).read_text().strip()


def test_cancelled_diagnostic_fsync_is_not_replayed(tmp_path, monkeypatch):
    async def scenario():
        from test_feature_s60b1_adapter import FakeHTTP
        async with FakeHTTP() as server:
            server.responses = [None]
            journal = probe.Journal(tmp_path / 'receipt')
            adapter, _, _ = rig(server.port, R3DiagnosticTransport)
            adapter._config = replace(adapter.config, read_s=10)
            adapter.journal = journal
            adapter._diagnostic_start = journal.start
            await server.next_post()
            adapter._observe('SCHEMA_UNCONFIRMED', adapter._attempt, task_required=False)
            entered = asyncio.Event()
            release = threading.Event()
            loop = asyncio.get_running_loop()
            original = journal.emit
            def emit(phase, **facts):
                if phase.startswith('DIAG_'):
                    loop.call_soon_threadsafe(entered.set)
                    assert release.wait(2)
                original(phase, **facts)
            monkeypatch.setattr(journal, 'emit', emit)
            task = asyncio.create_task(adapter.drain())
            await asyncio.wait_for(entered.wait(), 2)
            task.cancel()
            release.set()
            with pytest.raises(asyncio.CancelledError):
                await task
            assert not adapter.diagnostics
            count = journal.count
            await adapter.drain()
            assert journal.count == count
            await adapter.aclose()
            await adapter.drain()
            journal.close()
            rows = [json.loads(x) for x in (journal.root / 'events.jsonl').read_text().splitlines()]
            assert sum(r['phase'] == 'DIAG_SCHEMA_UNCONFIRMED' for r in rows) == 1
    asyncio.run(scenario())


def test_buffer_overflow_preserves_first_64_and_write_failure_preserves_receipt(tmp_path, monkeypatch):
    async def scenario():
        from test_feature_s60b1_adapter import FakeHTTP
        async with FakeHTTP() as server:
            server.responses = [None]
            journal = probe.Journal(tmp_path / 'receipt')
            adapter, _, _ = rig(server.port, R3DiagnosticTransport)
            adapter._config = replace(adapter.config, read_s=10)
            adapter.journal = journal
            adapter._diagnostic_start = journal.start
            await server.next_post()
            for _ in range(64):
                adapter._observe('SCHEMA_UNCONFIRMED', adapter._attempt, task_required=False)
            first = adapter.diagnostics
            adapter._observe('JSON_DECODE_FAILURE', adapter._attempt, task_required=False)
            assert adapter.diagnostics == first and adapter._diagnostic_overflow
            with pytest.raises(probe.ProbeRejected, match='buffer exhausted'):
                await adapter.drain()
            assert adapter.diagnostics == first
            adapter._diagnostic_overflow = False  # isolate durable failure gate
            await probe.MeasuredTransport.drain(adapter)
            def fail(*args, **kwargs):
                raise OSError('private /secret')
            monkeypatch.setattr(journal, 'emit', fail)
            with pytest.raises(OSError):
                await adapter.drain()
            assert adapter.diagnostics == first
            await adapter.aclose()
            journal.close()
    asyncio.run(scenario())
