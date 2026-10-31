"""Original S49 L0 run_session -> existing live_probe -> passive M/L8 seam.

Uses the *actual pinned original S49 NormalWorldL0.run_session*, original S
B0 producer and L8 observer in the SAME Python process. Input frames are
synthetic and the Action callback is a NO-ISSUE local witness. This is
not a real Minecraft server, S49 Action execution or runtime deployment.
"""
from __future__ import annotations

import asyncio
from dataclasses import replace
from types import SimpleNamespace

import pytest
import test_metabolism_same_process_slm_product as slm
import test_postmain_s42_world_contrast as s42
from adapters.mineflayer.normal_action import NormalWorldL0
from relay_self.provenance import Provenance
from relay_self.reactive_l0 import L0ActionGrant

from experiments.metabolism_s49_live_probe_bridge import S49PassiveSourceLease
from experiments.metabolism_slm_dev_host_tap import bounded_s_l_m_audit_row


def owner_handoff(data, lease, **kwargs):
    (_, ledger, decision, _probe, s, _supervisor, _views, _resource,
     learned, native, retained, *_rest) = data
    args = dict(
        original_s_epoch=s, native=native,
        ledger=ledger, original_b0_decision=decision,
        retained=retained,
        self_id=learned.cognition.identity.self_id,
        epoch_id=f"one-s49-after-s-{native.observation.seq}",
        learning=learned, retention_enabled=True, noise_bound=0,
    )
    args.update(kwargs)
    return lease.observe_after_original_s_epoch(**args)


def test_actual_original_s49_l0_session_receives_same_probe_before_choice():
    data = slm.common_epoch(energy=0.6)
    probe = data[3]
    retained, fixture_native, _, event, _ = s42._pair()
    assert fixture_native.observation == probe
    assert retained == data[10]
    lease = S49PassiveSourceLease(enabled=True)

    class OneNativeEvent:
        started = SimpleNamespace(session_id=probe.session_id)

        def __init__(self):
            self.reads = 0

        async def receive(self):
            self.reads += 1
            assert self.reads == 1
            return event

    native_source = OneNativeEvent()
    l0 = NormalWorldL0(
        probe.session_id, "escape-threat", retained,
        max_events=1, max_action_requests=1,
    )
    action_requests = []

    async def reprobe(s49_event):
        assert s49_event is event
        await lease.observe(probe)  # original S49 live_probe callback position
        assert lease.summary().status == "CAPTURED"
        assert lease._last_probe is probe
        return probe  # same object to S49 original L0, zero extra native reads

    def grant(choice, event_seq):
        return L0ActionGrant(
            authority_id="synthetic-operator-grant",
            action_id="not-executed-physical-action",
            intent_id="escape-threat",
            session_id=probe.session_id, event_seq=event_seq,
            probe_seq=choice.probe_seq, entity_id=choice.entity_id,
            granted=True, provenance=Provenance("synthetic-dev", "not-native"),
        )

    async def on_action_request(step):
        # A request witness, NOT executor.execute or an S49 outcome receipt.
        action_requests.append(step)

    async def run():
        return await l0.run_session(
            native_source, probe=reprobe, grant=grant,
            on_action_request=on_action_request, max_frames=1,
        )

    before = (data[1].body, data[1].credit_count, data[5].open_actions)
    steps = asyncio.run(run())
    assert len(steps) == 1
    assert steps[0].choice.selection.value == "MOVE_AWAY"
    assert steps[0].choice.probe_seq == probe.seq
    assert action_requests == [steps[0]]
    assert l0.events == l0.action_requests == 1
    assert native_source.reads == 1

    # This S42 result and B0 owner decision already existed BEFORE the tap:
    # no extra native query, S coordination, Action issue or M0 owner advance.
    output = owner_handoff(data, lease)
    assert output.status == "RECORDED"
    assert output.original_s_epoch is data[4]
    assert output.s_choice == steps[0].choice.selection.value
    assert output.l1_candidate == "WAIT"
    assert output.m_model_tension == "MOVE_MODEL_INSUFFICIENT"
    assert bounded_s_l_m_audit_row(output)["action_issues"] == 0
    assert lease.summary().status == "CONSUMED"
    assert before == (data[1].body, data[1].credit_count, data[5].open_actions)
    assert native_source.reads == 1
    assert len(action_requests) == 1


def test_s49_callback_disabled_does_not_inspect_any_probe():
    class NeverAccess:
        def __getattribute__(self, name):
            raise AssertionError("disabled S49 callback read forbidden")

    lease = S49PassiveSourceLease()
    asyncio.run(lease.observe(NeverAccess()))
    summary = lease.summary()
    assert summary.status == "DISABLED"
    assert summary.accepted_probes == summary.rejected_probes == 0
    source = object()
    result = lease.observe_after_original_s_epoch(
        original_s_epoch=source, native=NeverAccess(), ledger=NeverAccess(),
        original_b0_decision=NeverAccess(), retained=NeverAccess(),
        self_id="none", epoch_id="none",
    )
    assert result.status == "DISABLED" and result.original_s_epoch is source


def test_new_s49_live_probe_invalidates_older_source_before_m_join():
    data = slm.common_epoch()
    lease = S49PassiveSourceLease(enabled=True)
    source = data[3]
    async def receive():
        await lease.observe(source)
        newer = replace(source, seq=source.seq + 3, request_id="next-epoch")
        await lease.observe(newer)
        assert lease._last_probe is newer
    asyncio.run(receive())
    result = owner_handoff(data, lease)
    assert result.status == "DEFERRED"
    assert result.original_s_epoch is data[4]
    assert lease.summary().status == "CONSUMED"
    assert bounded_s_l_m_audit_row(result)["session_id"] is None
    assert owner_handoff(data, lease).status == "DEFERRED"


@pytest.mark.parametrize("attack", (
    "replay", "foreign", "non_probe", "bad_provenance", "over_budget",
))
def test_s49_bad_or_stale_source_never_reuses_last_valid_probe(attack):
    data = slm.common_epoch()
    probe = data[3]
    lease = S49PassiveSourceLease(enabled=True, max_probes=1)
    async def run():
        await lease.observe(probe)
        if attack == "replay":
            await lease.observe(probe)
        elif attack == "foreign":
            await lease.observe(replace(probe, session_id="other-session"))
        elif attack == "non_probe":
            await lease.observe(replace(probe, kind="entities", request_id=None))
        elif attack == "bad_provenance":
            await lease.observe(replace(probe, provenance=Provenance(
                "synthetic-attacker", "bad",
            )))
        else:
            await lease.observe(replace(probe, seq=probe.seq + 4))
    asyncio.run(run())
    assert lease.summary().status == "REJECTED"
    assert lease.summary().accepted_probes == 1
    assert lease.summary().rejected_probes == 1
    assert owner_handoff(data, lease).status == "DEFERRED"
    assert data[1].credit_count == 0
    assert data[5].open_actions == ()


def test_s49_prechoice_source_without_s_b0_owner_epoch_must_defer():
    data = slm.common_epoch()
    lease = S49PassiveSourceLease(enabled=True)
    asyncio.run(lease.observe(data[3]))
    result = owner_handoff(data, lease, original_b0_decision=None)
    assert result.status == "DEFERRED"
    assert result.original_s_epoch is data[4]
    assert result.action_issues == result.food_credits == 0


def test_s49_source_lease_rejects_unauthorized_switches():
    with pytest.raises(ValueError):
        S49PassiveSourceLease(enabled="yes")
    with pytest.raises(ValueError):
        S49PassiveSourceLease(enabled=True, max_probes=1000)
    with pytest.raises(ValueError):
        S49PassiveSourceLease(enabled=True, max_probes=True)
