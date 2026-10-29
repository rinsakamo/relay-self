"""Strict G4.3 DEV no-new-motor native tail versus late quiet reference.

Source-observed XZ distances and host times only. The same S49 body remains
in the same World; late quiet samples are not randomized independent trials,
and no causal proof of inertia or zero physical controls is implied.
"""
from __future__ import annotations

import math
from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class G43PassiveNativeSampleDev:
    label: str
    session_id: str
    source_seq: int
    request_id: str
    source: str
    x: float
    z: float
    host_ns: int
    entities_truncated: bool


@dataclass(frozen=True, slots=True)
class G43PassiveNativeTailDev:
    action_id: str
    session_id: str
    clear_seq: int
    s16_seq: int
    samples: tuple[G43PassiveNativeSampleDev, ...]
    early_s16_to_120_m: float
    mid_120_to_300_m: float
    quiet_550_to_800_m: float
    full_s16_to_800_m: float
    early_window_host_ms: float
    quiet_window_host_ms: float
    source: str = "S49_SINGLE_NATIVE_READER_CLEAR_POST_S16_NO_NEW_MOTOR_DEV"
    no_new_s49_motor_during_samples: bool = True
    independently_randomized_control: bool = False
    physical_input_off_per_tick_attested: bool = False
    inertia_causality_attested: bool = False
    world_tick_speed_attested: bool = False


def qualify_g43_passive_native_tail_dev(
    *, action_id: str, session_id: str,
    clear_seq: int, s16_seq: int,
    s16_x: float, s16_z: float, s16_host_ns: int,
    samples: tuple[G43PassiveNativeSampleDev, ...],
    original_action_closed: bool,
) -> G43PassiveNativeTailDev:
    """Fail closed on identity, source ordering, host time, and sample gaps."""
    labels=("EARLY_40","EARLY_120","MID_300","QUIET_550","QUIET_800")
    if (
        type(action_id) is not str or not action_id.startswith("goal-")
        or type(session_id) is not str or not session_id
        or type(clear_seq) is not int or type(s16_seq) is not int
        or not 0<=clear_seq<s16_seq
        or type(s16_host_ns) is not int or s16_host_ns<=0
        or any(type(x) not in (int,float) or not math.isfinite(x) for x in (
            s16_x,s16_z,
        ))
        or type(original_action_closed) is not bool
        or not original_action_closed
        or type(samples) is not tuple or len(samples)!=5
    ):
        raise ValueError("G4.3 requires a closed original Action and finite S16")
    previous_seq=s16_seq
    previous_ns=s16_host_ns
    for index,sample in enumerate(samples):
        if (
            not isinstance(sample,G43PassiveNativeSampleDev)
            or sample.label!=labels[index]
            or sample.session_id!=session_id
            or sample.source!="mineflayer"
            or sample.request_id!=f"{action_id}-g43-off-{index}"
            or type(sample.source_seq) is not int
            or sample.source_seq<=previous_seq
            or type(sample.host_ns) is not int
            or sample.host_ns<=previous_ns
            or type(sample.entities_truncated) is not bool
            or sample.entities_truncated
            or any(type(value) not in (int,float) or not math.isfinite(value)
                   for value in (sample.x,sample.z))
        ):
            raise ValueError("G4.3 refuses stale/foreign/gapped native controls")
        previous_seq=sample.source_seq
        previous_ns=sample.host_ns

    def delta(ax: float,az: float,bx: float,bz: float)->float:
        return math.hypot(ax-bx,az-bz)

    return G43PassiveNativeTailDev(
        action_id=action_id,session_id=session_id,clear_seq=clear_seq,
        s16_seq=s16_seq,samples=samples,
        early_s16_to_120_m=delta(
            s16_x,s16_z,samples[1].x,samples[1].z,
        ),
        mid_120_to_300_m=delta(
            samples[1].x,samples[1].z,samples[2].x,samples[2].z,
        ),
        quiet_550_to_800_m=delta(
            samples[3].x,samples[3].z,samples[4].x,samples[4].z,
        ),
        full_s16_to_800_m=delta(
            s16_x,s16_z,samples[4].x,samples[4].z,
        ),
        early_window_host_ms=(
            samples[1].host_ns-s16_host_ns
        )/1_000_000,
        quiet_window_host_ms=(
            samples[4].host_ns-samples[3].host_ns
        )/1_000_000,
    )
