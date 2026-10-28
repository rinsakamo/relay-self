"""G3 one original T2 P1/M0 owner; no duplicate Dash tick or false WAIT."""
from __future__ import annotations

import pytest

from adapters.mineflayer.b0_energy_bridge import B0EnergyLedger, B0EnergyRejected
from adapters.mineflayer.g3_applied_gait_source_dev import applied_gait_from_original_t1u_dev
from adapters.mineflayer.t2_tick_accounting import TickAccounting
from test_s49_t2_applied_gait_observation_dev import SID, _controls, _frame


def native_frame(monkeypatch, tick, *, x, mode="DASH", generation=1):
    config = {
        "DASH": (_controls("forward","sprint"), True, False, 2, .195),
        "RUN": (_controls("forward","sprint"), True, False, 1, .13),
        "JOG": (_controls("forward"), False, False, 0, .1),
        "WALK": (_controls("forward","sneak"), False, True, 0, .1),
        "BLOCKED": (_controls("forward","sprint"), True, False, 2, .195),
    }
    c, sprint, sneak, mods, value = config[mode]
    m = _frame(
        monkeypatch, tick, x=x, blocks=x, controls=c,
        sprint=sprint, sneak=sneak, mods=mods, value=value,
        generation=generation,
    )
    s = m.data["snapshot"]
    s.update(basal_ticks=tick, basal_exhaustion=0., motion_exhaustion=0.,
             threats=[])
    m.data.update(challenge_sent_ns="100", evaluation_start_ns="101",
                  evaluation_completed_ns="102")
    m.data["control"]["since_ns"]="0"
    return m


def test_g3_not_default_on(monkeypatch):
    monkeypatch.delenv("S49_L1_G3_T2_DEV_ONLY", raising=False)
    with pytest.raises(ValueError,match="explicit opt-in"):
        TickAccounting(SID,gait_source=applied_gait_from_original_t1u_dev,
                       g3_partial_dev=True)
    assert TickAccounting(SID).gait_source is None


def test_g3_one_world_tick_one_p1_one_atomic_m0_dash(monkeypatch):
    monkeypatch.setenv("S49_L1_G3_T2_DEV_ONLY","1")
    owner=TickAccounting(
        SID,gait_source=applied_gait_from_original_t1u_dev,g3_partial_dev=True,
    )
    first=native_frame(monkeypatch, 1, x=0.)
    second=native_frame(monkeypatch, 2, x=.20)
    third=native_frame(monkeypatch, 3, x=.43)
    assert owner.observe(first) is None
    initial=owner.energy.body.energy
    owner.observe(second)
    assert len(owner.rows)==1 and owner.rows[-1]["motor_mode"]=="DASH"
    assert owner.rows[-1]["g3_extra_m0_paid_dev"]==pytest.approx(.01)
    assert owner.rows[-1]["p1_gait_extra_m0_posted"] is True
    assert owner.rows[-1]["m0"]["expenditure"]==pytest.approx(.0011+.0004+.01)
    assert owner.energy.body.tick==1 and owner.fatigue.world_tick==2
    owner.observe(third)
    assert len(owner.rows)==2 and owner.energy.body.tick==2
    assert owner.g3_dash_energy_total_dev==pytest.approx(.02)
    assert owner.energy.body.energy==pytest.approx(
        initial-sum(row["m0"]["expenditure"] for row in owner.rows)
    )
    assert owner.g3_applied_gait_ticks_dev==2
    assert owner.g3_unknown_fallback_ticks_dev==0
    assert all(r["full_tick_R_attested"] is False for r in owner.rows)
    with pytest.raises(ValueError,match="nonconsecutive"):
        owner.observe(third)
    assert owner.failed and owner.energy.body.tick==2


def test_g3_source_transition_and_blocked_do_not_post_dash_or_wait(monkeypatch):
    monkeypatch.setenv("S49_L1_G3_T2_DEV_ONLY","1")
    owner=TickAccounting(
        SID,gait_source=applied_gait_from_original_t1u_dev,g3_partial_dev=True,
    )
    for frame in [
        native_frame(monkeypatch,1,x=0.,mode="JOG"),
        native_frame(monkeypatch,2,x=.14,mode="DASH"),
        native_frame(monkeypatch,3,x=.14,mode="BLOCKED"),
        native_frame(monkeypatch,4,x=.31,mode="RUN"),
    ]:
        owner.observe(frame)
    assert owner.g3_applied_gait_ticks_dev==0
    assert owner.g3_unknown_fallback_ticks_dev==3
    assert owner.g3_dash_energy_total_dev==0
    assert all(r["activity"]!="WAIT_DEV" for r in owner.rows)
    assert all(r["g3_extra_m0_paid_dev"]==0 for r in owner.rows)
    assert owner.energy.body.tick==3 and owner.fatigue.world_tick==4


@pytest.mark.parametrize("extra", [0., -.1, float("nan"), .1, True])
def test_m0_g3_invalid_dash_source_never_mutates_original_owner(extra):
    ledger=B0EnergyLedger(SID)
    before=ledger.body
    with pytest.raises(B0EnergyRejected):
        ledger.post_g3_observed_dash_tick_dev(world_tick=5,extra=extra)
    assert ledger.body==before


def test_m0_g3_replay_denied_with_original_balance_unchanged():
    ledger=B0EnergyLedger(SID)
    first=ledger.post_g3_observed_dash_tick_dev(world_tick=5,extra=.01)
    assert first.after.tick==1 and first.expenditure> .01
    before=ledger.body
    with pytest.raises(B0EnergyRejected,match="replay refused"):
        ledger.post_g3_observed_dash_tick_dev(world_tick=5,extra=.01)
    assert ledger.body==before
