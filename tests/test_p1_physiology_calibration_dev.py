"""P1 physics calibration opt-in: no backward rewrite of T1r / Draft #626."""
from __future__ import annotations

import hashlib
import json
import math
from dataclasses import asdict, replace

import pytest

from adapters.mineflayer.t2_tick_accounting import TickAccounting
from experiments.fatigue_p1 import (
    FatigueFrame, FatigueProfile, FatigueRejected, FatigueSensor,
    Rate, advance, initial_state, observe,
)
from experiments.p1_physiology_profile_dev import (
    P1_RECOVERY_TAU_WORLD_SECONDS, P1_WALK_FATIGUE_PER_BLOCK,
    calibrated_walk_profile_dev,
)
from test_t1f_t2_dev import frame, release


def step(profile, state, activity, **extra):
    return advance(profile, state, FatigueFrame(
        state.session_id, state.world_tick + 1, activity, **extra))


def test_historical_default_profile_hash_exactly_preserved():
    old = FatigueProfile(enabled=True, initial=.35)
    fields = asdict(old)
    assert fields.pop("recovery_time_constant_world_seconds") is None
    legacy_sha = hashlib.sha256(json.dumps(
        fields, sort_keys=True, separators=(",", ":"), allow_nan=False,
    ).encode("utf-8")).hexdigest()
    assert old.sha256 == legacy_sha
    result = step(old, initial_state(old, "legacy"), "WAIT")
    assert result.recovered == pytest.approx(.10)
    assert result.after.fatigue == pytest.approx(.25)


def test_calibrated_native_case_is_opt_in_only():
    from adapters.mineflayer.t1e_native_dev import TICK_CASES
    from adapters.mineflayer.t1o_trace_policy_dev import trace_enabled

    assert "t1s_calibrated_body_loop" in TICK_CASES
    assert trace_enabled("t1s_calibrated_body_loop", "off") is False
    assert trace_enabled("t1r_body_recovery", "off") is False


def test_new_profile_is_opt_in_distinct_source_hash():
    candidate = calibrated_walk_profile_dev()
    old = FatigueProfile(enabled=True)
    assert old.recovery_time_constant_world_seconds is None
    assert candidate.recovery_time_constant_world_seconds == 40.0
    assert candidate.sha256 != old.sha256
    assert candidate.move_per_block.value == P1_WALK_FATIGUE_PER_BLOCK
    assert TickAccounting("legacy").profile.sha256 == old.sha256
    assert TickAccounting("new", fatigue_profile=candidate).profile.sha256 == candidate.sha256
    with pytest.raises(TypeError):
        TickAccounting("invalid", fatigue_profile="not-P1")


def test_single_wait_tick_cannot_reset_fatigue():
    profile = replace(calibrated_walk_profile_dev(), initial=1)
    before = initial_state(profile, "person")
    one = step(profile, before, "WAIT")
    assert 0 < one.recovered < .002
    assert one.after.fatigue > .998
    assert one.after.fatigue == pytest.approx(
        math.exp(-1 / (20 * P1_RECOVERY_TAU_WORLD_SECONDS)),
    )
    assert one.recovered < .02 * before.fatigue


def test_calibrated_exponential_recovery_is_world_time_not_tps():
    profile = replace(calibrated_walk_profile_dev(), initial=.8)
    results = []
    for wall_tps in (2, 20, 200):
        state = initial_state(profile, f"session-{wall_tps}")
        for _ in range(20 * 40):
            state = step(profile, state, "WAIT").after
        results.append(state.fatigue)
    assert results[0] == results[1] == results[2]
    assert results[0] == pytest.approx(.8 * math.exp(-1), rel=1e-10)
    assert results[0] > .25  # 40 seconds rest is not full recovery


def test_short_walk_load_is_small_but_real_and_sensed_only_after_quantization():
    candidate = calibrated_walk_profile_dev()
    state = initial_state(candidate, "walk")
    moved = step(candidate, state, "MOVE", observed_blocks=.8)
    assert moved.accumulated == pytest.approx(.00008)
    assert moved.recovered == 0
    assert observe(candidate, moved.after, FatigueSensor(quantum=.01)).reading == 0.0
    # Tiny normal-WALK effort must not be magnified into a fabricated
    # immediately visible REST signal merely to preserve historical T1r PASS.
    blocked = step(candidate, moved.after, "MOVE", observed_blocks=0, blocked=True)
    assert blocked.recovered == 0
    assert blocked.after.fatigue == moved.after.fatigue


def test_one_minute_walk_load_and_rest_do_not_imply_exhaustion_or_instant_recovery():
    candidate = calibrated_walk_profile_dev()
    state = initial_state(candidate, "walk")
    for _ in range(1200):
        state = step(candidate, state, "MOVE", observed_blocks=.20).after  # 4 blocks/s
    assert state.fatigue == pytest.approx(.024)
    before = state.fatigue
    rest = step(candidate, state, "WAIT")
    assert rest.after.fatigue > before * .99
    assert rest.recovered > 0


def test_p1_m0_original_source_and_basal_remain_separate():
    profile = calibrated_walk_profile_dev()
    owner = TickAccounting("test-session", fatigue_profile=profile)
    owner.observe(frame(1))
    release(owner, seq=1)
    owner.observe(frame(2, control="MOVING", bits=2, x=.5))
    owner.observe(frame(3, x=.5))
    owner.observe(frame(4, x=.5))
    assert [r["activity"] for r in owner.rows] == [
        "MOVE_OR_UNDETERMINED", "MOVE_OR_UNDETERMINED", "WAIT_DEV",
    ]
    assert owner.rows[0]["p1"]["accumulated"] == pytest.approx(.00005)
    assert 0 < owner.rows[-1]["p1"]["recovered"] < .000001
    assert sum(r["m0_basal"] for r in owner.rows) == pytest.approx(.003)
    assert owner.energy.body.tick == 3
    assert owner.rows[-1]["full_tick_R_attested"] is False


@pytest.mark.parametrize("tau", [0, -.1, .5, 3600.1, math.inf, math.nan, True, "40"])
def test_bad_recovery_time_constants_fail_closed(tau):
    with pytest.raises(FatigueRejected):
        replace(calibrated_walk_profile_dev(), recovery_time_constant_world_seconds=tau)


def test_source_profile_swap_denied_after_a_tick():
    profile = calibrated_walk_profile_dev()
    state = step(profile, initial_state(profile, "s"), "MOVE", observed_blocks=.5).after
    foreign = replace(profile, recovery_time_constant_world_seconds=30.0)
    with pytest.raises(FatigueRejected):
        step(foreign, state, "WAIT")


def test_wait_rate_still_caps_exponential_recovery():
    profile = replace(calibrated_walk_profile_dev(), initial=1.0,
                      wait_recovery_per_world_tick=Rate(.0002))
    one = step(profile, initial_state(profile, "s"), "WAIT")
    assert one.recovered == pytest.approx(.0002)
