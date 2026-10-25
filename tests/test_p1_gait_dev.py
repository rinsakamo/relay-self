"""Focused DEV checks for one-P1 running fatigue and M0 DASH charge."""

from dataclasses import replace

import pytest

from experiments.fatigue_p1 import (
    FatigueFrame,
    FatigueProfile,
    FatigueRejected,
    advance,
    initial_state,
)
from experiments.p1_gait_dev import (
    GaitRatesDev,
    GaitTickDev,
    advance_gait_dev,
    dash_budget_dev,
)


def tick(profile, state, gait, *, power=0.0, extra=None, direction="forward"):
    return advance_gait_dev(
        profile, state,
        GaitTickDev(state.session_id, state.world_tick + 1, gait,
                    direction, power, extra),
    )


def test_legacy_p1_wait_and_move_unchanged():
    cfg = FatigueProfile(enabled=True, initial=0.5)
    state = initial_state(cfg, "legacy")
    old = advance(cfg, state, FatigueFrame("legacy", 1, "MOVE", 1.0))
    assert old.after.fatigue == pytest.approx(.54)
    assert old.recovered == 0
    assert tick(cfg, state, "WALK").after.fatigue < state.fatigue


def test_four_modes_speed_and_forward_only_dash():
    cfg = FatigueProfile(enabled=True)
    state = initial_state(cfg, "s")
    speeds = [tick(cfg, state, gait).nominal_forward_speed_m_s
              for gait in ("WALK", "JOG", "RUN")]
    dash = tick(cfg, state, "DASH", power=1.0, extra=1.0)
    assert speeds == pytest.approx([1.3, 4.32, 5.61])
    assert dash.nominal_forward_speed_m_s == pytest.approx(5.61 * 1.5)
    with pytest.raises(FatigueRejected):
        tick(cfg, state, "DASH", power=1, extra=1, direction="back")
    with pytest.raises(FatigueRejected):
        tick(cfg, state, "DASH", power=1, extra=1, direction="side")
    assert tick(cfg, state, "RUN", direction="back").frame.direction == "back"


def test_full_dash_fatigue_reaches_limit_at_20s_while_recovering():
    cfg = FatigueProfile(enabled=True)
    state = initial_state(cfg, "full-dash")
    m0_charges = 0
    for _ in range(399):
        result = tick(cfg, state, "DASH", power=1, extra=1)
        assert result.recovered >= 0
        if state.fatigue > 0:
            assert result.recovered > 0
        m0_charges += result.added_m0_charge
        state = result.after
    assert state.fatigue < 1.0
    final = tick(cfg, state, "DASH", power=1, extra=1)
    assert final.after.fatigue == pytest.approx(1.0, abs=1e-9)
    assert final.exhausted
    assert m0_charges + final.added_m0_charge == pytest.approx(4.0)
    assert final.m0_ledger_posted is False
    assert final.source_authenticated is False
    with pytest.raises(FatigueRejected):
        tick(cfg, final.after, "DASH", power=1, extra=1)


def test_partial_dash_last_longer_with_gentle_curve():
    cfg = FatigueProfile(enabled=True)
    full = initial_state(cfg, "full")
    half = initial_state(cfg, "half")
    for _ in range(400):
        full = tick(cfg, full, "DASH", power=1, extra=1).after
        half = tick(cfg, half, "DASH", power=.5, extra=1).after
    assert full.fatigue > half.fatigue
    assert 0.30 < half.fatigue < .60
    assert tick(cfg, half, "DASH", power=.5, extra=1).after.fatigue > half.fatigue


def test_run_plateaus_and_walk_recovers_during_motion():
    cfg = FatigueProfile(enabled=True, initial=.5)
    state = initial_state(cfg, "recover")
    first = tick(cfg, state, "RUN")
    assert first.accumulated > 0 and first.recovered > 0
    assert first.after.fatigue < state.fatigue
    for _ in range(4000):
        first = tick(cfg, first.after, "RUN")
    assert first.after.fatigue == pytest.approx(.16, abs=.003)
    before_walk = first.after
    after_walk = tick(cfg, before_walk, "WALK")
    assert after_walk.after.fatigue < before_walk.fatigue
    before_wait = after_walk.after
    assert tick(cfg, before_wait, "WAIT").after.fatigue < before_wait.fatigue


def test_m0_extra_energy_budget_limits_output_not_action_authority():
    cfg = FatigueProfile(enabled=True)
    state = initial_state(cfg, "energy")
    assert dash_budget_dev(cfg, state, 1.0, 1).permitted_power == 1
    capped = dash_budget_dev(cfg, state, 1.0, .005)
    assert capped.permitted_power == pytest.approx(.5)
    assert capped.energy_limited
    no_budget = dash_budget_dev(cfg, state, 1.0, 0)
    assert no_budget.permitted_power == 0
    assert no_budget.admitted_gait == "RUN"
    with pytest.raises(FatigueRejected):
        tick(cfg, state, "DASH", power=1, extra=.005)
    applied = tick(cfg, state, "DASH", power=.5, extra=.005)
    assert applied.added_m0_charge == pytest.approx(.005)
    assert applied.new_action_issuer is False


def test_dash_exhaustion_recovers_with_walk_and_wait_no_extra_gauge():
    cfg = FatigueProfile(enabled=True, initial=1.0)
    exhausted = initial_state(cfg, "exhausted")
    assert dash_budget_dev(cfg, exhausted, 1, 1).fatigue_limited
    assert dash_budget_dev(cfg, exhausted, 1, 1).permitted_power == 0
    walked = tick(cfg, exhausted, "WALK").after
    assert walked.fatigue < exhausted.fatigue
    assert dash_budget_dev(cfg, walked, 1, 1).permitted_power == 1
    assert not hasattr(walked, "dash_stamina")
    assert tick(cfg, walked, "WAIT").after.fatigue < walked.fatigue


@pytest.mark.parametrize("gait,power,extra,direction", [
    ("DASH", 1, None, "forward"),
    ("DASH", 1, -1, "forward"),
    ("DASH", -1, 1, "forward"),
    ("DASH", 1.1, 1, "forward"),
    ("DASH", float("nan"), 1, "forward"),
    ("DASH", True, 1, "forward"),
    ("DASH", 0, 1, "forward"),
    ("JOG", 0, 1, "forward"),
    ("RUN", 1, None, "forward"),
    ("WAIT", 0, None, "invalid"),
    ("FLY", 0, None, "forward"),
])
def test_invalid_applied_motion_cannot_fake_gait(gait, power, extra, direction):
    cfg = FatigueProfile(enabled=True)
    with pytest.raises(FatigueRejected):
        tick(cfg, initial_state(cfg, "s"), gait,
             power=power, extra=extra, direction=direction)


def test_nonconsecutive_other_session_off_profile_and_rates_fail_closed():
    cfg = FatigueProfile(enabled=True)
    state = initial_state(cfg, "s")
    with pytest.raises(FatigueRejected):
        advance_gait_dev(cfg, state, GaitTickDev("other", 1, "RUN"))
    with pytest.raises(FatigueRejected):
        advance_gait_dev(cfg, state, GaitTickDev("s", 2, "RUN"))
    with pytest.raises(FatigueRejected):
        tick(FatigueProfile(), initial_state(FatigueProfile(), "s"), "RUN")
    with pytest.raises(FatigueRejected):
        tick(replace(cfg, initial=.2), state, "RUN")
    for kwargs in (
        {"run_speed_m_s": 0},
        {"max_dash_multiplier": 1},
        {"dash_load_curve": float("inf")},
        {"jog_recovery_per_s": -1},
        {"walk_load_per_s": 1},
    ):
        with pytest.raises(FatigueRejected):
            GaitRatesDev(**kwargs)
