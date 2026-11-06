"""D5 DEV-only two Intent epochs under ONE original S49 physical Action owner.

Uses FakeNativeSession only. No Paper World, real actions, real EAT or claims
of long-term survival; rearm requires independently closed first Intent.
"""
from __future__ import annotations

import asyncio
from dataclasses import replace

import pytest

import test_bug0_s49_attack_owner as base
from adapters.mineflayer import attack_execution, normal_action
from adapters.mineflayer.normal_action import (
    NormalActionRejected,
    NormalSessionActionExecutor,
)
from relay_self.action import ActionState
from relay_self.intent import IntentEventKind
from relay_self.provenance import Provenance


def _new_native(old, *, next_id=None, seq=140):
    mob = old.snapshot.nearby_entities[0]
    new_id = mob.entity_id + 1 if next_id is None else next_id
    new_mob = replace(mob, entity_id=new_id)
    return replace(
        old, seq=seq, request_id=f"d5-next-generation-{seq}",
        snapshot=replace(
            old.snapshot, nearby_entities=(new_mob,),
            nearby_entities_coverage=replace(
                old.snapshot.nearby_entities_coverage,
                candidate_count=1, truncated=False,
            ),
        ),
    )


def _completed(owner):
    old_id = owner.intent.current_intent.intent_id
    owner.intent.complete(
        old_id, reason="closed original S49 Action OUTCOMEs and observed next epoch",
        at_ns=2, provenance=Provenance("test-d5-owner", "completed"),
    )
    owner.intent.commit(
        "d5-epoch2", objective="second bounded zombie encounter",
        at_ns=3, provenance=Provenance("test-d5-owner", "second-intent"),
    )
    assert owner.intent.events[-2].kind is IntentEventKind.COMPLETED
    return old_id


def _first(monkeypatch, *, max_intent_epochs=2):
    first, second = base._pair()
    owner = NormalSessionActionExecutor(
        first.session_id, base._owner(first).intent,
        max_sequential_attacks=1, max_intent_epochs=max_intent_epochs,
    )
    native = base.FakeNativeSession(second)
    monkeypatch.setattr(normal_action, "MineflayerProcessSession", base.FakeNativeSession)
    monkeypatch.setattr(attack_execution, "MineflayerProcessSession", base.FakeNativeSession)
    eid = second.snapshot.nearby_entities[0].entity_id
    propose, issue = base._grants(owner, second, eid)
    receipt = asyncio.run(owner.execute_attack(
        native, first, second, eid, propose, issue,
    ))
    assert receipt.terminal.state is ActionState.OUTCOME
    assert owner._count == owner._attack_count == 1
    assert owner.supervisor.open_actions == ()
    return owner, native, first, second, eid, propose, issue


def test_original_s49_owner_reuses_same_supervisor_across_two_intents(monkeypatch):
    owner, native, _, before, eid, old_propose, old_issue = _first(monkeypatch)
    supervisor = owner.supervisor
    first_action = owner.supervisor.get(old_propose.action_id)
    old_intent = _completed(owner)
    reborn = _new_native(before)
    with pytest.raises(NormalActionRejected):
        owner.require_attack_authorizations(
            reborn, replace(reborn, seq=141, request_id="unarmed-new-intent"),
            eid + 1, old_propose, old_issue,
        )
    rearm = owner.advance_intent_epoch(
        reborn, previous_zombie_entity_id=eid,
    )
    assert rearm.session_id == owner.session_id
    assert rearm.completed_intent_id == old_intent
    assert rearm.next_intent_id == owner.intent.current_intent.intent_id
    assert rearm.next_epoch == 2
    assert rearm.previous_zombie_entity_id == eid
    assert rearm.next_zombie_entity_id == eid + 1
    assert rearm.physically_issued is False
    assert owner.supervisor is supervisor
    assert owner.supervisor.get(old_propose.action_id) is first_action
    assert owner._count == 1 and owner._attack_count == 1
    assert owner._epoch_attack_count == 0
    with pytest.raises(NormalActionRejected):
        owner.advance_intent_epoch(reborn, previous_zombie_entity_id=eid)

    previous = replace(reborn, seq=141, request_id="d5-prev-new-generation")
    current = replace(reborn, seq=142, request_id="d5-fresh-new-generation")
    native.before = current
    p2, i2 = base._grants(owner, current, eid + 1)
    p2 = replace(p2, action_id="d5-original-owner-second-intent-attack")
    i2 = replace(i2, action_id=p2.action_id)
    r2 = asyncio.run(owner.execute_attack(
        native, previous, current, eid + 1, p2, i2,
    ))
    assert r2.terminal.state is ActionState.OUTCOME
    assert owner.supervisor is supervisor
    assert owner._count == owner._attack_count == 2
    assert owner._epoch_attack_count == 1
    assert owner._dispatched == {old_propose.action_id, p2.action_id}
    assert all(
        owner.supervisor.get(id).state is ActionState.OUTCOME
        for id in owner._dispatched
    )
    assert len([e for e in native.sent if e[0] == "attack"]) == 2
    third = replace(current, seq=143, request_id="new-same-intent-strike")
    p3, i3 = base._grants(owner, third, eid + 1)
    p3 = replace(p3, action_id="not-eligible-same-intent-third")
    i3 = replace(i3, action_id=p3.action_id)
    with pytest.raises(NormalActionRejected):
        owner.require_attack_authorizations(current, third, eid + 1, p3, i3)


@pytest.mark.parametrize("invalid", [0, -1, 5, True, 1.1, "2"])
def test_intent_epoch_budget_is_explicit_bounded_not_implicit(invalid):
    first, _ = base._pair()
    with pytest.raises(NormalActionRejected):
        NormalSessionActionExecutor(
            first.session_id, base._owner(first).intent, max_intent_epochs=invalid,
        )


def test_default_one_intent_owner_cannot_rearm(monkeypatch):
    owner, _, _, before, eid, _, _ = _first(
        monkeypatch, max_intent_epochs=1,
    )
    _completed(owner)
    with pytest.raises(NormalActionRejected):
        owner.advance_intent_epoch(
            _new_native(before), previous_zombie_entity_id=eid,
        )


@pytest.mark.parametrize("invalid", [
    "no-completion", "old-entity", "no-entity", "foreign-session",
    "stale-source", "truncated", "invalid-health", "invalid-oxygen",
    "wrong-previous-id", "missing-request", "no-owner-action",
])
def test_new_intent_cannot_reset_old_action_safety(monkeypatch, invalid):
    owner, _, _, before, eid, _, _ = _first(monkeypatch)
    if invalid != "no-completion":
        _completed(owner)
    fresh = _new_native(before)
    kw = dict(previous_zombie_entity_id=eid)
    if invalid == "old-entity":
        fresh = _new_native(before, next_id=eid)
    elif invalid == "no-entity":
        fresh = replace(fresh, snapshot=replace(
            fresh.snapshot,
            nearby_entities=(),
            nearby_entities_coverage=replace(
                fresh.snapshot.nearby_entities_coverage, candidate_count=0,
            ),
        ))
    elif invalid == "foreign-session":
        fresh = replace(fresh, session_id="foreign")
    elif invalid == "stale-source":
        fresh = replace(fresh, seq=100)
    elif invalid == "truncated":
        candidates = tuple(
            replace(fresh.snapshot.nearby_entities[0], entity_id=eid + j)
            for j in range(17)
        )
        fresh = replace(fresh, snapshot=replace(
            fresh.snapshot,
            nearby_entities=candidates[:16],
            nearby_entities_coverage=replace(
                fresh.snapshot.nearby_entities_coverage,
                candidate_count=17, truncated=True,
            ),
        ))
    elif invalid == "invalid-health":
        fresh = replace(fresh, snapshot=replace(fresh.snapshot, health=0))
    elif invalid == "invalid-oxygen":
        fresh = replace(fresh, snapshot=replace(fresh.snapshot, oxygen_level=0))
    elif invalid == "wrong-previous-id":
        kw["previous_zombie_entity_id"] = eid + 1
    elif invalid == "missing-request":
        fresh = replace(fresh, request_id=None)
    elif invalid == "no-owner-action":
        owner._epoch_action_count_start = owner._count
    with pytest.raises(NormalActionRejected):
        owner.advance_intent_epoch(fresh, **kw)
    assert owner._intent_epoch == 1
    assert owner._epoch_attack_count == 1


def test_uncertain_original_attacked_action_blocks_new_intent_rearm(monkeypatch):
    first, second = base._pair()

    class RejectedNative(base.FakeNativeSession):
        async def send_attack_entity(self, action_id, *, entity_id):
            await super().send_attack_entity(action_id, entity_id=entity_id)
            self.frames[0] = replace(
                self.frames[0], result="rejected", error="entity_not_found",
            )

    owner = NormalSessionActionExecutor(
        first.session_id, base._owner(first).intent, max_intent_epochs=2,
    )
    native = RejectedNative(second)
    monkeypatch.setattr(normal_action, "MineflayerProcessSession", RejectedNative)
    monkeypatch.setattr(attack_execution, "MineflayerProcessSession", RejectedNative)
    eid = second.snapshot.nearby_entities[0].entity_id
    propose, issue = base._grants(owner, second, eid)
    with pytest.raises(Exception):
        asyncio.run(owner.execute_attack(
            native, first, second, eid, propose, issue,
        ))
    assert owner.supervisor.get(propose.action_id).state is ActionState.UNKNOWN
    assert owner.supervisor.open_actions == ()
    _completed(owner)
    with pytest.raises(NormalActionRejected):
        owner.advance_intent_epoch(
            _new_native(second), previous_zombie_entity_id=eid,
        )
    assert owner._intent_epoch == 1
