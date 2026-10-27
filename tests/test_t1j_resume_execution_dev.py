"""Offline faults through the consumed T1j gate and original S49 executor."""
import asyncio
from dataclasses import replace
from types import SimpleNamespace as S

import pytest

import adapters.mineflayer.t1j_resume_native_dev as resume
import test_mineflayer_execution_qualification as base
from adapters.mineflayer.python_protocol import MineflayerConnectionEnd
from adapters.mineflayer.t1j_resume_gate_dev import ResumeDevRejected
from relay_self.action import ActionState
from relay_self.action_supervision import ActionSupervisor
from test_t1f_t2_dev import frame
from test_t1j_native_rebase_dev import stopped


@pytest.mark.parametrize('fault', ['missing_ack', 'old_ack', 'disconnect', 'before_send'])
def test_resumed_motor_fault_is_unknown_and_permit_cannot_retry(monkeypatch, fault):
    owner, old = stopped()
    aid = 't1j-T1J-R1-move'
    messages = [base.observation(130, 0, 0)]
    if fault == 'old_ack':
        messages.append(base.effect(131, 'old-action', 'set_control'))
    elif fault == 'disconnect':
        messages.extend([base.effect(131, aid, 'set_control'),
                         MineflayerConnectionEnd('s15-session', 132, 'fault')])
    session = base.FakeSession([replace(m, session_id='test-session') for m in messages])
    session.started = replace(session.started, session_id='test-session')
    session.process_returncode = None
    session.source_lost = False
    session.consume_tick_accounting = False
    session.tick_owner = old
    session.t1j_reauthorization = 'DEV_EXPLICIT_OPERATOR_REAUTHORIZE'
    if fault == 'before_send':
        session.t1k_fault = 'BEFORE_RESUME_SEND'

        async def disconnect(_boundary):
            assert not session.consume_tick_accounting
            session.source_lost = True

        session.inject_disconnect = disconnect
    ticks = iter([frame(10), frame(12)])

    async def next_tick(*a, **kw):
        if session.source_lost:
            raise RuntimeError('original receiver observed injected disconnect')
        return next(ticks)

    async def observe(*a, **kw):
        return S(session_id='test-session', seq=110, kind='probe',
                 request_id='t1j-R1-reobserve', provenance=S(source='mineflayer'),
                 snapshot=S(food=20, health=20, position=S(x=0, y=1, z=0)))

    original_execute = resume.execute_mineflayer_command

    async def execute(session, command, **kw):
        kw['timeout_s'] = .01
        return await original_execute(session, replace(command, duration_s=.002), **kw)

    monkeypatch.setattr(resume, 'next_tick', next_tick)
    monkeypatch.setattr(resume, '_correlated_observe', observe)
    monkeypatch.setattr(resume, 'execute_mineflayer_command', execute)
    supervisor = ActionSupervisor()
    report = {'epochs': []}
    with pytest.raises(ResumeDevRejected):
        asyncio.run(resume.resume_one_move_dev(session, supervisor, owner, report, time_base=400))
    if fault == 'before_send':
        attempt = report['resume_attempts_dev'][0]
        assert attempt['permit_consumed'] and not attempt['motor_send_attempted']
        assert attempt['permission_cleared'] and attempt['old_ledger_unchanged']
        assert attempt['ledger']['rows'] == []
        assert not supervisor.open_actions and not session.sent
        with pytest.raises(ResumeDevRejected):
            asyncio.run(resume.resume_one_move_dev(session, supervisor, owner, report, time_base=500))
        assert not session.sent
        return
    assert supervisor.get(aid).state is ActionState.UNKNOWN
    attempt = report['resume_attempts_dev'][0]
    assert attempt['terminal']['state'] == 'unknown'
    assert attempt['terminal']['_events'][-1]['state'] == 'unknown'
    assert attempt['permit_consumed'] and attempt['permission_cleared']
    assert attempt['old_ledger_unchanged']
    assert old.failed and owner.requested and not owner.allows_action
    assert session.tick_owner.failed and session.t1j_resume_permission is None
    assert sum(x[0] == 'set_control' for x in session.sent) == 1
    assert sum(x[0] == 'clear_controls' for x in session.sent) == 1
    with pytest.raises(ResumeDevRejected):
        asyncio.run(resume.resume_one_move_dev(session, supervisor, owner, report, time_base=500))
    assert sum(x[0] == 'set_control' for x in session.sent) == 1

@pytest.mark.parametrize('fault', ['no_authority', 'no_stop_ack', 'missing_native',
                                  'stale_paper', 'food_mismatch', 'control_active',
                                  'hazard', 'foreign_session', 'unknown_eat'])
def test_resume_refusal_never_issues_or_sends_motor(monkeypatch, fault):
    owner, old = stopped()
    session = base.FakeSession()
    session.started = replace(session.started, session_id='test-session')
    session.process_returncode = None
    session.source_lost = False
    session.consume_tick_accounting = False
    session.tick_owner = old
    session.t1j_reauthorization = None if fault == 'no_authority' else 'DEV_EXPLICIT_OPERATOR_REAUTHORIZE'
    before, after = frame(10), frame(12)
    native = S(session_id='test-session', seq=110, kind='probe',
               request_id='t1j-R1-reobserve', provenance=S(source='mineflayer'),
               snapshot=S(food=20, health=20, position=S(x=0, y=1, z=0)))
    if fault == 'no_stop_ack':
        owner.ack = None
    elif fault == 'missing_native':
        native = None
    elif fault == 'stale_paper':
        before.data['status'] = 'STALE'
    elif fault == 'food_mismatch':
        native.snapshot.food = 18
    elif fault == 'control_active':
        before.data['control']['phase'] = 'MOVING'
    elif fault == 'hazard':
        before.data['snapshot']['threats'] = ['hazard']
    elif fault == 'foreign_session':
        native.session_id = 'foreign'
    elif fault == 'unknown_eat':
        old.pending_meal = object()
    ticks = iter([before, after])

    async def next_tick(*a, **kw):
        return next(ticks)

    async def observe(*a, **kw):
        return native

    monkeypatch.setattr(resume, 'next_tick', next_tick)
    monkeypatch.setattr(resume, '_correlated_observe', observe)
    supervisor = ActionSupervisor()
    with pytest.raises(ResumeDevRejected):
        asyncio.run(resume.resume_one_move_dev(session, supervisor, owner, {}, time_base=400))
    assert not supervisor.open_actions and session.sent == []
    assert session.tick_owner is old and old.failed
    assert not session.consume_tick_accounting and owner.requested
