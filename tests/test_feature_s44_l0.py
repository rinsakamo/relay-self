"""S44 feature contract: native observation -> bounded decision/request only."""
from __future__ import annotations

from dataclasses import replace
from types import SimpleNamespace

import pytest

import test_postmain_s42_world_contrast as s42
from relay_self.provenance import Provenance
from relay_self.reactive_l0 import L0ActionGrant, ReactiveL0, ReactiveL0Rejected


def permit(choice, seq, *, intent="escape-threat", action="fresh-action"):
    return L0ActionGrant(
        authority_id="external-supervisor", action_id=action,
        intent_id=intent, session_id=choice.session_id, event_seq=seq,
        probe_seq=choice.probe_seq, entity_id=choice.entity_id,
        granted=True, provenance=Provenance("operator", "explicit-grant"),
    )


def test_wait_and_move_require_different_grant_and_fresh_evidence():
    retained, near, far, near_event, far_event = s42._pair()
    owner = ReactiveL0(near.observation.session_id, "escape-threat", retained)
    near_step = owner.decide(
        near_event, near.observation,
        grant=permit(
            s42.select_world_conditioned_choice(
                near, retained,
                expected_session_id=near.observation.session_id,
                expected_entity_id=near.entity_id,
            ),
            near_event.seq,
        ),
    )
    assert near_step.asks_for_action and owner.action_requests == 1
    far_step = owner.decide(far_event, far.observation)
    assert far_step.choice.selection.value == "WAIT"
    assert not far_step.asks_for_action and owner.action_requests == 1
    with pytest.raises(ReactiveL0Rejected):
        owner.decide(far_event, far.observation)


def test_no_move_without_authorization_or_with_foreign_grant():
    retained, near, _, event, _ = s42._pair()
    owner = ReactiveL0(near.observation.session_id, "escape-threat", retained)
    with pytest.raises(ReactiveL0Rejected):
        owner.decide(event, near.observation)
    choice = s42.select_world_conditioned_choice(
        near, retained, expected_session_id=near.observation.session_id,
        expected_entity_id=near.entity_id,
    )
    with pytest.raises(ReactiveL0Rejected):
        owner.decide(event, near.observation, grant=replace(
            permit(choice, event.seq), intent_id="not-committed-intent",
        ))
    assert owner.events == 0 and owner.action_requests == 0


@pytest.mark.parametrize("bad", ("foreign-session", "same-seq", "changed-id", "missing-probe"))
def test_bad_native_evidence_never_consumes_budget(bad):
    retained, near, _, event, _ = s42._pair()
    probe = near.observation
    owner = ReactiveL0(probe.session_id, "escape-threat", retained)
    if bad == "foreign-session":
        probe = replace(probe, session_id="foreign-session")
    elif bad == "same-seq":
        probe = replace(probe, seq=event.seq)
    elif bad == "changed-id":
        ent = replace(probe.snapshot.nearby_entities[0], entity_id=123)
        probe = replace(
            probe, snapshot=replace(probe.snapshot, nearby_entities=(ent,)),
        )
    else:
        probe = replace(probe, request_id=None, kind="entities")
    with pytest.raises((ReactiveL0Rejected, ValueError)):
        owner.decide(event, probe)
    assert owner.events == 0 and owner.action_requests == 0
