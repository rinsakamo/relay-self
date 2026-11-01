"""MP11 read-only developmental candidate, fake L2 and unverified World fixtures."""
from __future__ import annotations

import json
from dataclasses import replace

import pytest

from adapters.mineflayer.self_body_mp11_retained_shadow import (
    MP11RetentionRejected,
    forecast_next_epoch,
    freeze_epoch,
    score_later,
)
from adapters.mineflayer.self_body_s50_l2_mp11_experiment import (
    EXPERIMENTS,
    L2ExperimentLoop,
    WorldTrialReceipt,
)
from relay_self.provenance import Provenance
from relay_self.relay_engine import OpenCognitionResult


def fixture_l2(req):
    allowed = json.loads(req.context[1].value_json)
    return OpenCognitionResult(
        request_id=req.request_id,
        text=json.dumps({
            "experiment_id": next(iter(allowed)),
            "model_family": "SINGLE_DECAY",
            "explanation": "A prospective applicability hypothesis is provisional.",
            "falsification_test": "Compare the frozen prediction to a later Paper outcome.",
            "predicted_wait_total_m": .02,
        }),
        provenance=Provenance("fixture.provider", "fake-mp11-l2"),
    )


def owner_fixture(loop, proposal, *, motion=.02, tick=100):
    floor, regime = EXPERIMENTS[proposal.experiment_id]
    return WorldTrialReceipt(
        world_uuid=loop.world_uuid, subject_uuid=loop.subject_uuid,
        session_id=loop.session_id, proposal_sha256=proposal.proposal_sha256,
        experiment_id=proposal.experiment_id,
        action_id=f"original-{proposal.round}", action_outcome="S16_OUTCOME",
        actual_floor_material=floor, actual_input_regime=regime,
        wait_ticks=tuple(range(tick, tick + 8)),
        wait_motion_m=(motion,) * 8,
        paper_original_sha256="a" * 64,
        native_original_sha256="b" * 64,
    )


def train():
    loop = L2ExperimentLoop("old-world", "one-subject", "old-session")
    for i in range(2):
        p = loop.propose(fixture_l2)
        loop.record_owner_result(owner_fixture(
            loop, p, motion=.03 if i == 0 else .01, tick=100 + i * 20,
        ))
    return loop


def predict(model, experiment="GRASS_SHORT"):
    return forecast_next_epoch(
        model, world_uuid="new-world", subject_uuid=model.subject_uuid,
        session_id="new-session", action_id="heldout-action",
        proposal_sha256="e" * 64, experiment_id=experiment,
    )


def next_fixture(frozen, *, motion=.03):
    floor, regime = EXPERIMENTS[frozen.experiment_id]
    return WorldTrialReceipt(
        world_uuid=frozen.world_uuid, subject_uuid=frozen.subject_uuid,
        session_id=frozen.session_id,
        proposal_sha256=frozen.proposal_sha256,
        experiment_id=frozen.experiment_id, action_id=frozen.action_id,
        action_outcome="S16_OUTCOME", actual_floor_material=floor,
        actual_input_regime=regime, wait_ticks=tuple(range(300, 308)),
        wait_motion_m=(motion,) * 8,
        paper_original_sha256="c" * 64,
        native_original_sha256="d" * 64,
    )


def test_completed_past_epoch_frozen_before_future_result_and_no_promotion():
    past = train()
    model = freeze_epoch(past)
    assert len(model.training) == 2
    assert model.authorized_actions == model.learning_admissions == model.l0_promotions == 0
    assert model.source_status == "UNVERIFIED_MP11_OWNER_FIXTURES"
    future = predict(model)
    assert future.candidate_m == pytest.approx(.24)
    assert future.cheap_global_m == pytest.approx(.16)
    assert future.executable_action is False
    result = score_later(model, future, next_fixture(future))
    assert result.candidate_absolute_error_m == pytest.approx(0)
    assert result.cheap_global_absolute_error_m == pytest.approx(.08)
    assert result.classification == "SHADOW_LOWER_ERROR_UNVERIFIED_SINGLE_HELDOUT"
    assert result.scientific_advantage == "NOT_ESTABLISHED"
    assert result.learning_admissions == 0
    assert freeze_epoch(past) == model  # zero heldout training leakage


def test_unseen_context_abstains_and_returns_to_l2():
    model = freeze_epoch(train())
    future = predict(model, "ICE_LONG")
    assert future.decision == "ABSTAIN_ESCALATE_L2"
    assert future.candidate_m is None
    result = score_later(model, future, next_fixture(future))
    assert result.classification == "ABSTAIN_UNSEEN_CONDITION"
    assert result.candidate_absolute_error_m is None


def test_fixed_cheap_path_can_beat_retained_model():
    model = freeze_epoch(train())
    future = predict(model)
    result = score_later(model, future, next_fixture(future, motion=0.0))
    assert result.cheap_zero_absolute_error_m == 0
    assert result.classification == "CHEAP_TIE_OR_BETTER_UNVERIFIED_SINGLE_HELDOUT"


@pytest.mark.parametrize("changes", [
    {"world_uuid": "old-world"},
    {"session_id": "old-session"},
    {"subject_uuid": "foreign-subject"},
    {"experiment_id": "EXEC_SHELL"},
    {"proposal_sha256": "forged"},
])
def test_cross_epoch_and_proposal_scope_are_strict(changes):
    model = freeze_epoch(train())
    kwargs = dict(
        world_uuid="new-world", subject_uuid=model.subject_uuid,
        session_id="new-session", action_id="heldout-action",
        experiment_id="GRASS_SHORT", proposal_sha256="e" * 64,
    )
    with pytest.raises(MP11RetentionRejected):
        forecast_next_epoch(model, **(kwargs | changes))


@pytest.mark.parametrize("changes", [
    {"candidate_m": 999.0},
    {"forecast_sha256": "b" * 64},
    {"learning_admission": 1},
    {"executable_action": True},
])
def test_modified_pre_result_forecast_fails_closed(changes):
    model = freeze_epoch(train())
    frozen = predict(model)
    with pytest.raises(MP11RetentionRejected):
        score_later(model, replace(frozen, **changes), next_fixture(frozen))


@pytest.mark.parametrize("changes", [
    {"world_uuid": "old-world"},
    {"session_id": "old-session"},
    {"proposal_sha256": "f" * 64},
    {"actual_floor_material": "LAVA"},
    {"actual_input_regime": "OTHER"},
    {"wait_motion_m": (float("nan"),) * 8},
    {"wait_ticks": (1, 2, 3, 4, 5, 6, 8, 9)},
    {"source_status": "QUALIFIED_BY_CLAIM"},
])
def test_forged_or_incomplete_future_original_is_rejected(changes):
    model = freeze_epoch(train())
    frozen = predict(model)
    with pytest.raises(MP11RetentionRejected):
        score_later(model, frozen, replace(next_fixture(frozen), **changes))


def test_outstanding_and_forged_training_or_modified_retained_model_rejected():
    loop = L2ExperimentLoop("old-world", "one-subject", "old-session")
    p = loop.propose(fixture_l2)
    with pytest.raises(MP11RetentionRejected):
        freeze_epoch(loop)
    loop.record_owner_result(owner_fixture(loop, p))
    model = freeze_epoch(loop)
    with pytest.raises(MP11RetentionRejected):
        predict(replace(model, model_sha256="f" * 64))
    with pytest.raises(MP11RetentionRejected):
        predict(replace(model, training=()))
    loop.receipts[0] = replace(
        loop.receipts[0], source_status="UNILATERALLY_AUTHENTICATED",
    )
    with pytest.raises(MP11RetentionRejected):
        freeze_epoch(loop)
