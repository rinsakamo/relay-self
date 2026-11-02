"""WB structured L2 read port: current-epoch attention vs past-source review.

Pure, bounded presentation of one S60-admitted uncertainty. The model output is
a question, NOT a verified prediction, action, memory, learned rule or Habit.
This module cannot read World, query a provider or commit to a Learning owner.
"""
from __future__ import annotations

import json
from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class WBL2UncertaintyRead:
    """Immutable read surface; never an owner authority or a verified source."""

    state: str  # UNAVAILABLE / CURRENT_EPOCH_READ_ONLY / PAST_EPOCH_REVIEW_ONLY
    session_id: str | None
    source_world_seq: int | None
    latest_world_seq: int | None
    source_ref: str | None
    current_uncertainty: str | None
    past_review_candidate: str | None
    origin: str = "L2_GENERATED_UNCERTAINTY_NOT_WORLD_FACT"
    authority: str = "READ_ONLY_NO_ACTION_MEMORY_LEARNING_HABIT"
    source_attested: bool = False

    def to_mapping(self) -> dict[str, object]:
        return {
            "state": self.state,
            "session_id": self.session_id,
            "source_world_seq": self.source_world_seq,
            "latest_world_seq": self.latest_world_seq,
            "source_ref": self.source_ref,
            "current_uncertainty": self.current_uncertainty,
            "past_review_candidate": self.past_review_candidate,
            "origin": self.origin,
            "authority": self.authority,
            "source_attested": self.source_attested,
        }


def _unique_json_pairs(pairs: list[tuple[str, object]]) -> dict[str, object]:
    if len({key for key, _ in pairs}) != len(pairs):
        raise ValueError("duplicate JSON field")
    return dict(pairs)


def project_wb_l2_uncertainty(
    *,
    accepted_text: str | None,
    session_id: str | None,
    source_world_seq: int | None,
    latest_world_seq: int | None,
    source_ref: str | None,
    expected_source_ref: str | None,
    owner_admitted: bool,
    source_callback_failed: bool = False,
) -> WBL2UncertaintyRead:
    """Fail-closed projection of an already-admitted, source-bound L2 question.

    An exact same-source snapshot offers read-only current attention. A newer
    native callback removes current availability and exposes the old question
    for *possible* future review only; it does not assert prediction validity
    or create an experience record. Caller authenticates original S49 owner.
    """
    unavailable = WBL2UncertaintyRead(
        "UNAVAILABLE", None, None, None, None, None, None,
    )
    if (
        type(owner_admitted) is not bool or not owner_admitted
        or type(source_callback_failed) is not bool or source_callback_failed
        or not isinstance(session_id, str) or not session_id
        or type(source_world_seq) is not int or source_world_seq < 1
        or type(latest_world_seq) is not int
        or latest_world_seq < source_world_seq
        or not isinstance(source_ref, str)
        or not isinstance(expected_source_ref, str)
        or source_ref != expected_source_ref
        or not source_ref.startswith(f"present:{session_id}:{source_world_seq}:")
        or not isinstance(accepted_text, str)
        or len(accepted_text) > 2048
    ):
        return unavailable
    try:
        payload = json.loads(accepted_text, object_pairs_hook=_unique_json_pairs)
    except (ValueError, TypeError):
        return unavailable
    if (
        not isinstance(payload, dict)
        or set(payload) != {"uncertainty"}
        or not isinstance(payload["uncertainty"], str)
        or not 0 < len(payload["uncertainty"].strip()) <= 300
    ):
        return unavailable
    question = payload["uncertainty"]
    if latest_world_seq == source_world_seq:
        return WBL2UncertaintyRead(
            "CURRENT_EPOCH_READ_ONLY", session_id, source_world_seq,
            latest_world_seq, source_ref, question, None,
        )
    return WBL2UncertaintyRead(
        "PAST_EPOCH_REVIEW_ONLY", session_id, source_world_seq,
        latest_world_seq, source_ref, None, question,
    )
