"""Offline original owner wiring. No physical execution claim."""
import asyncio

import pytest

import test_postmain_s42_world_contrast as s42
from adapters.mineflayer.normal_action import NormalWorldL0
from adapters.mineflayer.slm_passive_dev import S49SLMDevOwner
from relay_self.action_supervision import ActionSupervisor
from relay_self.provenance import Provenance
from relay_self.reactive_l0 import L0ActionGrant


def setup():
    retained, native, _, event, _ = s42._pair()
    host = NormalWorldL0(native.observation.session_id, "escape-threat", retained)
    owner = S49SLMDevOwner()
    supervisor = ActionSupervisor()
    owner.bind(host, supervisor)
    return owner, host, supervisor, native, event


def decide(owner, host, native, event):
    probe = native.observation
    asyncio.run(owner.observe(probe))
    choice = host._check(event, probe)  # existing preliminary grant check
    grant = L0ActionGrant(
        authority_id="offline", action_id="offline-action", intent_id=host.intent_id,
        session_id=host.session_id, event_seq=event.seq,
        probe_seq=probe.seq, entity_id=choice.entity_id, granted=True,
        provenance=Provenance("synthetic", "offline-no-issuer"),
    )
    return host.decide(event, probe, grant=grant)


def test_real_owner_choice_coordinator_and_post_loop_join():
    owner, host, supervisor, native, event = setup()
    step = decide(owner, host, native, event)
    assert step.choice.selection.value == "MOVE_AWAY"
    assert host.events == host.action_requests == 1
    assert owner.ledger._last_decision_seq == -1  # no B0 before Action
    assert supervisor.open_actions == ()
    assert len(owner.pending) == 1
    epoch = owner.pending[0][3]
    assert epoch.cognition_result is step.choice
    result = owner.finish([{"probe_seq": native.observation.seq, "terminal": "UNKNOWN"}])
    assert result["observer_errors"] == 0
    row = result["rows"][0]
    assert row["status"] == "RECORDED"
    assert row["l1_status"] == "retention_off"
    assert row["action_outcomes"][0]["terminal"] == "UNKNOWN"
    assert row["action_issues"] == row["learning_updates"] == row["food_credits"] == 0
    assert not row["native_source_attested"]
    assert owner.ledger.credit_count == 0
    assert not owner.pending
    with pytest.raises(ValueError):
        owner.finish([])


def test_missing_capture_does_not_change_original_choice():
    owner, host, supervisor, native, event = setup()
    expected = host._check(event, native.observation)
    actual = owner.coordinate_original_choice(native, host.retained, lambda _: expected)
    assert actual is expected
    assert owner.errors == 1 and not owner.pending


def test_passive_failure_after_actions_is_contained(monkeypatch):
    owner, host, _, native, event = setup()
    step = decide(owner, host, native, event)
    def fail(_):
        raise RuntimeError("diagnostic failure")
    monkeypatch.setattr(owner.ledger, "decide", fail)
    result = owner.finish([])
    assert result["observer_errors"] == 1
    assert step.choice.selection.value == "MOVE_AWAY"
    assert host.action_requests == 1


def test_owner_cannot_bind_twice():
    owner, host, supervisor, _, _ = setup()
    with pytest.raises(ValueError):
        owner.bind(host, supervisor)
