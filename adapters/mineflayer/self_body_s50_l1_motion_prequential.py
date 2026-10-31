"""#653 L1-MP2: freeze -> heldout score -> next-World refit, read-only DEV.

Does NOT attest pre-World wall-clock chronology: archived replay demonstrates
only API ordering. The immutable ticket digest is a consistency checksum, NOT
a signature or independent source authentication. No native read or Action.
"""
from __future__ import annotations

import hashlib
import json
import math
from dataclasses import asdict, dataclass

from adapters.mineflayer.self_body_s50_l1_motion_prediction import (
    MotionForecast,
    MotionHeldoutComparison,
    MotionPredictionRejected,
    MotionSequence,
    _require_sequence,
    evaluate_heldout,
    freeze_forecast,
)

_ARCHIVE_REPLAY = "ARCHIVAL_REPLAY_ORDER_SIMULATION_ONLY"
_PREPARED_LOCAL = "PROSPECTIVE_LOCAL_ORDER_NOT_EXTERNALLY_ATTESTED"


@dataclass(frozen=True, slots=True)
class TargetWorldIdentity:
    session_id: str
    paper_world_uuid: str
    action_id: str
    subject_uuid: str


@dataclass(frozen=True, slots=True)
class FrozenPredictionTicket:
    """Frozen *before calling score*, not physical timestamp proof."""

    model: MotionForecast
    target: TargetWorldIdentity
    source_ceiling: str
    capture_mode: str
    ticket_sha256: str
    issued_action: bool = False
    goal_admitted: bool = False
    p1_wait_admitted: int = 0
    s10_updates: int = 0
    s11_grants: int = 0


@dataclass(frozen=True, slots=True)
class ScoredPredictionTicket:
    ticket: FrozenPredictionTicket
    heldout_prefix_sha256: str
    errors: MotionHeldoutComparison
    scoring_status: str = "DEV_SOURCE_SHAPED_ORDER_ONLY"
    prediction_committed_before_world_attested: bool = False
    original_paper_reauthenticated: bool = False
    learned_l1_policy: bool = False


@dataclass(frozen=True, slots=True)
class NextWorldRefit:
    """Experiment-local two-source model, not PersistentCognition/PRD/MEM."""

    predecessor_ticket_sha256: str
    training_source_sha256: str
    newly_scored_source_sha256: str
    distinct_worlds: int
    training_pairs: int
    refitted_slope: float
    refitted_mean_m: float
    cheap_pooled_slope: float
    cheap_equivalent: bool = True
    classification: str = "CHEAP_POOLED_REFIT_EQUIVALENT_UNTESTED_NEXT_WORLD"
    learning_admissions: int = 0
    s10_updates: int = 0
    s11_grants: int = 0
    action_issues: int = 0


def _ticket_digest(
    model: MotionForecast, target: TargetWorldIdentity, ceiling: str,
    mode: str,
) -> str:
    payload = json.dumps({
        "model": asdict(model), "target": asdict(target),
        "source_ceiling": ceiling, "capture_mode": mode,
        "schema": "S50_L1_MP2_FREEZE_V1",
    }, sort_keys=True, ensure_ascii=True, allow_nan=False, separators=(",", ":"))
    return hashlib.sha256(payload.encode("ascii")).hexdigest()


def _validate_identity(target: TargetWorldIdentity) -> None:
    if not isinstance(target, TargetWorldIdentity):
        raise MotionPredictionRejected("target typed identity required")
    if any(
        type(v) is not str or not v or len(v) > 128 or any(c.isspace() for c in v)
        for v in (
            target.session_id, target.paper_world_uuid,
            target.action_id, target.subject_uuid,
        )
    ):
        raise MotionPredictionRejected("unbound or invalid target identity")


def freeze_for_target(
    training: MotionSequence, target: TargetWorldIdentity, *,
    capture_mode: str = _ARCHIVE_REPLAY,
) -> FrozenPredictionTicket:
    """Make a one-target ticket using ONLY training (no future measurements).

    The archive mode is for CI. Local mode remains a DEV *intent* until
    independent source and chronology evidence is collected in a real run.
    """
    _require_sequence(training)
    _validate_identity(target)
    if (
        capture_mode not in (_ARCHIVE_REPLAY, _PREPARED_LOCAL)
        or target.session_id == training.session_id
        or target.paper_world_uuid == training.paper_world_uuid
        or target.subject_uuid != training.subject_uuid
    ):
        raise MotionPredictionRejected("target must be a separate matched World")
    model = freeze_forecast(training)
    digest = _ticket_digest(model, target, training.source_ceiling, capture_mode)
    return FrozenPredictionTicket(
        model, target, training.source_ceiling, capture_mode, digest,
    )


def _verify_ticket(ticket: FrozenPredictionTicket, training: MotionSequence) -> None:
    _require_sequence(training)
    if (
        not isinstance(ticket, FrozenPredictionTicket)
        or ticket.issued_action or ticket.goal_admitted or ticket.p1_wait_admitted
        or ticket.s10_updates or ticket.s11_grants
        or ticket.capture_mode not in (_ARCHIVE_REPLAY, _PREPARED_LOCAL)
        or ticket.source_ceiling != training.source_ceiling
        or ticket.model != freeze_forecast(training)
    ):
        raise MotionPredictionRejected("training changed after ticket freeze")
    _validate_identity(ticket.target)
    if (
        ticket.target.session_id == training.session_id
        or ticket.target.paper_world_uuid == training.paper_world_uuid
        or ticket.target.subject_uuid != training.subject_uuid
        or ticket.ticket_sha256 != _ticket_digest(
            ticket.model, ticket.target, ticket.source_ceiling, ticket.capture_mode
        )
    ):
        raise MotionPredictionRejected("ticket checksum or World identity mismatch")


def score_frozen(
    ticket: FrozenPredictionTicket, training: MotionSequence,
    heldout: MotionSequence,
) -> ScoredPredictionTicket:
    """Score the *same* frozen slope; no heldout-fit and no rule escalation.

    Offline caller input order can be tested, but cannot prove a real World
    timeline. Real source provenance/cleanup are separate owners.
    """
    _verify_ticket(ticket, training)
    _require_sequence(heldout)
    target = ticket.target
    if (
        heldout.session_id != target.session_id
        or heldout.paper_world_uuid != target.paper_world_uuid
        or heldout.action_id != target.action_id
        or heldout.subject_uuid != target.subject_uuid
        or heldout.source_ceiling != ticket.source_ceiling
        or any(step.last_reported_input_active for step in heldout.steps)
        or any(step.last_reported_input_active for step in training.steps)
    ):
        raise MotionPredictionRejected("foreign/changed-regime heldout callback source")
    result = evaluate_heldout(training, heldout)
    if result.slope != ticket.model.slope or not result.exact_cheap_equivalence:
        raise MotionPredictionRejected("forecast/cheap baseline changed on heldout")
    return ScoredPredictionTicket(
        ticket=ticket, heldout_prefix_sha256=heldout.paper_prefix_sha256,
        errors=result,
    )


def update_after_score(
    ticket: FrozenPredictionTicket, training: MotionSequence,
    heldout: MotionSequence, scored: ScoredPredictionTicket,
) -> NextWorldRefit:
    """Experiment-local refit for a THIRD future World; never score it here.

    A forged or reused score cannot silently become retained S10/MEM.
    """
    _verify_ticket(ticket, training)
    if (
        not isinstance(scored, ScoredPredictionTicket)
        or scored.ticket != ticket
        or scored.heldout_prefix_sha256 != heldout.paper_prefix_sha256
        or scored.scoring_status != "DEV_SOURCE_SHAPED_ORDER_ONLY"
        or scored.prediction_committed_before_world_attested
        or scored.original_paper_reauthenticated
        or scored.learned_l1_policy
        or score_frozen(ticket, training, heldout) != scored
    ):
        raise MotionPredictionRejected("missing or altered prior heldout score")
    all_pairs = tuple(
        (a.displacement_m, b.displacement_m)
        for source in (training, heldout)
        for a, b in zip(source.steps[:-1], source.steps[1:])
    )
    numerator = math.fsum(a * b for a, b in all_pairs)
    denominator = math.fsum(a * a for a, _ in all_pairs)
    slope = numerator / denominator if denominator else 0.0
    mean = math.fsum(b for _, b in all_pairs) / len(all_pairs)
    if not math.isfinite(slope) or not math.isfinite(mean):
        raise MotionPredictionRejected("invalid refit")
    # Same sufficient stats and same evidence for the cheapest alternative.
    cheap = numerator / denominator if denominator else 0.0
    return NextWorldRefit(
        predecessor_ticket_sha256=ticket.ticket_sha256,
        training_source_sha256=training.paper_prefix_sha256,
        newly_scored_source_sha256=heldout.paper_prefix_sha256,
        distinct_worlds=2, training_pairs=len(all_pairs),
        refitted_slope=slope, refitted_mean_m=mean,
        cheap_pooled_slope=cheap,
    )
