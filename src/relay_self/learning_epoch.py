"""L Lane: source-gated Memory retention -> next-epoch L1 *shadow* decision.

This adapter does not attest native bytes, commit S10 learning, grant S11 Habit,
select an authorized S49 Action, or claim a real World policy improvement.
Source and goal admissions must come from the existing S/R/V owners.
"""
from __future__ import annotations

from dataclasses import dataclass

from relay_self.action_outcome import ActionOutcomeDisposition
from relay_self.contextual_shadow import (
    ContextualStatus,
    ShadowAdvice,
    ShadowContext,
    ShadowSpecification,
    review_contextual_shadow,
)
from relay_self.experience_bridge import QualifiedEpisode, retain_observation
from relay_self.habit_shadow import MAX_SAMPLES, ExternalGoalLabel, GoalSourceAdmission
from relay_self.persistent_cognition import PersistentCognition
from relay_self.provenance import Provenance


class LearningEpochRejected(ValueError):
    """An incoming update is outside the owner-admitted, completed source scope."""


@dataclass(frozen=True, slots=True)
class LearningEpochResult:
    """Candidate decision only; neither a physical Action nor committed Habit."""

    cognition: PersistentCognition
    advice: ShadowAdvice
    current: ShadowContext
    no_memory_action_ref: str | None
    admitted_current_probe_sha256: frozenset[str]
    candidate_action_ref: str | None
    candidate_origin: str
    retained_memory_ids: tuple[str, ...] = ()
    learning_updates: int = 0
    habit_grants: int = 0
    action_authority: bool = False
    physical_goal_improvement_attested: bool = False


def advance_learning_epoch(
    cognition: PersistentCognition,
    *,
    current_self_id: str,
    current: ShadowContext,
    admitted_current_probe_sha256: frozenset[str],
    specification: ShadowSpecification,
    no_memory_action_ref: str | None,
    previous_goal_labels: tuple[ExternalGoalLabel, ...],
    new_episodes: tuple[QualifiedEpisode, ...],
    new_goal_labels: tuple[ExternalGoalLabel, ...],
    source_admission: GoalSourceAdmission,
    integration_provenance: Provenance,
    retention_enabled: bool = True,
) -> LearningEpochResult:
    """Retain completed S-supplied experience and judge the *following* epoch.

    The caller, not L, authenticates original Action/Goal/Present bytes and
    owns admissible self/session/epoch provenance. Inputs must be assembled
    from past completed epochs, never from the current candidate's outcome.

    The immutable Memory owner is updated via the existing L1 bridge. L5
    validates both newly retained and previously retained external labels;
    failed validation raises or abstains without granting any authority.
    """
    if not isinstance(cognition, PersistentCognition):
        raise LearningEpochRejected("existing Memory owner required")
    if not isinstance(current, ShadowContext):
        raise LearningEpochRejected("typed S-owned current observation required")
    if current_self_id != cognition.identity.self_id:
        raise LearningEpochRejected("foreign self identity")
    if not isinstance(retention_enabled, bool):
        raise LearningEpochRejected("retention flag must be boolean")
    if (
        not isinstance(new_episodes, tuple)
        or not isinstance(new_goal_labels, tuple)
        or not isinstance(previous_goal_labels, tuple)
        or len(new_episodes) != len(new_goal_labels)
        or len(new_goal_labels) + len(previous_goal_labels) > MAX_SAMPLES
        or not isinstance(source_admission, GoalSourceAdmission)
        or not isinstance(integration_provenance, Provenance)
    ):
        raise LearningEpochRejected("bounded typed original and goal batches required")

    snapshot = cognition
    admitted_labels = previous_goal_labels
    retained_ids: tuple[str, ...] = ()
    if retention_enabled:
        ids: list[str] = []
        for episode, label in zip(new_episodes, new_goal_labels, strict=True):
            if not isinstance(episode, QualifiedEpisode) or not isinstance(
                label, ExternalGoalLabel
            ):
                raise LearningEpochRejected("qualified Action/OUTCOME and goal required")
            source = episode.episode
            if (
                source.disposition is not ActionOutcomeDisposition.OUTCOME
                or source.source_status != "executed"
                or source.reason_code != "observed_execution"
                or label.observed_memory_id != source.memory_id
            ):
                raise LearningEpochRejected("UNKNOWN, hypothesis or mismatched goal is not training")
            if source.session_id == current.session_id:
                raise LearningEpochRejected("same-session prospective outcome leakage")
            if source.world_revision >= current.source_revision:
                raise LearningEpochRejected("stale or future source revision for next epoch")
            if (
                source.evidence_sha256 not in source_admission.admitted_action_sha256
                or label.goal_source_sha256 not in source_admission.admitted_goal_sha256
            ):
                raise LearningEpochRejected("new original Action/Goal not S/V admitted")
            snapshot = retain_observation(
                snapshot, episode, integration_provenance=integration_provenance
            )
            ids.append(source.memory_id)
        retained_ids = tuple(ids)
        admitted_labels = (*previous_goal_labels, *new_goal_labels)

    advice = review_contextual_shadow(
        snapshot,
        training=admitted_labels if retention_enabled else (),
        source_admission=source_admission,
        current=current,
        admitted_current_probe_sha256=admitted_current_probe_sha256,
        specification=specification,
        no_memory_action_ref=no_memory_action_ref,
    )

    # Compare against the strongest cheap baselines; never call Action issuer.
    candidate = no_memory_action_ref
    origin = "s_owned_no_memory_baseline" if candidate is not None else "unknown"
    if advice.status is ContextualStatus.SHADOW_DIFFERENCE:
        candidate = advice.proposed_action_ref
        origin = "l1_experience_shadow"
    elif advice.status is ContextualStatus.CHEAP_EQUIVALENT:
        candidate = advice.proposed_action_ref
        origin = "cheap_memory_rule"
    return LearningEpochResult(
        cognition=snapshot,
        advice=advice,
        current=current,
        no_memory_action_ref=no_memory_action_ref,
        admitted_current_probe_sha256=admitted_current_probe_sha256,
        candidate_action_ref=candidate,
        candidate_origin=origin,
        retained_memory_ids=retained_ids,
    )
