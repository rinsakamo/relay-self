"""Target-specific, read-only MinecraftPresent -> SelfWorld observation adapter.

A native entity registry is bounded visibility, NOT a World census.
This adapter does not peek at other Self memory, intentions or prediction.
"""
from __future__ import annotations

from adapters.mineflayer.execution import WorldConsequence, WorldConsequenceStatus
from adapters.mineflayer.present_projection import (
    MinecraftPresent,
    project_mineflayer_present,
)
from relay_self.action import ActionLifecycle
from relay_self.action_feedback import (
    ActionFeedbackCriterion,
    LearningFeedbackInterpretation,
    interpret_action_outcome_as_learning_feedback,
)
from relay_self.action_outcome import (
    ActionOutcomeDisposition,
    ActionOutcomeInterpretation,
)
from relay_self.provenance import Provenance
from relay_self.self_world import (
    InvalidSelfWorldData,
    SelfWorldView,
    WorldEntityObservation,
    WorldObservation,
    WorldPredictionReview,
    WorldPredictionReviewStatus,
    review_self_world_prediction,
)


def project_self_world_present(
    present: MinecraftPresent,
    *,
    observer_id: str,
    observed_at_ns: int | None = None,
) -> WorldObservation:
    """Only explicitly observed exterior facts are exposed to one Self.

    Observed time, if supplied, must be independently source-qualified by the
    caller; this projection cannot attest the physical clock or event origin.
    """
    if not isinstance(present, MinecraftPresent):
        raise InvalidSelfWorldData("requires existing MinecraftPresent")
    if (present.provenance.source != "mineflayer"
            or present.provenance.reference != f"{present.session_id}:{present.seq}"):
        raise InvalidSelfWorldData("foreign or mismatched Mineflayer source provenance")
    if present.coverage_candidates < len(present.observed_entities):
        raise InvalidSelfWorldData("incomplete entity coverage")
    entities = tuple(
        WorldEntityObservation(
            entity_ref=f"entity-{entity.entity_id}",
            label=entity.name,
            position=entity.position,
            distance_m=entity.distance_m,
        )
        for entity in present.observed_entities
    )
    return WorldObservation(
        observer_id=observer_id,
        session_id=present.session_id,
        native_seq=present.seq,
        request_id=present.request_id,
        entities=entities,
        coverage_scope=present.coverage_scope,
        coverage_radius_m=present.coverage_radius_m,
        coverage_cap=present.coverage_cap,
        coverage_candidates=present.coverage_candidates,
        coverage_truncated=present.coverage_truncated,
        provenance=present.provenance,
        observed_at_ns=observed_at_ns,
    )


def interpret_self_world_mismatch_as_s17_feedback(
    prior: SelfWorldView,
    current: SelfWorldView,
    *,
    scenario_id: str,
    variable_key: str,
    max_native_seq_gap: int,
    action: ActionLifecycle,
    outcome: ActionOutcomeInterpretation,
    consequence: WorldConsequence,
    criterion: ActionFeedbackCriterion,
    provenance: Provenance,
) -> tuple[WorldPredictionReview, LearningFeedbackInterpretation]:
    """S15/S16 source-bound, S17-owned *interpretation*, NOT an LRN commit.

    A mismatch is never itself a reward or a sufficient learning trigger.
    Explicit Action, execution consequence and S17 criterion remain required.
    In particular, the original native after-probe must actually contain the
    observed feature used in the mismatch; this bridge cannot mint it.
    """
    review = review_self_world_prediction(
        prior, current, scenario_id=scenario_id,
        variable_key=variable_key, max_native_seq_gap=max_native_seq_gap,
    )
    if review.status is not WorldPredictionReviewStatus.MISMATCH:
        raise InvalidSelfWorldData("only observed mismatch is eligible for S17 review")
    if not isinstance(action, ActionLifecycle):
        raise InvalidSelfWorldData("requires existing ActionLifecycle")
    if (not isinstance(outcome, ActionOutcomeInterpretation)
            or not isinstance(consequence, WorldConsequence)
            or not isinstance(criterion, ActionFeedbackCriterion)
            or not isinstance(provenance, Provenance)):
        raise InvalidSelfWorldData("requires typed S15/S16/S17 outcome and criterion")
    if (consequence.status is not WorldConsequenceStatus.EXECUTED
            or outcome.disposition is not ActionOutcomeDisposition.OUTCOME
            or outcome.source_status != WorldConsequenceStatus.EXECUTED.value
            or outcome.reason_code != "observed_execution"):
        raise InvalidSelfWorldData("unqualified executed Action outcome")
    if (outcome.session_id != review.session_id
            or consequence.session_id != review.session_id
            or consequence.action_id != action.action_id
            or consequence.action_id != outcome.action_id
            or consequence.binding_id != outcome.binding_id
            or consequence.action_ref != outcome.action_ref
            or consequence.provenance != outcome.world_provenance):
        raise InvalidSelfWorldData("Action/WorldConsequence lineage mismatch")

    before_native = consequence.before_observation
    after_native = consequence.after_observation
    if (before_native is None or after_native is None
            or before_native.session_id != review.session_id
            or after_native.session_id != review.session_id
            or prior.observation is None or current.observation is None
            or not (prior.observation.native_seq <= before_native.seq
                    < after_native.seq)):
        raise InvalidSelfWorldData("unqualified native before/after source order")
    native = project_self_world_present(
        project_mineflayer_present(after_native),
        observer_id=review.self_id,
        observed_at_ns=current.observation.observed_at_ns,
    )
    if native != current.observation or native.source_ref != review.later_observation_ref:
        raise InvalidSelfWorldData("SelfWorld observation not exact Action readback")
    if (f"action:{action.action_id}" not in
            next(s.state.source_refs for s in prior.scenarios
                 if s.scenario_id == scenario_id)):
        raise InvalidSelfWorldData("prediction was not bound to this Action")
    # The S17 owner still verifies the full terminal Action and criterion.
    # It may return NOT_APPLICABLE. We do not call propose/commit_learning_update.
    interpretation = interpret_action_outcome_as_learning_feedback(
        action, outcome, criterion, provenance=provenance,
    )
    return review, interpretation
