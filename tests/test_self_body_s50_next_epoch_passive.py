"""Read prior action's actual S50 diagnostic inside a NEW S49 probe epoch.

Synthetic native source fixtures only; real World must be tested separately.
No Action, native probe or provider is issued by this module.
"""
from __future__ import annotations

import asyncio
from dataclasses import replace

import pytest

from adapters.mineflayer.self_body_s50_motion_companion import (
    compose_self_body_s50_motion_companion,
)
from adapters.mineflayer.self_body_s50_next_epoch_passive import (
    SelfBodyS50NextEpochLease,
    SelfBodyS50NextEpochRejected,
)
from relay_self.self_body import BodyOrigin
from test_self_body_s50_motion_companion import existing_body, s50
from test_self_live_think import native_probe


def previous():
    return compose_self_body_s50_motion_companion(existing_body(), s50())


def probe(seq=19, session="S"):
    return native_probe(seq, 2.0, sid=session)


def test_new_native_epoch_reads_prior_motion_but_does_not_promote_paper_to_present():
    async def run():
        old = previous()
        lease = SelfBodyS50NextEpochLease(old)
        assert lease.status()["status"] == "WAITING_FOR_NEXT_ORIGINAL_S49_PROBE"
        assert lease.status()["readout_available"] is False
        with pytest.raises(SelfBodyS50NextEpochRejected):
            lease.take_readout_once()
        native = probe()
        await lease.observe_existing_s49_probe(native)
        assert lease.status()["status"] == "NEXT_ORIGINAL_NATIVE_EPOCH_READ_ONCE"
        assert lease.status()["next_native_source_read_count"] == 1
        readout = lease.take_readout_once()
        assert readout.previous_motion is old
        assert readout.current_body is readout.current_world.self_body
        assert readout.current_body.session_id == old.self_body.session_id
        assert readout.current_body.epoch_id != old.self_body.epoch_id
        assert readout.current_body.observation.native_seq == native.seq
        assert readout.current_body.observation.request_id == native.request_id
        assert readout.current_body.outcome is None
        assert readout.current_body.observed("position_x").origin is BodyOrigin.OBSERVATION
        assert readout.current_body.observed("paper_motion").origin is BodyOrigin.UNKNOWN
        assert readout.current_world.observation.native_seq == native.seq
        summary = readout.read_previous_motion()
        assert summary["previous_motion_changed_with_input_off"] == (251, 252)
        assert summary["prior_paper_samples_not_current_native_present"]
        assert summary["current_native_source_ref"].endswith(native.request_id)
        assert summary["current_epoch_id"] == readout.current_body.epoch_id
        assert summary["paper_node_world_clock_alignment"] == "NOT_ATTESTED"
        assert summary["prior_effective_s15_clear_tick"] == "NOT_ATTESTED"
        assert summary["full_tick_input_idle"] == "NOT_ATTESTED"
        assert summary["physical_stability"] == "UNPROVEN"
        assert summary["new_actions"] == 0
        assert summary["new_model_calls"] == 0
        assert summary["learning_updates"] == 0
        assert not summary["goal_admitted"]
        assert lease.status()["status"] == "NEXT_EPOCH_READOUT_CONSUMED"
        with pytest.raises(SelfBodyS50NextEpochRejected):
            lease.take_readout_once()
    asyncio.run(run())


@pytest.mark.parametrize("attack", (
    "same_native_seq", "older_native_seq", "foreign_session",
    "uncorrelated_request", "foreign_request", "non_probe",
    "missing_request", "non_typed", "session_relabel",
))
def test_bad_next_source_revokes_without_affecting_original_l0(attack):
    async def run():
        lease = SelfBodyS50NextEpochLease(previous())
        source = probe()
        if attack == "same_native_seq":
            source = probe(seq=8)
        elif attack == "older_native_seq":
            source = probe(seq=7)
        elif attack == "foreign_session":
            source = probe(session="T")
        elif attack == "uncorrelated_request":
            source = replace(source, request_id="unqualified")
        elif attack == "foreign_request":
            source = replace(source, request_id="s49-actual:T:event-18")
        elif attack == "non_probe":
            source = replace(source, kind="health", request_id=None)
        elif attack == "missing_request":
            source = replace(source, request_id=None)
        elif attack == "non_typed":
            source = object()
        elif attack == "session_relabel":
            source = replace(source, session_id="T")
        # No callback error is allowed to veto original native L0 behavior.
        await lease.observe_existing_s49_probe(source)
        assert lease.status()["status"] == "REVOKED_NEXT_NATIVE_EPOCH_SOURCE"
        assert not lease.status()["readout_available"]
        assert lease.status()["new_action_issuers"] == 0
        assert lease.status()["extra_native_probes"] == 0
        with pytest.raises(SelfBodyS50NextEpochRejected):
            lease.take_readout_once()
    asyncio.run(run())


def test_duplicate_callback_cannot_replay_or_reuse_one_slot():
    async def run():
        lease = SelfBodyS50NextEpochLease(previous())
        await lease.observe_existing_s49_probe(probe(19))
        await lease.observe_existing_s49_probe(probe(23))
        assert lease.status()["status"] == "REVOKED_NEXT_NATIVE_EPOCH_SOURCE"
        with pytest.raises(SelfBodyS50NextEpochRejected):
            lease.take_readout_once()
    asyncio.run(run())


def test_no_new_original_probe_expires_and_never_claims_next_epoch():
    lease = SelfBodyS50NextEpochLease(previous())
    lease.close()
    assert lease.status()["status"] == "EXPIRED_WITHOUT_NEXT_NATIVE_EPOCH"
    assert lease.status()["next_native_source_read_count"] == 0
    with pytest.raises(SelfBodyS50NextEpochRejected):
        lease.take_readout_once()


def test_reject_unqualified_previous_action_present():
    old = previous()
    with pytest.raises(SelfBodyS50NextEpochRejected):
        SelfBodyS50NextEpochLease(replace(old, native_present_minted=True))
    with pytest.raises(SelfBodyS50NextEpochRejected):
        SelfBodyS50NextEpochLease(replace(old, p1_wait_granted=True))
    with pytest.raises(SelfBodyS50NextEpochRejected):
        SelfBodyS50NextEpochLease(None)
