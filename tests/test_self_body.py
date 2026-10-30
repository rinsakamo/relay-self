"""#632 offline negative controls; never launches World, Node or an action issuer."""
from __future__ import annotations

import inspect
from dataclasses import FrozenInstanceError, replace

import pytest

from adapters.mineflayer.execution import WorldConsequence, WorldConsequenceStatus
from adapters.mineflayer.present_projection import MinecraftPresent
from adapters.mineflayer.self_body_projection import (
    project_body_action_readback,
    project_body_present,
)
from relay_self.action_outcome import (
    ActionOutcomeDisposition,
    ActionOutcomeInterpretation,
)
from relay_self.belief import (
    BeliefCriterion,
    BeliefEvidence,
    EvidenceRelation,
    PropositionKey,
    assess_belief,
)
from relay_self.prediction import PredictionState, StateVariable, TransitionRule, predict_transition
from relay_self.provenance import Provenance
from relay_self.reactive_l0 import ReactiveL0
from relay_self.self_body import (
    BodyField,
    BodyHypothesis,
    BodyObservation,
    BodyOrigin,
    BodyPrediction,
    BodyPredictionReviewStatus,
    InvalidSelfBodyData,
    compose_self_body_view,
    review_self_body_prediction,
)


def prov(ref: str, source: str = "offline") -> Provenance:
    return Provenance(source=source, reference=ref)


def present(seq: int = 8, session: str = "S") -> MinecraftPresent:
    return MinecraftPresent(
        session_id=session, seq=seq, request_id=f"probe-{seq}",
        body_position=(2.0, 64.0, 3.0), health=18.0,
        food=12.0, food_saturation=4.0, inventory=(),
        observed_entities=(), coverage_scope="offline",
        coverage_radius_m=16.0, coverage_cap=16,
        coverage_candidates=0, coverage_truncated=False,
        provenance=prov(f"{session}:{seq}", "mineflayer"),
    )


def observation(seq: int = 8, session: str = "S") -> BodyObservation:
    return project_body_present(present(seq, session))


def counterfactual():
    state = PredictionState(
        state_id="body:wings", provenance=prov("hypothesis:wings"),
        variables=(StateVariable("wings", True), StateVariable("can_fly", True),
                   StateVariable("position_x", 2)),
    )
    hypothesis = BodyHypothesis("wings", state)
    prediction = BodyPrediction("wings", predict_transition(
        state, TransitionRule("fly-forward",
                              (StateVariable("can_fly", True),),
                              (StateVariable("position_x", 100),), prov("rule:flight")),
    ))
    return hypothesis, prediction


def outcome(disposition: ActionOutcomeDisposition) -> ActionOutcomeInterpretation:
    return ActionOutcomeInterpretation(
        action_id="move1", binding_id="bind1", action_ref="MOVE_BACKWARD",
        skill_execution_id="skill1", intent_id="intent1", session_id="S",
        source_status="undetermined" if disposition is not ActionOutcomeDisposition.OUTCOME else "executed",
        disposition=disposition,
        reason_code="world_consequence_undetermined" if disposition is ActionOutcomeDisposition.UNAVAILABLE else
                    "adapter_failure_consequence_unknown" if disposition is ActionOutcomeDisposition.UNKNOWN else "observed_execution",
        world_provenance=prov("world-consequence"), provenance=prov("S16"),
    )


def test_phantom_wings_can_be_predicted_but_never_mint_physical_flight():
    h, p = counterfactual()
    view = compose_self_body_view(session_id="S", epoch_id="e1", observation=observation(),
                                  hypotheses=(h,), predictions=(p,))
    assert view.hypothetical("wings", "can_fly").value is True
    assert view.predicted("wings", "position_x").value == 100
    assert view.predicted("wings", "position_x").origin is BodyOrigin.PREDICTION
    assert view.observed("can_fly").origin is BodyOrigin.UNKNOWN
    assert not hasattr(view, "authorize_action")
    assert not hasattr(view, "issue_action")
    with pytest.raises(FrozenInstanceError):
        view.session_id = "rewrite-world"


def test_native_readback_takes_precedence_over_any_move_prediction():
    h, p = counterfactual()
    view = compose_self_body_view(session_id="S", epoch_id="e1", observation=observation(),
                                  hypotheses=(h,), predictions=(p,))
    assert view.observed("position_x").value == 2.0
    assert view.predicted("wings", "position_x").value == 100
    assert view.observed("position_x").origin is BodyOrigin.OBSERVATION
    assert view.observed("position_x").source_refs == ("native-probe:S:8:probe-8",)


def test_unknown_or_unavailable_outcome_cannot_update_physical_body():
    for state in (ActionOutcomeDisposition.UNKNOWN, ActionOutcomeDisposition.UNAVAILABLE):
        view = compose_self_body_view(session_id="S", epoch_id="e", outcome=outcome(state))
        assert view.observed("position_x").origin is BodyOrigin.UNKNOWN
        assert view.outcome is not None and view.outcome.disposition is state
        with pytest.raises(InvalidSelfBodyData, match="without S16 outcome|unqualified"):
            compose_self_body_view(
                session_id="S", epoch_id="e", outcome=outcome(state),
                observation=replace(observation(), action_id="move1",
                                    consequence_provenance=prov("world-consequence")),
            )


def test_action_readback_rejects_ack_failure_and_unknown():
    failure = WorldConsequence(
        action_id="move1", binding_id="bind1", action_ref="MOVE_BACKWARD",
        status=WorldConsequenceStatus.FAILED, session_id="S",
        before_observation=None, dispatch_receipt=None, cleanup_receipt=None,
        after_observation=None, movement_distance=None,
        cleanup_attempted=False, error="network failure",
        provenance=prov("world-consequence"),
    )
    with pytest.raises(InvalidSelfBodyData, match="exact executed"):
        project_body_action_readback(failure, outcome(ActionOutcomeDisposition.UNKNOWN))


def test_source_freshness_duplicate_and_cross_session_rejected():
    with pytest.raises(InvalidSelfBodyData, match="foreign-session"):
        compose_self_body_view(session_id="S", epoch_id="e", observation=observation(session="T"))
    with pytest.raises(InvalidSelfBodyData, match="stale"):
        compose_self_body_view(session_id="S", epoch_id="e", observation=observation(), minimum_native_seq=9)
    with pytest.raises(InvalidSelfBodyData, match="duplicate"):
        compose_self_body_view(session_id="S", epoch_id="e", observation=observation(),
                               seen_observation_refs=(observation().source_ref,))
    with pytest.raises(InvalidSelfBodyData, match="duplicate"):
        compose_self_body_view(session_id="S", epoch_id="e", observation=observation(),
                               seen_observation_refs=("same", "same"))


def test_adapter_rejects_source_reference_alias_or_forgery():
    reading = present()
    with pytest.raises(InvalidSelfBodyData, match="session and native seq"):
        project_body_present(replace(reading, provenance=prov("T:8", "mineflayer")))
    with pytest.raises(InvalidSelfBodyData, match="mineflayer Present provenance"):
        project_body_present(replace(reading, provenance=prov("S:8", "invented")))

def test_belief_keeps_fallibility_and_provenance_not_physical_truth():
    proposition = PropositionKey("body", "self", "can_fly")
    assessment = assess_belief((BeliefEvidence(
        "belief-e1", proposition, EvidenceRelation.SUPPORT, prov("belief-source"),
    ),), BeliefCriterion("belief-test", proposition))
    view = compose_self_body_view(session_id="S", epoch_id="e", beliefs=(assessment,))
    assert view.beliefs_about("can_fly") == (assessment,)
    assert view.observed("can_fly").origin is BodyOrigin.UNKNOWN
    invalid = assess_belief((), BeliefCriterion("wrong-domain", PropositionKey("world", "self", "safe")))
    with pytest.raises(InvalidSelfBodyData, match="non-self-body"):
        compose_self_body_view(session_id="S", epoch_id="e", beliefs=(invalid,))


def test_hypothesis_prediction_sources_must_match_exactly():
    h, p = counterfactual()
    with pytest.raises(InvalidSelfBodyData, match="not bound"):
        compose_self_body_view(session_id="S", epoch_id="e", predictions=(p,))
    with pytest.raises(InvalidSelfBodyData, match="duplicate body hypothesis"):
        compose_self_body_view(session_id="S", epoch_id="e", hypotheses=(h, h))
    other = BodyHypothesis("other", h.state)
    with pytest.raises(InvalidSelfBodyData, match="not bound"):
        compose_self_body_view(session_id="S", epoch_id="e", hypotheses=(other,), predictions=(p,))


def test_no_body_model_is_allowed_and_cannot_mint_m_or_p1_resources():
    blank = compose_self_body_view(session_id="S", epoch_id="first")
    assert blank.observed("position_x").origin is BodyOrigin.UNKNOWN
    assert blank.observed("energy").origin is BodyOrigin.UNKNOWN
    assert blank.observed("physical_fatigue").origin is BodyOrigin.UNKNOWN
    h = BodyHypothesis("fantasy-energy", PredictionState(
        "phantom", (StateVariable("energy", 99999), StateVariable("physical_fatigue", 0)),
        prov("imagined"),
    ))
    imaginary = compose_self_body_view(session_id="S", epoch_id="first", hypotheses=(h,))
    assert imaginary.hypothetical("fantasy-energy", "energy").value == 99999
    assert imaginary.observed("energy").origin is BodyOrigin.UNKNOWN
    assert imaginary.observed("physical_fatigue").origin is BodyOrigin.UNKNOWN
    # L0 remains independent: its constructor/decide API gains no SelfBody argument.
    assert "self_body" not in inspect.signature(ReactiveL0.decide).parameters


def test_no_invalid_numeric_or_mutable_body_observations():
    with pytest.raises(InvalidSelfBodyData, match="finite"):
        BodyField("position_x", float("nan"))
    with pytest.raises(InvalidSelfBodyData, match="scalar immutable"):
        BodyField("position_x", [1, 2, 3])
    with pytest.raises(InvalidSelfBodyData, match="duplicate"):
        BodyObservation("S", 1, "probe", (BodyField("x", 1), BodyField("x", 2)), prov("S:1"))
    with pytest.raises(InvalidSelfBodyData, match="consequence"):
        BodyObservation("S", 1, "probe", (BodyField("x", 1),), prov("S:1"), action_id="action")


def _body_review_pair(*, predicted_x=3, observed_x=3.0, gap=1):
    """Two separately sourced native Presents and a prior-only PRD model."""
    prior = observation(seq=8)
    state = PredictionState(
        "x-forecast", (StateVariable("position_x", 2),),
        prov("body-model"), source_refs=(
            prior.source_ref, "body-field:position_x",
        ), source_provenance=(prior.source_provenance,),
    )
    hyp = BodyHypothesis("move-estimate", state)
    forecast = BodyPrediction("move-estimate", predict_transition(
        state, TransitionRule(
            "step-x", (StateVariable("position_x", 2),),
            (StateVariable("position_x", predicted_x),), prov("PRD-rule"),
        ),
    ))
    before = compose_self_body_view(
        self_id="A", session_id="S", epoch_id="e1", observation=prior,
        hypotheses=(hyp,), predictions=(forecast,),
    )
    subsequent = observation(seq=8 + gap)
    subsequent = replace(
        subsequent,
        fields=tuple(
            BodyField(field.key, observed_x) if field.key == "position_x"
            else field for field in subsequent.fields
        ),
    )
    after = compose_self_body_view(
        self_id="A", session_id="S", epoch_id="e2",
        observation=subsequent,
    )
    return before, after


def test_body_forecast_success_and_failure_preserved_as_read_only_reviews():
    before, matched = _body_review_pair()
    review = review_self_body_prediction(
        before, matched, hypothesis_id="move-estimate",
        field_key="position_x", max_native_seq_gap=2,
    )
    assert review.status is BodyPredictionReviewStatus.MATCH
    assert review.predicted_value == 3 and review.observed_value == 3.0
    assert review.prior_observation_ref == "native-probe:S:8:probe-8"
    assert review.later_observation_ref == "native-probe:S:9:probe-9"
    assert not hasattr(review, "authorize_action")
    assert not hasattr(review, "energy_credit")
    before, failed = _body_review_pair(observed_x=1.0)
    mismatch = review_self_body_prediction(
        before, failed, hypothesis_id="move-estimate",
        field_key="position_x", max_native_seq_gap=2,
    )
    assert mismatch.status is BodyPredictionReviewStatus.MISMATCH
    assert mismatch.observed_value == 1.0
    assert failed.observed("position_x").value == 1.0
    assert before.predicted("move-estimate", "position_x").value == 3


def test_body_review_numeric_tolerance_and_unknown_result_do_not_mint_outcome():
    before, after = _body_review_pair(observed_x=3.08)
    args = dict(
        hypothesis_id="move-estimate", field_key="position_x",
        max_native_seq_gap=2,
    )
    assert review_self_body_prediction(
        before, after, **args,
    ).status is BodyPredictionReviewStatus.MISMATCH
    assert review_self_body_prediction(
        before, after, absolute_tolerance=0.1, **args,
    ).status is BodyPredictionReviewStatus.MATCH
    before, gap = _body_review_pair(gap=4)
    result = review_self_body_prediction(before, gap, **args)
    assert result.status is BodyPredictionReviewStatus.UNDETERMINED
    assert result.reason_code == "source_gap_beyond_explicit_bound"
    assert result.observed_value == 3.0  # not a verified immediate successor
    before, after = _body_review_pair()
    missing_field = replace(after, observation=replace(
        after.observation,
        fields=(BodyField("health", 18.0),),
    ))
    unknown = review_self_body_prediction(before, missing_field, **args)
    assert unknown.status is BodyPredictionReviewStatus.UNDETERMINED
    assert unknown.reason_code == "body_field_unobserved"
    assert unknown.observed_value is None
    assert missing_field.observed("position_x").origin is BodyOrigin.UNKNOWN
    assert not hasattr(unknown, "learning_feedback")


def test_body_review_rejects_cross_self_replay_forged_prediction_and_fake_s16():
    before, after = _body_review_pair()
    options = dict(
        hypothesis_id="move-estimate", field_key="position_x",
        max_native_seq_gap=2,
    )
    for invalid in (
        replace(after, self_id="B"),
        replace(after, session_id="foreign"),
        replace(after, epoch_id=before.epoch_id),
        replace(after, observation=replace(
            after.observation, native_seq=8,
            source_provenance=prov("S:8", "mineflayer"),
        )),
        replace(after, observation=replace(
            after.observation, source_provenance=prov("spoof", "mineflayer"),
        )),
        replace(after, observation=replace(
            after.observation, action_id="pretend-action",
            consequence_provenance=prov("fake-outcome"),
        )),
    ):
        with pytest.raises(InvalidSelfBodyData):
            review_self_body_prediction(before, invalid, **options)
    unbound = replace(before.hypotheses[0].state, source_refs=())
    bad_hyp = BodyHypothesis("move-estimate", unbound)
    bad_before = replace(before, hypotheses=(bad_hyp,))
    with pytest.raises(InvalidSelfBodyData, match="unbound"):
        review_self_body_prediction(bad_before, after, **options)
    bad_rule = replace(
        before.predictions[0].result,
        rule=TransitionRule(
            "other", (StateVariable("position_x", 2),),
            (StateVariable("position_x", 99),), prov("forged-rule"),
        ),
    )
    forged = replace(
        before, predictions=(BodyPrediction("move-estimate", bad_rule),),
    )
    with pytest.raises(InvalidSelfBodyData, match="counterfeit"):
        review_self_body_prediction(forged, after, **options)


def test_body_review_cannot_score_imagined_capability_or_unattested_p1():
    before, after = _body_review_pair()
    for key in ("can_fly", "energy", "physical_fatigue"):
        with pytest.raises(InvalidSelfBodyData, match="native body observable"):
            review_self_body_prediction(
                before, after, hypothesis_id="move-estimate",
                field_key=key, max_native_seq_gap=2,
            )
    for tolerance in (float("nan"), -1.0, True):
        with pytest.raises(InvalidSelfBodyData, match="absolute_tolerance"):
            review_self_body_prediction(
                before, after, hypothesis_id="move-estimate",
                field_key="position_x", max_native_seq_gap=2,
                absolute_tolerance=tolerance,
            )


def test_body_review_does_not_launder_imaginary_initial_state():
    before, after = _body_review_pair()
    prior = before.observation
    # These pointers look correct, but the asserted initial x=999 was
    # never present in native observation (x=2). Fail before scoring.
    imagined = PredictionState(
        "wrong-initial", (StateVariable("position_x", 999),),
        prov("hypothesis-phantom"),
        source_refs=(prior.source_ref, "body-field:position_x"),
        source_provenance=(prior.source_provenance,),
    )
    hypothesis = BodyHypothesis("move-estimate", imagined)
    forecast = BodyPrediction("move-estimate", predict_transition(
        imagined, TransitionRule(
            "phantom", (StateVariable("position_x", 999),),
            (StateVariable("position_x", 3),), prov("fake-physics"),
        ),
    ))
    forged = replace(before, hypotheses=(hypothesis,), predictions=(forecast,))
    with pytest.raises(InvalidSelfBodyData, match="differs from Present"):
        review_self_body_prediction(
            forged, after, hypothesis_id="move-estimate",
            field_key="position_x", max_native_seq_gap=2,
        )
