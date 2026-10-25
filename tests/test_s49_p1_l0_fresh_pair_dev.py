"""Fresh real native L0 event/probe check after Paper WAIT, no grants."""
from __future__ import annotations

from dataclasses import replace

import pytest

import test_postmain_two_epoch_continuation as s19
from adapters.mineflayer.m02_paper_dev.s50_boundary import BoundaryRejected
from adapters.mineflayer.s49_p1_l0_fresh_pair_dev import (
    review_postwait_fresh_l0_input_dev,
)
from adapters.mineflayer.s49_p1_self_body_dev import (
    compose_s49_p1_postwait_native_dev,
)
from experiments.fatigue_p1 import FatigueProfile
from test_s49_p1_self_body_dev import correlated_next_native
from test_self_live_think import native_probe


def source(monkeypatch, *, distance=2.0):
    handoff, p1, action, prior, req = correlated_next_native(monkeypatch)
    body, _ = compose_s49_p1_postwait_native_dev(
        handoff, p1, action, prior, expected_request_id=req,
    )
    event_seq = prior.seq + 3
    event_source = native_probe(event_seq, distance, sid=handoff.session_id)
    event = replace(event_source, kind="entities", request_id=None)
    # A genuinely different/new target (not the prior S49 target)
    earlier_ids = {e.entity_id for e in prior.snapshot.nearby_entities}
    assert event_seq not in earlier_ids
    probe_seq = event_seq + 2
    reading = native_probe(probe_seq, 2.0, sid=handoff.session_id)
    snap = replace(
        reading.snapshot,
        nearby_entities=event.snapshot.nearby_entities,
        nearby_entities_coverage=event.snapshot.nearby_entities_coverage,
    )
    probe = replace(
        reading, snapshot=snap,
        request_id=f"s49-postwait-event:{handoff.session_id}:{event.seq}",
    )
    retained = s19._epoch_one()[1].new_state
    return event, probe, prior, body, handoff, p1, retained


def evaluate(event, probe, prior, body, handoff, p1, retained):
    return review_postwait_fresh_l0_input_dev(
        event, probe,
        prior_postwait_probe=prior,
        body=body,
        handoff=handoff,
        p1_reviewed=p1,
        profile=FatigueProfile(enabled=True, initial=0.0),
        retained=retained,
    )


def test_fresh_native_source_reaches_original_l0_guard_without_deciding(monkeypatch):
    event, probe, prior, body, handoff, p1, retained = source(monkeypatch)
    out = evaluate(event, probe, prior, body, handoff, p1, retained)
    assert out["status"] == "DEV_REAL_NATIVE_POSTWAIT_FRESH_L0_INPUT_PAIRED"
    assert out["fresh_event_seq"] > out["prior_native_seq"]
    assert out["fresh_probe_seq"] > out["fresh_event_seq"]
    assert out["fresh_probe_request_id"] == probe.request_id
    assert out["fresh_zombie_entity_id"] == event.snapshot.nearby_entities[0].entity_id
    assert out["fresh_s42_selection"] == "MOVE_AWAY"
    assert out["fresh_native_event_and_probe"] is True
    assert out["original_l0_input_checked"] is True
    assert out["original_l0_decide_called"] is False
    assert out["bounded_dev_shadow_l0_decide_called"] is False
    assert out["bounded_dev_shadow_l0_decision"] is None
    assert out["bounded_dev_shadow_l0_events"] == 0
    assert out["bounded_dev_shadow_l0_action_requests"] == 0
    assert out["original_s49_host_l0_replaced"] is False
    assert out["new_l0_owner_registered"] is False
    assert out["new_action_grant_issued"] is False
    assert out["new_action_issued"] is False
    assert out["extra_native_probes"] == 1
    assert out["extra_protocol_receivers"] == 0
    assert out["p1_model_attested"] is False
    assert out["paper_native_tick_equivalence"] is False
    assert out["postwait_p1_capability_pct_model_only"] == 100
    assert out["qualification_go"] is False


@pytest.mark.parametrize("bad", (
    "foreign_session", "old_event", "old_probe", "wrong_request",
    "wrong_kind", "reused_zombie", "wrong_target", "missing_target",
    "foreign_profile", "missing_model", "foreign_paper",
))
def test_fresh_pair_rejects_malformed_stale_or_replayed_sources(monkeypatch, bad):
    event, probe, prior, body, handoff, p1, retained = source(monkeypatch)
    profile = FatigueProfile(enabled=True, initial=0.0)
    if bad == "foreign_session":
        event = replace(event, session_id="foreign")
    elif bad == "old_event":
        event = replace(event, seq=prior.seq)
    elif bad == "old_probe":
        probe = replace(probe, seq=event.seq)
    elif bad == "wrong_request":
        probe = replace(probe, request_id="unrelated-request")
    elif bad == "wrong_kind":
        event = replace(event, kind="probe", request_id="other")
    elif bad == "reused_zombie":
        same = prior.snapshot.nearby_entities[0]
        event = replace(event, snapshot=replace(
            event.snapshot, nearby_entities=(same,),
        ))
    elif bad == "wrong_target":
        different = replace(probe.snapshot.nearby_entities[0], entity_id=99999)
        probe = replace(probe, snapshot=replace(
            probe.snapshot, nearby_entities=(different,),
        ))
    elif bad == "missing_target":
        probe = replace(probe, snapshot=replace(
            probe.snapshot,
            nearby_entities=(),
            nearby_entities_coverage=replace(
                probe.snapshot.nearby_entities_coverage,
                candidate_count=0,
            ),
        ))
    elif bad == "foreign_profile":
        profile = FatigueProfile(enabled=True, initial=0.2)
    elif bad == "missing_model":
        body = replace(body, hypotheses=())
    else:
        p1["paper_window_sha256"] = "unbound-paper"
    with pytest.raises(BoundaryRejected):
        review_postwait_fresh_l0_input_dev(
            event, probe, prior_postwait_probe=prior,
            body=body, handoff=handoff, p1_reviewed=p1,
            profile=profile, retained=retained,
        )


def test_far_fresh_native_event_exercises_original_l0_wait_decide_without_grant(monkeypatch):
    event, probe, prior, body, handoff, p1, retained = source(
        monkeypatch, distance=10.0,
    )
    result = evaluate(event, probe, prior, body, handoff, p1, retained)
    assert result["fresh_s42_selection"] == "WAIT"
    assert result["fresh_s42_distance_m"] == pytest.approx(10.0)
    assert result["bounded_dev_shadow_l0_decide_called"] is True
    assert result["bounded_dev_shadow_l0_decision"] == "WAIT"
    assert result["bounded_dev_shadow_l0_events"] == 1
    assert result["bounded_dev_shadow_l0_action_requests"] == 0
    assert result["original_s49_host_l0_replaced"] is False
    assert result["original_l0_decide_called"] is False
    assert result["new_action_grant_issued"] is False
    assert result["new_action_issued"] is False
    assert result["extra_protocol_receivers"] == 0
    assert result["p1_model_attested"] is False


def test_near_real_l0_move_request_requires_independent_grant_and_is_not_called(monkeypatch):
    event, probe, prior, body, handoff, p1, retained = source(monkeypatch)
    from relay_self.reactive_l0 import ReactiveL0, ReactiveL0Rejected

    # Direct original API, without a grant, must never permit near MOVE.
    original_gate = ReactiveL0(handoff.session_id, "escape-threat", retained)
    with pytest.raises(ReactiveL0Rejected, match="fresh independent Action grant"):
        original_gate.decide(event, probe, grant=None)
    assert original_gate.events == 0
    assert original_gate.action_requests == 0
    result = evaluate(event, probe, prior, body, handoff, p1, retained)
    assert result["fresh_s42_selection"] == "MOVE_AWAY"
    assert result["bounded_dev_shadow_l0_decide_called"] is False
    assert result["new_action_grant_issued"] is False
