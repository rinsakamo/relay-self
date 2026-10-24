"""Synthetic controls for occlusion and counterfactual SelfWorld transfer."""

from dataclasses import replace

import pytest

from experiments.self_world_occlusion_counterfactual import (
    ACTION_HOLD,
    ACTION_NUDGE,
    ARM_LOCAL,
    ARM_PERSIST,
    ARM_TRANSFER,
    OccludedTask,
    PositivePosition,
    PositiveTransition,
    ScoreStatus,
    TransferProbeBlocked,
    compress_drift,
    issue_forecast,
    score_sealed,
    simulate_twin,
)


def _pos(
    region: str, target: str, step: int, x: int,
    *, self_id: str = "self-a", session: str = "session-a",
) -> PositivePosition:
    return PositivePosition(
        self_id, session, region, target,
        f"{session}/{region}/{target}/{step}", step, x,
    )


def _positive_training(delta: int = 1):
    return (
        PositiveTransition(
            _pos("region-a", "entity-a", 0, 10),
            _pos("region-a", "entity-a", 1, 10 + delta),
        ),
        PositiveTransition(
            _pos("region-b", "entity-b", 0, 100),
            _pos("region-b", "entity-b", 1, 100 + delta),
        ),
    )


def _rule(delta: int = 1):
    r = compress_drift(_positive_training(delta))
    assert r is not None
    return r


def _task(*, two: bool = False, goal: int = 2):
    observations = (
        (_pos("region-c", "entity-c", 0, -1),)
        if two else ()
    )
    return OccludedTask(
        history=(*observations, _pos("region-c", "entity-c", 1, 0)),
        goal_x=goal,
    )


def _outcome(task, hidden_drift: int = 1):
    return simulate_twin(
        task, hidden_drift=hidden_drift,
        after_ref_hold="synthetic/holdout/hold/step2",
        after_ref_nudge="synthetic/holdout/nudge/step2",
    )


def test_training_compresses_two_sites_into_one_regular_delta():
    rule = _rule()
    assert rule.delta_x == 1
    assert rule.trained_regions == ("region-a", "region-b")
    assert len(rule.evidence_pairs) == 2
    assert len(rule.digest) == 64


def test_compression_is_deterministic_and_disallows_conflicting_deltas():
    assert _rule().digest == _rule().digest
    pairs = _positive_training()
    mismatch = PositiveTransition(
        _pos("region-b", "entity-b", 0, 100),
        _pos("region-b", "entity-b", 1, 98),
    )
    assert compress_drift((pairs[0], mismatch)) is None


@pytest.mark.parametrize("training", [
    (),
    (_positive_training()[0],),
    (
        _positive_training()[0],
        PositiveTransition(
            _pos("region-a", "entity-b", 0, 100),
            _pos("region-a", "entity-b", 1, 101),
        ),
    ),
])
def test_two_independent_regions_required(training):
    assert compress_drift(training) is None


def test_cross_self_training_rejected():
    foreign = PositiveTransition(
        _pos("region-b", "entity-b", 0, 10, self_id="self-b"),
        _pos("region-b", "entity-b", 1, 11, self_id="self-b"),
    )
    with pytest.raises(TransferProbeBlocked, match="cross-self"):
        compress_drift((_positive_training()[0], foreign))


def test_cross_session_training_rejected():
    foreign = PositiveTransition(
        _pos("region-b", "entity-b", 0, 10, session="session-b"),
        _pos("region-b", "entity-b", 1, 11, session="session-b"),
    )
    with pytest.raises(TransferProbeBlocked, match="cross-self"):
        compress_drift((_positive_training()[0], foreign))


def test_mixed_identity_pair_rejected():
    with pytest.raises(TransferProbeBlocked, match="mixed source"):
        PositiveTransition(
            _pos("region-b", "entity-b", 0, 10),
            _pos("region-b", "entity-c", 1, 11),
        )


def test_training_intervention_rejected():
    with pytest.raises(TransferProbeBlocked, match="confound"):
        PositiveTransition(
            _pos("region-b", "entity-b", 0, 10),
            _pos("region-b", "entity-b", 1, 11),
            action=ACTION_NUDGE,
        )


def test_non_synthetic_source_does_not_get_attested():
    with pytest.raises(TransferProbeBlocked, match="synthetic"):
        replace(_pos("region-a", "entity-a", 0, 10),
                source_scope="mineflayer")


def test_observation_is_hidden_when_issuing_predictions():
    task = _task()
    assert not hasattr(task, "hidden_drift")
    assert not hasattr(task, "later_observation")
    forecast = issue_forecast(task, method=ARM_TRANSFER, rule=_rule())
    assert forecast.hold_x == 1
    assert forecast.nudge_x == 3
    assert forecast.selected_action == ACTION_HOLD
    assert len(forecast.commitment) == 64


def test_occlusion_forecast_improves_over_persistence():
    task = _task()
    twin = _outcome(task, hidden_drift=1)
    baseline = score_sealed(
        task, issue_forecast(task, method=ARM_PERSIST), twin,
    )
    learned = score_sealed(
        task, issue_forecast(task, method=ARM_TRANSFER, rule=_rule()), twin,
    )
    assert baseline.occluded_error == 1
    assert learned.occluded_error == 0
    assert baseline.counterfactual_error == 2
    assert learned.counterfactual_error == 0


def test_counterfactual_selection_benefit_only_in_synthetic_twin():
    task = _task(goal=2)
    twin = _outcome(task, hidden_drift=1)
    baseline = score_sealed(
        task, issue_forecast(task, method=ARM_PERSIST), twin,
    )
    learned = score_sealed(
        task, issue_forecast(task, method=ARM_TRANSFER, rule=_rule()), twin,
    )
    assert baseline.selected_action == ACTION_NUDGE
    assert learned.selected_action == ACTION_HOLD
    assert (baseline.realized_loss, learned.realized_loss) == (2, 1)
    assert (baseline.regret, learned.regret) == (1, 0)


def test_independent_local_baseline_unavailable_with_one_observation():
    task = _task(two=False)
    local = issue_forecast(task, method=ARM_LOCAL)
    score = score_sealed(task, local, _outcome(task))
    assert score.status is ScoreStatus.UNAVAILABLE
    assert score.realized_loss is None
    assert score.occluded_error is None


def test_independent_local_baseline_ties_transfer_with_two_observations():
    task = _task(two=True)
    twin = _outcome(task)
    local = score_sealed(
        task, issue_forecast(task, method=ARM_LOCAL), twin,
    )
    transfer = score_sealed(
        task, issue_forecast(task, method=ARM_TRANSFER, rule=_rule()), twin,
    )
    assert local.status is ScoreStatus.SCORED
    assert local.occluded_error == transfer.occluded_error == 0
    assert local.regret == transfer.regret == 0


def test_static_world_persistence_beats_wrong_learned_drift():
    task = _task()
    twin = _outcome(task, hidden_drift=0)
    cheap = score_sealed(task, issue_forecast(task, method=ARM_PERSIST), twin)
    transfer = score_sealed(
        task, issue_forecast(task, method=ARM_TRANSFER, rule=_rule()), twin,
    )
    assert cheap.occluded_error == 0
    assert transfer.occluded_error == 1


def test_rule_reversal_transfer_is_worse_than_cheap_persistence():
    task = _task()
    twin = _outcome(task, hidden_drift=-1)
    cheap = score_sealed(task, issue_forecast(task, method=ARM_PERSIST), twin)
    transfer = score_sealed(
        task, issue_forecast(task, method=ARM_TRANSFER, rule=_rule()), twin,
    )
    assert cheap.occluded_error == 1
    assert transfer.occluded_error == 2


def test_baseline_operates_even_when_transfer_disallowed():
    task = OccludedTask(
        (_pos("region-a", "entity-a", 2, 20),), goal_x=21,
    )
    assert issue_forecast(task, method=ARM_PERSIST).hold_x == 20
    with pytest.raises(TransferProbeBlocked, match="unseen"):
        issue_forecast(task, method=ARM_TRANSFER, rule=_rule())


def test_foreign_rule_rejected_without_blocking_baseline():
    task = _task()
    r = replace(_rule(), self_id="self-b")
    with pytest.raises(TransferProbeBlocked, match="cross-self"):
        issue_forecast(task, method=ARM_TRANSFER, rule=r)
    assert issue_forecast(task, method=ARM_PERSIST).selected_action is not None


def test_replayed_training_source_never_allowed_for_holdout():
    training = _positive_training()
    task = OccludedTask(
        (_pos("region-c", "entity-c", 0, 10),), goal_x=12,
    )
    reused = replace(
        task,
        history=(replace(task.history[0],
                         source_ref=training[0].before.source_ref),),
    )
    with pytest.raises(TransferProbeBlocked, match="leaked"):
        issue_forecast(reused, method=ARM_TRANSFER, rule=_rule())


def test_foreign_history_is_rejected():
    with pytest.raises(TransferProbeBlocked, match="foreign"):
        OccludedTask(
            (_pos("region-c", "entity-c", 0, 0),
             _pos("region-c", "entity-d", 1, 1)),
            goal_x=2,
        )


def test_forecast_identity_and_tampering_are_checked_before_scoring():
    task = _task()
    forecast = issue_forecast(task, method=ARM_TRANSFER, rule=_rule())
    twin = _outcome(task)
    with pytest.raises(TransferProbeBlocked, match="modified"):
        score_sealed(task, replace(forecast, hold_x=999), twin)
    with pytest.raises(TransferProbeBlocked, match="foreign"):
        score_sealed(replace(task, goal_x=100), forecast, twin)


def test_synthetic_twins_require_two_distinct_future_sources():
    task = _task()
    with pytest.raises(TransferProbeBlocked, match="replay"):
        simulate_twin(
            task, hidden_drift=1,
            after_ref_hold="same", after_ref_nudge="same",
        )


def test_no_physical_outcome_is_inferred_from_unknown_sensor_input():
    with pytest.raises(TransferProbeBlocked, match="pre-gap observations"):
        OccludedTask(history=(), goal_x=2)
    local = issue_forecast(_task(), method=ARM_LOCAL)
    assert local.selected_action is None


def test_future_truth_is_not_argument_to_forecast_issue():
    task = _task()
    with pytest.raises(TypeError):
        issue_forecast(task, method=ARM_TRANSFER, rule=_rule(), hidden_drift=1)


def test_multiple_methods_get_identical_task_fingerprint():
    task = _task()
    r = _rule()
    assert (
        issue_forecast(task, method=ARM_PERSIST).task_fingerprint
        == issue_forecast(task, method=ARM_LOCAL).task_fingerprint
        == issue_forecast(task, method=ARM_TRANSFER, rule=r).task_fingerprint
    )


def test_gap_is_explicit_unknown_not_entity_absence():
    task = replace(_task(), gap_status="UNOBSERVED")
    forecast = issue_forecast(task, method=ARM_TRANSFER, rule=_rule())
    assert forecast.hold_x == 1
    assert task.gap_status == "UNOBSERVED"
    assert task.fingerprint != _task().fingerprint


def test_invalid_gap_status_is_rejected():
    with pytest.raises(TransferProbeBlocked, match="gap status"):
        replace(_task(), gap_status="PRESENT_BUT_NO_ENEMIES")


def test_candidate_source_forgery_is_rejected():
    with pytest.raises(TransferProbeBlocked, match="not synthetic"):
        replace(_rule(), source_scope="mineflayer")


def test_candidate_evidence_mutation_is_rejected():
    with pytest.raises(TransferProbeBlocked, match="incomplete"):
        replace(_rule(), evidence_pairs=())


def test_inconsistent_twin_cannot_be_promoted_into_outcome():
    task = _task()
    forecast = issue_forecast(task, method=ARM_PERSIST)
    fake = replace(_outcome(task), nudge_x=999)
    with pytest.raises(TransferProbeBlocked, match="provenance inconsistent"):
        score_sealed(task, forecast, fake)


def test_future_training_cannot_leak_into_pre_gap_forecast():
    future = tuple(
        PositiveTransition(replace(pair.before, step=10), replace(pair.after, step=11))
        for pair in _positive_training()
    )
    rule = compress_drift(future)
    with pytest.raises(TransferProbeBlocked, match="future training"):
        issue_forecast(_task(), method=ARM_TRANSFER, rule=rule)



@pytest.mark.parametrize("bad_rule", [None, replace(_rule(), session_id="foreign")])
def test_two_reading_baselines_score_independently_of_invalid_transfer(bad_rule):
    task = _task(two=True)
    forecasts = [issue_forecast(task, method=arm) for arm in (ARM_PERSIST, ARM_LOCAL)]
    with pytest.raises(TransferProbeBlocked):
        issue_forecast(task, method=ARM_TRANSFER, rule=bad_rule)
    twin = _outcome(task)
    assert [score_sealed(task, f, twin).occluded_error for f in forecasts] == [1, 0]


def test_stale_or_duplicate_history_is_rejected():
    task = _task(two=True)
    with pytest.raises(TransferProbeBlocked, match="non-consecutive"):
        replace(task, history=(replace(task.history[0], step=task.latest.step), task.latest))
    with pytest.raises(TransferProbeBlocked, match="non-consecutive"):
        replace(task, history=(replace(task.history[0], source_ref=task.latest.source_ref),
                               task.latest))


def test_predictions_precede_twins_and_do_not_depend_on_hidden_outcome():
    task = _task(two=True)
    forecasts = tuple(issue_forecast(task, method=arm, rule=_rule() if arm == ARM_TRANSFER
                                    else None)
                      for arm in (ARM_PERSIST, ARM_LOCAL, ARM_TRANSFER))
    commitments = tuple(f.commitment for f in forecasts)
    for hidden in (1, 0, -1):
        twin = _outcome(task, hidden_drift=hidden)
        for forecast in forecasts:
            score_sealed(task, forecast, twin)
        assert tuple(f.commitment for f in forecasts) == commitments
    assert forecasts[-1] == issue_forecast(task, method=ARM_TRANSFER, rule=_rule())
