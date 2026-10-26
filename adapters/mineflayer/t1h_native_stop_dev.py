"""T1h isolated live STOP fixtures; original S49 issuer and sole receiver.

Clear ACK, bounded Paper idle-window DEV ACK, and shutdown are separate.
Faults are explicit DEV injections; raw native evidence remains unmodified.
"""
from __future__ import annotations

import asyncio
import time
from dataclasses import asdict, replace

from adapters.mineflayer.execution import (
    MineflayerCommand,
    WorldConsequenceStatus,
    execute_mineflayer_command,
)
from adapters.mineflayer.m02_paper_dev.s51_paper_physics_dev import _issue, _p
from adapters.mineflayer.s31a_real_server_ci import _command, _correlated_observe
from adapters.mineflayer.t1f_continuation_dev import next_tick
from adapters.mineflayer.t1h_stop_owner_dev import S49DevStopOwner, StopDevRejected
from relay_self.action_supervision import ActionSupervisor


async def run_stop_move_dev(session, server, report, root) -> None:
    """One live owner, one bounded MOVE, no additional Motor/reader."""
    case = report["case"]
    supervisor = ActionSupervisor()
    probe = await _correlated_observe(session, "t1h-start-source")
    fresh = await next_tick(session, after_seq=probe.seq)
    if fresh.data["assessment"] != "NO_KNOWN_URGENT_SIGNAL":
        raise StopDevRejected("initial Paper hazard refuses physical STOP fixture")
    sid = session.started.session_id
    owner = S49DevStopOwner(sid)
    session.t1h_stop_owner = owner
    report["t1h"] = detail = {
        "source_session": sid, "initial_paper": asdict(fresh),
        "next_action_issued": False, "next_action_issued_count": 0,
        "p1_wait_qualification": False, "accounting_ticks_created": 0,
        "node_shutdown_ack_is_not_stop_ack": True,
    }

    def requested():
        if owner.requested:
            report.setdefault("stop_recognized_python_ns", time.monotonic_ns())
        return owner.requested

    cmd = MineflayerCommand(
        action_id="t1h-owned-move", binding_id="t1h-owned-move-binding",
        action_ref="MOVE_BACKWARD", effect="set_control", control="back", state=True,
        duration_s=0.75, cleanup_action_id="t1h-owned-move-clear",
    )
    if case == "t1h_pre_stop":
        report["stop_requested_python_ns"] = time.monotonic_ns()
        owner.request("t1h-before-issue")
        detail["issued_action_count"] = 0
    else:
        if not owner.allows_action:
            raise StopDevRejected("owner refused initial Action")
        issued = _issue(
            supervisor, cmd.action_id, "paper-l0-move", "t1h-stop-intent",
            "single authorized bounded move interrupted by operator STOP", time_base=10,
        )
        session.t1h_active_action_id = issued.action_id
        detail["issued_action_count"] = 1
        detail["issued_action"] = asdict(issued)
    result = await execute_mineflayer_command(
        session, cmd, timeout_s=0.5, provenance=_p("t1h-stop-action"),
        l0_interrupt_dev=True, stop_requested_dev=requested,
    )
    detail.update(
        requested=owner.requested, stop_id=owner.stop_id, action_id=owner.active_action_id,
        action_status=result.status.value, action_error=result.error,
        cleanup_receipt=asdict(result.cleanup_receipt) if result.cleanup_receipt else None,
    )
    if case != "t1h_pre_stop":
        terminal = supervisor.mark_unknown(
            issued.action_id, at_ns=20, provenance=_p("t1h-stop-terminal"))
        detail["supervised_terminal"] = terminal.state.value
    if (not owner.requested or result.status is not WorldConsequenceStatus.FAILED
            or not result.error or "T1h high-level STOP" not in result.error
            or owner.allows_action):
        raise StopDevRejected("STOP failed to interrupt through original S49")

    # Probe the next effect boundary through the SAME executor. No new
    # Supervisor Action is issued after the latch, and no Motor may start.
    next_result = await execute_mineflayer_command(
        session, replace(cmd, action_id="t1h-forbidden-next",
                         cleanup_action_id="t1h-forbidden-next-clear"),
        timeout_s=.1, provenance=_p("t1h-next-refusal"), l0_interrupt_dev=True,
        stop_requested_dev=requested,
    )
    if next_result.status is not WorldConsequenceStatus.FAILED or next_result.cleanup_attempted:
        raise StopDevRejected("next Action boundary was not refused before Motor")
    detail["next_executor_refused_before_motor"] = True
    try:
        owner.request("t1h-duplicate-stop")
    except StopDevRejected:
        detail["duplicate_request_rejected"] = True
    else:
        raise AssertionError("duplicate STOP accepted")

    expected_rejection = {
        "t1h_pre_stop": "STOP cannot ACK without original clear",
        "t1h_lost_ack": "STOP cannot ACK without original clear",
        "t1h_delayed_ack": "STOP cannot ACK without original clear",
        "t1h_disconnect": "source lost before STOP ACK",
        "t1h_disconnect_after_idle": "source lost before STOP ACK",
        "t1h_paper_short": "insufficient Paper post-clear",
        "t1h_input_residual": "no 8 consecutive motion-free",
        "t1h_motion_residual": "no 8 consecutive motion-free",
        "t1h_stale_ack": "no matching acknowledged original S49 clear",
    }.get(case)
    try:
        if result.cleanup_receipt is not None:
            receipt = result.cleanup_receipt
            clear_id = cmd.cleanup_action_id
            if case == "t1h_stale_ack":
                # Consumer-only stale session/Action replay, explicitly labelled.
                # The original applied receipt and wire bytes stay in journals.
                receipt = replace(receipt, session_id="old-session", action_id="old-action-clear")
                clear_id = receipt.action_id
                detail["consumer_fault"] = "REPLAY_FOREIGN_SESSION_AND_ACTION_CLEAR"
                detail["replayed_receipt"] = asdict(receipt)
            owner.accept_clear(receipt, clear_action_id=clear_id)
        if result.cleanup_receipt is None:
            owner.finalize("", marker_id="T1H_AFTER_STOP_CLEAR", world="", player="")
        if case == "t1h_disconnect":
            _command(server, "kick RelaySelf T1h post-STOP DEV disconnect")
            await server.stdin.drain()
            try:
                async with asyncio.timeout(3):
                    while True:
                        await next_tick(session)
            except (RuntimeError, TimeoutError):
                if not session.source_lost:
                    raise
            owner.failed = True
            raise StopDevRejected("source lost before STOP ACK")
        if case == "t1h_motion_residual":
            # Environmental perturbation through the existing Paper console,
            # not a second Self movement writer. Input remains cleared.
            _command(server, "effect give RelaySelf minecraft:levitation 5 1 true")
        marker = "T1H_AFTER_STOP_CLEAR"
        _command(server, f"relaydevsnapshot {marker}")
        await server.stdin.drain()
        report["paper_marker_sent_python_ns"] = time.monotonic_ns()
        detail.update(marker_id=marker, world=fresh.data["snapshot"]["world"],
                      player=fresh.data["snapshot"]["player"])
        if case == "t1h_paper_short":
            # Wait for the real marker to be flushed, then inspect before
            # there can be eight later callbacks. No invented source rows.
            async with asyncio.timeout(2):
                while f"marker_id={marker} " not in (root / "paper.log").read_text():
                    await asyncio.sleep(.002)
        else:
            await asyncio.sleep(.85)
        if case == "t1h_disconnect_after_idle":
            _command(server, "kick RelaySelf T1h late post-idle DEV disconnect")
            await server.stdin.drain()
            await asyncio.sleep(.1)
        # Flush pending source terminal frames through the ORIGINAL single
        # receiver. A historic idle window cannot override a now-dead session.
        try:
            if session.source_lost or server.returncode is not None or session.process_returncode is not None:
                raise RuntimeError("owner source process already ended")
            async with asyncio.timeout(.5):
                live = await _correlated_observe(session, "t1h-before-stop-ack")
            detail["pre_ack_live_probe_seq"] = live.seq
        except Exception as exc:
            owner.failed = True
            detail["pre_ack_liveness_error"] = f"{type(exc).__name__}: {exc}"
            raise StopDevRejected("source lost before STOP ACK") from exc
        ack = owner.finalize(
            (root / "paper.log").read_text(), marker_id=marker,
            world=detail["world"], player=detail["player"],
        )
        report["stop_ack_python_ns"] = time.monotonic_ns()
        detail["stop_ack_dev"] = asdict(ack)
        if case == "t1h_double_ack":
            try:
                owner.finalize((root / "paper.log").read_text(), marker_id=marker,
                               world=detail["world"], player=detail["player"])
            except StopDevRejected:
                detail["double_ack_rejected"] = True
            else:
                raise AssertionError("STOP ACK committed twice")
    except StopDevRejected as exc:
        detail["stop_rejection"] = str(exc)
        detail["stop_ack_absent"] = owner.ack is None
        if expected_rejection is None or expected_rejection not in str(exc) or owner.ack is not None:
            raise
        detail["negative_control_pass"] = True
    else:
        if expected_rejection is not None:
            raise StopDevRejected("negative control unexpectedly acknowledged STOP")
    report["status"] = "T1H_EXPECTATION_MET_AWAITING_RESOURCE_SHUTDOWN"
