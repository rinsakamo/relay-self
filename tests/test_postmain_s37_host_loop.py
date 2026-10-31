"""S37 bounded host loop, event bursts, reconnect and old-ticket fail closed.

No live server in offline tests; genuine Minecraft has a separate CI job.
The frozen S35 native fixtures execute synthetic asyncio.run internally,
so create typed source snapshots *before* scheduler event loops start.
"""
from __future__ import annotations

import asyncio
import json
from dataclasses import replace
from pathlib import Path
from types import SimpleNamespace

import pytest

import test_postmain_s35_event_cognition_gate as s35
import test_postmain_two_epoch_continuation as s19
from relay_self.bounded_native_host_loop import (
    BoundedNativeHostLoop,
    HostLoopBoundaryError,
    HostLoopBudget,
    HostLoopResourceError,
)
from relay_self.native_event_cognition import EventCognitionTriggerGrant

ROOT = Path(__file__).resolve().parents[1]
BASE_EVENT = s35._source(distance_m=2.0)[0]


def _event(session="node-a", seq=10, entity_id=2, *, distance=None):
    entity = BASE_EVENT.snapshot.nearby_entities[0]
    entity = replace(
        entity, entity_id=entity_id,
        distance=entity.distance if distance is None else distance,
    )
    snap = replace(BASE_EVENT.snapshot, nearby_entities=(entity,))
    return replace(BASE_EVENT, session_id=session, seq=seq, snapshot=snap)


class _Session:
    def __init__(self, sid, events):
        self.started = SimpleNamespace(session_id=sid)
        self.events = list(events)

    async def receive(self):
        if self.events:
            return self.events.pop(0)
        await asyncio.sleep(60)
        raise AssertionError("timeout expected")


def _grant(candidate):
    return EventCognitionTriggerGrant(
        authority_id="s37-external-cognition-grant",
        candidate_id=candidate.candidate_id,
        session_id=candidate.session_id,
        event_seq=candidate.event_seq,
        target_entity_id=candidate.target_entity_id,
        granted=True,
        provenance=s19.provenance("s37-external-grant"),
    )


async def _probe(candidate):
    entity = candidate.target_entity_id
    event = _event(
        candidate.session_id, candidate.event_seq, entity_id=entity,
    )
    return replace(
        event, kind="probe", seq=candidate.event_seq + 1,
        request_id=f"s37-native-probe-{candidate.event_seq}-{entity}",
    )


def test_two_sessions_three_real_shaped_incidents_and_old_ticket_discard():
    async def run():
        h = BoundedNativeHostLoop()
        h.begin_session("node-a")
        s = _Session("node-a", [
            _event("node-a", 10, 2), _event("node-a", 12, 3),
        ])
        first = await h.wait_for_event_cognition(
            s, probe=_probe, grant=_grant, cognition=lambda t: t.event_id,
        )
        second = await h.wait_for_event_cognition(
            s, probe=_probe, grant=_grant, cognition=lambda t: t.event_id,
        )
        assert first.entity_id == 2 and second.entity_id == 3
        assert first.session_id == second.session_id == "node-a"
        h.end_session("node-a")
        with pytest.raises(HostLoopBoundaryError):
            h.require_current_ticket(first.ticket)
        h.begin_session("node-b")
        with pytest.raises(HostLoopBoundaryError):
            h.require_current_ticket(second.ticket)
        third = await h.wait_for_event_cognition(
            _Session("node-b", [_event("node-b", 3, 4)]),
            probe=_probe, grant=_grant, cognition=lambda t: t.event_id,
        )
        assert third.entity_id == 4
        assert third.session_id != first.session_id
        assert h.total_sessions == 2 and h.total_epochs == 3
        with pytest.raises(HostLoopResourceError):
            await h.wait_for_event_cognition(
                _Session("node-b", [_event("node-b", 7, 5)]),
                probe=_probe, grant=_grant, cognition=lambda t: t.event_id,
            )
        h.end_session("node-b")
        assert h.active_session_id is None and h.pending_count == 0
    asyncio.run(run())


def test_reconnect_erases_pending_queue_and_session_local_ledger():
    h = BoundedNativeHostLoop()
    h.begin_session("node-a")
    assert h._scheduler is not None
    assert h._scheduler.ingest_native(_event("node-a", 10, 2)).value == "enqueued"
    assert h.pending_count == 1
    h.end_session("node-a")
    assert h.expired_pending == 1
    assert h.pending_count == 0
    h.begin_session("node-b")
    assert h.pending_count == 0
    with pytest.raises(HostLoopBoundaryError):
        h.begin_session("node-c")
    h.end_session("node-b")
    with pytest.raises(HostLoopBoundaryError):
        h.begin_session("node-a")
    with pytest.raises(HostLoopResourceError):
        h.begin_session("node-c")


def test_repeated_entity_is_not_new_incident_and_leads_to_wait_budget_exhaustion():
    async def run():
        h = BoundedNativeHostLoop(HostLoopBudget(
            max_frames_per_event=1, receive_timeout_s=0.02,
        ))
        h.begin_session("node-a")
        first = await h.wait_for_event_cognition(
            _Session("node-a", [_event("node-a", 10, 2)]),
            probe=_probe, grant=_grant, cognition=lambda t: t.event_id,
        )
        assert first.entity_id == 2
        with pytest.raises(HostLoopResourceError):
            await h.wait_for_event_cognition(
                _Session("node-a", [_event("node-a", 12, 2)]),
                probe=_probe, grant=_grant, cognition=lambda t: t.event_id,
            )
        assert h.rejected_replays == 1
        assert h.total_epochs == 1
    asyncio.run(run())


def test_native_disappearance_does_not_mint_new_cognition():
    async def run():
        h = BoundedNativeHostLoop(HostLoopBudget(
            max_frames_per_event=1, receive_timeout_s=0.02,
        ))
        h.begin_session("node-a")
        gone = _event("node-a", 15)
        coverage = replace(gone.snapshot.nearby_entities_coverage, candidate_count=0)
        empty = replace(gone, snapshot=replace(
            gone.snapshot,
            nearby_entities=(), nearby_entities_coverage=coverage,
        ))
        with pytest.raises(HostLoopResourceError):
            await h.wait_for_event_cognition(
                _Session("node-a", [empty]),
                probe=_probe, grant=_grant, cognition=lambda t: t.event_id,
            )
        assert h.total_epochs == 0
    asyncio.run(run())


@pytest.mark.parametrize("fault", [
    "foreign-session", "missing-event", "double-session", "session-replay",
])
def test_session_and_wait_boundary_refuse_unqualified_progress(fault):
    async def run():
        h = BoundedNativeHostLoop(HostLoopBudget(receive_timeout_s=0.02))
        h.begin_session("node-a")
        if fault == "double-session":
            with pytest.raises(HostLoopBoundaryError):
                h.begin_session("node-b")
        elif fault == "session-replay":
            h.end_session("node-a")
            with pytest.raises(HostLoopBoundaryError):
                h.begin_session("node-a")
        else:
            s = _Session(
                "node-other" if fault == "foreign-session" else "node-a",
                [] if fault == "missing-event" else [_event()],
            )
            error_type = (
                HostLoopBoundaryError if fault == "foreign-session"
                else HostLoopResourceError
            )
            with pytest.raises(error_type):
                await h.wait_for_event_cognition(
                    s, probe=_probe, grant=_grant, cognition=lambda t: t.event_id,
                )
        assert h.total_epochs == 0
    asyncio.run(run())


@pytest.mark.parametrize("kwargs", [
    {"max_sessions": 0}, {"max_sessions": True},
    {"max_total_epochs": -1}, {"max_epochs_per_session": 0},
    {"max_frames_per_event": 0}, {"receive_timeout_s": 0},
    {"receive_timeout_s": True}, {"receive_timeout_s": 130},
])
def test_bounded_host_budget_cannot_be_unbounded(kwargs):
    with pytest.raises(HostLoopResourceError):
        HostLoopBudget(**kwargs)


def test_source_code_never_confuses_event_cognition_with_action_authority():
    source = (ROOT / "src/relay_self/bounded_native_host_loop.py").read_text()
    for unsafe in ("ActionSupervisor", "send_set_control(", "issue(", "attack("):
        assert unsafe not in source
    plan = json.loads((ROOT / "docs/postmain-s37-plan-receipt.json").read_text())
    assert plan["base_head"] == "670c2ee3c473cd2eb3f971bc2040356dc5060e06"
    assert plan["status"] == "PENDING_CI"
    assert plan["qualification_requires"] == "S37_REPORT.status == PASS"
    assert plan["real_world_incident_target"] == 3
    assert plan["real_mineflayer_session_target"] == 2
    assert plan["action_authority"] == "NONE"
