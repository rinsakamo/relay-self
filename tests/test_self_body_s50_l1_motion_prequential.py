"""#653 L1-MP2: immutable forecast ticket -> heldout score -> separate update.

Uses two OLD DEV World audit reports. This is a replay/order-test only,
NOT true prospective freeze before Minecraft World startup.
"""
from __future__ import annotations

from dataclasses import replace

import pytest

from adapters.mineflayer.self_body_s50_l1_motion_prediction import (
    MotionPredictionRejected,
)
from adapters.mineflayer.self_body_s50_l1_motion_prequential import (
    TargetWorldIdentity,
    freeze_for_target,
    score_frozen,
    update_after_score,
)
from test_self_body_s50_l1_motion_prediction import pair


def target(source):
    return TargetWorldIdentity(
        source.session_id, source.paper_world_uuid,
        source.action_id, source.subject_uuid,
    )


def advance():
    train, test = pair()
    ticket = freeze_for_target(train, target(test))
    scored = score_frozen(ticket, train, test)
    updated = update_after_score(ticket, train, test, scored)
    return train, test, ticket, scored, updated


def test_archived_training_freezes_prior_world_only_then_score_and_update():
    train, heldout, ticket, scored, updated = advance()
    assert ticket.model.train_session_id == train.session_id
    assert ticket.model.train_world_uuid == train.paper_world_uuid
    assert ticket.model.training_pairs == 7
    assert len(ticket.ticket_sha256) == 64
    assert ticket.capture_mode == "ARCHIVAL_REPLAY_ORDER_SIMULATION_ONLY"
    assert ticket.source_ceiling == "ARCHIVAL_READBACK_NOT_REAUTHENTICATED"
    assert ticket.model.slope == scored.errors.slope
    assert scored.errors.heldout_prefix_sha256 == heldout.paper_prefix_sha256
    assert scored.errors.l1_linear == scored.errors.cheap_same_linear
    assert not scored.prediction_committed_before_world_attested
    assert not scored.original_paper_reauthenticated
    assert not scored.learned_l1_policy
    assert updated.training_pairs == 14
    assert updated.distinct_worlds == 2
    assert updated.cheap_equivalent
    assert updated.refitted_slope == updated.cheap_pooled_slope
    assert updated.predecessor_ticket_sha256 == ticket.ticket_sha256
    assert updated.training_source_sha256 == train.paper_prefix_sha256
    assert updated.newly_scored_source_sha256 == heldout.paper_prefix_sha256
    assert updated.classification.endswith("UNTESTED_NEXT_WORLD")
    assert not any((
        updated.learning_admissions, updated.s10_updates,
        updated.s11_grants, updated.action_issues,
    ))


def test_no_lookahead_ticket_cannot_change_after_future_sample_edit():
    train, heldout = pair()
    ticket = freeze_for_target(train, target(heldout))
    modified = replace(heldout, steps=tuple(
        replace(row, displacement_m=0.0) for row in heldout.steps
    ))
    assert freeze_for_target(train, target(modified)) == ticket
    assert score_frozen(ticket, train, heldout) != score_frozen(ticket, train, modified)
    assert ticket == freeze_for_target(train, target(heldout))


def test_actual_source_flags_are_not_claimed_as_input_idle_or_rest():
    train, heldout, ticket, scored, updated = advance()
    assert ticket.capture_mode == "ARCHIVAL_REPLAY_ORDER_SIMULATION_ONLY"
    assert scored.scoring_status == "DEV_SOURCE_SHAPED_ORDER_ONLY"
    assert not scored.prediction_committed_before_world_attested
    assert not scored.original_paper_reauthenticated
    assert not scored.learned_l1_policy
    assert updated.learning_admissions == 0


@pytest.mark.parametrize("field", [
    "same_session", "same_world", "bad_subject", "empty_target",
    "foreign_session", "foreign_world", "foreign_action", "foreign_subject",
    "wrong_train_digest", "wrong_train_slope", "bad_ticket_digest",
    "bad_capture_mode", "claimed_action", "claimed_goal", "claimed_p1",
    "claimed_s10", "claimed_s11", "source_ceiling", "active_train",
    "active_test", "noncontiguous", "future_in_training",
])
def test_ticket_freeze_and_scoring_fail_closed(field):
    train, heldout = pair()
    target_identity = target(heldout)
    if field == "same_session":
        target_identity = replace(target_identity, session_id=train.session_id)
    elif field == "same_world":
        target_identity = replace(target_identity, paper_world_uuid=train.paper_world_uuid)
    elif field == "bad_subject":
        target_identity = replace(target_identity, subject_uuid="unrelated")
    elif field == "empty_target":
        target_identity = replace(target_identity, action_id="")
    if field in ("same_session", "same_world", "bad_subject", "empty_target"):
        with pytest.raises(MotionPredictionRejected):
            freeze_for_target(train, target_identity)
        return

    ticket = freeze_for_target(train, target_identity)
    if field == "foreign_session":
        heldout = replace(heldout, session_id="foreign")
    elif field == "foreign_world":
        heldout = replace(heldout, paper_world_uuid="foreign")
    elif field == "foreign_action":
        heldout = replace(heldout, action_id="foreign")
    elif field == "foreign_subject":
        heldout = replace(heldout, subject_uuid="foreign")
    elif field == "wrong_train_digest":
        train = replace(train, paper_prefix_sha256="a" * 64)
    elif field == "wrong_train_slope":
        ticket = replace(ticket, model=replace(
            ticket.model, slope=ticket.model.slope + 0.1,
        ))
    elif field == "bad_ticket_digest":
        ticket = replace(ticket, ticket_sha256="0" * 64)
    elif field == "bad_capture_mode":
        ticket = replace(ticket, capture_mode="QUALIFIED")
    elif field == "claimed_action":
        ticket = replace(ticket, issued_action=True)
    elif field == "claimed_goal":
        ticket = replace(ticket, goal_admitted=True)
    elif field == "claimed_p1":
        ticket = replace(ticket, p1_wait_admitted=8)
    elif field == "claimed_s10":
        ticket = replace(ticket, s10_updates=1)
    elif field == "claimed_s11":
        ticket = replace(ticket, s11_grants=1)
    elif field == "source_ceiling":
        ticket = replace(ticket, source_ceiling="PAPER_ORIGINAL_FINAL")
    elif field == "active_train":
        train = replace(train, steps=(
            replace(train.steps[0], last_reported_input_active=True),
            *train.steps[1:],
        ))
    elif field == "active_test":
        heldout = replace(heldout, steps=(
            replace(heldout.steps[0], last_reported_input_active=True),
            *heldout.steps[1:],
        ))
    elif field == "noncontiguous":
        heldout = replace(heldout, steps=(
            heldout.steps[0],
            replace(heldout.steps[1], world_tick=123456),
            *heldout.steps[2:],
        ))
    else:
        train = replace(train, steps=heldout.steps)
    with pytest.raises(MotionPredictionRejected):
        score_frozen(ticket, train, heldout)


@pytest.mark.parametrize("field", [
    "missing", "foreign_ticket", "foreign_digest", "fake_score",
    "fake_prospective", "fake_paper_original", "fake_l1_learning",
    "changed_heldout", "changed_training", "changed_model",
])
def test_only_exact_scored_heldout_allows_refit(field):
    train, heldout, ticket, scored, _ = advance()
    if field == "missing":
        scored = None
    elif field == "foreign_ticket":
        scored = replace(scored, ticket=replace(ticket, ticket_sha256="0" * 64))
    elif field == "foreign_digest":
        scored = replace(scored, heldout_prefix_sha256="0" * 64)
    elif field == "fake_score":
        scored = replace(scored, scoring_status="QUALIFIED")
    elif field == "fake_prospective":
        scored = replace(scored, prediction_committed_before_world_attested=True)
    elif field == "fake_paper_original":
        scored = replace(scored, original_paper_reauthenticated=True)
    elif field == "fake_l1_learning":
        scored = replace(scored, learned_l1_policy=True)
    elif field == "changed_heldout":
        heldout = replace(heldout, steps=(
            replace(heldout.steps[0], displacement_m=0.0),
            *heldout.steps[1:],
        ))
    elif field == "changed_training":
        train = replace(train, steps=(
            replace(train.steps[0], displacement_m=0.0),
            *train.steps[1:],
        ))
    else:
        ticket = replace(ticket, model=replace(ticket.model, slope=1.0))
    with pytest.raises(MotionPredictionRejected):
        update_after_score(ticket, train, heldout, scored)


def test_refit_zero_motion_and_cheap_equality_no_physical_go():
    train, heldout = pair()
    quiet_train = replace(train, steps=tuple(
        replace(t, displacement_m=0.0) for t in train.steps
    ))
    quiet_test = replace(heldout, steps=tuple(
        replace(t, displacement_m=0.0) for t in heldout.steps
    ))
    ticket = freeze_for_target(quiet_train, target(quiet_test))
    result = score_frozen(ticket, quiet_train, quiet_test)
    refit = update_after_score(ticket, quiet_train, quiet_test, result)
    assert refit.refitted_slope == refit.cheap_pooled_slope == 0.0
    assert refit.refitted_mean_m == 0.0
    assert refit.distinct_worlds == 2
    assert refit.learning_admissions == refit.s10_updates == refit.s11_grants == 0
