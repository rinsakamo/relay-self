"""SelfWorld v0: ephemeral, partial and observer-local composition of existing cognition.

Neither physical World truth nor a world-model, Memory, BLF, PRD or Action owner.
No native Minecraft imports, mutable registry, communication or actuator interface.
"""
from __future__ import annotations

import math
from dataclasses import dataclass, replace
from enum import Enum

from relay_self.epoch_continuation import RetainedPreferenceRead, read_retained_preference
from relay_self.learning import LearningPreferenceState
from relay_self.relay_engine import (
    BoundedChoiceRequest,
    CognitionDatum,
    OpenCognitionRequest,
)
from relay_self.attention import (
    AttentionCandidate,
    AttentionCriterion,
    AttentionSelection,
    select_attention,
)
from relay_self.belief import BeliefAssessment, BeliefStatus
from relay_self.persistent_cognition import Memory, PersistentCognition
from relay_self.prediction import (
    PredictionResult,
    PredictionState,
    PredictionStatus,
    predict_transition,
)
from relay_self.provenance import Provenance
from relay_self.self_body import SelfBodyView


class InvalidSelfWorldData(ValueError):
    """Malformed, misattributed, stale or cross-owner SelfWorld input."""


class WorldOrigin(str, Enum):
    OBSERVED = "observed"
    REMEMBERED = "remembered"
    INFERRED = "inferred"
    PREDICTED = "predicted"
    HYPOTHETICAL = "hypothetical"
    UNKNOWN = "unknown"


@dataclass(frozen=True, slots=True)
class WorldEntityObservation:
    """Exterior entity facts only. Other Self's private state has no field."""

    entity_ref: str
    label: str | None
    position: tuple[float, float, float] | None
    distance_m: float | None
    visible_action: str | None = None

    def __post_init__(self) -> None:
        _token("entity_ref", self.entity_ref)
        for name in ("label", "visible_action"):
            value = getattr(self, name)
            if value is not None:
                _token(name, value)
        if self.position is not None:
            if (not isinstance(self.position, tuple) or len(self.position) != 3
                    or not all(type(x) in (int, float) and math.isfinite(x)
                               for x in self.position)):
                raise InvalidSelfWorldData("position requires finite 3D tuple")
        if self.distance_m is not None and (
            type(self.distance_m) not in (float, int)
            or not math.isfinite(self.distance_m) or self.distance_m < 0
        ):
            raise InvalidSelfWorldData("distance_m must be finite nonnegative")


@dataclass(frozen=True, slots=True)
class WorldObservation:
    """One bounded, source-linked Present. No claim that unlisted entities are absent."""

    observer_id: str
    session_id: str
    native_seq: int
    request_id: str
    entities: tuple[WorldEntityObservation, ...]
    coverage_scope: str
    coverage_radius_m: float
    coverage_cap: int
    coverage_candidates: int
    coverage_truncated: bool
    provenance: Provenance
    observed_at_ns: int | None = None

    def __post_init__(self) -> None:
        for name in ("observer_id", "session_id", "request_id", "coverage_scope"):
            _token(name, getattr(self, name))
        _seq("native_seq", self.native_seq)
        for name in ("coverage_cap", "coverage_candidates"):
            _seq(name, getattr(self, name))
        if (type(self.coverage_radius_m) not in (int, float)
                or not math.isfinite(self.coverage_radius_m)
                or self.coverage_radius_m < 0
                or self.coverage_cap <= 0):
            raise InvalidSelfWorldData("invalid bounded coverage")
        if type(self.coverage_truncated) is not bool:
            raise InvalidSelfWorldData("coverage_truncated must be bool")
        if not isinstance(self.entities, tuple) or not all(
            isinstance(x, WorldEntityObservation) for x in self.entities
        ):
            raise InvalidSelfWorldData("entities require immutable typed tuple")
        ids = tuple(x.entity_ref for x in self.entities)
        if len(set(ids)) != len(ids):
            raise InvalidSelfWorldData("duplicate observed entity")
        if (len(ids) > self.coverage_cap or
                self.coverage_candidates < len(ids) or
                (not self.coverage_truncated and self.coverage_candidates != len(ids))):
            raise InvalidSelfWorldData("inconsistent limited coverage")
        if not isinstance(self.provenance, Provenance):
            raise InvalidSelfWorldData("observation requires source provenance")
        if self.observed_at_ns is not None:
            _seq("observed_at_ns", self.observed_at_ns)

    @property
    def source_ref(self) -> str:
        return f"present:{self.session_id}:{self.native_seq}:{self.request_id}"


@dataclass(frozen=True, slots=True)
class WorldScenario:
    """An observer's counterfactual, never another Self's private World."""

    scenario_id: str
    owner_id: str
    target_ref: str
    state: PredictionState

    def __post_init__(self) -> None:
        for name in ("scenario_id", "owner_id", "target_ref"):
            _token(name, getattr(self, name))
        if not isinstance(self.state, PredictionState):
            raise InvalidSelfWorldData("scenario requires existing PRD state")


@dataclass(frozen=True, slots=True)
class WorldForecast:
    scenario_id: str
    prediction: PredictionResult

    def __post_init__(self) -> None:
        _token("scenario_id", self.scenario_id)
        if not isinstance(self.prediction, PredictionResult):
            raise InvalidSelfWorldData("forecast requires existing PRD result")


@dataclass(frozen=True, slots=True)
class WorldReading:
    origin: WorldOrigin
    value: WorldEntityObservation | Memory | BeliefAssessment | bool | int | str | None
    source_refs: tuple[str, ...]
    source_provenance: tuple[Provenance, ...]


@dataclass(frozen=True, slots=True)
class SelfWorldView:
    """Single decision-epoch view of what ONE Self can currently consult."""

    self_id: str
    session_id: str
    epoch_id: str
    observation: WorldObservation | None
    memories: tuple[Memory, ...]
    beliefs: tuple[BeliefAssessment, ...]
    scenarios: tuple[WorldScenario, ...]
    forecasts: tuple[WorldForecast, ...]
    self_body: SelfBodyView | None

    def observed_entity(self, entity_ref: str) -> WorldReading:
        _token("entity_ref", entity_ref)
        if self.observation is not None:
            for item in self.observation.entities:
                if item.entity_ref == entity_ref:
                    return WorldReading(
                        WorldOrigin.OBSERVED, item,
                        (self.observation.source_ref,), (self.observation.provenance,),
                    )
        # In particular: not observed != physically absent, safe or defeated.
        return WorldReading(WorldOrigin.UNKNOWN, None, (), ())

    def remembered(self, memory_id: str) -> WorldReading:
        _token("memory_id", memory_id)
        for item in self.memories:
            if item.memory_id == memory_id:
                return WorldReading(
                    WorldOrigin.REMEMBERED, item,
                    (f"memory:{item.memory_id}",),
                    (item.source_provenance, item.integration_provenance),
                )
        return WorldReading(WorldOrigin.UNKNOWN, None, (), ())

    def beliefs_about(self, target_ref: str, predicate: str) -> tuple[BeliefAssessment, ...]:
        _token("target_ref", target_ref)
        _token("predicate", predicate)
        return tuple(
            b for b in self.beliefs
            if b.proposition.subject == target_ref
            and b.proposition.predicate == predicate
        )

    def inferred(self, target_ref: str, predicate: str) -> WorldReading:
        """Existing BLF assessment, never measured World state."""
        matches = self.beliefs_about(target_ref, predicate)
        if len(matches) == 1:
            item = matches[0]
            if item.status in {BeliefStatus.SUPPORTED, BeliefStatus.UNSUPPORTED}:
                return WorldReading(
                    WorldOrigin.INFERRED, item,
                    tuple(f"belief-evidence:{e.evidence_id}" for e in item.evidence),
                    tuple(e.provenance for e in item.evidence),
                )
        return WorldReading(WorldOrigin.UNKNOWN, None, (), ())

    def hypothetical(self, scenario_id: str, key: str) -> WorldReading:
        _token("scenario_id", scenario_id)
        _token("key", key)
        for scenario in self.scenarios:
            if scenario.scenario_id == scenario_id:
                variable = scenario.state.variable(key)
                if variable is not None:
                    return WorldReading(
                        WorldOrigin.HYPOTHETICAL, variable.value,
                        (f"scenario:{scenario_id}",), (scenario.state.provenance,),
                    )
        return WorldReading(WorldOrigin.UNKNOWN, None, (), ())

    def predicted(self, scenario_id: str, key: str) -> WorldReading:
        _token("scenario_id", scenario_id)
        _token("key", key)
        for forecast in self.forecasts:
            if forecast.scenario_id == scenario_id:
                result = forecast.prediction
                if result.status is PredictionStatus.PREDICTED:
                    assert result.predicted_state is not None
                    variable = result.predicted_state.variable(key)
                    if variable is not None:
                        return WorldReading(
                            WorldOrigin.PREDICTED, variable.value,
                            (f"scenario:{scenario_id}", f"rule:{result.rule.rule_id}"),
                            (result.source_state.provenance, result.rule.provenance),
                        )
                break
        return WorldReading(WorldOrigin.UNKNOWN, None, (), ())



def select_self_world_attention(
    view: SelfWorldView,
    criterion: AttentionCriterion,
) -> AttentionSelection:
    """Existing ATT over actually observed exterior targets, never simulated facts.

    Target-specific Present does not certify a global census. ATT never reads
    SelfBody, private Memory, BLF claims, counterfactuals or forecast state.
    It selects a subset of already visible source refs; it cannot authorize
    a physical Action or decide whether an unseen target physically exists.
    """
    if not isinstance(view, SelfWorldView):
        raise InvalidSelfWorldData("requires a typed SelfWorldView")
    if not isinstance(criterion, AttentionCriterion):
        raise InvalidSelfWorldData("requires existing ATT criterion")
    return select_attention(_observed_attention_candidates(view), criterion)


def resolve_self_world_attention(
    view: SelfWorldView,
    selection: AttentionSelection,
) -> tuple[WorldReading, ...]:
    """Resolve ATT references ONLY against their exact current view source.

    A stolen A selection, earlier epoch result, or fabricated hypothetical
    cannot masquerade as B's own observed World. No source payload is stored
    in ATT, and missing selection matches fail closed.
    """
    if not isinstance(view, SelfWorldView) or not isinstance(
        selection, AttentionSelection
    ):
        raise InvalidSelfWorldData("requires typed SelfWorld and ATT selection")
    allowed = _observed_attention_candidates(view)
    if selection.considered_count != len(allowed):
        raise InvalidSelfWorldData("ATT source candidate count mismatch")
    by_id = {item.candidate_id: item for item in allowed}
    seen: set[str] = set()
    result: list[WorldReading] = []
    for selected in selection.selected:
        if (selected.candidate_id in seen
                or by_id.get(selected.candidate_id) != selected):
            raise InvalidSelfWorldData("foreign, stale or invented ATT source")
        seen.add(selected.candidate_id)
        reading = view.observed_entity(selected.payload_ref)
        if (reading.origin is not WorldOrigin.OBSERVED
                or view.observation is None
                or reading.source_provenance != (view.observation.provenance,)):
            raise InvalidSelfWorldData("ATT result not a current observed entity")
        result.append(reading)
    return tuple(result)


def _observed_attention_candidates(
    view: SelfWorldView,
) -> tuple[AttentionCandidate, ...]:
    observation = view.observation
    if observation is None:
        return ()
    return tuple(
        AttentionCandidate(
            candidate_id=(
                f"{view.self_id}:{view.session_id}:{view.epoch_id}:"
                f"{observation.source_ref}:{item.entity_ref}"
            ),
            payload_ref=item.entity_ref,
            provenance=observation.provenance,
            # Priority is neutral: no invented threat score or salience.
            priority=0,
            focus_keys=(
                "observed", "world-entity", item.entity_ref,
                *((f"name:{item.label}",) if item.label is not None else ()),
            ),
        )
        for item in observation.entities
    )



class WorldPredictionReviewStatus(str, Enum):
    MATCH = "match"
    MISMATCH = "mismatch"
    UNDETERMINED = "undetermined"


@dataclass(frozen=True, slots=True)
class WorldPredictionReview:
    """Read-only comparison witness. Not a reward, LRN proposal or BLF update."""

    self_id: str
    session_id: str
    prior_epoch_id: str
    later_epoch_id: str
    scenario_id: str
    target_ref: str
    variable_key: str
    status: WorldPredictionReviewStatus
    reason_code: str
    predicted_value: bool | int | str | None
    observed_value: bool | int | str | None
    prior_observation_ref: str
    later_observation_ref: str
    prediction_source_provenance: tuple[Provenance, ...]
    observation_provenance: Provenance


def review_self_world_prediction(
    before: SelfWorldView,
    after: SelfWorldView,
    *,
    scenario_id: str,
    variable_key: str,
    max_native_seq_gap: int,
) -> WorldPredictionReview:
    """Compare a bounded PRD claim to a *later positive source observation*.

    Only source-attested observables are comparable: entity_visible (True when
    the target is positively present), entity_label and visible_action. A target
    omitted by native limited coverage is UNKNOWN, never visible=False.
    The caller owns timestamp authentication and max-seq-gap qualification.
    This does not prove that a predicted Action caused the observed result.
    """
    if not isinstance(before, SelfWorldView) or not isinstance(
        after, SelfWorldView
    ):
        raise InvalidSelfWorldData("review requires two typed SelfWorld views")
    _token("scenario_id", scenario_id)
    _token("variable_key", variable_key)
    if variable_key not in {"entity_visible", "entity_label", "visible_action"}:
        raise InvalidSelfWorldData("variable is not an observable exterior field")
    if type(max_native_seq_gap) is not int or max_native_seq_gap <= 0:
        raise InvalidSelfWorldData("max_native_seq_gap must be positive integer")
    if before.self_id != after.self_id or before.session_id != after.session_id:
        raise InvalidSelfWorldData("foreign observer or session in prediction review")
    if before.epoch_id == after.epoch_id:
        raise InvalidSelfWorldData("review requires distinct decision epochs")
    prior, later = before.observation, after.observation
    if not isinstance(prior, WorldObservation) or not isinstance(
        later, WorldObservation
    ):
        raise InvalidSelfWorldData("both epochs require typed native Present")
    if (prior.observer_id != before.self_id
            or later.observer_id != after.self_id
            or prior.session_id != before.session_id
            or later.session_id != after.session_id
            or prior.provenance.source != later.provenance.source
            or prior.provenance.source != "mineflayer"
            or prior.provenance.reference != f"{prior.session_id}:{prior.native_seq}"
            or later.provenance.reference != f"{later.session_id}:{later.native_seq}"):
        raise InvalidSelfWorldData("foreign observation source lineage")
    if later.native_seq <= prior.native_seq or prior.source_ref == later.source_ref:
        raise InvalidSelfWorldData("stale or replayed successor observation")
    if (prior.observed_at_ns is not None
            and later.observed_at_ns is not None
            and later.observed_at_ns < prior.observed_at_ns):
        raise InvalidSelfWorldData("nonmonotonic observation timestamps")

    cases = tuple(x for x in before.scenarios if x.scenario_id == scenario_id)
    forecasts = tuple(x for x in before.forecasts if x.scenario_id == scenario_id)
    if len(cases) != 1 or len(forecasts) != 1:
        raise InvalidSelfWorldData("requires one explicit matching PRD forecast")
    scenario, forecast = cases[0], forecasts[0]
    result = forecast.prediction
    if (scenario.owner_id != before.self_id
            or result.source_state != scenario.state
            or result != predict_transition(scenario.state, result.rule)
            or prior.source_ref not in scenario.state.source_refs
            or f"target:{scenario.target_ref}" not in scenario.state.source_refs):
        raise InvalidSelfWorldData("unbound or counterfeit prediction source")
    if not scenario.target_ref.startswith("entity-"):
        raise InvalidSelfWorldData("prediction must target external entity ref")

    predicted = None
    if result.status is PredictionStatus.PREDICTED:
        assert result.predicted_state is not None
        variable = result.predicted_state.variable(variable_key)
        if variable is not None:
            predicted = variable.value

    observed = None
    entity = next(
        (x for x in later.entities if x.entity_ref == scenario.target_ref), None
    )
    if entity is not None:
        if variable_key == "entity_visible":
            observed = True
        elif variable_key == "entity_label":
            observed = entity.label
        else:
            observed = entity.visible_action

    gap = later.native_seq - prior.native_seq
    if gap > max_native_seq_gap:
        status = WorldPredictionReviewStatus.UNDETERMINED
        reason = "source_gap_beyond_explicit_bound"
    elif predicted is None:
        status = WorldPredictionReviewStatus.UNDETERMINED
        reason = "prediction_unavailable_or_key_missing"
    elif observed is None:
        status = WorldPredictionReviewStatus.UNDETERMINED
        reason = "target_or_property_unobserved"
    elif type(predicted) is not type(observed):
        status = WorldPredictionReviewStatus.UNDETERMINED
        reason = "incommensurate_prediction_and_observation"
    else:
        status = (
            WorldPredictionReviewStatus.MATCH
            if predicted == observed else WorldPredictionReviewStatus.MISMATCH
        )
        reason = "observed_prediction_match" if (
            status is WorldPredictionReviewStatus.MATCH
        ) else "observed_prediction_mismatch"

    return WorldPredictionReview(
        before.self_id, before.session_id, before.epoch_id, after.epoch_id,
        scenario_id, scenario.target_ref, variable_key, status, reason,
        predicted, observed, prior.source_ref, later.source_ref,
        (
            scenario.state.provenance,
            result.rule.provenance,
            *(scenario.state.source_provenance),
        ),
        later.provenance,
    )



_SELF_WORLD_COGNITION_KEYS = frozenset({
    "self_world_observer",
    "self_world_observed",
    "self_world_prediction_review",
    "self_world_retained_preference",
})


def bind_self_world_to_cognition_request(
    view: SelfWorldView,
    selection: AttentionSelection,
    request: BoundedChoiceRequest | OpenCognitionRequest,
    *,
    review: WorldPredictionReview | None = None,
    retained_owner_self_id: str | None = None,
    owner_snapshot: LearningPreferenceState | None = None,
    retained_read: RetainedPreferenceRead | None = None,
) -> BoundedChoiceRequest | OpenCognitionRequest:
    """Opt-in input to existing RelayEngine BOUNDED/THINK/OPEN; no issuer.

    No route, Action authorization or model invocation is performed here.
    Current owner snapshot and observer binding must be supplied by caller;
    this projection cannot authenticate that caller's owner registry.
    """
    if not isinstance(view, SelfWorldView) or not isinstance(
        request, (BoundedChoiceRequest, OpenCognitionRequest)
    ):
        raise InvalidSelfWorldData("typed SelfWorld and existing cognition request required")
    if any(datum.key in _SELF_WORLD_COGNITION_KEYS for datum in request.context):
        raise InvalidSelfWorldData("caller attempted to overwrite SelfWorld context")
    if len({datum.key for datum in request.context}) != len(request.context):
        raise InvalidSelfWorldData("duplicate external cognition datum keys")
    selected = resolve_self_world_attention(view, selection)
    source = view.observation
    provenance = (
        source.provenance if source is not None
        else Provenance("relay_self.self_world", f"{view.self_id}:{view.epoch_id}:unknown")
    )
    items = [
        CognitionDatum.from_value(
            "self_world_observer",
            {
                "self_id": view.self_id,
                "session_id": view.session_id,
                "epoch_id": view.epoch_id,
                "status": "observed" if source is not None else "unknown",
                "source_ref": source.source_ref if source is not None else None,
                "coverage_truncated": (
                    source.coverage_truncated if source is not None else None
                ),
            }, provenance,
        ),
        CognitionDatum.from_value(
            "self_world_observed",
            [
                {
                    "entity_ref": reading.value.entity_ref,
                    "label": reading.value.label,
                    "position": reading.value.position,
                    "distance_m": reading.value.distance_m,
                    "visible_action": reading.value.visible_action,
                    "origin": reading.origin.value,
                }
                for reading in selected
            ], provenance,
        ),
    ]
    if review is not None:
        if not isinstance(review, WorldPredictionReview):
            raise InvalidSelfWorldData("prediction review must be typed")
        if (
            source is None
            or review.self_id != view.self_id
            or review.session_id != view.session_id
            or review.later_epoch_id != view.epoch_id
            or review.later_observation_ref != source.source_ref
            or review.observation_provenance != source.provenance
        ):
            raise InvalidSelfWorldData("stale, foreign or unbound prediction review")
        items.append(CognitionDatum.from_value(
            "self_world_prediction_review",
            {
                "status": review.status.value,
                "reason": review.reason_code,
                "scenario_id": review.scenario_id,
                "target_ref": review.target_ref,
                "variable_key": review.variable_key,
                "predicted_value": review.predicted_value,
                "observed_value": review.observed_value,
                "prior_source": review.prior_observation_ref,
                "later_source": review.later_observation_ref,
                # A prediction error is evidence of mismatch, not failure reward.
                "action_success": None,
            }, source.provenance,
        ))
    retain_supplied = (
        retained_owner_self_id is not None
        or owner_snapshot is not None or retained_read is not None
    )
    if retain_supplied:
        if (
            retained_owner_self_id != view.self_id
            or not isinstance(owner_snapshot, LearningPreferenceState)
            or not isinstance(retained_read, RetainedPreferenceRead)
            or retained_read.snapshot is not owner_snapshot
        ):
            raise InvalidSelfWorldData("foreign, missing or stale retained owner read")
        read = read_retained_preference(
            owner_snapshot, retained_read.snapshot,
            required_target_id=owner_snapshot.target_id,
            expected_revision=retained_read.revision,
            provenance=retained_read.read_provenance,
        )
        if (
            read.last_update is not retained_read.last_update
            or read.origin_provenance != retained_read.origin_provenance
        ):
            raise InvalidSelfWorldData("counterfeit retained read metadata")
        items.append(CognitionDatum.from_value(
            "self_world_retained_preference",
            {
                "owner_self_id": view.self_id,
                "target_id": read.snapshot.target_id,
                "revision": read.revision,
                "value": read.snapshot.value,
                "committed_feedback_ref": (
                    read.last_update.feedback_id
                    if read.last_update is not None else None
                ),
                "origin": "governed-retained-read",
            },
            (
                read.last_update.update_provenance
                if read.last_update is not None
                else read.origin_provenance
            ),
        ))
    return replace(request, context=(*request.context, *items))


def compose_self_world_view(
    *,
    self_id: str,
    session_id: str,
    epoch_id: str,
    observation: WorldObservation | None = None,
    retained: PersistentCognition | None = None,
    memory_ids: tuple[str, ...] = (),
    beliefs: tuple[BeliefAssessment, ...] = (),
    scenarios: tuple[WorldScenario, ...] = (),
    forecasts: tuple[WorldForecast, ...] = (),
    self_body: SelfBodyView | None = None,
    minimum_native_seq: int = 0,
    seen_observation_refs: tuple[str, ...] = (),
    inspected_at_ns: int | None = None,
    max_age_ns: int | None = None,
) -> SelfWorldView:
    """Read-only join; no implicit cross-Self memory sharing or belief updating.

    The caller remains responsible for authenticating Present and time sources.
    Native seq, timestamp and decision epoch never substitute for each other.
    """
    for name, value in (("self_id", self_id), ("session_id", session_id),
                        ("epoch_id", epoch_id)):
        _token(name, value)
    _seq("minimum_native_seq", minimum_native_seq)
    _tokens("seen_observation_refs", seen_observation_refs)
    _tokens("memory_ids", memory_ids)
    if (inspected_at_ns is None) != (max_age_ns is None):
        raise InvalidSelfWorldData("time check requires inspected_at_ns and max_age_ns")
    if inspected_at_ns is not None:
        _seq("inspected_at_ns", inspected_at_ns)
        _seq("max_age_ns", max_age_ns)
        if max_age_ns == 0:
            raise InvalidSelfWorldData("max_age_ns must be positive")
    if observation is not None:
        if not isinstance(observation, WorldObservation):
            raise InvalidSelfWorldData("observation requires typed Present")
        if observation.observer_id != self_id or observation.session_id != session_id:
            raise InvalidSelfWorldData("foreign observer or session")
        if observation.native_seq < minimum_native_seq:
            raise InvalidSelfWorldData("stale native observation")
        if observation.source_ref in seen_observation_refs:
            raise InvalidSelfWorldData("duplicate native observation")
        if inspected_at_ns is not None:
            t = observation.observed_at_ns
            if t is None or not (t <= inspected_at_ns <= t + max_age_ns):
                raise InvalidSelfWorldData("stale, future or undated observation")
    if retained is not None:
        if not isinstance(retained, PersistentCognition):
            raise InvalidSelfWorldData("retained must be existing PersistentCognition")
        if retained.identity.self_id != self_id:
            raise InvalidSelfWorldData("foreign Self private memory")
    if memory_ids and retained is None:
        raise InvalidSelfWorldData("memory selection requires own retained snapshot")
    owned = {m.memory_id: m for m in retained.memories} if retained is not None else {}
    if any(mid not in owned for mid in memory_ids):
        raise InvalidSelfWorldData("unknown or foreign private memory")
    if not isinstance(beliefs, tuple) or not all(
        isinstance(b, BeliefAssessment) for b in beliefs
    ):
        raise InvalidSelfWorldData("beliefs require existing BLF assessments")
    if any(b.proposition.domain not in {"world", "entity"} for b in beliefs):
        raise InvalidSelfWorldData("SelfBody/private belief is not World belief")
    for name, values, cls in (
        ("scenarios", scenarios, WorldScenario),
        ("forecasts", forecasts, WorldForecast),
    ):
        if not isinstance(values, tuple) or not all(isinstance(v, cls) for v in values):
            raise InvalidSelfWorldData(f"{name} require typed PRD inputs")
    if any(s.owner_id != self_id for s in scenarios):
        raise InvalidSelfWorldData("foreign Self counterfactual")
    ids = tuple(s.scenario_id for s in scenarios)
    if len(set(ids)) != len(ids):
        raise InvalidSelfWorldData("duplicate scenario")
    forecast_ids = tuple(f.scenario_id for f in forecasts)
    if len(set(forecast_ids)) != len(forecast_ids):
        raise InvalidSelfWorldData("duplicate forecast")
    by_scenario = {s.scenario_id: s.state for s in scenarios}
    if any(by_scenario.get(f.scenario_id) != f.prediction.source_state
           for f in forecasts):
        raise InvalidSelfWorldData("forecast must reference own exact scenario")
    if self_body is not None:
        if not isinstance(self_body, SelfBodyView):
            raise InvalidSelfWorldData("self_body requires existing SelfBodyView")
        if (self_body.self_id != self_id or
                self_body.session_id != session_id or
                self_body.epoch_id != epoch_id):
            raise InvalidSelfWorldData("SelfBody owner/session/epoch mismatch")
        if observation is not None and self_body.observation is not None:
            body = self_body.observation
            if (body.native_seq != observation.native_seq or
                    body.request_id != observation.request_id or
                    body.source_provenance != observation.provenance):
                raise InvalidSelfWorldData("SelfBody/World Present source mismatch")
    return SelfWorldView(
        self_id, session_id, epoch_id, observation,
        tuple(owned[mid] for mid in memory_ids), beliefs,
        scenarios, forecasts, self_body,
    )


def _token(name: str, value: object) -> None:
    if not isinstance(value, str) or not value or value != value.strip() or any(
        c.isspace() for c in value
    ):
        raise InvalidSelfWorldData(f"{name} must be a nonempty structured token")


def _seq(name: str, value: object) -> None:
    if type(value) is not int or value < 0:
        raise InvalidSelfWorldData(f"{name} must be a nonnegative integer")


def _tokens(name: str, values: object) -> None:
    if not isinstance(values, tuple):
        raise InvalidSelfWorldData(f"{name} must be an immutable tuple")
    for v in values:
        _token(name, v)
    if len(set(values)) != len(values):
        raise InvalidSelfWorldData(f"duplicate {name}")
