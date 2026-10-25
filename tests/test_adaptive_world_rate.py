"""Offline tests only; no Minecraft/LLM/GPU, no TPS actuator."""
from dataclasses import replace

import pytest

from adapters.mineflayer.m02_paper_dev.adaptive_world_rate import (
    RateAction,
    RatePolicy,
    RateState,
    TickWindow,
    propose_world_rate,
    simulated_seconds,
)


def ticks(first=101, size=10, *, tps=20, **kw):
    sequence = tuple(range(first, first + size))
    return TickWindow(
        "world-A", "session-A", first, first + size - 1,
        sequence, sequence, size * 1_000_000_000 // tps, **kw,
    )


def test_stable_windows_gradually_raise_without_a_fixed_200_tps_limit():
    policy = RatePolicy(experimental_cap_tps=400)
    state = RateState()
    for start, expected, action in ((101, 20, RateAction.HOLD),
                                    (111, 20, RateAction.HOLD),
                                    (121, 25, RateAction.RAISE),
                                    (131, 25, RateAction.HOLD)):
        result = propose_world_rate(state, ticks(start, tps=state.requested_tps),
                                    policy=policy)
        assert result.state.requested_tps == expected
        assert result.action is action
        assert not result.stop_required
        state = result.state


def test_actual_tps_lag_reduces_rate_immediately_and_clears_streak():
    result = propose_world_rate(RateState(200, 2), ticks(tps=80))
    assert result.action is RateAction.LOWER
    assert result.state.requested_tps == 100
    assert result.state.good_windows == 0
    assert result.effective_tps == 80


def test_cognition_slows_world_without_world_pause():
    result = propose_world_rate(RateState(20), ticks(cognition_pending=True))
    assert result.state.requested_tps == 10
    assert propose_world_rate(result.state,
                              ticks(111, tps=10, cognition_pending=True)).state.requested_tps == 5
    result = propose_world_rate(RateState(2), ticks(tps=2, cognition_pending=True))
    assert result.state.requested_tps == 2
    assert result.action is RateAction.HOLD


def test_every_world_tick_must_have_a_matching_l0_tick_not_merely_a_count():
    sample = ticks()
    for bad in (
        replace(sample, l0_checked_ticks=sample.l0_checked_ticks[:-1]),
        replace(sample, l0_checked_ticks=(102,) + sample.l0_checked_ticks[1:]),
        replace(sample, l0_checked_ticks=tuple(reversed(sample.l0_checked_ticks))),
        replace(sample, paper_ticks=sample.paper_ticks[:-1]),
        replace(sample, paper_ticks=sample.paper_ticks[:-1] + (999,)),
    ):
        result = propose_world_rate(RateState(200), bad)
        assert result.action is RateAction.FALLBACK
        assert result.state.requested_tps == 20
        assert result.effective_tps is None
        assert result.stop_required


def test_mismatched_world_session_or_noncontiguous_windows_fail_closed():
    state = propose_world_rate(RateState(), ticks()).state
    for bad in (ticks(112), replace(ticks(111), world_id="other"),
                replace(ticks(111), session_id="other")):
        result = propose_world_rate(state, bad)
        assert result.action is RateAction.FALLBACK
        assert result.stop_required


def test_active_action_requires_separate_motor_proof_and_authorization():
    for params in ({}, {"tick_motor_verified": True},
                   {"action_rate_authorized": True}):
        result = propose_world_rate(
            RateState(200), ticks(tps=200, action_active=True, **params),
        )
        assert result.action is RateAction.FALLBACK
        assert result.stop_required
        assert result.state.requested_tps == 20
    good = ticks(tps=200, action_active=True, tick_motor_verified=True,
                 action_rate_authorized=True)
    result = propose_world_rate(RateState(200), good)
    assert result.action is RateAction.HOLD
    assert not result.stop_required


def test_unqualified_20tps_action_never_accelerates_and_lag_stops():
    state = RateState(20, 2)
    accepted = propose_world_rate(state, ticks(action_active=True))
    assert accepted.state.requested_tps == 20
    assert accepted.state.good_windows == 0
    assert accepted.action is RateAction.HOLD
    lag = propose_world_rate(state, ticks(tps=11, action_active=True))
    assert lag.action is RateAction.FALLBACK
    assert lag.stop_required


def test_danger_or_late_stop_preempts_any_acceleration():
    for key in ("danger", "missed_control_deadline"):
        result = propose_world_rate(RateState(250), ticks(tps=250, **{key: True}))
        assert result.action is RateAction.FALLBACK
        assert result.stop_required
        assert result.reason == "DANGER_OR_CONTROL_DEADLINE"


def test_explicit_cap_minimum_and_real_elapsed_time_accounting():
    policy = RatePolicy(experimental_cap_tps=31, raise_after_windows=2)
    result = propose_world_rate(RateState(30, 1), ticks(tps=30), policy=policy)
    assert result.state.requested_tps == 31
    second = propose_world_rate(result.state, ticks(111, tps=31), policy=policy)
    assert second.state.requested_tps == 31
    assert simulated_seconds(200) == 10.0  # At ANY wall TPS.
    with pytest.raises(ValueError):
        simulated_seconds(-1)
    with pytest.raises(ValueError):
        RatePolicy(min_tps=0)
    with pytest.raises(ValueError):
        RatePolicy(raise_after_windows=1)


def test_invalid_numeric_and_bool_inputs_never_grant_acceleration():
    good = ticks()
    for bad in (replace(good, first_server_tick=True),
                replace(good, wall_elapsed_ns=0),
                replace(good, action_active="no"),
                replace(good, first_server_tick=-1)):
        result = propose_world_rate(RateState(20), bad)
        assert result.action is RateAction.FALLBACK
        assert result.stop_required
