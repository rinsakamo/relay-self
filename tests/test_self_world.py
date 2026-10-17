"""#633 SelfWorld v0 synthetic/offline negative controls; no external World runs."""
from __future__ import annotations

import inspect
from dataclasses import FrozenInstanceError, replace

import pytest

from adapters.mineflayer.present_projection import MinecraftEntityPresent, MinecraftPresent
from adapters.mineflayer.self_body_projection import project_body_present
from adapters.mineflayer.self_world_projection import project_self_world_present
from relay_self.belief import (
    BeliefCriterion,
    BeliefEvidence,
    EvidenceRelation,
    PropositionKey,
    assess_belief,
)
from relay_self.persistent_cognition import IdentitySpecification, Memory, PersistentCognition
from relay_self.prediction import PredictionState, StateVariable, TransitionRule, predict_transition
from relay_self.provenance import Provenance
from relay_self.reactive_l0 import ReactiveL0
from relay_self.self_body import compose_self_body_view
from relay_self.self_world import (
    InvalidSelfWorldData,
    WorldForecast,
    WorldOrigin,
    WorldScenario,
    compose_self_world_view,
)


def prov(ref: str, source: str = "synthetic") -> Provenance:
    return Provenance(source, ref)


def present(
    *, session: str = "s-A", seq: int = 8, entity_id: int | None = 42,
    truncated: bool = False,
) -> MinecraftPresent:
    entities = () if entity_id is None else (
        MinecraftEntityPresent(entity_id, "zombie", 3.0, (4.0, 64.0, 2.0)),
    )
    return MinecraftPresent(
        session_id=session, seq=seq, request_id=f"probe-{seq}",
        body_position=(1.0, 64.0, 2.0), health=10.0, food=6.0,
        food_saturation=3.0, inventory=(), observed_entities=entities,
        coverage_scope="bounded-native-nearby", coverage_radius_m=16.0,
        coverage_cap=16, coverage_candidates=len(entities),
        coverage_truncated=truncated,
        provenance=prov(f"{session}:{seq}", "mineflayer"),
    )


def view(self_id="A", *, present_value=None, **kwargs):
    obs = None if present_value is None else project_self_world_present(
        present_value, observer_id=self_id, observed_at_ns=100,
    )
    return compose_self_world_view(
        self_id=self_id, session_id=f"s-{self_id}", epoch_id="e1",
        observation=obs, **kwargs,
    )


def owned(self_id: str, *memory_ids: str) -> PersistentCognition:
    return PersistentCognition(
        identity=IdentitySpecification(
            self_id, ("keep-private-context-local",), prov(f"identity:{self_id}"),
        ),
        memories=tuple(
            Memory(m, f"{self_id}:personal-experience:{m}", prov(f"source:{m}"),
                   prov(f"commit:{m}"))
            for m in memory_ids
        ),
    )


def scenario() -> tuple[WorldScenario, WorldForecast]:
    state = PredictionState(
        "imagine-world-without-monster",
        (StateVariable("monster_present", False), StateVariable("distance_band", "near")),
        prov("imagined"),
    )
    hyp = WorldScenario("h1", "A", "minecraft:entity:42", state)
    result = predict_transition(
        state, TransitionRule(
            "monster-away", (StateVariable("distance_band", "near"),),
            (StateVariable("distance_band", "far"),), prov("rule"),
        ),
    )
    return hyp, WorldForecast("h1", result)


def test_observed_entity_is_bounded_and_missing_is_unknown_not_safe():
    a = view(present_value=present())
    reading = a.observed_entity("minecraft:entity:42")
    assert reading.origin is WorldOrigin.OBSERVED
    assert reading.value.position == (4.0, 64.0, 2.0)
    assert reading.source_refs == ("present:s-A:8:probe-8",)
    assert a.observed_entity("minecraft:entity:99").origin is WorldOrigin.UNKNOWN
    empty = view(present_value=present(entity_id=None, truncated=False))
    assert empty.observation.coverage_candidates == 0
    assert empty.observed_entity("minecraft:entity:42").origin is WorldOrigin.UNKNOWN
    truncated = view(present_value=present(entity_id=None, truncated=True))
    assert truncated.observed_entity("minecraft:entity:42").origin is WorldOrigin.UNKNOWN
    assert truncated.observation.coverage_truncated
    assert not hasattr(a, "world_truth")
    assert not hasattr(a, "authorize_action")


def test_two_selves_same_world_are_information_asymmetric_and_have_no_shared_state():
    # One synthetic World with one monster; only Self A gets source visibility.
    a = view(present_value=present())
    b = view("B", present_value=present(session="s-B", entity_id=None))
    assert a.observed_entity("minecraft:entity:42").origin is WorldOrigin.OBSERVED
    assert b.observed_entity("minecraft:entity:42").origin is WorldOrigin.UNKNOWN
    # A's refreshed observation is immutable and does not magically update B.
    a2 = view(present_value=present(seq=9, entity_id=None))
    assert a2.observed_entity("minecraft:entity:42").origin is WorldOrigin.UNKNOWN
    assert a.observed_entity("minecraft:entity:42").origin is WorldOrigin.OBSERVED
    assert b.observed_entity("minecraft:entity:42").origin is WorldOrigin.UNKNOWN
    with pytest.raises(FrozenInstanceError):
        a.self_id = "B"


def test_other_self_external_location_is_not_private_body_or_memory():
    other_visible = replace(
        present(), observed_entities=(
            MinecraftEntityPresent(7, "B", 2.0, (3.0, 64.0, 2.0)),
        ),
    )
    a = view(present_value=other_visible)
    b_public = a.observed_entity("minecraft:entity:7").value
    assert b_public.label == "B" and b_public.position == (3.0, 64.0, 2.0)
    assert not hasattr(b_public, "memory")
    assert not hasattr(b_public, "intent")
    assert not hasattr(b_public, "energy")
    assert not hasattr(b_public, "self_body")
    b_private = owned("B", "private-b")
    with pytest.raises(InvalidSelfWorldData, match="foreign Self private memory"):
        view(retained=b_private, memory_ids=("private-b",))
    assert a.remembered("private-b").origin is WorldOrigin.UNKNOWN


def test_explicit_own_retained_memory_is_not_current_observation_or_shareable():
    a = view(retained=owned("A", "seen-monster-yesterday"), memory_ids=("seen-monster-yesterday",))
    recalled = a.remembered("seen-monster-yesterday")
    assert recalled.origin is WorldOrigin.REMEMBERED
    assert recalled.value.content.startswith("A:personal-experience")
    assert a.observed_entity("minecraft:entity:42").origin is WorldOrigin.UNKNOWN
    with pytest.raises(InvalidSelfWorldData, match="retained snapshot"):
        view(memory_ids=("seen-monster-yesterday",))
    with pytest.raises(InvalidSelfWorldData, match="unknown or foreign"):
        view(retained=owned("A"), memory_ids=("seen-monster-yesterday",))
    with pytest.raises(InvalidSelfWorldData, match="duplicate"):
        view(retained=owned("A", "m"), memory_ids=("m", "m"))


def test_existing_belief_is_inferred_never_measured_and_not_mutated():
    proposition = PropositionKey("entity", "minecraft:entity:42", "dangerous")
    b = assess_belief(
        (BeliefEvidence("ev1", proposition, EvidenceRelation.SUPPORT, prov("source")),),
        BeliefCriterion("danger-belief", proposition),
    )
    a = view(beliefs=(b,))
    assert a.inferred("minecraft:entity:42", "dangerous").origin is WorldOrigin.INFERRED
    assert a.observed_entity("minecraft:entity:42").origin is WorldOrigin.UNKNOWN
    no_evidence = assess_belief((), BeliefCriterion("undetermined", proposition))
    assert view(beliefs=(no_evidence,)).inferred(
        "minecraft:entity:42", "dangerous"
    ).origin is WorldOrigin.UNKNOWN
    wrong_domain = assess_belief(
        (), BeliefCriterion("private", PropositionKey("body", "self", "healthy")),
    )
    with pytest.raises(InvalidSelfWorldData, match="not World belief"):
        view(beliefs=(wrong_domain,))


def test_hypothetical_and_predicted_world_never_override_observation():
    hyp, forecast = scenario()
    a = view(present_value=present(), scenarios=(hyp,), forecasts=(forecast,))
    assert a.observed_entity("minecraft:entity:42").origin is WorldOrigin.OBSERVED
    assert a.hypothetical("h1", "monster_present").value is False
    assert a.hypothetical("h1", "monster_present").origin is WorldOrigin.HYPOTHETICAL
    assert a.predicted("h1", "distance_band").value == "far"
    assert a.predicted("h1", "distance_band").origin is WorldOrigin.PREDICTED
    assert a.observed_entity("minecraft:entity:42").value.label == "zombie"
    assert not hasattr(a, "commit_memory") and not hasattr(a, "execute_action")
    with pytest.raises(InvalidSelfWorldData, match="foreign Self counterfactual"):
        view(scenarios=(replace(hyp, owner_id="B"),))
    with pytest.raises(InvalidSelfWorldData, match="exact scenario"):
        view(forecasts=(forecast,))


def test_stale_foreign_duplicate_future_time_and_source_provenance_fail_closed():
    obs = project_self_world_present(present(), observer_id="A", observed_at_ns=100)
    with pytest.raises(InvalidSelfWorldData, match="foreign observer or session"):
        compose_self_world_view(self_id="B", session_id="s-A", epoch_id="e1", observation=obs)
    with pytest.raises(InvalidSelfWorldData, match="stale native"):
        view(present_value=present(), minimum_native_seq=9)
    with pytest.raises(InvalidSelfWorldData, match="duplicate native"):
        view(present_value=present(), seen_observation_refs=(obs.source_ref,))
    with pytest.raises(InvalidSelfWorldData, match="stale, future"):
        view(present_value=present(), inspected_at_ns=200, max_age_ns=10)
    with pytest.raises(InvalidSelfWorldData, match="stale, future"):
        view(present_value=present(), inspected_at_ns=99, max_age_ns=10)
    with pytest.raises(InvalidSelfWorldData, match="time check"):
        view(present_value=present(), inspected_at_ns=101)
    forged = replace(present(), provenance=prov("foreign:s", "mineflayer"))
    with pytest.raises(InvalidSelfWorldData, match="source provenance"):
        project_self_world_present(forged, observer_id="A")


def test_selfbody_requires_exact_self_id_session_epoch_and_native_source():
    present_a = present()
    world_obs = project_self_world_present(present_a, observer_id="A")
    body = compose_self_body_view(
        self_id="A", session_id="s-A", epoch_id="e1",
        observation=project_body_present(present_a),
    )
    combined = view(present_value=present_a, self_body=body)
    assert combined.self_body is body
    assert combined.observed_entity("minecraft:entity:42").origin is WorldOrigin.OBSERVED
    with pytest.raises(InvalidSelfWorldData, match="SelfBody owner"):
        view(present_value=present_a, self_body=replace(body, self_id="B"))
    with pytest.raises(InvalidSelfWorldData, match="SelfBody owner"):
        view(present_value=present_a, self_body=replace(body, epoch_id="e2"))
    with pytest.raises(InvalidSelfWorldData, match="source mismatch"):
        view(present_value=present_a, self_body=replace(
            body, observation=project_body_present(present(seq=9)),
        ))
    with pytest.raises(InvalidSelfWorldData, match="SelfBody owner"):
        view(present_value=present_a, self_body=compose_self_body_view(
            session_id="s-A", epoch_id="e1",
        ))
    assert world_obs.provenance == body.observation.source_provenance


def test_action_memory_ownership_and_initial_l0_are_unchanged():
    initial = compose_self_world_view(self_id="A", session_id="s-A", epoch_id="initial")
    assert initial.observed_entity("minecraft:entity:42").origin is WorldOrigin.UNKNOWN
    assert "self_world" not in inspect.signature(ReactiveL0.decide).parameters
    assert "self_world" not in inspect.signature(ReactiveL0.__init__).parameters
    import relay_self.self_world as module
    assert not any(name in module.__dict__ for name in (
        "ActionSupervisor", "WorldConsequence", "MineflayerCommand",
        "save_persistent_cognition",
    ))
