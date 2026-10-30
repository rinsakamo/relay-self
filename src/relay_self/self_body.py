"""SelfBody v0: immutable, ephemeral, read-only body-focused cognition view.

This is not a body, world, action, resource, persistence, or learning owner.
Upstream Present/S16 qualify input evidence; BLF/PRD retain their semantics.
"""
from __future__ import annotations

import math
from dataclasses import dataclass
from enum import Enum

from relay_self.action_outcome import (
    ActionOutcomeDisposition,
    ActionOutcomeInterpretation,
)
from relay_self.belief import BeliefAssessment
from relay_self.prediction import (
    PredictionResult,
    PredictionState,
    PredictionStatus,
    predict_transition,
)
from relay_self.provenance import Provenance


class InvalidSelfBodyData(ValueError):
    """Unqualified, aliased, stale, or cross-origin SelfBody view input."""


class BodyOrigin(str, Enum):
    OBSERVATION = "observation"
    INTEROCEPTION = "interoception"
    BELIEF = "belief"
    HYPOTHESIS = "hypothesis"
    PREDICTION = "prediction"
    UNKNOWN = "unknown"


BodyValue = bool | int | float | str


@dataclass(frozen=True, slots=True)
class BodyField:
    key: str
    value: BodyValue

    def __post_init__(self) -> None:
        _token("body field key", self.key)
        if type(self.value) not in (bool, int, float, str):
            raise InvalidSelfBodyData("body field must be a scalar immutable value")
        if type(self.value) is float and not math.isfinite(self.value):
            raise InvalidSelfBodyData("body numeric field must be finite")
        if type(self.value) is str and not self.value:
            raise InvalidSelfBodyData("body string field must be nonempty")


@dataclass(frozen=True, slots=True)
class BodyObservation:
    """Typed, source-addressed Present projection; NOT authoritative World state."""

    session_id: str
    native_seq: int
    request_id: str
    fields: tuple[BodyField, ...]
    source_provenance: Provenance
    action_id: str | None = None
    consequence_provenance: Provenance | None = None

    def __post_init__(self) -> None:
        _token("session_id", self.session_id)
        _token("request_id", self.request_id)
        _seq("native_seq", self.native_seq)
        _fields("observation fields", self.fields)
        if not isinstance(self.source_provenance, Provenance):
            raise InvalidSelfBodyData("source_provenance must be Provenance")
        if self.action_id is not None:
            _token("action_id", self.action_id)
            if not isinstance(self.consequence_provenance, Provenance):
                raise InvalidSelfBodyData("action-correlated observation requires consequence provenance")
        elif self.consequence_provenance is not None:
            raise InvalidSelfBodyData("consequence cannot be attached without action")

    @property
    def source_ref(self) -> str:
        return f"native-probe:{self.session_id}:{self.native_seq}:{self.request_id}"


@dataclass(frozen=True, slots=True)
class BodyHypothesis:
    """Caller-owned temporary scenario; its PredictionState is not Present."""

    hypothesis_id: str
    state: PredictionState

    def __post_init__(self) -> None:
        _token("hypothesis_id", self.hypothesis_id)
        if not isinstance(self.state, PredictionState):
            raise InvalidSelfBodyData("hypothesis state must be existing PredictionState")


@dataclass(frozen=True, slots=True)
class BodyPrediction:
    """Existing PRD result bound to exactly one temporary body scenario."""

    hypothesis_id: str
    result: PredictionResult

    def __post_init__(self) -> None:
        _token("hypothesis_id", self.hypothesis_id)
        if not isinstance(self.result, PredictionResult):
            raise InvalidSelfBodyData("prediction must be existing PredictionResult")


@dataclass(frozen=True, slots=True)
class BodyInteroception:
    """Owner-local sensor reading joined to native Present, not World truth."""

    field: BodyField
    session_id: str
    native_seq: int
    request_id: str
    native_provenance: Provenance
    owner_tick: int
    owner_provenance: Provenance

    def __post_init__(self) -> None:
        if not isinstance(self.field, BodyField):
            raise InvalidSelfBodyData("typed sensor field required")
        _token("sensor session_id", self.session_id)
        _token("sensor request_id", self.request_id)
        _seq("sensor native_seq", self.native_seq)
        _seq("sensor owner_tick", self.owner_tick)
        if not isinstance(self.native_provenance, Provenance) or not isinstance(
            self.owner_provenance, Provenance
        ):
            raise InvalidSelfBodyData("sensor requires independent native/owner provenance")


@dataclass(frozen=True, slots=True)
class BodyReading:
    key: str
    origin: BodyOrigin
    value: BodyValue | None
    source_refs: tuple[str, ...]
    provenance: tuple[Provenance, ...]


@dataclass(frozen=True, slots=True)
class SelfBodyView:
    """One-epoch composition, never an Action-grant or reusable state store."""

    session_id: str
    epoch_id: str
    observation: BodyObservation | None
    beliefs: tuple[BeliefAssessment, ...]
    hypotheses: tuple[BodyHypothesis, ...]
    predictions: tuple[BodyPrediction, ...]
    outcome: ActionOutcomeInterpretation | None
    self_id: str | None = None  # Optional legacy; required for SelfWorld join.
    interoceptions: tuple[BodyInteroception, ...] = ()

    def sensed(self, key: str) -> BodyReading:
        """Sensor values never become Minecraft OBSERVATION or true M0 energy."""
        _token("sensor key", key)
        for item in self.interoceptions:
            if item.field.key == key:
                assert self.observation is not None
                return BodyReading(
                    key, BodyOrigin.INTEROCEPTION, item.field.value,
                    (
                        self.observation.source_ref,
                        f"body-sensor:{item.session_id}:{item.native_seq}:"
                        f"{item.owner_tick}:{item.request_id}",
                    ),
                    (item.native_provenance, item.owner_provenance),
                )
        return BodyReading(key, BodyOrigin.UNKNOWN, None, (), ())

    def observed(self, key: str) -> BodyReading:
        """Only admitted native Present may populate OBSERVATION (never PRD)."""
        _token("body key", key)
        if self.observation is not None:
            for item in self.observation.fields:
                if item.key == key:
                    sources = (self.observation.source_provenance,)
                    if self.observation.consequence_provenance is not None:
                        sources += (self.observation.consequence_provenance,)
                    return BodyReading(
                        key, BodyOrigin.OBSERVATION, item.value,
                        (self.observation.source_ref,), sources,
                    )
        return BodyReading(key, BodyOrigin.UNKNOWN, None, (), ())

    def hypothetical(self, hypothesis_id: str, key: str) -> BodyReading:
        """Counterfactual values never become native measurements."""
        _token("hypothesis_id", hypothesis_id)
        _token("body key", key)
        for item in self.hypotheses:
            if item.hypothesis_id == hypothesis_id:
                variable = item.state.variable(key)
                if variable is not None:
                    return BodyReading(
                        key, BodyOrigin.HYPOTHESIS, variable.value,
                        (f"hypothesis:{hypothesis_id}",), (item.state.provenance,),
                    )
        return BodyReading(key, BodyOrigin.UNKNOWN, None, (), ())

    def predicted(self, hypothesis_id: str, key: str) -> BodyReading:
        _token("hypothesis_id", hypothesis_id)
        _token("body key", key)
        for item in self.predictions:
            if item.hypothesis_id == hypothesis_id:
                if item.result.status is PredictionStatus.PREDICTED:
                    assert item.result.predicted_state is not None
                    variable = item.result.predicted_state.variable(key)
                    if variable is not None:
                        return BodyReading(
                            key, BodyOrigin.PREDICTION, variable.value,
                            (f"hypothesis:{hypothesis_id}",
                             f"rule:{item.result.rule.rule_id}"),
                            (item.result.source_state.provenance,
                             item.result.rule.provenance),
                        )
                break
        return BodyReading(key, BodyOrigin.UNKNOWN, None, (), ())

    def beliefs_about(self, predicate: str) -> tuple[BeliefAssessment, ...]:
        """Keep existing fallible BLF assessments, not bool World facts."""
        _token("body predicate", predicate)
        return tuple(b for b in self.beliefs if b.proposition.predicate == predicate)


def compose_self_body_view(
    *,
    session_id: str,
    epoch_id: str,
    observation: BodyObservation | None = None,
    beliefs: tuple[BeliefAssessment, ...] = (),
    hypotheses: tuple[BodyHypothesis, ...] = (),
    predictions: tuple[BodyPrediction, ...] = (),
    outcome: ActionOutcomeInterpretation | None = None,
    minimum_native_seq: int = 0,
    seen_observation_refs: tuple[str, ...] = (),
    self_id: str | None = None,
    interoceptions: tuple[BodyInteroception, ...] = (),
) -> SelfBodyView:
    """Fail closed across session, freshness, origin, and branch boundaries.

    The upstream adapter/source qualifies native evidence. This composition
    does not authenticate an arbitrary caller or transform S16 ACK into success.
    """
    _token("session_id", session_id)
    _token("epoch_id", epoch_id)
    if self_id is not None:
        _token("self_id", self_id)
    _seq("minimum_native_seq", minimum_native_seq)
    if not isinstance(seen_observation_refs, tuple) or not all(
        isinstance(s, str) and s for s in seen_observation_refs
    ) or len(set(seen_observation_refs)) != len(seen_observation_refs):
        raise InvalidSelfBodyData("duplicate or malformed seen source refs")
    for name, values, cls in (
        ("beliefs", beliefs, BeliefAssessment),
        ("hypotheses", hypotheses, BodyHypothesis),
        ("predictions", predictions, BodyPrediction),
    ):
        if not isinstance(values, tuple) or not all(isinstance(x, cls) for x in values):
            raise InvalidSelfBodyData(f"{name} must be tuple of existing typed inputs")
    if observation is not None:
        if not isinstance(observation, BodyObservation):
            raise InvalidSelfBodyData("observation requires a typed Present projection")
        if observation.session_id != session_id:
            raise InvalidSelfBodyData("foreign-session body observation")
        if observation.native_seq < minimum_native_seq:
            raise InvalidSelfBodyData("stale native body observation")
        if observation.source_ref in seen_observation_refs:
            raise InvalidSelfBodyData("duplicate native body observation")

    if not isinstance(interoceptions, tuple) or not all(
        isinstance(item, BodyInteroception) for item in interoceptions
    ):
        raise InvalidSelfBodyData("interoception requires typed immutable tuple")
    if interoceptions and observation is None:
        raise InvalidSelfBodyData("sensor cannot exist without matching native Present")
    if len({item.field.key for item in interoceptions}) != len(interoceptions):
        raise InvalidSelfBodyData("duplicate sensor field")
    for item in interoceptions:
        if (
            observation is None
            or item.session_id != session_id
            or item.native_seq != observation.native_seq
            or item.request_id != observation.request_id
            or item.native_provenance != observation.source_provenance
        ):
            raise InvalidSelfBodyData("sensor does not match current native Present")
    if outcome is not None:
        if not isinstance(outcome, ActionOutcomeInterpretation) or outcome.session_id != session_id:
            raise InvalidSelfBodyData("invalid or foreign S16 Action outcome")
        # UNKNOWN, UNAVAILABLE and known rejection may be displayed as audit
        # status only, never converted into an observed body change.
        if observation is not None and observation.action_id is not None:
            if (observation.action_id != outcome.action_id
                    or observation.consequence_provenance != outcome.world_provenance
                    or outcome.disposition is not ActionOutcomeDisposition.OUTCOME
                    or outcome.reason_code != "observed_execution"):
                raise InvalidSelfBodyData("unqualified action readback lineage")
    elif observation is not None and observation.action_id is not None:
        raise InvalidSelfBodyData("action readback without S16 outcome")
    for belief in beliefs:
        if belief.proposition.domain != "body" or belief.proposition.subject != "self":
            raise InvalidSelfBodyData("non-self-body belief must not be promoted")
    ids = tuple(x.hypothesis_id for x in hypotheses)
    if len(set(ids)) != len(ids):
        raise InvalidSelfBodyData("duplicate body hypothesis id")
    prediction_ids = tuple(x.hypothesis_id for x in predictions)
    if len(set(prediction_ids)) != len(prediction_ids):
        raise InvalidSelfBodyData("duplicate body prediction id")
    by_id = {x.hypothesis_id: x.state for x in hypotheses}
    for item in predictions:
        if by_id.get(item.hypothesis_id) != item.result.source_state:
            raise InvalidSelfBodyData("PRD result not bound to matching body hypothesis")
    return SelfBodyView(
        session_id, epoch_id, observation, beliefs, hypotheses, predictions,
        outcome, self_id, interoceptions,
    )


class BodyPredictionReviewStatus(str, Enum):
    MATCH = "match"
    MISMATCH = "mismatch"
    UNDETERMINED = "undetermined"


@dataclass(frozen=True, slots=True)
class BodyPredictionReview:
    """Epistemic comparison only, never an Action outcome or resource update."""

    self_id: str
    session_id: str
    prior_epoch_id: str
    later_epoch_id: str
    hypothesis_id: str
    field_key: str
    status: BodyPredictionReviewStatus
    reason_code: str
    predicted_value: BodyValue | None
    observed_value: BodyValue | None
    prior_observation_ref: str
    later_observation_ref: str
    prediction_provenance: tuple[Provenance, ...]
    observation_provenance: Provenance


# Only fields that the current native Present adapter actually exports.
# In particular: P1 fatigue/M0 energy/can_fly are NOT native body readings.
_NATIVE_BODY_REVIEW_FIELDS = frozenset({
    "position_x", "position_y", "position_z", "health", "food",
    "food_saturation",
})


def review_self_body_prediction(
    before: SelfBodyView,
    after: SelfBodyView,
    *,
    hypothesis_id: str,
    field_key: str,
    max_native_seq_gap: int,
    absolute_tolerance: float = 0.0,
) -> BodyPredictionReview:
    """Compare existing PRD conditional value with a later *observed* body field.

    This proves only an observational match/mismatch in the supplied source
    stream; not an Action effect, validated physical law, energy credit,
    learning signal, or authenticated hardware clock. Only native Present
    scalars are comparable: unverified M0/P1 sensors remain separate.
    """
    if not isinstance(before, SelfBodyView) or not isinstance(after, SelfBodyView):
        raise InvalidSelfBodyData("requires two typed SelfBody views")
    _token("hypothesis_id", hypothesis_id)
    _token("field_key", field_key)
    if field_key not in _NATIVE_BODY_REVIEW_FIELDS:
        raise InvalidSelfBodyData("field is not an admitted native body observable")
    if type(max_native_seq_gap) is not int or max_native_seq_gap <= 0:
        raise InvalidSelfBodyData("max_native_seq_gap must be positive int")
    if (type(absolute_tolerance) not in (int, float)
            or not math.isfinite(absolute_tolerance)
            or absolute_tolerance < 0):
        raise InvalidSelfBodyData("absolute_tolerance must be finite and nonnegative")
    if (before.self_id is None or before.self_id != after.self_id
            or before.session_id != after.session_id):
        raise InvalidSelfBodyData("foreign or unscoped Self/session")
    if before.epoch_id == after.epoch_id:
        raise InvalidSelfBodyData("distinct decision epochs required")
    prior, later = before.observation, after.observation
    if not isinstance(prior, BodyObservation) or not isinstance(later, BodyObservation):
        raise InvalidSelfBodyData("both epochs require original native body Present")
    for obs in (prior, later):
        if (obs.session_id != before.session_id
                or obs.source_provenance.source != "mineflayer"
                or obs.source_provenance.reference
                != f"{obs.session_id}:{obs.native_seq}"):
            raise InvalidSelfBodyData("foreign or counterfeit native body source")
    if (later.native_seq <= prior.native_seq
            or later.source_ref == prior.source_ref):
        raise InvalidSelfBodyData("replayed or nonmonotonic successor body Present")
    # An Action readback must have its already qualified S16 lineage; ACK and
    # UNKNOWN do not qualify as an Action's physical body consequence.
    for view in (before, after):
        obs = view.observation
        if obs.action_id is not None and (
            view.outcome is None
            or view.outcome.disposition is not ActionOutcomeDisposition.OUTCOME
            or view.outcome.reason_code != "observed_execution"
            or view.outcome.action_id != obs.action_id
            or view.outcome.session_id != view.session_id
            or view.outcome.world_provenance != obs.consequence_provenance
        ):
            raise InvalidSelfBodyData("unqualified S16 Action readback")

    hypotheses = tuple(
        item for item in before.hypotheses if item.hypothesis_id == hypothesis_id
    )
    predictions = tuple(
        item for item in before.predictions if item.hypothesis_id == hypothesis_id
    )
    if len(hypotheses) != 1 or len(predictions) != 1:
        raise InvalidSelfBodyData("one exact prior hypothesis/PRD forecast required")
    hypothesis, prediction = hypotheses[0], predictions[0].result
    if (prediction.source_state != hypothesis.state
            or prediction != predict_transition(hypothesis.state, prediction.rule)
            or prior.source_ref not in hypothesis.state.source_refs
            or f"body-field:{field_key}" not in hypothesis.state.source_refs):
        raise InvalidSelfBodyData("unbound or counterfeit body prediction")

    predicted = None
    if prediction.status is PredictionStatus.PREDICTED:
        assert prediction.predicted_state is not None
        variable = prediction.predicted_state.variable(field_key)
        if variable is not None:
            predicted = variable.value
    reading = after.observed(field_key)
    observed = reading.value if reading.origin is BodyOrigin.OBSERVATION else None
    if later.native_seq - prior.native_seq > max_native_seq_gap:
        status = BodyPredictionReviewStatus.UNDETERMINED
        reason = "source_gap_beyond_explicit_bound"
    elif predicted is None:
        status = BodyPredictionReviewStatus.UNDETERMINED
        reason = "prediction_unavailable_or_key_missing"
    elif observed is None:
        status = BodyPredictionReviewStatus.UNDETERMINED
        reason = "body_field_unobserved"
    elif type(predicted) in (int, float) and type(observed) in (int, float):
        status = (
            BodyPredictionReviewStatus.MATCH
            if abs(predicted - observed) <= absolute_tolerance
            else BodyPredictionReviewStatus.MISMATCH
        )
        reason = "numeric_body_prediction_comparison"
    elif type(predicted) is not type(observed):
        status = BodyPredictionReviewStatus.UNDETERMINED
        reason = "incommensurate_body_values"
    else:
        status = (
            BodyPredictionReviewStatus.MATCH
            if predicted == observed else BodyPredictionReviewStatus.MISMATCH
        )
        reason = "typed_body_prediction_comparison"
    return BodyPredictionReview(
        before.self_id, before.session_id, before.epoch_id, after.epoch_id,
        hypothesis_id, field_key, status, reason, predicted, observed,
        prior.source_ref, later.source_ref,
        (hypothesis.state.provenance, prediction.rule.provenance,
         *hypothesis.state.source_provenance),
        later.source_provenance,
    )


def _token(name: str, value: object) -> None:
    if not isinstance(value, str) or not value or value != value.strip() or any(
        character.isspace() for character in value
    ):
        raise InvalidSelfBodyData(f"{name} must be one nonempty token")


def _seq(name: str, value: object) -> None:
    if type(value) is not int or value < 0:
        raise InvalidSelfBodyData(f"{name} must be nonnegative integer")


def _fields(name: str, fields: object) -> None:
    if not isinstance(fields, tuple) or not fields or not all(
        isinstance(field, BodyField) for field in fields
    ):
        raise InvalidSelfBodyData(f"{name} requires typed nonempty tuple")
    keys = tuple(item.key for item in fields)
    if len(set(keys)) != len(keys):
        raise InvalidSelfBodyData(f"{name} must not duplicate keys")
