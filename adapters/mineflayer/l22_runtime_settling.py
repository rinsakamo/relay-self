"""L22 opt-in, single-reader post-S16 settling *diagnostic* window.

Only existing S7 MineflayerSession.send_observe()/receive() are used.
Sampled quiet cannot establish continuous World tick physical idle.
"""
from __future__ import annotations

import asyncio
import math
from dataclasses import dataclass

from adapters.mineflayer.process_session import MineflayerProcessSession
from adapters.mineflayer.python_protocol import MineflayerObservation

SCHEMA = "L22_RUNTIME_SETTLING_SAMPLES_V1"
QUIET_PROBES = 3
MAX_FRAMES_PER_PROBE = 120
PROBE_GAP_SECONDS = 0.1
TIMEOUT_PER_PROBE_SECONDS = 5.0


class L22RuntimeRejected(ValueError):
    """No second actor, foreign stream, missing probe or unknown event accepted."""


@dataclass(frozen=True, slots=True)
class L22RuntimeWindow:
    schema: str
    session_id: str
    action_id: str
    request_ids: tuple[str, ...]
    observed_probe_seqs: tuple[int, ...]
    observed_move_seqs: tuple[int, ...]
    quiet_streak: int
    window_status: str
    reason: str
    accepted_goal_status: str = "UNDETERMINED"
    stable_world_ticks_attested: bool = False
    physically_stopped_proven: bool = False
    qualified_real_learning_pairs: int = 0
    s10_updates: int = 0
    s11_grants: int = 0


async def observe_bounded_settling(
    session: MineflayerProcessSession, *,
    session_id: str, action_id: str, max_probes: int = 6,
    drift_limit_m: float = 0.05,
) -> L22RuntimeWindow:
    """Sample without Action grants or motor calls; return after <=8 probes.

    'QUIET_SAMPLES_ONLY' means only no native movement detected during the
    sampled intervals. No Paper input-idle or tick-contiguous evidence exists.
    """
    if (
        type(max_probes) is not int or not 3 <= max_probes <= 8
        or type(drift_limit_m) not in (int, float)
        or not math.isfinite(drift_limit_m)
        or not 0 < drift_limit_m <= 0.1
        or not isinstance(session_id, str) or not session_id
        or not isinstance(action_id, str) or not action_id
        or session.started.session_id != session_id
    ):
        raise L22RuntimeRejected("invalid bounded settling opt-in or source identity")
    requests: list[str] = []
    probe_seqs: list[int] = []
    moves: list[int] = []
    prev: MineflayerObservation | None = None
    quiet = 0
    for i in range(1, max_probes + 1):
        # A monotonic host delay is *not* evidence of elapsed World ticks.
        await asyncio.sleep(PROBE_GAP_SECONDS)
        rid = f"l22:{session_id}:{action_id}:settle-{i}"
        await session.send_observe(rid)
        requests.append(rid)
        moving = False
        probe: MineflayerObservation | None = None
        loop = asyncio.get_running_loop()
        deadline = loop.time() + TIMEOUT_PER_PROBE_SECONDS
        for _ in range(MAX_FRAMES_PER_PROBE):
            remaining = deadline - loop.time()
            if remaining <= 0:
                raise L22RuntimeRejected("settling probe deadline expired")
            try:
                msg = await asyncio.wait_for(
                    session.receive(), timeout=remaining,
                )
            except (TimeoutError, EOFError) as exc:
                raise L22RuntimeRejected("settling observation timed out or ended") from exc
            if (
                not isinstance(msg, MineflayerObservation)
                or msg.session_id != session_id
            ):
                raise L22RuntimeRejected("foreign/unsafe physical frame during settling")
            if msg.kind == "move" and msg.request_id is None:
                moves.append(msg.seq)
                moving = True
            elif msg.kind == "entities" and msg.request_id is None:
                continue  # other entity updates are not physical stillness
            elif msg.kind == "probe" and msg.request_id == rid:
                probe = msg
                break
            else:
                raise L22RuntimeRejected("foreign/probe/motor event in settling window")
        if probe is None:
            raise L22RuntimeRejected("bounded settling probe not received")
        probe_seqs.append(probe.seq)
        if prev is not None:
            shift = math.hypot(
                prev.snapshot.position.x - probe.snapshot.position.x,
                prev.snapshot.position.z - probe.snapshot.position.z,
            )
            if shift > drift_limit_m:
                moving = True
        quiet = 0 if moving else quiet + 1
        prev = probe
        if quiet >= QUIET_PROBES:
            break
    quiet_only = quiet >= QUIET_PROBES
    return L22RuntimeWindow(
        schema=SCHEMA, session_id=session_id, action_id=action_id,
        request_ids=tuple(requests), observed_probe_seqs=tuple(probe_seqs),
        observed_move_seqs=tuple(moves), quiet_streak=quiet,
        window_status=(
            "QUIET_SAMPLES_ONLY" if quiet_only else "UNDETERMINED"
        ),
        reason=(
            "NO_ATTESTED_WORLD_TICK_IDLE"
            if quiet_only else "SETTLING_NOT_RESOLVED_WITHIN_BUDGET"
        ),
    )
