"""T1h: bounded DEV STOP injection through the existing S49 owner/receiver.

This fixture issues one independently authorized, already-supported S49 MOVE;
a timed owner-local STOP request interrupts it. Only S49 sends the original
clear_controls. An independent Paper log is assessed AFTER runner shutdown.
"""
from __future__ import annotations

import asyncio
from dataclasses import asdict

from adapters.mineflayer.execution import (
    MineflayerCommand, WorldConsequenceStatus, execute_mineflayer_command,
)
from adapters.mineflayer.m02_paper_dev.s51_paper_physics_dev import _issue, _p
from adapters.mineflayer.s31a_real_server_ci import _command, _correlated_observe
from adapters.mineflayer.t1f_continuation_dev import next_tick
from adapters.mineflayer.t1h_stop_owner_dev import S49DevStopOwner, StopDevRejected
from relay_self.action_supervision import ActionSupervisor


async def run_stop_move_dev(session, server, report, root) -> None:
    """Only owner-local DEV fixture; no new S49 Action authority or reader."""
    supervisor = ActionSupervisor()
    probe = await _correlated_observe(session, "t1h-start-source")
    fresh = await next_tick(session, after_seq=probe.seq)
    if fresh.data["assessment"] != "NO_KNOWN_URGENT_SIGNAL":
        raise StopDevRejected("initial Paper hazard refuses physical STOP fixture")
    sid = session.started.session_id
    owner = S49DevStopOwner(sid)
    session.t1h_stop_owner = owner
    issued = _issue(
        supervisor, "t1h-owned-move", "paper-l0-move", "t1h-stop-intent",
        "single authorized bounded move interrupted by external operator STOP",
        time_base=10,
    )
    session.t1h_active_action_id = issued.action_id
    cmd = MineflayerCommand(
        action_id=issued.action_id,
        binding_id="t1h-owned-move-binding",
        action_ref="MOVE_BACKWARD", effect="set_control",
        control="back", state=True, duration_s=0.75,
        cleanup_action_id=issued.action_id + "-clear",
    )
    result = await execute_mineflayer_command(
        session, cmd, timeout_s=0.5, provenance=_p("t1h-stop-action"),
        l0_interrupt_dev=True, stop_requested_dev=lambda: owner.requested,
    )
    terminal = (
        supervisor.mark_unknown if result.status is not WorldConsequenceStatus.EXECUTED
        else supervisor.record_outcome
    )(issued.action_id, at_ns=20, provenance=_p("t1h-stop-terminal"))
    report["t1h"] = {
        "requested": owner.requested,
        "stop_id": owner.stop_id,
        "source_session": sid,
        "action_id": issued.action_id,
        "action_status": result.status.value,
        "action_error": result.error,
        "supervised_terminal": terminal.state.value,
        "clear_count_expected": 1,
        "cleanup_receipt": asdict(result.cleanup_receipt)
        if result.cleanup_receipt is not None else None,
        "node_shutdown_ack_is_not_stop_ack": True,
        "p1_wait_qualification": False,
    }
    if (
        not owner.requested or result.status is not WorldConsequenceStatus.FAILED
        or result.error is None or "T1h high-level STOP" not in result.error
        or owner.allows_action or result.cleanup_receipt is None
    ):
        raise StopDevRejected("STOP did not interrupt one existing S49 MOVE")
    owner.accept_clear(result.cleanup_receipt, clear_action_id=cmd.cleanup_action_id)

    # Control was already cleared and the original ACK was verified.
    # Only now is a Paper-console marker requested. The independent Paper
    # scheduler emits later pose/input callback rows.
    marker = "T1H_AFTER_STOP_CLEAR"
    _command(server, f"relaydevsnapshot {marker}")
    await server.stdin.drain()
    report["t1h"].update(
        marker_id=marker,
        world=fresh.data["snapshot"]["world"],
        player=fresh.data["snapshot"]["player"],
        next_action_issued=False,
        paper_ack_pending=True,
    )
    await asyncio.sleep(0.85)
    # The independent Paper stdout collector flushes each line. Audit native
    # Paper evidence before process shutdown while the S49 owner is still
    # in charge; absence or inconsistency leaves this STOP unacknowledged.
    ack = owner.finalize(
        (root / "paper.log").read_text(), marker_id=marker,
        world=report["t1h"]["world"], player=report["t1h"]["player"],
    )
    report["t1h"]["stop_ack_dev"] = asdict(ack)
    report["t1h"]["paper_ack_pending"] = False
    report["status"] = "T1H_OWNER_STOP_ACKED_AWAITING_CLEAN_RESOURCE_SHUTDOWN"
