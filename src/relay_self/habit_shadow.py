"""L3: non-authorizing S11 shadow review of externally goal-labeled L1 experience.

Goal labels and digests MUST be independently qualified by S/V. This module
does not authenticate physical World bytes, learn a production Habit, create
LearningUpdateAuthority, or issue/schedule any Action. The strongest cheap
exact-cue majority comparator sees precisely the same admitted training data.
"""
from __future__ import annotations

import json
import re
from dataclasses import dataclass
from enum import Enum

from relay_self.experience_bridge import ReuseQuery, ReuseStatus, retrieve_experience
from relay_self.habit import (
    CueFeature,
    HabitCue,
    HabitRepertoire,
    HabitRule,
    HabitSelectionStatus,
    select_habit,
)
from relay_self.persistent_cognition import Memory, PersistentCognition
from relay_self.provenance import Provenance

_TOKEN = re.compile(r"[A-Za-z0-9_.:/-]+")
_SHA = re.compile(r"[0-9a-f]{64}")
_L1_KEYS = frozenset({
    "schema", "session_id", "world_revision", "action_id", "binding_id",
    "action_ref", "source_status", "disposition", "reason_code",
    "evidence_sha256", "cue_tags", "hypothesis",
})
MAX_SAMPLES = 48


class ShadowHabitRejected(ValueError):
    """Malformed or forged source lineage; no fallback to conjectural labels."""


class ShadowStatus(str, Enum):
    NO_GOAL_EVIDENCE = "no_goal_evidence"
    UNVERIFIED = "unverified"
    INSUFFICIENT = "insufficient"
    CONFLICTING = "conflicting"
    SHIFT_DETECTED = "shift_detected"
    CHEAP_NULL_EQUAL = "cheap_null_equal"


@dataclass(frozen=True, slots=True)
class ExternalGoalLabel:
    """S/V-attested external goal source pointer, NOT created from movement.

    Its mere construction does not qualify the contents of the external goal
    evidence. Caller must separately authenticate the exact original bytes.
    """

    observed_memory_id: str
    goal_source_sha256: str
    goal_reached: bool
    provenance: Provenance

    def __post_init__(self) -> None:
        if (
            not isinstance(self.observed_memory_id, str)
            or not self.observed_memory_id.startswith("l1:")
            or not isinstance(self.goal_source_sha256, str)
            or _SHA.fullmatch(self.goal_source_sha256) is None
            or type(self.goal_reached) is not bool
            or not isinstance(self.provenance, Provenance)
        ):
            raise ShadowHabitRejected("typed external goal evidence required")


@dataclass(frozen=True, slots=True)
class GoalSourceAdmission:
    """Exact digests independently admitted by S/V owners; no internal signing."""

    admitted_action_sha256: frozenset[str]
    admitted_goal_sha256: frozenset[str]

    def __post_init__(self) -> None:
        for name in ("admitted_action_sha256", "admitted_goal_sha256"):
            value = getattr(self, name)
            if (
                not isinstance(value, frozenset)
                or any(not isinstance(x, str) or _SHA.fullmatch(x) is None
                       for x in value)
            ):
                raise ShadowHabitRejected("source-owned digest admission required")


@dataclass(frozen=True, slots=True)
class _Sample:
    session_id: str
    revision: int
    action_ref: str
    cue_tags: tuple[str, ...]
    observed_sha256: str
    goal_sha256: str
    goal_reached: bool
    memory_id: str


@dataclass(frozen=True, slots=True)
class ShadowReview:
    status: ShadowStatus
    candidate_ref: str | None = None
    cheap_candidate_ref: str | None = None
    train_sessions: int = 0
    holdout_sessions: int = 0
    selection_matches: bool = False
    action_authority: bool = False
    learning_updates: int = 0
    habit_grants: int = 0
    reason: str = ""


def _tags(tags: object) -> None:
    if (
        not isinstance(tags, tuple) or not tags
        or any(not isinstance(x, str) or _TOKEN.fullmatch(x) is None for x in tags)
        or tags != tuple(sorted(set(tags)))
    ):
        raise ShadowHabitRejected("sorted, unique source cue tags required")


def _samples(
    owner: PersistentCognition,
    labeled: tuple[ExternalGoalLabel, ...],
    admission: GoalSourceAdmission,
) -> tuple[tuple[_Sample, ...], bool]:
    if not isinstance(labeled, tuple) or len(labeled) > MAX_SAMPLES:
        raise ShadowHabitRejected("bounded external goal label tuple required")
    if any(not isinstance(x, ExternalGoalLabel) for x in labeled):
        raise ShadowHabitRejected("typed external goal labels required")
    by_id = {m.memory_id: m for m in owner.memories}
    samples = []
    unknown = False
    seen = set()
    for label in labeled:
        if label.observed_memory_id in seen:
            raise ShadowHabitRejected("duplicate original observation or goal label")
        seen.add(label.observed_memory_id)
        stored = by_id.get(label.observed_memory_id)
        if stored is None:
            raise ShadowHabitRejected("original L1 observed Memory absent")
        try:
            data = json.loads(stored.content)
            if (
                not isinstance(data, dict)
                or frozenset(data) != _L1_KEYS
                or data["schema"] != "L1_SOURCE_EPISODE_V1"
                or data["source_status"] != "executed"
                or data["disposition"] != "outcome"
                or data["reason_code"] != "observed_execution"
                or not isinstance(data["cue_tags"], list)
                or label.observed_memory_id != (
                    f'l1:{data["session_id"]}:{data["action_id"]}:'
                    f'{data["world_revision"]}'
                )
            ):
                raise ShadowHabitRejected("goal label is not an observed S16 outcome")
            cue_tags = tuple(data["cue_tags"])
            _tags(cue_tags)
            if (
                not isinstance(data["session_id"], str)
                or not data["session_id"]
                or type(data["world_revision"]) is not int
                or data["world_revision"] < 0
                or not isinstance(data["action_ref"], str)
                or _TOKEN.fullmatch(data["action_ref"]) is None
                or not isinstance(data["evidence_sha256"], str)
                or _SHA.fullmatch(data["evidence_sha256"]) is None
            ):
                raise ShadowHabitRejected("invalid original L1 Action scope")
        except (ValueError, TypeError, KeyError) as exc:
            raise ShadowHabitRejected("malformed original L1 observed Memory") from exc
        # Reuse the actual L1 admission and contradiction gate; a goal label
        # never rewrites S16 UNKNOWN into a physically observed execution.
        hint = retrieve_experience(owner, ReuseQuery(
            data["session_id"], data["world_revision"], cue_tags,
            frozenset({data["evidence_sha256"]}), max_revision_lag=0,
        ))
        if (
            hint.status is not ReuseStatus.RECALL
            or stored.memory_id not in hint.memory_ids
            or data["action_ref"] not in hint.observed_action_refs
        ):
            raise ShadowHabitRejected("L1 source outcome not qualified for reuse")
        if (
            data["evidence_sha256"] not in admission.admitted_action_sha256
            or label.goal_source_sha256 not in admission.admitted_goal_sha256
        ):
            unknown = True
            continue
        samples.append(_Sample(
            data["session_id"], data["world_revision"], data["action_ref"],
            cue_tags, data["evidence_sha256"], label.goal_source_sha256,
            label.goal_reached, stored.memory_id,
        ))
    return tuple(samples), unknown


def cheap_exact_cue_majority(
    samples: tuple[_Sample, ...],
    cue_tags: tuple[str, ...],
) -> str | None:
    """No extra features: strongest cheap mean-success rate over same train."""
    scores: dict[str, tuple[int, int]] = {}
    for item in samples:
        if item.cue_tags != cue_tags:
            continue
        wins, total = scores.get(item.action_ref, (0, 0))
        scores[item.action_ref] = (wins + int(item.goal_reached), total + 1)
    if not scores:
        return None
    ordered = sorted(
        scores,
        key=lambda act: (
            scores[act][0] / scores[act][1], scores[act][0], -scores[act][1],
        ),
        reverse=True,
    )
    best = ordered[0]
    if len(ordered) > 1:
        first = scores[best]
        other = scores[ordered[1]]
        if first[0] * other[1] == other[0] * first[1]:
            return None
    return best


def review_shadow_habit(
    owner: PersistentCognition,
    *,
    train: tuple[ExternalGoalLabel, ...],
    holdout: tuple[ExternalGoalLabel, ...],
    admission: GoalSourceAdmission,
    cue_tags: tuple[str, ...],
    min_train_sessions: int = 3,
    min_holdout_sessions: int = 2,
) -> ShadowReview:
    """Simulate S11 selection only; NEVER return a retained HabitRepertoire.

    Holdout does NOT train or select a rule. Equal cheap exact-cue performance
    deliberately fails the value-added gate for habit admission.
    """
    if not isinstance(owner, PersistentCognition):
        raise ShadowHabitRejected("existing owner required")
    if not isinstance(admission, GoalSourceAdmission):
        raise ShadowHabitRejected("external goal admission required")
    _tags(cue_tags)
    if (
        type(min_train_sessions) is not int or not 2 <= min_train_sessions <= 16
        or type(min_holdout_sessions) is not int
        or not 1 <= min_holdout_sessions <= 16
    ):
        raise ShadowHabitRejected("bounded independent session requirements")
    if not train or not holdout:
        return ShadowReview(ShadowStatus.NO_GOAL_EVIDENCE, reason="no_external_goal_source")
    train_samples, train_unverified = _samples(owner, train, admission)
    test_samples, test_unverified = _samples(owner, holdout, admission)
    if train_unverified or test_unverified:
        return ShadowReview(ShadowStatus.UNVERIFIED, reason="original_digest_not_admitted")
    if (
        len(set(x.memory_id for x in train_samples + test_samples))
        != len(train_samples + test_samples)
        or set(x.session_id for x in train_samples)
        & set(x.session_id for x in test_samples)
        or set(x.observed_sha256 for x in train_samples)
        & set(x.observed_sha256 for x in test_samples)
        or set(x.goal_sha256 for x in train_samples)
        & set(x.goal_sha256 for x in test_samples)
    ):
        raise ShadowHabitRejected("holdout is not independent original evidence")
    relevant_train = tuple(x for x in train_samples if x.cue_tags == cue_tags)
    relevant_holdout = tuple(x for x in test_samples if x.cue_tags == cue_tags)
    if len({x.session_id for x in relevant_train}) < min_train_sessions:
        return ShadowReview(ShadowStatus.INSUFFICIENT, reason="training_independence_missing")
    cheap = cheap_exact_cue_majority(train_samples, cue_tags)
    if cheap is None:
        return ShadowReview(ShadowStatus.CONFLICTING, reason="no_unique_cheap_action")
    candidate_train = tuple(x for x in relevant_train if x.action_ref == cheap)
    if (
        len({x.session_id for x in candidate_train}) < min_train_sessions
        or not all(x.goal_reached for x in candidate_train)
    ):
        return ShadowReview(ShadowStatus.CONFLICTING, cheap_candidate_ref=cheap,
                            reason="goal_success_not_repeated_consistently")
    # Existing S11 selector is used on an EPHEMERAL shadow rule, never returned
    # as an executable repertoire or persisted as an acquired Habit.
    rule = HabitRule(
        habit_id="l3-shadow-not-admitted", candidate_ref=cheap, priority=0,
        cue_requirements=(CueFeature("source_cue_tags", "/".join(cue_tags)),),
        provenance=Provenance("l3-shadow-unqualified", "non-production"),
    )
    temporary = HabitRepertoire(
        "l3-shadow-only", 0, (rule,),
        Provenance("l3-shadow-unqualified", "ephemeral"),
    )
    selection = select_habit(temporary, HabitCue(
        "l3-shadow-cue", (CueFeature("source_cue_tags", "/".join(cue_tags)),),
        Provenance("l3-synthetic-observation", "no-world-grant"),
    ))
    if (
        selection.status is not HabitSelectionStatus.SELECTED
        or selection.selected_candidate_ref != cheap
    ):
        raise ShadowHabitRejected("existing S11 and exact-cue baseline disagree")
    independent_holdout = tuple(
        x for x in relevant_holdout if x.action_ref == cheap
    )
    if len({x.session_id for x in independent_holdout}) < min_holdout_sessions:
        return ShadowReview(
            ShadowStatus.INSUFFICIENT, cheap_candidate_ref=cheap,
            train_sessions=len({x.session_id for x in candidate_train}),
            reason="no_independent_holdout_for_executed_action",
        )
    if not all(x.goal_reached for x in independent_holdout):
        return ShadowReview(
            ShadowStatus.SHIFT_DETECTED, cheap_candidate_ref=cheap,
            train_sessions=len({x.session_id for x in candidate_train}),
            holdout_sessions=len({x.session_id for x in independent_holdout}),
            reason="heldout_goal_failure_no_habit",
        )
    return ShadowReview(
        ShadowStatus.CHEAP_NULL_EQUAL, candidate_ref=cheap,
        cheap_candidate_ref=cheap,
        train_sessions=len({x.session_id for x in candidate_train}),
        holdout_sessions=len({x.session_id for x in independent_holdout}),
        selection_matches=True,
        reason="shadow_matches_same_information_cheap_rule_no_promotion",
    )
