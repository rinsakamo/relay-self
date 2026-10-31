"""SelfBody #653: one source-bound L1 *attention* shadow, not trained policy.

Compare next S49 WAIT's original no-experience attention (abstain) with a
trivial prior-S50 sampled-motion cue. L10 requires independently qualified
Goal and histories: here Goal is UNDETERMINED, thus L10=0 and S10/S11=0.
The experience-conditioned difference is EXACTLY reproducible by one-bit
cheap control; do not call this L1 learning or a new Action policy.
"""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from math import isfinite

from adapters.mineflayer.self_body_s50_live_next_epoch import LiveNextEpochReadout
from relay_self.world_conditioned_choice import WorldChoiceKind, WorldConditionedChoice


class L1MotionShadowRejected(ValueError):
    """Foreign original S choice, unqualified sample, or authority escalation."""


class L1AttentionCandidate(str, Enum):
    ABSTAIN_NO_PRIOR = "ABSTAIN_NO_PRIOR_MOTION_EVIDENCE"
    RECHECK_SETTLING = "RECHECK_SAMPLED_POST_CLEAR_MOTION"
    NO_SAMPLED_MOTION = "NO_SAMPLED_MOTION_NOT_PHYSICALLY_STABLE"


class L1MotionContrast(str, Enum):
    CHEAP_EQUIVALENT = "cheap_one_bit_prior_motion_equivalent"
    NO_CHANGE = "no_sampled_motion_no_attention_change"


@dataclass(frozen=True, slots=True)
class L1MotionShadow:
    """Non-executable post-S-choice source review in one original native epoch."""

    session_id: str
    epoch_id: str
    current_native_source_ref: str
    current_native_seq: int
    current_s_choice: WorldChoiceKind
    prior_action_id: str
    prior_paper_prefix_sha256: str
    previous_motion_ticks: tuple[int, ...]
    without_experience: L1AttentionCandidate
    with_experience: L1AttentionCandidate
    cheap_same_information: L1AttentionCandidate
    contrast: L1MotionContrast
    attention_candidate_differs: bool
    cognitive_priority_committed: bool = False
    learned_l1_policy: bool = False
    original_s_choice_kept: bool = True
    current_native_present_unchanged: bool = True
    paper_input_is_full_tick: bool = False
    effective_clear_tick_attested: bool = False
    goal_admitted: bool = False
    l10_training_episodes: int = 0
    s10_updates: int = 0
    s11_grants: int = 0
    p1_wait_admitted: int = 0
    new_native_probes: int = 0
    extra_actions: int = 0
    model_calls: int = 0


def compare_l1_motion_attention_shadow(
    readout: LiveNextEpochReadout, original_s_choice: WorldConditionedChoice,
) -> L1MotionShadow:
    """Retrospective shadow after original S49 decision; NEVER feeds L0.

    The source window was provisional when the *real* L0 probe arrived.
    A later full Paper/Node original audit remains a separate owner gate.
    """
    if (
        not isinstance(readout, LiveNextEpochReadout)
        or not isinstance(original_s_choice, WorldConditionedChoice)
    ):
        raise L1MotionShadowRejected("existing original typed L0 and Body required")
    body, world, window = (
        readout.current_body, readout.current_world, readout.prior_window
    )
    # BodyObservation.source_ref is native-probe:<session>:<seq>:<request>.
    # Split only the owner prefix: request IDs themselves contain colons.
    prior_ref = readout.prior_native_ref.split(":", 3)
    prior_source_valid = (
        len(prior_ref) == 4 and prior_ref[0] == "native-probe"
        and prior_ref[1] == body.session_id
        and prior_ref[2].isascii() and prior_ref[2].isdecimal()
        and bool(prior_ref[3])
    )
    present = body.observation
    world_present = world.observation
    if (
        present is None or world_present is None or body.outcome is not None
        or world.self_body is not body
        or world.self_id != body.self_id or not body.self_id
        or world.session_id != body.session_id
        or world.epoch_id != body.epoch_id
        or body.session_id != original_s_choice.session_id
        or body.session_id != window.session_id
        or present.native_seq != original_s_choice.probe_seq
        or present.request_id != original_s_choice.request_id
        or present.source_provenance != original_s_choice.provenance
        or world_present.native_seq != present.native_seq
        or world_present.request_id != present.request_id
        or world_present.provenance != present.source_provenance
        or original_s_choice.selection is not WorldChoiceKind.WAIT
        or original_s_choice.action_authorized
        or window.action_id != readout.prior_action_id
        or window.paper_prefix_sha256 != readout.prior_window.paper_prefix_sha256
        or readout.prior_native_ref == present.source_ref
        or not prior_source_valid
        or not 0 <= int(prior_ref[2]) < present.native_seq
        or not window.provisional or window.final_source_verified
        or window.node_trace_complete or window.full_tick_input_idle
        or window.physical_stability_attested or window.goal_admitted
        or window.p1_wait_granted or window.l10_pairs
        or window.s10_updates or window.s11_grants
        or len(window.ticks) != 8
        or any(
            type(t.world_tick) is not int
            or type(t.displacement_m) is not float
            or not isfinite(t.displacement_m)
            or t.displacement_m < 0
            or type(t.last_reported_input_active) is not bool
            or (i > 0 and t.world_tick != window.ticks[i - 1].world_tick + 1)
            for i, t in enumerate(window.ticks)
        )
    ):
        raise L1MotionShadowRejected("unqualified L1 shadow S/S50 native lineage")
    original = L1AttentionCandidate.ABSTAIN_NO_PRIOR
    off_motion = tuple(
        t.world_tick for t in window.ticks
        if t.displacement_m > 0 and not t.last_reported_input_active
    )
    # Reusing the exact same one-bit source as the cheapest cheap baseline.
    with_exp = (
        L1AttentionCandidate.RECHECK_SETTLING
        if off_motion else L1AttentionCandidate.NO_SAMPLED_MOTION
    )
    cheap = with_exp
    # Only the positive sampled motion changes the attention candidate from
    # the abstention baseline. Never translate this into WAIT/MOVE_AWAY.
    return L1MotionShadow(
        session_id=body.session_id, epoch_id=body.epoch_id,
        current_native_source_ref=present.source_ref,
        current_native_seq=present.native_seq,
        current_s_choice=original_s_choice.selection,
        prior_action_id=readout.prior_action_id,
        prior_paper_prefix_sha256=window.paper_prefix_sha256,
        previous_motion_ticks=off_motion,
        without_experience=original, with_experience=with_exp,
        cheap_same_information=cheap,
        contrast=(
            L1MotionContrast.CHEAP_EQUIVALENT if off_motion
            else L1MotionContrast.NO_CHANGE
        ),
        attention_candidate_differs=bool(off_motion),
    )
