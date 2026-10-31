"""S50 owner DEV: bounded Paper 8-tick window readable before Node shutdown.

A completed eight-callback Paper window is NOT a complete Node trace; no
TRACE_END is forged or relaxed. It may be *provisionally* read before an
original next native S49/L0 epoch, then must be compared with the actual
sealed Paper original after Java shutdown. Does not attest wire input,
effective client clear, full tick idle, physical rest, Goal or P1 WAIT.
"""
from __future__ import annotations

import hashlib
import math
from dataclasses import dataclass

from adapters.mineflayer.l23_paper_s7_settling import (
    _paper_rows,
    _verify_paper_event_order,
)
from adapters.mineflayer.m02_paper_dev.s50_input_witness_source import (
    review_s50_input_samples,
)

MAX_LIVE_PREFIX_BYTES = 2_000_000


class S50LivePaperWindowRejected(ValueError):
    """Unbounded, incomplete, foreign or corrupted in-session Paper window."""


@dataclass(frozen=True, slots=True)
class S50LivePaperTick:
    world_tick: int
    displacement_m: float
    last_reported_input_active: bool


@dataclass(frozen=True, slots=True)
class S50LivePaperWindow:
    """Read-only tentative S50 source, NOT source-complete MotionCompanion."""

    session_id: str
    action_id: str
    marker_id: str
    paper_world_uuid: str
    subject_uuid: str
    paper_prefix_sha256: str
    paper_prefix_bytes: int
    ticks: tuple[S50LivePaperTick, ...]
    input_event_count_at_window_end: int
    scope: str = "IN_SESSION_PAPER_CALLBACK_WINDOW_ONLY"
    provisional: bool = True
    final_source_verified: bool = False
    node_trace_complete: bool = False
    client_packet_writes_attested: bool = False
    effective_clear_tick: str = "NOT_ATTESTED"
    full_tick_input_idle: bool = False
    physical_stability_attested: bool = False
    goal_admitted: bool = False
    p1_wait_granted: int = 0
    l10_pairs: int = 0
    s10_updates: int = 0
    s11_grants: int = 0

    def prior_motion_summary(self) -> dict[str, object]:
        return {
            "source_scope": self.scope,
            "provisional": True,
            "session_id": self.session_id,
            "action_id": self.action_id,
            "paper_world": self.paper_world_uuid,
            "paper_prefix_sha256": self.paper_prefix_sha256,
            "paper_ticks": tuple(row.world_tick for row in self.ticks),
            "motion_with_last_reported_input_off_ticks": tuple(
                row.world_tick for row in self.ticks
                if row.displacement_m > 0 and not row.last_reported_input_active
            ),
            "node_trace_complete": False,
            "full_tick_input_idle_attested": False,
            "physical_stability_attested": False,
            "effective_clear_tick": "NOT_ATTESTED",
            "goal_admitted": False,
            "p1_wait_granted": 0,
            "l10_pairs": 0,
            "s10_updates": 0,
            "s11_grants": 0,
        }


def _extract_window(
    original: bytes, *, session_id: str, action_id: str,
    world: str, subject_uuid: str,
) -> tuple[S50LivePaperTick, ...]:
    """Validate exact S50 phase, WAIT_BEGIN, 8 WAIT and 8 INPUT callbacks."""
    marker = f"{action_id}-{session_id}"
    _verify_paper_event_order(original)
    begin = _paper_rows(original, "S50_DEV_WAIT_BEGIN ")
    waits = _paper_rows(original, "S50_DEV_WAIT_TICK ")
    phases = _paper_rows(original, "M02_DEV_S50_PHASE ")
    if (
        len(begin) != 1 or len(waits) != 8 or len(phases) != 2
        or [p.get("phase") for p in phases] != ["PRE_FORWARD", "POST_CLEAR"]
        or any(p.get("marker_id") != marker or p.get("world") != world for p in phases)
        or begin[0].get("marker_id") != marker
        or begin[0].get("world") != world
    ):
        raise S50LivePaperWindowRejected("wrong complete Paper phase/marker bracket")
    try:
        first = int(begin[0]["tick"]) + 1
    except (KeyError, ValueError) as exc:
        raise S50LivePaperWindowRejected("missing S50 first callback tick") from exc
    if first < 1:
        raise S50LivePaperWindowRejected("invalid S50 callback tick")
    try:
        begin_position = tuple(float(begin[0][axis]) for axis in ("x", "y", "z"))
    except (KeyError, TypeError, ValueError) as exc:
        raise S50LivePaperWindowRejected("missing initial Paper WAIT position") from exc
    if not all(math.isfinite(v) for v in begin_position):
        raise S50LivePaperWindowRejected("nonfinite Paper WAIT start position")
    input_readback = review_s50_input_samples(
        original, marker_id=marker, world=world,
        subject_uuid=subject_uuid, start_tick=first - 1,
    )
    previous = begin_position
    samples = []
    for i, row in enumerate(waits):
        try:
            tick = int(row["tick"])
            index = int(row["index"])
            origin = tuple(float(row["from_" + axis]) for axis in ("x", "y", "z"))
            target = tuple(float(row[axis]) for axis in ("x", "y", "z"))
        except (KeyError, TypeError, ValueError) as exc:
            raise S50LivePaperWindowRejected("malformed Paper sampled position") from exc
        if (
            tick != first + i or index != i + 1
            or row.get("marker_id") != marker
            or row.get("world") != world
            or not all(math.isfinite(v) for v in (*origin, *target))
            or (previous is not None and origin != previous)
        ):
            raise S50LivePaperWindowRejected("nonconsecutive/foreign Paper movement")
        samples.append(S50LivePaperTick(
            tick, math.dist(origin, target),
            tick in input_readback.sampled_input_active_ticks,
        ))
        previous = target
    return tuple(samples)


def capture_s50_live_paper_window(
    paper_prefix: bytes, *, session_id: str, action_id: str,
    world: str, subject_uuid: str,
) -> S50LivePaperWindow:
    """Capture only a newline-terminated *byte prefix* while Java remains live.

    Caller owns read boundary and must verify the server still runs. A
    prefix snapshot is immutable, but never implies Java/Node session end.
    """
    if (
        not isinstance(paper_prefix, bytes)
        or not 0 < len(paper_prefix) <= MAX_LIVE_PREFIX_BYTES
        or not paper_prefix.endswith(b"\n")
        or not all(
            isinstance(v, str) and 0 < len(v) <= 128 and not any(c.isspace() for c in v)
            for v in (session_id, action_id, world, subject_uuid)
        )
        or len(f"{action_id}-{session_id}") > 128
    ):
        raise S50LivePaperWindowRejected("unbounded/unterminated/missing S50 live source")
    ticks = _extract_window(
        paper_prefix, session_id=session_id, action_id=action_id,
        world=world, subject_uuid=subject_uuid,
    )
    # Parse input event count using existing owner, not client packet guesses.
    input_summary = review_s50_input_samples(
        paper_prefix, marker_id=f"{action_id}-{session_id}",
        world=world, subject_uuid=subject_uuid,
        start_tick=ticks[0].world_tick - 1,
    )
    return S50LivePaperWindow(
        session_id=session_id, action_id=action_id,
        marker_id=f"{action_id}-{session_id}",
        paper_world_uuid=world, subject_uuid=subject_uuid,
        paper_prefix_sha256=hashlib.sha256(paper_prefix).hexdigest(),
        paper_prefix_bytes=len(paper_prefix), ticks=ticks,
        input_event_count_at_window_end=input_summary.input_event_count_final,
    )


def verify_s50_live_window_against_final_paper(
    tentative: S50LivePaperWindow, final_paper_original: bytes,
) -> bool:
    """Post-hoc audit, NOT retrospective real-time qualification of an L0 choice.

    The exact immutable prefix MUST match byte-for-byte after final Java exit;
    this does not validate Node TRACE_END, which stays with the old S50 owner.
    """
    if (
        not isinstance(tentative, S50LivePaperWindow)
        or not tentative.provisional or tentative.final_source_verified
        or not isinstance(final_paper_original, bytes)
        or len(final_paper_original) < tentative.paper_prefix_bytes
        or len(final_paper_original) > 16_000_000
    ):
        raise S50LivePaperWindowRejected("missing/invalid final Paper source")
    prefix = final_paper_original[:tentative.paper_prefix_bytes]
    if hashlib.sha256(prefix).hexdigest() != tentative.paper_prefix_sha256:
        raise S50LivePaperWindowRejected("post-hoc Paper original prefix not identical")
    after = capture_s50_live_paper_window(
        prefix, session_id=tentative.session_id,
        action_id=tentative.action_id, world=tentative.paper_world_uuid,
        subject_uuid=tentative.subject_uuid,
    )
    if after != tentative:
        raise S50LivePaperWindowRejected("Paper window changed after capture")
    return True
