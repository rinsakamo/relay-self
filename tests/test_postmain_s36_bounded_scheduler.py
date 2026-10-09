"""S36 bounded event-driven cognition scheduler: deterministic capacity and security.

No Minecraft server is started in pytest. Physical native-event validation
belongs to the separate real Java/Mineflayer CI job.
"""
from __future__ import annotations

import asyncio
import json
from dataclasses import replace
from pathlib import Path

import pytest

import test_postmain_s35_event_cognition_gate as s35
import test_postmain_two_epoch_continuation as s19
from adapters.mineflayer.s34_native_world_cognition_ci import (
    _native_epoch_two,
    _native_threat,
)
from relay_self.action_supervision import ActionSupervisor, UnknownSupervisedAction
from relay_self.bounded_event_scheduler import (
    BoundedEventCognitionScheduler,
    EventQueueDisposition,
    EventSchedulerBudget,
    SchedulerGateError,
    SchedulerResourceExhausted,
)
from relay_self.native_event_cognition import (
    EventCognitionNotAdmitted,
    EventCognitionTriggerGrant,
    InvalidEventCognitionEvidence,
)

ROOT = Path(__file__).resolve().parents[1]


def _event(session="s36-session-a", seq=10, distance=2.0, entity_id=None):
    event, _ = s35._source(distance_m=distance)
    if entity_id is not None:
        entity = replace(event.snapshot.nearby_entities[0], entity_id=entity_id)
        event = replace(event, snapshot=replace(
            event.snapshot, nearby_entities=(entity,),
        ))
    return replace(event, session_id=session, seq=seq)


def _grant(candidate):
    return EventCognitionTriggerGrant(
        authority_id="s36-independent-trigger-authority",
        candidate_id=candidate.candidate_id,
        session_id=candidate.session_id,
        event_seq=candidate.event_seq,
        target_entity_id=candidate.target_entity_id,
        granted=True,
        provenance=s19.provenance("independent-s36-grant"),
    )


def _functions(event_by_session=None, *, on_cognition=None):
    async def probe(candidate):
        initial = (event_by_session or {})[candidate.session_id] if event_by_session else None
        if initial is None:
            initial = _event(
                session=candidate.session_id,
                seq=candidate.event_seq,
                distance=candidate.distance_m,
                entity_id=candidate.target_entity_id,
            )
        return replace(
            initial, kind="probe", seq=candidate.event_seq + 1,
            request_id=f"s36-probe:{candidate.session_id}:{candidate.event_seq}",
        )

    def cognition(ticket):
        if on_cognition is not None:
            on_cognition(ticket)
        return ticket.event_id

    return probe, _grant, cognition


def test_real_event_ingested_and_auto_scheduled_without_manual_cognition():
    async def run():
        scheduler = BoundedEventCognitionScheduler()
        event = _event()
        callbacks = _functions()
        disposition, batch = await scheduler.on_native_event(
            event, probe=callbacks[0], grant=callbacks[1], cognition=callbacks[2],
        )
        assert disposition is EventQueueDisposition.ENQUEUED
        assert batch.work_attempted == 1
        assert batch.remaining_pending == 0
        assert len(batch.outcomes) == 1
        assert scheduler.total_cognition == 1
        assert batch.outcomes[0].ticket.candidate.event_seq == event.seq
        replay, no_batch = await scheduler.on_native_event(
            event, probe=callbacks[0], grant=callbacks[1], cognition=callbacks[2],
        )
        assert replay is EventQueueDisposition.STALE
        assert not no_batch.outcomes
        assert scheduler.total_cognition == 1
    asyncio.run(run())


def test_native_event_coalesces_latest_per_session_and_entity():
    scheduler = BoundedEventCognitionScheduler()
    first = _event(seq=10)
    newer = _event(seq=12, distance=2.5)
    assert scheduler.ingest_native(first) is EventQueueDisposition.ENQUEUED
    assert scheduler.ingest_native(newer) is EventQueueDisposition.COALESCED
    assert scheduler.pending_count == 1
    assert scheduler.total_coalesced == 1
    async def run():
        batch = await scheduler.drain_batch(
            probe=_functions()[0], grant=_grant, cognition=lambda t: t.event_id,
        )
        assert len(batch.outcomes) == 1
        assert batch.outcomes[0].ticket.candidate.event_seq == 12
    asyncio.run(run())


def test_disappearance_or_safe_distance_invalidates_pending_not_safe_world_claim():
    scheduler = BoundedEventCognitionScheduler()
    assert scheduler.ingest_native(_event(seq=10)) is EventQueueDisposition.ENQUEUED
    assert scheduler.ingest_native(_event(seq=11, distance=6)) is EventQueueDisposition.INVALIDATED
    assert scheduler.pending_count == 0
    assert scheduler.total_invalidated == 1
    assert scheduler.ingest_native(_event(seq=10)) is EventQueueDisposition.STALE


def test_stale_native_event_rejected_by_monotonic_session_cursor():
    scheduler = BoundedEventCognitionScheduler()
    assert scheduler.ingest_native(_event(seq=10)) is EventQueueDisposition.ENQUEUED
    assert scheduler.ingest_native(_event(seq=9)) is EventQueueDisposition.STALE
    assert scheduler.pending_count == 1


def test_queue_capacity_is_hard_failure_to_enqueue_and_not_priority_evict():
    scheduler = BoundedEventCognitionScheduler(
        EventSchedulerBudget(max_pending=2),
    )
    assert scheduler.ingest_native(_event("a")) is EventQueueDisposition.ENQUEUED
    assert scheduler.ingest_native(_event("b")) is EventQueueDisposition.ENQUEUED
    assert scheduler.ingest_native(_event("c")) is EventQueueDisposition.FULL
    assert scheduler.total_full == 1
    assert scheduler.pending_count == 2


def test_seq_age_expiration_discards_unverified_old_candidate():
    scheduler = BoundedEventCognitionScheduler(
        EventSchedulerBudget(max_event_age_seq=5),
    )
    scheduler.ingest_native(_event(seq=10, entity_id=2))
    scheduler.ingest_native(_event(seq=30, entity_id=8))
    async def run():
        batch = await scheduler.drain_batch(
            probe=_functions()[0], grant=_grant, cognition=lambda t: t.event_id,
        )
        assert batch.dropped_stale == 1
        assert len(batch.outcomes) == 1
        assert batch.outcomes[0].ticket.candidate.target_entity_id == 8
    asyncio.run(run())


def test_priority_with_burst_fairness_serves_low_priority_by_third_dispatch():
    budget = EventSchedulerBudget(
        max_pending=4, max_epochs_per_batch=4,
        max_total_cognition=4, max_urgent_burst=2,
    )
    s = BoundedEventCognitionScheduler(budget)
    events = {
        "urgent-a": _event("urgent-a", distance=1.5),
        "urgent-b": _event("urgent-b", distance=2),
        "urgent-c": _event("urgent-c", distance=2),
        "normal": _event("normal", distance=3.5),
    }
    for event in events.values():
        assert s.ingest_native(event) is EventQueueDisposition.ENQUEUED
    async def run():
        probe, grant, cognition = _functions(events)
        batch = await s.drain_batch(probe=probe, grant=grant, cognition=cognition)
        processed = [x.ticket.candidate.session_id for x in batch.outcomes]
        assert processed == ["urgent-a", "urgent-b", "normal", "urgent-c"]
        assert batch.work_attempted == 4
        assert s.total_cognition == 4
    asyncio.run(run())


def test_batch_and_cumulative_limits_prevent_unbounded_cognition():
    budget = EventSchedulerBudget(
        max_epochs_per_batch=1, max_total_cognition=2,
    )
    s = BoundedEventCognitionScheduler(budget)
    for idx in range(3):
        s.ingest_native(_event(f"sess-{idx}"))
    async def run():
        callbacks = _functions()
        first = await s.drain_batch(
            probe=callbacks[0], grant=callbacks[1], cognition=callbacks[2],
        )
        second = await s.drain_batch(
            probe=callbacks[0], grant=callbacks[1], cognition=callbacks[2],
        )
        third = await s.drain_batch(
            probe=callbacks[0], grant=callbacks[1], cognition=callbacks[2],
        )
        assert len(first.outcomes) == len(second.outcomes) == 1
        assert len(third.outcomes) == 0
        assert third.remaining_pending == 1
        assert s.total_cognition == 2
        with pytest.raises(SchedulerResourceExhausted):
            await s.on_native_event(
                _event("fourth"),
                probe=callbacks[0], grant=callbacks[1], cognition=callbacks[2],
            )
    asyncio.run(run())


@pytest.mark.parametrize("kwargs", [
    {"max_pending": 0}, {"max_pending": True},
    {"max_total_cognition": -1}, {"max_epochs_per_batch": 0},
    {"max_event_age_seq": 0}, {"max_urgent_burst": 0},
    {"per_probe_timeout_s": 0}, {"per_probe_timeout_s": True},
    {"per_probe_timeout_s": 61},
])
def test_bad_budget_values_never_expand_to_unbounded(kwargs):
    with pytest.raises(SchedulerGateError):
        EventSchedulerBudget(**kwargs)


def test_probe_timeout_fails_not_skips_as_pass():
    s = BoundedEventCognitionScheduler(
        EventSchedulerBudget(per_probe_timeout_s=0.01),
    )
    s.ingest_native(_event())
    async def too_slow(_candidate):
        await asyncio.sleep(0.2)
        raise AssertionError("should be cancelled")
    async def run():
        with pytest.raises(SchedulerResourceExhausted):
            await s.drain_batch(
                probe=too_slow, grant=_grant, cognition=lambda t: t.event_id,
            )
        assert s.total_cognition == 0
        assert s.pending_count == 0
    asyncio.run(run())


@pytest.mark.parametrize("bad", ["denied", "wrong_session", "older_probe", "different_zombie"])
def test_separate_authority_and_native_reprobe_still_fail_closed(bad):
    s = BoundedEventCognitionScheduler()
    s.ingest_native(_event())
    probe, grant, cognition = _functions()
    async def bad_probe(candidate):
        msg = await probe(candidate)
        if bad == "older_probe":
            return replace(msg, seq=candidate.event_seq)
        if bad == "wrong_session":
            return replace(msg, session_id="not-s36")
        if bad == "different_zombie":
            entity = replace(
                msg.snapshot.nearby_entities[0],
                entity_id=candidate.target_entity_id + 1,
            )
            return replace(msg, snapshot=replace(
                msg.snapshot, nearby_entities=(entity,),
            ))
        return msg
    def bad_grant(candidate):
        g = grant(candidate)
        return replace(g, granted=False) if bad == "denied" else g
    async def run():
        with pytest.raises((EventCognitionNotAdmitted, InvalidEventCognitionEvidence)):
            await s.drain_batch(probe=bad_probe, grant=bad_grant, cognition=cognition)
        assert s.total_cognition == 0
    asyncio.run(run())


def test_cognition_invoked_from_auto_event_has_no_action_owner():
    async def run():
        past_supervisor, committed, _intent, past_closed, feedback, _ = (
            await asyncio.to_thread(s19._epoch_one)
        )
        assert past_supervisor.get(past_closed.action_id) is past_closed
        assert feedback.feedback is not None
        supervisor = ActionSupervisor()
        intent = s19.IntentCommitment()
        intent.commit(
            "escape-threat", objective="escape the nearby threat", at_ns=1,
            provenance=s19.provenance("s36-offline-existing-intent"),
        )
        observed = []
        def cognition(ticket):
            native = _native_threat(ticket.correlated_probe, ticket.probe_request_id)
            values, outer = _native_epoch_two(
                supervisor, intent, committed.new_state, committed.new_state,
                expected_revision=1, native=native,
            )
            assert values["admission"].status.value == "admitted"
            assert values["plan"].selected.candidate_id == "MOVE_AWAY"
            assert outer.cognition_requested is False
            assert supervisor.open_actions == ()
            observed.append(ticket.event_id)
            return values["plan"].selected.candidate_id
        probe, grant, _ = _functions()
        scheduler = BoundedEventCognitionScheduler()
        disp, batch = await scheduler.on_native_event(
            _event(), probe=probe, grant=grant, cognition=cognition,
        )
        assert disp is EventQueueDisposition.ENQUEUED
        assert batch.outcomes[0].cognition_result == "MOVE_AWAY"
        assert len(observed) == 1
        with pytest.raises(UnknownSupervisedAction):
            supervisor.get("action-s36")
    asyncio.run(run())


def test_static_plan_gates_action_scope_and_live_result():
    plan = json.loads((ROOT / "docs/postmain-s36-plan-receipt.json").read_text())
    assert plan["status"] == "PENDING_CI"
    assert plan["base_head"] == "37965b61932930039360f09d5991c552c4229dfd"
    assert plan["qualification_requires"] == "S36_REPORT.status == PASS"
    assert plan["action_issued_by_scheduler"] is False
    assert plan["scheduler_resource_limits"]["max_total_cognition"] == 2
    source = (ROOT / "src/relay_self/bounded_event_scheduler.py").read_text()
    assert "ActionSupervisor" not in source
    assert "send_set_control(" not in source
    assert "issue(" not in source
