"""DEV-only Paper observer transcript audit against typed S49 S16 closure.

One run-id and ordered records are correlation, NOT source authentication,
server-effective control release, complete Self inactivity, or P1 admission.
"""
from __future__ import annotations

import hashlib
from uuid import UUID

from adapters.mineflayer.m02_paper_dev.s50_boundary import BoundaryRejected
from adapters.mineflayer.s49_paper_backward_wait_dev import BEGIN, TICK, _parse_paper
from adapters.mineflayer.s49_wait_typed_capture_dev import S49TypedClosureCaptureDev

SUBJECT = "S49_OBSERVER_SUBJECT"
COMPLETE = "S49_OBSERVER_COMPLETE"
ABORT = "S49_DEV_BACK_WAIT_ABORT"
ORDER = (SUBJECT, BEGIN, *(TICK for _ in range(8)), COMPLETE)


def _fields(line: str, kind: str, names: frozenset[str]) -> dict[str, str]:
    tokens = line.split()
    if not tokens or tokens[0] != kind or len(tokens) != len(names) + 1:
        raise BoundaryRejected("bad Paper observer transcript record")
    values: dict[str, str] = {}
    for token in tokens[1:]:
        if token.count("=") != 1:
            raise BoundaryRejected("malformed Paper transcript field")
        key, value = token.split("=", 1)
        if not value or key in values:
            raise BoundaryRejected("duplicate or empty transcript field")
        values[key] = value
    if values.keys() != names:
        raise BoundaryRejected("missing or foreign transcript field")
    return values


def _uuid4(value: str) -> bool:
    try:
        parsed = UUID(value)
    except (TypeError, ValueError, AttributeError):
        return False
    return parsed.version == 4 and str(parsed) == value


def review_s49_paper_transcript_dev(
    capture: S49TypedClosureCaptureDev, original_text: str, *,
    expected_player_uuid: str,
) -> dict:
    """Check a full supplied log transcript, without controlling S49 or Paper.

    Log prefixes are removed only to parse records. The SHA covers all given
    original text, and cannot independently attest its production or custody.
    """
    if (not isinstance(capture, S49TypedClosureCaptureDev)
            or capture.state != "CAPTURED" or capture.projection is None
            or not isinstance(original_text, str)
            or not 0 < len(original_text) <= 65536
            or not _uuid4(expected_player_uuid)):
        raise BoundaryRejected("bounded transcript and typed S49 close required")
    evidence = capture.projection
    owner = capture._executor
    action, session = evidence.action_id, evidence.session_id
    world, marker = owner._wait_fence._world, owner._wait_fence._marker
    decoded = evidence.decoded_evidence
    if (marker != action + "-" + session
            or decoded.get("action_id") != action
            or decoded.get("session_id") != session
            or decoded.get("action_ref") != "MOVE_BACKWARD"
            or decoded.get("status") != "executed"
            or decoded.get("cleanup_receipt", {}).get("effect") != "clear_controls"
            or decoded.get("cleanup_receipt", {}).get("result") != "applied"
            or decoded.get("cleanup_receipt", {}).get("action_id")
            != action + "-s15-clear"):
        raise BoundaryRejected("original S16 MOVE_BACKWARD clear not captured")
    observations: list[tuple[str, str]] = []
    for row in original_text.splitlines(keepends=True):
        if len(row) > 2048:
            raise BoundaryRejected("oversized Paper source line")
        hits = [(row.find(kind), kind) for kind in
                (SUBJECT, COMPLETE, BEGIN, TICK, ABORT)]
        hits = [(offset, kind) for offset, kind in hits if offset >= 0]
        if not hits:
            continue
        offset, kind = min(hits)
        if kind == ABORT:
            raise BoundaryRejected("Paper observer aborted")
        observations.append((kind, row[offset:].strip()))
    if tuple(kind for kind, _ in observations) != ORDER:
        raise BoundaryRejected("missing, replayed or restarted Paper observation")
    subject = _fields(observations[0][1], SUBJECT, frozenset({
        "action_id", "session_id", "player_uuid", "world", "run_id", "clear_ack",
    }))
    complete = _fields(observations[-1][1], COMPLETE, frozenset({
        "action_id", "session_id", "player_uuid", "world", "run_id",
        "last_tick", "samples", "authority", "p1_recovery",
    }))
    run_id = subject["run_id"]
    keys = {
        "action_id": action, "session_id": session, "world": world,
        "player_uuid": expected_player_uuid, "run_id": run_id,
    }
    if (not _uuid4(run_id)
            or any(subject.get(k) != v or complete.get(k) != v
                   for k, v in keys.items())
            or subject["clear_ack"] != "UNATTESTED_CONSOLE_CLAIM"
            or complete["samples"] != "8" or complete["authority"] != "NONE"
            or complete["p1_recovery"] != "NONE"):
        raise BoundaryRejected("foreign observer run/subject or fake authority")
    for kind, line in observations[1:10]:
        fields = _fields(line, kind, frozenset({
            "marker_id", "action_id", "session_id", "world",
            "run_id", "tick", "index",
        }))
        if fields["run_id"] != run_id:
            raise BoundaryRejected("mixed observer run in Paper callbacks")
    normalized = "\n".join(line for _, line in observations[1:10]) + "\n"
    begin, samples = _parse_paper(
        normalized, action_id=action, session_id=session,
        marker_id=marker, world=world,
    )
    if complete["last_tick"] != str(begin + 8):
        raise BoundaryRejected("terminal tick not eighth callback")
    return {
        "schema": "S49_PAPER_TRANSCRIPT_DEV_V1",
        "status": "ONE_RUN_TRANSCRIPT_SHAPE_ONLY",
        "action_id": action, "session_id": session, "world": world,
        "observer_run_id": run_id, "claimed_player_uuid": expected_player_uuid,
        "first_tick": begin + 1, "last_tick": begin + 8,
        "sample_count": len(samples),
        "typed_s16_sha256": evidence.evidence_sha256,
        "original_text_sha256": hashlib.sha256(
            original_text.encode("utf-8")
        ).hexdigest(),
        "normalized_paper_sha256": hashlib.sha256(
            normalized.encode("utf-8")
        ).hexdigest(),
        "source_authentication": "UNATTESTED_PAPER_LOG_TEXT",
        "server_effective_control_release": "NOT_ATTESTED",
        "whole_tick_self_inactivity": "NOT_ATTESTED",
        "all_action_issuers_idle": "NOT_ATTESTED",
        "source_bound_tick": None, "wait_interval_ref": None,
        "wait_ticks_admitted": 0, "p1_fatigue_recovered": 0.0,
        "qualification_go": False, "science_go": False,
    }
