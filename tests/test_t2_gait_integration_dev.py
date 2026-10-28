"""T1u DEV: ONE P1 state, existing four-gait model and original T2 owner."""
from __future__ import annotations

import math
from dataclasses import replace
from types import SimpleNamespace

import pytest

from adapters.mineflayer.t1p_body_runtime_dev import run_body_loop_dev
from adapters.mineflayer.t2_tick_accounting import TickAccounting
from experiments.fatigue_p1 import FatigueProfile, initial_state
from experiments.p1_gait_dev import GaitTickDev, advance_gait_dev
from experiments.p1_physiology_profile_dev import calibrated_walk_profile_dev
from test_t1f_t2_dev import frame


def source_for_original_back(frame_now, previous, wait):
    """DEV fixture contract: never infer a gait from the requested Action only.

    A native Paper back-input source with old/new control phases MOVING and
    measured motion is sufficient for *one known* original JOG/back tick.
    Any other non-WAIT evidence is unknown; refusing it is intentional.
    """
    current, earlier = frame_now.data["snapshot"], previous.data["snapshot"]
    assert current["world_tick"] == earlier["world_tick"] + 1
    if wait:
        return GaitTickDev(frame_now.session_id, current["world_tick"], "WAIT")
    if (current["input"] == 2 and frame_now.data["control"]["phase"] == "MOVING"
            and current["motion_blocks"] > earlier["motion_blocks"]):
        return GaitTickDev(
            frame_now.session_id, current["world_tick"], "JOG", direction="back")
    raise ValueError("unproven applied gait, no WAIT or invented WALK")


def test_legacy_t1s_default_unchanged_with_single_p1_owner():
    owner = TickAccounting("test-session")
    owner.observe(frame(1))
    owner.begin("a")
    owner.observe(frame(2, control="MOVING", bits=2, x=.5))
    assert owner.gait_source is None
    assert owner.rows[0]["p1"]["accumulated"] == pytest.approx(.02)
    assert owner.rows[0]["p1"]["recovered"] == 0
    assert owner.rows[0]["motor_mode"] == "WALK"  # legacy label retained
    assert "p1_transition" not in owner.rows[0]
    assert owner.energy.body.tick == 1


def test_existing_gait_model_adopted_once_on_admitted_world_tick():
    calls = []

    def classifier(current, prior, wait):
        calls.append((current.seq, prior.seq, wait))
        return source_for_original_back(current, prior, wait)

    owner = TickAccounting("test-session", gait_source=classifier)
    owner.observe(frame(1))
    assert calls == []  # unaccounted anchor cannot produce a P1 tick
    owner.begin("issued-one")
    new = frame(2, control="MOVING", bits=2, x=.5)
    owner.observe(new)
    assert calls == [(20, 10, False)]
    row = owner.rows[0]
    assert len(owner.rows) == owner.energy.body.tick == 1
    assert owner.fatigue.world_tick == row["world_tick"]
    assert row["source_seq"] == new.seq
    assert row["motor_mode"] == row["applied_gait"] == "JOG"
    assert row["applied_direction"] == "back"
    assert row["p1_transition"] == "SINGLE_P1_APPLIED_GAIT_DEV"
    assert row["gait_source_authenticated_R"] is False
    assert row["p1_gait_extra_m0_posted"] is False
    expected = advance_gait_dev(
        owner.profile,
        initial_state(owner.profile, "test-session", world_tick=201),
        GaitTickDev("test-session", 202, "JOG", direction="back"),
    )
    assert owner.fatigue == expected.after
    assert row["p1"]["accumulated"] == pytest.approx(expected.accumulated)
    assert row["p1"]["recovered"] == pytest.approx(expected.recovered)
    assert owner.energy.body.tick == 1
    assert row["m0_move"] == pytest.approx(.001)


def test_owner_refuses_unknown_residual_motion_instead_of_fake_wait():
    owner = TickAccounting("test-session", gait_source=source_for_original_back)
    owner.observe(frame(1))
    owner.begin("original-action")
    owner.observe(frame(2, control="MOVING", bits=2, x=.5))
    residual = frame(3, control="CLEARED", bits=0, x=.5)
    with pytest.raises(ValueError, match="unproven applied gait"):
        owner.observe(residual)
    assert owner.failed
    assert len(owner.rows) == 1
    with pytest.raises(ValueError, match="prior motor/action not closed"):
        owner.begin("second-action")


@pytest.mark.parametrize("falsify", [
    lambda f, p, w: GaitTickDev(f.session_id, f.data["snapshot"]["world_tick"], "WAIT"),
    lambda f, p, w: GaitTickDev("foreign", f.data["snapshot"]["world_tick"], "JOG"),
    lambda f, p, w: GaitTickDev(f.session_id, f.data["snapshot"]["world_tick"] + 1, "JOG"),
    lambda f, p, w: None,
])
def test_unauthorized_wait_foreign_gait_and_missing_gait_all_latch(falsify):
    owner = TickAccounting("test-session", gait_source=falsify)
    owner.observe(frame(1))
    owner.begin("a")
    with pytest.raises(ValueError):
        owner.observe(frame(2, control="MOVING", bits=2, x=.5))
    assert owner.failed
    assert owner.rows == []


def test_real_causal_wait_cannot_be_labeled_jog():
    owner = TickAccounting("test-session", gait_source=lambda f, p, w:
                           GaitTickDev(f.session_id, f.data["snapshot"]["world_tick"], "JOG"))
    owner.observe(frame(1))
    # A real original close happened before the observation; first cleared
    # boundary tick can be unknown, so explicit second source is needed.
    owner.clear_seq = 10
    owner.terminal_seq = 10
    owner.previous = frame(3, seq=30)
    owner.fatigue = replace(owner.fatigue, world_tick=203)
    with pytest.raises(ValueError, match="disagrees with WAIT_DEV"):
        owner.observe(frame(4, seq=40))
    assert owner.failed


def test_unposted_dash_energy_must_not_create_a_free_motor_budget():
    owner = TickAccounting("test-session", gait_source=lambda f, p, w:
                           GaitTickDev(
                               f.session_id, f.data["snapshot"]["world_tick"],
                               "DASH", direction="forward",
                               applied_dash_power=1.0,
                               available_extra_m0_energy=1.0,
                           ))
    owner.observe(frame(1))
    owner.begin("a")
    before_energy = owner.energy.body
    with pytest.raises(ValueError, match="extra M0"):
        owner.observe(frame(2, control="MOVING", bits=2, x=.5))
    assert owner.failed
    assert owner.energy.body == before_energy
    assert not owner.rows


def test_no_double_recovery_legacy_tau_and_gait_prohibited():
    with pytest.raises(ValueError, match="non-tau"):
        TickAccounting(
            "test-session", fatigue_profile=calibrated_walk_profile_dev(),
            gait_source=source_for_original_back,
        )
    with pytest.raises(TypeError):
        TickAccounting("test-session", gait_source=5)
    with pytest.raises(ValueError):
        TickAccounting("test-session", fatigue_profile=FatigueProfile(),
                       gait_source=source_for_original_back)


def test_original_runner_can_receive_gait_source_without_any_new_issuer():
    import inspect

    sig = inspect.signature(run_body_loop_dev)
    assert sig.parameters["gait_source"].default is None
    assert sig.parameters["fatigue_profile"].default is None
    assert sig.parameters["l0_decider"].default is None


def test_steady_gait_model_reuses_existing_tested_recovery_law():
    p = FatigueProfile(enabled=True, initial=.5)
    state = initial_state(p, "s")
    state = advance_gait_dev(
        p, state, GaitTickDev("s", 1, "WALK")).after
    assert state.fatigue < .5
    while state.world_tick < 20:
        state = advance_gait_dev(
            p, state, GaitTickDev("s", state.world_tick + 1, "WALK")).after
    assert state.fatigue == pytest.approx(.5 * math.exp(-.1), rel=1e-9)
