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
from adapters.mineflayer.python_protocol import MineflayerPaperSnapshot
from adapters.mineflayer.s31a_real_server_ci import _command, _correlated_observe
from relay_self.action_supervision import ActionSupervisor


async def next_tick(session, *, after_seq=-1, timeout=3):
    deadline = asyncio.get_running_loop().time() + timeout
    while True:
        remaining = deadline - asyncio.get_running_loop().time()
        if remaining <= 0:
            raise TimeoutError("fresh Paper tick absent")
        frame = await asyncio.wait_for(session.receive(), remaining)
        if isinstance(frame, MineflayerPaperSnapshot) and frame.seq > after_seq:
            if frame.data["status"] != "ADMITTED":
                raise ValueError(f"T1f refusal: {frame.data['status']} / {frame.data['reason']}")
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


async def native_meal(session, server, supervisor, report, *, time_base):
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
    issued = _issue(supervisor, "t2-native-meal", "eat", "t2-meal-intent",
                    "eat provided steak on actual hunger", time_base=time_base)
    owner = session.tick_owner
    owner.begin(issued.action_id)
    eating = await IssuedEatingExecutor().execute(
        session, supervisor, issued, choice, probe, paper_tick_dev=True)
    owner.active_action = None
    owner.terminal_seq = eating.outcome.after_probe_seq
    owner.queue_meal(eating)
    report["meal"] = asdict(eating)
    fresh = await next_tick(session, after_seq=eating.outcome.after_probe_seq)
    report["post_meal_decision_source"] = asdict(fresh)
    return fresh


async def run_continuation(session, server, report, root, *, observe_only, accounting, normal_epochs=2):
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
            if accounting and epoch == normal_epochs:
                fresh = await native_meal(session, server, supervisor, report, time_base=normal_epochs * 100 - 40)
            if supervisor.open_actions:
                raise ValueError("previous Action still open")
            if fresh.data["assessment"] != "NO_KNOWN_URGENT_SIGNAL":
                report["epochs"].append({"epoch": epoch, "decision": "WAIT_NO_ACTION",
                                         "source_seq": fresh.seq, "assessment": fresh.data["assessment"]})
                break
            issued = _issue(supervisor, f"t1f-epoch-{epoch}", "paper-l0-move", "t1f-dev-intent",
                            "DEV bounded move selected from current Paper L0", time_base=epoch * 100 + 10)
            step = {"epoch": epoch, "source_seq": fresh.seq,
                    "source_tick": fresh.data["snapshot"]["world_tick"],
                    "assessment": fresh.data["assessment"], "decision": "MOVE_BACKWARD",
                    "issued_action": asdict(issued)}
            report["epochs"].append(step)
            if accounting:
                session.tick_owner.begin(issued.action_id)
            fixture = None
            if epoch == normal_epochs:
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
                    timeout_s=.5, provenance=_p(f"t1f-epoch-{epoch}"), l0_interrupt_dev=True)
            finally:
                if fixture:
                    await fixture
            step["consequence"] = asdict(result)
            close = supervisor.record_outcome if result.status.value == "executed" else supervisor.mark_unknown
            terminal = close(issued.action_id, at_ns=epoch * 100 + 20, provenance=_p("t1f-terminal"))
            step["terminal"] = asdict(terminal)
            if accounting:
                session.tick_owner.finish(result, terminal)
            if result.cleanup_receipt is None:
                raise RuntimeError("clear ACK absent; next epoch forbidden")
            fresh, frames = await settled(session, result.cleanup_receipt.seq)
            step["post_clear"] = frames
            step["next_source_seq"] = fresh.seq
            step["next_source_tick"] = fresh.data["snapshot"]["world_tick"]
            step["next_assessment"] = fresh.data["assessment"]
            if epoch < normal_epochs and result.status.value != "executed":
                raise RuntimeError("benign Action failed")
            if epoch == normal_epochs and (result.status.value != "failed" or fresh.data["assessment"] != "LOW_HEALTH"):
                raise RuntimeError("Paper hazard did not interrupt")
        decisions = [e["decision"] for e in report["epochs"]]
        report["status"] = "PASS" if decisions == ["MOVE_BACKWARD"] * (normal_epochs + 1) + ["WAIT_NO_ACTION"] else "FAIL"
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
