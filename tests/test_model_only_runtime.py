"""Model-only ownership regressions. Fake API is not actual model evidence."""
from __future__ import annotations

import hashlib
import json
import os
import subprocess
import sys
from builtins import BaseExceptionGroup
from pathlib import Path
from types import SimpleNamespace

import pytest

from adapters.llama_cpp import model_runtime as runtime
from adapters.llama_cpp.owned_backend import OwnedBackendRejected, OwnedBackendSpec


def fixture(tmp_path, monkeypatch):
    binary = tmp_path / 'llama-server'
    binary.write_bytes(b'fake')
    binary.chmod(0o700)
    model = tmp_path / 'model.gguf'
    model.write_bytes(b'fake-model')
    spec = OwnedBackendSpec(binary, model, hashlib.sha256(b'fake').hexdigest(),
                            hashlib.sha256(b'fake-model').hexdigest(), 'alias',
                            ctx_size=8192)
    child = SimpleNamespace(pid=987654321, returncode=None)
    child.poll = lambda: child.returncode
    child.wait = lambda **kwargs: child.returncode
    monkeypatch.setattr(runtime.subprocess, 'Popen', lambda *a, **k: child)
    monkeypatch.setattr(runtime.os, 'getpgid', lambda pid: pid)
    monkeypatch.setattr(runtime, '_starttime', lambda pid: '123')
    monkeypatch.setattr(runtime, 'backend_ready', lambda *a, **k: None)
    monkeypatch.setattr(runtime, 'preflight_available_port', lambda port: None)
    monkeypatch.setattr(runtime.subprocess, 'run', lambda *a, **k: SimpleNamespace(
        stdout='version build 10874, commit abcdef123', stderr=''))
    props = {'build_info': '10874 abcdef123', 'model_alias': 'alias',
             'model_path': str(model), 'default_generation_settings': {'n_ctx': 8192},
             'total_slots': 1, 'model_ftype': 'Q4_K - Medium', 'chat_template': 'test'}
    api = {'/health': {'status': 'ok'}, '/v1/models': {'data': [{'id': 'alias'}]},
           '/props': props, '/slots': [{'id': 0, 'n_ctx': 8192}]}
    monkeypatch.setattr(runtime, '_json_get', lambda port, route, path: api[route])
    def stop(proc):
        proc.returncode = -15
        return -15
    monkeypatch.setattr(runtime, 'terminate_owned_process', stop)
    return spec, child, props


@pytest.mark.parametrize('fault', ['none', 'body', 'cancel', 'health', 'identity'])
def test_scope_reaps_owned_child_for_all_exits(tmp_path, monkeypatch, fault):
    spec, child, props = fixture(tmp_path, monkeypatch)
    if fault == 'health':
        monkeypatch.setattr(runtime, 'backend_ready', lambda *a, **k: (_ for _ in ()).throw(
            OwnedBackendRejected('health fault')))
    if fault == 'identity':
        props['model_alias'] = 'foreign'
    def execute():
        with runtime.owned_model(spec, evidence=tmp_path / 'new',
                                 confirm='PRODUCT_MODEL_DEV_ONLY') as probes:
            assert probes['identity']['requestModel'] == 'alias'
            if fault == 'body':
                raise RuntimeError('body fault')
            if fault == 'cancel':
                raise KeyboardInterrupt('cancel fault')
    if fault == 'none':
        execute()
    else:
        expected = {"body": RuntimeError, "cancel": KeyboardInterrupt,
                    "health": OwnedBackendRejected, "identity": RuntimeError}[fault]
        with pytest.raises(expected):
            execute()
    rows = [json.loads(s) for s in (tmp_path / 'new/lifecycle.jsonl').read_text().splitlines()]
    assert child.returncode == -15
    reap = next(r for r in rows if r['event'] == 'REAPED')
    assert reap['returncode'] == reap['wait_result'] == -15
    assert reap['proc_absent'] is True
    assert any(r['event'] == 'PORT_RELEASED' and r['bindable'] for r in rows)
    assert rows[-1]['event'] == 'TERMINAL'


def test_primary_and_cleanup_faults_both_survive(tmp_path, monkeypatch):
    spec, _, _ = fixture(tmp_path, monkeypatch)
    def fail(proc):
        raise OSError('secondary cleanup fault')
    monkeypatch.setattr(runtime, 'terminate_owned_process', fail)
    with pytest.raises(BaseExceptionGroup) as info:
        with runtime.owned_model(spec, evidence=tmp_path / 'new',
                                 confirm='PRODUCT_MODEL_DEV_ONLY'):
            raise RuntimeError('primary body fault')
    assert [type(e) for e in info.value.exceptions] == [RuntimeError, OSError]


def test_hash_mismatch_and_existing_evidence_never_spawn(tmp_path, monkeypatch):
    spec, child, _ = fixture(tmp_path, monkeypatch)
    spec.gguf.write_bytes(b'changed')
    with pytest.raises(ValueError):
        with runtime.owned_model(spec, evidence=tmp_path / 'new',
                                 confirm='PRODUCT_MODEL_DEV_ONLY'):
            pytest.fail('bad hash admitted')
    assert child.returncode is None
    with pytest.raises(FileExistsError):
        with runtime.owned_model(spec, evidence=tmp_path / 'new',
                                 confirm='PRODUCT_MODEL_DEV_ONLY'):
            pytest.fail('evidence reused')


def test_model_only_import_has_no_minecraft_closure():
    done = subprocess.run([sys.executable, '-c',
        'import sys; import adapters.llama_cpp.model_runtime; '
        'assert not any(n.startswith("adapters.mineflayer") for n in sys.modules)'],
        check=False, capture_output=True, text=True)
    assert done.returncode == 0, done.stderr


def test_native_process_reap_and_foreign_group_guard():
    from adapters.llama_cpp.owned_backend import terminate_owned_process
    child = subprocess.Popen([sys.executable, '-c', 'import time; time.sleep(60)'],
                             start_new_session=True)
    try:
        code = terminate_owned_process(child)
        assert code == child.wait() and code is not None
        assert not Path(f'/proc/{child.pid}').exists()
    finally:
        if child.poll() is None:
            os.killpg(child.pid, 9)
            child.wait()


def test_foreign_process_group_never_signalled(monkeypatch):
    from adapters.llama_cpp import owned_backend
    child = SimpleNamespace(pid=999, poll=lambda: None)
    monkeypatch.setattr(owned_backend.os, 'getpgid', lambda pid: 998)
    monkeypatch.setattr(owned_backend.os, 'killpg', lambda *a: pytest.fail('foreign signal'))
    with pytest.raises(OwnedBackendRejected):
        owned_backend.terminate_owned_process(child)


def test_kill_escalation_reaps_same_child(monkeypatch):
    from adapters.llama_cpp import owned_backend
    signals = []
    class Child:
        pid = 999
        def poll(self):
            return None
        def wait(self, *, timeout):
            if timeout == 12:
                raise subprocess.TimeoutExpired('owned', timeout)
            return -9
    monkeypatch.setattr(owned_backend.os, 'getpgid', lambda pid: pid)
    monkeypatch.setattr(owned_backend.os, 'killpg', lambda pid, sig: signals.append((pid, sig)))
    assert owned_backend.terminate_owned_process(Child()) == -9
    assert signals == [(999, 15), (999, 9)]


def test_busy_gpu_scope_never_starts_second_child(tmp_path, monkeypatch):
    import fcntl
    spec, child, _ = fixture(tmp_path, monkeypatch)
    lock = os.open(f'/tmp/relay-self-llama-cpp-local-gpu-{os.getuid()}.lock', os.O_RDWR)
    try:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        with pytest.raises(BlockingIOError):
            with runtime.owned_model(spec, evidence=tmp_path / 'new',
                                     confirm='PRODUCT_MODEL_DEV_ONLY'):
                pytest.fail('competing lease admitted')
        assert child.returncode is None
    finally:
        os.close(lock)


def test_port_time_wait_is_separate_from_reap(monkeypatch):
    attempts = []
    records = []
    def bind(port):
        attempts.append(port)
        if len(attempts) == 1:
            raise OwnedBackendRejected('TIME_WAIT fixture')
    monkeypatch.setattr(runtime, 'preflight_available_port', bind)
    monkeypatch.setattr(runtime.time, 'sleep', lambda duration: None)
    runtime._wait_for_port(1234, lambda event, **kw: records.append(event))
    assert attempts == [1234, 1234]
    assert records == ['PORT_BIND_PENDING', 'PORT_RELEASED']


def test_persistent_port_fault_keeps_reap_receipt(tmp_path, monkeypatch):
    spec, child, _ = fixture(tmp_path, monkeypatch)
    def fail(port, record):
        raise OwnedBackendRejected('persistent cleanup bind fault')
    monkeypatch.setattr(runtime, '_wait_for_port', fail)
    with pytest.raises(BaseExceptionGroup):
        with runtime.owned_model(spec, evidence=tmp_path / 'new',
                                 confirm='PRODUCT_MODEL_DEV_ONLY'):
            pass
    rows = [json.loads(s) for s in (tmp_path / 'new/lifecycle.jsonl').read_text().splitlines()]
    assert any(r['event'] == 'REAPED' and r['wait_result'] == -15 for r in rows)
    assert rows[-1]['cleanup_errors']
    assert child.returncode == -15
