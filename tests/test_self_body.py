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
    InvalidSelfBodyData,
    compose_self_body_view,
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
