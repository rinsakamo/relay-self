"""P1 fresh-World counterfactual preload comparison, no real recovery assertion."""
from __future__ import annotations

from copy import deepcopy

import pytest

from adapters.mineflayer.s49_p1_dash_pair_review_dev import (
    P1DashPairRejected,
    compare_p1_pair_dev,
)
from adapters.mineflayer.s49_paper_forward_dash_dev import (
    PAIR_FATIGUE,
    PAIR_SOURCE_DIGEST,
    ForwardDashDevRejected,
    audit_native_paper_p1_dev,
)
from experiments.fatigue_p1 import FatigueProfile, initial_state
from experiments.p1_gait_dev import (
    GaitTickDev,
    advance_gait_dev,
    p1_motor_power_limit_dev,
)


def cases():
    def arm(case, sid, world, power, speed, distance):
        return {
            "case": case, "session_id": sid, "paper_world_uuid": world,
            "first_action_id": "s49-native-move-10",
            "first_native_distance_m": distance,
            "second_unboosted_distance_m": .63,
            "first_before_y": -60., "first_threat_distance_m": 2.,
            "first_native_health": 20., "first_native_food": 20.,
            "paper_boost_count": 10,
            "paper_first_applied_power": power,
            "paper_mean_applied_power": power,
            "paper_peak_sampled_speed_mps": speed,
            "paper_mean_boost_sampled_speed_mps": speed,
            "preloaded_hypothetical_fatigue": PAIR_FATIGUE[case],
            "actual_source_frames_verified": True, "model_replay_verified": True,
        }
    return (arm("CARRY", "sid-carry", "world-carry", .76, 7.65, 3.0),
            arm("WAIT_ASSUMED", "sid-post", "world-post", 1., 8.8, 3.5))


def test_two_fresh_world_arms_separate_model_preload_from_wait_recovery():
    base, post = cases()
    same = deepcopy((base, post))
    out = compare_p1_pair_dev(base, post)
    assert (base, post) == same
    assert out["prior_p1_model_source_sha256"] == PAIR_SOURCE_DIGEST
    assert out["paper_applied_power_gain"] == pytest.approx(.24)
    assert out["measured_first_native_distance_delta_m"] == pytest.approx(.5)
    assert out["physical_output_difference_observed"] is True
    assert out["same_self_longitudinal_wait_recovery"] is False
    assert out["actual_p1_fatigue_observed"] is False
    assert out["distance_causally_attributed_to_wait_recovery"] is False
    assert out["physically_qualified_l0_power_admission"] is None
    assert out["r_qualified_wait_ticks"] == 0


def test_source_power_separated_but_physical_delta_undetermined_is_not_failure():
    base, post = cases()
    post["first_native_distance_m"] = 2.95
    post["paper_mean_boost_sampled_speed_mps"] = 7.61
    out = compare_p1_pair_dev(base, post)
    assert out["physical_output_difference_observed"] is False
    assert out["physical_output_if_no_clear_separation"] == "NOT_ESTABLISHED"
    assert out["qualification_go"] is False


@pytest.mark.parametrize("fault", [
    "same_session", "same_world", "forged_verified", "no_replay",
    "foreign_preload", "swap_case", "health_shift", "food_shift",
    "y_shift", "threat_shift", "no_power_gain", "insufficient_gain",
    "power_above_one", "invalid_distance", "nan_speed",
])
def test_pair_rejects_noncomparable_or_unverified_trials(fault):
    base, post = cases()
    if fault == "same_session":
        post["session_id"] = base["session_id"]
    elif fault == "same_world":
        post["paper_world_uuid"] = base["paper_world_uuid"]
    elif fault == "forged_verified":
        base["actual_source_frames_verified"] = False
    elif fault == "no_replay":
        post["model_replay_verified"] = False
    elif fault == "foreign_preload":
        post["preloaded_hypothetical_fatigue"] = 0.1
    elif fault == "swap_case":
        base["case"] = "WAIT_ASSUMED"
    elif fault == "health_shift":
        post["first_native_health"] = 19
    elif fault == "food_shift":
        post["first_native_food"] = 19
    elif fault == "y_shift":
        post["first_before_y"] += 1
    elif fault == "threat_shift":
        post["first_threat_distance_m"] = 3
    elif fault == "no_power_gain":
        post["paper_first_applied_power"] = base["paper_first_applied_power"]
    elif fault == "insufficient_gain":
        post["paper_first_applied_power"] = .8
    elif fault == "power_above_one":
        post["paper_first_applied_power"] = 2
    elif fault == "invalid_distance":
        post["first_native_distance_m"] = float("nan")
    else:
        post["paper_mean_boost_sampled_speed_mps"] = float("nan")
    with pytest.raises(P1DashPairRejected):
        compare_p1_pair_dev(base, post)


def _model_log(initial):
    sid, aid = "pair-dev-sid", "pair-dev-action"
    cfg = FatigueProfile(enabled=True, initial=initial)
    state = initial_state(cfg, sid)
    previous = 0.
    lines = []
    for i in range(1, 14):
        next_ = advance_gait_dev(
            cfg, state, GaitTickDev(sid, i, "DASH" if previous > 0 else "RUN",
                                    "forward", previous, 1. if previous else None)
        )
        output = p1_motor_power_limit_dev(cfg, next_.after, 1., 1.) if i >= 3 else 0.
        lines.append(
            f"S49_DASH_DEV_TICK action_id={aid} session_id={sid} tick={200+i}"
            f" p1_world_ticks={i} p1_motor_dev=true"
            f" p1_before={state.fatigue} p1_after={next_.after.fatigue}"
            f" p1_prev_applied_power={previous} p1_current_applied_power={output}"
            f" modifier_applied={'true' if output else 'false'}"
        )
        state, previous = next_.after, output
    return "\n".join(lines)


@pytest.mark.parametrize("case", ["CARRY", "WAIT_ASSUMED"])
def test_each_frozen_preloaded_single_p1_state_replays_with_no_authority(case):
    initial = PAIR_FATIGUE[case]
    out = audit_native_paper_p1_dev(
        _model_log(initial), action_id="pair-dev-action",
        session_id="pair-dev-sid", model_initial=initial,
    )
    assert out["fatigue_initial"] == initial
    assert out["world_ticks_replayed"] == 13
    assert out["single_p1_model_replayed"] is True
    assert out["source_qualified"] is False
    assert out["p1_ledger_posted"] is False
    assert out["m0_ledger_posted"] is False
    if case == "CARRY":
        assert 0 < out["last_boost_power"] < out["initial_boost_power"] < 1
    else:
        assert out["initial_boost_power"] == out["last_boost_power"] == 1.


@pytest.mark.parametrize("initial", [0.3, 0.0, 1.0, float("nan"), True])
def test_arbitrary_preload_rejected(initial):
    with pytest.raises(ForwardDashDevRejected):
        audit_native_paper_p1_dev(
            _model_log(PAIR_FATIGUE["CARRY"]),
            action_id="pair-dev-action", session_id="pair-dev-sid",
            model_initial=initial,
        )
