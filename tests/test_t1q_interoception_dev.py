"""T1q SelfBody: source-bound, fallible interoception; no new Action issuer."""
from __future__ import annotations

from dataclasses import replace

import pytest

from adapters.mineflayer.t1q_interoception_dev import (
    T1qRejected,
    cognition_summary,
    decide_sensed_l0,
    project_t1q_selfbody,
)
from adapters.mineflayer.t2_tick_accounting import TickAccounting
from relay_self.self_body import BodyOrigin, compose_self_body_view
from test_t1f_t2_dev import frame


def ready(i=1):
    f = frame(i, seq=i * 10)
    owner = TickAccounting("test-session")
    owner.observe(f)
    return f, owner


def test_reuse_original_selfbody_typed_view_not_truth():
    f, owner = ready()
    view = project_t1q_selfbody(f, owner, epoch_id="e0")
    assert view.session_id == "test-session"
    assert view.epoch_id == "e0"
    assert view.observed("health").value == 20
    assert view.observed("food").value == 20
    assert view.sensed("m0_energy_sensor").origin is BodyOrigin.INTEROCEPTION
    assert view.sensed("p1_fatigue_sensor").origin is BodyOrigin.INTEROCEPTION
    assert view.sensed("m0_energy_sensor").value == 12.0
    assert view.sensed("p1_fatigue_sensor").value == 0.0
    assert view.observed("m0_energy_sensor").origin is BodyOrigin.UNKNOWN
    assert view.observed("p1_fatigue_sensor").origin is BodyOrigin.UNKNOWN
    assert view.observed("can_fly").origin is BodyOrigin.UNKNOWN
    assert decide_sensed_l0(view, host_decision="MOVE") == "MOVE"
    assert view.observation.source_ref in view.sensed("m0_energy_sensor").source_refs
    assert len(view.sensed("m0_energy_sensor").provenance) == 2


def test_sensor_masks_true_energy_and_can_change_decision():
    f, owner = ready()
    owner.energy.body = replace(owner.energy.body, energy=2.13)
    view = project_t1q_selfbody(f, owner, epoch_id="low-energy")
    assert view.sensed("m0_energy_sensor").value == 2.25
    assert view.observed("m0_energy_sensor").value is None
    assert decide_sensed_l0(view, host_decision="MOVE") == "HALT"
    # Host guard must not be overturned even when cognition suggests MOVE.
    assert decide_sensed_l0(view, host_decision="HALT") == "HALT"


def test_fatigue_sensor_can_hold_after_real_model_state_change():
    f, owner = ready()
    owner.fatigue = replace(owner.fatigue, fatigue=0.064)
    view = project_t1q_selfbody(f, owner, epoch_id="higher-fatigue")
    assert view.sensed("p1_fatigue_sensor").value == 0.06
    assert decide_sensed_l0(view, host_decision="MOVE") == "HOLD_BODY"
    assert decide_sensed_l0(view, host_decision="HALT") == "HALT"


def test_unknown_selfbody_does_not_turn_into_fake_sensor_or_permission():
    missing = compose_self_body_view(session_id="test-session", epoch_id="blank")
    assert missing.sensed("m0_energy_sensor").origin is BodyOrigin.UNKNOWN
    assert missing.sensed("p1_fatigue_sensor").origin is BodyOrigin.UNKNOWN
    assert decide_sensed_l0(missing, host_decision="MOVE") == "HALT"
    assert decide_sensed_l0(missing, host_decision="COMPLETE") == "COMPLETE"


def test_projection_preserves_two_distinct_time_domains_and_only_sensors():
    f, owner = ready()
    view = project_t1q_selfbody(f, owner, epoch_id="one")
    row = cognition_summary(view, native_seq=f.seq, world_tick=201,
                            host_decision="MOVE", sensed_decision="MOVE")
    assert row["world_tick"] == 201
    assert row["m0_clock_kind"] == "B0_LEDGER_TICKS"
    assert row["paper_clock_kind"] == "WORLD_FULL_TIME"
    assert row["physical_permission_from_view"] is False
    assert row["p1_qualified_wait"] is False
    for key in ("true_energy", "true_fatigue", "physical_motor_permit",
                "energy_after", "fatigue_after"):
        assert key not in row


@pytest.mark.parametrize("change", [
    lambda f, o: setattr(o, "failed", True),
    lambda f, o: setattr(o, "previous", None),
    lambda f, o: setattr(o, "active_action", "still-moving"),
    lambda f, o: setattr(o, "pending_meal", "unverified-food"),
    lambda f, o: setattr(o, "fatigue", replace(o.fatigue, world_tick=999)),
    lambda f, o: setattr(o, "session_id", "foreign"),
    lambda f, o: f.data.update(status="STALE"),
    lambda f, o: f.data["snapshot"].update(threats_complete=False),
    lambda f, o: setattr(o.energy, "body", replace(o.energy.body, tick=3)),
])
def test_inconsistent_world_body_or_native_never_projects(change):
    f, owner = ready()
    change(f, owner)
    with pytest.raises(T1qRejected):
        project_t1q_selfbody(f, owner, epoch_id="e0")


def test_stale_frame_cannot_piggyback_current_owner():
    old, owner = ready()
    next_frame = frame(2, seq=20)
    owner.observe(next_frame)
    with pytest.raises(T1qRejected):
        project_t1q_selfbody(old, owner, epoch_id="old")
    view = project_t1q_selfbody(next_frame, owner, epoch_id="current")
    assert view.sensed("m0_energy_sensor").value <= 12.0


def test_quantized_energy_can_disagree_with_exact_host_state():
    f, owner = ready()
    owner.energy.body = replace(owner.energy.body, energy=11.89)
    view = project_t1q_selfbody(f, owner, epoch_id="quantized")
    assert view.sensed("m0_energy_sensor").value == 12.0
    assert owner.energy.body.energy == 11.89
    assert view.observed("m0_energy_sensor").origin is BodyOrigin.UNKNOWN


def test_t1q_wrapper_injects_one_read_only_policy_into_original_loop(monkeypatch):
    import asyncio
    from types import SimpleNamespace
    import adapters.mineflayer.t1q_interoception_dev as mod
    from test_t1f_t2_dev import release

    calls = []

    async def fake_original_loop(session, report, *, move_limit, l0_decider):
        calls.append("original_t1p_owner")
        first, owner = ready()
        assert l0_decider(first, owner, completed=0, limit=move_limit) == "MOVE"
        release(owner, seq=1)
        second = frame(2, seq=20)
        owner.observe(second)
        assert l0_decider(second, owner, completed=1, limit=move_limit) == "MOVE"
        report["t1p"] = {"completed_moves": 2}
        report["status"] = "PASS"

    monkeypatch.setattr(mod, "run_body_loop_dev", fake_original_loop)
    report = {}
    asyncio.run(mod.run_t1q_body_loop_dev(SimpleNamespace(), report, move_limit=2))
    assert calls == ["original_t1p_owner"]
    assert report["t1q"]["decision_count"] == 2
    assert report["t1q"]["additional_native_reads"] == 0
    assert report["t1q"]["additional_actions"] == 0
    assert [x["native_seq"] for x in report["t1q"]["readings"]] == [10, 20]
    assert [x["world_tick"] for x in report["t1q"]["readings"]] == [201, 202]



def test_producer_projector_has_no_action_or_receive_side_effect(monkeypatch):
    f, owner = ready()
    import adapters.mineflayer.t1q_interoception_dev as mod

    def no_native(*args, **kwargs):
        raise AssertionError("interoception must never issue native IO")

    monkeypatch.setattr(mod, "run_body_loop_dev", no_native)
    # Only projecting and evaluating; no producer clock increment.
    before_tick = owner.energy.body.tick
    before_fatigue = owner.fatigue
    view = mod.project_t1q_selfbody(f, owner, epoch_id="e0")
    assert mod.decide_sensed_l0(view, host_decision="MOVE") == "MOVE"
    assert owner.energy.body.tick == before_tick
    assert owner.fatigue == before_fatigue
