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
    owner.permit_g3_dash_action_dev("g3-original-s49-action")
    owner.begin("g3-original-s49-action")
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


def test_g3_unscoped_doublespeed_stays_unbilled_while_t2_advances(monkeypatch):
    monkeypatch.setenv("S49_L1_G3_T2_DEV_ONLY","1")
    owner=TickAccounting(
        SID,gait_source=applied_gait_from_original_t1u_dev,g3_partial_dev=True,
    )
    first=native_frame(monkeypatch,1,x=0.)
    second=native_frame(monkeypatch,2,x=.20)
    owner.observe(first)
    owner.observe(second)
    assert len(owner.rows)==1
    assert owner.rows[-1]["g3_unknown_fallback_dev"] is True
    assert owner.rows[-1]["g3_extra_m0_paid_dev"]==0
    assert owner.rows[-1]["g3_dash_source_action_scope_dev"] is None
    assert owner.g3_dash_scoped_fallback_ticks_dev==1
    assert owner.energy.body.tick==1 and owner.fatigue.world_tick==2
    assert owner.failed is False


def test_g3_foreign_and_closed_s49_does_not_bill_dash(monkeypatch):
    monkeypatch.setenv("S49_L1_G3_T2_DEV_ONLY","1")
    owner=TickAccounting(
        SID,gait_source=applied_gait_from_original_t1u_dev,g3_partial_dev=True,
    )
    owner.observe(native_frame(monkeypatch,1,x=0.))
    owner.permit_g3_dash_action_dev("paper-armed-A")
    with pytest.raises(ValueError,match="G3_DASH_ACTION_SCOPE_REFUSED"):
        owner.permit_g3_dash_action_dev("paper-armed-B")
    owner.begin("unrelated-B")
    owner.observe(native_frame(monkeypatch,2,x=.20))
    assert owner.rows[-1]["g3_extra_m0_paid_dev"]==0
    owner.active_action=None  # simulate closed S49 without issuing a new motor
    owner.observe(native_frame(monkeypatch,3,x=.43))
    assert owner.rows[-1]["g3_extra_m0_paid_dev"]==0
    assert owner.g3_dash_scoped_fallback_ticks_dev==2
    assert owner.g3_dash_energy_total_dev==0


def test_g3_paper_dash_accounting_scope_requires_initialized_t2(monkeypatch):
    monkeypatch.setenv("S49_L1_G3_T2_DEV_ONLY","1")
    owner=TickAccounting(
        SID,gait_source=applied_gait_from_original_t1u_dev,g3_partial_dev=True,
    )
    with pytest.raises(ValueError,match="G3_DASH_ACTION_SCOPE_REFUSED"):
        owner.permit_g3_dash_action_dev("paper-armed-A")
    assert owner.g3_dash_approved_action_dev is None


def test_g3_scope_cannot_be_enabled_in_default_t2(monkeypatch):
    owner=TickAccounting(SID)
    with pytest.raises(ValueError,match="G3_DASH_ACTION_SCOPE_REFUSED"):
        owner.permit_g3_dash_action_dev("some-action")


def _set_paper_modifier_identity(frame, *, dash_key="relays49dashdev:forward_dash_only",
                                 dash_amount=.5, operation="MULTIPLY_SCALAR_1"):
    gait=frame.data["snapshot"]["gait_dev"]
    modifiers=[{
        "key":"minecraft:sprinting","operation":"MULTIPLY_SCALAR_1",
        "amount":.3,
    }, {
        "key":dash_key,"operation":operation,"amount":dash_amount,
    }]
    gait["speed_modifier_details"]=sorted(modifiers,key=lambda m:m["key"])
    return frame


def test_g3_strict_identity_charges_only_exact_paper_key_and_power(monkeypatch):
    from functools import partial

    monkeypatch.setenv("S49_L1_G3_T2_DEV_ONLY","1")
    owner=TickAccounting(
        SID,gait_source=partial(applied_gait_from_original_t1u_dev,
                                strict_modifier_identity_dev=True),
        g3_partial_dev=True,
    )
    first=_set_paper_modifier_identity(native_frame(monkeypatch,1,x=0.))
    second=_set_paper_modifier_identity(native_frame(monkeypatch,2,x=.21))
    owner.observe(first)
    owner.permit_g3_dash_action_dev("source-paper-arm")
    owner.begin("source-paper-arm")
    owner.observe(second)
    assert owner.rows[-1]["motor_mode"]=="DASH"
    assert owner.rows[-1]["g3_dash_source_action_scope_dev"]=="source-paper-arm"
    assert owner.rows[-1]["g3_extra_m0_paid_dev"]==pytest.approx(.01)
    assert owner.g3_dash_energy_total_dev==pytest.approx(.01)


@pytest.mark.parametrize("bad_key,bad_amount,bad_op", [
    ("foreign:fake_dash", .5, "MULTIPLY_SCALAR_1"),
    ("relays49dashdev:forward_dash_only", .4, "MULTIPLY_SCALAR_1"),
    ("relays49dashdev:forward_dash_only", .5, "ADD_SCALAR"),
])
def test_g3_strict_identity_rejects_same_speed_lookalike_without_debit(
    monkeypatch,bad_key,bad_amount,bad_op,
):
    from functools import partial

    monkeypatch.setenv("S49_L1_G3_T2_DEV_ONLY","1")
    owner=TickAccounting(
        SID,gait_source=partial(applied_gait_from_original_t1u_dev,
                                strict_modifier_identity_dev=True),
        g3_partial_dev=True,
    )
    first=_set_paper_modifier_identity(
        native_frame(monkeypatch,1,x=0.),dash_key=bad_key,
        dash_amount=bad_amount,operation=bad_op)
    second=_set_paper_modifier_identity(
        native_frame(monkeypatch,2,x=.22),dash_key=bad_key,
        dash_amount=bad_amount,operation=bad_op)
    owner.observe(first)
    owner.permit_g3_dash_action_dev("paper-arm")
    owner.begin("paper-arm")
    owner.observe(second)
    assert owner.rows[-1]["g3_unknown_fallback_dev"] is True
    assert owner.rows[-1]["g3_extra_m0_paid_dev"]==0
    assert owner.energy.body.tick==1
    assert owner.failed is False


def test_g3_strict_identity_absent_fails_closed_while_legacy_remains_dev(monkeypatch):
    from functools import partial

    monkeypatch.setenv("S49_L1_G3_T2_DEV_ONLY","1")
    owner=TickAccounting(
        SID,gait_source=partial(applied_gait_from_original_t1u_dev,
                                strict_modifier_identity_dev=True),
        g3_partial_dev=True)
    owner.observe(native_frame(monkeypatch,1,x=0.))
    owner.permit_g3_dash_action_dev("paper-arm")
    owner.begin("paper-arm")
    owner.observe(native_frame(monkeypatch,2,x=.25))
    assert owner.g3_dash_energy_total_dev==0
    assert owner.rows[-1]["g3_unknown_fallback_dev"]
    assert owner.energy.body.tick==1


def test_g3_exact_identity_rejects_wrong_vanilla_sprint_amount(monkeypatch):
    from functools import partial

    monkeypatch.setenv("S49_L1_G3_T2_DEV_ONLY","1")
    owner=TickAccounting(SID,gait_source=partial(
        applied_gait_from_original_t1u_dev,strict_modifier_identity_dev=True),
        g3_partial_dev=True)
    first=_set_paper_modifier_identity(native_frame(monkeypatch,1,x=0.))
    second=_set_paper_modifier_identity(native_frame(monkeypatch,2,x=.20))
    for frame in (first,second):
        details=frame.data["snapshot"]["gait_dev"]["speed_modifier_details"]
        assert details[0]["key"]=="minecraft:sprinting"
        details[0]["amount"]=.29
    owner.observe(first)
    owner.permit_g3_dash_action_dev("original-paper-arm")
    owner.begin("original-paper-arm")
    owner.observe(second)
    assert owner.failed is False and owner.energy.body.tick==1
    assert owner.fatigue.world_tick==2
    assert owner.rows[-1]["g3_unknown_fallback_dev"]
    assert owner.rows[-1]["g3_extra_m0_paid_dev"]==0
    assert owner.g3_dash_energy_total_dev==0


def test_g3_exact_identity_requires_same_modifier_on_adjacent_paper_ticks(
    monkeypatch,
):
    from functools import partial

    monkeypatch.setenv("S49_L1_G3_T2_DEV_ONLY","1")
    owner=TickAccounting(SID,gait_source=partial(
        applied_gait_from_original_t1u_dev,strict_modifier_identity_dev=True),
        g3_partial_dev=True)
    first=_set_paper_modifier_identity(native_frame(monkeypatch,1,x=0.))
    second=_set_paper_modifier_identity(native_frame(monkeypatch,2,x=.21))
    # Both Paper frames have the same effective 0.195 speed, but the
    # first has a different modifier. Never mistake a transition for
    # a stable and payable observed DASH WorldTick.
    first.data["snapshot"]["gait_dev"]["speed_modifier_details"][1]["amount"]=.4
    owner.observe(first)
    owner.permit_g3_dash_action_dev("original-paper-arm")
    owner.begin("original-paper-arm")
    owner.observe(second)
    assert owner.failed is False and owner.energy.body.tick==1
    assert owner.rows[-1]["g3_unknown_fallback_dev"] is True
    assert owner.rows[-1]["g3_extra_m0_paid_dev"]==0
    assert owner.g3_dash_energy_total_dev==0
