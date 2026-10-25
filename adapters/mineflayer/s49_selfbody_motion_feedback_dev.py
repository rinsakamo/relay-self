"""SelfBody Motion Feedback v0: DEV-only, Action-closed proprioceptive proxy.

Uses *observed native World displacement* after original S16 closure to
update an imperfect command-duration -> displacement estimate. This is a
World-observed body proxy, not actual biological proprioception, measured
fatigue, an Action issuer, or source-attested World tick time.

One-way:
   original S16 completed Action -> SelfBody motion estimate ->
   bounded *next issued Action* duration proposal -> next S16 result.
"""
from __future__ import annotations

import math
from dataclasses import dataclass, replace

from adapters.mineflayer.execution import (
    MOVE_BACKWARD_DURATION_S,
    MineflayerCommand,
    WorldConsequence,
)
from adapters.mineflayer.m02_paper_dev.s50_boundary import BoundaryRejected
from adapters.mineflayer.self_action_evidence import capture_native_action_evidence


@dataclass(frozen=True, slots=True)
class MotionSample:
    """Recorded command request and actual closed World consequence."""

    action_id: str
    session_id: str
    before_seq: int
    after_seq: int
    requested_duration_s: float
    observed_displacement_m: float
    predicted_displacement_m: float | None
    prediction_error_m: float | None

    def as_report(self) -> dict[str, object]:
        return {
            **self.__dict__,
            "sample_source": "ORIGINAL_S16_NATIVE_WORLD_CONSEQUENCE",
            "realized_control_hold_s_attested": False,
            "world_tick_count_attested": False,
        }


@dataclass(frozen=True, slots=True)
class SelfBodyMotionState:
    """Session-local predictor, not S10 state; no authority to execute."""

    session_id: str
    samples: tuple[MotionSample, ...] = ()

    @property
    def estimated_m_per_requested_s(self) -> float | None:
        if not self.samples:
            return None
        return sum(x.observed_displacement_m for x in self.samples) / sum(
            x.requested_duration_s for x in self.samples
        )

    def observe_closed(
        self, consequence: WorldConsequence, *, requested_duration_s: float,
    ) -> "SelfBodyMotionState":
        if (not isinstance(consequence, WorldConsequence)
                or consequence.session_id != self.session_id
                or type(requested_duration_s) is not float
                or not math.isfinite(requested_duration_s)
                or not 0.05 <= requested_duration_s <= MOVE_BACKWARD_DURATION_S):
            raise BoundaryRejected("SelfBody needs original session and bounded issued duration")
        # Original S16 decoded frames must include verified dispatch, cleanup,
        # source, ordered native frames and actual x/z displacement.
        evidence = capture_native_action_evidence(consequence)
        before = evidence["before_observation"]["seq"]
        after = evidence["after_observation"]["seq"]
        if (any(s.action_id == consequence.action_id for s in self.samples)
                or self.samples and before <= self.samples[-1].after_seq):
            raise BoundaryRejected("SelfBody cannot reuse or reorder original closed Actions")
        value = consequence.movement_distance
        if (type(value) is not float or not math.isfinite(value)
                or value < 0.05 or value > 10.0):
            raise BoundaryRejected("SelfBody observed displacement invalid")
        velocity = self.estimated_m_per_requested_s
        predicted = (
            velocity * requested_duration_s if velocity is not None else None
        )
        sample = MotionSample(
            action_id=consequence.action_id,
            session_id=self.session_id,
            before_seq=before,
            after_seq=after,
            requested_duration_s=requested_duration_s,
            observed_displacement_m=value,
            predicted_displacement_m=predicted,
            prediction_error_m=(value - predicted if predicted is not None else None),
        )
        return replace(self, samples=self.samples + (sample,))


@dataclass(frozen=True, slots=True)
class MotionCorrection:
    """Bounded proposal for a future *already issued* original S49 command."""

    source_action_id: str
    source_session_id: str
    sample_count_before: int
    last_native_after_seq: int
    goal_distance_m: float
    estimated_m_per_requested_s: float
    original_model_duration_s: float
    proposed_duration_s: float
    predicted_displacement_before_m: float
    predicted_displacement_after_m: float
    predicted_error_before_m: float
    bound_relative_step: float
    goal_source: str = "EXPLICIT_DEV_DISTANCE_GOAL_NOT_ORIGINAL_L0_INTENT"

    def as_report(self) -> dict[str, object]:
        return {
            **self.__dict__,
            "model_measures_elapsed_world_ticks": False,
            "native_fatigue_measured": False,
            "new_action_issuer": False,
            "s10_updated": False,
            "qualification_go": False,
            "science_go": False,
        }


def propose_motion_correction(
    state: SelfBodyMotionState, *, current_native_seq: int,
    baseline_duration_s: float, explicit_dev_goal_m: float = 0.45,
    max_relative_step: float = 0.25,
) -> MotionCorrection:
    if (not isinstance(state, SelfBodyMotionState)
            or len(state.samples) < 3
            or type(current_native_seq) is not int
            or current_native_seq <= state.samples[-1].after_seq
            or type(baseline_duration_s) is not float
            or not math.isfinite(baseline_duration_s)
            or not 0.08 <= baseline_duration_s <= MOVE_BACKWARD_DURATION_S
            or type(explicit_dev_goal_m) is not float
            or not math.isfinite(explicit_dev_goal_m)
            or not 0.05 <= explicit_dev_goal_m <= 1.0
            or type(max_relative_step) is not float
            or max_relative_step != 0.25):
        raise BoundaryRejected("motion feedback missing closed history or bounded DEV goal")
    speed = state.estimated_m_per_requested_s
    if speed is None or not math.isfinite(speed) or not 0.25 <= speed <= 10:
        raise BoundaryRejected("motion predictor not estimated from native outcomes")
    raw_duration = explicit_dev_goal_m / speed
    # A small *one-Action* correction only. No loop inside a native Action,
    # no retries and no conversion to fictional whole World ticks.
    proposed = max(
        0.05,
        min(
            MOVE_BACKWARD_DURATION_S,
            max(baseline_duration_s * (1 - max_relative_step),
                min(baseline_duration_s * (1 + max_relative_step), raw_duration)),
        ),
    )
    return MotionCorrection(
        source_action_id=state.samples[-1].action_id,
        source_session_id=state.session_id,
        sample_count_before=len(state.samples),
        last_native_after_seq=state.samples[-1].after_seq,
        goal_distance_m=explicit_dev_goal_m,
        estimated_m_per_requested_s=speed,
        original_model_duration_s=baseline_duration_s,
        proposed_duration_s=proposed,
        predicted_displacement_before_m=speed * baseline_duration_s,
        predicted_displacement_after_m=speed * proposed,
        predicted_error_before_m=explicit_dev_goal_m - speed * baseline_duration_s,
        bound_relative_step=max_relative_step,
    )


def apply_to_next_issued(
    correction: MotionCorrection, command: MineflayerCommand, *,
    current_session_id: str, current_native_seq: int,
) -> MineflayerCommand:
    if (not isinstance(correction, MotionCorrection)
            or not isinstance(command, MineflayerCommand)
            or correction.source_session_id != current_session_id
            or type(current_native_seq) is not int
            or current_native_seq <= correction.last_native_after_seq
            or correction.source_action_id == command.action_id
            or command.duration_s != correction.original_model_duration_s
            or command.control != "back" or command.action_ref != "MOVE_BACKWARD"
            or not 0.05 <= correction.proposed_duration_s <= MOVE_BACKWARD_DURATION_S):
        raise BoundaryRejected("SelfBody cannot authorize or modify foreign native Action")
    updated = replace(command, duration_s=correction.proposed_duration_s)
    if (updated.action_id != command.action_id
            or updated.binding_id != command.binding_id
            or updated.cleanup_action_id != command.cleanup_action_id):
        raise BoundaryRejected("SelfBody correction may only change duration")
    return updated
