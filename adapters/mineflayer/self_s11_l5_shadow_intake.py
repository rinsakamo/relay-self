"""S11: S-owned, read-only L5 proposal intake against S10's fixed L0 baseline.

Consumes L5 ShadowAdvice *data*, not a new decision policy, Action candidate
grant or independently authenticated original. L5's policy and its cheap
comparators are owned by L; S10 keeps its original S49 L0 unchanged.

The intentionally separate L5/S10 synthetic fixtures cannot be presented
as one paired native World trial by copying a session ID or a SHA pointer.
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from enum import Enum
from typing import Mapping

from adapters.mineflayer.python_protocol import MineflayerObservation
from adapters.mineflayer.self_s10_memory_ablation import S10ShadowAB

L5_EXACT_HEAD = "17c5357fd5625274ee567ad979b780e77bf7b1e7"
_SHA = re.compile(r"[0-9a-f]{64}\Z")
_TOKEN = re.compile(r"[A-Za-z0-9_.:/-]+\Z")
_L5_KEYS = frozenset({
    "status", "proposed_action_ref", "original_no_memory_ref",
    "exact_cue_cheap_ref", "singleton_cheap_ref", "global_cheap_ref",
    "training_sessions", "comparisons", "memory_causal_benefit_established",
    "goal_improvement_attested", "action_authority", "habit_grants",
    "learning_updates", "reason",
})
_L5_POSITIVE = "shadow_distinct_from_cheapest_controls"
_L5_EQUAL = {"cheap_same_information_matches", "unchanged_from_no_memory"}
_L5_ABSTAIN = {
    "no_goal_data", "unverified_originals",
    "insufficient_balanced_contexts", "ambiguous_contextual_evidence",
}


class S11IntakeRejected(ValueError):
    """A prospective L5/S10 source or admission assertion cannot be trusted."""


class S11Disposition(str, Enum):
    L5_ABSTAINED = "l5_abstained_no_action"
    CHEAP_OR_NO_MEMORY_EQUAL = "cheap_or_no_memory_equal_no_action"
    UNPAIRED_SOURCE = "l5_s10_not_paired_no_action"
    SHADOW_DIFFERENCE = "shadow_difference_non_authorizing"


@dataclass(frozen=True, slots=True)
class S11SourcePointer:
    """Claimed L5 current context; source authenticity NOT created by this class."""

    session_id: str
    source_seq: int
    original_probe_sha256: str
    claimed_l5_head: str

    def __post_init__(self) -> None:
        if (
            not isinstance(self.session_id, str)
            or _TOKEN.fullmatch(self.session_id) is None
            or type(self.source_seq) is not int or self.source_seq < 0
            or not isinstance(self.original_probe_sha256, str)
            or _SHA.fullmatch(self.original_probe_sha256) is None
            or self.claimed_l5_head != L5_EXACT_HEAD
        ):
            raise S11IntakeRejected("exact L5 source and current probe pointer required")


@dataclass(frozen=True, slots=True)
class S11ReadOnlyReview:
    status: S11Disposition
    session_id: str
    probe_seq: int
    fixed_l0_selection: str
    suggested_ref: str | None
    no_memory_ref: str | None
    two_feature_cheap_equivalent_possible: bool = True
    source_byte_authenticated_here: bool = False
    goal_evidence_authenticated_here: bool = False
    physical_actions: int = 0
    action_authority: bool = False
    memory_causal_benefit_established: bool = False
    learning_updates: int = 0
    habit_grants: int = 0
    science_qualified: bool = False


def _ref(value: object) -> bool:
    return value is None or (
        isinstance(value, str) and _TOKEN.fullmatch(value) is not None
    )


def review_l5_against_s10(
    *,
    paired: S10ShadowAB,
    current_probe: MineflayerObservation,
    source: S11SourcePointer,
    admitted_current_probe_sha256: frozenset[str],
    l5_advice: Mapping[str, object],
) -> S11ReadOnlyReview:
    """Accept an advisory comparison only, with no World/Action side effects.

    NOTE: exact pointer membership is only caller-supplied evidence *shape*.
    It does not rehash Mineflayer bridge original bytes, prove R1/R2
    typed Action/Goal source, or certify that L5's training actually occurred.
    """
    if (
        not isinstance(paired, S10ShadowAB)
        or not isinstance(current_probe, MineflayerObservation)
        or not isinstance(source, S11SourcePointer)
        or not isinstance(admitted_current_probe_sha256, frozenset)
        or any(not isinstance(x, str) or _SHA.fullmatch(x) is None
               for x in admitted_current_probe_sha256)
        or not isinstance(l5_advice, Mapping)
        or frozenset(l5_advice) != _L5_KEYS
    ):
        raise S11IntakeRejected("exact matched S10/L5 data shape required")
    if (
        paired.disposition != "RECALL_DIFFERENCE_NO_L0_DECISION_EFFECT"
        or paired.present_hint != "recall" or paired.withheld_hint == "recall"
        or paired.present_selection != paired.withheld_selection
        or paired.retained_memory_count < 1
        or paired.physical_runs != 0 or paired.issued_actions != 0
        or paired.goal_attested or paired.memory_caused_physical_action
        or paired.learning_updates or paired.habit_grants or paired.scientific_go
        or current_probe.kind != "probe" or not current_probe.request_id
        or current_probe.provenance.source != "mineflayer"
        or current_probe.snapshot.nearby_entities_coverage.truncated
        or current_probe.session_id != paired.session_id
        or current_probe.seq != paired.probe_seq
    ):
        raise S11IntakeRejected("S10 original read-only paired L0 invariant required")
    status = l5_advice["status"]
    status = getattr(status, "value", status)  # accepts L5's *actual* str Enum
    if status not in {_L5_POSITIVE, *_L5_EQUAL, *_L5_ABSTAIN}:
        raise S11IntakeRejected("unknown exact L5 status")
    for field in (
        "proposed_action_ref", "original_no_memory_ref",
        "exact_cue_cheap_ref", "singleton_cheap_ref", "global_cheap_ref",
    ):
        if not _ref(l5_advice[field]):
            raise S11IntakeRejected("L5 Action ref not in declared token vocabulary")
    for field in ("training_sessions", "comparisons", "habit_grants", "learning_updates"):
        if type(l5_advice[field]) is not int or l5_advice[field] < 0:
            raise S11IntakeRejected("bounded numeric L5 claim required")
    if (
        l5_advice["memory_causal_benefit_established"] is not False
        or l5_advice["goal_improvement_attested"] is not False
        or l5_advice["action_authority"] is not False
        or l5_advice["habit_grants"] != 0
        or l5_advice["learning_updates"] != 0
        or not isinstance(l5_advice["reason"], str)
        or not l5_advice["reason"]
    ):
        raise S11IntakeRejected("L5 cannot transfer authority or a science/goal claim")
    proposed = l5_advice["proposed_action_ref"]
    no_memory = l5_advice["original_no_memory_ref"]
    cheap = (
        l5_advice["exact_cue_cheap_ref"],
        l5_advice["singleton_cheap_ref"],
        l5_advice["global_cheap_ref"],
    )
    if status == _L5_POSITIVE and (
        proposed is None or no_memory is None
        or proposed == no_memory or proposed in cheap
        or l5_advice["training_sessions"] < 16
    ):
        raise S11IntakeRejected("unsupported claimed contextual difference")
    if status in _L5_EQUAL and proposed is None:
        raise S11IntakeRejected("equal-control result requires a candidate")
    if status in _L5_ABSTAIN and proposed is not None:
        raise S11IntakeRejected("abstention cannot contain executable candidate")
    if status in _L5_ABSTAIN:
        disposition = S11Disposition.L5_ABSTAINED
    elif (
        source.session_id != paired.session_id
        or source.source_seq != paired.probe_seq
        or source.original_probe_sha256 not in admitted_current_probe_sha256
        or no_memory != paired.withheld_selection
    ):
        # L5's separately tested OPTION_A/B synthetic case is intentionally
        # UNPAIRED with S10's MOVE_AWAY: cannot rewrite the baseline.
        disposition = S11Disposition.UNPAIRED_SOURCE
    elif status in _L5_EQUAL:
        disposition = S11Disposition.CHEAP_OR_NO_MEMORY_EQUAL
    else:
        disposition = S11Disposition.SHADOW_DIFFERENCE
    return S11ReadOnlyReview(
        status=disposition, session_id=paired.session_id,
        probe_seq=paired.probe_seq,
        fixed_l0_selection=paired.present_selection,
        suggested_ref=proposed, no_memory_ref=no_memory,
    )
