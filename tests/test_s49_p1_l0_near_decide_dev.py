"""One real native near L0.decide with an isolated, non-dispatchable grant."""
from __future__ import annotations

from dataclasses import replace

import pytest

from adapters.mineflayer.m02_paper_dev.s50_boundary import BoundaryRejected
from adapters.mineflayer.s49_p1_l0_near_decide_dev import (
    decide_bounded_near_move_dev,
)
from experiments.fatigue_p1 import FatigueProfile
from relay_self.provenance import Provenance
from relay_self.reactive_l0 import L0ActionGrant
from test_s49_p1_l0_fresh_pair_dev import source


def shadow_grant(event, probe):
    return L0ActionGrant(
        authority_id=f"dev-shadow-only:{event.session_id}:{event.seq}",
        action_id=f"dev-shadow-no-dispatch:{event.session_id}:{event.seq}",
        intent_id="escape-threat",
        session_id=event.session_id,
        event_seq=event.seq, probe_seq=probe.seq,
        entity_id=event.snapshot.nearby_entities[0].entity_id,
        granted=True,
        provenance=Provenance(
            "dev-independent-shadow-only-not-s49-issuer",
            f"{event.session_id}:event-{event.seq}:operator-scoped-dev",
        ),
    )


def evaluate(monkeypatch, *, distance=2.0, bad=None):
    event, probe, prior, body, handoff, p1, retained = source(
        monkeypatch, distance=distance,
    )
    grant = shadow_grant(event, probe)
    if bad == "stale_seq":
        grant = replace(grant, probe_seq=probe.seq - 1)
    elif bad == "wrong_action":
        grant = replace(grant, action_id="an-executable-looking-action")
    elif bad == "other_entity":
        grant = replace(grant, entity_id=987654)
    elif bad == "foreign_session":
        grant = replace(grant, session_id="wrong-session")
    elif bad == "ungranted":
        grant = replace(grant, granted=False)
    elif bad == "wrong_provenance":
        grant = replace(
            grant, provenance=Provenance("s49-independent-operator", "wrong"),
        )
    elif bad == "old_paper":
        p1["paper_window_sha256"] = "altered"
    return decide_bounded_near_move_dev(
        event, probe, prior_postwait_probe=prior,
        body=body, handoff=handoff, p1_reviewed=p1,
        profile=FatigueProfile(enabled=True, initial=0.0),
        retained=retained, operator_shadow_grant=grant,
    )


def test_genuine_near_event_uses_original_bounded_decide_without_dispatch(monkeypatch):
    out = evaluate(monkeypatch)
    assert out["status"] == "DEV_REAL_NATIVE_BOUNDED_L0_MOVE_REQUEST_NO_EXECUTION"
    assert out["original_s42_selection"] == "MOVE_AWAY"
    assert out["bounded_dev_l0_decide_called"] is True
    assert out["bounded_dev_l0_events"] == 1
    assert out["bounded_dev_l0_action_requests"] == 1
    assert out["fresh_event_seq"] < out["fresh_probe_seq"]
    assert out["logical_shadow_action_id"].startswith("dev-shadow-no-dispatch:")
    assert out["logical_dev_grant_used"] is True
    assert out["logical_dev_grant_source"] == (
        "dev-independent-shadow-only-not-s49-issuer"
    )
    assert out["s49_execution_authorization_issued"] is False
    assert out["normal_action_executor_called"] is False
    assert out["physical_action_issued"] is False
    assert out["original_s49_l0_owner_replaced"] is False
    assert out["additional_native_receivers"] == 0
    assert out["additional_native_probes"] == 0
    assert out["p1_modeled_not_native"] is True
    assert out["p1_model_changes_s42_choice"] is False
    assert out["qualification_go"] is False
    assert out["science_go"] is False


@pytest.mark.parametrize("bad", (
    "stale_seq", "wrong_action", "other_entity", "foreign_session",
    "ungranted", "wrong_provenance", "old_paper",
))
def test_grant_or_source_mismatch_never_mints_near_move_request(monkeypatch, bad):
    with pytest.raises(BoundaryRejected):
        evaluate(monkeypatch, bad=bad)


def test_far_world_cannot_issue_near_shadow_grant(monkeypatch):
    with pytest.raises(BoundaryRejected, match="fresh MOVE choice"):
        evaluate(monkeypatch, distance=10.0)
