"""T1j M0/P1 gap rebase: no retrospective food/energy or WAIT recovery."""
from __future__ import annotations

from types import SimpleNamespace
import pytest

from adapters.mineflayer.t2_tick_accounting import TickAccounting
from adapters.mineflayer.t1j_resume_gate_dev import ResumeDevPermit, ResumeDevRejected
from adapters.mineflayer.t1j_resume_accounting_dev import rebase_tick_accounting_dev
from test_t1f_t2_dev import frame


def fixtures():
    old = TickAccounting("test-session")
    old.observe(frame(1))
    old.observe(frame(2))
    old.failed = True
    old.t1j_resumed_stop_id = "stopped-move"
    baseline = frame(10)
    permit = ResumeDevPermit(
        resume_id="R1", stop_id="stopped-move",
        session_id="test-session", next_action_id="t1j-R1-move",
        world=baseline.data["snapshot"]["world"],
        player=baseline.data["snapshot"]["player"],
        old_stop_ack_last_server_tick=105, before_source_seq=80,
        after_source_seq=baseline.seq, native_probe_seq=90,
        after_world_tick=baseline.data["snapshot"]["world_tick"],
        unobserved_world_ticks=7,
    )
    return old, baseline, permit


def test_new_segment_only_bills_consecutive_ticks_after_new_baseline():
    old, baseline, permit = fixtures()
    prior_energy = old.energy.body
    prior_fatigue = old.fatigue
    prior_rows = list(old.rows)
    new = rebase_tick_accounting_dev(old, baseline=baseline, permit=permit)
    assert old.failed and old.energy.body == prior_energy
    assert old.fatigue == prior_fatigue and old.rows == prior_rows
    assert new.rows == [] and new.previous == baseline
    assert new.energy.body == prior_energy
    assert new.energy.credit_count == old.energy.credit_count
    assert new.fatigue.world_tick == baseline.data["snapshot"]["world_tick"]
    assert new.fatigue.fatigue == prior_fatigue.fatigue
    assert new.segment_origin_dev["unobserved_world_ticks"] == 7
    assert not new.segment_origin_dev["resumed_m0_p1_qualified"]
    new.observe(frame(11))
    assert len(new.rows) == 1 and old.rows == prior_rows
    assert new.energy.body.tick == prior_energy.tick + 1
    assert new.energy.credit_count == old.energy.credit_count
    assert new.rows[0]["world_tick"] == 211
    assert not new.rows[0]["full_tick_R_attested"]


def test_rebase_never_reuses_the_same_old_frozen_ledger():
    old, baseline, permit = fixtures()
    rebase_tick_accounting_dev(old, baseline=baseline, permit=permit)
    with pytest.raises(ResumeDevRejected):
        rebase_tick_accounting_dev(old, baseline=baseline, permit=permit)


@pytest.mark.parametrize("failure", ["not_granted", "not_frozen", "wrong_session",
                                      "stale_baseline", "pending_meal"])
def test_no_segment_start_without_clean_explicit_boundary(failure):
    old, baseline, permit = fixtures()
    if failure == "not_granted":
        del old.t1j_resumed_stop_id
    elif failure == "not_frozen":
        old.failed = False
    elif failure == "wrong_session":
        baseline = SimpleNamespace(
            session_id="foreign", seq=baseline.seq, data=baseline.data)
    elif failure == "stale_baseline":
        baseline = frame(2)
    elif failure == "pending_meal":
        old.pending_meal = object()
    with pytest.raises(ResumeDevRejected):
        rebase_tick_accounting_dev(old, baseline=baseline, permit=permit)
