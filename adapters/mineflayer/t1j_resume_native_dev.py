"""T1j original native reader + original S49 issuer: one opt-in resumed MOVE.

Previous STOP owner stays latched; an explicit one-shot DEV authority and two
fresh Paper samples around a correlated native probe precede a NEW Action ID.
No unknown EAT is resumed, no missing World ticks are reconciled as fact.
"""
from __future__ import annotations

from dataclasses import asdict

from adapters.mineflayer.execution import MineflayerCommand, WorldConsequenceStatus, execute_mineflayer_command
from adapters.mineflayer.m02_paper_dev.s51_paper_physics_dev import _issue, _p
from adapters.mineflayer.s31a_real_server_ci import _correlated_observe
from adapters.mineflayer.t1f_continuation_dev import next_tick, settled
from adapters.mineflayer.t1h_stop_owner_dev import S49DevStopOwner
from adapters.mineflayer.t1j_resume_accounting_dev import rebase_tick_accounting_dev
from adapters.mineflayer.t1j_resume_gate_dev import S49DevResumeGate, ResumeDevRejected


async def resume_one_move_dev(
    session, supervisor, old_owner, report, *, time_base: int,
) -> dict:
    """Same S49 owner/session; no new native IO writer or read task."""
    old_ledger = session.tick_owner
    if (getattr(session, "source_lost", False)
            or session.process_returncode is not None
            or supervisor.open_actions
            or not getattr(old_ledger, "failed", False)
            or getattr(session, "consume_tick_accounting", True)):
        raise ResumeDevRejected("T1j old S49 action/source/accounting not closed")
    prior = frozenset([
        e["issued_action"]["action_id"]
        for e in report.get("epochs", []) if "issued_action" in e
    ] + ["t2-native-meal"])
    gate = S49DevResumeGate(
        stopped_owner=old_owner, frozen_ledger=old_ledger,
        unresolved_eat=False, retired_action_ids=prior,
    )
    sid = session.started.session_id
    resume_id = "T1J-R1"
    next_action_id = f"t1j-{resume_id}-move"
    gate.authorize(
        authority="DEV_EXPLICIT_OPERATOR_REAUTHORIZE",
        resume_id=resume_id, stop_id=old_owner.stop_id,
        session_id=sid, next_action_id=next_action_id,
    )
    # The old STOP owner is STILL latched throughout the entire reobservation.
    # The sole original receive owner consumes prior queued Paper ticks.
    lower_bound = max(old_owner.ack.clear_ack_seq, old_ledger.previous.seq)
    before = None
    for _ in range(160):
        candidate = await next_tick(session, after_seq=lower_bound)
        lower_bound = candidate.seq
        if candidate.data["snapshot"]["tick"] > old_owner.ack.last_idle_tick:
            before = candidate
            break
    if before is None:
        raise ResumeDevRejected("T1j no Paper tick after old DEV STOP window")
    probe_request = "t1j-R1-reobserve"
    native = await _correlated_observe(session, probe_request)
    after = await next_tick(session, after_seq=native.seq)
    permit = gate.reobserve(
        before=before, native_probe=native, after=after,
        expected_probe_request_id=probe_request,
    )
    gate.consume(permit)
    new_ledger = rebase_tick_accounting_dev(
        old_ledger, baseline=after, permit=permit,
    )
    session.t1j_resume_permission = permit
    new_stop_owner = S49DevStopOwner(sid)
    session.t1j_new_stop_owner = new_stop_owner
    session.tick_owner = new_ledger
    session.consume_tick_accounting = True
    result = None
    try:
        if (getattr(session, "source_lost", False)
                or old_owner.allows_action or not new_stop_owner.allows_action):
            raise ResumeDevRejected("T1j source/new owner invalidated before issue")
        issued = _issue(
            supervisor, permit.next_action_id, "paper-l0-move",
            "t1j-explicit-resume-intent",
            "one bounded DEV MOVE after fresh World reauthorization",
            time_base=time_base,
        )
        if issued.action_id != permit.next_action_id:
            raise ResumeDevRejected("T1j Supervisor did not issue exact action")
        new_ledger.begin(issued.action_id)
        command = MineflayerCommand(
            action_id=issued.action_id, binding_id="t1j-explicit-resume-binding",
            action_ref="MOVE_BACKWARD", effect="set_control", control="back",
            state=True, duration_s=.2, cleanup_action_id=issued.action_id + "-clear",
        )
        result = await execute_mineflayer_command(
            session, command, timeout_s=.5, provenance=_p("t1j-resumed-move"),
            l0_interrupt_dev=True,
            stop_requested_dev=lambda: new_stop_owner.requested,
        )
        finish = (
            supervisor.record_outcome if result.status is WorldConsequenceStatus.EXECUTED
            else supervisor.mark_unknown
        )
        terminal = finish(
            issued.action_id, at_ns=time_base + 20,
            provenance=_p("t1j-resumed-terminal"),
        )
        new_ledger.finish(result, terminal)
        if (result.status is not WorldConsequenceStatus.EXECUTED
                or result.cleanup_receipt is None or new_ledger.failed):
            raise ResumeDevRejected("T1j resumed Action not executed/cleared")
        fresh, idle = await settled(session, result.cleanup_receipt.seq)
        if fresh.data["assessment"] != "NO_KNOWN_URGENT_SIGNAL":
            raise ResumeDevRejected("T1j post-resume hazard")
        return {
            "classification": "T1J_EXPLICIT_REOBSERVED_RESUME_DEV",
            "permit": asdict(permit),
            "rebase": new_ledger.segment_origin_dev,
            "new_action": asdict(issued),
            "consequence": asdict(result),
            "terminal": asdict(terminal),
            "post_move_idle": idle,
            "next_paper_seq": fresh.seq,
            "old_owner_still_latched": old_owner.requested and not old_owner.allows_action,
            "new_owner_is_distinct": new_stop_owner is not old_owner,
            "unknown_eat_retried": False,
            "historical_m0_p1_retroactively_filled": False,
            "p1_wait_qualified": False,
        }
    except BaseException:
        new_ledger.failed = True
        raise
    finally:
        # The explicit permit only authorizes the single new physical send.
        session.t1j_resume_permission = None
