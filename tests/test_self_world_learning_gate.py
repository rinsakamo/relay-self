"""Stage M governed learning ON/OFF/sham controls, all SYNTHETIC S17.

This never turns Stage L's physical source-only DEV receipts into
ActionLifecycle or LRN authority. Real S17/10 adaptation is NOT attested.
"""
from __future__ import annotations

import json
from dataclasses import replace

import pytest

import test_action_feedback_qualification as s17
from adapters.mineflayer.self_world_learning_gate import evaluate_governed_stage_m
from relay_self.action_feedback import LearningFeedbackInterpretationStatus
from relay_self.epoch_continuation import read_retained_preference
from relay_self.learning import (
    FeedbackDirection,
    InvalidLearningAuthority,
    MissingLearningAuthority,
)
from relay_self.prediction import StateVariable, predict_transition
from relay_self.provenance import Provenance
from relay_self.relay_engine import (
    BoundedChoice,
    BoundedChoiceRequest,
    DecisionStatus,
    ProviderDecision,
    RelayEngine,
)
from relay_self.self_world import (
    InvalidSelfWorldData,
    WorldForecast,
    WorldPredictionReviewStatus,
    compose_self_world_view,
)
from test_self_world import synthetic_s17_world_review_chain


def _context():
    _, prior, current, action, outcome, consequence = (
        synthetic_s17_world_review_chain()
    )
    original = current.observation
    assert original is not None
    next_obs = replace(
        original, native_seq=original.native_seq + 1,
        request_id="synthetic-followup-5",
        provenance=Provenance("mineflayer", f"{original.session_id}:{original.native_seq+1}"),
    )
    next_view = compose_self_world_view(
        self_id=current.self_id, session_id=current.session_id,
        epoch_id="synthetic-third-epoch",
        observation=next_obs,
    )
    request = BoundedChoiceRequest(
        request_id="stage-m-control", instruction="Read one bounded cognitive choice",
        intent_id="synthetic-survive", focus="entity-42",
        choices=(
            BoundedChoice("WAIT", "No further model-side check"),
            BoundedChoice("RECHECK", "Check the observation again"),
        ),
        context=(),
    )
    consumed = []

    def deterministic_fake_provider(req, *, mode):
        values = {d.key: json.loads(d.value_json) for d in req.context}
        retained = values["self_world_retained_preference"]
        consumed.append((
            req.request_id, retained["value"], retained["revision"],
            retained["committed_feedback_ref"],
            values["self_world_observer"]["source_ref"],
        ))
        selected = "RECHECK" if retained["value"] >= 4 else "WAIT"
        return ProviderDecision(DecisionStatus.RESOLVED, selected, "synthetic policy")

    args = dict(
        prior=prior, current=current, next_view=next_view, action=action,
        outcome=outcome, consequence=consequence,
        criterion=s17.feedback_criterion(direction=FeedbackDirection.INCREASE),
        owner=s17.learning_state(), rule=s17.learning_rule(),
        authority=s17.learning_authority(),
        engine=RelayEngine(deterministic_fake_provider), request=request,
        provenance=Provenance("stage-m-synthetic-operator", "explicit-test"),
        scenario_id="source-bound-future", variable_key="entity_label",
        max_native_seq_gap=10,
    )
    return args, consumed


@pytest.mark.parametrize(
    ("feedback_on", "learning_on", "sham", "expect_commit"),
    (
        (True, True, False, True),
        (True, False, False, False),
        (False, True, False, False),
        (False, False, False, False),
        (True, True, True, False),
    ),
)
def test_stage_m_sham_and_knockout_identical_next_native_input(
    feedback_on, learning_on, sham, expect_commit,
):
    args, consumed = _context()
    if sham:
        args["criterion"] = s17.feedback_criterion(action_ref="NOT-MOVE_BACKWARD")
    outcome = evaluate_governed_stage_m(
        **args, feedback_on=feedback_on, learning_on=learning_on,
    )
    assert outcome.review.status is WorldPredictionReviewStatus.MISMATCH
    assert outcome.before_choice.choice_id == "WAIT"
    assert outcome.next_choice.choice_id == ("RECHECK" if expect_commit else "WAIT")
    assert outcome.original_owner.value == 3
    assert outcome.original_owner.revision == 0
    assert outcome.next_owner.value == (4 if expect_commit else 3)
    assert outcome.next_owner.revision == int(expect_commit)
    assert outcome.update_committed is expect_commit
    assert outcome.physical_actions_issued == 0
    assert consumed[0][4] == consumed[1][4]
    assert consumed[0][0] != consumed[1][0]
    assert consumed[0][1:3] == (3, 0)
    assert consumed[1][1:3] == (
        4 if expect_commit else 3, int(expect_commit),
    )
    assert consumed[0][3] is None
    assert (consumed[1][3] is not None) is expect_commit
    assert outcome.feedback is None if not feedback_on else True
    if feedback_on:
        assert outcome.feedback.status is (
            LearningFeedbackInterpretationStatus.NOT_APPLICABLE if sham
            else LearningFeedbackInterpretationStatus.PRODUCED
        )
    # Actual S17 criterion direction is NOT derived from the prediction error.
    assert args["criterion"].feedback_direction is FeedbackDirection.INCREASE


@pytest.mark.parametrize("mode", ("missing", "denied", "wrong_owner"))
def test_stage_m_no_s10_update_without_valid_independent_authority(mode):
    args, consumed = _context()
    if mode == "missing":
        args["authority"] = None
    elif mode == "denied":
        args["authority"] = s17.learning_authority(granted=False)
    else:
        args["authority"] = s17.learning_authority(target_id="alien_weight")
    with pytest.raises((MissingLearningAuthority, InvalidLearningAuthority, ValueError)):
        evaluate_governed_stage_m(
            **args, feedback_on=True, learning_on=True,
        )
    assert consumed == []
    assert args["owner"].revision == 0
    assert args["owner"].value == 3


@pytest.mark.parametrize("kind", (
    "stale_seq", "foreign_session", "foreign_self", "same_epoch",
    "counterfeit_lifecycle", "counterfeit_outcome", "wrong_target",
))
def test_stage_m_cannot_invent_next_world_or_s17_lineage(kind):
    args, consumed = _context()
    current = args["current"]
    future = args["next_view"]
    if kind == "stale_seq":
        args["next_view"] = replace(
            future, observation=replace(
                future.observation, native_seq=current.observation.native_seq,
            ),
        )
    elif kind == "foreign_session":
        args["next_view"] = replace(future, session_id="other-session")
    elif kind == "foreign_self":
        args["next_view"] = replace(future, self_id="B")
    elif kind == "same_epoch":
        args["next_view"] = replace(future, epoch_id=current.epoch_id)
    elif kind == "counterfeit_lifecycle":
        args["action"] = None
    elif kind == "counterfeit_outcome":
        args["outcome"] = None
    else:
        args["criterion"] = s17.feedback_criterion(target_id="foreign-owner-target")
    with pytest.raises((InvalidSelfWorldData, ValueError, TypeError)):
        evaluate_governed_stage_m(
            **args, feedback_on=True, learning_on=True,
        )
    assert consumed == []


def test_stage_m_matching_prediction_cannot_trigger_error_based_s17():
    args, consumed = _context()
    prior = args["prior"]
    forecast = prior.forecasts[0]
    prediction = predict_transition(
        prior.scenarios[0].state,
        replace(
            forecast.prediction.rule,
            assignments=(StateVariable("entity_label", "zombie"),),
        ),
    )
    args["prior"] = replace(
        prior, forecasts=(WorldForecast(forecast.scenario_id, prediction),),
    )
    outcome = evaluate_governed_stage_m(
        **args, feedback_on=True, learning_on=True,
    )
    assert outcome.review.status is WorldPredictionReviewStatus.MATCH
    assert outcome.feedback is None
    assert outcome.update_committed is False
    assert outcome.next_choice.choice_id == "WAIT"
    assert outcome.next_owner is args["owner"]


def test_stage_m_readback_rejects_reconstructed_owner_and_feedback_bypass():
    args, _ = _context()
    result = evaluate_governed_stage_m(
        **args, feedback_on=True, learning_on=True,
    )
    with pytest.raises(ValueError):
        read_retained_preference(
            result.next_owner, result.original_owner,
            required_target_id="risk_weight", expected_revision=1,
            provenance=Provenance("stage-m-synthetic", "stale"),
        )
    assert result.next_owner.last_update is not None
    assert result.next_owner.last_update.authority_id == (
        args["authority"].authority_id
    )
