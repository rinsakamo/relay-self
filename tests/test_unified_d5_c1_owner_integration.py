"""Offline owner-identity bridge for D5 #764 + C1 #763.

These fixtures prove co-resident modules and cross-owner fail-closed behavior,
not an integrated real-World ATTACK->MOVE->C1 learning or survival success.
"""
from __future__ import annotations

import inspect

import pytest

import test_bug0_d5_intent_epoch_rearm as d5
from adapters.mineflayer.bug0_intent_motion_learning import (
    forecast_from_retained,
)
from adapters.mineflayer.normal_action import (
    NormalActionRejected,
    NormalSessionActionExecutor,
)
from adapters.mineflayer.s49_c1_motion_owner_dev import S49C1MotionDevJoin
from relay_self.action import ActionState
from relay_self.c1_motion_journal import C1MotionJournal
from relay_self.c1_physical_action_fence import (
    OriginalS49PhysicalFence,
    UnresolvedPhysicalAction,
)
from relay_self.learning import LearningPreferenceState
from relay_self.provenance import Provenance


def _combined_owner_after_first_attack(monkeypatch, tmp_path, *, epoch_limit=2):
    owner, _, _, original, old_zombie_id, old_propose, _ = d5._first(
        monkeypatch, max_intent_epochs=epoch_limit,
    )
    original_supervisor = owner.supervisor
    original_terminal = owner.supervisor.get(old_propose.action_id)
    assert original_terminal.state is ActionState.OUTCOME
    assert owner._dispatched == {old_propose.action_id}
    assert owner._count == 1

    owner_id = "s49-original-self"
    seed = LearningPreferenceState(
        "motion_decimeters", 7, 0, 10, 0,
        Provenance("integration-offline", "seed-only-not-world"),
    )
    journal = C1MotionJournal.create(
        tmp_path / "c1_motion_journal.json", self_id=owner_id, seed=seed,
    )
    physical = OriginalS49PhysicalFence.create(
        tmp_path / "c1_physical_action_fence.json", self_id=owner_id,
    )
    # ATTACK has NOT been covered by this MOVE-only physical fence.
    assert physical.actions == ()
    assert journal.experience_ids == ()
    assert journal.state.revision == 0
    return (
        owner, original, old_zombie_id, old_propose.action_id,
        original_supervisor, original_terminal, journal, physical,
    )


def test_one_original_s49_owner_after_d5_attack_rearm_can_read_c1_s10(
    monkeypatch, tmp_path,
):
    (
        owner, original, old_zombie_id, original_action,
        same_supervisor, original_terminal, journal, physical,
    ) = _combined_owner_after_first_attack(monkeypatch, tmp_path)
    old_intent = d5._completed(owner)
    new_native = d5._new_native(original, seq=140)
    handoff = owner.advance_intent_epoch(
        new_native, previous_zombie_entity_id=old_zombie_id,
    )
    assert handoff.completed_intent_id == old_intent
    assert handoff.next_intent_id == owner.intent.current_intent.intent_id
    assert handoff.next_epoch == 2 and not handoff.physically_issued
    assert owner.supervisor is same_supervisor
    assert owner.supervisor.get(original_action) is original_terminal

    # C1, S10 and D5 reference the exact SAME original S49 owner; there is
    # no second ActionSupervisor, separate Action issuer or new authority.
    c1 = S49C1MotionDevJoin(
        owner.intent, owner, journal.state,
        self_id=journal.self_id, journal=journal,
    )
    assert c1.intent is owner.intent and c1.executor is owner
    forecast = forecast_from_retained(
        journal.state, c1.retained_motion,
        self_id=journal.self_id,
        intent_id=owner.intent.current_intent.intent_id,
        session_id=owner.session_id,
        native_probe_seq=new_native.seq,
        expected_revision=journal.state.revision,
        source_provenance=new_native.provenance,
    )
    assert forecast.predicted_total_m == 0.7
    assert forecast.owner_revision == 0

    # A future original source-bound MOVE reservation is durably prepared.
    # It is deliberately NOT issued by this offline test, so its state must
    # remain UNKNOWN and prohibit replay/restart.
    physical.prepare(
        session_id=owner.session_id,
        intent_id=owner.intent.current_intent.intent_id,
        action_id="future-move-not-issued-in-test", probe=new_native,
    )
    with pytest.raises(UnresolvedPhysicalAction):
        OriginalS49PhysicalFence.restore(
            physical.path, self_id=journal.self_id,
        ).require_clear()
    assert owner.supervisor is same_supervisor
    assert owner._dispatched == {original_action}
    assert owner._count == 1
    assert journal.state.revision == 0 and journal.experience_ids == ()


def test_d5_epoch_rearm_failure_does_not_forge_c1_or_physical_outcome(
    monkeypatch, tmp_path,
):
    (
        owner, original, old_id, original_action,
        supervisor, terminal, journal, physical,
    ) = _combined_owner_after_first_attack(
        monkeypatch, tmp_path, epoch_limit=1,
    )
    d5._completed(owner)
    with pytest.raises(NormalActionRejected):
        owner.advance_intent_epoch(
            d5._new_native(original), previous_zombie_entity_id=old_id,
        )
    assert owner.supervisor is supervisor
    assert owner.supervisor.get(original_action) is terminal
    assert physical.actions == ()
    assert journal.experience_ids == ()
    assert journal.state.revision == 0
    assert owner._count == 1


def test_merged_s49_executor_keeps_d5_rearm_and_c1_preissue_move_boundary():
    cls = NormalSessionActionExecutor
    assert "max_intent_epochs" in inspect.signature(cls.__init__).parameters
    assert callable(cls.advance_intent_epoch)
    move = inspect.signature(cls.execute).parameters
    assert move["pre_issue_reservation"].default is None
    # This v0 physical fence applies to MOVE only; not to D5's ATTACK or
    # S51 EAT. Never imply cross-Action-kind crash protection.
    assert "pre_issue_reservation" not in inspect.signature(
        cls.execute_attack,
    ).parameters
    assert "pre_issue_reservation" not in inspect.signature(
        cls.execute_eat,
    ).parameters
    original_source = inspect.getsource(cls.execute)
    assert original_source.index("pre_issue_reservation()") < (
        original_source.index("issued = self.supervisor.issue(")
    )
    assert original_source.index("issued = self.supervisor.issue(") < (
        original_source.index("await execute_mineflayer_command(")
    )



def test_d5_real_owner_2nd_epoch_motion_c1_persists_only_move_feedback(
    monkeypatch, tmp_path,
):
    """One ORIGINAL supervisor ATTACK -> D5 rearm -> typed synthetic MOVE
    -> C1/S10 commit, all under one owner. No live World/physical MOVE here.
    """
    from dataclasses import replace

    from adapters.mineflayer.normal_action import NormalActionReceipt
    from relay_self.action import ActionLifecycle
    from relay_self.c1_motion_journal import C1MotionJournal
    from relay_self.reactive_l0 import L0Step
    from relay_self.skill import SkillExecution
    from test_s49_c1_motion_owner_dev import _joined_original_owner

    (
        executor, native, prior_zombie, old_action,
        same_supervisor, old_terminal, journal, physical,
    ) = _combined_owner_after_first_attack(monkeypatch, tmp_path)
    old_intent = d5._completed(executor)
    fresh = d5._new_native(native, seq=140)
    handoff = executor.advance_intent_epoch(
        fresh, previous_zombie_entity_id=prior_zombie,
    )
    assert handoff.completed_intent_id == old_intent
    assert handoff.next_intent_id == executor.intent.current_intent.intent_id
    assert executor.supervisor is same_supervisor
    assert executor.supervisor.get(old_action) is old_terminal

    # Rebind a source-shaped *offline fixture* to the actual original D5
    # supervisor's session and next-epoch zombie. No Action is physically sent.
    _, _, _, example_step, example_selected, example_receipt, _, p = (
        _joined_original_owner()
    )
    chosen = replace(
        example_selected,
        session_id=executor.session_id, seq=150,
        request_id="d5-c1-second-native-probe",
        snapshot=fresh.snapshot,
    )
    action_id = "d5-c1-next-intent-motion"
    decision = replace(
        example_step.choice,
        session_id=executor.session_id,
        probe_seq=chosen.seq,
        request_id=chosen.request_id,
        entity_id=fresh.snapshot.nearby_entities[0].entity_id,
        provenance=chosen.provenance,
    )
    step = L0Step(
        decision, chosen.seq - 1, action_id,
        replace(
            example_step.grant,
            action_id=action_id,
            intent_id=executor.intent.current_intent.intent_id,
            session_id=executor.session_id,
            event_seq=chosen.seq - 1,
            probe_seq=chosen.seq,
            entity_id=decision.entity_id,
        ),
    )
    c1 = S49C1MotionDevJoin(
        executor.intent, executor, journal.state,
        self_id=journal.self_id, journal=journal,
    )
    predicted = c1.prepare_original_action(step, chosen)
    assert predicted.owner_revision == 0
    assert predicted.predicted_total_m == 0.7
    assert predicted.intent_id == handoff.next_intent_id

    # Physical replay fence is prepared BEFORE issuing the action under
    # this same supervisor; synthetic outcome cannot imply Minecraft proof.
    physical.prepare(
        session_id=executor.session_id,
        intent_id=executor.intent.current_intent.intent_id,
        action_id=action_id, probe=chosen,
    )
    with pytest.raises(UnresolvedPhysicalAction):
        physical.require_clear()
    timestamp = max(
        executor.supervisor.last_at_ns or 0,
        executor.intent.last_at_ns or 0,
    ) + 10
    skill = SkillExecution.start(
        "d5-c1-next-epoch-original-move-skill",
        skill_id="escape-movement",
        intent_commitment=executor.intent,
        at_ns=timestamp, provenance=p,
    )
    authorized = ActionLifecycle.propose(
        action_id, skill_execution=skill,
        intent_commitment=executor.intent,
        at_ns=timestamp + 1, provenance=p,
    ).authorize(
        at_ns=timestamp + 2, provenance=p,
        authority="synthetic-offline-only",
    )
    issued = executor.supervisor.issue(
        authorized, at_ns=timestamp + 3,
        deadline_ns=timestamp + 99, provenance=p,
    )
    executor._dispatched.add(issued.action_id)
    executor._count += 1
    original_terminal = executor.supervisor.record_outcome(
        action_id, at_ns=timestamp + 4, provenance=p,
    )
    shaped = example_receipt.consequence
    wrapped = replace(
        shaped,
        session_id=executor.session_id, action_id=action_id,
        before_observation=replace(
            shaped.before_observation, session_id=executor.session_id,
            seq=151, request_id=None,
        ),
        dispatch_receipt=replace(
            shaped.dispatch_receipt, session_id=executor.session_id,
            action_id=action_id, seq=152,
        ),
        cleanup_receipt=replace(
            shaped.cleanup_receipt, session_id=executor.session_id,
            action_id=action_id + "-s15-clear", seq=153,
        ),
        after_observation=replace(
            shaped.after_observation, session_id=executor.session_id,
            seq=154, request_id=None,
        ),
    )
    receipt = NormalActionReceipt(
        original_terminal, wrapped, chosen.provenance,
    )
    assert executor.supervisor.get(action_id) is original_terminal
    assert executor.supervisor.get(old_action) is old_terminal

    # First close the original physical Action, then commit the only C1
    # experience: the MOVE, not the first epoch's ATTACK.
    physical.close(
        receipt, chosen, original_supervisor=executor.supervisor,
    )
    c1.accept_original_terminal(step, chosen, receipt)
    completed = c1.close_original_intent()
    assert completed.experience.forecast is predicted
    assert len(completed.experience.action_receipts) == 1
    assert completed.experience.action_receipts[0] is receipt
    assert completed.experience.action_receipts[0].terminal.action_id == action_id
    assert old_action not in (
        x.terminal.action_id for x in completed.experience.action_receipts
    )
    assert completed.learning.new_state.revision == 1
    assert completed.learning.new_state.value == 6

    restored_c1 = C1MotionJournal.restore(
        journal.path, self_id=journal.self_id,
    )
    restored_fence = OriginalS49PhysicalFence.restore(
        physical.path, self_id=journal.self_id,
    )
    restored_fence.require_clear()
    assert restored_fence.actions[-1]["action_id"] == action_id
    assert restored_fence.actions[-1]["status"] == "S16_OUTCOME"
    assert restored_c1.original_action_keys == (
        (executor.session_id, action_id),
    )
    assert restored_c1.experience_ids == (
        completed.experience.experience_id,
    )
    assert restored_c1.state.revision == 1
    assert executor.supervisor is same_supervisor
    assert executor.supervisor.get(old_action) is old_terminal
    assert executor._dispatched == {old_action, action_id}
    assert executor._count == 2
    with pytest.raises(UnresolvedPhysicalAction):
        other = OriginalS49PhysicalFence.create(
            physical.path, self_id=journal.self_id,
        )
        other.require_clear()
