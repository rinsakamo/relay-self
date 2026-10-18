"""Target-specific, read-only MinecraftPresent -> SelfWorld observation adapter.

A native entity registry is bounded visibility, NOT a World census.
This adapter does not peek at other Self memory, intentions or prediction.
"""
from __future__ import annotations

import json
from dataclasses import replace

from adapters.mineflayer.execution import WorldConsequence, WorldConsequenceStatus
from adapters.mineflayer.python_protocol import (
    MineflayerObservation,
    parse_mineflayer_line,
)
from adapters.mineflayer.self_action_evidence import verify_native_action_evidence
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
from relay_self.prediction import (
    PredictionState,
    StateVariable,
    TransitionRule,
    predict_transition,
)
from relay_self.provenance import Provenance
from relay_self.self_world import (
    InvalidSelfWorldData,
    SelfWorldView,
    WorldForecast,
    WorldScenario,
    WorldEntityObservation,
    WorldObservation,
    compose_self_world_view,
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


def review_self_world_s15_action_frames(
    evidence: dict[str, object],
    *,
    action_id: str,
    session_id: str,
    movement_m: float,
    target_entity_id: int,
    preceding_s49_probe_seq: int,
    observer_id: str = "self-demo-live-observer",
) -> WorldPredictionReview | None:
    """Review an *existing* executed S15 before/after frame pair.

    Original S49 deliberately replaces zombies between separate decisions.
    S15's already-captured before/after native frames, from ONE actual Action,
    are the only eligible source here. No new observe or Action request occurs.
    The adapter-generated request_id is explicitly an evidence-frame handle,
    NOT a claim that S15 originated a correlated request_id.
    """
    if (type(target_entity_id) is not int or target_entity_id < 0
            or type(preceding_s49_probe_seq) is not int
            or preceding_s49_probe_seq < 0
            or not isinstance(observer_id, str) or not observer_id):
        raise InvalidSelfWorldData("invalid S49 target/source attribution")
    verify_native_action_evidence(
        evidence, action_id=action_id, session_id=session_id,
        movement_m=movement_m,
    )

    observations = []
    for slot in ("before", "after"):
        raw = evidence[f"{slot}_observation"]
        if not isinstance(raw, dict) or raw.get("kind") != "probe":
            raise InvalidSelfWorldData("S15 frame must be an original native probe")
        # The saved decoded frame has source provenance, not an artificial
        # native request_id; parse its snapshot through the genuine decoder.
        packet = {
            "type": "observation", "session_id": raw["session_id"],
            "seq": raw["seq"], "kind": raw["kind"],
            "snapshot": raw["snapshot"],
        }
        if raw.get("request_id") is not None:
            packet["request_id"] = raw["request_id"]
        decoded = parse_mineflayer_line(json.dumps(packet, allow_nan=False))
        if not isinstance(decoded, MineflayerObservation):
            raise InvalidSelfWorldData("S15 frame not decoded to native observation")
        snap, coverage = decoded.snapshot, decoded.snapshot.nearby_entities_coverage
        # This token identifies a verified immutable evidence frame, never an
        # actual Mineflayer request ID from the source.
        observations.append(WorldObservation(
            observer_id=observer_id,
            session_id=decoded.session_id,
            native_seq=decoded.seq,
            request_id=f"s15-evidence-{action_id}-{slot}",
            entities=tuple(
                WorldEntityObservation(
                    entity_ref=f"entity-{e.entity_id}", label=e.name,
                    position=(e.position.x, e.position.y, e.position.z),
                    distance_m=e.distance,
                )
                for e in snap.nearby_entities
            ),
            coverage_scope=coverage.source_scope,
            coverage_radius_m=coverage.max_distance,
            coverage_cap=coverage.max_entities,
            coverage_candidates=coverage.candidate_count,
            coverage_truncated=coverage.truncated,
            provenance=decoded.provenance,
        ))
    before_obs, after_obs = observations
    if (before_obs.native_seq <= preceding_s49_probe_seq
            or after_obs.native_seq <= before_obs.native_seq):
        raise InvalidSelfWorldData("S15 frames not after admitted S49 source")
    target = next(
        (entity for entity in before_obs.entities
         if entity.entity_ref == f"entity-{target_entity_id}"),
        None,
    )
    if target is None or target.label is None:
        # No initial positively observed subject: cannot create a forecast.
        return None
    before = compose_self_world_view(
        self_id=observer_id, session_id=session_id,
        epoch_id=f"s15-{action_id}-before", observation=before_obs,
    )
    after = compose_self_world_view(
        self_id=observer_id, session_id=session_id,
        epoch_id=f"s15-{action_id}-after", observation=after_obs,
    )
    state = PredictionState(
        state_id=f"s15-label-state-{action_id}",
        variables=(StateVariable("entity_label", target.label),),
        provenance=Provenance("selfworld-s15-explicit-hypothesis", action_id),
        source_refs=(before_obs.source_ref, f"target:entity-{target_entity_id}"),
        source_provenance=(before_obs.provenance,),
    )
    rule = TransitionRule(
        rule_id="s15-label-persistence",
        preconditions=(StateVariable("entity_label", target.label),),
        assignments=(StateVariable("entity_label", target.label),),
        provenance=Provenance("selfworld-s15-rule", "fixed-label-persistence"),
    )
    scenario = WorldScenario(
        scenario_id="s15-label-persistence", owner_id=observer_id,
        target_ref=f"entity-{target_entity_id}", state=state,
    )
    before = replace(
        before,
        scenarios=(scenario,),
        forecasts=(WorldForecast(scenario.scenario_id,
                                 predict_transition(state, rule)),),
    )
    return review_self_world_prediction(
        before, after, scenario_id=scenario.scenario_id,
        variable_key="entity_label", max_native_seq_gap=64,
    )
