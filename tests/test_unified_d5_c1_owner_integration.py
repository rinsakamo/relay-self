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
