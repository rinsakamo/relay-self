"""G4.2 DEV host latency and unpowered drift candidate from original S49.

The host monotonic clock measures callback-to-ACK receipt latency, not
Minecraft physical ticks. Native XZ samples bound apparent after-clear
motion but do not by themselves distinguish inertia from other World forces.
"""
from __future__ import annotations

import math
from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class G42NativeWindowDev:
    action_id: str
    session_id: str
    brake_seq: int | None
    clear_seq: int
    after_seq: int
    next_seq: int
    brake_to_clear_ack_host_ms: float | None
    after_s16_to_next_probe_host_ms: float
    postclear_delta_x_m: float
    postclear_delta_z_m: float
    postclear_drift_candidate_m: float
    source: str = "ORIGINAL_NATIVE_S49_AFTER_CLEAR_TO_NEXT_PROBE_DEV"
    inertia_causality_attested: bool = False
    paper_tick_latency_attested: bool = False
    motor_speed_change_attested: bool = False


def qualify_g42_native_window_dev(
    *, action_id: str, session_id: str,
    brake_seq: int | None, brake_host_ns: int | None,
    clear_seq: int, clear_host_ns: int,
    after_seq: int, after_x: float, after_z: float,
    after_host_ns: int, next_seq: int, next_x: float, next_z: float,
    next_host_ns: int,
) -> G42NativeWindowDev:
    """Require the same ordered original S49 source and monotonic host times."""
    if (
        type(action_id) is not str or not action_id.startswith("goal-")
        or type(session_id) is not str or not session_id
        or any(type(v) is not int or v < 0 for v in (
            clear_seq, after_seq, next_seq, clear_host_ns,
            after_host_ns, next_host_ns,
        ))
        or not 0 <= clear_seq < after_seq < next_seq
        or not 0 < clear_host_ns <= after_host_ns < next_host_ns
        or any(type(v) not in (float, int) or not math.isfinite(v) for v in (
            after_x, after_z, next_x, next_z,
        ))
        or (brake_seq is None) != (brake_host_ns is None)
    ):
        raise ValueError("G4.2 refuses nonmonotonic or foreign action window")
    latency=None
    if brake_seq is not None:
        if (
            type(brake_seq) is not int or brake_seq < 0
            or type(brake_host_ns) is not int or brake_host_ns <= 0
            or brake_seq >= clear_seq or brake_host_ns >= clear_host_ns
        ):
            raise ValueError("G4.2 brake-to-CLEAR requires original ordered ACK")
        latency=(clear_host_ns-brake_host_ns)/1_000_000
    dx=next_x-after_x
    dz=next_z-after_z
    return G42NativeWindowDev(
        action_id=action_id,session_id=session_id,
        brake_seq=brake_seq,clear_seq=clear_seq,
        after_seq=after_seq,next_seq=next_seq,
        brake_to_clear_ack_host_ms=latency,
        after_s16_to_next_probe_host_ms=(
            next_host_ns-after_host_ns
        )/1_000_000,
        postclear_delta_x_m=dx,postclear_delta_z_m=dz,
        postclear_drift_candidate_m=math.hypot(dx,dz),
    )
