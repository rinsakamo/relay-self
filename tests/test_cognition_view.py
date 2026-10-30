"""Offline #632/#633 cognitive-resolution tests; no World/LLM/Action execution."""
from __future__ import annotations

from dataclasses import FrozenInstanceError, replace

import pytest

from adapters.mineflayer.present_projection import MinecraftEntityPresent, MinecraftPresent
from adapters.mineflayer.self_body_projection import project_body_present
from adapters.mineflayer.self_world_projection import project_self_world_present
from relay_self.cognition_view import (
    CognitionTier,
    InvalidCognitiveView,
    project_cognitive_view,
)
from relay_self.persistent_cognition import IdentitySpecification, Memory, PersistentCognition
from relay_self.prediction import PredictionState, StateVariable, TransitionRule, predict_transition
from relay_self.provenance import Provenance
from relay_self.self_body import (
    BodyHypothesis,
    BodyOrigin,
    BodyPrediction,
    compose_self_body_view,
)
from relay_self.self_world import (
    InvalidSelfWorldData,
    WorldForecast,
    WorldOrigin,
    WorldPredictionReviewStatus,
    WorldScenario,
    compose_self_world_view,
    review_self_world_prediction,
)


def provenance(ref: str, source: str = "offline") -> Provenance:
    return Provenance(source, ref)


def fixture(
    *,
    self_id: str = "A",
    session: str = "session-A",
    seq: int = 8,
    with_entity: bool = True,
    with_body: bool = True,
    with_memory: bool = False,
    with_world_forecast: bool = False,
    with_body_forecast: bool = False,
    native_time: int | None = 100,
):
    entities = (
        (MinecraftEntityPresent(42, "zombie", 3.0, (4.0, 64.0, 2.0)),)
        if with_entity else ()
    )
    present = MinecraftPresent(
        session_id=session, seq=seq, request_id=f"probe-{seq}",
        body_position=(1.0, 64.0, 2.0), health=10.0, food=6.0,
        food_saturation=3.0, inventory=(), observed_entities=entities,
        coverage_scope="bounded-nearby", coverage_radius_m=16.0, coverage_cap=16,
        coverage_candidates=len(entities), coverage_truncated=False,
        provenance=provenance(f"{session}:{seq}", "mineflayer"),
    )
    observed = project_self_world_present(
        present, observer_id=self_id, observed_at_ns=native_time,
    )
    body_hypotheses, body_predictions = (), ()
    if with_body_forecast:
        state = PredictionState(
            "imagined-wings", (StateVariable("can_fly", True),),
            provenance("body-hypothesis"),
        )
        body_hypotheses = (BodyHypothesis("wings", state),)
        body_predictions = (BodyPrediction("wings", predict_transition(
            state, TransitionRule(
                "fly", (StateVariable("can_fly", True),),
                (StateVariable("can_fly", True),), provenance("flight-rule"),
            ),
        )),)
    body = compose_self_body_view(
        self_id=self_id, session_id=session, epoch_id=f"epoch-{seq}",
        observation=project_body_present(present),
        hypotheses=body_hypotheses, predictions=body_predictions,
    ) if with_body else None
    retained = None
    if with_memory:
        retained = PersistentCognition(
            IdentitySpecification(
                self_id, ("keep-private-local",), provenance("identity"),
            ),
            (Memory(
                "memory-1", "private text must not be copied into cheap view",
                provenance("experience"), provenance("memory-commit"),
            ),),
        )
    scenarios, forecasts = (), ()
    if with_world_forecast:
        state = PredictionState(
            "world-scenario",
            (StateVariable("entity_visible", True),),
            provenance("imagine"), source_refs=(
                observed.source_ref, "target:entity-42",
            ),
        )
        scenarios = (WorldScenario("case-1", self_id, "entity-42", state),)
        forecasts = (WorldForecast("case-1", predict_transition(
            state, TransitionRule(
                "disappear", (StateVariable("entity_visible", True),),
                (StateVariable("entity_visible", False),), provenance("world-rule"),
            ),
        )),)
    return compose_self_world_view(
        self_id=self_id, session_id=session, epoch_id=f"epoch-{seq}",
        observation=observed, self_body=body, retained=retained,
        memory_ids=("memory-1",) if retained else (),
        scenarios=scenarios, forecasts=forecasts,
    )


def test_minimum_and_l0_remain_bounded_without_models():
    empty = compose_self_world_view(self_id="A", session_id="S", epoch_id="e")
    frame = project_cognitive_view(empty, tier=CognitionTier.L0)
    assert frame.world_status == frame.body_status == "UNKNOWN"
    assert frame.world_facts == frame.body_facts == ()
    assert frame.information_options == (
        "REQUEST_FRESH_WORLD_OBSERVATION", "BODY_STATE_UNKNOWN",
    )
    viewed = project_cognitive_view(
        fixture(), tier=CognitionTier.L0,
        max_world_facts=32, max_body_facts=32,
    )
    assert len(viewed.world_facts) <= 4
    assert len(viewed.body_facts) <= 4
    assert all(f.origin is WorldOrigin.OBSERVED for f in viewed.world_facts)
    assert all(f.origin is BodyOrigin.OBSERVATION for f in viewed.body_facts)
    assert viewed.world_revision is None
    assert not hasattr(viewed, "authorize_action")
    assert not hasattr(viewed, "issue_action")
    with pytest.raises(FrozenInstanceError):
        viewed.epoch_id = "other-epoch"


def test_same_native_source_yields_level_specific_finite_views():
    view = fixture(with_memory=True, with_world_forecast=True, with_body_forecast=True)
    l0 = project_cognitive_view(view, tier=CognitionTier.L0)
    l1 = project_cognitive_view(view, tier=CognitionTier.L1)
    l2 = project_cognitive_view(
        view, tier=CognitionTier.L2, max_world_facts=32, max_body_facts=32,
    )
    for frame in (l0, l1, l2):
        assert frame.world_source_ref == "present:session-A:8:probe-8"
        assert frame.body_source_ref == "native-probe:session-A:8:probe-8"
        assert frame.self_id == "A" and frame.epoch_id == "epoch-8"
        assert frame.coverage_truncated is False
        assert frame.emitted_facts == len(frame.world_facts) + len(frame.body_facts)
    assert not any(f.origin is WorldOrigin.REMEMBERED for f in l0.world_facts)
    assert any(f.origin is WorldOrigin.REMEMBERED for f in l1.world_facts)
    assert any(f.origin is WorldOrigin.PREDICTED for f in l2.world_facts)
    assert any(f.origin is BodyOrigin.HYPOTHESIS for f in l2.body_facts)
    assert any(f.origin is BodyOrigin.PREDICTION for f in l2.body_facts)
    assert all(f.value != "private text must not be copied into cheap view"
               for f in l2.world_facts)
    assert "REVIEW_OWN_RETAINED_MEMORY" in l1.information_options
    assert "COMPARE_CONDITIONAL_WORLD_PREDICTION" in l2.information_options
    assert "COMPARE_CONDITIONAL_BODY_PREDICTION" in l2.information_options
    # Imagining flight cannot change the native body observation.
    assert not any(
        f.key == "body.can_fly" and f.origin is BodyOrigin.OBSERVATION
        for f in l2.body_facts
    )


def test_clock_freshness_and_native_sequence_fail_closed():
    view = fixture(native_time=100)
    fresh = project_cognitive_view(
        view, tier=CognitionTier.L1, inspected_at_ns=110, max_age_ns=20,
    )
    assert fresh.world_status == fresh.body_status == "OBSERVED_WITHIN_BOUND"
    stale = project_cognitive_view(
        view, tier=CognitionTier.L2, inspected_at_ns=500, max_age_ns=20,
    )
    assert stale.world_status == stale.body_status == "STALE_OR_UNDATED"
    assert stale.world_facts == stale.body_facts == ()
    assert "REQUEST_FRESH_WORLD_OBSERVATION" in stale.information_options
    older_seq = project_cognitive_view(
        view, tier=CognitionTier.L0, minimum_native_seq=9,
    )
    assert older_seq.world_status == older_seq.body_status == "STALE"
    assert not older_seq.world_facts
    undated = project_cognitive_view(
        fixture(native_time=None), tier=CognitionTier.L1,
        inspected_at_ns=110, max_age_ns=20,
    )
    assert undated.world_status == "STALE_OR_UNDATED"
    assert undated.world_facts == ()
    assert project_cognitive_view(
        fixture(native_time=None), tier=CognitionTier.L0,
    ).world_status == "UNVERIFIED_FRESHNESS"


def test_no_observation_does_not_mean_world_safe_or_entity_absent():
    without = fixture(with_entity=False)
    projected = project_cognitive_view(without, tier=CognitionTier.L1)
    assert projected.world_facts == ()
    assert projected.coverage_truncated is False
    assert not hasattr(projected, "safe")
    assert not hasattr(projected, "entity_absent")
    assert "INSPECT_OBSERVED_ENTITIES" not in projected.information_options


def test_other_self_private_memory_and_foreign_source_rejected():
    a = fixture(with_memory=True)
    b = fixture(self_id="B", session="session-B")
    assert not any(
        fact.origin is WorldOrigin.REMEMBERED
        for fact in project_cognitive_view(b, tier=CognitionTier.L1).world_facts
    )
    forged = replace(
        b, self_body=a.self_body,
    )
    with pytest.raises(InvalidCognitiveView, match="foreign SelfBody"):
        project_cognitive_view(forged, tier=CognitionTier.L1)
    corrupted = replace(
        a, observation=replace(
            a.observation, provenance=provenance("fake", "mineflayer"),
        ),
    )
    with pytest.raises(InvalidCognitiveView, match="source lineage"):
        project_cognitive_view(corrupted, tier=CognitionTier.L0)


def test_cross_epoch_and_invalid_budgets_rejected():
    view = fixture()
    with pytest.raises(InvalidCognitiveView, match="epoch"):
        project_cognitive_view(
            view, tier=CognitionTier.L1, expected_epoch_id="epoch-99",
        )
    for bad in (-1, 33, True):
        with pytest.raises(InvalidCognitiveView, match="budgets"):
            project_cognitive_view(view, tier=CognitionTier.L2, max_world_facts=bad)
    with pytest.raises(InvalidCognitiveView, match="freshness"):
        project_cognitive_view(view, tier=CognitionTier.L1, inspected_at_ns=100)
    zero = project_cognitive_view(
        view, tier=CognitionTier.L2, max_world_facts=0, max_body_facts=0,
    )
    assert zero.world_facts == zero.body_facts == ()
    assert zero.world_omitted > 0 and zero.body_omitted > 0


def test_prediction_mismatch_is_not_outcome_or_learning_commit():
    before = fixture(with_world_forecast=True)
    after = fixture(seq=9)
    review = review_self_world_prediction(
        before, after, scenario_id="case-1",
        variable_key="entity_visible", max_native_seq_gap=2,
    )
    assert review.status is WorldPredictionReviewStatus.MISMATCH
    next_input = project_cognitive_view(after, tier=CognitionTier.L1)
    assert all(f.origin is not WorldOrigin.PREDICTED for f in next_input.world_facts)
    assert not hasattr(next_input, "retained_update")
    assert not hasattr(next_input, "outcome_success")


def test_unbound_world_forecast_never_enters_current_world_summary():
    view = fixture(with_world_forecast=True)
    hypothetical_state = PredictionState(
        "unbound", (StateVariable("entity_visible", True),),
        provenance("unbound"),
    )
    scenario = WorldScenario("unbound-scenario", "A", "entity-42", hypothetical_state)
    forecast = WorldForecast("unbound-scenario", predict_transition(
        hypothetical_state, TransitionRule(
            "false", (StateVariable("entity_visible", True),),
            (StateVariable("entity_visible", False),), provenance("false-rule"),
        ),
    ))
    changed = replace(view, scenarios=(scenario,), forecasts=(forecast,))
    projected = project_cognitive_view(
        changed, tier=CognitionTier.L2, max_world_facts=32,
    )
    assert not any(f.origin is WorldOrigin.PREDICTED for f in projected.world_facts)


def test_existing_owner_composer_still_rejects_cross_session():
    a = fixture()
    with pytest.raises(InvalidSelfWorldData):
        compose_self_world_view(
            self_id="B", session_id="session-B", epoch_id="epoch-8",
            observation=a.observation,
        )


def test_retained_memory_without_current_present_stays_remembered():
    retained = PersistentCognition(
        IdentitySpecification("A", ("private",), provenance("identity")),
        (Memory("older", "historical path", provenance("past"),
                provenance("retained")),),
    )
    world = compose_self_world_view(
        self_id="A", session_id="S", epoch_id="now",
        retained=retained, memory_ids=("older",),
    )
    l0 = project_cognitive_view(world, tier=CognitionTier.L0)
    l1 = project_cognitive_view(world, tier=CognitionTier.L1)
    assert l0.world_facts == ()
    assert l1.world_status == "UNKNOWN" and l1.world_source_ref is None
    assert len(l1.world_facts) == 1
    assert l1.world_facts[0].origin is WorldOrigin.REMEMBERED
    assert "REVIEW_OWN_RETAINED_MEMORY" in l1.information_options
    assert "REQUEST_FRESH_WORLD_OBSERVATION" in l1.information_options
