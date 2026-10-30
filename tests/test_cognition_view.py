"""Offline #632/#633 cognitive-resolution tests; no World/LLM/Action execution."""
from __future__ import annotations

import json
from dataclasses import FrozenInstanceError, replace

import pytest

from adapters.mineflayer.present_projection import MinecraftEntityPresent, MinecraftPresent
from adapters.mineflayer.self_body_projection import project_body_present
from adapters.mineflayer.self_world_projection import project_self_world_present
from relay_self.cognition_view import (
    CognitionTier,
    InvalidCognitiveView,
    bind_body_prediction_review_to_request,
    bind_cognitive_view_to_request,
    project_cognitive_view,
)
from relay_self.persistent_cognition import IdentitySpecification, Memory, PersistentCognition
from relay_self.prediction import PredictionState, StateVariable, TransitionRule, predict_transition
from relay_self.provenance import Provenance
from relay_self.relay_engine import (
    BoundedChoice,
    BoundedChoiceRequest,
    CognitionDatum,
    ProviderDecision,
    RelayEngine,
)
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
    body_x: float = 1.0,
):
    entities = (
        (MinecraftEntityPresent(42, "zombie", 3.0, (4.0, 64.0, 2.0)),)
        if with_entity else ()
    )
    present = MinecraftPresent(
        session_id=session, seq=seq, request_id=f"probe-{seq}",
        body_position=(body_x, 64.0, 2.0), health=10.0, food=6.0,
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


def test_l1_l2_bridge_to_existing_relay_engine_changes_context_not_actions():
    request = BoundedChoiceRequest(
        request_id="r1", instruction="compare available information",
        intent_id=None, focus=None,
        choices=(BoundedChoice("INSPECT", "observe source"),
                 BoundedChoice("DEFER", "recheck later")), context=(),
    )
    with_memory = fixture(
        with_memory=True, with_world_forecast=True, with_body_forecast=True,
    )
    cheap = bind_cognitive_view_to_request(
        with_memory, request, tier=CognitionTier.L0, expected_epoch_id="epoch-8",
    )
    learned = bind_cognitive_view_to_request(
        with_memory, request, tier=CognitionTier.L1,
    )
    deliberative = bind_cognitive_view_to_request(
        with_memory, request, tier=CognitionTier.L2,
        max_world_facts=32, max_body_facts=32,
    )
    assert cheap.choices == learned.choices == deliberative.choices == request.choices
    assert cheap.instruction == learned.instruction == deliberative.instruction
    assert request.context == ()
    assert [item.key for item in learned.context] == [
        "self_cognitive_source", "self_cognitive_world", "self_cognitive_body",
    ]
    cheap_world = json.loads(cheap.context[1].value_json)
    learned_world = json.loads(learned.context[1].value_json)
    deep_world = json.loads(deliberative.context[1].value_json)
    assert not any(f["origin"] == "remembered" for f in cheap_world)
    assert any(f["origin"] == "remembered" for f in learned_world)
    assert any(f["origin"] == "predicted" for f in deep_world)
    assert any(f["source_provenance"] for f in deep_world)
    deep_body = json.loads(deliberative.context[2].value_json)
    assert any(f["origin"] == "hypothesis" for f in deep_body)
    meta = json.loads(deliberative.context[0].value_json)
    assert meta["world_revision"] is None
    assert "information_options_not_actions" in meta
    assert not hasattr(deliberative, "issue_action")


def test_relay_engine_bridge_rejects_context_spoof_and_stale_epoch():
    view = fixture()
    base = BoundedChoiceRequest(
        request_id="r", instruction="source view", intent_id=None, focus=None,
        choices=(BoundedChoice("A", "option A"),
                 BoundedChoice("B", "option B")), context=(),
    )
    fake = replace(base, context=(
        CognitionDatum.from_value(
            "self_cognitive_world", [{"origin": "observed", "value": "safe"}],
            provenance("forged"),
        ),
    ))
    with pytest.raises(InvalidCognitiveView, match="reserved"):
        bind_cognitive_view_to_request(view, fake, tier=CognitionTier.L1)
    with pytest.raises(InvalidCognitiveView, match="epoch"):
        bind_cognitive_view_to_request(
            view, base, tier=CognitionTier.L1, expected_epoch_id="epoch-9",
        )


def _paired_body_world_prediction(*, predicted_x: int, seq_gap: int = 1):
    """One fixed pair of World observations, alter *only* Self's PRD belief."""
    prior = fixture(seq=8, body_x=1.0)
    later = fixture(seq=8 + seq_gap, body_x=3.0)
    source = prior.self_body.observation
    state = PredictionState(
        "body-step", (StateVariable("position_x", 1),),
        provenance("hypothesis"),
        source_refs=(source.source_ref, "body-field:position_x"),
        source_provenance=(source.source_provenance,),
    )
    hypothesis = BodyHypothesis("step", state)
    prediction = BodyPrediction("step", predict_transition(
        state, TransitionRule(
            "step-rule", (StateVariable("position_x", 1),),
            (StateVariable("position_x", predicted_x),),
            provenance("conditional-rule"),
        ),
    ))
    body = compose_self_body_view(
        self_id="A", session_id="session-A", epoch_id="epoch-8",
        observation=source,
        hypotheses=(hypothesis,), predictions=(prediction,),
    )
    return replace(prior, self_body=body), later


def test_body_review_reaches_l1_l2_and_changes_stub_decision_not_actions():
    """Same real observation, different fallible PRD -> different choices."""
    request = BoundedChoiceRequest(
        request_id="r", instruction="choose epistemic follow-up",
        intent_id=None, focus=None,
        choices=(BoundedChoice("COMPARE", "compare body evidence"),
                 BoundedChoice("REASSESS", "reassess body model")),
        context=(), think_allowed=False,
    )
    before_match, now_match = _paired_body_world_prediction(predicted_x=3)
    before_bad, now_bad = _paired_body_world_prediction(predicted_x=2)
    assert now_match == now_bad
    match = bind_body_prediction_review_to_request(
        before_match, now_match, request, tier=CognitionTier.L1,
        hypothesis_id="step", field_key="position_x", max_native_seq_gap=2,
    )
    mismatch = bind_body_prediction_review_to_request(
        before_bad, now_bad, request, tier=CognitionTier.L2,
        hypothesis_id="step", field_key="position_x", max_native_seq_gap=2,
    )
    assert match.choices == mismatch.choices == request.choices
    assert match.instruction == mismatch.instruction == request.instruction
    assert request.context == ()
    a = json.loads(match.context[-1].value_json)
    b = json.loads(mismatch.context[-1].value_json)
    assert a["status"] == "match"
    assert b["status"] == "mismatch"
    assert b["epistemic_candidate_not_action"] == "REASSESS_BODY_MODEL"
    assert a["epistemic_candidate_not_action"] == "COMPARE_MODEL_WITH_OBSERVATION"
    assert a["action_success"] is b["action_success"] is None
    assert not a["learning_committed"] and not b["resource_credited"]
    assert a["later_source_ref"] == b["later_source_ref"]
    assert a["observation_source_provenance"] == b["observation_source_provenance"]

    def offline_fixture_provider(request, *, mode):
        context = {d.key: json.loads(d.value_json) for d in request.context}
        # Deliberately simple deterministic comparator, NOT an online L1 learner.
        review = context["self_cognitive_body_review"]
        choice = "REASSESS" if review["status"] == "mismatch" else "COMPARE"
        return ProviderDecision.resolved(choice, reason="offline fixture only")

    engine = RelayEngine(offline_fixture_provider)
    first, second = engine(match), engine(mismatch)
    assert first.choice_id == "COMPARE" and second.choice_id == "REASSESS"
    assert first.provider_call_count == second.provider_call_count == 1
    assert not hasattr(engine, "issue_action")


def test_body_review_request_refuses_foreign_stale_or_spoofed_context():
    before, after = _paired_body_world_prediction(predicted_x=3)
    req = BoundedChoiceRequest(
        request_id="r", instruction="epistemic compare",
        intent_id=None, focus=None,
        choices=(BoundedChoice("COMPARE", "compare"),
                 BoundedChoice("REASSESS", "reassess")), context=(),
    )
    kwargs = dict(
        tier=CognitionTier.L1, hypothesis_id="step",
        field_key="position_x", max_native_seq_gap=2,
    )
    forged = replace(req, context=(CognitionDatum.from_value(
        "self_cognitive_body_review", {"status": "match"},
        provenance("forged"),
    ),))
    with pytest.raises(InvalidCognitiveView, match="reserved"):
        bind_body_prediction_review_to_request(before, after, forged, **kwargs)
    for invalid in (
        replace(after, self_id="B"),
        replace(after, session_id="other"),
        replace(after, epoch_id=before.epoch_id),
        replace(after, self_body=replace(after.self_body, epoch_id="old")),
        replace(after, observation=replace(after.observation, native_seq=8)),
    ):
        with pytest.raises(InvalidCognitiveView):
            bind_body_prediction_review_to_request(before, invalid, req, **kwargs)
    with pytest.raises(InvalidCognitiveView, match="L1/L2"):
        bind_body_prediction_review_to_request(
            before, after, req, **(kwargs | {"tier": CognitionTier.L0}),
        )
    with pytest.raises(InvalidCognitiveView, match="stale or undated"):
        bind_body_prediction_review_to_request(
            before, after, req,
            **(kwargs | {"inspected_at_ns": 400, "max_age_ns": 10}),
        )


def test_body_review_missing_world_or_excess_gap_produces_no_fake_success():
    before, after = _paired_body_world_prediction(predicted_x=3, seq_gap=5)
    req = BoundedChoiceRequest(
        request_id="r", instruction="compare body state",
        intent_id=None, focus=None,
        choices=(BoundedChoice("COMPARE", "compare"),
                 BoundedChoice("REASSESS", "reassess")), context=(),
    )
    kwargs = dict(
        tier=CognitionTier.L1, hypothesis_id="step",
        field_key="position_x", max_native_seq_gap=2,
    )
    projected = bind_body_prediction_review_to_request(
        before, after, req, **kwargs,
    )
    review = json.loads(projected.context[-1].value_json)
    assert review["status"] == "undetermined"
    assert review["epistemic_candidate_not_action"] == (
        "REQUEST_ADDITIONAL_BODY_EVIDENCE"
    )
    assert review["action_success"] is None
    for view in (
        replace(before, observation=None),
        replace(before, self_body=None),
    ):
        with pytest.raises(InvalidCognitiveView, match="matching Present"):
            bind_body_prediction_review_to_request(view, after, req, **kwargs)
