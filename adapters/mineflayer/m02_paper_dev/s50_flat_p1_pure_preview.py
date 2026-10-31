"""Optional offline cross-branch P1 evaluator preview for FLAT MOVE-only witnesses.

Caller must explicitly supply the P1 #626 module from its pinned owner checkout.
This creates brand-new, isolated hypothetical states for *each* contiguous
positive-motion window, never carries a state across UNKNOWN World ticks,
never emits an admitted SourceBoundTick, and never controls the World.
"""
from __future__ import annotations

import math

from adapters.mineflayer.m02_paper_dev.s50_boundary import BoundaryRejected
from adapters.mineflayer.m02_paper_dev.s50_flat_p1_tick_lineage import (
    contiguous_motion_windows,
)

P1_PROFILE_EXPECTED_RATE = 0.04


def replay_p1_motion_only_preview(ledger: dict, *, p1) -> dict:
    """Dry-run the original P1 physics, without externally authenticating source."""
    windows = contiguous_motion_windows(ledger)
    if not all(callable(getattr(p1, name, None))
               for name in ("initial_state", "advance", "capability")):
        raise BoundaryRejected("missing actual P1 evaluator owner functions")
    if not callable(getattr(p1, "FatigueProfile", None)):
        raise BoundaryRejected("missing P1 owner profile")
    if not callable(getattr(p1, "FatigueFrame", None)):
        raise BoundaryRejected("missing P1 owner Body frame")
    profile = p1.FatigueProfile(enabled=True)
    if (not math.isclose(profile.move_per_block.value, P1_PROFILE_EXPECTED_RATE)
            or not math.isclose(profile.wait_recovery_per_world_tick.value, 0.10)):
        raise BoundaryRejected("P1 owner rates changed; re-register preview")
    ticks = ledger["ticks"]
    by_tick = {row["world_full_time"]: row for row in ticks}
    results = []
    cap_conflicts = 0
    for i, window in enumerate(windows):
        start = window["first_world_tick"]
        end = window["last_world_tick"]
        session = f"DEV-CANDIDATE-{ledger['arm']}-{ledger['world']}-{i}"
        state = p1.initial_state(profile, session, world_tick=start - 1)
        transitions = []
        conflict = None
        for tick in range(start, end + 1):
            observed = by_tick[tick]["native_horizontal_blocks"]
            if observed > p1.capability(profile, state).max_move_blocks_per_world_tick:
                # No post-hoc body cap enforcement. Save the original overrun.
                conflict = {"world_tick": tick, "observed_blocks": observed,
                            "max_allowed_blocks": p1.capability(
                                profile, state
                            ).max_move_blocks_per_world_tick}
                cap_conflicts += 1
                break
            step = p1.advance(profile, state, p1.FatigueFrame(
                session_id=session, world_tick=tick, activity="MOVE",
                observed_blocks=observed,
            ))
            if (step.recovered != 0
                    or step.frame.activity != "MOVE"
                    or step.after.world_tick != tick
                    or step.after.fatigue < step.before.fatigue):
                raise BoundaryRejected("P1 MOVE-only preview emitted free recovery")
            transitions.append({
                "world_tick": tick,
                "real_movement_candidate_blocks": observed,
                "hypothetical_fatigue_before": step.before.fatigue,
                "hypothetical_fatigue_after": step.after.fatigue,
                "hypothetical_gain": step.accumulated,
                "hypothetical_recovered": 0.0,
            })
            state = step.after
        results.append({
            "first_world_tick": start,
            "last_world_tick": end,
            "candidate_ticks_replayed": len(transitions),
            "hypothetical_window_end_fatigue": state.fatigue,
            "conflict": conflict,
            "transitions": transitions,
            "lineage_reset_at_unknown_gap": True,
            "authoritative_body_state_updated": False,
        })
    return {
        "classification": "S_P1_FLAT_CROSS_BRANCH_MOTION_ONLY_PREVIEW_NOT_ADMITTED",
        "arm": ledger["arm"],
        "world": ledger["world"],
        "P1_owner_profile_sha256": profile.sha256,
        "windows": results,
        "native_move_tick_candidates": ledger["move_observed_ticks"],
        "unknown_tick_count": ledger["unclassified_ticks"],
        "cap_conflicts": cap_conflicts,
        "P1_World_SourceBoundTick_issued": 0,
        "P1_authoritative_state_advanced": False,
        "P1_wait_recovery": 0.0,
        "M02_energy_ledger_writes": 0,
        "World_Action_writes": 0,
        "science_trials": 0,
        "engineering_qualified": False,
        "R_new_original_review": "PENDING",
    }
