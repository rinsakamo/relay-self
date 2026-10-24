"""Small DEV-only Paper WAIT -> existing P1 fatigue replay.

This is a *model replay on caller-supplied sources*, not a World-run verdict,
R SourceBoundTick, or a physical assertion of whole-tick inactivity.
Keep the genuine Paper DEV run and original S49 action on the same World
before elevating the observation to DEV_WORLD_OBSERVED in an external run report.
"""

from __future__ import annotations

from adapters.mineflayer.m02_paper_dev.s50_boundary import BoundaryRejected
from adapters.mineflayer.s49_paper_preaction_dev import (
    review_s49_preaction_paper_dev,
)
from adapters.mineflayer.s49_wait_typed_capture_dev import S49TypedClosureCaptureDev
from experiments.fatigue_p1 import (
    FatigueFrame,
    FatigueProfile,
    FatigueRejected,
    FatigueState,
    advance,
    capability,
)

SCHEMA = "S49_S50_P1_WAIT_MODEL_REPLAY_DEV_V1"


def replay_wait_fatigue_dev(
    capture: S49TypedClosureCaptureDev,
    paper_transcript: str,
    *,
    expected_player_uuid: str,
    profile: FatigueProfile,
    state_before_wait: FatigueState,
) -> dict:
    """Calculate P1 on the eight strictly screened post-release Paper ticks.

    The first admitted candidate is the first complete callback tick AFTER
    BACK-off/BEGIN; the uncertain release boundary itself is never credited.
    The caller must supply its *already maintained* P1 state at the preceding
    tick. Never invent that state by silently aligning to Paper time.
    """
    audit = review_s49_preaction_paper_dev(
        capture, paper_transcript, expected_player_uuid=expected_player_uuid,
    )
    if (not isinstance(profile, FatigueProfile) or not profile.enabled
            or not isinstance(state_before_wait, FatigueState)
            or state_before_wait.session_id != audit["session_id"]
            or state_before_wait.world_tick != audit["first_tick"] - 1
            or audit["first_tick"] != audit["back_false_tick"] + 1
            or audit["sample_count"] != 8
            or audit["last_tick"] != audit["first_tick"] + 7):
        raise BoundaryRejected("valid enabled P1 state at post-release tick required")
    try:
        capability(profile, state_before_wait)
        current = state_before_wait
        ticks = []
        for tick in range(audit["first_tick"], audit["last_tick"] + 1):
            result = advance(
                profile, current,
                FatigueFrame(session_id=audit["session_id"],
                             world_tick=tick, activity="WAIT"),
            )
            ticks.append({
                "world_tick": tick,
                "fatigue_before": result.before.fatigue,
                "fatigue_after": result.after.fatigue,
                "recovered": result.recovered,
            })
            current = result.after
    except FatigueRejected as exc:
        raise BoundaryRejected("P1 virtual body state rejected") from exc
    total = sum(row["recovered"] for row in ticks)
    return {
        "schema": SCHEMA,
        "status": "OFFLINE_WAIT_MODEL_REPLAY",
        "source_kind": "CALLER_SUPPLIED_S49_AND_PAPER_TRANSCRIPT",
        "session_id": audit["session_id"],
        "action_id": audit["action_id"],
        "paper_world": audit["world"],
        "paper_run_id": audit["observer_run_id"],
        "paper_text_sha256": audit["original_text_sha256"],
        "s16_typed_sha256": audit["typed_s16_sha256"],
        "p1_profile_sha256": profile.sha256,
        "excluded_release_boundary_tick": audit["back_false_tick"],
        "dev_wait_tick_count": len(ticks),
        "dev_wait_ticks": ticks,
        "dev_fatigue_before": state_before_wait.fatigue,
        "dev_fatigue_after": current.fatigue,
        "dev_fatigue_recovered": total,
        "dev_fatigue_recovery_positive": total > 0,
        "p1_world_state_updated": False,
        "source_bound_tick": None,
        "wait_interval_ref": None,
        "wait_ticks_admitted": 0,
        "p1_fatigue_recovered": 0.0,
        "qualification_go": False,
        "science_go": False,
        "world_run_verified": False,
    }
