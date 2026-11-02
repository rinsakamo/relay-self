"""WB-only L2-question ATT shadow and later-source review handoff.

Neither surface is a retained Habit, selected physical Action, learned World
hypothesis, S10/Memory transaction, or an L-lane owner. They only project a
previously source-bound WBL2UncertaintyRead into existing ATT data structures.
"""
from __future__ import annotations

from dataclasses import dataclass

from relay_self.attention import AttentionCandidate, AttentionCriterion, select_attention
from relay_self.provenance import Provenance
from relay_self.wb_l2_read_port import WBL2UncertaintyRead


@dataclass(frozen=True, slots=True)
class WBL1AttentionShadow:
    state: str  # UNAVAILABLE / ATT_SELECTED_READ_ONLY
    source_world_seq: int | None
    source_ref: str | None
    question: str | None
    selected_candidate_ids: tuple[str, ...] = ()
    authority: str = "ATT_SHADOW_NO_L1_POLICY_OR_ACTION"
    source_attested: bool = False

    def to_mapping(self) -> dict[str, object]:
        return {
            "state": self.state,
            "source_world_seq": self.source_world_seq,
            "source_ref": self.source_ref,
            "question": self.question,
            "selected_candidate_ids": list(self.selected_candidate_ids),
            "authority": self.authority,
            "source_attested": self.source_attested,
        }


@dataclass(frozen=True, slots=True)
class WBL2ReviewHandoff:
    state: str  # UNAVAILABLE / PENDING_INDEPENDENT_OUTCOME
    session_id: str | None
    origin_world_seq: int | None
    later_world_seq: int | None
    origin_source_ref: str | None
    later_source_ref: str | None
    question: str | None
    outcome_verified: bool = False
    learning_authorized: bool = False
    authority: str = "READ_ONLY_REVIEW_NOT_MEMORY_OR_S10"

    def to_mapping(self) -> dict[str, object]:
        return {
            "state": self.state,
            "session_id": self.session_id,
            "origin_world_seq": self.origin_world_seq,
            "later_world_seq": self.later_world_seq,
            "origin_source_ref": self.origin_source_ref,
            "later_source_ref": self.later_source_ref,
            "question": self.question,
            "outcome_verified": self.outcome_verified,
            "learning_authorized": self.learning_authorized,
            "authority": self.authority,
        }


def project_wb_l1_attention_shadow(read: WBL2UncertaintyRead) -> WBL1AttentionShadow:
    """Use the *existing* ATT selector; no L1 Habit/policy consumer is installed."""
    unavailable = WBL1AttentionShadow("UNAVAILABLE", None, None, None)
    if (
        not isinstance(read, WBL2UncertaintyRead)
        or read.state != "CURRENT_EPOCH_READ_ONLY"
        or read.source_attested is not False
        or read.authority != "READ_ONLY_NO_ACTION_MEMORY_LEARNING_HABIT"
        or type(read.source_world_seq) is not int
        or not isinstance(read.source_ref, str)
        or not isinstance(read.current_uncertainty, str)
        or not 0 < len(read.current_uncertainty.strip()) <= 300
        or read.past_review_candidate is not None
        or read.latest_world_seq != read.source_world_seq
    ):
        return unavailable
    candidate = AttentionCandidate(
        "wb-l2-question", read.source_ref,
        Provenance("wb-s60-generated-uncertainty-not-world-fact", read.source_ref),
        priority=0, focus_keys=("wb-l2-uncertainty",),
    )
    selection = select_attention(
        (candidate,), AttentionCriterion(
            "wb-l1-attention-shadow", focus_key="wb-l2-uncertainty", top_k=1,
        ),
    )
    if selection.candidate_ids != ("wb-l2-question",):
        return unavailable
    return WBL1AttentionShadow(
        "ATT_SELECTED_READ_ONLY", read.source_world_seq,
        read.source_ref, read.current_uncertainty, selection.candidate_ids,
    )


def project_wb_past_review_handoff(
    read: WBL2UncertaintyRead, *, later_source_ref: str | None,
) -> WBL2ReviewHandoff:
    """Carry an old *question* next to a later same-session source, not an outcome.

    The latest native observation is only a source pointer. Evaluating whether
    it answers the L2 question belongs to a separately authorized L lane.
    """
    unavailable = WBL2ReviewHandoff("UNAVAILABLE", None, None, None, None, None, None)
    if (
        not isinstance(read, WBL2UncertaintyRead)
        or read.state != "PAST_EPOCH_REVIEW_ONLY"
        or read.source_attested is not False
        or read.authority != "READ_ONLY_NO_ACTION_MEMORY_LEARNING_HABIT"
        or not isinstance(read.session_id, str) or not read.session_id
        or type(read.source_world_seq) is not int
        or type(read.latest_world_seq) is not int
        or read.latest_world_seq <= read.source_world_seq
        or not isinstance(read.source_ref, str)
        or not read.source_ref.startswith(
            f"present:{read.session_id}:{read.source_world_seq}:"
        )
        or read.current_uncertainty is not None
        or not isinstance(read.past_review_candidate, str)
        or not 0 < len(read.past_review_candidate.strip()) <= 300
        or not isinstance(later_source_ref, str)
        or not later_source_ref.startswith(
            f"present:{read.session_id}:{read.latest_world_seq}:"
        )
        or later_source_ref == read.source_ref
    ):
        return unavailable
    return WBL2ReviewHandoff(
        "PENDING_INDEPENDENT_OUTCOME", read.session_id,
        read.source_world_seq, read.latest_world_seq,
        read.source_ref, later_source_ref, read.past_review_candidate,
    )
