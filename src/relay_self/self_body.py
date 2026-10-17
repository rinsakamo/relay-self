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
from relay_self.prediction import PredictionResult, PredictionState, PredictionStatus
from relay_self.provenance import Provenance


class InvalidSelfBodyData(ValueError):
    """Unqualified, aliased, stale, or cross-origin SelfBody view input."""


class BodyOrigin(str, Enum):
    OBSERVATION = "observation"
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
) -> SelfBodyView:
    """Fail closed across session, freshness, origin, and branch boundaries.

    The upstream adapter/source qualifies native evidence. This composition
    does not authenticate an arbitrary caller or transform S16 ACK into success.
    """
    _token("session_id", session_id)
    _token("epoch_id", epoch_id)
    _seq("minimum_native_seq", minimum_native_seq)
    if not isinstance(seen_observation_refs, tuple) or not all(
        isinstance(s, str) and s for s in seen_observation_refs
    ) or len(set(seen_observation_refs)) != len(seen_observation_refs):
        raise InvalidSelfBodyData("seen source refs must be unique structured refs")
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
    return SelfBodyView(session_id, epoch_id, observation, beliefs, hypotheses, predictions, outcome)


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
