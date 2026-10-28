"""T1v DEV: physically idle WorldBody != causal Action WAIT."""
from __future__ import annotations

import copy

import pytest

from adapters.mineflayer.python_protocol import MineflayerPaperSnapshot
from adapters.mineflayer.t1p_body_runtime_dev import decide_l0
from adapters.mineflayer.t1u_gait_source_dev import applied_gait_source_dev
from adapters.mineflayer.t1v_physical_idle_dev import (
    applied_gait_or_physical_idle_dev,
    physical_idle_witness_dev,
)
from adapters.mineflayer.t2_tick_accounting import TickAccounting
from experiments.fatigue_p1 import FatigueProfile
from experiments.p1_gait_dev import GaitTickDev
from test_t1u_gait_source_dev import witness


def changed(source, mutate):
    data = copy.deepcopy(source.data)
    mutate(data)
    return MineflayerPaperSnapshot(source.session_id, source.seq, data)


def test_initial_quiet_world_is_physical_rest_without_control_plane_wait():
    a = witness(1, control="INITIAL")
    b = witness(2, control="INITIAL")
    assert physical_idle_witness_dev(b, a)
    with pytest.raises(ValueError, match="NATIVE_GAIT_NOT_ATTESTED"):
        applied_gait_source_dev(b, a, False)
    supplied = applied_gait_or_physical_idle_dev(b, a, False)
    assert supplied.gait == "WAIT" and supplied.world_tick == 202

    profile = FatigueProfile(enabled=True, initial=.6)
    owner = TickAccounting(a.session_id, fatigue_profile=profile,
                           gait_source=applied_gait_or_physical_idle_dev)
    owner.observe(a)  # source anchor is never charged
    owner.observe(b)
    assert len(owner.rows) == owner.energy.body.tick == 1
    assert owner.fatigue.world_tick == 202
    assert 0 < owner.rows[0]["p1"]["recovered"] < .01
    assert owner.fatigue.fatigue < .6
    assert owner.rows[0]["p1_transition"] == "SINGLE_P1_APPLIED_GAIT_DEV"
    assert owner.rows[0]["activity"] == "PHYSICAL_IDLE_DEV"
    assert owner.rows[0]["physical_idle_model_only"] is True
    assert owner.rows[0]["gait_physical_idle_without_action_wait"] is True
    assert owner.rows[0]["wait_causal_clear"] is False
    assert owner.rows[0]["qualified_physical_wait"] is False
    assert owner.rows[0]["full_tick_R_attested"] is False
    assert decide_l0(b, owner, completed=0, limit=2) == "MOVE"


def test_original_owner_causal_wait_is_not_renamed_to_initial_idle():
    a, b = witness(1, control="CLEARED"), witness(2, control="CLEARED")
    owner = TickAccounting(a.session_id, gait_source=applied_gait_or_physical_idle_dev)
    owner.observe(a)
    owner.clear_seq = owner.terminal_seq = 1
    owner.observe(b)
    assert owner.rows[0]["activity"] == "WAIT_DEV"
    assert owner.rows[0]["physical_idle_model_only"] is False
    assert owner.rows[0]["wait_causal_clear"] is True


@pytest.mark.parametrize("mutate", [
    lambda d: d["snapshot"].update(input=2),
    lambda d: d["snapshot"].update(x=.001),
    lambda d: d["snapshot"].update(motion_blocks=.001),
    lambda d: d["applied_controls_dev"].update(back=True),
    lambda d: d["snapshot"]["gait_dev"].update(sneaking=True),
    lambda d: d["snapshot"]["gait_dev"].update(sprinting=True),
    lambda d: d["snapshot"]["gait_dev"].update(speed_value=.15, speed_modifiers=1),
    lambda d: d["control"].update(phase="MOVING"),
    lambda d: d["control"].update(generation=3),
])
def test_initial_physical_rest_rejects_motion_controls_attributes_and_edges(mutate):
    a, b = witness(1, control="INITIAL"), witness(2, control="INITIAL")
    b = changed(b, mutate)
    assert not physical_idle_witness_dev(b, a)
    with pytest.raises(ValueError, match="NATIVE_GAIT_NOT_ATTESTED"):
        applied_gait_or_physical_idle_dev(b, a, False)


def test_missing_applied_source_cannot_mint_preaction_rest():
    a, b = witness(1, control="INITIAL"), witness(2, control="INITIAL")
    a = changed(a, lambda d: d.pop("applied_controls_dev"))
    assert not physical_idle_witness_dev(b, a)
    with pytest.raises(ValueError):
        applied_gait_or_physical_idle_dev(b, a, False)


def test_initial_idle_then_unproven_onset_is_still_latched():
    a, b = witness(1, control="INITIAL"), witness(2, control="INITIAL")
    owner = TickAccounting(a.session_id, gait_source=applied_gait_or_physical_idle_dev)
    owner.observe(a)
    owner.observe(b)
    assert owner.rows[0]["activity"] == "PHYSICAL_IDLE_DEV"
    before = owner.fatigue
    energy_before = owner.energy.body
    owner.begin("a")
    onset = witness(3, control="MOVING", bits=2, x=.4)
    with pytest.raises(ValueError, match="NATIVE_GAIT_NOT_ATTESTED"):
        owner.observe(onset)
    assert owner.failed
    assert owner.gait_refusal["world_tick"] == 203
    assert owner.gait_refusal["p1_updated"] is False
    assert owner.fatigue == before
    assert owner.energy.body == energy_before
    assert len(owner.rows) == 1
    with pytest.raises(ValueError):
        owner.begin("next-action")


def test_forged_wait_cannot_bypass_physical_idle_gate():
    owner = TickAccounting("test-session",
                           gait_source=lambda frame, p, wait:
                           GaitTickDev(frame.session_id, frame.data["snapshot"]["world_tick"],
                                       "WAIT"))
    owner.observe(witness(1, control="MOVING", bits=2, x=.1))
    with pytest.raises(ValueError, match="unproven body rest"):
        owner.observe(witness(2, control="MOVING", bits=2, x=.4))
    assert owner.failed and not owner.rows


def test_new_case_registered_without_changing_prior_t1u():
    from adapters.mineflayer.t1e_native_dev import TICK_CASES
    assert "t1u_gait_body_loop" in TICK_CASES
    assert "t1u_gait_witness_loop" in TICK_CASES
    assert "t1v_physical_idle_loop" in TICK_CASES


def test_refusal_tail_observes_coasting_without_advancing_or_reauthorizing():
    import asyncio
    from dataclasses import asdict
    from types import SimpleNamespace

    from adapters.mineflayer.t1v_physical_idle_dev import observe_refused_boundary_tail_dev

    owner = TickAccounting("test-session", gait_source=applied_gait_or_physical_idle_dev)
    owner.observe(witness(1, control="INITIAL"))
    owner.observe(witness(2, control="INITIAL"))
    with pytest.raises(ValueError):
        owner.observe(witness(3, control="MOVING", bits=2, x=.1))
    owner.clear_seq = 30
    frozen = (asdict(owner.fatigue), asdict(owner.energy.body), len(owner.rows))

    class Session:
        tick_owner = owner
        started = SimpleNamespace(session_id=owner.session_id)
        consume_tick_accounting = True
        source_lost = False
        received = 0

        async def receive(self):
            self.received += 1
            f = witness(4 + self.received, control="CLEARED", x=.1 + .001*self.received)
            assert not self.consume_tick_accounting
            return f

    session = Session()
    tail = asyncio.run(observe_refused_boundary_tail_dev(session, ticks=3))
    assert len(tail["frames"]) == session.received == 3
    assert tail["p1_current"] == "UNKNOWN_AFTER_REFUSED_TICK"
    assert frozen == (asdict(owner.fatigue), asdict(owner.energy.body), len(owner.rows))
    with pytest.raises(ValueError):
        owner.begin("forbidden-next-action")


def test_refusal_tail_cannot_disable_healthy_accounting():
    import asyncio

    from adapters.mineflayer.t1v_physical_idle_dev import observe_refused_boundary_tail_dev

    class Session:
        tick_owner = TickAccounting("test-session")
        consume_tick_accounting = True

    session = Session()
    with pytest.raises(ValueError, match="latched refusal"):
        asyncio.run(observe_refused_boundary_tail_dev(session))
    assert session.consume_tick_accounting
