"""SelfWorld v0: ephemeral, partial and observer-local composition of existing cognition.

Neither physical World truth nor a world-model, Memory, BLF, PRD or Action owner.
No native Minecraft imports, mutable registry, communication or actuator interface.
"""
from __future__ import annotations

import math
from dataclasses import dataclass
from enum import Enum

from relay_self.belief import BeliefAssessment
from relay_self.persistent_cognition import Memory, PersistentCognition
from relay_self.prediction import PredictionResult, PredictionState, PredictionStatus
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
    value: WorldEntityObservation | Memory | bool | int | str | None
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
