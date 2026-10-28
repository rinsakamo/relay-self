"""DEV-only XZ target locked before second original S49 Action is issued.

The world can move during input-off gaps. No scalar-distance sums, action
tick equivalence, yaw inference, or invented motor outcome are admitted.
"""
from __future__ import annotations

import math
from dataclasses import dataclass

from adapters.mineflayer.execution import WorldConsequence, WorldConsequenceStatus
from adapters.mineflayer.python_protocol import MineflayerPosition


class S49XZGoalRejected(ValueError):
    pass


@dataclass(frozen=True, slots=True)
class S49LockedXZGoal:
    session_id: str
    first_action_id: str
    first_end_x: float
    first_end_z: float
    forward_x: float
    forward_z: float
    target_x: float
    target_z: float
    offset_m: float
    # World location, not an absolute planning or destination success claim.
    qualification_go: bool = False
    science_go: bool = False


@dataclass(frozen=True, slots=True)
class S49XZReading:
    source_kind: str
    source_seq: int
    current_x: float
    current_z: float
    forward_remaining_m: float
    cross_track_m: float
    euclidean_error_m: float
    stop_reason: str | None
    actual_goal_reached_attested: bool = False
    world_tick_synchronized: bool = False


def _closed(consequence: WorldConsequence, *, action_ref: str) -> None:
    if (
        not isinstance(consequence, WorldConsequence)
        or consequence.status is not WorldConsequenceStatus.EXECUTED
        or consequence.action_ref != action_ref
        or not consequence.action_id
        or not consequence.session_id
        or consequence.before_observation is None
        or consequence.after_observation is None
        or consequence.dispatch_receipt is None
        or consequence.cleanup_receipt is None
        or not consequence.cleanup_attempted
        or consequence.before_observation.session_id != consequence.session_id
        or consequence.after_observation.session_id != consequence.session_id
        or consequence.before_observation.seq >= consequence.after_observation.seq
    ):
        raise S49XZGoalRejected("requires closed original native S16 with source identity")


def lock_goal_after_first_s16(
    first: WorldConsequence, *, target_offset_m: float,
) -> S49LockedXZGoal:
    """Lock WORLD target using first genuine direction and endpoint.

    Must be called before the independent second S14/15 dispatch.
    """
    _closed(first, action_ref="MOVE_FORWARD_SPRINT_DEV")
    if (
        type(target_offset_m) not in (float, int)
        or not math.isfinite(target_offset_m)
        or not 0.50 <= target_offset_m <= 2.50
    ):
        raise S49XZGoalRejected("unbounded target offset")
    a=first.before_observation.snapshot.position
    b=first.after_observation.snapshot.position
    if not isinstance(a,MineflayerPosition) or not isinstance(b,MineflayerPosition):
        raise S49XZGoalRejected("missing native xz")
    dx=b.x-a.x
    dz=b.z-a.z
    distance=math.hypot(dx,dz)
    if not 0.20 <= distance <= 10.0:
        raise S49XZGoalRejected("no usable observed first forward vector")
    if first.movement_distance is None or not math.isclose(
        distance,first.movement_distance,rel_tol=1e-6,abs_tol=1e-6
    ):
        raise S49XZGoalRejected("native XZ and scalar displacement disagree")
    ux,uz=dx/distance,dz/distance
    return S49LockedXZGoal(
        session_id=first.session_id,first_action_id=first.action_id,
        first_end_x=b.x,first_end_z=b.z,
        forward_x=ux,forward_z=uz,
        target_x=b.x+ux*target_offset_m,
        target_z=b.z+uz*target_offset_m,
        offset_m=float(target_offset_m),
    )


def read_xz_goal(
    goal: S49LockedXZGoal, position: MineflayerPosition, *,
    session_id: str, source_kind: str, source_seq: int, tolerance_m: float = 0.20,
) -> S49XZReading:
    if (
        not isinstance(goal,S49LockedXZGoal)
        or not isinstance(position,MineflayerPosition)
        or session_id != goal.session_id
        or source_kind not in ("second_s16_after","fourth_native_probe",
                              "third_s16_after","third_s16_before")
        or type(source_seq) is not int or source_seq < 0
        or type(tolerance_m) not in (int,float)
        or not math.isfinite(tolerance_m)
        or not 0.05 <= tolerance_m <= 0.25
        or not math.isclose(
            math.hypot(goal.forward_x,goal.forward_z),1.0,abs_tol=1e-9
        )
    ):
        raise S49XZGoalRejected("stale, nonnumeric or foreign native XZ observation")
    dx=goal.target_x-position.x
    dz=goal.target_z-position.z
    forward=dx*goal.forward_x+dz*goal.forward_z
    cross=dx*goal.forward_z-dz*goal.forward_x
    error=math.hypot(dx,dz)
    stop=(
        "STOP_PASSED_TARGET_XZ" if forward <= 0
        else "STOP_WITHIN_TARGET_XZ_TOLERANCE" if error <= tolerance_m
        else None
    )
    return S49XZReading(
        source_kind=source_kind,source_seq=source_seq,
        current_x=position.x,current_z=position.z,
        forward_remaining_m=forward,cross_track_m=cross,
        euclidean_error_m=error,stop_reason=stop,
    )


def assess_closed_second_xz(
    goal:S49LockedXZGoal, second:WorldConsequence,
) -> S49XZReading:
    _closed(second,action_ref="MOVE_FORWARD_SPRINT_DEV")
    if second.session_id != goal.session_id or second.action_id == goal.first_action_id:
        raise S49XZGoalRejected("reused/foreign S16 action")
    return read_xz_goal(
        goal,second.after_observation.snapshot.position,
        session_id=second.session_id,source_kind="second_s16_after",
        source_seq=second.after_observation.seq,
    )


def plan_third_walk_xz(
    goal:S49LockedXZGoal,second:WorldConsequence, *,
    second_input_s:float, live_position:MineflayerPosition,
    live_probe_session_id:str, live_probe_seq:int,
    current_threat_distance_m:float,
) -> tuple[S49XZReading,float]:
    """Only a current real probe can provide the next input's remaining XZ."""
    previous=assess_closed_second_xz(goal,second)
    if (
        type(second_input_s) not in (float,int)
        or not math.isfinite(second_input_s)
        or not 0.10 <= second_input_s <= 0.60
        or type(current_threat_distance_m) not in (float,int)
        or not math.isfinite(current_threat_distance_m)
        or not 1.5 <= current_threat_distance_m < 4.0
        or live_probe_seq <= previous.source_seq
    ):
        raise S49XZGoalRejected("fresh safe second→third S16/probe ordering required")
    reading=read_xz_goal(
        goal,live_position,session_id=live_probe_session_id,
        source_kind="fourth_native_probe",source_seq=live_probe_seq,
    )
    if reading.stop_reason is not None:
        raise S49XZGoalRejected("third WALK forbidden: target already reached or passed")
    if abs(reading.cross_track_m)>0.25:
        raise S49XZGoalRejected("third WALK forbidden: off-axis position")
    mean_speed=second.movement_distance/second_input_s
    if not 0.1 <= mean_speed <= 20:
        raise S49XZGoalRejected("invalid second measured speed")
    return reading,max(0.10,min(0.60,reading.forward_remaining_m/mean_speed))
