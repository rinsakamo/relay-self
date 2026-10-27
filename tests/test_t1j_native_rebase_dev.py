"""T1j integration of real T1f Paper message shape with the frozen T2 owner."""
from types import SimpleNamespace as S

import pytest

from adapters.mineflayer.python_protocol import MineflayerEffectResult
from adapters.mineflayer.t1h_stop_owner_dev import S49DevStopOwner, StopDevAck
from adapters.mineflayer.t1j_resume_gate_dev import S49DevResumeGate, ResumeDevRejected
from adapters.mineflayer.t1j_resume_accounting_dev import rebase_tick_accounting_dev
from adapters.mineflayer.t2_tick_accounting import TickAccounting
from test_t1f_t2_dev import frame


def stopped():
    old = TickAccounting("test-session")
    old.observe(frame(1))
    old.observe(frame(2))
    old.failed = True
    owner = S49DevStopOwner("test-session")
    owner.request("STOP-1", active_action_id="old-action",
                  expected_clear_action_id="old-action-clear")
    owner.accept_clear(MineflayerEffectResult(
        "test-session", 35, "old-action-clear", "clear_controls",
        "applied", None), clear_action_id="old-action-clear")
    w = frame(2).data["snapshot"]
    owner.ack = StopDevAck(
        "STOP-1", "test-session", "old-action", "old-action-clear",
        35, "STOP-AFTER-CLEAR", w["world"], w["player"], 99, 106)
    return owner, old


def test_t1j_admitted_native_boundary_rebases_without_minting_gap_ticks():
    owner, old = stopped()
    gate = S49DevResumeGate(stopped_owner=owner, frozen_ledger=old,
                            retired_action_ids={"old-action", "t1f-epoch-0"})
    gate.authorize(
        authority="DEV_EXPLICIT_OPERATOR_REAUTHORIZE", resume_id="R01",
        stop_id="STOP-1", session_id="test-session",
        next_action_id="t1j-R01-move",
    )
    before = frame(10)
    native = S(session_id="test-session", seq=110, kind="probe",
               request_id="t1j-R01-reobserve", provenance=S(source="mineflayer"),
               snapshot=S(food=20))
    after = frame(12)
    permit = gate.reobserve(
        before=before, native_probe=native, after=after,
        expected_probe_request_id="t1j-R01-reobserve")
    assert permit.unobserved_world_ticks == 9
    assert gate.consume(permit) is permit
    fresh = rebase_tick_accounting_dev(old, baseline=after, permit=permit)
    assert not fresh.failed and old.failed and owner.requested
    assert fresh.energy.body == old.energy.body
    assert fresh.energy.credit_count == old.energy.credit_count
    assert not fresh.rows and len(old.rows) == 1
    fresh.observe(frame(13))
    assert len(fresh.rows) == 1 and len(old.rows) == 1
    assert fresh.energy.body.tick == old.energy.body.tick + 1


def test_no_resume_after_unknown_eat_without_move_stop_ack():
    owner, old = stopped()
    owner.ack = None
    with pytest.raises(ResumeDevRejected):
        S49DevResumeGate(stopped_owner=owner, frozen_ledger=old,
                         unresolved_eat=True)
