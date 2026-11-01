"""Synthetic stream checks only; no physical chronology attestation."""
import json

import pytest

from adapters.mineflayer.self_body_s50_l1_host_prediction import HostPrediction


def stream(hook):
    hook.arm('new-session', 'new-action', 'marker')
    hook.observe(b'M02_DEV_S50_PHASE marker_id=marker phase=PRE_FORWARD world=new-world\n')


def test_fsync_prediction_precedes_next_read(tmp_path):
    path = tmp_path / 'journal'
    hook = HostPrediction(path)
    stream(hook)
    for i in range(1, 9):
        hook.observe((f'S50_DEV_WAIT_TICK marker_id=marker world=new-world tick={i} '
                      f'index={i} from_x=0 from_y=0 from_z=0 x=0.01 y=0 z=0\n').encode())
        rows = [json.loads(x) for x in path.read_text().splitlines()]
        assert rows[-1]['kind'] == ('PREDICTION_FIXED' if i < 8 else 'OBSERVED')
    assert len([r for r in rows if r['kind'] == 'PREDICTION_FIXED']) == 7
    assert rows[2]['kind'] == 'TARGET_FIXED'
    assert rows[2]['ticket']['model']['slope'] == 0.20331885786720635


@pytest.mark.parametrize('row', [
    b'S50_DEV_WAIT_TICK marker_id=marker world=foreign tick=1 index=1\n',
    b'S50_DEV_WAIT_TICK marker_id=marker world=new-world tick=1 index=2\n',
    b'S50_DEV_WAIT_TICK marker_id=marker world=new-world tick=1 index=1 from_x=nan from_y=0 from_z=0 x=0 y=0 z=0\n',
])
def test_reject_invalid_source(tmp_path, row):
    hook = HostPrediction(tmp_path / 'journal')
    stream(hook)
    with pytest.raises(ValueError):
        hook.observe(row)


def test_no_reuse(tmp_path):
    path = tmp_path / 'journal'
    hook = HostPrediction(path)
    stream(hook)
    with pytest.raises(ValueError):
        hook.arm('new', 'new', 'new')
    with pytest.raises(FileExistsError):
        HostPrediction(path)


def test_original_collector_sink_flush_notifies_synchronously(tmp_path):
    hook = HostPrediction(tmp_path / 'journal')
    hook.arm('new-session', 'new-action', 'marker')
    path = tmp_path / 'server.log'
    observed = hook.collector_log(path)
    assert observed == path and observed.parent == path.parent
    line = 'M02_DEV_S50_PHASE marker_id=marker phase=PRE_FORWARD world=new-world\n'
    with observed.open('w', encoding='utf-8') as sink:
        sink.write(line)
        assert hook.ticket is None
        sink.flush()
        assert hook.ticket is not None
        assert path.read_text() == line
    assert path.read_text() == line


def test_protected_sole_collector_commits_before_reading_next_callback(monkeypatch, tmp_path):
    import asyncio
    from types import SimpleNamespace

    from adapters.mineflayer.s31a_real_server_ci import _ready_server

    async def run():
        hook = HostPrediction(tmp_path / 'journal')
        hook.arm('new-session', 'new-action', 'marker')
        raw_lines = [
            b'Done (1s)! For help\n',
            b'M02_DEV_S50_PHASE marker_id=marker phase=PRE_FORWARD world=new-world\n',
            b'S50_DEV_WAIT_TICK marker_id=marker world=new-world tick=1 index=1 from_x=0 from_y=0 from_z=0 x=0.01 y=0 z=0\n',
        ]

        class Stream:
            count = 0

            async def readline(self):
                if self.count == 3:
                    rows = [json.loads(x) for x in hook.path.read_text().splitlines()]
                    assert rows[-1]['kind'] == 'PREDICTION_FIXED'
                    return b''
                line = raw_lines[self.count]
                self.count += 1
                return line

        process = SimpleNamespace(stdout=Stream(), returncode=None)

        async def fixture_java(*args, **kwargs):
            return process

        monkeypatch.setattr(asyncio, 'create_subprocess_exec', fixture_java)
        log = tmp_path / 'server.log'
        raw = tmp_path / 'raw.bin'
        _, collector, _ = await _ready_server(
            tmp_path, tmp_path / 'unused.jar', hook.collector_log(log), raw_stdout_path=raw,
        )
        await collector
        assert raw.read_bytes() == log.read_bytes() == b''.join(raw_lines)

    asyncio.run(run())
