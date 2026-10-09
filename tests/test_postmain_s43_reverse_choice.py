"""S43 prospective reverse-world negative controls, no real World claims."""
from __future__ import annotations

import json
from dataclasses import replace
from pathlib import Path

import pytest

import test_postmain_s41_post_unknown as s41
import test_postmain_s42_world_contrast as s42
from relay_self.action import ActionState
from relay_self.reversed_world_choice import (
    ReversedWorldChoiceRejected,
    verify_far_then_near,
)
from relay_self.world_conditioned_choice import select_world_conditioned_choice

ROOT = Path(__file__).resolve().parents[1]


def _reverse_case():
    retained, native_near, native_far, _, far_event = s42._pair()
    # Offline: make another, later distinct near observation on same session.
    probe = replace(
        native_near.observation, seq=native_far.observation.seq + 5,
        request_id="s43-later-near-probe",
    )
    near_native = replace(
        native_near, observation=probe, request_id=probe.request_id,
    )
    near = select_world_conditioned_choice(
        near_native, retained,
        expected_session_id=probe.session_id, expected_entity_id=near_native.entity_id,
    )
    far = select_world_conditioned_choice(
        native_far, retained,
        expected_session_id=native_far.observation.session_id,
        expected_entity_id=native_far.entity_id,
    )
    f, supervisor, unknown, receipt = s41._unknown()
    return (
        far, near, far_event.seq, far.probe_seq + 2, f,
        supervisor, unknown, receipt,
    )


def test_reversed_far_wait_precedes_near_move_without_rewriting_unknown():
    far, near, far_event, near_event, _, supervisor, unknown, _ = _reverse_case()
    result = verify_far_then_near(
        far, near, far_event_seq=far_event, near_event_seq=near_event,
        supervisor=supervisor, prior_unknown=unknown,
    )
    assert result.first_choice == "WAIT"
    assert result.second_choice == "MOVE_AWAY"
    assert result.far_event_seq < result.far_probe_seq
    assert result.far_probe_seq < result.near_event_seq < result.near_probe_seq
    assert result.far_entity_id != result.near_entity_id
    assert result.same_retained_revision == 1
    assert result.same_retained_value == 4
    assert result.far_action_issued is False
    assert result.historic_unknown_reclassified is False
    assert supervisor.get(unknown.action_id).state is ActionState.UNKNOWN
    assert supervisor.open_actions == ()


@pytest.mark.parametrize("variant", (
    "far_later_than_near", "same_probe", "near_event_before_far",
    "near_event_equal_far_probe", "same_entity", "wrong_session",
    "changed_retained", "mislabeled_far", "mislabeled_near", "untrusted_old_action",
))
def test_reversed_gate_rejects_invalid_chronology_source_or_history(variant):
    far, near, far_event, near_event, _, supervisor, unknown, _ = _reverse_case()
    if variant == "far_later_than_near":
        far_event = near.probe_seq + 1
    elif variant == "same_probe":
        near = replace(near, probe_seq=far.probe_seq)
    elif variant == "near_event_before_far":
        near_event = far_event
    elif variant == "near_event_equal_far_probe":
        near_event = far.probe_seq
    elif variant == "same_entity":
        near = replace(near, entity_id=far.entity_id)
    elif variant == "wrong_session":
        near = replace(near, session_id="foreign-current-node")
    elif variant == "changed_retained":
        near = replace(near, retained_revision=0)
    elif variant == "mislabeled_far":
        far = replace(far, selection=near.selection)
    elif variant == "mislabeled_near":
        near = replace(near, selection=far.selection)
    elif variant == "untrusted_old_action":
        unknown = replace(unknown, state=ActionState.ISSUED)
    with pytest.raises(ReversedWorldChoiceRejected):
        verify_far_then_near(
            far, near, far_event_seq=far_event, near_event_seq=near_event,
            supervisor=supervisor, prior_unknown=unknown,
        )


def test_s43_static_prospective_gate_is_not_a_physical_pass():
    data = json.loads((ROOT / "docs/postmain-s43-plan-receipt.json").read_text())
    assert data["status"] == "PENDING_CI"
    assert data["base_head"] == "0b46d6b3c42c43c004ce00e29c571a0cb0821ab6"
    assert data["qualification_requires"] == "S43_REPORT.status == PASS"
    assert data["s31b_wsl2_reproduction"] == "SKIPPED"
