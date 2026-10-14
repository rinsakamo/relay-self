"""DEV isolation and negative controls; no physical launch in these fixtures."""
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
