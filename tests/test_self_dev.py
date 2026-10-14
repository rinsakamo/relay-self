"""DEV isolation and negative controls; no physical launch in these fixtures."""
import asyncio
import json
import socket
from types import SimpleNamespace

import pytest

from adapters.mineflayer import self_demo as demo


def args(root, **changes):
    return SimpleNamespace(output_dir=root, confirm=demo.CONFIRM, run_disposable=True,
                           think=False, live_think=False, reflect_report=None, smoke=False,
                           retry_of=None, **changes)


def test_default_and_mode_spoofing(tmp_path, monkeypatch):
    monkeypatch.setattr(demo, '_run_disposable', lambda *a: pytest.fail('launched'))
    assert demo.main([]) == 0
    for mode in ('QUALIFICATION', 'SCIENCE', 'DEV_ONLY'):
        with pytest.raises(SystemExit):
            demo.main(['--mode', mode])


@pytest.mark.parametrize('kind', ['existing', 'symlink', 'relative', 'no_consent'])
def test_unsafe_output_and_consent(tmp_path, monkeypatch, kind):
    monkeypatch.setattr(demo, '_run_disposable', lambda *a: pytest.fail('launched'))
    root = tmp_path / 'fresh'
    a = args(root)
    if kind == 'existing':
        root.mkdir()
    elif kind == 'symlink':
        root.symlink_to(tmp_path, target_is_directory=True)
    elif kind == 'relative':
        a.output_dir = demo.Path('relative')
    else:
        a.confirm = None
    assert demo._dev_run(a) == 2
    assert not (root / 'dev_receipt.json').exists()


def test_two_failed_runs_preserve_lineage(tmp_path, monkeypatch):
    monkeypatch.setattr(demo.shutil, 'which', lambda _: None)
    roots = [tmp_path / 'one', tmp_path / 'two']
    assert demo._dev_run(args(roots[0])) == 2
    original = (roots[0] / 'dev_receipt.json').read_bytes()
    first = json.loads(original)
    second_args = args(roots[1])
    second_args.retry_of = first['run_id']
    assert demo._dev_run(second_args) == 2
    second = json.loads((roots[1] / 'dev_receipt.json').read_text())
    assert first['run_id'] != second['run_id']
    assert second['retry_of'] == first['run_id']
    assert (roots[0] / 'dev_receipt.json').read_bytes() == original
    for row in (first, second):
        assert row['mode'] == 'DEV' and row['classification'] == 'DEV_ONLY'
        assert row['status'] == 'NOT_RUN'
        assert not any(row[k] for k in ('engineering_qualified', 'science_success', 'g3_go',
                                       'm_energy_credited'))


def test_busy_port_stops_before_owner(tmp_path, monkeypatch):
    monkeypatch.setattr(demo.shutil, 'which', lambda _: '/tool')
    monkeypatch.setattr(demo.subprocess, 'run', lambda *a, **kw:
                        SimpleNamespace(returncode=0, stdout='version', stderr=''))
    monkeypatch.setattr(demo, '_run_disposable', lambda *a: pytest.fail('launched'))
    with socket.socket() as listener:
        listener.bind(('127.0.0.1', 25565))
        listener.listen()
        assert demo._dev_run(args(tmp_path / 'busy')) == 2
    assert 'Address already in use' in (tmp_path / 'busy' / 'dev_receipt.json').read_text()


def test_dev_success_keeps_owner_report_but_never_promotes(tmp_path, monkeypatch):
    monkeypatch.setattr(demo.shutil, 'which', lambda _: '/tool')
    monkeypatch.setattr(demo.subprocess, 'run', lambda *a, **kw:
                        SimpleNamespace(returncode=0, stdout='version', stderr=''))
    async def owner(report, log):
        assert demo.tempfile.gettempdir() == str(report.parent / 'owned-worlds')
        report.write_text(json.dumps({'status': 'PASS', 'session_id': 'fixture',
                                     'classification': 'QUALIFIED', 'server_exit': 0}))
        return 0
    monkeypatch.setattr(demo, '_run_disposable', owner)
    root = tmp_path / 'success'
    assert demo._dev_run(args(root)) == 0
    row = json.loads((root / 'dev_receipt.json').read_text())
    assert row['classification'] == 'DEV_ONLY'
    assert row['engineering_qualified'] is False
    assert not (root / 'observed_memory.json').exists()


@pytest.mark.parametrize('marker', ['level.dat', 'SHA256SUMS', 'grant-consumed.json', '.git',
                                   'dev_receipt.json'])
def test_existing_world_and_frozen_evidence_ancestry(tmp_path, monkeypatch, marker):
    monkeypatch.setattr(demo, '_run_disposable', lambda *a: pytest.fail('launched'))
    (tmp_path / marker).write_text('protected')
    assert demo._dev_run(args(tmp_path / 'new')) == 2
    assert not (tmp_path / 'new').exists()
    assert (tmp_path / marker).read_text() == 'protected'


def test_b0_dev_scenario_rejects_non_dev_authority():
    with pytest.raises(SystemExit):
        demo.main(['--run-disposable', '--dev-scenario', 'b0-ground'])


def test_s51_b0_dev_source_scope_denies_v6_and_rsee(tmp_path):
    from adapters.mineflayer.s51_eat_real_ci import qualify
    report, log = tmp_path / 'report.json', tmp_path / 'server.log'
    for values in (
        {'food_source': 'groundv6'},
        {'rsee': object()},
        {'confirmation': 'B0-RSEE-I-OWN-ONE-DISPOSABLE-WORLD'},
        {'preflight_only': True},
    ):
        opts = {'food_item': 'rotten_flesh', 'food_source': 'ground', 'dev_only': True}
        opts.update(values)
        with pytest.raises(ValueError, match='DEV B0 requires'):
            asyncio.run(qualify(report, log, **opts))
    assert not report.exists() and not log.exists()


def test_dev_b0_delegates_existing_s51_owner_without_new_launch(tmp_path, monkeypatch):
    from adapters.mineflayer import s51_eat_real_ci as s51
    calls = []
    async def existing_owner(report, server_log, **kwargs):
        calls.append((report, server_log, kwargs))
        assert demo.os.environ.get('S51_REAL_SERVER_CI') == '1'
        return 0
    monkeypatch.setattr(s51, 'qualify', existing_owner)
    monkeypatch.setenv('S51_REAL_SERVER_CI', 'previous-isolated-value')
    report = tmp_path / 'owner.json'
    log = tmp_path / 'server.log'
    assert asyncio.run(demo._run_b0_ground_dev(report, log)) == 0
    assert calls == [(report, log, {'food_item': 'rotten_flesh',
                                    'food_source': 'ground', 'dev_only': True})]
    assert demo.os.environ['S51_REAL_SERVER_CI'] == 'previous-isolated-value'


def test_dev_b0_receipt_cannot_promote_forged_s51_qualified(tmp_path, monkeypatch):
    monkeypatch.setattr(demo.shutil, 'which', lambda _: '/tool')
    monkeypatch.setattr(demo.subprocess, 'run', lambda *a, **kw:
                        SimpleNamespace(returncode=0, stdout='version', stderr=''))
    async def mocked_s51(report, log):
        report.write_text(json.dumps({
            'status': 'PASS', 'owner_status': 'PASS',
            'classification': 'QUALIFIED', 'session_id': 'dev-source',
            'm_energy_credited': True,
            'metabolism_after_eat': {'credit_count': 1},
            'ground_pickup': {'status': 'PICKUP_SOURCE_CONSISTENT',
                              'movement_outcomes': [{'kind': 'MOVE'}]},
            'action_terminal': 'OUTCOME',
            'next_l0': {'kind': 'WAIT'},
            'server_exit': 0, 'node_exit': 0,
        }))
        return 0
    monkeypatch.setattr(demo, '_run_b0_ground_dev', mocked_s51)
    root = tmp_path / 'b0-dev'
    a = args(root)
    a.dev_scenario = 'b0-ground'
    assert demo._dev_run(a) == 0
    receipt = json.loads((root / 'dev_receipt.json').read_text())
    assert receipt['classification'] == 'DEV_ONLY'
    assert receipt['scenario'] == 'b0-ground'
    assert receipt['dev_b0_pickup'] == 'PICKUP_SOURCE_CONSISTENT'
    assert receipt['dev_b0_m0_credit_source_claim'] is True
    assert receipt['dev_b0_m0_credit_count'] == 1
    assert receipt['dev_b0_next_l0_kind'] == 'WAIT'
    assert receipt['dev_b0_move_outcomes'] == 1
    assert receipt['engineering_qualified'] is False
    assert receipt['science_success'] is False
    assert receipt['m_energy_credited'] is False
    assert receipt['g3_go'] is False
    assert (root / 'native_report.json').is_file()
    assert (root / 'SHA256SUMS').is_file()

