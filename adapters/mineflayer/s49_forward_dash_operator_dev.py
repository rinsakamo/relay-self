"""Explicit operator-owned DEV forward motor measurement in an ORIGINAL S49 session.

This is NOT an S49-issued MOVE_FORWARD Action: original S49 authorizes only
MOVE_BACKWARD. It runs only while the original S49 host is suspended AFTER
the second S16 terminal, through that same MineflayerProcessSession reader,
and is reported separately. Never send its motor effect to S16/S10 or M0/P1.
"""
from __future__ import annotations

import asyncio
import math
import time
from pathlib import Path
from typing import Callable

from adapters.mineflayer.process_session import MineflayerProcessSession
from adapters.mineflayer.python_protocol import (
    MineflayerAdapterErrorMessage,
    MineflayerCommandError,
    MineflayerConnectionEnd,
    MineflayerEffectResult,
    MineflayerObservation,
)

CONFIRM = "S49-EXTRA-FORWARD-OPERATOR-MOTOR-DEV"
ID = "s49-forward-operator-dev"
DURATION_S = 0.9


class OperatorDashDevRejected(ValueError):
    """The separate, explicitly operator-authorized DEV motor has failed."""


async def _receive_effect(session: MineflayerProcessSession, action: str,
                          effect: str, *, timeout: float = 8.0) -> None:
    until = time.monotonic() + timeout
    while time.monotonic() < until:
        message = await asyncio.wait_for(session.receive(), until - time.monotonic())
        if isinstance(message, (MineflayerConnectionEnd, MineflayerCommandError,
                                MineflayerAdapterErrorMessage)):
            raise OperatorDashDevRejected("native session error during operator motor")
        if isinstance(message, MineflayerEffectResult):
            if (message.action_id != action or message.effect != effect
                    or message.result != "applied"):
                raise OperatorDashDevRejected("foreign or rejected motor receipt")
            return
        # One owner consumes incidental native entity/move observations too.
    raise OperatorDashDevRejected("operator motor effect receipt timed out")


async def _probe(session: MineflayerProcessSession, request: str) -> MineflayerObservation:
    await session.send_observe(request)
    until = time.monotonic() + 8.0
    while time.monotonic() < until:
        msg = await asyncio.wait_for(session.receive(), until - time.monotonic())
        if isinstance(msg, (MineflayerConnectionEnd, MineflayerCommandError,
                            MineflayerAdapterErrorMessage, MineflayerEffectResult)):
            raise OperatorDashDevRejected("foreign native frame during operator probe")
        if isinstance(msg, MineflayerObservation) and msg.kind == "probe":
            if msg.request_id != request or msg.session_id != session.started.session_id:
                raise OperatorDashDevRejected("uncorrelated native probe")
            return msg
    raise OperatorDashDevRejected("native operator probe timed out")


def _xz_distance(before: MineflayerObservation, after: MineflayerObservation) -> float:
    dx = after.snapshot.position.x - before.snapshot.position.x
    dz = after.snapshot.position.z - before.snapshot.position.z
    return math.hypot(dx, dz)


async def _run_forward(
    session: MineflayerProcessSession, *, label: str,
) -> dict[str, object]:
    before = await _probe(session, ID + "-" + label + "-before")
    forward_id = ID + "-" + label + "-forward"
    sprint_id = ID + "-" + label + "-sprint"
    clear_id = ID + "-" + label + "-clear"
    attempted = False
    try:
        attempted = True
        await session.send_set_control(forward_id, control="forward", state=True)
        await _receive_effect(session, forward_id, "set_control")
        await session.send_set_control(sprint_id, control="sprint", state=True)
        await _receive_effect(session, sprint_id, "set_control")
        # Bounded host duration is NOT treated as Paper-effective ticks.
        await asyncio.sleep(DURATION_S)
    finally:
        if attempted:
            await session.send_clear_controls(clear_id)
            await _receive_effect(session, clear_id, "clear_controls")
    # Allow deceleration to settle before observing next episode.
    await asyncio.sleep(0.45)
    after = await _probe(session, ID + "-" + label + "-after")
    return {
        "native_before_seq": before.seq,
        "native_after_seq": after.seq,
        "native_session_id": session.started.session_id,
        "observed_displacement_m": _xz_distance(before, after),
        "host_requested_hold_s": DURATION_S,
        "host_hold_is_paper_effective_ticks": False,
        "original_s49_action": False,
        "original_s16_terminal": False,
        "m0_posted": False,
        "p1_updated": False,
    }


async def _paper_wait_for(
    log: Path, offset: int, needle: str, *, timeout: float = 10.0,
) -> str:
    until = time.monotonic() + timeout
    while time.monotonic() < until:
        with log.open("rb") as source:
            source.seek(offset)
            raw = source.read(131072)
        if len(raw) == 131072:
            raise OperatorDashDevRejected("bounded Paper diagnostic window exceeded")
        window = raw.decode("utf-8")
        if ("S49_DASH_DEV_DENIED" in window
                or "S49_DASH_DEV_CLEANUP_UNCONFIRMED" in window):
            raise OperatorDashDevRejected("Paper DASH arm or cleanup rejected")
        if needle in window:
            return window
        await asyncio.sleep(0.1)
    raise OperatorDashDevRejected("Paper DASH callback missing: " + needle)


async def run_forward_operator_dev(
    *, session: MineflayerProcessSession,
    paper_server: asyncio.subprocess.Process,
    paper_log: Path,
    subject_uuid: str,
    send_console: Callable[[asyncio.subprocess.Process, str], None],
    confirmation: str,
) -> dict[str, object]:
    """Single operator DEV motor with RUN baseline then full forward DASH.

    Caller must hold original S49 one-session receiver and have completed the
    original second Action. Original S49's receipt list remains unchanged.
    """
    if (confirmation != CONFIRM or paper_server.returncode is not None
            or paper_server.stdin is None or session.process_returncode is not None):
        raise OperatorDashDevRejected("missing explicit operator motor authorization")
    baseline = await _run_forward(session, label="run")
    if baseline["observed_displacement_m"] < 0.3:
        raise OperatorDashDevRejected("baseline RUN did not move in real World")

    action = ID + "-dash"
    offset = paper_log.stat().st_size
    send_console(
        paper_server, "relays49dasharm " + action + " " +
        session.started.session_id + " " + subject_uuid + " 1.0",
    )
    await paper_server.stdin.drain()
    await _paper_wait_for(paper_log, offset, "S49_DASH_DEV_ARM action_id=" + action + " ")
    sample_offset = paper_log.stat().st_size
    try:
        dash = await _run_forward(session, label="dash")
    finally:
        send_console(
            paper_server, "relays49dashoff " + action + " " +
            session.started.session_id + " " + subject_uuid,
        )
        await paper_server.stdin.drain()
    window = await _paper_wait_for(
        paper_log, sample_offset, "S49_DASH_DEV_COMPLETE action_id=" + action + " ",
    )
    rows = [row for row in window.splitlines() if
            "S49_DASH_DEV_TICK action_id=" + action + " " in row]
    ending = [row for row in window.splitlines() if
              "S49_DASH_DEV_COMPLETE action_id=" + action + " " in row]
    forward = [row for row in rows if "modifier_applied=true" in row]
    if (len(ending) != 1 or not rows
            or "modifier_applied=false" not in ending[0]):
        raise OperatorDashDevRejected("DASH World receipt missing or not cleaned")
    return {
        "status": "DEV_OPERATOR_FORWARD_DASH_WORLD_MEASURED",
        "classification": "DEV_ONLY",
        "original_s49_authorized_forward": False,
        "operator_extra_motor_command": True,
        "same_original_session_id": session.started.session_id,
        "baseline_run": baseline,
        "full_dash": dash,
        "paper_callback_ticks": len(rows),
        "paper_forward_modifier_ticks": len(forward),
        "paper_modifier_removed": True,
        "observed_displacement_ratio": (
            dash["observed_displacement_m"] / baseline["observed_displacement_m"]
        ),
        "effective_paper_input_tick_alignment_attested": False,
        "side_cap_verified": False,
        "back_cap_verified_by_other_run": True,
        "m0_posted": False,
        "p1_native_updated": False,
        "qualification_go": False,
        "science_go": False,
    }
