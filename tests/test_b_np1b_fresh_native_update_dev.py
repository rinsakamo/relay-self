"""Same-session current WorldBody; external sources are synthetic."""
import asyncio
from dataclasses import replace
from pathlib import Path

import pytest

from relay_self.b_np1b_fresh_native_update_dev import FreshNativeHold, update_fresh_native
from relay_self.b_np1b_initial_source_dev import build_initial_source_receipts
from test_b_np1b_initial_source_dev import ready


def files(f):
    return {str(p): p.read_bytes() for o in f.owners.values()
            for p in Path(o.files.self_root).rglob('*') if p.is_file()}


def test_original_owner_updates_and_keeps_historical_sources(tmp_path):
    f, tick = ready(tmp_path)
    try:
        receipts = build_initial_source_receipts(bridge=f.bridge, tick=tick)
        before = files(f)
        state = {sid: (o.retained, o.intent, o.pattern_registry, dict(o.skills),
                       set(o.pending_questions)) for sid, o in f.owners.items()}
        evidence = f.bridge.last_login_evidence['A']
        initial = f.bridge.last_login_observations['A']
        other = f.owners['B'].current_worldbody_observation
        async def run():
            first = await update_fresh_native(bridge=f.bridge, self_id='A', initial_receipt=receipts[0])
            assert f.owners['A'].current_worldbody_observation.request_id == first.native_request_id
            assert first.native_sequence > initial.seq
            assert first.native_revision != receipts[0].native_revision
            assert first.native_world_time == receipts[0].native_world_time
            second = await update_fresh_native(bridge=f.bridge, self_id='A', initial_receipt=receipts[0])
            assert second.native_sequence > first.native_sequence
            assert second.native_revision != first.native_revision
        asyncio.run(run())
        assert f.bridge.last_login_evidence['A'] is evidence
        assert f.bridge.last_login_observations['A'] is initial
        assert f.owners['B'].current_worldbody_observation is other
        assert receipts[0].paper_revision and receipts[0].paper_tick == 10
        assert files(f) == before
        assert all((o.retained, o.intent, o.pattern_registry, o.skills, o.pending_questions)
                   == state[sid] for sid, o in f.owners.items())
    finally:
        f.paper._process.terminate()
        f.paper._process.wait(timeout=3)


@pytest.mark.parametrize('case', ['sequence', 'request', 'session', 'epoch', 'fence',
                                  'logout', 'time', 'malformed', 'timeout', 'adoption'])
def test_hostile_update_holds(tmp_path, monkeypatch, case):
    f, tick = ready(tmp_path)
    try:
        receipt = build_initial_source_receipts(bridge=f.bridge, tick=tick)[0]
        bridge = f.bridge
        session = bridge.sessions['A']
        owner = f.owners['A']
        old = owner.current_worldbody_observation
        receive = session.receive
        async def hostile():
            if case == 'timeout':
                await asyncio.sleep(1)
            item = await receive()
            if case == 'sequence':
                return replace(item, seq=old.seq)
            if case == 'request':
                return replace(item, request_id='foreign')
            if case == 'session':
                return replace(item, session_id='foreign')
            if case == 'epoch':
                f.cognitive._states['A'].world_epoch += 1
            if case == 'fence':
                f.cognitive.fence_self('A')
            if case == 'logout':
                await bridge.logout('A')
            if case == 'time':
                return replace(item, snapshot=replace(item.snapshot, time=replace(item.snapshot.time, time_of_day=0)))
            if case == 'malformed':
                raise ValueError('bad JSON')
            return item
        monkeypatch.setattr(session, 'receive', hostile)
        if case == 'timeout':
            bridge.probe_timeout_s = 0.01
        if case == 'adoption':
            def fail(*args, **kwargs):
                raise RuntimeError('partial adoption')
            monkeypatch.setattr(owner, 'accept_rejoined_worldbody', fail)
        async def run():
            with pytest.raises(FreshNativeHold):
                await update_fresh_native(bridge=bridge, self_id='A', initial_receipt=receipt)
        asyncio.run(run())
        assert owner.current_worldbody_observation is old
        if case == 'adoption':
            with pytest.raises(RuntimeError):
                f.cognitive.current_scope('A')
    finally:
        f.paper._process.terminate()
        f.paper._process.wait(timeout=3)


def test_actual_process_session_decoder_end_to_end(tmp_path, monkeypatch):
    import json

    import test_b_np1b_initial_source_dev as initial_tests
    from adapters.mineflayer.process_session import MineflayerProcessSession
    from adapters.mineflayer.python_protocol import MINEFLAYER_VERSION
    from test_b_np1b_native_worldbody_adoption_dev import fixture
    from test_mineflayer_process_session import observation_line

    class Session(MineflayerProcessSession):
        @property
        def owned_child_pid(self):
            return self._process.pid

        @owned_child_pid.setter
        def owned_child_pid(self, value):
            self._process.pid = value

    def make_fixture(*args, **kwargs):
        f = fixture(*args, **kwargs)
        async def launch(config):
            sid = 'native-' + config.username
            started = {'type': 'adapter_started', 'session_id': sid, 'seq': 0,
                       'mineflayer_version': MINEFLAYER_VERSION,
                       'config': {'host': config.host, 'port': config.port,
                                  'username': config.username, 'version': config.version}}
            template = json.loads(observation_line())
            template['session_id'] = sid
            template['snapshot']['time'] = {'time_of_day': 180, 'day': 0, 'is_day': True}
            template['kind'] = 'spawn'
            template['seq'] = 1
            class Pipe:
                def __init__(self):
                    self.lines = [json.dumps(started).encode() + b'\n',
                                  json.dumps(template).encode() + b'\n']
                    self.seq = 1
                def write(self, data):
                    command = json.loads(data)
                    self.seq += 1
                    probe = dict(template, kind='probe', seq=self.seq,
                                 request_id=command['request_id'])
                    self.lines.append(json.dumps(probe).encode() + b'\n')
                async def drain(self):
                    pass
                async def readline(self):
                    return self.lines.pop(0)
            class Process:
                returncode = None
                pid = 1234
                def __init__(self):
                    self.stdin = self.stdout = Pipe()
            session = Session(Process())
            session._started = await session.receive()
            return session
        f.bridge.launch = launch
        return f
    monkeypatch.setattr(initial_tests, 'fixture', make_fixture)
    f, tick = ready(tmp_path)
    try:
        receipt = build_initial_source_receipts(bridge=f.bridge, tick=tick)[0]
        session = f.bridge.sessions['A']
        revision = asyncio.run(update_fresh_native(bridge=f.bridge, self_id='A', initial_receipt=receipt))
        assert isinstance(session, MineflayerProcessSession)
        assert revision.native_sequence == 3
        assert session._decoder.next_seq == 4
        assert f.owners['A'].current_worldbody_observation.request_id == revision.native_request_id
    finally:
        f.paper._process.terminate()
        f.paper._process.wait(timeout=3)
