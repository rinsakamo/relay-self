"""Target-specific, read-only MinecraftPresent -> SelfWorld observation adapter.

A native entity registry is bounded visibility, NOT a World census.
This adapter does not peek at other Self memory, intentions or prediction.
"""
from __future__ import annotations

from dataclasses import replace

from adapters.mineflayer.execution import WorldConsequence, WorldConsequenceStatus
from adapters.mineflayer.present_projection import (
    MinecraftPresent,
    project_mineflayer_present,
)
from adapters.mineflayer.python_protocol import _decode_snapshot
from adapters.mineflayer.self_action_evidence import verify_native_action_evidence
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
    WorldEntityObservation,
    WorldForecast,
    WorldObservation,
    WorldPredictionReview,
    WorldPredictionReviewStatus,
    WorldScenario,
    compose_self_world_view,
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
        # S15 preserved decoded Python frame fields, not the canonical
        # JSON protocol's id/type spelling. Normalize ONLY their field
        # names, then call the existing strict native snapshot decoder.
        snapshot = raw["snapshot"]
        snap = _decode_snapshot({
            **snapshot,
            "nearby_entities": [
                {
                    "id": entry["entity_id"], "name": entry["name"],
                    "type": entry["entity_type"], "distance": entry["distance"],
                    "position": entry["position"],
                }
                for entry in snapshot["nearby_entities"]
            ],
        })
        coverage = snap.nearby_entities_coverage
        # This token identifies a verified immutable evidence frame, never an
        # actual Mineflayer request ID from the source.
        observations.append(WorldObservation(
            observer_id=observer_id,
            session_id=raw["session_id"],
            native_seq=raw["seq"],
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
            provenance=Provenance("mineflayer", f"{session_id}:{raw['seq']}"),
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


def review_saved_s16_action_self_world(
    evidence: dict[str, object], *,
    action_id: str,
    session_id: str,
    movement_m: float,
    target_entity_id: int,
    observer_id: str = "self-demo-live-observer",
    max_native_seq_gap: int = 64,
) -> WorldPredictionReview:
    """Review two ALREADY captured S16 native before/after frames; no World IO.

    A one-step fixed entity-label hypothesis is made retrospectively, not
    proven to have been predicted prior to physical execution. No causality,
    reward, learning, or live L2 competence is inferred from MATCH/MISMATCH.
    The 's16-evidence-...' refs identify receipt fields, NOT a native
    request_id on the original Action-internal observations.
    """
    verify_native_action_evidence(
        evidence, action_id=action_id, session_id=session_id, movement_m=movement_m,
    )
    if type(target_entity_id) is not int or target_entity_id < 0:
        raise InvalidSelfWorldData("exact externally selected entity ID required")

    def native_world(frame_name: str) -> SelfWorldView:
        frame = evidence[frame_name]
        raw = frame["snapshot"]
        # Original S16 asdict uses entity_id/entity_type whereas canonical
        # protocol decoder uses id/type; do not invent any entity or fact.
        native = _decode_snapshot({
            **raw,
            "nearby_entities": [
                {
                    "id": e["entity_id"], "name": e["name"],
                    "type": e["entity_type"], "distance": e["distance"],
                    "position": e["position"],
                }
                for e in raw["nearby_entities"]
            ],
        })
        seq = frame["seq"]
        entities = tuple(
            WorldEntityObservation(
                entity_ref=f"entity-{e.entity_id}", label=e.name,
                position=(e.position.x, e.position.y, e.position.z),
                distance_m=e.distance,
            )
            for e in native.nearby_entities
        )
        coverage = native.nearby_entities_coverage
        observed = WorldObservation(
            observer_id=observer_id, session_id=session_id,
            native_seq=seq,
            request_id=f"s16-evidence-{action_id}-{frame_name}",
            entities=entities,
            coverage_scope=coverage.source_scope,
            coverage_radius_m=coverage.max_distance,
            coverage_cap=coverage.max_entities,
            coverage_candidates=coverage.candidate_count,
            coverage_truncated=coverage.truncated,
            provenance=Provenance("mineflayer", f"{session_id}:{seq}"),
        )
        return compose_self_world_view(
            self_id=observer_id, session_id=session_id,
            epoch_id=f"s16-{action_id}-{frame_name}-{seq}",
            observation=observed,
        )

    before = native_world("before_observation")
    after = native_world("after_observation")
    entity_ref = f"entity-{target_entity_id}"
    first = before.observed_entity(entity_ref).value
    if (not isinstance(first, WorldEntityObservation)
            or first.label != "zombie"):
        raise InvalidSelfWorldData("no positive S16 pre-action zombie witness")
    assert before.observation is not None
    source = before.observation
    state = PredictionState(
        f"s16-label-{action_id}",
        (StateVariable("entity_label", first.label),),
        Provenance("selfworld-s16-declared-hypothesis", source.source_ref),
        source_refs=(source.source_ref, f"target:{entity_ref}"),
        source_provenance=(source.provenance,),
    )
    rule = TransitionRule(
        "s16-fixed-label-persistence",
        (StateVariable("entity_label", first.label),),
        (StateVariable("entity_label", first.label),),
        Provenance("selfworld-s16-declared-rule", "hypothesis-not-native-law"),
    )
    scenario = WorldScenario("s16-label-persistence", observer_id, entity_ref, state)
    before = replace(
        before, scenarios=(scenario,),
        forecasts=(WorldForecast(scenario.scenario_id, predict_transition(state, rule)),),
    )
    return review_self_world_prediction(
        before, after, scenario_id=scenario.scenario_id,
        variable_key="entity_label", max_native_seq_gap=max_native_seq_gap,
    )
