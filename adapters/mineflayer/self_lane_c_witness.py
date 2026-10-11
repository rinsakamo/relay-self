"""Read-only Self S16 → Lane C C15 spatial witness reconciliation.

The C15 reducer and manifest are copied byte-for-byte from its frozen
qualification branch. This adapter never invokes S49, Node, a model, an Action,
S17 feedback, an S10 update, or S11 Habit. A captured S16 outcome has only
ONE poststop observation; C15 requires TWO independently source-sequenced
poststop probes. Never invent the second one or rewrite source sequence IDs.
"""
from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass
from typing import Iterable

from adapters.mineflayer.goal_witness import (
    SIGNED_ACTION_LABEL,
    EndpointReducer,
    SpatialContract,
)
from adapters.mineflayer.python_protocol import (
    MineflayerStreamDecoder,
    MineflayerEffectResult,
    MineflayerObservation,
)
from adapters.mineflayer.self_action_evidence import (
    NativeEvidenceRejected,
    verify_native_action_evidence,
)

SCHEMA = "SELF_LANEC_C15_SOURCE_RECONCILIATION_V1"


@dataclass(frozen=True)
class SelfSpatialObservation:
    schema: str
    status: str
    reason: str
    session_id: str | None
    action_id: str | None
    source_references: tuple[str, ...]
    source_sha256: str | None
    source_matches_s16: bool
    physical_source_attested: bool = False
    goal_success_attested: bool = False
    signed_action_label: str = SIGNED_ACTION_LABEL
    s17_feedback_issued: bool = False
    s10_updates: int = 0
    s11_habit_promotions: int = 0


def _unknown(reason: str, session: str | None = None,
             action: str | None = None) -> SelfSpatialObservation:
    return SelfSpatialObservation(
        SCHEMA, "UNDETERMINED", reason, session, action, (), None, False,
    )


def qualify_self_action_spatial(
    report: object, *,
    action_id: str,
    spec: SpatialContract,
    source_lines: Iterable[str] | None,
) -> SelfSpatialObservation:
    """Cross-check exact source records before using unmodified C15 reducer.

    report: saved S49 native_report.json (not a synthetic smoke or prior
    four-hash receipt without captured decoded action evidence).
    source_lines: OPTIONAL original *complete* bridge JSONL, as saved.
    Caller-controlled source files are NOT independent proof of physical World.
    Missing raw source or insufficient second post-stop probe is UNKNOWN.
    """
    if (not isinstance(report, dict)
            or report.get("status") != "PASS"
            or type(report.get("actual_native_actions")) is not list
            or not isinstance(action_id, str) or not action_id
            or not isinstance(spec, SpatialContract)):
        return _unknown("INVALID_REPORT_OR_CONTRACT")
    actions = [a for a in report["actual_native_actions"]
               if isinstance(a, dict) and a.get("action") == action_id]
    if len(actions) != 1:
        return _unknown("ACTION_MISSING_OR_DUPLICATE", action=action_id)
    entry = actions[0]
    session = entry.get("source")
    if not isinstance(session, str) or not session:
        return _unknown("MISSING_SESSION", action=action_id)
    if (report.get("session_id") != session
            or entry.get("terminal") != "outcome"
            or spec.session_id != session
            or spec.start_action_id != action_id
            or spec.stop_action_id != f"{action_id}-s15-clear"):
        return _unknown("SESSION_OR_ACTION_CONTRACT_MISMATCH", session, action_id)
    ev = entry.get("execution_evidence")
    try:
        verify_native_action_evidence(
            ev, action_id=action_id, session_id=session,
            movement_m=entry["movement_m"],
        )
    except (NativeEvidenceRejected, TypeError, KeyError, ValueError):
        return _unknown("INVALID_OR_MISSING_S16_SOURCE_FRAMES", session, action_id)
    if source_lines is None:
        return _unknown("NO_COMPLETE_ORIGINAL_BRIDGE_JSONL", session, action_id)

    # No inferred/resequenced wire events. Strict per-session stream decoder
    # must accept every original line from adapter_started seq=0 onwards.
    lines = tuple(source_lines)
    if not lines or len(lines) > 10000 or any(
        not isinstance(line, str) or len(line) > 1_000_000 for line in lines
    ):
        return _unknown("INVALID_OR_UNBOUNDED_SOURCE", session, action_id)
    digest = hashlib.sha256("".join(lines).encode("utf-8")).hexdigest()
    decoder = MineflayerStreamDecoder()
    matched: dict[int, object] = {}
    try:
        for line in lines:
            message = decoder.decode(line)
            if message.session_id != session:
                return _unknown("SOURCE_SESSION_MISMATCH", session, action_id)
            matched[message.seq] = message
        for key, cls in (
            ("before_observation", MineflayerObservation),
            ("dispatch_receipt", MineflayerEffectResult),
            ("cleanup_receipt", MineflayerEffectResult),
            ("after_observation", MineflayerObservation),
        ):
            original = ev[key]
            decoded = matched.get(original["seq"])
            if not isinstance(decoded, cls):
                return _unknown("S16_FRAME_MISSING_FROM_SOURCE", session, action_id)
            expected = dict(original)
            expected.pop("provenance", None)
            if asdict(decoded) != expected:
                return _unknown("S16_SOURCE_CONTENT_MISMATCH", session, action_id)
    except (ValueError, TypeError, KeyError, UnicodeError):
        return _unknown("INVALID_OR_NONCONTIGUOUS_SOURCE", session, action_id)

    # C15 is the *only* authority to identify a spatial region. The original
    # reducer requires two stable post-stop probes. Existing S49 S16 evidence
    # alone must remain UNDETERMINED, including when movement_m is positive.
    outcome = EndpointReducer().qualify(lines, spec)
    return SelfSpatialObservation(
        schema=SCHEMA,
        status=outcome.status,
        reason=outcome.reason,
        session_id=session,
        action_id=action_id,
        source_references=outcome.evidence,
        source_sha256=digest,
        source_matches_s16=True,
    )


def observation_json(value: SelfSpatialObservation) -> str:
    """Durable result; no Action/feedback/learning privileges."""
    if not isinstance(value, SelfSpatialObservation):
        raise TypeError("SelfSpatialObservation required")
    return json.dumps(asdict(value), ensure_ascii=False, sort_keys=True) + "\n"
