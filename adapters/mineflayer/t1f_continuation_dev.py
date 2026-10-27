"""Bounded S49 owner-local DEV continuation, reusing T1e resource ownership.

Policy is explicit, cheap and designed: healthy -> short MOVE_BACKWARD;
LOW_HEALTH/hostile/unknown -> no new Action. Post-clear fresh input/pose settles
before another issue. Every Action uses existing S51 issuer, Supervisor, S49
executor and S16 clear. No parallel native receive task or model call.
"""
from __future__ import annotations

import asyncio
import json
import time
from dataclasses import asdict

from adapters.mineflayer.execution import MineflayerCommand, execute_mineflayer_command
from adapters.mineflayer.m02_paper_dev.s51_paper_physics_dev import _issue, _p
from adapters.mineflayer.process_session import MineflayerProcessEnded, MineflayerProcessIOError
from adapters.mineflayer.python_protocol import (
    MineflayerAdapterErrorMessage,
    MineflayerCommandError,
    MineflayerConnectionEnd,
    MineflayerPaperSnapshot,
    MineflayerShutdownAck,
)
from adapters.mineflayer.s31a_real_server_ci import _command, _correlated_observe
from relay_self.action_supervision import ActionSupervisor


def _latch_source_loss(session):
    """No next Action / WAIT_DEV admission after this owner loses its source."""
    session.source_lost = True
    owner = getattr(session, "tick_owner", None)
    if owner is not None:
        owner.failed = True


async def next_tick(session, *, after_seq=-1, timeout=3):
    """Read through the sole session; NEVER skip terminal/error frames.

    Only admitted, session-matched Paper samples can continue an epoch.
    An EOF or shutdown acknowledgment is not proof of high-level STOP.
    """
    if getattr(session, "source_lost", False):
        raise RuntimeError("T1g source already lost; continuation forbidden")
    deadline = asyncio.get_running_loop().time() + timeout
    while True:
        remaining = deadline - asyncio.get_running_loop().time()
        if remaining <= 0:
            _latch_source_loss(session)
            raise TimeoutError("fresh Paper tick absent; T1g source latched")
        try:
            frame = await asyncio.wait_for(session.receive(), remaining)
        except (TimeoutError, MineflayerProcessEnded, MineflayerProcessIOError):
            _latch_source_loss(session)
            raise
        if isinstance(frame, (MineflayerConnectionEnd,
                              MineflayerAdapterErrorMessage,
                              MineflayerCommandError, MineflayerShutdownAck)):
            _latch_source_loss(session)
            raise RuntimeError(
                f"T1g terminal native frame before next Action: {type(frame).__name__}"
            )
        if isinstance(frame, MineflayerPaperSnapshot):
            if frame.session_id != session.started.session_id:
                _latch_source_loss(session)
                raise RuntimeError("foreign T1g Paper session")
            if frame.seq <= after_seq:
                continue
            if frame.data["status"] != "ADMITTED":
                _latch_source_loss(session)
                raise ValueError(
                    f"T1f refusal: {frame.data['status']} / {frame.data['reason']}"
                )
            return frame


async def settled(session, after_seq):
    # Correlated probe drains previous-epoch frames through the same owner.
    # Current Node admission is rechecked immediately at actual motor dispatch.
    probe = await _correlated_observe(session, f"t1f-boundary-{after_seq}")
    prior = None
    consecutive = 0
    frames = []
    for _ in range(80):
        f = await next_tick(session, after_seq=max(after_seq, probe.seq))
        d, s = f.data, f.data["snapshot"]
        c = d["control"]
        post_clear = (c["phase"] == "CLEARED" and d["challenge_sent_ns"] is not None
                      and int(d["challenge_sent_ns"]) > int(c["since_ns"]))
        if prior is not None:
            p = prior.data["snapshot"]
            idle = (post_clear and s["input"] == p["input"] == 0
                    and all(abs(s[k] - p[k]) < 1e-9 for k in ("x", "y", "z"))
                    and s["motion_blocks"] == p["motion_blocks"]
                    and s["tick"] == p["tick"] + 1
                    and c == prior.data["control"])
            consecutive = consecutive + 1 if idle else 0
            frames.append({"seq": f.seq, "world_tick": s["world_tick"],
                           "idle": idle, "input": s["input"],
                           "pose": [s[k] for k in ("x", "y", "z")]})
            if consecutive >= 8:
                return f, frames
        prior = f
    raise RuntimeError("Paper residual motion/input did not settle")


async def native_meal(session, server, supervisor, report, *, time_base, stop_owner=None):
    from adapters.mineflayer.eat_execution import IssuedEatingExecutor
    from relay_self.eat_hunger import EatCursor, EatStatus

    _command(server, "give RelaySelf minecraft:cooked_beef 3")
    _command(server, "effect give RelaySelf minecraft:hunger 25 20 true")
    await server.stdin.drain()
    cursor = EatCursor(session.started.session_id, hunger_threshold=19)
    for i in range(300):
        fresh = await next_tick(session)
        if fresh.data["snapshot"]["food"] < 19:
            _command(server, "effect clear RelaySelf minecraft:hunger")
            await server.stdin.drain()
            probe = await _correlated_observe(session, f"t2-eat-source-{i}")
            choice = cursor.choose(probe)
            if choice.status is EatStatus.CANDIDATE:
                break
    else:
        raise RuntimeError("native hunger/food source absent")
    from adapters.mineflayer.t1i_session_stop_dev import require_stop_permits_action
    require_stop_permits_action(stop_owner)
    issued = _issue(supervisor, "t2-native-meal", "eat", "t2-meal-intent",
                    "eat provided steak on actual hunger", time_base=time_base)
    owner = session.tick_owner
    owner.begin(issued.action_id)
    if stop_owner is not None:
        session.t1i_eat_action_id = issued.action_id
    report["meal_before"] = asdict(probe)
    eating = await IssuedEatingExecutor().execute(
        session, supervisor, issued, choice, probe, paper_tick_dev=True,
        stop_requested_dev=(lambda: stop_owner.requested) if stop_owner else None)
    require_stop_permits_action(stop_owner)
    owner.active_action = None
    owner.terminal_seq = eating.outcome.after_probe_seq
    owner.queue_meal(eating)
    report["meal"] = asdict(eating)
    fresh = await next_tick(session, after_seq=eating.outcome.after_probe_seq)
    report["post_meal_decision_source"] = asdict(fresh)
    return fresh


async def run_continuation(session, server, report, root, *,
                           observe_only, accounting, normal_epochs=2,
                           stop_owner=None, stop_mode=None, resume_mode=False):
    from adapters.mineflayer.t1i_session_stop_dev import (
        finish_multi_epoch_move_stop,
        require_stop_permits_action,
    )
    from relay_self.action import ActionState
    if (stop_mode not in (None, "MOVE", "EAT")
            or (stop_mode and stop_owner is None)
            or (resume_mode and (stop_mode != "MOVE" or not accounting))):
        raise ValueError("T1i/T1j STOP requires exact original S49 owner/accounting")
    supervisor = ActionSupervisor()
    report.update(action_source="PAPER_L0_DESIGNED_POLICY_EXISTING_S51_ISSUER_S49_EXECUTOR",
                  epochs=[], model_calls=0, tps_actuator=False)
    if accounting:
        from adapters.mineflayer.t2_tick_accounting import TickAccounting
        session.tick_owner = TickAccounting(session.started.session_id)
    probe = await _correlated_observe(session, "t1f-start-barrier")
    fresh = await next_tick(session, after_seq=probe.seq)
    if observe_only:
        for _ in range(40):
            fresh = await next_tick(session, after_seq=fresh.seq)
        report["status"] = "PASS"
    else:
        for epoch in range(normal_epochs + 2):
            require_stop_permits_action(stop_owner)
            if accounting and epoch == normal_epochs:
                try:
                    fresh = await native_meal(
                        session, server, supervisor, report,
                        time_base=normal_epochs * 100 - 40,
                        stop_owner=stop_owner,
                    )
                except Exception as exc:
                    from adapters.mineflayer.eat_execution import EatingExecutionRejected
                    if not (
                        stop_mode == "EAT" and stop_owner.requested
                        and not getattr(session, "source_lost", False)
                        and isinstance(exc, EatingExecutionRejected)
                        and "T1i owner STOP" in str(exc)
                        and supervisor.get("t2-native-meal").state is ActionState.UNKNOWN
                    ):
                        raise
                    # Consume is non-idempotent. A STOP while its receipt is
                    # pending CANNOT prove that Minecraft did not eat. Preserve
                    # UNKNOWN and never fabricate a food/inventory or M0 credit.
                    owner = session.tick_owner
                    owner.failed = True
                    report["t1i"] = {
                        "mode": "EAT", "stop_requested": True,
                        "action_state": "unknown", "consumption": "UNDETERMINED",
                        "physical_eat_interruption": "UNVERIFIED",
                        "stop_ack_dev": None, "meal_credit_issued": False,
                        "remaining_action_effects": "FORBIDDEN",
                        "error": f"{type(exc).__name__}: {exc}",
                    }
                    from adapters.mineflayer.t1i_session_stop_dev import observe_stopped_eat
                    report["t1i"]["passive_observation"] = await observe_stopped_eat(
                        session, server, report["meal_before"], root / "paper.log",
                    )
                    report["t1i"]["classification"] = "EAT_STOP_FAIL_CLOSED_DEV_PASS"
                    report["status"] = "PASS"
                    break
            require_stop_permits_action(stop_owner)
            if supervisor.open_actions:
                raise ValueError("previous Action still open")
            if fresh.data["assessment"] != "NO_KNOWN_URGENT_SIGNAL":
                report["epochs"].append({"epoch": epoch, "decision": "WAIT_NO_ACTION",
                                         "source_seq": fresh.seq, "assessment": fresh.data["assessment"]})
                break
            require_stop_permits_action(stop_owner)
            issued = _issue(supervisor, f"t1f-epoch-{epoch}", "paper-l0-move", "t1f-dev-intent",
                            "DEV bounded move selected from current Paper L0", time_base=epoch * 100 + 10)
            step = {"epoch": epoch, "source_seq": fresh.seq,
                    "source_tick": fresh.data["snapshot"]["world_tick"],
                    "assessment": fresh.data["assessment"], "decision": "MOVE_BACKWARD",
                    "issued_action": asdict(issued)}
            report["epochs"].append(step)
            if accounting:
                session.tick_owner.begin(issued.action_id)
            if stop_mode == "MOVE" and epoch == normal_epochs:
                session.t1i_stop_arm_action_id = issued.action_id
            fixture = None
            if epoch == normal_epochs and stop_mode != "MOVE":
                async def hazard():
                    await asyncio.sleep(.08)
                    _command(server, "damage RelaySelf 15 minecraft:generic")
                    await server.stdin.drain()
                fixture = asyncio.create_task(hazard())
            try:
                result = await execute_mineflayer_command(session, MineflayerCommand(
                    action_id=issued.action_id, binding_id=f"t1f-epoch-binding-{epoch}",
                    action_ref="MOVE_BACKWARD", effect="set_control", control="back", state=True,
                    duration_s=.6 if epoch == normal_epochs else .2,
                    cleanup_action_id=issued.action_id + "-clear"),
                    timeout_s=.5, provenance=_p(f"t1f-epoch-{epoch}"),
                    l0_interrupt_dev=True,
                    stop_requested_dev=(lambda: stop_owner.requested) if stop_owner else None)
            finally:
                if fixture:
                    await fixture
            step["consequence"] = asdict(result)
            close = supervisor.record_outcome if result.status.value == "executed" else supervisor.mark_unknown
            terminal = close(issued.action_id, at_ns=epoch * 100 + 20, provenance=_p("t1f-terminal"))
            step["terminal"] = asdict(terminal)
            if accounting:
                session.tick_owner.finish(result, terminal)
            if stop_mode == "MOVE" and stop_owner.requested:
                report["t1i"] = {
                    "mode": "MOVE", "stop_requested": True,
                    **(await finish_multi_epoch_move_stop(
                        session, server, fresh.data["snapshot"], result,
                        terminal, stop_owner, root / "paper.log",
                    )),
                }
                if resume_mode:
                    from adapters.mineflayer.t1j_resume_native_dev import resume_one_move_dev
                    report["t1j"] = await resume_one_move_dev(
                        session, supervisor, stop_owner, report,
                        time_base=(normal_epochs + 2) * 100 + 10,
                    )
                report["status"] = "PASS"
                break
            if result.cleanup_receipt is None:
                raise RuntimeError("clear ACK absent; next epoch forbidden")
            require_stop_permits_action(stop_owner)
            if hasattr(session, "boundary_fault"):
                await session.boundary_fault()
            fresh, frames = await settled(session, result.cleanup_receipt.seq)
            step["post_clear"] = frames
            step["next_source_seq"] = fresh.seq
            step["next_source_tick"] = fresh.data["snapshot"]["world_tick"]
            step["next_assessment"] = fresh.data["assessment"]
            if epoch < normal_epochs and result.status.value != "executed":
                raise RuntimeError("benign Action failed")
            if epoch == normal_epochs and (result.status.value != "failed" or fresh.data["assessment"] != "LOW_HEALTH"):
                raise RuntimeError("Paper hazard did not interrupt")
        if stop_mode is None:
            decisions = [e["decision"] for e in report["epochs"]]
            report["status"] = "PASS" if decisions == ["MOVE_BACKWARD"] * (normal_epochs + 1) + ["WAIT_NO_ACTION"] else "FAIL"
        elif "t1i" not in report or not report["t1i"]["stop_requested"]:
            report["status"] = "FAIL"
    frames = session.paper_frames or []
    data = [f.data for f in frames]
    admitted = [r for r in data if r["status"] == "ADMITTED"]
    report["t1f"] = {
        "frames": len(data), "admitted": len(admitted),
        "statuses": {k: sum(r["status"] == k for r in data) for k in
                     ("ADMITTED", "STALE", "MISSING", "LATE", "UNDETERMINED")},
        "max_causal_age_upper_ms": max((int(r["age_upper_ns"]) / 1e6 for r in admitted), default=None),
        "max_node_processing_ms": max((int(r["evaluation_completed_ns"]) - int(r["received_ns"])) / 1e6
                                      for r in admitted) if admitted else None,
        "paper_to_node_exact_delay": "UNKNOWN", "source": "PAPER_CALLBACK_BODY_NOT_CACHE",
        "cache_mismatch_frames": sum(r["cache_mismatch"] is True for r in data),
        "world": fresh.data["snapshot"]["world"], "player": fresh.data["snapshot"]["player"]}
    if accounting:
        owner = session.tick_owner
        (root / "t2_ticks.json").write_text(json.dumps(owner.rows, indent=2) + "\n")
        report["t2"] = {"ticks": len(owner.rows), "world_seconds": len(owner.rows) / 20,
                        "first_tick": owner.rows[0]["world_tick"] if owner.rows else None,
                        "last_tick": owner.rows[-1]["world_tick"] if owner.rows else None,
                        "energy": asdict(owner.energy.body), "fatigue": asdict(owner.fatigue),
                        "m0_basal": sum(r["m0_basal"] for r in owner.rows),
                        "m0_move": sum(r["m0_move"] for r in owner.rows),
                        "m0_cognition": sum(r["m0_cognition"] for r in owner.rows),
                        "intake": sum(r["m0"]["intake"] for r in owner.rows),
                        "credit_count": owner.energy.credit_count,
                        "p1_accumulated": sum(r["p1"]["accumulated"] for r in owner.rows),
                        "p1_recovered": sum(r["p1"]["recovered"] for r in owner.rows),
                        "wait_dev_ticks": sum(r["activity"] == "WAIT_DEV" for r in owner.rows),
                        "P1_qualified_WAIT": False, "latched": owner.failed}
    report["observed_at_python_ns"] = time.monotonic_ns()
