"""S35 event->cognition one-shot admission; no live Minecraft in pytest."""
from __future__ import annotations

from dataclasses import replace
from pathlib import Path

import pytest

import test_postmain_source_native_world as s27
import test_postmain_two_epoch_continuation as s19
from adapters.mineflayer.python_protocol import MineflayerAdapterProtocolError
from adapters.mineflayer.s34_native_world_cognition_ci import (
    _native_epoch_two,
    _native_threat,
)
from relay_self.action_supervision import ActionSupervisor, UnknownSupervisedAction
from relay_self.native_event_cognition import (
    EventCognitionLedger,
    EventCognitionNotAdmitted,
    EventCognitionTriggerGrant,
    InvalidEventCognitionEvidence,
    native_entity_event_to_cognition_candidate,
)

ROOT = Path(__file__).resolve().parents[1]


def _source(*, distance_m=2.0):
    _, _, _, args = s27._fixture(distance_m=distance_m)
    native = args["observation"]
    event = replace(native, kind="entities", request_id=None)
    probe = replace(native, kind="probe", request_id="s35-check:001", seq=event.seq + 1)
    return event, probe


def _grant(candidate, *, granted=True):
    return EventCognitionTriggerGrant(
        authority_id="s35-distinct-authority",
        candidate_id=candidate.candidate_id,
        session_id=candidate.session_id,
        event_seq=candidate.event_seq,
        target_entity_id=candidate.target_entity_id,
        granted=granted,
        provenance=s19.provenance("s35-distinct-grant"),
    )


def test_unsolicited_native_entities_event_yields_exact_cognition_candidate():
    event, probe = _source()
    candidate = native_entity_event_to_cognition_candidate(event)
    assert candidate is not None
    assert candidate.event_seq == event.seq
    assert candidate.session_id == event.session_id
    assert candidate.distance_m == 2.0
    assert candidate.source_provenance == event.provenance
    assert "entity-" in candidate.candidate_id
    ledger = EventCognitionLedger()
    ticket = ledger.admit(candidate, probe, _grant(candidate), request_id="s35-check:001")
    assert ticket.event_id == candidate.candidate_id
    assert ticket.correlated_probe.seq > event.seq


@pytest.mark.parametrize("kind", ["move", "time", "spawn", "health", "probe"])
def test_non_entity_events_do_not_create_cognition_work(kind):
    event, _ = _source()
    event = replace(event, kind=kind, request_id="s35-check:001" if kind == "probe" else None)
    assert native_entity_event_to_cognition_candidate(event) is None


def test_missing_or_far_zombie_cannot_be_inferred_as_unsafe_or_safe():
    far, _ = _source(distance_m=5.0)
    assert native_entity_event_to_cognition_candidate(far) is None
    near, _ = _source()
    snapshot = near.snapshot
    coverage = replace(snapshot.nearby_entities_coverage, candidate_count=0)
    empty = replace(near, snapshot=replace(
        snapshot, nearby_entities=(), nearby_entities_coverage=coverage,
    ))
    assert native_entity_event_to_cognition_candidate(empty) is None


def test_invalid_truncation_rejected_by_earlier_typed_protocol_boundary():
    event, _ = _source()
    coverage = replace(event.snapshot.nearby_entities_coverage, truncated=True)
    with pytest.raises(MineflayerAdapterProtocolError):
        replace(event.snapshot, nearby_entities_coverage=coverage)


@pytest.mark.parametrize("change", [
    "grant_denied", "grant_event_seq", "grant_entity", "grant_provenance",
    "wrong_probe_id", "probe_old_seq", "probe_other_session",
    "probe_identity_changed", "probe_outside_threat",
])
def test_no_cognition_if_trigger_or_proof_not_exact(change):
    event, probe = _source()
    candidate = native_entity_event_to_cognition_candidate(event)
    assert candidate is not None
    grant = _grant(candidate)
    request_id = "s35-check:001"
    if change == "grant_denied":
        grant = replace(grant, granted=False)
    elif change == "grant_event_seq":
        grant = replace(grant, event_seq=grant.event_seq + 1)
    elif change == "grant_entity":
        grant = replace(grant, target_entity_id=grant.target_entity_id + 1)
    elif change == "grant_provenance":
        grant = replace(grant, provenance=candidate.source_provenance)
    elif change == "wrong_probe_id":
        request_id = "s35-wrong:001"
    elif change == "probe_old_seq":
        probe = replace(probe, seq=event.seq)
    elif change == "probe_other_session":
        probe = replace(probe, session_id="different-node-session")
    elif change == "probe_identity_changed":
        entity = replace(
            probe.snapshot.nearby_entities[0],
            entity_id=candidate.target_entity_id + 50,
        )
        probe = replace(probe, snapshot=replace(
            probe.snapshot, nearby_entities=(entity,),
        ))
    elif change == "probe_outside_threat":
        _, probe = _source(distance_m=5.0)
    with pytest.raises((EventCognitionNotAdmitted, InvalidEventCognitionEvidence)):
        EventCognitionLedger().admit(
            candidate, probe, grant, request_id=request_id,
        )


def test_replay_and_session_local_stale_cursor_are_fail_closed():
    event, probe = _source()
    candidate = native_entity_event_to_cognition_candidate(event)
    assert candidate is not None
    ledger = EventCognitionLedger()
    grant = _grant(candidate)
    ledger.admit(candidate, probe, grant, request_id=probe.request_id)
    with pytest.raises(EventCognitionNotAdmitted):
        ledger.admit(candidate, probe, grant, request_id=probe.request_id)


def test_admitted_event_can_run_existing_cognition_without_action_issue():
    event, probe = _source()
    candidate = native_entity_event_to_cognition_candidate(event)
    assert candidate is not None
    ticket = EventCognitionLedger().admit(
        candidate, probe, _grant(candidate), request_id=probe.request_id,
    )
    native = _native_threat(ticket.correlated_probe, ticket.probe_request_id)
    supervisor = ActionSupervisor()
    intent = s19.IntentCommitment()
    intent.commit(
        "escape-threat", objective="escape the nearby threat",
        at_ns=1, provenance=s19.provenance("s35-offline-intent"),
    )
    # A rev1 read requires the real governed-commit record from the
    # frozen S19 deterministic history, not a fabricated revision field.
    past_supervisor, committed, _intent, closed, _feedback, _result = s19._epoch_one()
    assert past_supervisor.get(closed.action_id) is closed
    retained = committed.new_state
    outputs, epoch = _native_epoch_two(
        supervisor, intent, retained, retained,
        expected_revision=1, native=native,
    )
    assert outputs["external"][1].provenance == probe.provenance
    assert outputs["plan"].selected.candidate_id == "MOVE_AWAY"
    assert outputs["admission"].status.value == "admitted"
    assert epoch.cognition_requested is False
    assert supervisor.open_actions == ()
    with pytest.raises(UnknownSupervisedAction):
        supervisor.get("s35-action")


def test_static_plan_cannot_claim_live_world_pass():
    import json

    plan = json.loads((ROOT / "docs/postmain-s35-plan-receipt.json").read_text())
    assert plan["status"] == "PENDING_CI"
    assert plan["base_head"] == "a5fbec611caf86231e95932adf8e7fdf3a6ef099"
    assert plan["qualification_requires"] == "S35_REPORT.status == PASS"
    assert plan["no_automatic_action_issue"] is True
