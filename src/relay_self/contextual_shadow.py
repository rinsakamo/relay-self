"""L Lane L5: bounded two-feature contextual learning SHADOW (no Action rights).

Uses original L1 observed Memory and L3 externally goal-admitted labels.
The original L3 validator owns source-memory qualification. This module
derives a non-executable proposal and compares exact-cue, one-feature and
global same-information cheap controls. Synthetic training success is NOT
physical validation, causal evidence, a Habit, or a grant.
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from enum import Enum

from relay_self.habit_shadow import (
    ExternalGoalLabel,
    GoalSourceAdmission,
    ShadowHabitRejected,
    _samples,
)
from relay_self.persistent_cognition import PersistentCognition
from relay_self.provenance import Provenance

_TOKEN = re.compile(r"[A-Za-z0-9_.:/-]+\Z")
_SHA = re.compile(r"[0-9a-f]{64}\Z")


class ContextualShadowRejected(ValueError):
    """Source, policy or trial scope could not be safely established."""


class ContextualStatus(str, Enum):
    NO_GOAL_DATA = "no_goal_data"
    UNVERIFIED = "unverified_originals"
    INSUFFICIENT = "insufficient_balanced_contexts"
    AMBIGUOUS = "ambiguous_contextual_evidence"
    SHADOW_DIFFERENCE = "shadow_distinct_from_cheapest_controls"
    CHEAP_EQUIVALENT = "cheap_same_information_matches"
    NO_MEMORY_EQUAL = "unchanged_from_no_memory"


def _token(x: object) -> bool:
    return isinstance(x, str) and _TOKEN.fullmatch(x) is not None


def _tags(items: object) -> bool:
    return (
        isinstance(items, tuple)
        and bool(items)
        and items == tuple(sorted(set(items)))
        and all(_token(x) for x in items)
    )


@dataclass(frozen=True, slots=True)
class ShadowContext:
    """Current observation pointer supplied by S, not authenticated by L."""

    session_id: str
    source_revision: int
    original_probe_sha256: str
    cue_tags: tuple[str, ...]
    source_provenance: Provenance

    def __post_init__(self) -> None:
        if (
            not _token(self.session_id)
            or type(self.source_revision) is not int
            or self.source_revision < 0
            or not isinstance(self.original_probe_sha256, str)
            or _SHA.fullmatch(self.original_probe_sha256) is None
            or not _tags(self.cue_tags)
            or not isinstance(self.source_provenance, Provenance)
        ):
            raise ContextualShadowRejected("S-owned current source scope required")


@dataclass(frozen=True, slots=True)
class ShadowSpecification:
    """Predeclared *claimed* feature pair and S-provided candidate vocabulary."""

    feature_pair: tuple[str, str]
    candidate_refs: tuple[str, str]
    minimum_per_action_per_context: int = 2

    def __post_init__(self) -> None:
        if (
            not isinstance(self.feature_pair, tuple)
            or len(self.feature_pair) != 2
            or not all(_token(x) for x in self.feature_pair)
            or self.feature_pair != tuple(sorted(set(self.feature_pair)))
            or not isinstance(self.candidate_refs, tuple)
            or len(self.candidate_refs) != 2
            or not all(_token(x) for x in self.candidate_refs)
            or self.candidate_refs != tuple(sorted(set(self.candidate_refs)))
            or type(self.minimum_per_action_per_context) is not int
            or not 2 <= self.minimum_per_action_per_context <= 4
        ):
            raise ContextualShadowRejected("exactly two declared independent features/actions")


@dataclass(frozen=True, slots=True)
class ShadowAdvice:
    status: ContextualStatus
    proposed_action_ref: str | None = None
    original_no_memory_ref: str | None = None
    exact_cue_cheap_ref: str | None = None
    singleton_cheap_ref: str | None = None
    global_cheap_ref: str | None = None
    training_sessions: int = 0
    comparisons: int = 0
    memory_causal_benefit_established: bool = False
    goal_improvement_attested: bool = False
    action_authority: bool = False
    habit_grants: int = 0
    learning_updates: int = 0
    reason: str = ""


def _majority(samples: tuple, candidates: tuple[str, str], minimum: int) -> str | None:
    """Cheapest exact matched-goal success fraction; ties/low support abstain."""
    count = {a: 0 for a in candidates}
    successes = {a: 0 for a in candidates}
    for sample in samples:
        if sample.action_ref not in count:
            raise ContextualShadowRejected("source Action not from fixed S candidates")
        count[sample.action_ref] += 1
        successes[sample.action_ref] += int(sample.goal_reached)
    if any(n < minimum for n in count.values()):
        return None
    first, second = candidates
    a = successes[first] * count[second]
    b = successes[second] * count[first]
    if a == b:
        return None
    return first if a > b else second


def review_contextual_shadow(
    owner: PersistentCognition,
    *,
    training: tuple[ExternalGoalLabel, ...],
    source_admission: GoalSourceAdmission,
    current: ShadowContext,
    admitted_current_probe_sha256: frozenset[str],
    specification: ShadowSpecification,
    no_memory_action_ref: str | None,
) -> ShadowAdvice:
    """Non-authorizing advice only, not executed or stored.

    Both cheap controls and the two-feature shadow see the identical training
    source and goal labels. This is NOT a comparative physical experiment.
    """
    if not isinstance(owner, PersistentCognition):
        raise ContextualShadowRejected("existing PersistentCognition owner required")
    if not isinstance(current, ShadowContext):
        raise ContextualShadowRejected("typed current original source required")
    if not isinstance(source_admission, GoalSourceAdmission):
        raise ContextualShadowRejected("original goal evidence admission required")
    if not isinstance(specification, ShadowSpecification):
        raise ContextualShadowRejected("predeclared two-feature specification required")
    if (
        not isinstance(admitted_current_probe_sha256, frozenset)
        or any(not isinstance(x, str) or _SHA.fullmatch(x) is None
               for x in admitted_current_probe_sha256)
    ):
        raise ContextualShadowRejected("S-owned current original digest set required")
    if (
        no_memory_action_ref is not None
        and no_memory_action_ref not in specification.candidate_refs
    ):
        raise ContextualShadowRejected("no-memory policy Action outside S vocabulary")
    if not training:
        return ShadowAdvice(ContextualStatus.NO_GOAL_DATA, reason="no_prior_external_goal")
    if current.original_probe_sha256 not in admitted_current_probe_sha256:
        return ShadowAdvice(ContextualStatus.UNVERIFIED, reason="current_original_not_admitted")
    try:
        samples, unverified = _samples(owner, training, source_admission)
    except ShadowHabitRejected as exc:
        raise ContextualShadowRejected("original L1/L3 training denied") from exc
    if unverified:
        return ShadowAdvice(ContextualStatus.UNVERIFIED, reason="prior_action_or_goal_unverified")
    if len(samples) != len(training):
        raise ContextualShadowRejected("training source and label count drift")
    sessions = [s.session_id for s in samples]
    original_action = [s.observed_sha256 for s in samples]
    original_goals = [s.goal_sha256 for s in samples]
    if (
        len(set(sessions)) != len(sessions)
        or current.session_id in sessions
        or len(set(original_action + original_goals)) != 2 * len(samples)
        or current.original_probe_sha256 in set(original_action + original_goals)
        or any(s.action_ref not in specification.candidate_refs for s in samples)
    ):
        raise ContextualShadowRejected("training/current replay or foreign Action vocabulary")
    feature_a, feature_b = specification.feature_pair
    candidates = specification.candidate_refs
    required = specification.minimum_per_action_per_context
    selected: dict[tuple[bool, bool], str] = {}
    for a in (False, True):
        for b in (False, True):
            cell = tuple(
                s for s in samples
                if (feature_a in s.cue_tags, feature_b in s.cue_tags) == (a, b)
            )
            winner = _majority(cell, candidates, required)
            if winner is None:
                return ShadowAdvice(
                    ContextualStatus.INSUFFICIENT,
                    training_sessions=len(samples),
                    reason="balanced_independent_two_feature_cell_missing_or_tied",
                )
            selected[(a, b)] = winner
    chosen_context = (feature_a in current.cue_tags, feature_b in current.cue_tags)
    proposed = selected[chosen_context]
    exact = _majority(
        tuple(s for s in samples if s.cue_tags == current.cue_tags),
        candidates, required,
    )
    global_majority = _majority(samples, candidates, required)
    singleton_votes = [
        _majority(
            tuple(s for s in samples if tag in s.cue_tags), candidates, required,
        )
        for tag in current.cue_tags
    ]
    nonempty_singletons = set(v for v in singleton_votes if v is not None)
    singleton = (
        next(iter(nonempty_singletons)) if len(nonempty_singletons) == 1 else None
    )
    same_information = (exact, singleton, global_majority)
    if proposed == no_memory_action_ref:
        status = ContextualStatus.NO_MEMORY_EQUAL
    elif proposed in same_information:
        status = ContextualStatus.CHEAP_EQUIVALENT
    else:
        status = ContextualStatus.SHADOW_DIFFERENCE
    return ShadowAdvice(
        status=status,
        proposed_action_ref=proposed,
        original_no_memory_ref=no_memory_action_ref,
        exact_cue_cheap_ref=exact,
        singleton_cheap_ref=singleton,
        global_cheap_ref=global_majority,
        training_sessions=len(set(sessions)),
        comparisons=len(singleton_votes) + 3,
        reason="two_feature_source_shaped_shadow_only_not_verified_policy_benefit",
    )
