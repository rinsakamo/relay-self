"""DEV-only repeated S49 ATTACK permission and disappearing native target.

Offline mock transport: not original real World; a vanished zombie never means
death, kill credit, item drop, or permission to repeat a failed/UNKNOWN Action.
"""
from __future__ import annotations

import asyncio
from dataclasses import replace

import pytest

import test_bug0_s49_attack_owner as base
from adapters.mineflayer import attack_execution, normal_action
from adapters.mineflayer.attack_execution import AttackExecutionRejected, verify_attack_effect
from adapters.mineflayer.normal_action import NormalActionRejected, NormalSessionActionExecutor
from adapters.mineflayer.python_protocol import MineflayerEffectResult
from relay_self.action import ActionState


def _empty(original):
    cov = original.snapshot.nearby_entities_coverage
    return replace(
        original,
        snapshot=replace(
            original.snapshot,
            nearby_entities=(),
            nearby_entities_coverage=replace(
                cov, candidate_count=0, truncated=False,
            ),
        ),
    )


def test_default_one_attack_guard_unchanged():
    first, second = base._pair()
    owner = base._owner(first)
    eid = second.snapshot.nearby_entities[0].entity_id
    owner._count = 1
    owner._attack_count = 1
    propose, issue = base._grants(owner, second, eid)
    with pytest.raises(NormalActionRejected):
        owner.require_attack_authorizations(first, second, eid, propose, issue)


@pytest.mark.parametrize("invalid", [0, -1, 33, True, 1.1, "32"])
def test_attack_budget_is_operator_bounded_not_user_suggested(invalid):
    first, _ = base._pair()
    with pytest.raises(NormalActionRejected):
        NormalSessionActionExecutor(
            first.session_id, base._owner(first).intent,
            max_sequential_attacks=invalid,
        )


def test_repeated_actions_require_unique_authorization_and_native_probes(monkeypatch):
    first, second = base._pair()
    owner = NormalSessionActionExecutor(
        first.session_id, base._owner(first).intent, max_sequential_attacks=2,
    )
    native = base.FakeNativeSession(second)
    monkeypatch.setattr(normal_action, "MineflayerProcessSession", base.FakeNativeSession)
    monkeypatch.setattr(attack_execution, "MineflayerProcessSession", base.FakeNativeSession)
    eid = second.snapshot.nearby_entities[0].entity_id

    a1, b1 = base._grants(owner, second, eid)
    r1 = asyncio.run(owner.execute_attack(native, first, second, eid, a1, b1))
    assert r1.terminal.state is ActionState.OUTCOME
    assert r1.target_missing_in_native_view is False
    assert owner._attack_count == owner._count == 1

    # Repeating the same old source or Action ID cannot initiate new physical IO.
    with pytest.raises(NormalActionRejected):
        asyncio.run(owner.execute_attack(native, first, second, eid, a1, b1))
    assert len([e for e in native.sent if e[0] == "attack"]) == 1

    p2 = replace(second, seq=110, request_id="fresh-rearm-before")
    q2 = replace(second, seq=111, request_id="fresh-rearm-after")
    native.before = q2
    olda, oldb = base._grants(owner, q2, eid)
    a2 = replace(olda, action_id="second-distinct-attack")
    b2 = replace(oldb, action_id="second-distinct-attack")
    r2 = asyncio.run(owner.execute_attack(native, p2, q2, eid, a2, b2))
    assert r2.terminal.state is ActionState.OUTCOME
    assert owner._attack_count == owner._count == 2
    assert owner.supervisor.open_actions == ()
    assert len([e for e in native.sent if e[0] == "attack"]) == 2
    q3 = replace(q2, seq=121, request_id="third-new")
    with pytest.raises(NormalActionRejected):
        owner.require_attack_authorizations(q2, q3, eid, a2, b2)


def test_missing_target_requires_explicit_opt_in_and_no_fabricated_death():
    _, before = base._pair()
    eid = before.snapshot.nearby_entities[0].entity_id
    ack = MineflayerEffectResult(
        before.session_id, before.seq + 1,
        "a", "attack_entity", "applied", None,
    )
    after = replace(_empty(before), seq=before.seq + 3, request_id="after")
    with pytest.raises(AttackExecutionRejected):
        verify_attack_effect(before, ack, after, action_id="a", entity_id=eid)
    verify_attack_effect(
        before, ack, after, action_id="a", entity_id=eid,
        allow_target_disappearance=True,
    )


@pytest.mark.parametrize("bad", ["foreign-ack", "foreign-session", "mob-replacement", "truncated", "stale"])
def test_missing_does_not_override_source_failures(bad):
    _, before = base._pair()
    eid = before.snapshot.nearby_entities[0].entity_id
    ack = MineflayerEffectResult(
        before.session_id, before.seq + 1,
        "a", "attack_entity", "applied", None,
    )
    after = replace(_empty(before), seq=before.seq + 3, request_id="after")
    if bad == "foreign-ack":
        ack = replace(ack, action_id="other")
    elif bad == "foreign-session":
        after = replace(after, session_id="other")
    elif bad == "mob-replacement":
        mob = replace(before.snapshot.nearby_entities[0], name="cow")
        after = replace(
            after, snapshot=replace(after.snapshot,
                nearby_entities=(mob,),
                nearby_entities_coverage=replace(
                    after.snapshot.nearby_entities_coverage, candidate_count=1),
            ),
        )
    elif bad == "truncated":
        mob = before.snapshot.nearby_entities[0]
        after = replace(
            after, snapshot=replace(after.snapshot,
                nearby_entities=tuple(replace(mob, entity_id=mob.entity_id + i)
                                      for i in range(16)),
                nearby_entities_coverage=replace(
                    after.snapshot.nearby_entities_coverage,
                    candidate_count=17, truncated=True),
            ),
        )
    else:
        after = replace(after, seq=before.seq, request_id="stale")
    with pytest.raises(AttackExecutionRejected):
        verify_attack_effect(
            before, ack, after, action_id="a", entity_id=eid,
            allow_target_disappearance=True,
        )


def test_repeated_attack_cannot_follow_unknown_outcome(monkeypatch):
    first, second = base._pair()
    owner = NormalSessionActionExecutor(
        first.session_id, base._owner(first).intent, max_sequential_attacks=2,
    )
    eid = second.snapshot.nearby_entities[0].entity_id

    class NativeRejects(base.FakeNativeSession):
        async def send_attack_entity(self, action_id, *, entity_id):
            await super().send_attack_entity(action_id, entity_id=entity_id)
            self.frames[0] = replace(
                self.frames[0], result="rejected", error="entity_not_found",
            )

    session = NativeRejects(second)
    monkeypatch.setattr(normal_action, "MineflayerProcessSession", NativeRejects)
    monkeypatch.setattr(attack_execution, "MineflayerProcessSession", NativeRejects)
    propose, issue = base._grants(owner, second, eid)
    with pytest.raises(AttackExecutionRejected):
        asyncio.run(owner.execute_attack(
            session, first, second, eid, propose, issue,
        ))
    assert owner.supervisor.get(propose.action_id).state is ActionState.UNKNOWN
    assert owner.supervisor.open_actions == ()
    assert owner._attack_count == owner._count == 1
    pre = replace(second, seq=110, request_id="unknown-rearm-prev")
    cur = replace(second, seq=111, request_id="unknown-rearm-fresh")
    p2, i2 = base._grants(owner, cur, eid)
    p2 = replace(p2, action_id="not-authorized-after-unknown")
    i2 = replace(i2, action_id="not-authorized-after-unknown")
    with pytest.raises(NormalActionRejected):
        owner.require_attack_authorizations(pre, cur, eid, p2, i2)
    assert len([x for x in session.sent if x[0] == "attack"]) == 1
