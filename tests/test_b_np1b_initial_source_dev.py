"""Synthetic Paper boundary through fresh original owners and bridge."""
import asyncio
from dataclasses import replace
from pathlib import Path

import pytest

from relay_self.b_np1b_initial_source_dev import InitialSourceHold, build_initial_source_receipts
from relay_self.owned_paper_world_dev import PaperTickReceipt
from test_b_np1b_native_worldbody_adoption_dev import fixture

WORLD = '11111111-1111-4111-8111-111111111111'
BOOT = '22222222-2222-4222-8222-222222222222'
PRESENCE = '33333333-3333-4333-8333-333333333333'
NONCE = '44444444-4444-4444-8444-444444444444'
ACTORS = ('55555555-5555-4555-8555-555555555555', '66666666-6666-4666-8666-666666666666')


def ready(tmp_path):
    f = fixture(tmp_path, names=('A', 'B'), world_id=WORLD)
    # Names in the actual Paper trace are Minecraft player names.
    for sid in f.names:
        f.bridge.configs[sid] = replace(f.bridge.configs[sid], username='Relay' + sid)
    async def login():
        for sid in f.names:
            await f.bridge.login(sid)
            f.bridge.sessions[sid].owned_child_pid = 1000 + ord(sid)
    asyncio.run(login())
    sid = f.paper.owned_session_id
    lines = [f'P0D_TICK_READY boot={BOOT} source=PAPER_MAIN_THREAD',
             f'P0D_RESIDENT_READY boot={PRESENCE} source=PAPER_MAIN_THREAD version=1']
    for tick, (name, event, actor) in enumerate((
        ('RelayA', 'JOIN', ACTORS[0]), ('RelayB', 'JOIN', ACTORS[1]),
        ('RelayA', 'PRESENT', ACTORS[0]), ('RelayB', 'MOVE', ACTORS[1]),
    ), 1):
        lines.append(f'P0D_RESIDENT event={event} boot={PRESENCE} tick={tick} '
                     f'world={WORLD} actor={actor} name={name} x=0 y=64 z=0 source=PAPER_MAIN_THREAD')
    lines.append(f'P0D_TICK_ACK nonce={NONCE} boot={BOOT} session={sid} '
                 f'world={WORLD} tick=10 source=PAPER_MAIN_THREAD')
    f.paper._log_path.write_text('\n'.join(lines) + '\n')
    tick = PaperTickReceipt(sid, 10, f'paper-main-thread:p0d:{BOOT}:{NONCE}:sha256:' + 'a' * 64)
    return f, tick


def test_fresh_initial_source_both_are_stable_and_read_only(tmp_path):
    f, tick = ready(tmp_path)
    try:
        before = {str(p): p.read_bytes() for o in f.owners.values()
                  for p in Path(o.files.self_root).rglob('*') if p.is_file()}
        state = {sid: (o.retained, o.intent, o.pattern_registry, dict(o.skills),
                       set(o.pending_questions)) for sid, o in f.owners.items()}
        receipts = build_initial_source_receipts(bridge=f.bridge, tick=tick)
        assert receipts == build_initial_source_receipts(bridge=f.bridge, tick=tick)
        for receipt, sid, actor in zip(receipts, f.names, ACTORS):
            assert receipt.self_id == sid
            assert receipt.native_session_id == f.bridge.sessions[sid].started.session_id
            assert receipt.paper_actor_uuid == actor
        assert before == {str(p): p.read_bytes() for o in f.owners.values()
                          for p in Path(o.files.self_root).rglob('*') if p.is_file()}
        assert all((o.retained, o.intent, o.pattern_registry, o.skills, o.pending_questions)
                   == state[sid] for sid, o in f.owners.items())
    finally:
        f.paper._process.terminate()
        f.paper._process.wait(timeout=3)


@pytest.mark.parametrize('mutation', ['request', 'session', 'unadopted', 'paper_session',
                                      'boot', 'nonce', 'missing_ack', 'join', 'presence', 'duplicate',
                                      'pid', 'native_change', 'log_change'])
def test_foreign_and_changing_sources_hold(tmp_path, monkeypatch, mutation):
    f, tick = ready(tmp_path)
    try:
        b = f.bridge
        if mutation == 'request':
            b.last_login_evidence['A'] = replace(b.last_login_evidence['A'], observation_ref='foreign')
        elif mutation == 'session':
            b.sessions['A'].started.session_id = 'foreign'
        elif mutation == 'unadopted':
            f.owners['A'].current_worldbody_observation = None
        elif mutation == 'paper_session':
            tick = replace(tick, server_session_id='foreign')
        elif mutation == 'boot':
            tick = replace(tick, source_ref=tick.source_ref.replace(BOOT, 'foreign'))
        elif mutation == 'nonce':
            tick = replace(tick, source_ref=tick.source_ref.replace(NONCE, 'foreign'))
        elif mutation in ('presence', 'duplicate', 'join', 'missing_ack'):
            data = f.paper._log_path.read_text()
            if mutation == 'presence':
                data = data.replace('event=PRESENT', 'event=QUIT')
            elif mutation == 'join':
                data = data.replace('event=JOIN', 'event=MOVE')
            elif mutation == 'missing_ack':
                data = data.replace('P0D_TICK_ACK', 'P0D_TICK_MISSING')
            else:
                data = data.replace(ACTORS[1], ACTORS[0])
            f.paper._log_path.write_text(data)
        elif mutation == 'pid':
            original = f.paper._assert_owned
            calls = [0]
            def changed_pid():
                calls[0] += 1
                process = original()
                if calls[0] > 2:
                    from types import SimpleNamespace
                    return SimpleNamespace(pid=process.pid + 1)
                return process
            monkeypatch.setattr(f.paper, '_assert_owned', changed_pid)
        elif mutation == 'native_change':
            read = f.paper.read_owned_log
            def changing_native(session):
                value = read(session)
                b.sessions['A'].started.session_id = 'changed'
                return value
            monkeypatch.setattr(f.paper, 'read_owned_log', changing_native)
        else:
            read = f.paper.read_owned_log
            count = [0]
            def changing(session):
                count[0] += 1
                return read(session) + (b'changed' if count[0] > 1 else b'')
            monkeypatch.setattr(f.paper, 'read_owned_log', changing)
        with pytest.raises(InitialSourceHold):
            build_initial_source_receipts(bridge=b, tick=tick)
    finally:
        f.paper._process.terminate()
        f.paper._process.wait(timeout=3)
