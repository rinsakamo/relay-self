"""L-BCG opt-in reader of an original completed S49/L0 epoch.

This adapter never creates a goal, a native observation, a MotorOutcome,
or an admission. Current route B carries a provisional Paper window and no
source-qualified goal/gait/P1/M/hazard vector: the live consumer MUST abstain.
"""
from __future__ import annotations

from dataclasses import dataclass

from adapters.mineflayer.self_body_s50_l1_motion_shadow import (
    compare_l1_motion_attention_shadow,
)
from adapters.mineflayer.self_body_s50_live_next_epoch import LiveNextEpochReadout
from relay_self.l1_bcg_motion_shadow import (
    Attention,
    BCGRejected,
    BCGShadow,
    MotionContext,
    MotorOutcome,
    MotorSourceAdmission,
    compare_conditional_motion_shadow,
)
from relay_self.world_conditioned_choice import WorldConditionedChoice


@dataclass(frozen=True, slots=True)
class LiveBCGHandoff:
    session_id: str
    original_native_ref: str
    original_selection: str
    advice: Attention
    reason: str
    conditional: BCGShadow | None = None
    used_physical_training_worlds: int = 0
    original_l0_choice_kept: bool = True
    action_issues: int = 0
    extra_native_reads: int = 0
    learning_updates: int = 0
    habit_grants: int = 0
    action_authority: bool = False
    goal_success_attested: bool = False
    source_ceiling: str = "ROUTE_B_PROVISIONAL_PAPER_NOT_POST_CLEAR_ATTESTED"


def review_l_bcg_after_original_l0(
    readout: LiveNextEpochReadout,
    original_choice: WorldConditionedChoice,
    *,
    current: MotionContext | None = None,
    training: tuple[MotorOutcome, ...] = (),
    admission: MotorSourceAdmission | None = None,
    memory_enabled: bool = True,
) -> LiveBCGHandoff:
    """Use an *already selected* original L0; never recompute or execute it.

    If the S/R owner has not separately supplied a full verified cue vector,
    do not guess missing goal clearance, gait, fatigue, energy or obstacles.
    This leaves the real existing #653 S50 sample in PROVISIONAL, not training.
    """
    if type(memory_enabled) is not bool or not isinstance(training, tuple):
        raise BCGRejected("typed bounded shadow inputs required")
    original = compare_l1_motion_attention_shadow(readout, original_choice)
    base = dict(
        session_id=original.session_id,
        original_native_ref=original.current_native_source_ref,
        original_selection=original.current_s_choice.value,
    )
    if current is None:
        if training or admission is not None:
            raise BCGRejected("cannot admit training without complete current owner cues")
        return LiveBCGHandoff(
            **base, advice=Attention.DEFER,
            reason="CURRENT_GOAL_GAIT_P1_M_OBSTACLE_SOURCE_NOT_ADMITTED",
        )
    body = readout.current_body
    world = readout.current_world
    if (
        not isinstance(current, MotionContext)
        or current.self_id != body.self_id
        or current.session_id != body.session_id
        or current.world_id != readout.prior_window.paper_world_uuid
        or current.body_source_ref != body.observation.source_ref
        or current.world_source_ref != world.observation.source_ref
        or admission is None
    ):
        raise BCGRejected("current owner cues do not bind original S49 and Body/World")
    shadow = compare_conditional_motion_shadow(
        current=current, training=training,
        admission=admission, memory_enabled=memory_enabled,
    )
    return LiveBCGHandoff(
        **base, advice=shadow.advice, reason=shadow.reason,
        conditional=shadow, used_physical_training_worlds=shadow.training_worlds,
        source_ceiling="EXTERNALLY_ADMITTED_TYPED_CUES_PHYSICAL_PROOF_EXTERNAL",
    )
