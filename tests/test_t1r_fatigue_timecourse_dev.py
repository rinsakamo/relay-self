"""T1r: real TickAccounting source to passive SelfBody fatigue timeline."""
from __future__ import annotations

import asyncio
from dataclasses import replace
from types import SimpleNamespace

import pytest

from adapters.mineflayer.t1q_interoception_dev import project_t1q_selfbody
from adapters.mineflayer.t1r_fatigue_timecourse_dev import (
    MAX_PASSIVE_TICKS,
    T1rRejected,
    audit_t1r_trace,
    capture_passive_tick,
    run_t1r_body_recovery_dev,
    sensed_rest_preference,
)
from adapters.mineflayer.t2_tick_accounting import TickAccounting
from relay_self.self_body import BodyOrigin, compose_self_body_view
from test_t1f_t2_dev import frame


def _physical_timeline():
    """Real original T2 advance: one measured MOVE and one causally valid WAIT."""
    owner = TickAccounting("test-session")
    owner.observe(frame(1))
    owner.begin("original-action")
    entries = []
    motor = frame(2, control="MOVING", bits=2, x=.8, seq=20)
    owner.observe(motor)
    capture_passive_tick(motor, owner, entries)

    owner.finish(
        SimpleNamespace(action_id="original-action",
                        cleanup_receipt=SimpleNamespace(
                            result="applied", effect="clear_controls", seq=25),
                        after_observation=None),
        SimpleNamespace(action_id="original-action"),
    )
    # First newly cleared tick is NOT instantly a P1 WAIT entitlement.
    boundary = frame(3, x=.8, seq=30)
    owner.observe(boundary)
    capture_passive_tick(boundary, owner, entries)

    waiting = frame(4, x=.8, seq=40)
    owner.observe(waiting)
    capture_passive_tick(waiting, owner, entries)
    return owner, entries


def test_motion_and_wait_views_capture_real_fatigue_timecourse():
    owner, records = _physical_timeline()
    assert owner.rows[0]["activity"] == "MOVE_OR_UNDETERMINED"
    assert owner.rows[1]["activity"] != "WAIT_DEV"
    assert owner.rows[2]["activity"] == "WAIT_DEV"
    assert owner.rows[0]["p1"]["accumulated"] == pytest.approx(.032)
    assert owner.rows[2]["p1"]["recovered"] == pytest.approx(.032)
    assert [r["fatigue_sensed"] for r in records] == [0.03, 0.03, 0.0]
    assert [r["sensed_rest_preference"] for r in records] == [
        "REST_PREFERRED", "REST_PREFERRED", "READY_FEELING",
    ]
    assert records[0]["original_action_open"] is True
    assert records[-1]["original_action_open"] is False
    assert all(r["physical_permission_from_view"] is False for r in records)
    assert all(r["fatigue_origin"] == "interoception" for r in records)
    assert all("host_audit_true_fatigue" not in r for r in records)
    audit = audit_t1r_trace(records, owner, completed_moves=2)
    assert audit["source_bound_tick_samples"] == 3
    assert audit["rest_preferred_samples"] == 2
    assert audit["ready_feeling_samples"] == 1
    assert audit["observed_change_in_sensed_preference"] is True


def test_original_strict_t1q_action_guard_stays_in_place():
    owner = TickAccounting("test-session")
    owner.observe(frame(1))
    owner.begin("in-flight")
    motor = frame(2, control="MOVING", bits=2, x=.8, seq=20)
    owner.observe(motor)
    from adapters.mineflayer.t1q_interoception_dev import T1qRejected
    with pytest.raises(T1qRejected):
        project_t1q_selfbody(motor, owner, epoch_id="strict")
    # Explicitly passive readout is not physical admission or real S49 stop.
    view = project_t1q_selfbody(
        motor, owner, epoch_id="passive", passive_during_action=True,
    )
    assert view.sensed("p1_fatigue_sensor").origin is BodyOrigin.INTEROCEPTION
    assert sensed_rest_preference(view) == "REST_PREFERRED"
    assert owner.active_action == "in-flight"
    assert owner.rows[-1]["activity"] == "MOVE_OR_UNDETERMINED"


def test_missing_body_sensors_remain_unknown_and_cannot_grant_movement():
    blank = compose_self_body_view(session_id="test-session", epoch_id="none")
    assert sensed_rest_preference(blank) == "UNKNOWN_HOLD"
    assert blank.observed("p1_fatigue_sensor").origin is BodyOrigin.UNKNOWN


@pytest.mark.parametrize("damage", [
    lambda r: r.update(native_seq=9999),
    lambda r: r.update(world_tick=9999),
    lambda r: r.update(m0_tick=9999),
    lambda r: r.update(fatigue_sensed=0.9),
    lambda r: r.update(energy_sensed=0.0),
    lambda r: r.update(physical_permission_from_view=True),
    lambda r: r.update(p1_qualified_wait=True),
    lambda r: r.update(fatigue_origin="observation"),
])
def test_replay_audit_rejects_forged_view_or_cross_clock(damage):
    owner, entries = _physical_timeline()
    damage(entries[0])
    with pytest.raises(T1rRejected):
        audit_t1r_trace(entries, owner, completed_moves=2)


def test_duplicate_and_stale_timeline_refused():
    owner = TickAccounting("test-session")
    owner.observe(frame(1))
    f2 = frame(2, x=.3, bits=2)
    owner.observe(f2)
    records = []
    capture_passive_tick(f2, owner, records)
    with pytest.raises(T1rRejected):
        capture_passive_tick(f2, owner, records)
    f3 = frame(3, x=.5, bits=2)
    owner.observe(f3)
    with pytest.raises(T1rRejected):
        capture_passive_tick(f2, owner, records)
    with pytest.raises(T1rRejected):
        capture_passive_tick(f3, owner, records * MAX_PASSIVE_TICKS)


def test_session_and_profile_mismatch_refused_passively():
    owner = TickAccounting("test-session")
    owner.observe(frame(1))
    f2 = frame(2, x=.5, bits=2)
    owner.observe(f2)
    owner.fatigue = replace(owner.fatigue, session_id="alien")
    with pytest.raises(Exception):
        capture_passive_tick(f2, owner, [])


def test_readonly_observer_is_scoped_to_original_t1q_runner(monkeypatch):
    import adapters.mineflayer.t1r_fatigue_timecourse_dev as mod
    session = SimpleNamespace(passive_body_tick_observer=None, tick_owner=None)
    calls = []

    async def fake_t1q(existing_session, report, *, move_limit):
        assert existing_session is session
        assert move_limit == 2
        assert callable(session.passive_body_tick_observer)
        calls.append("original_t1q")
        owner = TickAccounting("test-session")
        owner.observe(frame(1))
        session.tick_owner = owner
        owner.begin("a")
        motor = frame(2, control="MOVING", bits=2, x=.8, seq=20)
        owner.observe(motor)
        session.passive_body_tick_observer(motor, owner)
        owner.finish(SimpleNamespace(action_id="a", cleanup_receipt=SimpleNamespace(
            result="applied", effect="clear_controls", seq=25),
            after_observation=None), SimpleNamespace(action_id="a"))
        boundary = frame(3, x=.8, seq=30)
        owner.observe(boundary)
        session.passive_body_tick_observer(boundary, owner)
        resting = frame(4, x=.8, seq=40)
        owner.observe(resting)
        session.passive_body_tick_observer(resting, owner)
        report.update(status="PASS", t1q={"completed_moves": 2})

    monkeypatch.setattr(mod, "run_t1q_body_loop_dev", fake_t1q)
    report = {}
    asyncio.run(run_t1r_body_recovery_dev(session, report, move_limit=2))
    assert calls == ["original_t1q"]
    assert session.passive_body_tick_observer is None
    assert report["status"] == "PASS"
    assert report["t1r"]["audit"]["rest_preferred_samples"] > 0
    assert report["t1r"]["audit"]["ready_feeling_samples"] > 0
    assert report["t1r"]["extra_motor_commands"] == 0


def test_passive_observer_removed_even_when_original_runner_fails(monkeypatch):
    import adapters.mineflayer.t1r_fatigue_timecourse_dev as mod

    async def failed(*args, **kwargs):
        raise RuntimeError("original S49 unavailable")

    monkeypatch.setattr(mod, "run_t1q_body_loop_dev", failed)
    session = SimpleNamespace(passive_body_tick_observer=None)
    with pytest.raises(RuntimeError, match="S49 unavailable"):
        asyncio.run(run_t1r_body_recovery_dev(session, {}, move_limit=2))
    assert session.passive_body_tick_observer is None


def test_t1r_no_more_synchronous_trace_or_independent_paper_receiver():
    from adapters.mineflayer.t1e_native_dev import TICK_CASES, run_case
    assert "t1r_body_recovery" in TICK_CASES
    assert "rows" not in run_case.__code__.co_varnames
