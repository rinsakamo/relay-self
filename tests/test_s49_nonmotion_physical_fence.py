"""Offline original S49 ATTACK/EAT physical PRE-ISSUE fence tests.

Uses typed scripted Mineflayer frames, NEVER a live Minecraft World.
"""
from __future__ import annotations

import asyncio
import hashlib
import json

import pytest

import test_bug0_s49_attack_owner as attack
import test_bug0_s49_s51_eat_handoff as eat
from adapters.mineflayer import attack_execution, normal_action
from adapters.mineflayer.eat_execution import EatingActionReceipt
from relay_self.action import ActionState
from relay_self.c1_motion_journal import _canonical
from relay_self.s49_nonmotion_physical_fence import (
    NonMotionFenceError,
    NonMotionReplay,
    NonMotionUnresolved,
    OriginalS49NonMotionFence,
)


def _fence(path, *, self_id="s49-original-self"):
    return OriginalS49NonMotionFence.create(path, self_id=self_id)


def _attack(monkeypatch, path, *, fence=None):
    before, selected = attack._pair()
    owner = attack._owner(before)
    native = attack.FakeNativeSession(selected)
    monkeypatch.setattr(normal_action, "MineflayerProcessSession", attack.FakeNativeSession)
    monkeypatch.setattr(attack_execution, "MineflayerProcessSession", attack.FakeNativeSession)
    mob_id = selected.snapshot.nearby_entities[0].entity_id
    propose, issue = attack._grants(owner, selected, mob_id)
    fence = fence or _fence(path)
    result = asyncio.run(owner.execute_attack(
        native, before, selected, mob_id, propose, issue,
        physical_fence=fence,
    ))
    return owner, selected, result, fence, native, propose


def test_attack_preissue_original_s16_native_ack_persisted(monkeypatch, tmp_path):
    path = tmp_path / "attack-eat.json"
    owner, before, receipt, fence, native, grant = _attack(monkeypatch, path)
    assert receipt.terminal is owner.supervisor.get(grant.action_id)
    assert receipt.terminal.state is ActionState.OUTCOME
    assert len([x for x in native.sent if x[0] == "attack"]) == 1
    assert not fence.unresolved
    original = OriginalS49NonMotionFence.restore(path, self_id="s49-original-self")
    original.require_clear()
    assert original.actions == fence.actions
    a = original.actions[0]
    assert a["kind"] == "ATTACK" and a["status"] == "S16_OUTCOME"
    assert a["action_id"] == grant.action_id
    assert a["effect_seqs"] == [receipt.effect.seq]
    assert a["after_seq"] == receipt.after_probe.seq
    assert a["result"]["death_attested"] is False
    with pytest.raises(NonMotionReplay):
        original.prepare_attack(
            probe=before, intent_id=grant.intent_id,
            action_id=grant.action_id, target_entity_id=a["subject"],
        )
    with pytest.raises(NonMotionFenceError):
        OriginalS49NonMotionFence.restore(path, self_id="foreign-self")


def test_eat_preissue_original_two_child_effects_persisted(tmp_path):
    before, choice, owner, _ = eat.fixture()
    propose, issue = eat.grants(
        before, choice, owner.intent.current_intent.intent_id,
    )
    session = eat.ScriptedNativeSession(before, propose.action_id)
    fence = _fence(tmp_path / "eat.json")
    receipt = asyncio.run(owner.execute_eat(
        session, choice, before, propose, issue,
        previous_probe=eat.prior_probe(before), physical_fence=fence,
    ))
    assert receipt.terminal is owner.supervisor.get(propose.action_id)
    assert receipt.terminal.state is ActionState.OUTCOME
    assert receipt.equip_receipt.effect == "equip_item"
    assert receipt.consume_receipt.effect == "consume_held"
    loaded = OriginalS49NonMotionFence.restore(
        fence.path, self_id="s49-original-self",
    )
    loaded.require_clear()
    a = loaded.actions[0]
    assert a["status"] == "S16_OUTCOME" and a["kind"] == "EAT"
    assert a["subject"] == choice.item_name
    assert a["effect_seqs"] == [
        receipt.equip_receipt.seq, receipt.consume_receipt.seq,
    ]
    assert a["result"] == {
        "food_before": 7, "food_after": 12,
        "item_count_before": 2, "item_count_after": 1,
    }
    assert [x[0] for x in session.commands] == ["equip", "consume", "observe"]


def test_rejected_eat_consume_remains_unknown_and_restart_stops(tmp_path):
    before, choice, owner, _ = eat.fixture()
    propose, issue = eat.grants(
        before, choice, owner.intent.current_intent.intent_id,
    )
    session = eat.ScriptedNativeSession(
        before, propose.action_id, consume_applied=False,
    )
    fence = _fence(tmp_path / "eat-unknown.json")
    with pytest.raises(Exception):
        asyncio.run(owner.execute_eat(
            session, choice, before, propose, issue,
            previous_probe=eat.prior_probe(before), physical_fence=fence,
        ))
    assert owner.supervisor.get(propose.action_id).state is ActionState.UNKNOWN
    assert OriginalS49NonMotionFence.restore(
        fence.path, self_id="s49-original-self",
    ).unresolved
    with pytest.raises(NonMotionUnresolved):
        fence.require_clear()
    with pytest.raises(NonMotionUnresolved):
        fence.prepare_eat(
            probe=before, intent_id=propose.intent_id,
            action_id="other-action", food_item=choice.item_name,
        )


def test_invalid_attack_does_not_write_fence_or_issue(monkeypatch, tmp_path):
    first, selected = attack._pair()
    owner = attack._owner(first)
    native = attack.FakeNativeSession(selected)
    monkeypatch.setattr(normal_action, "MineflayerProcessSession", attack.FakeNativeSession)
    eid = selected.snapshot.nearby_entities[0].entity_id
    propose, issue = attack._grants(owner, selected, eid)
    fence = _fence(tmp_path / "invalid.json")
    with pytest.raises(normal_action.NormalActionRejected):
        asyncio.run(owner.execute_attack(
            native, first, selected, eid + 1, propose, issue,
            physical_fence=fence,
        ))
    assert fence.actions == ()
    assert owner._dispatched == set()


def test_attack_fence_failed_disk_write_never_calls_native(monkeypatch, tmp_path):
    from relay_self import s49_nonmotion_physical_fence as module

    first, selected = attack._pair()
    owner = attack._owner(first)
    native = attack.FakeNativeSession(selected)
    monkeypatch.setattr(normal_action, "MineflayerProcessSession", attack.FakeNativeSession)
    eid = selected.snapshot.nearby_entities[0].entity_id
    propose, issue = attack._grants(owner, selected, eid)
    fence = _fence(tmp_path / "iofail.json")
    def failed(*args, **kwargs):
        raise OSError("durable write failed before ISSUE")
    monkeypatch.setattr(module, "_write", failed)
    with pytest.raises(OSError, match="durable write failed"):
        asyncio.run(owner.execute_attack(
            native, first, selected, eid, propose, issue,
            physical_fence=fence,
        ))
    assert owner.supervisor.open_actions == ()
    assert owner._dispatched == set()
    assert not native.sent


def test_eat_failure_at_preissue_never_calls_native(monkeypatch, tmp_path):
    before, choice, owner, _ = eat.fixture()
    propose, issue = eat.grants(before, choice, owner.intent.current_intent.intent_id)
    session = eat.ScriptedNativeSession(before, propose.action_id)
    fence = _fence(tmp_path / "unresolved.json")
    fence.prepare_eat(
        probe=before, intent_id=propose.intent_id,
        action_id="old-uncertain", food_item=choice.item_name,
    )
    with pytest.raises(NonMotionUnresolved):
        asyncio.run(owner.execute_eat(
            session, choice, before, propose, issue,
            previous_probe=eat.prior_probe(before), physical_fence=fence,
        ))
    assert not session.commands
    assert owner._dispatched == set()


@pytest.mark.parametrize("mutation", [
    "bad_sha", "duplicate", "forged_effect", "fake_death",
    "bad_seq", "false_eat", "corrupt_json",
])
def test_corrupt_or_forged_fence_never_restores(monkeypatch, tmp_path, mutation):
    path = tmp_path / "fence.json"
    _attack(monkeypatch, path)
    if mutation == "corrupt_json":
        path.write_text("{", encoding="utf-8")
    else:
        env = json.loads(path.read_text(encoding="utf-8"))
        a = env["body"]["actions"][0]
        if mutation == "bad_sha":
            a["action_id"] = "tampered"
        elif mutation == "duplicate":
            env["body"]["actions"].append(a)
        elif mutation == "forged_effect":
            a["effect_seqs"].append(a["effect_seqs"][0] + 1)
        elif mutation == "fake_death":
            a["result"]["death_attested"] = True
        elif mutation == "bad_seq":
            a["after_seq"] = a["effect_seqs"][0]
        elif mutation == "false_eat":
            a["kind"] = "EAT"
        if mutation != "bad_sha":
            env["sha256"] = hashlib.sha256(
                _canonical(env["body"]),
            ).hexdigest()
        path.write_text(json.dumps(env), encoding="utf-8")
    with pytest.raises(NonMotionFenceError):
        OriginalS49NonMotionFence.restore(path, self_id="s49-original-self")


def test_original_owner_eat_receipt_without_child_evidence_cannot_seal(tmp_path):
    before, choice, owner, _ = eat.fixture()
    propose, issue = eat.grants(before, choice, owner.intent.current_intent.intent_id)
    session = eat.ScriptedNativeSession(before, propose.action_id)
    receipt = asyncio.run(owner.execute_eat(
        session, choice, before, propose, issue,
        previous_probe=eat.prior_probe(before),
    ))
    fence = _fence(tmp_path / "missing-native.json")
    fence.prepare_eat(
        probe=before, intent_id=propose.intent_id, action_id=propose.action_id,
        food_item=choice.item_name,
    )
    missing = EatingActionReceipt(receipt.terminal, receipt.outcome)
    with pytest.raises(NonMotionFenceError):
        fence.close_eat(
            receipt=missing, choice=choice, probe=before, supervisor=owner.supervisor,
        )
    assert OriginalS49NonMotionFence.restore(
        fence.path, self_id="s49-original-self",
    ).unresolved


def test_stale_writer_and_duplicate_restart_are_fail_closed(monkeypatch, tmp_path):
    path = tmp_path / "fence.json"
    fence = _fence(path)
    stale = OriginalS49NonMotionFence.restore(path, self_id="s49-original-self")
    before, selected = attack._pair()
    eid = selected.snapshot.nearby_entities[0].entity_id
    fence.prepare_attack(
        probe=selected, intent_id="escape-threat",
        action_id="original-strike", target_entity_id=eid,
    )
    with pytest.raises(NonMotionReplay):
        stale.prepare_attack(
            probe=selected, intent_id="escape-threat",
            action_id="foreign-strike", target_entity_id=eid,
        )
    restored = OriginalS49NonMotionFence.restore(path, self_id="s49-original-self")
    with pytest.raises(NonMotionUnresolved):
        restored.require_clear()
    with pytest.raises(NonMotionReplay):
        OriginalS49NonMotionFence.create(path, self_id="s49-original-self")
