"""T1i: reuse T1h's S49 STOP owner on an existing multi-epoch MOVE.

The original S49 owner issues the one clear and receives its ACK.  Only a
bounded Paper callback window can qualify a scoped DEV STOP ACK.
Never infer P1 qualified WAIT, high-TPS timing, or EAT physical cancellation.
"""
from __future__ import annotations

import asyncio
from dataclasses import asdict
from pathlib import Path

from adapters.mineflayer.execution import WorldConsequenceStatus, WorldConsequence
from adapters.mineflayer.s31a_real_server_ci import _command, _correlated_observe
from adapters.mineflayer.t1h_stop_owner_dev import S49DevStopOwner, StopDevRejected
from relay_self.action import ActionState


def require_stop_permits_action(owner: S49DevStopOwner | None) -> None:
    if owner is not None and not owner.allows_action:
        raise StopDevRejected("T1i latched STOP forbids next supervised Action")


async def finish_multi_epoch_move_stop(
    session, server, original_paper: dict, outcome: WorldConsequence,
    terminal, owner: S49DevStopOwner, paper_log: Path,
) -> dict:
    """Observe S49 clear → separate Paper marker → live probe → bounded ACK."""
    if (
        not owner.requested or owner.failed or owner.ack is not None
        or owner.active_action_id != outcome.action_id
        or outcome.session_id != owner.session_id
        or outcome.status is not WorldConsequenceStatus.FAILED
        or terminal.state is not ActionState.UNKNOWN
        or outcome.cleanup_receipt is None
        or getattr(session, "source_lost", False)
    ):
        raise StopDevRejected("T1i interrupted MOVE provenance/owner invalid")
    owner.accept_clear(
        outcome.cleanup_receipt, clear_action_id=outcome.action_id + "-clear",
    )
    marker = "T1I_MULTI_AFTER_CLEAR"
    _command(server, f"relaydevsnapshot {marker}")
    await server.stdin.drain()
    await asyncio.sleep(.85)
    # The sole session receiver is still the original Action owner's receiver.
    # No fresh Action can be issued while it is checking the post-clear source.
    try:
        if getattr(session, "source_lost", False) or session.process_returncode is not None:
            raise StopDevRejected("T1i native source lost")
        live = await asyncio.wait_for(
            _correlated_observe(session, "t1i-before-stop-ack"), timeout=.75,
        )
        if live.session_id != owner.session_id:
            raise StopDevRejected("foreign T1i liveness probe")
        ack = owner.finalize(
            paper_log.read_text(), marker_id=marker,
            world=original_paper["world"], player=original_paper["player"],
        )
    except Exception:
        owner.failed = True
        raise
    return {
        "stop_ack_dev": asdict(ack), "post_clear_live_probe_seq": live.seq,
        "terminal": terminal.state.value, "action_status": outcome.status.value,
        "next_action_issued": False, "p1_wait_qualified": False,
        "independent_full_tick_census": False,
    }
