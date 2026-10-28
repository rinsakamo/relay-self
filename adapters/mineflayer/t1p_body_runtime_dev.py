"""T1p bounded, unforced L0 -> original S49 -> Paper -> M0/P1 DEV loop.

This is a designed L0 policy on a disposable World, not autonomous navigation.
The original session alone reads native frames and writes motor effects. No
additional Paper control channel, artificial hazard, food gift, or new fatigue
formula. Physical qualification and high-TPS Motor remain out of scope.
"""
from __future__ import annotations

from dataclasses import asdict

from adapters.mineflayer.execution import MineflayerCommand, execute_mineflayer_command
from adapters.mineflayer.m02_paper_dev.s51_paper_physics_dev import _issue, _p
from adapters.mineflayer.s31a_real_server_ci import _correlated_observe
from adapters.mineflayer.t1f_continuation_dev import next_tick, settled
from adapters.mineflayer.t2_tick_accounting import TickAccounting
from relay_self.action_supervision import ActionSupervisor


class T1pRejected(ValueError):
    """Refuse to issue an Action without a live, admitted owner-local source."""


def decide_l0(frame, owner, *, completed: int, limit: int) -> str:
    """Return MOVE / HOLD_BODY / HALT / COMPLETE, never an Action grant itself."""
    if (type(completed) is not int or type(limit) is not int
            or not 0 <= completed <= limit <= 32):
        raise T1pRejected("invalid bounded Action budget")
    if (owner.failed or owner.previous is None or owner.fatigue is None
            or owner.active_action is not None or owner.pending_meal is not None
            or frame is None or frame.session_id != owner.session_id
            or frame.seq != owner.previous.seq
            or frame.data["status"] != "ADMITTED"):
        raise T1pRejected("source/ledger/Action not eligible for new epoch")
    if completed == limit:
        return "COMPLETE"
    data = frame.data
    source = data["snapshot"]
    if (source["input"] != 0 or data["control"]["phase"] not in ("INITIAL", "CLEARED")
            or (completed and (owner.clear_seq is None
                               or data["control"]["phase"] != "CLEARED"))):
        return "HALT"
    # Only admitted Paper body and host-limited virtual capability are examined.
    # The evaluator's exact E/fatigue is NOT exported as a Self observation.
    if data["assessment"] != "NO_KNOWN_URGENT_SIGNAL":
        return "HALT"
    if owner.energy.body.energy <= 1.0:
        return "HALT"
    if owner.fatigue.fatigue >= 0.8 * owner.profile.capacity:
        return "HOLD_BODY"
    return "MOVE"


async def run_body_loop_dev(session, report, *, move_limit: int = 2,
                            wait_ticks: int = 12, l0_decider=None):
    """Small non-staged action/WAIT cycle using the original T1e resource owner.

    WAIT_DEV is the existing T2 conservative post-clear decision; time since
    clear, stationary command, or absence of an Action is never sufficient.
    An unexpected HALT is not relabelled success.
    """
    if (type(move_limit) is not int or not 2 <= move_limit <= 32
            or type(wait_ticks) is not int or not 8 <= wait_ticks <= 60
            or getattr(session, "source_lost", False)
            or getattr(session, "tick_owner", None) is not None):
        raise T1pRejected("fresh bounded T1p DEV session required")
    owner = TickAccounting(session.started.session_id)
    session.tick_owner = owner
    report.update(
        action_source="PAPER_DESIGNED_L0_EXISTING_S51_S49_SINGLE_ISSUER",
        model_calls=0, tps_actuator=False,
        t1p={"classification": "T1P_BOUNDED_UNFORCED_BODY_LOOP_DEV",
             "target_moves": move_limit, "wait_ticks_per_move": wait_ticks,
             "epochs": [], "p1_qualified_wait": False,
             "forced_hazard_count": 0, "gifted_food_count": 0})
    if l0_decider is not None and not callable(l0_decider):
        raise T1pRejected("read-only cognition policy must be callable")
    choose = decide_l0 if l0_decider is None else l0_decider
    supervisor = ActionSupervisor()
    probe = await _correlated_observe(session, "t1p-start-barrier")
    fresh = await next_tick(session, after_seq=probe.seq)
    body = report["t1p"]
    for epoch in range(move_limit):
        decision = choose(fresh, owner, completed=epoch, limit=move_limit)
        if decision == "HOLD_BODY":
            # No movement command while capability-limited; observe actual ticks.
            for _ in range(60):
                fresh = await next_tick(session, after_seq=fresh.seq)
                decision = choose(fresh, owner, completed=epoch, limit=move_limit)
                if decision != "HOLD_BODY":
                    break
        if decision != "MOVE":
            body.update(halt_reason=decision, halted_at_epoch=epoch)
            report["status"] = "FAIL"
            return body

        if supervisor.open_actions:
            raise T1pRejected("prior Action is still open")
        issued = _issue(
            supervisor, f"t1p-epoch-{epoch}", "paper-l0-move",
            "t1p-dev-intent", "bounded healthy Paper L0 MOVE_BACKWARD",
            time_base=epoch * 100 + 10)
        entry = {
            "epoch": epoch, "source_seq": fresh.seq,
            "source_world_tick": fresh.data["snapshot"]["world_tick"],
            "assessment": fresh.data["assessment"],
            "decision": "MOVE_BACKWARD", "issued_action": asdict(issued)}
        body["epochs"].append(entry)
        owner.begin(issued.action_id)
        try:
            result = await execute_mineflayer_command(
                session, MineflayerCommand(
                    action_id=issued.action_id,
                    binding_id=f"t1p-epoch-binding-{epoch}",
                    action_ref="MOVE_BACKWARD", effect="set_control",
                    control="back", state=True, duration_s=.2,
                    cleanup_action_id=issued.action_id + "-clear"),
                timeout_s=.5, provenance=_p(f"t1p-epoch-{epoch}"),
                l0_interrupt_dev=True)
        except BaseException:
            owner.failed = True
            raise
        entry["consequence"] = asdict(result)
        close = (supervisor.record_outcome if result.status.value == "executed"
                 else supervisor.mark_unknown)
        terminal = close(
            issued.action_id, at_ns=epoch * 100 + 20,
            provenance=_p(f"t1p-terminal-{epoch}"))
        entry["terminal"] = asdict(terminal)
        owner.finish(result, terminal)
        if (result.status.value != "executed" or owner.failed
                or owner.active_action is not None):
            body.update(halt_reason="ACTION_FAILED_OR_CLEAR_UNCONFIRMED",
                        halted_at_epoch=epoch)
            report["status"] = "FAIL"
            return body
        fresh, post_clear = await settled(session, result.cleanup_receipt.seq)
        entry["settle_transitions"] = post_clear
        entry["settled_source_seq"] = fresh.seq
        for _ in range(wait_ticks):
            fresh = await next_tick(session, after_seq=fresh.seq)
        entry["post_wait_world_tick"] = fresh.data["snapshot"]["world_tick"]
        entry["energy_after"] = owner.energy.body.energy
        entry["fatigue_after"] = owner.fatigue.fatigue

    rows = owner.rows
    move_rows = [r for r in rows if r["native_motion_blocks"] > 0]
    wait_rows = [r for r in rows if r["activity"] == "WAIT_DEV"]
    recovered = sum(r["p1"]["recovered"] for r in rows)
    body.update(
        completed_moves=len(body["epochs"]),
        accounted_ticks=len(rows),
        first_accounted_tick=rows[0]["world_tick"] if rows else None,
        last_accounted_tick=rows[-1]["world_tick"] if rows else None,
        motion_ticks=len(move_rows), wait_dev_ticks=len(wait_rows),
        m0_basal=sum(r["m0_basal"] for r in rows),
        m0_cognition=sum(r["m0_cognition"] for r in rows),
        m0_move=sum(r["m0_move"] for r in rows),
        p1_accumulated=sum(r["p1"]["accumulated"] for r in rows),
        p1_recovered=recovered, energy=asdict(owner.energy.body),
        fatigue=asdict(owner.fatigue),
        source_latched=owner.failed, p1_qualified_wait=False)
    good = (not owner.failed and owner.active_action is None
            and not owner.pending_meal and len(body["epochs"]) == move_limit
            and len(rows) >= move_limit * wait_ticks and bool(move_rows)
            and bool(wait_rows) and body["p1_accumulated"] > 0
            and recovered > 0 and owner.energy.credit_count == 0)
    report["status"] = "PASS" if good else "FAIL"
    return body
