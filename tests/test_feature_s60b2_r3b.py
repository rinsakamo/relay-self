"""R3-B0 grant and owned runner: synthetic HTTP/process only, never inference."""
import asyncio
import hashlib
import json
from pathlib import Path
from types import SimpleNamespace

import pytest

from adapters.mineflayer import s60b2_owned_backend_probe as probe
from test_feature_s60b2_diagnostic import cases
from test_feature_s60b2_preflight import approval, config, encoded, proc_fixture
from test_feature_s60b2_r3 import StockWire


@pytest.fixture
def admission(monkeypatch):
    for key in ('CI', 'GITHUB_ACTIONS', 'GITLAB_CI'):
        monkeypatch.delenv(key, raising=False)
    original = probe.digest
    monkeypatch.setattr(probe, 'git', lambda root, *args:
                        'a' * 40 if args[0] == 'rev-parse' else '')
    monkeypatch.setattr(probe, 'digest', lambda p:
                        probe.MANIFEST if p.name == 'manifest.md' and p.parent.name == 's60b2'
                        else original(p))


def grants(cfg, root):
    data = encoded(cfg)
    base = json.dumps(approval(data, root) | {'arm': cfg.arm}).encode()
    grant = dict(runner_head='a' * 40, manifest_sha256=probe.R3B_MANIFEST,
                 base_manifest_sha256=probe.MANIFEST,
                 config_sha256=hashlib.sha256(data).hexdigest(),
                 approval_sha256=hashlib.sha256(base).hexdigest(), arm='A',
                 diagnostic_arm_a=True, operator_token='b' * 64,
                 allow_model_gpu_launch=True, source_binary_mapping_reviewed=True,
                 runtime_shared_libraries_reviewed=True, prior_cleanup_confirmed=True,
                 evidence_root=str(root.resolve()))
    return data, base, grant


@pytest.mark.parametrize('entry', ['api', 'cli'])
@pytest.mark.parametrize('field,value', [
    ('runner_head', '82988fb889079ae8e420d76f4436fa9ff2b88397'),
    ('manifest_sha256', probe.MANIFEST), ('base_manifest_sha256', '0' * 64),
    ('config_sha256', '0' * 64), ('approval_sha256', '0' * 64), ('arm', 'B'),
    ('diagnostic_arm_a', 1), ('operator_token', 'c' * 64), ('operator_token', 'bad'),
    ('allow_model_gpu_launch', False), ('source_binary_mapping_reviewed', False),
    ('runtime_shared_libraries_reviewed', False), ('prior_cleanup_confirmed', False),
    ('evidence_root', '/private/other'), ('extra', '/secret'),
])
def test_diagnostic_grant_refused_before_reservation(tmp_path, admission, monkeypatch,
                                                    capsys, entry, field, value):
    root = tmp_path / 'receipt'
    data, base, grant = grants(config(tmp_path), root)
    grant[field] = value
    def forbidden(*args, **kw):
        pytest.fail('rejected grant reached reservation or launch')
    monkeypatch.setattr(probe, 'Journal', forbidden)
    monkeypatch.setattr(probe.asyncio, 'create_subprocess_exec', forbidden)
    raw = json.dumps(grant).encode()
    if entry == 'api':
        with pytest.raises(probe.ProbeRejected):
            asyncio.run(probe.run(data, base, root, diagnostic_arm_a=True,
                                 diagnostic_grant_bytes=raw))
    else:
        assert invoke(tmp_path, data, base, root, raw) == 2
        assert '/secret' not in capsys.readouterr().out
    assert not root.exists()


def invoke(tmp_path, data, base, root, raw):
    for name, body in [('config', data), ('approval', base), ('grant', raw)]:
        (tmp_path / name).write_bytes(body)
    return probe.main(['--run', '--diagnostic-arm-a', '--config', str(tmp_path / 'config'),
                       '--approval', str(tmp_path / 'approval'), '--evidence', str(root),
                       '--diagnostic-grant', str(tmp_path / 'grant')])


@pytest.mark.parametrize('raw', [None, b'{}', b'[]', b'\xff', b'x' * 8193,
                                b'{"arm":"A","arm":"A"}'])
def test_missing_old_or_malformed_grants(tmp_path, admission, raw):
    root = tmp_path / 'receipt'
    data, base, _ = grants(config(tmp_path), root)
    for grant in (raw, base):
        with pytest.raises(probe.ProbeRejected):
            asyncio.run(probe.run(data, base, root, diagnostic_arm_a=True,
                                 diagnostic_grant_bytes=grant))
    assert not root.exists()


@pytest.mark.parametrize('arm', ['B', 'C'])
def test_b_c_diagnostic_api_and_cli_refused(tmp_path, admission, arm):
    root = tmp_path / 'receipt'
    data, base, grant = grants(config(tmp_path, arm), root)
    raw = json.dumps(grant).encode()
    with pytest.raises(probe.ProbeRejected):
        asyncio.run(probe.run(data, base, root, diagnostic_arm_a=True,
                             diagnostic_grant_bytes=raw))
    assert invoke(tmp_path, data, base, root, raw) == 2
    assert not root.exists()


@pytest.mark.parametrize('argv', [['--diagnostic-arm-a'], ['--plan', '--diagnostic-arm-a'],
                                 ['--run', '--diagnostic-arm-a'],
                                 ['--diagnostic-grant', '/secret'],
                                 ['--run', '--diagnostic-grant', '/secret']])
def test_invalid_cli_mode_performs_no_work(monkeypatch, argv):
    def forbidden(*a, **kw):
        pytest.fail('invalid mode performed external work')
    monkeypatch.setattr(probe, 'bounded_read', forbidden)
    monkeypatch.setattr(probe, 'git', forbidden)
    assert probe.main(argv) == 2


@pytest.mark.parametrize('mutation', ['dirty', 'manifest', 'used_root', 'external',
                                     'CI', 'GITHUB_ACTIONS', 'GITLAB_CI', 'old_base',
                                     'config_bytes', 'approval_bytes', 'implicit', 'nonbool'])
def test_admission_fail_closed(tmp_path, admission, monkeypatch, mutation):
    root = tmp_path / 'receipt'
    data, base, grant = grants(config(tmp_path), root)
    mode = True
    if mutation == 'dirty':
        monkeypatch.setattr(probe, 'git', lambda root, *a:
                            'a' * 40 if a[0] == 'rev-parse' else ' M file')
    elif mutation == 'manifest':
        monkeypatch.setattr(probe, 'digest', lambda p: probe.MANIFEST)
    elif mutation == 'used_root':
        root.mkdir()
    elif mutation == 'external':
        root = probe.ROOT / 'unused-private-root'
        data, base, grant = grants(config(tmp_path), root)
    elif mutation in ('CI', 'GITHUB_ACTIONS', 'GITLAB_CI'):
        monkeypatch.setenv(mutation, 'false')  # any nonempty value refuses
    elif mutation == 'old_base':
        old = json.loads(base)
        old['runner_head'] = '66afcc2017d12b760e21539bf698baf176d3dd68'
        base = json.dumps(old).encode()
        grant['approval_sha256'] = hashlib.sha256(base).hexdigest()
    elif mutation == 'config_bytes':
        data += b' '
        fresh = json.loads(base)
        fresh['config_sha256'] = hashlib.sha256(data).hexdigest()
        base = json.dumps(fresh).encode()
        grant['approval_sha256'] = hashlib.sha256(base).hexdigest()
    elif mutation == 'approval_bytes':
        base += b' '
    elif mutation == 'implicit':
        mode = False
    else:
        mode = 1
    with pytest.raises(probe.ProbeRejected):
        asyncio.run(probe.run(data, base, root, diagnostic_arm_a=mode,
                             diagnostic_grant_bytes=json.dumps(grant).encode()))


@pytest.mark.parametrize('entry', ['api', 'cli'])
@pytest.mark.parametrize('wire,stage', [*cases(), (None, 'timeout')], ids=lambda _: 'synthetic')
def test_owned_run_real_measure_with_diagnostics(tmp_path, admission, monkeypatch,
                                               entry, wire, stage):
    async def scenario():
        cfg, proc, witness = proc_fixture(tmp_path)
        async with StockWire(cfg, wire) as server:
            # Synthetic /proc includes the actual fake HTTP port and exact argv.
            (proc / 'cmdline').write_bytes(b'\0'.join(x.encode() for x in server.cfg.argv()) + b'\0')
            (proc / 'net/tcp').write_text(
                f'header\n0: 0100007F:{server.cfg.port:04X} 00000000:0000 0A 0 0 0 0 0 987\n')
            witness.config = server.cfg
            from adapters.mineflayer import s60b2_offline_diagnostic as diagnostic
            from test_feature_s60b2_preflight import accelerated
            clock = accelerated(monkeypatch)
            monkeypatch.setattr(diagnostic, 'time', probe.time)
            monkeypatch.setattr(probe, 'preflight', lambda cfg: ())
            monkeypatch.setattr(probe, 'ProcessWitness', lambda *a: witness)
            async def ready(cfg, process, witness):
                witness.verify()
            monkeypatch.setattr(probe, 'ready', ready)
            child = SimpleNamespace(pid=345, returncode=None)
            starts, kills = [], []
            async def spawn(*args, **kw):
                starts.append(args)
                return child
            async def wait():
                child.returncode = 0
                return 0
            child.wait = wait
            monkeypatch.setattr(probe.asyncio, 'create_subprocess_exec', spawn)
            monkeypatch.setattr(probe.os, 'killpg', lambda pid, sig: kills.append((pid, sig)))
            loop = asyncio.get_running_loop()
            original = probe.Journal.emit
            def emit(self, phase, **facts):
                original(self, phase, **facts)
                if phase == 'L0_CALLBACK_RETURN' or (
                    phase == 'NEW_INFERENCE_STARTED' and facts['generation'] > 1):
                    loop.call_soon_threadsafe(server.release[-1].set)
                    if wire is None:
                        clock[0] += 61  # reach existing arm deadline, no retry
            monkeypatch.setattr(probe.Journal, 'emit', emit)
            root = tmp_path / 'receipt'
            data, base, grant = grants(server.cfg, root)
            raw = json.dumps(grant).encode()
            if entry == 'cli':
                # CLI owns asyncio.run; execute in a worker with its own loop.
                code = await asyncio.to_thread(invoke, tmp_path, data, base, root, raw)
                assert code == (2 if stage else 0)
                result = json.loads((root / 'summary.json').read_text())
            else:
                result = await probe.run(data, base, root, diagnostic_arm_a=True,
                                         diagnostic_grant_bytes=raw)
            assert len(starts) == 1 and kills == [(345, probe.signal.SIGTERM)]
            rows = [json.loads(x) for x in (root / 'events.jsonl').read_text().splitlines()]
            phases = [r['phase'] for r in rows]
            diags = [r for r in rows if r['phase'].startswith('DIAG_')]
            assert 'L0_CALLBACK_RETURN' in phases and 'OWNED_PROCESS_EXIT' in phases
            assert len(server.posts) == (1 if stage else 2)
            assert result['accounting']['complete_responses'] == (0 if stage else 2)
            if stage:
                assert result['status'] == 'UNDETERMINED'
                assert diags and all(r['phase'] == 'DIAG_' + (
                    'CLIENT_CANCEL_OR_UNKNOWN' if wire is None else stage) for r in diags)
            else:
                assert result['status'] == 'R3B_RECEIPTS_REVIEW_REQUIRED' and not diags
                assert result['accounting']['transport_starts'] == 2
            for row in diags:
                assert set(row) == {'phase', 'generation', 'monotonic_elapsed_s', 'observed_elapsed_s'}
            public = (root / 'events.jsonl').read_text() + (root / 'summary.json').read_text()
            assert all(secret not in public for secret in
                       (server.cfg.prompt, str(server.cfg.binary), 'transient-output',
                        'b' * 64, 'private /secret'))
            with pytest.raises(probe.ProbeRejected):
                await probe.run(data, base, root, diagnostic_arm_a=True, diagnostic_grant_bytes=raw)
            assert len(starts) == 1 and not result['physical_qualification']
    asyncio.run(scenario())


def test_frozen_manifest_and_authorize_unchanged():
    import inspect
    assert hashlib.sha256((probe.ROOT / 'docs/s60b2-r3b/manifest.md').read_bytes()).hexdigest() == (
        probe.R3B_MANIFEST)
    assert probe.git(probe.ROOT, 'rev-parse', 'a00b3bc:docs/s60b2-r3b/manifest.md') == (
        'fcef08402a618bc32cd2d3317dd5c6f63d9cad22')
    predecessor = probe.git(probe.ROOT, 'show', '82988fb:adapters/mineflayer/s60b2_owned_backend_probe.py')
    old = predecessor[predecessor.index('def authorize('):predecessor.index('\n\nclass Journal:')]
    assert inspect.getsource(probe.authorize).strip() == old.strip()
    for name in ('s60b1_loopback_adapter.py', 's60b2_offline_diagnostic.py', 's60b2_r3_diagnostic.py'):
        path = 'adapters/mineflayer/' + name
        assert probe.git(probe.ROOT, 'show', '82988fb:' + path) == (
            probe.ROOT / path).read_text().strip()
    assert Path(probe.ROOT / 'docs/s60b2-r3b/manifest.md').is_file()


@pytest.mark.parametrize('failure', ['preflight', 'spawn', 'cleanup', 'reservation_fsync'])
def test_diagnostic_one_shot_failures(tmp_path, admission, monkeypatch, failure):
    root = tmp_path / 'receipt'
    data, base, grant = grants(config(tmp_path), root)
    calls = []
    def preflight(cfg):
        if failure == 'preflight':
            raise probe.ProbeRejected('private /secret')
        return ()
    monkeypatch.setattr(probe, 'preflight', preflight)
    child = SimpleNamespace(pid=345, returncode=0)
    async def spawn(*a, **kw):
        calls.append(a)
        if failure == 'spawn':
            raise OSError('private /secret')
        return child
    monkeypatch.setattr(probe.asyncio, 'create_subprocess_exec', spawn)
    monkeypatch.setattr(probe, 'ProcessWitness', lambda *a: None)
    async def ready(*a):
        pass
    async def measure(*a, **kw):
        from adapters.mineflayer.s60b2_r3_diagnostic import R3DiagnosticTransport
        assert kw == {'diagnostic_adapter': R3DiagnosticTransport}
        return dict(status='P1_RECEIPTS_REVIEW_REQUIRED')
    async def cleanup(*a):
        raise TimeoutError('private /secret')
    monkeypatch.setattr(probe, 'ready', ready)
    monkeypatch.setattr(probe, 'measure', measure)
    monkeypatch.setattr(probe, 'cleanup', cleanup)
    if failure == 'reservation_fsync':
        original = probe.os.fsync
        def fsync(fd):
            original(fd)
            raise OSError('private /secret')
        monkeypatch.setattr(probe.os, 'fsync', fsync)
        with pytest.raises(OSError):
            asyncio.run(probe.run(data, base, root, diagnostic_arm_a=True,
                                 diagnostic_grant_bytes=json.dumps(grant).encode()))
        assert not calls
    else:
        result = asyncio.run(probe.run(data, base, root, diagnostic_arm_a=True,
                                      diagnostic_grant_bytes=json.dumps(grant).encode()))
        assert result['status'] == ('CLEANUP_UNCONFIRMED' if failure == 'cleanup'
                                    else 'UNDETERMINED')
        assert len(calls) == (1 if failure in ('spawn', 'cleanup') else 0)
        assert 'private /secret' not in (root / 'summary.json').read_text()
    with pytest.raises(probe.ProbeRejected):
        asyncio.run(probe.run(data, base, root, diagnostic_arm_a=True,
                             diagnostic_grant_bytes=json.dumps(grant).encode()))


def test_legacy_cli_does_not_load_extra_grant(tmp_path, monkeypatch):
    reads = []
    monkeypatch.setattr(probe, 'bounded_read', lambda p: (reads.append(p.name) or b'legacy'))
    async def run(data, base, root):
        assert data == base == b'legacy'
        return dict(status='P1_RECEIPTS_REVIEW_REQUIRED')
    monkeypatch.setattr(probe, 'run', run)
    assert probe.main(['--run', '--config', '/config', '--approval', '/approval',
                       '--evidence', str(tmp_path / 'receipt')]) == 0
    assert reads == ['config', 'approval']


def test_diagnostic_occupied_port_preflight_never_spawns(tmp_path, admission, monkeypatch):
    cfg = config(tmp_path)
    cfg.binary.write_bytes(b'fake stock')
    cfg.binary.chmod(0o700)
    cfg.gguf.write_bytes(b'GGUFfake')
    original = probe.digest
    monkeypatch.setattr(probe, 'digest', lambda p:
                        probe.BINARY if p == cfg.binary else probe.MODEL if p == cfg.gguf
                        else probe.SOURCE_FILES[str(p.relative_to(cfg.source))]
                        if cfg.source in p.parents else original(p))
    monkeypatch.setattr(probe, 'git', lambda root, *a:
                        (probe.SOURCE if root == cfg.source else 'a' * 40)
                        if a[0] == 'rev-parse' else '')
    def forbidden(*a, **kw):
        pytest.fail('occupied port reached spawn')
    monkeypatch.setattr(probe.asyncio, 'create_subprocess_exec', forbidden)
    from dataclasses import replace
    with probe.socket.socket() as listener:
        listener.bind(('127.0.0.1', 0))
        cfg = replace(cfg, port=listener.getsockname()[1])
        root = tmp_path / 'receipt'
        data, base, grant = grants(cfg, root)
        result = asyncio.run(probe.run(data, base, root, diagnostic_arm_a=True,
                                      diagnostic_grant_bytes=json.dumps(grant).encode()))
    assert result['status'] == 'UNDETERMINED'
    assert 'OWNED_PROCESS_START_INVOKED' not in (root / 'events.jsonl').read_text()
