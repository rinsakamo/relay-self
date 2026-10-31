"""Integration gates on retained owners; only Python inert or synthetic children."""
from __future__ import annotations

import asyncio
import json
import os
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

from adapters.mineflayer import s31a_real_server_ci as s31a
from adapters.mineflayer import s34_native_world_cognition_ci as s34
from adapters.mineflayer import s49_normal_session_real_ci as s49
from adapters.mineflayer.process_session import MineflayerProcessSession
from test_w4_pr634_startup_ownership import FakeProcess


def _emit(tmp_path, name, record):
    line = json.dumps(record, sort_keys=True)
    (tmp_path / (name + '.json')).write_text(line + '\n')
    evidence = os.environ.get('W4_PR634_LIFECYCLE_ROOT')
    if evidence:
        (Path(evidence) / (name + '.json')).write_text(line + '\n')
    print('INERT_OS_LIFECYCLE=' + line)


@pytest.mark.parametrize('fault', ['cancel', 'exception'])
def test_retained_s34_native_spawn_failure_reaps_before_transfer(monkeypatch, tmp_path, fault):
    async def run():
        process = await asyncio.create_subprocess_exec(
            sys.executable, '-u', '-c', 'import time; time.sleep(30)',
            stdin=asyncio.subprocess.PIPE, stdout=asyncio.subprocess.PIPE,
        )
        proc = Path(f'/proc/{process.pid}')
        identity = (proc / 'stat').read_text().split()[21]
        session = MineflayerProcessSession(process, raw_capture_root=tmp_path)
        entered = asyncio.Event()
        async def launch(cls, *args, **kwargs):
            return session
        async def native_spawn(existing):
            assert existing is session
            entered.set()
            if fault == 'exception':
                raise RuntimeError('inert native spawn failure')
            await asyncio.Event().wait()
        monkeypatch.setattr(s34.MineflayerProcessSession, 'launch', classmethod(launch))
        monkeypatch.setattr(s34, '_await_spawn', native_spawn)
        owner = asyncio.create_task(s34._new_session(raw_capture_root=tmp_path))
        baseline = set(asyncio.all_tasks())
        record = {'case': 'retained-s34-' + fault, 'pid': process.pid,
                  'starttime': identity, 'argv': [sys.executable, '-u', '-c',
                                               'import time; time.sleep(30)']}
        try:
            await asyncio.wait_for(entered.wait(), 2)
            if fault == 'cancel':
                owner.cancel()
                with pytest.raises(asyncio.CancelledError):
                    await owner
            else:
                with pytest.raises(RuntimeError, match='inert native spawn failure'):
                    await owner
            record.update(owner_done=owner.done(),
                          owner_returncode=process.returncode,
                          pid_present_after_owner=proc.exists(),
                          receipt_present_after_owner=(tmp_path / 'w3-node-stdout-receipt.json').exists())
        finally:
            # Harness rescue is explicitly separate from the production owner result.
            record['harness_rescue_needed'] = process.returncode is None
            record['harness_signal'] = 'SIGTERM' if process.returncode is None else None
            record['harness_abort_result'] = await session.abort_startup()
            record['wait_result'] = await process.wait()
            record['returncode_after_rescue'] = process.returncode
            record['pid_present_after_rescue'] = proc.exists()
            record['pending_new_tasks_after_rescue'] = [
                t.get_name() for t in asyncio.all_tasks() - baseline if not t.done()
            ]
            record['receipt_after_rescue'] = json.loads(
                (tmp_path / 'w3-node-stdout-receipt.json').read_text())['status']
            _emit(tmp_path, record['case'], record)
        assert not record['pid_present_after_rescue']
        assert not record['pending_new_tasks_after_rescue']
        assert record['owner_returncode'] is not None, 'retained S34 lost live child before handoff'
        assert not record['pid_present_after_owner']
        assert record['receipt_present_after_owner']
    asyncio.run(run())


@pytest.mark.parametrize('fault', ['cancel', 'secondary_exception'])
def test_retained_s49_node_cleanup_fault_still_closes_java(monkeypatch, tmp_path, fault):
    async def run():
        java = FakeProcess()
        java_closed = False
        async def ready(*args):
            return java, None, asyncio.Event()
        async def shutdown_server(*args):
            nonlocal java_closed
            java_closed = True
            java.terminate()
            await java.wait()
        class Session:
            started = SimpleNamespace(session_id='inert-fixture')
            async def shutdown(self, **kwargs):
                if fault == 'cancel':
                    raise asyncio.CancelledError('injected Node close cancellation')
                raise RuntimeError('injected Node close failure')
            async def terminate(self):
                raise RuntimeError('injected secondary cleanup failure')
        async def new_session():
            return Session()
        def stop_before_cognition():
            raise RuntimeError('stop fixture before Action/S10')
        monkeypatch.setenv('S49_REAL_SERVER_CI', '1')
        monkeypatch.delenv('NODE_OPTIONS', raising=False)
        monkeypatch.setattr(s49, '_fetch_official_server', lambda *args: {})
        monkeypatch.setattr(s49, '_write_config', lambda *args: None)
        monkeypatch.setattr(s49, '_ready_server', ready)
        monkeypatch.setattr(s49, '_new_session', new_session)
        monkeypatch.setattr(s49, '_shutdown_server', shutdown_server)
        monkeypatch.setattr(s49.s19, '_epoch_one', stop_before_cognition)
        try:
            if fault == 'cancel':
                with pytest.raises(asyncio.CancelledError, match='Node close cancellation'):
                    await s49.qualify(tmp_path / 'report.json', tmp_path / 'java.log')
            else:
                # qualify() handles ordinary faults by publishing FAIL and rc=1;
                # only cancellation must be re-raised after all cleanup.
                assert await s49.qualify(tmp_path / 'report.json', tmp_path / 'java.log') == 1
            report = json.loads((tmp_path / 'report.json').read_text())
            assert report['status'] == 'FAIL'
            assert report['server_exit'] == -15
            assert 'node_cleanup_error' in report
            assert report['actual_native_actions'] == []
            owner_closed = java_closed
        finally:
            await shutdown_server(java, None)
        assert owner_closed, 'retained S49 skipped Java cleanup after Node cleanup fault'
    asyncio.run(run())


def test_java_default_collector_failure_stops_before_ready(monkeypatch, tmp_path):
    async def run():
        process = FakeProcess()
        class BrokenStdout:
            async def readline(self):
                raise OSError('inert Java collector read fault')
        process.stdout = BrokenStdout()
        async def spawn(*args, **kwargs):
            return process
        monkeypatch.setattr(asyncio, 'create_subprocess_exec', spawn)
        owner = asyncio.create_task(s31a._ready_server(tmp_path, tmp_path / 'unused', tmp_path / 'java.log'))
        done, _ = await asyncio.wait({owner}, timeout=0.1)
        stopped_on_fault = bool(done)
        if not done:
            owner.cancel()
        try:
            await owner
        except (OSError, asyncio.CancelledError):
            pass
        assert process.reaped == 1
        assert stopped_on_fault, 'default Java collector fault waited for readiness timeout'
    asyncio.run(run())
