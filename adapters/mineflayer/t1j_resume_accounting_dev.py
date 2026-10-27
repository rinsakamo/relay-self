"""T1j DEV segmentation: carry last known virtual values, never fill STOP gap.

This is a *provisional* M0/P1 segment; actual World metabolism continues during
STOP and is not reconstructed. An R-qualified P1 state is NEVER established.
"""
from __future__ import annotations

from dataclasses import replace

from adapters.mineflayer.t1j_resume_gate_dev import ResumeDevPermit, ResumeDevRejected
from adapters.mineflayer.t2_tick_accounting import TickAccounting


def rebase_tick_accounting_dev(
    old: TickAccounting, *, baseline, permit: ResumeDevPermit,
) -> TickAccounting:
    """Start separate consecutive accounting at fresh Paper tick; old remains frozen."""
    if (not isinstance(old, TickAccounting)
            or not isinstance(permit, ResumeDevPermit)
            or getattr(old, "t1j_resumed_stop_id", None) != permit.stop_id
            or getattr(old, "t1j_accounting_rebased", False)
            or not old.failed or old.active_action is not None
            or old.pending_meal is not None or old.previous is None
            or old.fatigue is None or old.energy.body.terminal
            or baseline is not old.previous and baseline.seq != permit.after_source_seq
            or baseline.session_id != old.session_id
            or baseline.data["status"] != "ADMITTED"
            or baseline.data["snapshot"]["world_tick"] != permit.after_world_tick
            or baseline.data["snapshot"]["world"] != permit.world
            or baseline.data["snapshot"]["player"] != permit.player
            or old.previous.data["snapshot"]["world_tick"] >= permit.after_world_tick):
        raise ResumeDevRejected("T1j accounting rebase requires consumed explicit grant")
    new = TickAccounting(old.session_id)
    new.profile = old.profile
    new.energy.config = old.energy.config
    # These virtual values are *last known*, not retrospectively corrected.
    # Never mint food units for STOP-time World food/inventory changes.
    new.energy.body = old.energy.body
    new.energy._credits = set(old.energy._credits)
    new.energy._last_eat_seq = old.energy._last_eat_seq
    new.energy._last_decision_seq = old.energy._last_decision_seq
    new.previous = baseline
    new.fatigue = replace(old.fatigue, world_tick=permit.after_world_tick)
    new.segment_origin_dev = {
        "kind": "PROVISIONAL_LAST_KNOWN_CARRY_WITH_UNOBSERVED_GAP",
        "resume_id": permit.resume_id,
        "stop_id": permit.stop_id,
        "prior_ledger_rows": len(old.rows),
        "new_origin_world_tick": permit.after_world_tick,
        "unobserved_world_ticks": permit.unobserved_world_ticks,
        "prior_energy_last_known": old.energy.body.energy,
        "prior_fatigue_last_known": old.fatigue.fatigue,
        "world_physical_energy_during_gap": "UNKNOWN",
        "world_fatigue_during_gap": "UNKNOWN",
        "resumed_m0_p1_qualified": False,
        "p1_wait_qualified": False,
        "stop_gap_debit_and_credit": 0,
    }
    old.t1j_accounting_rebased = True
    return new
