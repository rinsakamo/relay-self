"""Bug-0 S49 ATTACK offline: source-bound original issuer, fail-closed effects.

All World/transport fixtures are synthetic. No physical combat claim.
"""
from __future__ import annotations

import asyncio
import json
from dataclasses import replace
from types import SimpleNamespace

import pytest

import test_bug0_s49_food_refusal_priority as cases
from adapters.mineflayer import (
    attack_execution,
    normal_action,
    s49_attack_dev,
)
from adapters.mineflayer import (
    s49_normal_session_real_ci as s49,
)
from adapters.mineflayer.attack_execution import (
    AttackExecutionRejected,
    verify_attack_effect,
)
from adapters.mineflayer.normal_action import (
    NormalActionRejected,
    NormalActionStage,
    NormalAttackingAuthorization,
    NormalSessionActionExecutor,
)
from adapters.mineflayer.python_protocol import (
    MineflayerEffectResult,
    MineflayerEntityHurt,
)
from relay_self.action import ActionState
from relay_self.intent import IntentCommitment
from relay_self.provenance import Provenance


def _owner(probe):
    intent = IntentCommitment()
    intent.commit(
        "escape-threat", objective="one bounded ATTACK fallback", at_ns=1,
        provenance=Provenance("test-s49-attack", "intent"),
    )
    return NormalSessionActionExecutor(probe.session_id, intent)


def _pair():
    p = cases.sample(food=20, seq=100, zombie=True)
    # The existing S42 native fixture has exactly one 2m zombie and
    # complete nearby registry coverage, same source native session.
    q = replace(p, seq=101, request_id="s49-attack-fresh-second")
    assert len(q.snapshot.nearby_entities) == 1
    assert q.snapshot.nearby_entities[0].name == "zombie"
    assert q.snapshot.nearby_entities[0].distance <= 2.8
    return p, q


def _grants(owner, probe, entity_id):
    fields = dict(
        intent_id=owner.intent.current_intent.intent_id,
        session_id=probe.session_id,
        action_id="test-s49-attack-action",
        probe_seq=probe.seq,
        probe_request_id=probe.request_id,
        target_entity_id=entity_id, granted=True,
    )
    return (
        NormalAttackingAuthorization(
            stage=NormalActionStage.PROPOSE, authority_id="operator-propose",
            provenance=Provenance("test-operator", "propose"), **fields,
        ),
        NormalAttackingAuthorization(
            stage=NormalActionStage.ISSUE, authority_id="operator-issue",
            provenance=Provenance("test-operator", "issue"), **fields,
        ),
    )


@pytest.mark.parametrize("bad", [
    "target-id", "foreign-session", "stale-probe", "same-request",
    "far-distance", "different-id", "wrong-issuer",
    "wrong-grant", "same-authority", "second-action", "moving-body",
    "moving-target", "truncated", "no-health", "unknown-entity",
])
def test_attack_denies_bad_native_source_or_authorization(bad):
    first, second = _pair()
    owner = _owner(first)
    eid = first.snapshot.nearby_entities[0].entity_id
    propose, issue = _grants(owner, second, eid)
    if bad == "target-id":
        eid += 5
    elif bad == "foreign-session":
        second = replace(second, session_id="foreign-session")
    elif bad == "stale-probe":
        second = replace(second, seq=first.seq)
    elif bad == "same-request":
        second = replace(second, request_id=first.request_id)
    elif bad == "far-distance":
        mob = second.snapshot.nearby_entities[0]
        second = replace(second, snapshot=replace(
            second.snapshot,
            nearby_entities=(replace(mob, distance=4.0),),
        ))
    elif bad == "different-id":
        mob = second.snapshot.nearby_entities[0]
        second = replace(second, snapshot=replace(
            second.snapshot,
            nearby_entities=(replace(mob, entity_id=eid + 1),),
        ))
    elif bad == "wrong-issuer":
        owner._post_move_settling_unqualified = True
    elif bad == "wrong-grant":
        issue = replace(issue, probe_seq=first.seq)
    elif bad == "same-authority":
        issue = replace(issue, authority_id=propose.authority_id)
    elif bad == "second-action":
        owner._count = 1
    elif bad == "moving-body":
        pos = second.snapshot.position
        second = replace(second, snapshot=replace(
            second.snapshot, position=replace(pos, x=pos.x + 0.1),
        ))
    elif bad == "moving-target":
        mob = second.snapshot.nearby_entities[0]
        second = replace(second, snapshot=replace(
            second.snapshot, nearby_entities=(replace(
                mob, position=replace(mob.position, x=mob.position.x + 0.3),
            ),),
        ))
    elif bad == "truncated":
        coverage = second.snapshot.nearby_entities_coverage
        mob = second.snapshot.nearby_entities[0]
        # A true native truncated registry carries 16 observed of 17
        # candidates. Fabricating one observed of 17 violates the protocol.
        second = replace(second, snapshot=replace(
            second.snapshot,
            nearby_entities=tuple(
                replace(mob, entity_id=mob.entity_id + i)
                for i in range(16)
            ),
            nearby_entities_coverage=replace(
                coverage, candidate_count=17, truncated=True,
            ),
        ))
    elif bad == "no-health":
        second = replace(second, snapshot=replace(second.snapshot, health=0))
    else:
        mob = second.snapshot.nearby_entities[0]
        second = replace(second, snapshot=replace(
            second.snapshot,
            nearby_entities=(replace(mob, name="cow"),),
        ))
    with pytest.raises(NormalActionRejected):
        owner.require_attack_authorizations(first, second, eid, propose, issue)
    assert owner._dispatched == set()
    assert owner.supervisor.open_actions == ()
    assert owner._count == (1 if bad == "second-action" else 0)


class FakeNativeSession:
    def __init__(self, before):
        self.started = SimpleNamespace(session_id=before.session_id)
        self.process_returncode = None
        self.before = before
        self.sent = []
        self.frames = []

    async def send_attack_entity(self, action_id, *, entity_id):
        assert entity_id == self.before.snapshot.nearby_entities[0].entity_id
        self.sent.append(("attack", action_id, entity_id))
        self.frames.extend([
            MineflayerEffectResult(
                self.before.session_id, self.before.seq + 1, action_id,
                "attack_entity", "applied", None,
            ),
            MineflayerEntityHurt(
                self.before.session_id, self.before.seq + 2,
                entity_id, None, 1,
            ),
        ])

    async def send_observe(self, request_id):
        self.sent.append(("observe", request_id))
        self.frames.append(replace(
            self.before, seq=self.before.seq + 3, request_id=request_id,
        ))

    async def receive(self):
        assert self.frames, "unexpected native protocol read"
        return self.frames.pop(0)


def test_actual_original_supervisor_path_mocked_transport_is_one_shot(monkeypatch):
    first, second = _pair()
    owner = _owner(first)
    eid = second.snapshot.nearby_entities[0].entity_id
    propose, issue = _grants(owner, second, eid)
    session = FakeNativeSession(second)
    monkeypatch.setattr(normal_action, "MineflayerProcessSession", FakeNativeSession)
    monkeypatch.setattr(attack_execution, "MineflayerProcessSession", FakeNativeSession)
    receipt = asyncio.run(owner.execute_attack(
        session, first, second, eid, propose, issue,
    ))
    assert receipt.terminal is owner.supervisor.get(propose.action_id)
    assert receipt.terminal.state is ActionState.OUTCOME
    assert owner._count == 1 and owner.supervisor.open_actions == ()
    assert receipt.effect.result == "applied"
    assert receipt.observed_target_hurt is True
    assert receipt.observed_hurt_source_entity_ids == (None,)
    assert receipt.damage_attested is False
    assert receipt.target_death_attested is False
    assert session.sent == [
        ("attack", propose.action_id, eid),
        ("observe", propose.action_id + "-after-attack"),
    ]
    with pytest.raises(NormalActionRejected):
        asyncio.run(owner.execute_attack(
            session, first, second, eid, propose, issue,
        ))
    assert len([x for x in session.sent if x[0] == "attack"]) == 1



def test_rejected_native_attack_marks_original_supervisor_unknown_no_replay(
    monkeypatch,
):
    first, second = _pair()
    owner = _owner(first)
    eid = second.snapshot.nearby_entities[0].entity_id
    propose, issue = _grants(owner, second, eid)

    class RejectedNativeSession(FakeNativeSession):
        async def send_attack_entity(self, action_id, *, entity_id):
            await super().send_attack_entity(action_id, entity_id=entity_id)
            self.frames[0] = replace(
                self.frames[0], result="rejected", error="entity_not_found",
            )

    session = RejectedNativeSession(second)
    monkeypatch.setattr(normal_action, "MineflayerProcessSession", RejectedNativeSession)
    monkeypatch.setattr(attack_execution, "MineflayerProcessSession", RejectedNativeSession)
    with pytest.raises(AttackExecutionRejected, match="not applied"):
        asyncio.run(owner.execute_attack(
            session, first, second, eid, propose, issue,
        ))
    assert owner.supervisor.get(propose.action_id).state is ActionState.UNKNOWN
    assert owner.supervisor.open_actions == ()
    assert owner._count == 1
    assert propose.action_id in owner._dispatched
    with pytest.raises(NormalActionRejected):
        asyncio.run(owner.execute_attack(
            session, first, second, eid, propose, issue,
        ))
    assert len([x for x in session.sent if x[0] == "attack"]) == 1


def test_native_effect_ack_is_not_damage_and_requires_fresh_target():
    first, second = _pair()
    entity_id = second.snapshot.nearby_entities[0].entity_id
    ack = MineflayerEffectResult(
        second.session_id, second.seq + 1, "attack-1",
        "attack_entity", "applied", None,
    )
    after = replace(second, seq=second.seq + 2, request_id="after-attack")
    verify_attack_effect(
        second, ack, after, action_id="attack-1", entity_id=entity_id,
    )
    with pytest.raises(AttackExecutionRejected):
        verify_attack_effect(
            second, replace(ack, result="rejected", error="not_found"),
            after, action_id="attack-1", entity_id=entity_id,
        )
    with pytest.raises(AttackExecutionRejected):
        verify_attack_effect(
            second, ack, replace(after, request_id=second.request_id),
            action_id="attack-1", entity_id=entity_id,
        )


def test_original_s49_attack_dev_driver_reaches_real_owner_without_extra_issuer(
    monkeypatch,
):
    first, second = _pair()
    owner = _owner(first)
    session = FakeNativeSession(second)

    class FakeStdin:
        async def drain(self):
            pass

    fake_server = SimpleNamespace(stdin=FakeStdin())
    sources = iter((first, second))
    commands = []

    async def read(_session, _req):
        return next(sources)

    async def no_sleep(_):
        pass

    monkeypatch.setattr(s49_attack_dev, "MineflayerProcessSession", FakeNativeSession)
    monkeypatch.setattr(normal_action, "MineflayerProcessSession", FakeNativeSession)
    monkeypatch.setattr(attack_execution, "MineflayerProcessSession", FakeNativeSession)
    monkeypatch.setattr(s49_attack_dev, "_correlated_observe", read)
    monkeypatch.setattr(s49_attack_dev, "_command", lambda _, command: commands.append(command))
    monkeypatch.setattr(s49_attack_dev.asyncio, "sleep", no_sleep)
    report = {}
    receipt = asyncio.run(s49_attack_dev.run_s49_attack_dev(
        session, fake_server, owner, report,
    ))
    assert receipt.terminal.state is ActionState.OUTCOME
    assert report["stage"] == "BUG0_S49_ATTACK_EFFECT_CLOSED"
    assert report["attack_effect_commands_issued"] == 1
    assert report["actual_native_actions"][0]["same_supervisor"] is True
    assert report["actual_native_actions"][0]["kind"] == "ATTACK"
    assert report["attack_evidence"]["damage_attested"] is False
    assert report["attack_evidence"]["outcome_scope"] == (
        "ATTACK_COMMAND_EFFECT_APPLIED_ONLY"
    )
    assert report["real_model_calls"] == 0
    assert report["learning_in_world"] is False
    assert report["m_energy_credited"] is False
    assert "kill @e[type=!minecraft:player]" in commands
    assert sum("summon minecraft:zombie" in x for x in commands) == 1
    assert len([x for x in session.sent if x[0] == "attack"]) == 1


@pytest.mark.parametrize("variant", [
    "missing-gate", "conflict-food", "conflict-unified",
    "conflict-refusal", "invalid-type",
])
def test_attack_optin_blocks_before_java(variant, monkeypatch, tmp_path):
    monkeypatch.setenv("S49_REAL_SERVER_CI", "1")
    monkeypatch.setenv("S49_BUG0_ATTACK_DEV_ONLY", "1")
    monkeypatch.delenv("NODE_OPTIONS", raising=False)
    monkeypatch.setattr(
        s49, "_fetch_official_server",
        lambda *_: (_ for _ in ()).throw(AssertionError("Java started")),
    )
    args = {"bug0_attack_dev": True}
    if variant == "missing-gate":
        monkeypatch.delenv("S49_BUG0_ATTACK_DEV_ONLY")
    elif variant == "conflict-food":
        args["bug0_food_loop_dev"] = True
    elif variant == "conflict-unified":
        args["bug0_unified_survival_dev"] = True
    elif variant == "conflict-refusal":
        args["bug0_food_refusal_dev"] = True
    else:
        args["bug0_attack_dev"] = "true"
    path = tmp_path / "attack-blocked.json"
    rc = asyncio.run(s49.qualify(
        path, tmp_path / "paper.log", **args,
    ))
    report = json.loads(path.read_text())
    assert rc == 2 and report["status"] == "BLOCKED"
    assert report["actual_native_actions"] == []
