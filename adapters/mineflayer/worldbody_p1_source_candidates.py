"""Read-only P1-B source-readiness adapter over the EXISTING #734 emitter.

The original S49P1SourcePlugin/inspector already gathers bounded Paper
callback intervals. Do NOT create another tick sensor or pretend that an
empty callback interval authenticates a full, Action-free World WAIT tick.
No runtime WorldBody mutation, P1 state advance, S49 grant or source promotion.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

from adapters.mineflayer.s49_p1_paper_dev import inspect_paper_tick_source

ActivityCandidate = Literal[
    "FIGHT_CALLBACK_CANDIDATE", "MOVE_CALLBACK_CANDIDATE",
    "QUIET_CALLBACK_WAIT_CANDIDATE", "MIXED_OR_OTHER_UNQUALIFIED",
]


@dataclass(frozen=True, slots=True)
class P1CallbackCandidate:
    session_id: str
    world_uuid: str
    world_tick: int
    activity: ActivityCandidate
    observed_move_blocks: float
    observed_fight_events: int
    admissible_as_source_bound_tick: bool = False
    genuine_full_tick_wait_attested: bool = False


@dataclass(frozen=True, slots=True)
class P1SourceReadiness:
    session_id: str
    world_uuid: str
    original_attack_action_id: str
    callback_count: int
    candidates: tuple[P1CallbackCandidate, ...]
    p1_admitted_tick_count: int = 0
    original_source_qualification: str = "DEV_CALLBACK_BOUNDED_ONLY"
    outstanding_owner_evidence: tuple[str, ...] = (
        "S49_ACTION_EFFECT_AND_CONTROL_OWNERSHIP_PER_TICK",
        "S_R_INDEPENDENT_FULL_TICK_WAIT_INACTIVITY_WITNESS",
        "S_R_WORLD_SOURCE_AUTHENTICATION",
    )


def assess_existing_paper_p1_source(
    paper_log: str, *, nonce: str, native_report: dict,
    expected_choice: Literal["REST", "WAIT"] = "REST",
    marker_style: Literal["legacy", "choice"] = "legacy",
) -> P1SourceReadiness:
    """Reuse #734's original source inspector; classify, but never admit.

    This is a *readiness* result, not P1-B SourceBoundTick/WAIT evidence.
    Even a perfect quiet callback cannot become a physical recovery receipt.
    """
    source = inspect_paper_tick_source(
        paper_log, nonce=nonce, native_report=native_report,
        expected_choice=expected_choice, marker_style=marker_style,
    )
    if (
        source["source_full_tick_activity_independently_attested"] is not False
        or source["r_source_original_independently_attested"] is not False
        or source["source_complete_callback_series"] is not True
    ):
        raise ValueError("unexpected #734 callback source qualification boundary")
    rows = source["source_tick_rows"]
    if not 0 < len(rows) <= 480 or len(rows) != source["total_consecutive_source_callback_rows"]:
        raise ValueError("unbounded/partial original callback source")
    candidates = []
    for row in rows:
        counts = row["event_counters"]
        move = row["observed_move_blocks"]
        fight = counts["fight_events"]
        extras = sum(counts[name] for name in (
            "interact_events", "velocity_events", "teleport_events",
            "player_damage_events",
        ))
        if (
            fight == 1 and counts["move_events"] == 0 and move == 0
            and extras == 0
        ):
            kind: ActivityCandidate = "FIGHT_CALLBACK_CANDIDATE"
        elif (
            fight == 0 and counts["move_events"] > 0 and move > 0
            and counts["swing_events"] == 0 and extras == 0
        ):
            kind = "MOVE_CALLBACK_CANDIDATE"
        elif (
            not any(counts.values()) and move == 0
            and not row["sprint"] and not row["sneak"] and not row["swimming"]
        ):
            kind = "QUIET_CALLBACK_WAIT_CANDIDATE"
        else:
            kind = "MIXED_OR_OTHER_UNQUALIFIED"
        candidates.append(P1CallbackCandidate(
            session_id=source["native_session_id"],
            world_uuid=source["paper_world"],
            world_tick=row["world_tick"],
            activity=kind,
            observed_move_blocks=move,
            observed_fight_events=fight,
        ))
    return P1SourceReadiness(
        session_id=source["native_session_id"],
        world_uuid=source["paper_world"],
        original_attack_action_id=source["native_attack_action_id"],
        callback_count=len(candidates), candidates=tuple(candidates),
    )


def p1_physical_tick_from_callback(_candidate: P1CallbackCandidate) -> None:
    """Deliberate hard fence until S/R has a genuine World-tick admission API.

    A string marker, quiet probe, row counter, model FatigueFrame, or boolean
    supplied by this adapter is NEVER a substitute for S/R source authority.
    """
    raise ValueError("P1-B original authenticated S/R tick owner not connected")
