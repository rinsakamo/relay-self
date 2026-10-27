"""DEV counterfactual P1 WAIT recovery inside the causally fenced S49 Paper interval.

Read-only. Body stillness and no new action from the original S49 issuer are
NOT global physical WAIT attestation. Never apply this projection to live P1,
the S49 owner, SelfBody, or the M0 ledger.
"""
from __future__ import annotations

import math

from experiments.fatigue_p1 import FatigueProfile, FatigueState
from experiments.p1_gait_dev import GaitRatesDev, GaitTickDev, advance_gait_dev


class P1CausalShadowRejected(ValueError):
    """Invalid DEV-only fence, P1 replay, or accounting boundary."""


def _finite(value: object) -> bool:
    return type(value) in (int, float) and math.isfinite(value)


def project_p1_fenced_wait_shadow_dev(
    *, fence: dict, p1_replay: dict, action_bracket: dict,
    profile: FatigueProfile, session_id: str, first_action_id: str,
    second_action_id: str, original_m0_energy_remaining: float,
    rates: GaitRatesDev = GaitRatesDev(),
) -> dict:
    """What-if WAIT for every *observed* fenced static tick, not actual WAIT.

    The replayed P1 final value belongs to the first DASH. Its value just
    before the candidate window is UNKNOWN because intermediate World ticks
    have no WAIT/MOVE activity classification. Holding it fixed over that gap
    is an explicitly counterfactual starting condition, not a measurement.
    The original S49/World reviewers must be called before this function:
    correlated Python dictionaries alone cannot authenticate a producer.
    """
    if (
        type(fence) is not dict or type(p1_replay) is not dict
        or type(action_bracket) is not dict
        or not isinstance(profile, FatigueProfile) or profile.enabled is not True
        or not isinstance(rates, GaitRatesDev)
        or type(session_id) is not str or not session_id
        or type(first_action_id) is not str or not first_action_id
        or type(second_action_id) is not str or not second_action_id
        or first_action_id == second_action_id
        or not _finite(original_m0_energy_remaining)
        or original_m0_energy_remaining < 0
    ):
        raise P1CausalShadowRejected("invalid read-only P1 shadow inputs")
    if (
        fence.get("classification") != "S49_CAUSAL_OWNER_PAPER_STATIC_SUBWINDOW_DEV_ONLY"
        or fence.get("session_id") != session_id
        or fence.get("action_ids") != [first_action_id, second_action_id]
        or fence.get("boundary_guard_ticks_each_side") != 2
        or any(fence.get(field) is not True for field in (
            "owner_original_first_s16_terminal_before_start_delivery",
            "owner_original_second_s15_issue_after_end_delivery",
            "node_original_first_clear_before_start_delivery",
            "node_original_second_set_after_end_delivery",
            "original_issuer_no_second_issue_during_causal_subwindow",
            "node_local_controls_off_sampled_between_first_clear_second_set",
            "paper_body_static_measured_inside_causal_subwindow",
        ))
        or any(fence.get(field) is not False for field in (
            "same_process_native_paper_clock_epoch_calibrated",
            "node_physics_paper_tick_1_to_1_attested",
            "global_world_quiescence_attested", "global_action_absence_attested",
            "physical_WAIT_admitted", "P1_recovery_posted", "M0_posted",
            "qualification_go", "science_go",
        ))
        or p1_replay.get("single_p1_model_replayed") is not True
        or p1_replay.get("source_qualified") is not False
        or p1_replay.get("p1_ledger_posted") is not False
        or p1_replay.get("m0_ledger_posted") is not False
        or action_bracket.get("original_owner_release") is not True
        or action_bracket.get("independent_source_attested") is not False
    ):
        raise P1CausalShadowRejected("fence or first DASH replay not safely screened")
    start = fence.get("paper_first_owner_fence_delivery_tick")
    end = fence.get("paper_second_owner_fence_delivery_tick")
    low = fence.get("paper_causal_subwindow_first_tick")
    high = fence.get("paper_causal_subwindow_last_tick")
    count = fence.get("paper_causal_subwindow_contiguous_still_ticks")
    interval = fence.get("paper_stillness_candidate_interval")
    last_p1 = action_bracket.get("last_tick")
    replayed = p1_replay.get("world_ticks_replayed")
    initial = p1_replay.get("fatigue_initial")
    prior = p1_replay.get("fatigue_final")
    if (
        any(type(v) is not int for v in (
            start, end, low, high, count, last_p1, replayed
        ))
        or not (0 <= last_p1 < start < low <= high < end)
        or low < start + 2 or high > end - 2
        or type(interval) is not list or len(interval) != 2
        or any(type(t) is not int for t in interval)
        or not interval[0] <= low <= high <= interval[1]
        or count != high - low + 1 or not 8 <= count <= 1200
        or action_bracket.get("elapsed_callbacks") != replayed
        or not 1 <= replayed <= 80
        or not _finite(initial) or not _finite(prior)
        or not (0 <= prior <= profile.capacity)
        or not math.isclose(initial, profile.initial, abs_tol=1e-12)
    ):
        raise P1CausalShadowRejected("World tick continuity or P1 initial boundary missing")
    # Neither the unclassified ticks after the first DASH nor its first
    # physical WAIT status can be inferred from the S49 Action owner fence.
    gap_ticks = low - last_p1 - 1
    state = FatigueState(session_id, profile.sha256, low - 1, float(prior))
    for tick in range(low, high + 1):
        transition = advance_gait_dev(
            profile, state, GaitTickDev(session_id, tick, "WAIT"), rates=rates,
        )
        if transition.added_m0_charge != 0 or transition.m0_ledger_posted:
            raise P1CausalShadowRejected("unexpected M0 mutation in WAIT projection")
        state = transition.after
    recovered = float(prior) - state.fatigue
    if not math.isfinite(recovered) or recovered < 0:
        raise P1CausalShadowRejected("nonfinite or negative counterfactual recovery")
    return {
        "classification": "P1_CAUSALLY_FENCED_STATIC_WAIT_COUNTERFACTUAL_UNAPPLIED_DEV_ONLY",
        "session_id": session_id,
        "action_ids": [first_action_id, second_action_id],
        "paper_stillness_tick_interval": [low, high],
        "candidate_ticks": count,
        "normalized_world_seconds_if_20tps": count / 20,
        "unclassified_world_ticks_after_first_dash_before_candidate": gap_ticks,
        "p1_first_dash_replayed_final_fatigue": float(prior),
        "starting_fatigue_assumption": "HOLD_FIRST_DASH_FINAL_OVER_UNKNOWN_GAP",
        "starting_fatigue_not_observed_at_candidate": True,
        "counterfactual_activity": "WAIT_FOR_ALL_CANDIDATE_TICKS_ONLY",
        "wait_recovery_rate_per_normalized_second": rates.wait_recovery_per_s,
        "single_existing_p1_profile_sha256": profile.sha256,
        "counterfactual_start_fatigue": float(prior),
        "counterfactual_end_fatigue": state.fatigue,
        "counterfactual_p1_recovered_if_all_wait": recovered,
        "verified_physical_WAIT_ticks": 0,
        "p1_recovery_applied": 0.0,
        "source_bound_tick_created": False,
        "actual_p1_state_updated": False,
        "original_m0_energy_remaining_unchanged": original_m0_energy_remaining,
        "m0_posted": False,
        "action_issued": False,
        "global_world_quiescence_attested": False,
        "physical_wait_admitted": False,
        "qualification_go": False,
        "science_go": False,
    }
