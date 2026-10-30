"""Bounded read-only L0/L1/L2 projection of existing SelfWorld / SelfBody.

No native reads, clock calls, action issuance, learning writes or new truth owner.
A view is already owner-local; this module only selects typed evidence for a
single decision epoch. Missing and unqualified information remains UNKNOWN.
"""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

from relay_self.prediction import PredictionStatus
from relay_self.provenance import Provenance
from relay_self.self_body import BodyOrigin, SelfBodyView
from relay_self.self_world import SelfWorldView, WorldOrigin


class InvalidCognitiveView(ValueError):
    """A cross-owner, malformed or unqualified read request."""


class CognitionTier(str, Enum):
    L0 = "L0"
    L1 = "L1"
    L2 = "L2"


@dataclass(frozen=True, slots=True)
class CognitiveFact:
    """Scalar evidence retaining epistemic type AND original provenance."""

    key: str
    origin: WorldOrigin | BodyOrigin
    value: bool | int | float | str
    source_refs: tuple[str, ...]
    provenances: tuple[Provenance, ...]


@dataclass(frozen=True, slots=True)
class CognitiveView:
    self_id: str
    session_id: str
    epoch_id: str
    tier: CognitionTier
    world_status: str
    body_status: str
    world_source_ref: str | None
    body_source_ref: str | None
    world_facts: tuple[CognitiveFact, ...]
    body_facts: tuple[CognitiveFact, ...]
    coverage_truncated: bool | None
    world_omitted: int
    body_omitted: int
    information_options: tuple[str, ...]
    # Number of facts exposed, NOT measured latency/tokens or physical energy.
    emitted_facts: int
    # Native Present has no authoritative World revision field at this stage.
    world_revision: None = None


def project_cognitive_view(
    world: SelfWorldView,
    *,
    tier: CognitionTier,
    max_world_facts: int = 8,
    max_body_facts: int = 8,
    expected_epoch_id: str | None = None,
    minimum_native_seq: int = 0,
    focus_entity_ref: str | None = None,
    inspected_at_ns: int | None = None,
    max_age_ns: int | None = None,
) -> CognitiveView:
    """Choose bounded, source-typed facts from ONE already composed view.

    FRESHNESS: without a caller-qualified clock, observations are explicitly
    UNVERIFIED_FRESHNESS, not assumed fresh. With a clock, missing timestamps
    are STALE_OR_UNDATED and their observations cannot be exposed.
    The caller must qualify source/clock and World revision externally.
    """
    if not isinstance(world, SelfWorldView) or not isinstance(tier, CognitionTier):
        raise InvalidCognitiveView("typed SelfWorld and cognition tier required")
    if expected_epoch_id is not None and world.epoch_id != expected_epoch_id:
        raise InvalidCognitiveView("stale or foreign cognition epoch")
    if focus_entity_ref is not None and (
        not isinstance(focus_entity_ref, str) or not focus_entity_ref
    ):
        raise InvalidCognitiveView("focus must be a nonempty entity ref")
    if type(minimum_native_seq) is not int or minimum_native_seq < 0:
        raise InvalidCognitiveView("invalid native sequence lower bound")
    if (inspected_at_ns is None) != (max_age_ns is None):
        raise InvalidCognitiveView("clock and freshness bound must be supplied together")
    if inspected_at_ns is not None and (
        type(inspected_at_ns) is not int or inspected_at_ns < 0
        or type(max_age_ns) is not int or max_age_ns <= 0
    ):
        raise InvalidCognitiveView("invalid freshness bound")
    for count in (max_world_facts, max_body_facts):
        if type(count) is not int or not 0 <= count <= 32:
            raise InvalidCognitiveView("fact budgets must be 0..32")
    # L0 is intrinsically small, even if its caller asks for more.
    ceiling = {CognitionTier.L0: 4, CognitionTier.L1: 16, CognitionTier.L2: 32}[tier]
    world_limit = min(ceiling, max_world_facts)
    body_limit = min(ceiling, max_body_facts)
    obs = world.observation
    body: SelfBodyView | None = world.self_body
    body_obs = body.observation if body is not None else None
    if body is not None and (
        body.self_id != world.self_id or body.session_id != world.session_id
        or body.epoch_id != world.epoch_id
    ):
        raise InvalidCognitiveView("foreign SelfBody identity, session or epoch")
    if obs is not None and (
        obs.observer_id != world.self_id or obs.session_id != world.session_id
        or obs.provenance.source != "mineflayer"
        or obs.provenance.reference != f"{obs.session_id}:{obs.native_seq}"
    ):
        raise InvalidCognitiveView("world Present has invalid source lineage")
    if body_obs is not None and (
        body_obs.session_id != world.session_id
        or body_obs.source_provenance.source != "mineflayer"
        or body_obs.source_provenance.reference
        != f"{body_obs.session_id}:{body_obs.native_seq}"
    ):
        raise InvalidCognitiveView("body Present has invalid source lineage")
    if obs is not None and body_obs is not None and (
        obs.native_seq != body_obs.native_seq
        or obs.request_id != body_obs.request_id
        or obs.provenance != body_obs.source_provenance
    ):
        raise InvalidCognitiveView("World/Body observation source mismatch")

    def source_status(native_seq: int | None, observed_at: int | None) -> str:
        if native_seq is None:
            return "UNKNOWN"
        if native_seq < minimum_native_seq:
            return "STALE"
        if inspected_at_ns is None:
            return "UNVERIFIED_FRESHNESS"
        if observed_at is None or not (
            observed_at <= inspected_at_ns <= observed_at + max_age_ns
        ):
            return "STALE_OR_UNDATED"
        return "OBSERVED_WITHIN_BOUND"

    world_status = source_status(
        obs.native_seq if obs is not None else None,
        obs.observed_at_ns if obs is not None else None,
    )
    body_status = source_status(
        body_obs.native_seq if body_obs is not None else None,
        obs.observed_at_ns if obs is not None and body_obs is not None else None,
    )
    valid = {"UNVERIFIED_FRESHNESS", "OBSERVED_WITHIN_BOUND"}
    world_facts: list[CognitiveFact] = []
    body_facts: list[CognitiveFact] = []
    if obs is not None and world_status in valid:
        ordered = sorted(obs.entities, key=lambda item: (
            0 if item.entity_ref == focus_entity_ref else 1,
            item.distance_m if item.distance_m is not None else float("inf"),
            item.entity_ref,
        ))
        for item in ordered:
            world_facts.append(CognitiveFact(
                "world.entity_ref", WorldOrigin.OBSERVED, item.entity_ref,
                (obs.source_ref,), (obs.provenance,),
            ))
            if item.distance_m is not None:
                world_facts.append(CognitiveFact(
                    f"world.{item.entity_ref}.distance_m", WorldOrigin.OBSERVED,
                    item.distance_m, (obs.source_ref,), (obs.provenance,),
                ))
            if tier is not CognitionTier.L0:
                if item.label is not None:
                    world_facts.append(CognitiveFact(
                        f"world.{item.entity_ref}.label", WorldOrigin.OBSERVED,
                        item.label, (obs.source_ref,), (obs.provenance,),
                    ))
            if tier is CognitionTier.L2:
                if item.visible_action is not None:
                    world_facts.append(CognitiveFact(
                        f"world.{item.entity_ref}.visible_action", WorldOrigin.OBSERVED,
                        item.visible_action, (obs.source_ref,), (obs.provenance,),
                    ))
                if item.position is not None:
                    for axis, value in zip("xyz", item.position, strict=True):
                        world_facts.append(CognitiveFact(
                            f"world.{item.entity_ref}.position_{axis}",
                            WorldOrigin.OBSERVED, value, (obs.source_ref,),
                            (obs.provenance,),
                        ))
        if tier is not CognitionTier.L0:
            for memory in world.memories:
                world_facts.append(CognitiveFact(
                    "world.memory_id", WorldOrigin.REMEMBERED, memory.memory_id,
                    (f"memory:{memory.memory_id}",),
                    (memory.source_provenance, memory.integration_provenance),
                ))
        if tier is CognitionTier.L2:
            scenarios = {item.scenario_id: item for item in world.scenarios}
            for forecast in world.forecasts:
                scenario = scenarios.get(forecast.scenario_id)
                result = forecast.prediction
                # A PRD scenario may be hypothetical but not bound to Present.
                # Do not present unbound forecasts as current-world evidence.
                if (scenario is None
                    or obs.source_ref not in scenario.state.source_refs
                    or f"target:{scenario.target_ref}" not in scenario.state.source_refs
                    or result.status is not PredictionStatus.PREDICTED
                    or result.predicted_state is None):
                    continue
                for variable in result.predicted_state.variables:
                    if variable.value is not None:
                        world_facts.append(CognitiveFact(
                            f"world.predicted.{forecast.scenario_id}.{variable.key}",
                            WorldOrigin.PREDICTED, variable.value,
                            (obs.source_ref, f"scenario:{forecast.scenario_id}",
                             f"rule:{result.rule.rule_id}"),
                            (obs.provenance, scenario.state.provenance,
                             result.rule.provenance),
                        ))
    if body_obs is not None and body_status in valid:
        keys = {"position_x", "position_y", "position_z", "health"}
        for field in body_obs.fields:
            if tier is CognitionTier.L0 and field.key not in keys:
                continue
            body_facts.append(CognitiveFact(
                f"body.{field.key}", BodyOrigin.OBSERVATION, field.value,
                (body_obs.source_ref,), (body_obs.source_provenance,),
            ))
        if tier is not CognitionTier.L0:
            for item in body.interoceptions:
                body_facts.append(CognitiveFact(
                    f"body.sensed.{item.field.key}", BodyOrigin.INTEROCEPTION,
                    item.field.value,
                    (body_obs.source_ref,
                     f"body-sensor:{item.session_id}:{item.native_seq}:"
                     f"{item.owner_tick}:{item.request_id}"),
                    (item.native_provenance, item.owner_provenance),
                ))
            if tier is CognitionTier.L2:
                for hypothesis in body.hypotheses:
                    for variable in hypothesis.state.variables:
                        if variable.value is not None:
                            body_facts.append(CognitiveFact(
                                f"body.hypothetical.{hypothesis.hypothesis_id}."
                                f"{variable.key}", BodyOrigin.HYPOTHESIS,
                                variable.value,
                                (f"hypothesis:{hypothesis.hypothesis_id}",),
                                (hypothesis.state.provenance,),
                            ))
                for prediction in body.predictions:
                    result = prediction.result
                    if (result.status is PredictionStatus.PREDICTED
                            and result.predicted_state is not None):
                        for variable in result.predicted_state.variables:
                            if variable.value is not None:
                                body_facts.append(CognitiveFact(
                                    f"body.predicted.{prediction.hypothesis_id}."
                                    f"{variable.key}", BodyOrigin.PREDICTION,
                                    variable.value,
                                    (f"hypothesis:{prediction.hypothesis_id}",
                                     f"rule:{result.rule.rule_id}"),
                                    (result.source_state.provenance,
                                     result.rule.provenance),
                                ))
    selected_world = tuple(world_facts[:world_limit])
    selected_body = tuple(body_facts[:body_limit])
    options: list[str] = []
    if world_status not in valid:
        options.append("REQUEST_FRESH_WORLD_OBSERVATION")
    elif obs is not None:
        if obs.entities:
            options.append("INSPECT_OBSERVED_ENTITIES")
        if tier is not CognitionTier.L0 and world.memories:
            options.append("REVIEW_OWN_RETAINED_MEMORY")
        if tier is CognitionTier.L2 and any(
            fact.origin is WorldOrigin.PREDICTED for fact in selected_world
        ):
            options.append("COMPARE_CONDITIONAL_WORLD_PREDICTION")
    if body_status not in valid:
        options.append("BODY_STATE_UNKNOWN")
    elif selected_body and tier is not CognitionTier.L0:
        options.append("CONSIDER_OBSERVED_BODY_CONSTRAINTS")
        if any(fact.origin is BodyOrigin.PREDICTION for fact in selected_body):
            options.append("COMPARE_CONDITIONAL_BODY_PREDICTION")
    return CognitiveView(
        world.self_id, world.session_id, world.epoch_id, tier,
        world_status, body_status,
        obs.source_ref if obs is not None else None,
        body_obs.source_ref if body_obs is not None else None,
        selected_world, selected_body,
        obs.coverage_truncated if obs is not None else None,
        len(world_facts) - len(selected_world),
        len(body_facts) - len(selected_body),
        tuple(options), len(selected_world) + len(selected_body),
    )
