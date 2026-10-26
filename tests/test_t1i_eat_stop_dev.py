"""T1i: issued EAT STOP is UNKNOWN, never a second consume or food credit."""
from __future__ import annotations

import asyncio
from collections import deque
from dataclasses import replace
from types import SimpleNamespace

import pytest

import test_feature_s46_eat as s46
from adapters.mineflayer import eat_execution as eat
from adapters.mineflayer.m02_paper_dev.s51_paper_physics_dev import _issue
from adapters.mineflayer.python_protocol import MineflayerEffectResult
from adapters.mineflayer.t1h_stop_owner_dev import S49DevStopOwner, StopDevRejected
from adapters.mineflayer.t1i_session_stop_dev import require_stop_permits_action
from relay_self.action import ActionState
from relay_self.action_supervision import ActionSupervisor
from relay_self.eat_hunger import EatCursor


class Session:
    def __init__(self, before, owner, *, moment):
        self.started = SimpleNamespace(session_id=before.session_id)
        self.process_returncode = None
        self.before = before
        self.owner = owner
        self.moment = moment
        self.messages = deque()
        self.sent = []
        self._requested = False

    async def send_equip_item(self, action_id, *, item_name):
        self.sent.append(("equip_item", action_id, item_name))
        if self.moment == "after_equip":
            self.owner.request("t1i-test-stop", active_action_id="t1i-eat")
        self.messages.append(MineflayerEffectResult(
            self.before.session_id, self.before.seq + 1, action_id,
            "equip_item", "applied", None,
        ))

    async def send_consume_held(self, action_id):
        self.sent.append(("consume_held", action_id))
        if self.moment == "consume_send":
            self.owner.request("t1i-test-stop", active_action_id="t1i-eat")
        elif self.moment == "consume_wait":
            async def later():
                await asyncio.sleep(.035)
                self.owner.request("t1i-test-stop", active_action_id="t1i-eat")
            asyncio.create_task(later())
        elif self.moment in ("after_consume_receipt", "observe_stop"):
            self.messages.append(MineflayerEffectResult(
                self.before.session_id, self.before.seq + 2, action_id,
                "consume_held", "applied", None,
            ))

    async def receive(self):
        if self.messages:
            msg = self.messages.popleft()
            if self.moment == "after_consume_receipt" and (
                isinstance(msg, MineflayerEffectResult)
                and msg.effect == "consume_held"
            ):
                self.owner.request("t1i-test-stop", active_action_id="t1i-eat")
            return msg
        await asyncio.sleep(30)

    async def send_observe(self, request_id):
        self.sent.append(("observe", request_id))
        if self.moment == "observe_stop":
            self.owner.request("t1i-test-stop", active_action_id="t1i-eat")


def scenario(monkeypatch, moment):
    before = s46.case()
    choice = EatCursor(before.session_id).choose(before)
    supervisor = ActionSupervisor()
    issued = _issue(
        supervisor, "t1i-eat", "eat", "t1i-eat-intent",
        "consume native food once in a disposable DEV test", time_base=10,
    )
    owner = S49DevStopOwner(before.session_id)
    session = Session(before, owner, moment=moment)
    monkeypatch.setattr(eat, "MineflayerProcessSession", Session)
    return before, choice, supervisor, issued, owner, session


@pytest.mark.parametrize("moment", [
    "before_effect", "after_equip", "consume_send", "consume_wait", "after_consume_receipt", "observe_stop",
])
def test_stop_during_issued_eat_never_reissues_or_completes(monkeypatch, moment):
    before, choice, supervisor, issued, owner, session = scenario(monkeypatch, moment)
    if moment == "before_effect":
        owner.request("t1i-test-stop", active_action_id="t1i-eat")
    executor = eat.IssuedEatingExecutor()
    async def run():
        with pytest.raises(eat.EatingExecutionRejected, match="T1i owner STOP"):
            await asyncio.wait_for(executor.execute(
                session, supervisor, issued, choice, before,
                paper_tick_dev=True, stop_requested_dev=lambda: owner.requested,
            ), timeout=.5)
    asyncio.run(run())
    assert supervisor.get(issued.action_id).state is ActionState.UNKNOWN
    assert len([s for s in session.sent if s[0] == "consume_held"]) <= 1
    assert len([s for s in session.sent if s[0] == "equip_item"]) <= 1
    assert issued.action_id in executor._attempted
    assert owner.ack is None and not owner.allows_action
    with pytest.raises(eat.EatingExecutionRejected):
        asyncio.run(executor.execute(
            session, supervisor, issued, choice, before,
            paper_tick_dev=True, stop_requested_dev=lambda: owner.requested,
        ))


def test_stop_permission_refused_at_next_supervisor_boundary():
    owner = S49DevStopOwner("t1i-session")
    require_stop_permits_action(owner)
    owner.request("t1i-owner-stop")
    with pytest.raises(StopDevRejected, match="forbids next"):
        require_stop_permits_action(owner)
    assert owner.ack is None


def test_stop_callback_requires_explicit_paper_dev(monkeypatch):
    before, choice, supervisor, issued, owner, session = scenario(monkeypatch, "consume_wait")
    with pytest.raises(eat.EatingExecutionRejected, match="explicit Paper DEV"):
        asyncio.run(eat.IssuedEatingExecutor().execute(
            session, supervisor, issued, choice, before,
            stop_requested_dev=lambda: True,
        ))
    assert session.sent == []
    assert supervisor.get(issued.action_id).state is ActionState.ISSUED


def test_false_stop_callback_is_not_confused_with_other_safety_fault(monkeypatch):
    before, choice, supervisor, issued, owner, session = scenario(monkeypatch, "before_effect")
    # A malformed owner response cannot be interpreted as a request to
    # physically resume consumption or to book a successful EAT.
    with pytest.raises(eat.EatingExecutionRejected, match="T1i owner STOP"):
        asyncio.run(eat.IssuedEatingExecutor().execute(
            session, supervisor, issued, choice, before,
            paper_tick_dev=True, stop_requested_dev=lambda: None,
        ))
    assert supervisor.get(issued.action_id).state is ActionState.UNKNOWN
    assert session.sent == []


@pytest.mark.parametrize("fault", ["missing", "delayed", "old_session", "old_action", "source_loss"])
def test_receipt_fault_cannot_complete_eat_or_retry(monkeypatch, fault):
    from adapters.mineflayer.process_session import MineflayerProcessEnded
    before, choice, supervisor, issued, owner, session = scenario(monkeypatch, "fault")
    original = session.receive
    async def receive():
        if session.messages:
            return await original()
        if fault == "source_loss":
            raise MineflayerProcessEnded("injected source loss racing STOP")
        if fault in ("missing", "delayed"):
            await asyncio.sleep(.01)
            owner.request("t1i-test-stop", active_action_id=issued.action_id)
            if fault == "delayed":
                await asyncio.sleep(.1)
        elif fault in ("old_session", "old_action"):
            receipt = MineflayerEffectResult(
                before.session_id, before.seq + 2, issued.action_id + "-consume",
                "consume_held", "applied", None)
            if fault == "old_session":
                return replace(receipt, session_id="old-session")
            owner.request("t1i-test-stop", active_action_id=issued.action_id)
            return replace(receipt, action_id="old-action-consume")
        await asyncio.sleep(30)
    session.receive = receive
    executor = eat.IssuedEatingExecutor()
    async def run():
        with pytest.raises((eat.EatingExecutionRejected, MineflayerProcessEnded)):
            await asyncio.wait_for(executor.execute(
                session, supervisor, issued, choice, before, paper_tick_dev=True,
                stop_requested_dev=lambda: owner.requested), .5)
    asyncio.run(run())
    assert supervisor.get(issued.action_id).state is ActionState.UNKNOWN
    assert sum(x[0] == "consume_held" for x in session.sent) == 1
    assert owner.ack is None
