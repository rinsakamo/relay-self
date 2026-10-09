"""S42 offline parameter/identity checks. Physical near/far is CI-only."""
from __future__ import annotations

import json
from dataclasses import replace
from pathlib import Path

import pytest

import test_postmain_s35_event_cognition_gate as s35
import test_postmain_two_epoch_continuation as s19
from adapters.mineflayer.s34_native_world_cognition_ci import _native_threat
from relay_self.native_event_cognition import native_entity_event_to_cognition_candidate
from relay_self.world_conditioned_choice import (
    WorldChoiceKind,
    WorldChoiceRejected,
    select_world_conditioned_choice,
    verify_world_contrast,
)

ROOT = Path(__file__).resolve().parents[1]


def _pair():
    _, committed, _, _, _, _ = s19._epoch_one()
    event1, probe1 = s35._source(distance_m=2.0)
    event2, probe2 = s35._source(distance_m=10.0)
    old = probe1.snapshot.nearby_entities[0]
    current = probe2.snapshot.nearby_entities[0]
    current = replace(current, entity_id=old.entity_id + 10)
    probe2 = replace(
        probe2, session_id=probe1.session_id,
        seq=probe1.seq + 9,
        request_id="s42-far-offline-probe",
        snapshot=replace(probe2.snapshot, nearby_entities=(current,)),
    )
    event2 = replace(
        event2, session_id=probe1.session_id,
        seq=probe1.seq + 8,
        snapshot=probe2.snapshot,
    )
    near = _native_threat(
        probe1, probe1.request_id, expected_entity_id=old.entity_id,
    )
    far = _native_threat(
        probe2, probe2.request_id, expected_entity_id=current.entity_id,
    )
    return committed.new_state, near, far, event1, event2


def test_same_frozen_rev1_and_criterion_world_only_near_move_far_wait():
    retained, near_native, far_native, _, far_event = _pair()
    assert native_entity_event_to_cognition_candidate(far_event) is None
    near = select_world_conditioned_choice(
        near_native, retained,
        expected_session_id=near_native.observation.session_id,
        expected_entity_id=near_native.entity_id,
    )
    far = select_world_conditioned_choice(
        far_native, retained,
        expected_session_id=far_native.observation.session_id,
        expected_entity_id=far_native.entity_id,
    )
    verify_world_contrast(near, far)
    assert near.selection is WorldChoiceKind.MOVE_AWAY
    assert far.selection is WorldChoiceKind.WAIT
    assert near.wait_score == 8 and far.wait_score == 0
    assert near.move_score == far.move_score == 7
    assert near.retained_value == far.retained_value == 4
    assert near.retained_revision == far.retained_revision == 1
    assert not near.action_authorized and not far.action_authorized


@pytest.mark.parametrize("variant", (
    "foreign-session", "foreign-target", "request-id-mismatch",
    "native-distance-lie", "stale-revision", "altered-value",
))
def test_malformed_source_or_retained_cannot_adjudicate(variant):
    retained, near, _, _, _ = _pair()
    sid = near.observation.session_id
    eid = near.entity_id
    if variant == "foreign-session":
        sid = "foreign-node"
    elif variant == "foreign-target":
        eid += 4
    elif variant == "request-id-mismatch":
        near = replace(near, request_id="forged-request")
    elif variant == "native-distance-lie":
        near = replace(near, distance_m=7.0)
    elif variant == "stale-revision":
        retained = replace(retained, revision=0, last_update=None)
    elif variant == "altered-value":
        retained = replace(retained, value=3, last_update=None)
    with pytest.raises(WorldChoiceRejected):
        select_world_conditioned_choice(
            near, retained, expected_session_id=sid, expected_entity_id=eid,
        )


@pytest.mark.parametrize("variant", (
    "same-entity", "different-session", "same-probe", "same-choice",
    "different-retained", "same-provenance",
))
def test_contrast_fails_closed_on_confounds(variant):
    retained, n, f, _, _ = _pair()
    near = select_world_conditioned_choice(
        n, retained, expected_session_id=n.observation.session_id,
        expected_entity_id=n.entity_id,
    )
    far = select_world_conditioned_choice(
        f, retained, expected_session_id=f.observation.session_id,
        expected_entity_id=f.entity_id,
    )
    if variant == "same-entity":
        far = replace(far, entity_id=near.entity_id)
    elif variant == "different-session":
        far = replace(far, session_id="foreign-session")
    elif variant == "same-probe":
        far = replace(far, probe_seq=near.probe_seq)
    elif variant == "same-choice":
        far = replace(far, selection=WorldChoiceKind.MOVE_AWAY)
    elif variant == "different-retained":
        far = replace(far, retained_value=3)
    elif variant == "same-provenance":
        far = replace(far, provenance=near.provenance)
    with pytest.raises(WorldChoiceRejected):
        verify_world_contrast(near, far)


def test_prospective_plan_is_not_real_minecraft_receipt():
    r = json.loads((ROOT / "docs/postmain-s42-plan-receipt.json").read_text())
    assert r["status"] == "PENDING_CI"
    assert r["base_head"] == "d44a411829bcb03ed2d3307350b757186a7b6834"
    assert r["qualification_requires"] == "S42_REPORT.status == PASS"
    assert r["s31b_wsl2_reproduction"] == "SKIPPED"
