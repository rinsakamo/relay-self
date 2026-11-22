"""Original Resident async CPU scheduling after A reJOIN, CPU/offline only.

No new owner, periodic GPU calls, ActionPort or persistent memory writes.
Each scenario owns real original Bridge/Resident tasks in one asyncio loop,
with original synthetic Native decoder and owned Paper witness.
"""
from __future__ import annotations

import asyncio
from dataclasses import replace

import pytest

from relay_self.b_np1b_fresh_native_update_dev import update_fresh_native
from relay_self.b_np1b_normal_present_scheduler_dev import (
    NormalCpuScheduleHold,
    NormalResidentPresentCpuScheduler,
    ScheduledPresentCpu,
)
from relay_self.owned_paper_world_dev import PaperTickReceipt
from test_b_np1b_fresh_native_update_dev import files
from test_b_np1b_initial_source_dev import BOOT, WORLD
from test_b_np1b_normal_present_poll_dev import current_fixture as current_fixture
from test_b_np1b_normal_present_poll_dev import pair as pair
from test_b_np1b_normal_present_poll_dev import rejoined as rejoined
from test_b_np1b_normal_present_poll_dev import rejoined_present as rejoined_present
from test_b_np1b_owner_bound_rejoin_dev import _paper_line


async def _eventually_current(f, sid, *, after=0, different_ref=None):
    last = None
    for _ in range(100):
        try:
            result = f.bridge.require_scheduled_present_cpu(sid)
            if (
                result.iteration > after
                and (different_ref is None or result.source_pair_revision != different_ref)
            ):
                return result
        except NormalCpuScheduleHold as exc:
            last = exc
        await asyncio.sleep(0.01)
    raise AssertionError(f"{sid} never became current: {last}")


async def _eventually_status(scheduler, sid, status):
    for _ in range(100):
        if scheduler.status(sid)[0] == status:
            return
        await asyncio.sleep(0.01)
    raise AssertionError(f"no {status} status for {sid}: {scheduler.status(sid)}")


def _original_state(f):
    return {
        sid: (owner.retained, owner.intent, owner.pattern_registry,
              dict(owner.skills), set(owner.pending_questions))
        for sid, owner in f.owners.items()
    }


def _bind(pair):
    f, initial, _, historical, _, _, _ = pair
    f.bridge.bind_normal_rejoin_present_cpu(
        initial_receipts=initial, historical_composite=historical,
    )
    return f


def test_periodic_original_cpu_tasks_publish_only_rechecked_source(pair):
    f = _bind(pair)
    before_files = files(f)
    before_state = _original_state(f)

    async def scenario():
        scheduler = f.bridge.start_normal_present_cpu_schedule(interval_s=0.02)
        assert type(scheduler) is NormalResidentPresentCpuScheduler
        assert scheduler.resident is f.cognitive
        assert scheduler.bridge is f.bridge
        assert set(scheduler._tasks) == {"A", "B"}
        for sid in ("A", "B"):
            state = f.cognitive._state(sid)
            task = scheduler._tasks[sid]
            assert state.tasks[f"normal-present-cpu:{sid}"] is task
            assert not task.done()
            assert scheduler._tokens[sid].native_session_id == f.bridge.sessions[sid].started.session_id
        try:
            a = await _eventually_current(f, "A")
            b = await _eventually_current(f, "B")
            assert type(a) is ScheduledPresentCpu and type(b) is ScheduledPresentCpu
            assert a.self_id == "A" and b.self_id == "B"
            assert a.source_pair_revision == b.source_pair_revision
            assert a.poll == b.poll
            assert a.poll.a_present.present.three_self.scope.self_id == "A"
            assert b.poll.b_present.present.three_self.scope.self_id == "B"
            assert a.poll.a_inquiry is not None and b.poll.b_inquiry is not None
            assert a.poll.a_present.source.composite_receipt.composite_revision != (
                b.poll.b_present.source.composite_receipt.composite_revision
            )
            newer = await _eventually_current(f, "A", after=a.iteration)
            assert newer.iteration > a.iteration
            assert newer.source_pair_revision == a.source_pair_revision
            assert newer.token == a.token
            assert scheduler.status("A")[0] == "CURRENT"
            assert scheduler.status("B")[0] == "CURRENT"
            with pytest.raises(NormalCpuScheduleHold):
                f.bridge.require_scheduled_present_cpu("C")
            with pytest.raises(NormalCpuScheduleHold):
                f.bridge.start_normal_present_cpu_schedule(interval_s=0.02)
        finally:
            await scheduler.stop()
        assert scheduler.status("A")[0] == "STOPPED"
        assert scheduler.status("B")[0] == "STOPPED"
        assert all(task.done() for task in scheduler._tasks.values())
        with pytest.raises(NormalCpuScheduleHold):
            f.bridge.require_scheduled_present_cpu("A")
        # Original owner tracking remains present for later retirement auditing.
        for sid in ("A", "B"):
            assert f.cognitive._state(sid).tasks[f"normal-present-cpu:{sid}"] is scheduler._tasks[sid]

    asyncio.run(scenario())
    assert files(f) == before_files
    assert _original_state(f) == before_state
    assert f.bridge.physical.active_action_ids == frozenset()


def test_scheduler_recovers_after_actual_b_native_update_without_rebinding(pair):
    f = _bind(pair)
    initial = pair[1]

    async def scenario():
        scheduler = f.bridge.start_normal_present_cpu_schedule(interval_s=0.03)
        try:
            before = await _eventually_current(f, "B")
            old = before.poll.b_present.source.composite_receipt
            updated = await update_fresh_native(
                bridge=f.bridge, self_id="B", initial_receipt=initial[1],
            )
            assert updated.native_revision != old.native_revision
            current = await _eventually_current(
                f, "B", different_ref=before.source_pair_revision,
            )
            assert current.poll.b_present.source.composite_receipt.native_revision == updated.native_revision
            assert current.poll.b_present.source.composite_receipt.native_request_id == updated.native_request_id
            assert current.poll.a_present.source.composite_receipt.native_session_id == (
                before.poll.a_present.source.composite_receipt.native_session_id
            )
            assert current.poll.b_present.source.composite_receipt.native_session_id == (
                old.native_session_id
            )
            assert current.poll.b_present.source.composite_receipt.paper_revision == old.paper_revision
            assert current.source_pair_revision != before.source_pair_revision
            a = await _eventually_current(
                f, "A", different_ref=before.source_pair_revision,
            )
            assert a.poll == current.poll
            assert f.cognitive.current_scope("B") == (
                before.poll.b_present.source.resident_epoch,
                old.native_session_id, old.world_epoch,
            )
        finally:
            await scheduler.stop()

    asyncio.run(scenario())


def test_scheduler_rejects_paper_growth_then_uses_new_owned_ack(pair, monkeypatch):
    f = _bind(pair)
    paper = f.paper
    original_log = paper._log_path.read_text()

    async def scenario():
        scheduler = f.bridge.start_normal_present_cpu_schedule(interval_s=0.02)
        try:
            initial = await _eventually_current(f, "A")
            paper._log_path.write_text(original_log + "unverified\n")
            with pytest.raises(NormalCpuScheduleHold):
                f.bridge.require_scheduled_present_cpu("A")
            with pytest.raises(NormalCpuScheduleHold):
                f.bridge.require_scheduled_present_cpu("B")
            await _eventually_status(scheduler, "A", "HOLD")
            await _eventually_status(scheduler, "B", "HOLD")
            nonce = "99999999-9999-4999-8999-999999999999"
            session_id = paper.owned_session_id
            paper._log_path.write_text(
                original_log
                + _paper_line("PRESENT", 26, "B")
                + f"P0D_TICK_ACK nonce={nonce} boot={BOOT} session={session_id} "
                  f"world={WORLD} tick=27 source=PAPER_MAIN_THREAD\n"
            )
            tick = PaperTickReceipt(
                session_id, 27,
                f"paper-main-thread:p0d:{BOOT}:{nonce}:sha256:" + "d" * 64,
            )
            monkeypatch.setattr(paper, "tick_readback", lambda _: tick)
            repaired = await _eventually_current(
                f, "A", different_ref=initial.source_pair_revision,
            )
            assert repaired.source_pair_revision != initial.source_pair_revision
            assert repaired.poll.a_present.source.paper_tick_source_ref == tick.source_ref
            assert repaired.poll.b_present.source.paper_tick_source_ref == tick.source_ref
            assert repaired.poll.b_present.source.composite_receipt.b_post_rejoin_present_tick == 26
            assert scheduler.status("A")[0] == "CURRENT"
            assert scheduler.status("B")[0] == "CURRENT"
        finally:
            await scheduler.stop()

    asyncio.run(scenario())


def test_original_logout_cancels_a_owned_cpu_task_and_fences_b_result(pair):
    f = _bind(pair)
    b_session = f.bridge.sessions["B"]
    b_scope = f.cognitive.current_scope("B")

    async def scenario():
        scheduler = f.bridge.start_normal_present_cpu_schedule(interval_s=0.02)
        try:
            await _eventually_current(f, "A")
            await _eventually_current(f, "B")
            receipt = await f.bridge.logout("A")
            assert receipt.physical_issuer_revoked
            assert receipt.native_terminated
            assert f.cognitive.retired_clean("A")
            assert scheduler._tasks["A"].done()
            assert "normal-present-cpu:A" in receipt.__dict__.get(
                "cancelled_cpu_task_refs", (),
            ) or "normal-present-cpu:A" in (
                f.cognitive._state("A").retired.cancelled_cpu_task_refs
            )
            assert f.bridge.sessions["B"] is b_session
            assert f.cognitive.current_scope("B") == b_scope
            with pytest.raises(NormalCpuScheduleHold):
                f.bridge.require_scheduled_present_cpu("A")
            with pytest.raises(NormalCpuScheduleHold):
                f.bridge.require_scheduled_present_cpu("B")
            await _eventually_status(scheduler, "B", "HOLD")
        finally:
            await scheduler.stop()
        assert scheduler._tasks["B"].done()

    asyncio.run(scenario())


@pytest.mark.parametrize("case", [
    "b_quarantine", "a_quarantine", "b_epoch", "b_owner",
    "schema_a", "schema_b", "foreign_probe", "paper_pid",
])
def test_scheduler_does_not_expose_stale_results_after_owner_source_fence(pair, monkeypatch, case):
    f = _bind(pair)

    async def scenario():
        scheduler = f.bridge.start_normal_present_cpu_schedule(interval_s=0.02)
        try:
            first = await _eventually_current(f, "A")
            await _eventually_current(f, "B")
            if case in ("b_quarantine", "a_quarantine"):
                f.bridge.quarantine("B" if case == "b_quarantine" else "A")
            elif case == "b_epoch":
                f.cognitive._states["B"].epoch += 1
            elif case == "b_owner":
                f.bridge.owners["B"] = f.bridge.owners["A"]
            elif case == "schema_a":
                del f.cognitive._present_schemas["A"]
            elif case == "schema_b":
                del f.cognitive._present_schemas["B"]
            elif case == "foreign_probe":
                owner = f.owners["B"]
                owner.current_worldbody_observation = replace(
                    owner.current_worldbody_observation, seq=99,
                )
            else:
                process = f.paper._assert_owned
                monkeypatch.setattr(
                    f.paper, "_assert_owned",
                    lambda: type("ForeignPaper", (), {"pid": process().pid + 1})(),
                )
            with pytest.raises(NormalCpuScheduleHold):
                f.bridge.require_scheduled_present_cpu("A")
            with pytest.raises(NormalCpuScheduleHold):
                f.bridge.require_scheduled_present_cpu("B")
            assert first.source_pair_revision
            await asyncio.sleep(0.06)
            assert scheduler.status("A")[0] in ("HOLD", "STOPPED")
            assert scheduler.status("B")[0] in ("HOLD", "STOPPED")
        finally:
            await scheduler.stop()

    asyncio.run(scenario())


@pytest.mark.parametrize("interval", [0.0, -1, 30.1, float("nan"), "5", None, True])
def test_no_unbounded_or_invalid_scheduler_admission(pair, interval):
    f = _bind(pair)

    async def scenario():
        with pytest.raises(NormalCpuScheduleHold):
            f.bridge.start_normal_present_cpu_schedule(interval_s=interval)
        assert not hasattr(f.cognitive, "_normal_present_scheduler")
        assert all(not s.tasks for s in f.cognitive._states.values())

    asyncio.run(scenario())


def test_no_implicit_schedule_before_original_rejoin_source_binding(pair):
    f = pair[0]

    async def scenario():
        with pytest.raises(NormalCpuScheduleHold):
            f.bridge.start_normal_present_cpu_schedule(interval_s=0.02)
        with pytest.raises(NormalCpuScheduleHold):
            f.bridge.require_scheduled_present_cpu("A")
        assert all(not s.tasks for s in f.cognitive._states.values())

    asyncio.run(scenario())


def test_scheduler_cannot_be_started_outside_running_event_loop(pair):
    f = _bind(pair)
    with pytest.raises(NormalCpuScheduleHold):
        f.bridge.start_normal_present_cpu_schedule(interval_s=0.02)
    assert all(not s.tasks for s in f.cognitive._states.values())
