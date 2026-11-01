"""MP3 explicit archival -> provisional S50 handoff; no World/run authority.

Owner must call freeze_for_target BEFORE the S50 marker, persist the ticket,
then supply the existing owner window. This pure API does not prove chronology,
S16 OUTCOME or cleanup. It never relabels archived evidence as live evidence.
"""
from __future__ import annotations

from dataclasses import dataclass, replace

from adapters.mineflayer.m02_paper_dev.s50_live_paper_window import S50LivePaperWindow
from adapters.mineflayer.self_body_s50_l1_motion_prediction import (
    MotionHeldoutComparison,
    MotionPredictionRejected,
    MotionSequence,
    _compare_sequences,
    from_live_window,
)
from adapters.mineflayer.self_body_s50_l1_motion_prequential import (
    FrozenPredictionTicket,
    TargetWorldIdentity,
    _verify_ticket,
)


@dataclass(frozen=True, slots=True)
class LiveDevScore:
    ticket_sha256: str
    errors: MotionHeldoutComparison
    predictions_m: tuple[float, ...]
    measured_m: tuple[float, ...]
    classification: str = "CHEAP_EQUIVALENT"
    source_ceiling: str = "ARCHIVAL_TRAINING_TO_PROVISIONAL_PAPER_ONLY"
    chronology_attested: bool = False
    s16_outcome_verified: bool = False
    cleanup_verified: bool = False
    next_world_update: str = "WITHHELD_PENDING_ORIGINAL_OUTCOME_AND_CLEANUP"


def score_live_dev(
    ticket: FrozenPredictionTicket, training: MotionSequence,
    source: S50LivePaperWindow,
) -> LiveDevScore:
    """Explicit source transition, retaining both ceilings and MP2 checksum.

    Numeric scoring only. A constructed typed fixture cannot authenticate a
    physical run, and this result cannot enter MP2 update_after_score.
    """
    _verify_ticket(ticket, training)
    heldout = from_live_window(source)
    if (
        ticket.capture_mode != "PROSPECTIVE_LOCAL_ORDER_NOT_EXTERNALLY_ATTESTED"
        or training.source_ceiling != "ARCHIVAL_READBACK_NOT_REAUTHENTICATED"
        or ticket.target != TargetWorldIdentity(
            heldout.session_id, heldout.paper_world_uuid,
            heldout.action_id, heldout.subject_uuid,
        )
        or heldout.paper_prefix_sha256 == training.paper_prefix_sha256
        or any(s.last_reported_input_active for s in (*training.steps, *heldout.steps))
        or source.client_packet_writes_attested
    ):
        raise MotionPredictionRejected("invalid explicit archival/live DEV handoff")
    errors = replace(
        _compare_sequences(training, heldout),
        provenance_ceiling="ARCHIVAL_TRAINING_TO_PROVISIONAL_PAPER_ONLY",
        classification="CHEAP_EQUIVALENT",
    )
    return LiveDevScore(
        ticket.ticket_sha256, errors,
        tuple(ticket.model.slope * s.displacement_m for s in heldout.steps[:-1]),
        tuple(s.displacement_m for s in heldout.steps[1:]),
    )
