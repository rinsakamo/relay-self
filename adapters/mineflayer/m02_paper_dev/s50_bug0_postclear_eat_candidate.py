"""S-owned Bug-0 read-only join of existing S50 Paper WAIT and input readers.

Both existing readers inspect ONE original Paper stdout source. Matching eight
sampler callbacks do not attest server-effective S15 clear, continuous
physical inactivity, R qualification, an EAT grant, or P1 fatigue recovery.
"""
from __future__ import annotations

import hashlib
from dataclasses import dataclass

from adapters.mineflayer.m02_paper_dev.s50_boundary import BoundaryRejected
from adapters.mineflayer.m02_paper_dev.s50_input_witness_source import (
    S50InputWitnessRejected,
    review_s50_input_samples,
)
from adapters.mineflayer.m02_paper_dev.s50_p1_wait import candidate_wait_ticks

MAX_PAPER_ORIGINAL_BYTES = 16_000_000
QUIET_CANDIDATE = "SAMPLED_QUIET_INPUT_OFF_DEV_CANDIDATE_ONLY"
ACTIVITY_OBSERVED = "SAMPLED_ACTIVITY_OR_INPUT_CHANGE_NO_WAIT"


class S50Bug0PostClearRejected(ValueError):
    """Missing, mismatched or forged S50 observed-source join."""


@dataclass(frozen=True, slots=True)
class S50Bug0PostClearCandidate:
    """Diagnostic eligibility only. No Action/Skill/P1 ownership transferred."""

    paper_original_sha256: str
    marker_id: str
    world: str
    subject_uuid: str
    first_tick: int
    last_tick: int
    sampled_input_active_ticks: tuple[int, ...]
    sampled_body_activity_ticks: tuple[int, ...]
    input_event_count_final: int
    sample_status: str
    effective_s15_clear_tick: str = "NOT_ATTESTED"
    complete_tick_input_coverage: bool = False
    source_authenticated_independently: bool = False
    physically_stopped_proven: bool = False
    eat_action_authorized: bool = False
    p1_wait_ticks_admitted: int = 0
    learning_updates: int = 0


def review_s50_bug0_postclear_candidate(
    paper_original: bytes, *, marker_id: str,
    world: str, subject_uuid: str, wait_begin_tick: int,
    source_action_terminal: str,
) -> S50Bug0PostClearCandidate:
    """Reuse current S50 sources; correlate 8 same-tick samples without grant.

    A Paper callback is only one sample inside a World tick, even when
    its tick label is contiguous with other callbacks. A client-side clear
    ACK is not an independently observed server-effective tick transition.
    """
    if (
        not isinstance(paper_original, bytes)
        or not 0 < len(paper_original) <= MAX_PAPER_ORIGINAL_BYTES
        or any(
            not isinstance(x, str) or not x or len(x) > 128
            for x in (marker_id, world, subject_uuid)
        )
        or type(wait_begin_tick) is not int
        or wait_begin_tick < 0
        or source_action_terminal != "outcome"
    ):
        raise S50Bug0PostClearRejected(
            "bounded one-world post-S16 original required"
        )
    try:
        paper = paper_original.decode("utf-8")
    except UnicodeError as exc:
        raise S50Bug0PostClearRejected("not UTF-8 Paper original") from exc

    try:
        wait = candidate_wait_ticks(
            paper, marker_id=marker_id, expected_world=world,
            source_action_terminal=source_action_terminal,
        )
        witness = review_s50_input_samples(
            paper_original, marker_id=marker_id, world=world,
            subject_uuid=subject_uuid, start_tick=wait_begin_tick,
        )
    except (BoundaryRejected, S50InputWitnessRejected) as exc:
        raise S50Bug0PostClearRejected("S50 source join rejected") from exc
    if (
        wait["marker_id"] != witness.marker_id
        or wait["world"] != witness.world
        or wait["first_world_tick"] != witness.first_tick
        or wait["last_world_tick"] != witness.last_tick
        or wait["first_world_tick"] != wait_begin_tick + 1
        or wait["last_world_tick"] != wait_begin_tick + 8
        or len(wait["samples"]) != 8
        or wait["wait_ticks_admitted"] != 0
        or wait["p1_fatigue_recovered"] != 0.0
        or witness.p1_wait_ticks_admitted != 0
        or witness.entire_tick_input_idle
        or witness.physical_stability_verified
        or witness.effective_client_clear_tick != "NOT_ATTESTED"
    ):
        raise S50Bug0PostClearRejected(
            "cross-witness claim or World-tick boundary inconsistent"
        )
    body_activity = tuple(
        sample["world_tick"]
        for sample in wait["samples"]
        if not sample["observed_stationary"]
    )
    if tuple(wait["source_activity_ticks"]) != body_activity:
        raise S50Bug0PostClearRejected(
            "Paper WAIT activity tally inconsistent"
        )
    sampled_quiet = (
        not body_activity
        and not witness.sampled_input_active_ticks
        and not witness.input_event_observed
    )
    return S50Bug0PostClearCandidate(
        paper_original_sha256=hashlib.sha256(paper_original).hexdigest(),
        marker_id=marker_id, world=world, subject_uuid=subject_uuid,
        first_tick=witness.first_tick, last_tick=witness.last_tick,
        sampled_input_active_ticks=witness.sampled_input_active_ticks,
        sampled_body_activity_ticks=body_activity,
        input_event_count_final=witness.input_event_count_final,
        sample_status=QUIET_CANDIDATE if sampled_quiet else ACTIVITY_OBSERVED,
    )
