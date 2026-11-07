"""Offline original S49 ATTACK/EAT pre-ISSUE durability and native S16 checks.

Synthetic Mineflayer sessions only. No real World, provider, action or model.
The persistent fence NEVER asserts zombie death or independent World truth.
"""
from __future__ import annotations

import asyncio
import hashlib
import inspect
import json
from dataclasses import replace

import pytest

import test_bug0_s49_attack_owner as attack
import test_bug0_s49_s51_eat_handoff as eating
from adapters.mineflayer import attack_execution, normal_action
from adapters.mineflayer.eat_execution import EatingExecutionRejected
from adapters.mineflayer.normal_action import (
    NormalActionRejected,
    NormalSessionActionExecutor,
)
from relay_self.action import ActionState
from relay_self.c1_motion_journal import _canonical
from relay_self.s49_nonmotion_physical_fence import (
    NonmotionActionReplay,
    NonmotionActionUnknown,
    NonmotionFenceError,
    OriginalS49NonmotionFence,
)


def _attack_case(monkeypatch, path, *, broken=False):
    before, choice = attack._pair()
    owner = attack._owner(before)
    target = choice.snapshot.nearby_entities[0].entity_id
    propose, issue = attack._grants(owner, choice, target)
    if broken:
        class Native(attack.FakeNativeSession):
            async def send_attack_entity(self, action_id, *, entity_id):
                await super().send_attack_entity(action_id, entity_id=entity_id)
                self.frames[0] = replace(
                    self.frames[0], result="rejected", error="rejected-for-dev",
                )
    else:
        Native = attack.FakeNativeSession
    monkeypatch.setattr(normal_action, "MineflayerProcessSession", Native)
    monkeypatch.setattr(attack_execution, "MineflayerProcessSession", Native)
    session = Native(choice)
    fence = OriginalS49NonmotionFence.create(path, self_id="s49-original-self")
    return owner, session, before, choice, target, propose, issue, fence


def _attack_run(monkeypatch, path, *, broken=False):
    owner, session, before, choice, target, propose, issue, fence = (
        _attack_case(monkeypatch, path, broken=broken)
    )
    def reserve():
        fence.prepare_attack(
            session_id=owner.session_id, intent_id=owner.intent.current_intent.intent_id,
            action_id=propose.action_id, target_entity_id=target, probe=choice,
        )
    def close(receipt):
        fence.close_attack(receipt, choice, original_supervisor=owner.supervisor)
    return (
        owner, session, before, choice, target, propose, issue, fence, reserve, close,
    )


def _eat_run(path, *, consume_applied=True):
    before, choice, owner, _ = eating.fixture()
    propose, issue = eating.grants(
        before, choice, owner.intent.current_intent.intent_id,
    )
    native = eating.ScriptedNativeSession(
        before, propose.action_id, consume_applied=consume_applied,
    )
    fence = OriginalS49NonmotionFence.create(path, self_id="s49-original-self")
    def reserve():
        fence.prepare_eat(
            session_id=owner.session_id, intent_id=owner.intent.current_intent.intent_id,
            action_id=propose.action_id, choice=choice, probe=before,
        )
    def close(receipt):
        fence.close_eat(
            receipt, before, choice, original_supervisor=owner.supervisor,
        )
    return owner, native, before, choice, propose, issue, fence, reserve, close


def test_attack_s49_preissue_and_verified_native_ack_durably_reopen(monkeypatch, tmp_path):
    path = tmp_path / "nonmotion.json"
    owner, session, before, choice, target, propose, issue, fence, reserve, close = (
        _attack_run(monkeypatch, path)
    )
    receipt = asyncio.run(owner.execute_attack(
        session, before, choice, target, propose, issue,
        pre_issue_reservation=reserve, post_outcome_commit=close,
    ))
    assert receipt.terminal is owner.supervisor.get(propose.action_id)
    assert not fence.unresolved
    assert len(session.sent) == 2
    restored = OriginalS49NonmotionFence.restore(
        path, self_id="s49-original-self",
    )
    restored.require_clear()
    row = restored.actions[0]
    assert row["action_kind"] == "ATTACK"
    assert row["status"] == "S16_OUTCOME"
    assert row["target_entity_id"] == target
    assert row["effect_seq"] == choice.seq + 1
    assert row["after_seq"] == choice.seq + 3
    assert row["attack_effect_only"] is True
    assert row["food_after"] is None and row["count_after"] is None
    assert receipt.damage_attested is False
    assert receipt.target_death_attested is False
    with pytest.raises(NonmotionActionReplay):
        restored.prepare_attack(
            session_id=owner.session_id, intent_id=owner.intent.current_intent.intent_id,
            action_id=propose.action_id, target_entity_id=target, probe=choice,
        )


def test_eat_s49_s51_child_effects_durable_nutrition_not_inferred(monkeypatch, tmp_path):
    path = tmp_path / "nonmotion.json"
    owner, native, before, choice, propose, issue, fence, reserve, close = (
        _eat_run(path)
    )
    receipt = asyncio.run(owner.execute_eat(
        native, choice, before, propose, issue,
        previous_probe=eating.prior_probe(before),
        pre_issue_reservation=reserve, post_outcome_commit=close,
    ))
    assert receipt.terminal is owner.supervisor.get(propose.action_id)
    assert receipt.before_probe is before
    assert receipt.equip_receipt.action_id == propose.action_id + "-equip"
    assert receipt.consume_receipt.action_id == propose.action_id + "-consume"
    assert receipt.after_probe.seq > receipt.consume_receipt.seq
    assert receipt.terminal.state is ActionState.OUTCOME
    assert native.commands == [
        ("equip", propose.action_id + "-equip", "bread"),
        ("consume", propose.action_id + "-consume"),
        ("observe", propose.action_id + "-after-eating-00"),
    ]
    new = OriginalS49NonmotionFence.restore(
        path, self_id="s49-original-self",
    )
    new.require_clear()
    row = new.actions[0]
    assert row["action_kind"] == "EAT"
    assert row["status"] == "S16_OUTCOME"
    assert row["food_before"] == 7.0 and row["food_after"] == 12.0
    assert row["count_before"] == 2 and row["count_after"] == 1
    assert row["attack_effect_only"] is False
    assert row["effect_seq"] < row["consume_seq"] < row["after_seq"]


def test_attack_source_failure_remains_prepared_and_blocks_restart(monkeypatch, tmp_path):
    path = tmp_path / "attack-unknown.json"
    owner, session, before, choice, target, propose, issue, fence, reserve, close = (
        _attack_run(monkeypatch, path, broken=True)
    )
    with pytest.raises(Exception):
        asyncio.run(owner.execute_attack(
            session, before, choice, target, propose, issue,
            pre_issue_reservation=reserve, post_outcome_commit=close,
        ))
    assert len(session.sent) >= 1
    assert owner.supervisor.get(propose.action_id).state is ActionState.UNKNOWN
    assert fence.unresolved
    restarted = OriginalS49NonmotionFence.restore(
        path, self_id="s49-original-self",
    )
    with pytest.raises(NonmotionActionUnknown, match="STOP/UNKNOWN"):
        restarted.require_clear()
    with pytest.raises(NonmotionActionUnknown):
        restarted.prepare_attack(
            session_id=owner.session_id, intent_id=owner.intent.current_intent.intent_id,
            action_id="a-different-action", target_entity_id=target, probe=choice,
        )


def test_eat_rejected_consume_remains_prepared_and_no_auto_retry(tmp_path):
    path = tmp_path / "eat-unknown.json"
    owner, session, before, choice, propose, issue, fence, reserve, close = (
        _eat_run(path, consume_applied=False)
    )
    with pytest.raises(EatingExecutionRejected):
        asyncio.run(owner.execute_eat(
            session, choice, before, propose, issue,
            previous_probe=eating.prior_probe(before),
            pre_issue_reservation=reserve, post_outcome_commit=close,
        ))
    assert owner.supervisor.get(propose.action_id).state is ActionState.UNKNOWN
    assert fence.unresolved
    assert len(session.commands) == 2
    with pytest.raises(NonmotionActionUnknown):
        OriginalS49NonmotionFence.restore(
            path, self_id="s49-original-self",
        ).require_clear()


def test_failed_preissue_fsync_emits_no_attack_or_eat(monkeypatch, tmp_path):
    import relay_self.s49_nonmotion_physical_fence as module
    for mode in ("attack", "eat"):
        folder = tmp_path / mode
        folder.mkdir()
        if mode == "attack":
            (
                owner, native, before, choice, target, propose, issue,
                fence, reserve, close,
            ) = _attack_run(monkeypatch, folder / "fence.json")
            async def run():
                return await owner.execute_attack(
                    native, before, choice, target, propose, issue,
                    pre_issue_reservation=reserve, post_outcome_commit=close,
                )
        else:
            # The preceding ATTACK fixture replaced the S49 live-session
            # type guard; restore the original class for the S51 fixture.
            monkeypatch.setattr(
                normal_action, "MineflayerProcessSession",
                eating.MineflayerProcessSession,
            )
            owner, native, before, choice, propose, issue, fence, reserve, close = (
                _eat_run(folder / "fence.json")
            )
            async def run():
                return await owner.execute_eat(
                    native, choice, before, propose, issue,
                    previous_probe=eating.prior_probe(before),
                    pre_issue_reservation=reserve, post_outcome_commit=close,
                )
        original_write = module._write
        def fault(*args, **kwargs):
            raise OSError("simulated durable fsync failure")
        monkeypatch.setattr(module, "_write", fault)
        with pytest.raises(OSError, match="simulated durable fsync"):
            asyncio.run(run())
        monkeypatch.setattr(module, "_write", original_write)
        assert fence.actions == ()
        assert owner._dispatched == set()
        assert owner._count == 0
        assert owner.supervisor.open_actions == ()
        assert native.sent == [] if mode == "attack" else native.commands == []
        assert OriginalS49NonmotionFence.restore(
            fence.path, self_id="s49-original-self",
        ).actions == ()


@pytest.mark.parametrize("bad", ["attack-target", "attack-ack", "attack-copy",
                                  "eat-consume", "eat-outcome", "eat-copy"])
def test_forged_or_incomplete_S16_never_closes_durable_ledger(
    monkeypatch, tmp_path, bad,
):
    path = tmp_path / "nonmotion.json"
    if bad.startswith("attack"):
        owner, session, before, probe, target, propose, issue, fence, reserve, _ = (
            _attack_run(monkeypatch, path)
        )
        receipt = asyncio.run(owner.execute_attack(
            session, before, probe, target, propose, issue,
            pre_issue_reservation=reserve,
            post_outcome_commit=lambda _r: None,
        ))
        if bad == "attack-target":
            receipt = replace(receipt, target_entity_id=target + 1)
        elif bad == "attack-ack":
            receipt = replace(receipt, effect=replace(
                receipt.effect, effect="clear_controls",
            ))
        else:
            receipt = replace(receipt, terminal=replace(receipt.terminal))
        with pytest.raises(NonmotionFenceError):
            fence.close_attack(receipt, probe, original_supervisor=owner.supervisor)
    else:
        owner, session, before, choice, propose, issue, fence, reserve, _ = (
            _eat_run(path)
        )
        receipt = asyncio.run(owner.execute_eat(
            session, choice, before, propose, issue,
            previous_probe=eating.prior_probe(before),
            pre_issue_reservation=reserve,
            post_outcome_commit=lambda _r: None,
        ))
        if bad == "eat-consume":
            receipt = replace(receipt, consume_receipt=replace(
                receipt.consume_receipt, effect="attack_entity",
            ))
        elif bad == "eat-outcome":
            receipt = replace(receipt, outcome=replace(
                receipt.outcome, food_after=receipt.outcome.food_before,
            ))
        else:
            receipt = replace(receipt, terminal=replace(receipt.terminal))
        with pytest.raises(NonmotionFenceError):
            fence.close_eat(
                receipt, before, choice, original_supervisor=owner.supervisor,
            )
    assert OriginalS49NonmotionFence.restore(
        path, self_id="s49-original-self",
    ).unresolved


@pytest.mark.parametrize("bad", ["payload", "signature", "forged-status",
                                  "duplicate-action", "source-replay", "food-invalid"])
def test_nonmotion_corruption_or_duplicate_rejected_on_restart(monkeypatch, tmp_path, bad):
    path = tmp_path / "physical.json"
    owner, native, before, choice, target, propose, issue, fence, reserve, close = (
        _attack_run(monkeypatch, path)
    )
    asyncio.run(owner.execute_attack(
        native, before, choice, target, propose, issue,
        pre_issue_reservation=reserve, post_outcome_commit=close,
    ))
    packet = json.loads(path.read_text(encoding="utf8"))
    row = packet["body"]["actions"][0]
    if bad == "payload":
        path.write_text("{broken", encoding="utf8")
    else:
        if bad == "signature":
            row["target_entity_id"] += 1
        elif bad == "forged-status":
            row["status"] = "SUCCESS_PAPER_KILL"
        elif bad == "duplicate-action":
            packet["body"]["actions"].append(dict(row))
        elif bad == "source-replay":
            packet["body"]["actions"].append({
                **row, "action_id": row["action_id"] + "-new",
            })
        elif bad == "food-invalid":
            row["food_before"] = 12
        if bad != "signature":
            packet["sha256"] = hashlib.sha256(
                _canonical(packet["body"]),
            ).hexdigest()
        path.write_text(json.dumps(packet), encoding="utf8")
    with pytest.raises(NonmotionFenceError):
        OriginalS49NonmotionFence.restore(
            path, self_id="s49-original-self",
        )


def test_concurrent_stale_writer_and_foreign_self_fail_closed(monkeypatch, tmp_path):
    path = tmp_path / "physical.json"
    owner, native, before, choice, target, propose, issue, fence, reserve, close = (
        _attack_run(monkeypatch, path)
    )
    stale = OriginalS49NonmotionFence.restore(path, self_id="s49-original-self")
    asyncio.run(owner.execute_attack(
        native, before, choice, target, propose, issue,
        pre_issue_reservation=reserve, post_outcome_commit=close,
    ))
    with pytest.raises(NonmotionActionReplay):
        stale.prepare_attack(
            session_id=owner.session_id, intent_id=owner.intent.current_intent.intent_id,
            action_id="new-action-stale-writer", target_entity_id=target,
            probe=replace(choice, seq=choice.seq + 20, request_id="new-native"),
        )
    with pytest.raises(NonmotionFenceError):
        OriginalS49NonmotionFence.restore(path, self_id="some-other-Self")
    with pytest.raises(NonmotionActionReplay):
        OriginalS49NonmotionFence.create(path, self_id="s49-original-self")


def test_original_attacking_and_eating_callbacks_are_optin_and_before_issue():
    cls = NormalSessionActionExecutor
    for method in (cls.execute_attack, cls.execute_eat):
        params = inspect.signature(method).parameters
        assert params["pre_issue_reservation"].default is None
        assert params["post_outcome_commit"].default is None
        source = inspect.getsource(method)
        assert source.index("pre_issue_reservation()") < source.index(
            "issued = self.supervisor.issue(",
        )
        assert source.index("post_outcome_commit(receipt)") > source.index(
            "await Issued",
        )


def test_single_unpaired_callback_denied_before_any_world_io(monkeypatch, tmp_path):
    owner, session, before, probe, target, propose, issue, fence, reserve, close = (
        _attack_run(monkeypatch, tmp_path / "attack.json")
    )
    with pytest.raises(NormalActionRejected):
        asyncio.run(owner.execute_attack(
            session, before, probe, target, propose, issue,
            pre_issue_reservation=reserve,
        ))
    assert owner._count == 0 and not session.sent and not fence.actions
    owner, native, before, choice, propose, issue, fence, reserve, close = (
        _eat_run(tmp_path / "eat.json")
    )
    with pytest.raises(NormalActionRejected):
        asyncio.run(owner.execute_eat(
            native, choice, before, propose, issue,
            previous_probe=eating.prior_probe(before),
            post_outcome_commit=close,
        ))
    assert owner._count == 0 and not native.commands and not fence.actions



def test_d5_unresolved_nonmotion_action_blocks_before_paper_world(
    monkeypatch, tmp_path,
):
    from tools.bug0_d4_oneworld import run

    before, admitted = attack._pair()
    physical = OriginalS49NonmotionFence.create(
        tmp_path / "s49_nonmotion_physical_fence.json",
        self_id="s49-original-self",
    )
    physical.prepare_attack(
        session_id=admitted.session_id, intent_id="escape-threat",
        action_id="interrupted-d5-real-attack", probe=admitted,
        target_entity_id=admitted.snapshot.nearby_entities[0].entity_id,
    )
    assert physical.unresolved
    monkeypatch.setenv("S49_REAL_SERVER_CI", "1")
    monkeypatch.setenv("BUG0_S49_D4_ONE_WORLD_ONLY", "1")
    monkeypatch.setenv("BUG0_S49_NONMOTION_FENCE_DEV_ONLY", "1")
    monkeypatch.delenv("NODE_OPTIONS", raising=False)
    report_file = tmp_path / "blocked-original-report.json"
    server_log = tmp_path / "minecraft-never-created.log"
    rc = asyncio.run(run(
        report_file, server_log, nonmotion_fence_dev=True,
    ))
    report = json.loads(report_file.read_text(encoding="utf8"))
    assert rc == 2
    assert report["status"] == "BLOCKED"
    assert report["classification"] == "D5_NONMOTION_FENCE_BLOCKED_PREWORLD"
    assert "STOP/UNKNOWN" in report["failure"]
    assert report.get("real_world_started") is not True
    assert report["s49_actions"] == []
    assert report["cleanup_done"] is True
    assert not server_log.exists()
    assert OriginalS49NonmotionFence.restore(
        physical.path, self_id="s49-original-self",
    ).unresolved


def test_d5_nonmotion_gate_cannot_provision_world_without_distinct_DEV_grant(
    monkeypatch, tmp_path,
):
    from tools.bug0_d4_oneworld import run

    monkeypatch.setenv("S49_REAL_SERVER_CI", "1")
    monkeypatch.setenv("BUG0_S49_D4_ONE_WORLD_ONLY", "1")
    monkeypatch.delenv("BUG0_S49_NONMOTION_FENCE_DEV_ONLY", raising=False)
    monkeypatch.delenv("NODE_OPTIONS", raising=False)
    report_file = tmp_path / "ungranted-report.json"
    server_log = tmp_path / "server-never-created.log"
    rc = asyncio.run(run(
        report_file, server_log, nonmotion_fence_dev=True,
    ))
    report = json.loads(report_file.read_text(encoding="utf8"))
    assert rc == 2 and report["status"] == "BLOCKED"
    assert "separate ATTACK/EAT" in report["failure"]
    assert report.get("real_world_started") is not True
    assert not (tmp_path / "s49_nonmotion_physical_fence.json").exists()
    assert not server_log.exists()



@pytest.mark.parametrize("kind", ["ATTACK", "EAT"])
def test_s16_completed_but_durable_close_failed_keeps_PREPARED_unknown(
    monkeypatch, tmp_path, kind,
):
    path = tmp_path / "physical.json"
    def interrupted_commit(_receipt):
        raise OSError("simulated post-S16 journal commit interruption")
    if kind == "ATTACK":
        (
            owner, native, before, probe, target, propose, issue,
            fence, reserve, _,
        ) = _attack_run(monkeypatch, path)
        async def execute():
            return await owner.execute_attack(
                native, before, probe, target, propose, issue,
                pre_issue_reservation=reserve,
                post_outcome_commit=interrupted_commit,
            )
    else:
        owner, native, before, choice, propose, issue, fence, reserve, _ = (
            _eat_run(path)
        )
        async def execute():
            return await owner.execute_eat(
                native, choice, before, propose, issue,
                previous_probe=eating.prior_probe(before),
                pre_issue_reservation=reserve,
                post_outcome_commit=interrupted_commit,
            )
    with pytest.raises(OSError, match="post-S16"):
        asyncio.run(execute())
    assert owner.supervisor.get(propose.action_id).state is ActionState.OUTCOME
    assert owner.supervisor.open_actions == ()
    assert len(native.sent if kind == "ATTACK" else native.commands) > 0
    assert fence.unresolved
    with pytest.raises(NonmotionActionUnknown):
        OriginalS49NonmotionFence.restore(
            path, self_id="s49-original-self",
        ).require_clear()


def test_d5_2_original_intent_acks_share_one_nonmotion_fence_and_supervisor(
    monkeypatch, tmp_path,
):
    """D5 native-target next-generation rearm, not second physical World."""
    from test_bug0_d5_intent_epoch_rearm import _completed, _new_native
    from adapters.mineflayer.normal_action import NormalSessionActionExecutor

    first, second = attack._pair()
    owner = NormalSessionActionExecutor(
        first.session_id, attack._owner(first).intent,
        max_sequential_attacks=1, max_intent_epochs=2,
    )
    monkeypatch.setattr(normal_action, "MineflayerProcessSession", attack.FakeNativeSession)
    monkeypatch.setattr(attack_execution, "MineflayerProcessSession", attack.FakeNativeSession)
    native = attack.FakeNativeSession(second)
    target = second.snapshot.nearby_entities[0].entity_id
    propose, issue = attack._grants(owner, second, target)
    physical = OriginalS49NonmotionFence.create(
        tmp_path / "fence.json", self_id="s49-original-self",
    )
    original_supervisor = owner.supervisor
    first_receipt = asyncio.run(owner.execute_attack(
        native, first, second, target, propose, issue,
        pre_issue_reservation=lambda: physical.prepare_attack(
            session_id=owner.session_id, intent_id="escape-threat",
            action_id=propose.action_id, target_entity_id=target, probe=second,
        ),
        post_outcome_commit=lambda receipt: physical.close_attack(
            receipt, second, original_supervisor=owner.supervisor,
        ),
    ))
    assert physical.actions[0]["status"] == "S16_OUTCOME"
    old_action = first_receipt.terminal
    _completed(owner)
    reborn = _new_native(second, seq=140)
    handoff = owner.advance_intent_epoch(
        reborn, previous_zombie_entity_id=target,
    )
    assert handoff.next_epoch == 2 and owner.supervisor is original_supervisor
    previous = replace(reborn, seq=141, request_id="d5-prev-native")
    current = replace(reborn, seq=142, request_id="d5-next-native")
    native.before = current
    new_target = current.snapshot.nearby_entities[0].entity_id
    next_propose, next_issue = attack._grants(owner, current, new_target)
    next_propose = replace(next_propose, action_id="second-d5-attack")
    next_issue = replace(next_issue, action_id="second-d5-attack")
    next_receipt = asyncio.run(owner.execute_attack(
        native, previous, current, new_target, next_propose, next_issue,
        pre_issue_reservation=lambda: physical.prepare_attack(
            session_id=owner.session_id,
            intent_id=owner.intent.current_intent.intent_id,
            action_id=next_propose.action_id,
            target_entity_id=new_target, probe=current,
        ),
        post_outcome_commit=lambda receipt: physical.close_attack(
            receipt, current, original_supervisor=owner.supervisor,
        ),
    ))
    assert next_receipt.terminal.state is ActionState.OUTCOME
    assert owner.supervisor is original_supervisor
    assert owner.supervisor.get(propose.action_id) is old_action
    assert owner.supervisor.get(next_propose.action_id) is next_receipt.terminal
    fresh = OriginalS49NonmotionFence.restore(
        physical.path, self_id="s49-original-self",
    )
    fresh.require_clear()
    assert [row["action_id"] for row in fresh.actions] == [
        propose.action_id, next_propose.action_id,
    ]
    assert [row["intent_id"] for row in fresh.actions] == [
        "escape-threat", "d5-epoch2",
    ]
    assert [row["decision_seq"] for row in fresh.actions] == [
        second.seq, current.seq,
    ]
    assert [row["status"] for row in fresh.actions] == [
        "S16_OUTCOME", "S16_OUTCOME",
    ]
    assert next_receipt.damage_attested is False
    assert next_receipt.target_death_attested is False
