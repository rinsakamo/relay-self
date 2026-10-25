"""P1-aware, read-only one-tick movement feasibility beside frozen S42.

World geometry remains the original *post-WAIT* native probe in BOTH
comparisons. The earlier modeled after-MOVE capability is explicitly
counterfactual at this geometry. The new comparison never authorizes
Action, changes S42 selection, or silently changes MOVE to WAIT.
"""
from __future__ import annotations

import math

from adapters.mineflayer.m02_paper_dev.s50_boundary import BoundaryRejected
from adapters.mineflayer.python_protocol import MineflayerObservation
from adapters.mineflayer.s49_p1_l0_shadow_dev import preview_postwait_l0_dev
from adapters.mineflayer.s49_p1_self_body_dev import P1DevSelfBodyHandoff
from experiments.fatigue_p1 import FatigueProfile
from relay_self.learning import LearningPreferenceState
from relay_self.self_body import SelfBodyView


def compare_body_capability_l0_dev(
    body: SelfBodyView,
    native: MineflayerObservation,
    handoff: P1DevSelfBodyHandoff,
    reviewed: dict,
    profile: FatigueProfile,
    retained: LearningPreferenceState,
) -> dict[str, object]:
    """One native World snapshot; two model-only one-tick capacity envelopes.

    The demanded gait is P1's existing nominal 1-block/tick profile field,
    not the S49 Action's aggregated displacement/time. The result therefore
    evaluates a hypothetical **one tick** speed, not the historical MOVE.
    """
    shadow = preview_postwait_l0_dev(
        body, native, handoff, reviewed, profile, retained,
    )
    if (shadow["session_id"] != handoff.session_id
            or shadow["native_seq"] != native.seq
            or not isinstance(profile, FatigueProfile)
            or not profile.enabled
            or not math.isfinite(profile.nominal_move_limit_blocks)
            or profile.nominal_move_limit_blocks <= 0
            or shadow["original_s42_selection"] not in ("WAIT", "MOVE_AWAY")
            or shadow["fresh_action_grant_issued"] is not False
            or shadow["actual_reactive_l0_decide_called"] is not False):
        raise BoundaryRejected("body capability comparison requires complete passive shadow")
    demand = profile.nominal_move_limit_blocks
    before = shadow["after_move_p1_model_max_blocks_per_tick"]
    after = shadow["after_wait_p1_model_max_blocks_per_tick"]
    if (not all(type(v) in (float, int) and math.isfinite(v) and v >= 0
                for v in (before, after))
            or before > demand or after > demand
            or before > after):
        raise BoundaryRejected("unexpected P1 capability envelope")
    def envelope(limit: float) -> str:
        if shadow["original_s42_selection"] == "WAIT":
            return "S42_WAIT_UNCHANGED"
        if limit + 1e-9 < demand:
            return "MOVE_AWAY_SCALE_TO_CAPACITY_MODEL_ONLY"
        return "MOVE_AWAY_NOMINAL_GAIT_MODEL_ONLY"

    before_case = envelope(before)
    after_case = envelope(after)
    return {
        "status": "DEV_P1_L0_S42_NOMINAL_GAIT_COMPARISON",
        "session_id": handoff.session_id,
        "action_id": handoff.action_id,
        "world": handoff.world,
        "observer_run_id": handoff.observer_run_id,
        "paper_window_sha256": handoff.model_source_digest,
        "native_seq": shadow["native_seq"],
        "native_request_id": shadow["native_request_id"],
        "body_epoch_id": shadow["body_epoch_id"],
        "s42_selection_unchanged": shadow["original_s42_selection"],
        "s42_distance_m": shadow["s42_distance_m"],
        "nominal_one_tick_demand_blocks": demand,
        "modeled_after_move_one_tick_capacity_blocks": before,
        "modeled_after_wait_one_tick_capacity_blocks": after,
        "after_move_on_postwait_world_counterfactual": before_case,
        "after_wait_on_actual_postwait_world_model": after_case,
        "counterfactual_same_world_geometry_not_native_at_move_time": True,
        "original_s49_action_displacement_is_not_one_tick_demand": True,
        "original_l0_policy_modified": False,
        "original_l0_decide_called": False,
        "body_model_used_as_physical_authority": False,
        "new_action_grant_issued": False,
        "actual_native_actions_added": 0,
        "additional_native_reads": 0,
        "production_p1_state_updated": False,
        "qualification_go": False,
        "science_go": False,
    }
