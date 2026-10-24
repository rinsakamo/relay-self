"""S49 pre-action Paper BACK on→off transcript, strictly offline DEV.

This is a correlation-only screen on caller-provided text; it does NOT
authenticate S49 cleanup causality, original Paper custody, physical
inactivity for all World ticks, or any P1 admission.
"""
from __future__ import annotations

from adapters.mineflayer.m02_paper_dev.s50_boundary import BoundaryRejected
from adapters.mineflayer.s49_paper_backward_wait_dev import BEGIN, TICK
from adapters.mineflayer.s49_paper_transcript_dev import (
    ABORT,
    COMPLETE,
    SERVER_INPUT,
    SUBJECT,
    _fields,
    review_s49_paper_transcript_dev,
)
from adapters.mineflayer.s49_wait_typed_capture_dev import S49TypedClosureCaptureDev

PRE_ARM = "S49_OBSERVER_PRE_ARM"
BACK_ON = "S49_OBSERVER_BACK_TRUE"
BACK_OFF = "S49_OBSERVER_BACK_FALSE"
ORDER = (
    SUBJECT, PRE_ARM, BACK_ON, BACK_OFF, SERVER_INPUT, BEGIN,
    *(TICK for _ in range(8)), COMPLETE,
)
PRE_BASE_FIELDS = frozenset({
    "marker_id", "action_id", "session_id", "world", "run_id", "tick",
})


def _parse_tick(value: str) -> int:
    try:
        tick = int(value)
    except ValueError as exc:
        raise BoundaryRejected("invalid Paper pre-action tick") from exc
    if tick < 1 or str(tick) != value:
        raise BoundaryRejected("noncanonical Paper pre-action tick")
    return tick


def review_s49_preaction_paper_dev(
    capture: S49TypedClosureCaptureDev, transcript: str, *,
    expected_player_uuid: str,
) -> dict:
    """Cross-check one claimed event sequence, never build SourceBoundTick."""
    if not isinstance(transcript, str) or len(transcript) > 65536:
        raise BoundaryRejected("bounded source text is required")
    # The existing strict reviewer confirms original S16 typed close, one
    # Paper run, server input-idle snapshot and eight consecutive callbacks.
    prior = review_s49_paper_transcript_dev(
        capture, transcript, expected_player_uuid=expected_player_uuid,
    )
    recognized = (SUBJECT, PRE_ARM, BACK_ON, BACK_OFF, SERVER_INPUT,
                  BEGIN, TICK, COMPLETE, ABORT)
    observed = []
    for raw in transcript.splitlines(keepends=True):
        if len(raw) > 2048:
            raise BoundaryRejected("oversized Paper transition record")
        matches = [(raw.find(name), name) for name in recognized]
        matches = [(offset, name) for offset, name in matches if offset >= 0]
        if not matches:
            continue
        offset, name = min(matches)
        if name == ABORT:
            raise BoundaryRejected("Paper pre-action observer ABORT")
        observed.append((name, raw[offset:].strip()))
    if tuple(kind for kind, _ in observed) != ORDER:
        raise BoundaryRejected("missing/reordered/duplicated BACK transition")
    expected = {
        "action_id": prior["action_id"],
        "session_id": prior["session_id"],
        "world": prior["world"],
        "marker_id": prior["action_id"] + "-" + prior["session_id"],
        "run_id": prior["observer_run_id"],
    }
    armed = _fields(
        observed[1][1], PRE_ARM,
        PRE_BASE_FIELDS | {"input_idle"},
    )
    pressed = _fields(
        observed[2][1], BACK_ON,
        PRE_BASE_FIELDS | {"back"},
    )
    released = _fields(
        observed[3][1], BACK_OFF,
        PRE_BASE_FIELDS | {"back"},
    )
    for row in (armed, pressed, released):
        if any(row[key] != value for key, value in expected.items()):
            raise BoundaryRejected("Paper transition not same S49 claim/run")
    if (armed["input_idle"] != "true" or pressed["back"] != "true"
            or released["back"] != "false"):
        raise BoundaryRejected("not an idle→BACK-on→BACK-off event sequence")
    arm_tick = _parse_tick(armed["tick"])
    on_tick = _parse_tick(pressed["tick"])
    off_tick = _parse_tick(released["tick"])
    if (not arm_tick <= on_tick < off_tick
            or off_tick != prior["first_tick"] - 1
            or off_tick - arm_tick > 240):
        raise BoundaryRejected("Paper transition order/clock invalid")
    return {
        **prior,
        "schema": "S49_PRE_ACTION_PAPER_BACK_EDGE_DEV_V1",
        "status": "BACK_TRUE_TO_FALSE_PAPER_SHAPE_ONLY",
        "pre_arm_tick": arm_tick,
        "back_true_tick": on_tick,
        "back_false_tick": off_tick,
        "paper_back_edge": "CALLER_LOG_CLAIMED_TRUE_TO_FALSE",
        "s49_native_clear_caused_edge": "NOT_ATTESTED",
        "server_effective_control_release": "NOT_ATTESTED",
        "whole_tick_self_inactivity": "NOT_ATTESTED",
        "source_bound_tick": None,
        "wait_interval_ref": None,
        "wait_ticks_admitted": 0,
        "p1_fatigue_recovered": 0.0,
        "qualification_go": False,
        "science_go": False,
    }
