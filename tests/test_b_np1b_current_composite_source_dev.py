"""Current source projection through the original Native process decoder."""
import asyncio
import json
from dataclasses import replace

import pytest

from adapters.mineflayer.process_session import MineflayerProcessSession
from adapters.mineflayer.python_protocol import MINEFLAYER_VERSION
from relay_self.b_np1b_current_composite_source_dev import (
    CompositeSourceHold,
    build_current_composite_source,
)
from relay_self.b_np1b_fresh_native_update_dev import (
    FreshNativeHold,
    read_rejoined_native_revision,
    update_fresh_native,
)
from relay_self.b_np1b_initial_source_dev import build_initial_source_receipts
from relay_self.owned_paper_world_dev import PaperTickReceipt
from test_b_np1b_fresh_native_update_dev import files
from test_b_np1b_initial_source_dev import ACTORS, BOOT, PRESENCE, WORLD, ready
from test_b_np1b_native_worldbody_adoption_dev import fixture
from test_mineflayer_process_session import observation_line


@pytest.fixture
def current(tmp_path, monkeypatch):
    import test_b_np1b_initial_source_dev as initial_tests

    class Session(MineflayerProcessSession):
        @property
        def owned_child_pid(self):
            return self._process.pid

        @owned_child_pid.setter
        def owned_child_pid(self, value):
            self._process.pid = value

    def make_fixture(*args, **kwargs):
        f = fixture(*args, **kwargs)
        serial = [0]
        async def launch(config):
            serial[0] += 1
            sid = 'native-' + config.username + '-' + str(serial[0])
            started = {'type': 'adapter_started', 'session_id': sid, 'seq': 0,
                       'mineflayer_version': MINEFLAYER_VERSION,
                       'config': {'host': config.host, 'port': config.port,
                                  'username': config.username, 'version': config.version}}
            template = json.loads(observation_line())
            template.update(session_id=sid, kind='spawn', seq=1)
            template['snapshot']['time'] = {'time_of_day': 180, 'day': 0, 'is_day': True}
            class Pipe:
                def __init__(self):
                    self.lines = [json.dumps(started).encode() + b'\n',
                                  json.dumps(template).encode() + b'\n']
                    self.seq = 1
                def write(self, data):
                    command = json.loads(data)
                    self.seq += 1
                    self.lines.append(json.dumps(dict(template, kind='probe', seq=self.seq,
                        request_id=command['request_id'])).encode() + b'\n')
                async def drain(self):
                    pass
                async def readline(self):
                    return self.lines.pop(0)
            class Process:
                returncode = None
                pid = 1234
                def __init__(self):
                    self.stdin = self.stdout = Pipe()
                def terminate(self):
                    self.returncode = 0
                async def wait(self):
                    return self.returncode
            session = Session(Process())
            session._started = await session.receive()
            return session
        f.bridge.launch = launch
        return f
    monkeypatch.setattr(initial_tests, 'fixture', make_fixture)
    f, tick = ready(tmp_path)
    initial = build_initial_source_receipts(bridge=f.bridge, tick=tick)
    native = asyncio.run(update_fresh_native(bridge=f.bridge, self_id='A', initial_receipt=initial[0]))
    nonce = '77777777-7777-4777-8777-777777777777'
    session = f.paper.owned_session_id
    new_tick = PaperTickReceipt(session, 20, f'paper-main-thread:p0d:{BOOT}:{nonce}:sha256:' + 'b' * 64)
    with f.paper._log_path.open('a') as out:
        out.write(f'P0D_RESIDENT event=MOVE boot={PRESENCE} tick=15 world={WORLD} '
                  f'actor={ACTORS[0]} name=RelayA x=1 y=64 z=0 source=PAPER_MAIN_THREAD\n')
        out.write(f'P0D_TICK_ACK nonce={nonce} boot={BOOT} session={session} '
                  f'world={WORLD} tick=20 source=PAPER_MAIN_THREAD\n')
    monkeypatch.setattr(f.paper, 'tick_readback', lambda _: new_tick)
    yield f, initial, native, new_tick
    f.paper._process.terminate()
    f.paper._process.wait(timeout=3)


def build(f, initial, native):
    return build_current_composite_source(bridge=f.bridge, self_id='A',
                                           native_revision=native, initial_receipts=initial)


def test_real_logout_rejoin_fences_current_sources_and_preserves_pending(current, monkeypatch):
    from relay_self.checkpointed_cognitive_runtime_dev import load_persistent_cognition
    from relay_self.world_resident_lifecycle_dev import Presence

    f, initial, native, _ = current
    bridge = f.bridge
    composite = build(f, initial, native)
    historical = (initial, composite)
    old_probe = f.owners['A'].current_worldbody_observation
    old_login = bridge.last_login_observations['A']
    old_scope = f.cognitive.current_scope('A')
    other = (bridge.sessions['B'], f.owners['B'].current_worldbody_observation,
             f.cognitive.current_scope('B'))
    wal = f.owners['A'].files.physical_wal_file.read_bytes()
    session = bridge.sessions['A']
    receive = session.receive

    async def run():
        arrived, release = asyncio.Event(), asyncio.Event()
        async def delayed():
            item = await receive()
            arrived.set()
            await release.wait()
            return item
        monkeypatch.setattr(session, 'receive', delayed)
        task = asyncio.create_task(update_fresh_native(
            bridge=bridge, self_id='A', initial_receipt=initial[0]))
        await arrived.wait()
        proof = await bridge.logout('A')
        assert proof.physical_issuer_revoked and proof.no_physical_inflight
        assert proof.physical_wal_clear and proof.native_terminated
        assert f.cognitive.retired_clean('A')
        assert f.lifecycle.view('A').status is Presence.OFFLINE
        assert load_persistent_cognition(f.owners['A'].files.cognition_file) == f.owners['A'].retained
        assert f.owners['A'].files.physical_wal_file.read_bytes() == wal
        assert 'A' not in bridge.last_login_evidence and 'A' not in bridge.last_login_observations
        with pytest.raises(FreshNativeHold):
            read_rejoined_native_revision(bridge=bridge, self_id='A')
        with pytest.raises(CompositeSourceHold):
            build(f, initial, native)
        await bridge.login('A')
        new = read_rejoined_native_revision(bridge=bridge, self_id='A')
        assert new.resident_epoch > old_scope[0]
        assert new.native_session_id != old_scope[1]
        assert new.native_request_id != old_login.request_id
        assert f.owners['A'].current_worldbody_observation is bridge.last_login_observations['A']
        assert new.native_request_id == f.owners['A'].current_worldbody_observation.request_id
        current_probe = bridge.last_login_observations['A']
        bridge.last_login_observations['A'] = old_login
        with pytest.raises(FreshNativeHold):
            read_rejoined_native_revision(bridge=bridge, self_id='A')
        bridge.last_login_observations['A'] = replace(current_probe, request_id=old_login.request_id)
        with pytest.raises(FreshNativeHold):
            read_rejoined_native_revision(bridge=bridge, self_id='A')
        bridge.last_login_observations['A'] = current_probe
        with pytest.raises(CompositeSourceHold):
            build(f, initial, native)
        with pytest.raises(FreshNativeHold):
            await update_fresh_native(bridge=bridge, self_id='A', initial_receipt=initial[0])
        marker = object()
        bridge._fresh_native_pending['A'] = marker
        release.set()
        with pytest.raises(FreshNativeHold):
            await task
        assert bridge._fresh_native_pending['A'] is marker
        del bridge._fresh_native_pending['A']
        assert read_rejoined_native_revision(bridge=bridge, self_id='A') == new
        assert f.owners['A'].current_worldbody_observation is not old_probe
        assert (bridge.sessions['B'], f.owners['B'].current_worldbody_observation,
                f.cognitive.current_scope('B')) == other
        assert (initial, composite) == historical

    asyncio.run(run())


def test_current_composite_original_process_and_read_only(current):
    f, initial, native, _ = current
    before = files(f)
    other = f.owners['B'].current_worldbody_observation
    state = {s: (o.retained, o.intent, o.pattern_registry, dict(o.skills), set(o.pending_questions))
             for s, o in f.owners.items()}
    receipt = build(f, initial, native)
    assert isinstance(f.bridge.sessions['A'], MineflayerProcessSession)
    assert f.bridge.sessions['A']._decoder.next_seq == 4
    assert receipt == build(f, initial, native)
    assert receipt.native_revision == native.native_revision != initial[0].native_revision
    assert receipt.paper_revision != initial[0].paper_revision
    assert receipt.composite_revision not in (receipt.paper_revision, receipt.native_revision)
    assert receipt.paper_tick == 20 and receipt.paper_actor_uuid == ACTORS[0]
    assert f.owners['B'].current_worldbody_observation is other
    assert files(f) == before
    assert all((o.retained, o.intent, o.pattern_registry, o.skills, o.pending_questions) == state[s]
               for s, o in f.owners.items())
    assert initial[0].paper_tick == 10


@pytest.mark.parametrize('case', ['stale', 'pending', 'boot', 'session', 'pid', 'nonce', 'missing_ack',
                                  'observation', 'duplicate', 'replace', 'quit', 'log_change',
                                  'native_session', 'epoch'])
def test_hostile_sources_hold(current, monkeypatch, case):
    f, initial, native, tick = current
    paper, bridge = f.paper, f.bridge
    if case == 'stale':
        asyncio.run(update_fresh_native(bridge=bridge, self_id='A', initial_receipt=initial[0]))
    elif case == 'pending':
        bridge._fresh_native_pending['A'] = object()
    elif case in ('boot', 'session', 'nonce'):
        tick = replace(tick, **({'server_session_id': 'foreign'} if case == 'session' else
            {'source_ref': tick.source_ref.replace(BOOT if case == 'boot' else '77777777', 'foreign')}))
        monkeypatch.setattr(paper, 'tick_readback', lambda _: tick)
    elif case == 'pid':
        initial = tuple(replace(r, paper_pid=r.paper_pid + 1) for r in initial)
    elif case in ('missing_ack', 'observation', 'duplicate', 'replace', 'quit'):
        log = paper._log_path.read_text()
        if case == 'missing_ack':
            log = log.replace('nonce=77777777', 'nonce=88888888')
        elif case == 'observation':
            log = ''.join(line for line in log.splitlines(keepends=True) if 'tick=15' not in line)
        elif case == 'duplicate':
            log = log.replace(ACTORS[1], ACTORS[0])
        elif case == 'replace':
            log = log.replace('actor=' + ACTORS[0] + ' name=RelayA x=1', 'actor=' + ACTORS[1] + ' name=RelayA x=1')
        else:
            log = log.replace('event=MOVE boot=' + PRESENCE + ' tick=15', 'event=QUIT boot=' + PRESENCE + ' tick=15')
        paper._log_path.write_text(log)
    else:
        read = paper.read_owned_log
        count = [0]
        def changed(session):
            result = read(session)
            count[0] += 1
            if count[0] == 1:
                if case == 'native_session':
                    bridge.sessions['A'].started.session_id = 'foreign'
                elif case == 'epoch':
                    f.cognitive._states['A'].world_epoch += 1
            return result + (b'changed' if case == 'log_change' and count[0] > 1 else b'')
        monkeypatch.setattr(paper, 'read_owned_log', changed)
    with pytest.raises(CompositeSourceHold):
        build(f, initial, native)
