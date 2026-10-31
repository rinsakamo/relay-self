"""Offline S49 next L0 epoch receipt of provisional S50 Paper-only source."""
from __future__ import annotations

import asyncio
from dataclasses import replace

import pytest

from adapters.mineflayer.self_body_projection import project_body_action_readback
from adapters.mineflayer.self_body_s50_live_next_epoch import (
    LiveNextEpochLease,
    LiveNextEpochRejected,
)
from relay_self.action_outcome import ActionOutcomeDisposition
from relay_self.self_body import BodyOrigin, compose_self_body_view
from test_s50_live_paper_window import ACTION, SID, WORLD, capture, captured
from test_self_body import outcome
from test_self_body_s50_original_closure import synthetic_original_closed
from test_self_live_think import native_probe


def prior_body():
    o = replace(outcome(ActionOutcomeDisposition.OUTCOME), action_id=ACTION, session_id=SID)
    closed = synthetic_original_closed(action=ACTION, session=SID, interpretation=o)
    native = project_body_action_readback(closed.consequence, closed.interpretation)
    return compose_self_body_view(
        self_id="self", session_id=SID, epoch_id="original-s49-after",
        observation=native, outcome=o,
        minimum_native_seq=closed.consequence.before_observation.seq + 1,
    )


def next_source(*, seq=19, session=SID, event=24):
    return replace(
        native_probe(seq, 2.0, sid=session),
        request_id=f"s49-actual:{session}:event-{event}",
    )


def test_next_original_native_epoch_references_prior_s50_paper_provisionally():
    async def run():
        old = prior_body()
        window = capture()
        lease = LiveNextEpochLease(old, window)
        assert lease.status()["status"] == "WAITING_FOR_NEXT_ORIGINAL_S49_L0_NATIVE_PROBE"
        with pytest.raises(LiveNextEpochRejected):
            lease.take_once()
        reading = next_source()
        await lease.observe_original_l0_probe(reading)
        assert lease.status()["next_l0_provisional_paper_reads"] == 1
        result = lease.take_once()
        assert result.current_body.session_id == old.session_id
        assert result.current_body.epoch_id != old.epoch_id
        assert result.current_body.observation.native_seq == reading.seq
        assert result.current_body.observation.request_id == reading.request_id
        assert result.current_body.outcome is None
        assert result.current_world.self_body is result.current_body
        assert result.current_body.observed("position_x").origin is BodyOrigin.OBSERVATION
        assert result.current_body.observed("paper_motion").origin is BodyOrigin.UNKNOWN
        previous = result.read_previous_motion()
        assert previous["previous_action_id"] == ACTION
        assert previous["previous_paper_motion"] == (251, 252)
        assert previous["current_native_ref"].endswith(reading.request_id)
        assert previous["current_native_position_x"] == result.current_body.observed("position_x").value
        assert previous["source_status_at_decision"] == "PROVISIONAL_PAPER_ONLY"
        assert previous["full_node_trace_complete"] is False
        assert previous["paper_node_clock_alignment"] == "NOT_ATTESTED"
        assert previous["goal_admitted"] is False
        assert previous["p1_wait_admitted"] == 0
        assert previous["learning_updates"] == 0
        assert lease.status()["new_actions"] == 0
        audit = lease.postworld_audit(result, captured() + b"[INFO] end\n")
        assert audit["paper_prefix_matches_final_original"]
        assert audit["final_node_trace_still_requires_original_s50_owner"]
        with pytest.raises(LiveNextEpochRejected):
            lease.take_once()
    asyncio.run(run())


@pytest.mark.parametrize("attack", [
    "stale_seq", "foreign_session", "old_event", "same_event",
    "wrong_request", "missing_request", "non_probe", "not_typed",
])
def test_bad_next_original_l0_probe_never_changes_policy_or_mints_readout(attack):
    async def run():
        lease = LiveNextEpochLease(prior_body(), capture())
        reading = next_source()
        if attack == "stale_seq":
            reading = next_source(seq=12)
        elif attack == "foreign_session":
            reading = next_source(session="foreign")
        elif attack == "old_event":
            reading = next_source(event=22)
        elif attack == "same_event":
            reading = next_source(event=23)
        elif attack == "wrong_request":
            reading = replace(reading, request_id="operator-claimed-next")
        elif attack == "missing_request":
            reading = replace(reading, request_id=None)
        elif attack == "non_probe":
            reading = replace(reading, kind="health", request_id=None)
        elif attack == "not_typed":
            reading = {}
        await lease.observe_original_l0_probe(reading)
        assert lease.status()["status"] == "REVOKED_INVALID_NEXT_L0_EPOCH"
        assert lease.status()["new_native_probes"] == 0
        assert not lease.status()["l0_policy_modified"]
        with pytest.raises(LiveNextEpochRejected):
            lease.take_once()
    asyncio.run(run())


def test_wrong_prior_action_or_paper_session_rejected():
    body = prior_body()
    with pytest.raises(LiveNextEpochRejected):
        LiveNextEpochLease(replace(body, outcome=None), capture())
    with pytest.raises(LiveNextEpochRejected):
        LiveNextEpochLease(body, replace(capture(), paper_world_uuid=WORLD, action_id="other"))
    with pytest.raises(LiveNextEpochRejected):
        LiveNextEpochLease(body, replace(capture(), node_trace_complete=True))


def test_duplicate_existing_callback_revokes_tentative_source():
    async def run():
        lease = LiveNextEpochLease(prior_body(), capture())
        await lease.observe_original_l0_probe(next_source())
        await lease.observe_original_l0_probe(next_source(seq=25, event=25))
        with pytest.raises(LiveNextEpochRejected):
            lease.take_once()
    asyncio.run(run())


def test_missing_original_next_epoch_expires_without_actions():
    lease = LiveNextEpochLease(prior_body(), capture())
    lease.close()
    assert lease.status()["status"] == "EXPIRED_WITHOUT_NEXT_NATIVE_L0_EPOCH"
    with pytest.raises(LiveNextEpochRejected):
        lease.take_once()
