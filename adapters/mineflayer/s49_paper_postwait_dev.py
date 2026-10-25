"""Paper post-S49-WAIT DEV-only reviewer; reuses existing original receipts.

The result is an offline source/model join until a *single live owner run*
completes. No R-qualified SourceBoundTick is minted or P1 production state written.
"""
from __future__ import annotations

import hashlib
from uuid import UUID

from adapters.mineflayer.m02_paper_dev.s50_boundary import BoundaryRejected
from adapters.mineflayer.s49_paper_backward_wait_dev import BEGIN, TICK, _parse_paper
from adapters.mineflayer.s49_paper_transcript_dev import (
    ABORT,
    COMPLETE,
    ORDER,
    SERVER_INPUT,
    SUBJECT,
    _fields,
)
from adapters.mineflayer.self_action_evidence import (
    NativeEvidenceRejected,
    verify_native_action_evidence,
)
from experiments.fatigue_p1 import (
    FatigueFrame,
    FatigueProfile,
    FatigueRejected,
    advance,
    initial_state,
)

SCHEMA = "S49_PAPER_POSTWAIT_P1_DEV_V1"


def _uuid(value: str, *, version: int | None = None) -> bool:
    try:
        parsed = UUID(value)
        return str(parsed) == value and (version is None or parsed.version == version)
    except (TypeError, AttributeError, ValueError):
        return False


def review_postaction_wait_dev(
    original_s49: dict, paper_window: str, *, expected_player_uuid: str,
    profile: FatigueProfile,
) -> dict:
    """Join original S49 second Action to a same-run post-clear Paper window.

    The profile's initial fatigue is an **explicit DEV model seed**, not a
    measurement of physical exertion or a historical P1 state. Unknown
    command/packet causality stays outside the DEV claim.
    """
    actions = original_s49.get("actual_native_actions")
    session = original_s49.get("session_id")
    if (original_s49.get("status") != "PASS"
            or not isinstance(actions, list) or len(actions) != 2
            or not isinstance(session, str) or not session
            or not isinstance(paper_window, str)
            or not 0 < len(paper_window) <= 65536
            or not _uuid(expected_player_uuid)
            or not isinstance(profile, FatigueProfile) or not profile.enabled
            or profile.initial <= 0):
        raise BoundaryRejected("successful S49 pair, Paper window, seeded P1 required")
    action = actions[-1]
    if (not isinstance(action, dict)
            or action.get("terminal") != "outcome"
            or action.get("source") != session
            or not isinstance(action.get("action"), str)):
        raise BoundaryRejected("original second Action terminal missing")
    try:
        verify_native_action_evidence(
            action.get("execution_evidence"),
            action_id=action["action"], session_id=session,
            movement_m=action.get("movement_m"),
        )
    except (NativeEvidenceRejected, TypeError, ValueError) as exc:
        raise BoundaryRejected("S49 typed Action/S16 clear rejected") from exc

    found = []
    for line in paper_window.splitlines(keepends=True):
        if len(line) > 2048:
            raise BoundaryRejected("oversized Paper row")
        if "S49_OBSERVER_DENIED" in line or ABORT in line:
            raise BoundaryRejected("Paper observer rejected/aborted")
        matched = [(line.find(kind), kind) for kind in
                   (SUBJECT, SERVER_INPUT, BEGIN, TICK, COMPLETE)]
        matched = [(at, kind) for at, kind in matched if at >= 0]
        if matched:
            at, kind = min(matched)
            found.append((kind, line[at:].strip()))
    if tuple(kind for kind, _ in found) != ORDER:
        raise BoundaryRejected("Paper observer not one complete post-Action run")
    subject = _fields(found[0][1], SUBJECT, frozenset({
        "action_id", "session_id", "player_uuid", "world", "run_id", "clear_ack",
    }))
    server_input = _fields(found[1][1], SERVER_INPUT, frozenset({
        "action_id", "session_id", "player_uuid", "world", "run_id", "tick",
        "input_idle", "s49_release_causality",
    }))
    terminal = _fields(found[-1][1], COMPLETE, frozenset({
        "action_id", "session_id", "player_uuid", "world", "run_id",
        "last_tick", "samples", "authority", "p1_recovery",
    }))
    run_id = subject["run_id"]
    if (not _uuid(run_id, version=4)
            or not _uuid(subject["world"])
            or any(row.get(field) != value for row in
                   (subject, server_input, terminal)
                   for field, value in {
                       "action_id": action["action"], "session_id": session,
                       "player_uuid": expected_player_uuid,
                       "world": subject["world"], "run_id": run_id,
                   }.items())
            or subject["clear_ack"] != "UNATTESTED_CONSOLE_CLAIM"
            or server_input["input_idle"] != "true"
            or server_input["s49_release_causality"] != "NOT_ATTESTED"
            or terminal["samples"] != "8"
            or terminal["authority"] != "NONE"
            or terminal["p1_recovery"] != "NONE"):
        raise BoundaryRejected("Paper run/subject/idle context invalid")
    normalized = "\n".join(row for _, row in found[2:11]) + "\n"
    for kind, row in found[2:11]:
        fields = _fields(row, kind, frozenset({
            "marker_id", "action_id", "session_id", "world",
            "run_id", "tick", "index", "input_idle",
        }))
        if fields["run_id"] != run_id or fields["input_idle"] != "true":
            raise BoundaryRejected("active input or mixed-run Paper callback")
    begin, samples = _parse_paper(
        normalized, action_id=action["action"], session_id=session,
        marker_id=action["action"] + "-" + session,
        world=subject["world"],
    )
    if (server_input["tick"] != str(begin)
            or terminal["last_tick"] != str(begin + 8)
            or len(samples) != 8):
        raise BoundaryRejected("Paper World ticks not consecutive after idle")
    # Paper BEGIN is observed after the original native clear. The uncertain
    # boundary itself earns NO recovery. Only subsequent callback ticks do.
    try:
        state = initial_state(profile, session, world_tick=begin)
        before = state.fatigue
        rows = []
        for world_tick, ref in samples:
            transition = advance(
                profile, state, FatigueFrame(
                    session_id=session, world_tick=world_tick, activity="WAIT",
                ),
            )
            rows.append({
                "tick": world_tick,
                "paper_line_ref": ref,
                "before": transition.before.fatigue,
                "after": transition.after.fatigue,
                "recovered": transition.recovered,
            })
            state = transition.after
    except FatigueRejected as exc:
        raise BoundaryRejected("P1 DEV state/replay rejected") from exc
    return {
        "schema": SCHEMA,
        "status": "OFFLINE_MODEL_REPLAY",
        "source_mode": "CALLER_PROVIDED_PAPER_WINDOW_AND_S49_REPORT",
        "session_id": session,
        "action_id": action["action"],
        "world": subject["world"],
        "observer_run_id": run_id,
        "paper_window_sha256": hashlib.sha256(paper_window.encode()).hexdigest(),
        "p1_profile_sha256": profile.sha256,
        "dev_fatigue_initial_origin": "EXPLICIT_DEV_SEEDED_MODEL_NOT_PHYSICAL_MEASUREMENT",
        "dev_fatigue_before": before,
        "dev_fatigue_after": state.fatigue,
        "dev_fatigue_recovered": sum(row["recovered"] for row in rows),
        "dev_wait_ticks": rows,
        "dev_wait_count": 8,
        "uncertain_release_tick_excluded": begin,
        "world_run_verified": False,
        "source_bound_tick": None,
        "wait_interval_ref": None,
        "wait_ticks_admitted": 0,
        "p1_fatigue_recovered": 0.0,
        "qualification_go": False,
        "science_go": False,
    }
