"""DEV-only S/R joint evidence screen for S50/P1 WAIT; never P1 authority.

Joins *raw* Action/Executor, Paper tick sampler, loaded-entity census and
Paper lifecycle records through existing independent syntax/provenance readers.
A successful join does not prove full World-tick inactivity or exhaustive
Action issuance. No SourceBoundTick(WAIT) or WAIT witness is created here.
"""
from __future__ import annotations

from adapters.mineflayer.m02_paper_dev.s50_boundary import BoundaryRejected
from adapters.mineflayer.m02_paper_dev.s50_p1_control_action import (
    review_control_action,
)
from adapters.mineflayer.m02_paper_dev.s50_p1_lifecycle import review_lifecycle
from adapters.mineflayer.m02_paper_dev.s50_p1_scope import review_scope
from adapters.mineflayer.m02_paper_dev.s50_p1_wait import candidate_wait_ticks

MISSING_R_PROOFS = (
    "EXHAUSTIVE_PHYSICAL_ACTIVITY_FOR_EACH_COMPLETE_WORLD_TICK",
    "SINGLE_EXECUTOR_NO_ACTION_ISSUED_OR_IN_FLIGHT_DURING_EACH_TICK",
    "HELD_CONTROLS_AND_SERVER_EFFECTS_SETTLED_FOR_WHOLE_INTERVAL",
    "INDEPENDENT_R_ORIGINAL_SOURCE_AUTHENTICATION",
)


def review_joint_wait_sources(
    paper_original: str,
    native: list[dict],
    commands: list[dict],
    journal: list[dict],
    movement: dict,
) -> dict:
    """Reject incoherent original streams; always withhold physical WAIT.

    This is an S-owned offline cross-source screen. R must independently prove
    the complete-tick boundary, every original issuer, physical effects and
    immutable source binding; hashes/refs or clean samplers do not prove these.
    """
    action = review_control_action(
        paper_original, native, commands, journal, movement,
    )
    marker = action["marker_id"]
    world = action["paper_world"]
    begin = action["paper_wait_begin_tick"]
    candidate = candidate_wait_ticks(
        paper_original, marker_id=marker, expected_world=world,
        source_action_terminal="outcome",
    )
    first = candidate["first_world_tick"]
    last = candidate["last_world_tick"]
    if first != begin + 1 or last != begin + 8:
        raise BoundaryRejected("WAIT sampler not correlated with Action clear")
    scope = review_scope(
        paper_original, marker=marker, world=world,
        wait_first_tick=first, wait_last_tick=last,
        original_outcome="outcome",
    )
    lifecycle = review_lifecycle(
        paper_original, marker=marker, world=world,
        self_uuid=scope["self_uuid"],
        self_entity_world_uuid=scope["self_entity_world_uuid"],
        wait_first_tick=first, wait_last_tick=last,
    )
    if (scope["first_world_tick"] != first
            or scope["last_world_tick"] != last
            or lifecycle["first_world_tick"] != first
            or lifecycle["last_world_tick"] != last):
        raise BoundaryRejected("S/R cross-source World-tick window mismatch")

    # A nearby entity is World context, not automatically an active Self
    # motor. Never require an empty Minecraft World for the Body to rest.
    self_activity_flags = []
    if not candidate["source_stationary_8_of_8"]:
        self_activity_flags.append("SAMPLED_SELF_ACTIVITY")
    if scope["activity_counter_changed_after_first_sampler"]:
        self_activity_flags.append("NATIVE_SELF_EVENT_COUNTER_CHANGED")
    environment_context_flags = []
    if scope["same_world_other_loaded_entities_seen_ticks"]:
        environment_context_flags.append("OTHER_LOADED_ENTITY_IN_SELF_WORLD")
    if lifecycle["same_world_entity_lifecycle_ticks"]:
        environment_context_flags.append("TRANSIENT_ENTITY_LIFECYCLE_IN_SELF_WORLD")
    if lifecycle["same_world_chunk_change_ticks"]:
        environment_context_flags.append("CHUNK_LIFECYCLE_IN_SELF_WORLD")

    # Even an all-clean cross-source screen cannot fill the missing R witnesses.
    return {
        "classification": "S50_P1_JOINT_ORIGINALS_DEV_SCREEN_ONLY",
        "action_id": action["action_id"],
        "session_id": action["source_session"],
        "marker_id": marker,
        "paper_world": world,
        "self_uuid": scope["self_uuid"],
        "self_world_uuid": scope["self_entity_world_uuid"],
        "first_world_tick": first,
        "last_world_tick": last,
        "source_streams_screened": (
            "S_ACTION_AND_NATIVE_COMMAND",
            "PAPER_WAIT_SAMPLER",
            "PAPER_LOADED_CHUNK_CENSUS",
            "PAPER_ENTITY_LIFECYCLE_CALLBACK",
        ),
        "self_activity_flags": self_activity_flags,
        "environment_context_flags": environment_context_flags,
        "self_sample_screen_clear": not self_activity_flags,
        "missing_independent_r_proofs": MISSING_R_PROOFS,
        "complete_world_tick_inactivity_proven": False,
        "all_action_issuers_proven_idle": False,
        "r_original_source_authenticated": False,
        "wait_interval_ref": None,
        "source_bound_tick": None,
        "wait_ticks_admitted": 0,
        "p1_fatigue_recovered": 0.0,
        "qualification_go": False,
        "science_go": False,
    }
