"""S41 prospective offline fail-closed controls; physical claim belongs to CI."""
from __future__ import annotations

import json
from dataclasses import replace
from pathlib import Path

import pytest

import test_postmain_s40_inflight_loss as s40
import test_postmain_two_epoch_continuation as s19
from relay_self.action import ActionState, InvalidTransition
from relay_self.execution_binding import ExecutionBinding
from relay_self.post_unknown_continuation import (
    PostUnknownContinuationGate,
    PostUnknownReentryGrant,
    PostUnknownReentryRejected,
)

ROOT = Path(__file__).resolve().parents[1]


def _unknown():
    fence, supervisor, _, issued, binding_result, command, consequence, failure = (
        s40._setup()
    )
    fence.observe_forced_failure(
        consequence.session_id, transport_error=failure, process_returncode=-9,
    )
    terminal, receipt = s40._close(
        fence, supervisor, issued, binding_result, command, consequence, failure,
    )
    assert terminal.state is ActionState.UNKNOWN
    return fence, supervisor, terminal, receipt


def _binding():
    return ExecutionBinding(
        binding_id="s41-distinct-binding", candidate_ref="MOVE_AWAY",
        required_intent_id="escape-threat",
        skill_execution_id="s41-distinct-skill",
        skill_ref="escape-movement",
        action_id="s41-distinct-action",
        action_ref="MOVE_BACKWARD",
        provenance=s19.provenance("s41-separate-new-action"),
    )


def _grant(unknown, receipt, event):
    return PostUnknownReentryGrant(
        authority_id="s41-independent-new-generation-authority",
        previous_action_id=unknown.action_id,
        previous_session_id=receipt.session_id,
        new_session_id=event.session_id,
        new_event_seq=event.event_seq,
        new_probe_seq=event.probe_seq,
        new_entity_id=event.entity_id,
        new_action_id="s41-distinct-action",
        new_binding_id="s41-distinct-binding",
        granted=True,
        provenance=s19.provenance("s41-explicit-third-generation-grant"),
    )


def test_unknown_cannot_spontaneously_promote_to_outcome():
    f, s, unknown, receipt = _unknown()
    gate = PostUnknownContinuationGate(f, s, unknown, receipt)
    assert gate is not None
    assert s.get(unknown.action_id) is unknown
    with pytest.raises(InvalidTransition):
        s.record_outcome(
            unknown.action_id, at_ns=60,
            provenance=s19.provenance("s41-illegal-retroactive-outcome"),
        )
    assert s.get(unknown.action_id).state is ActionState.UNKNOWN


def test_premature_third_action_without_new_source_fails():
    f, s, unknown, receipt = _unknown()
    gate = PostUnknownContinuationGate(f, s, unknown, receipt)
    # The native object is from a now-dead source, not a fresh revalidated
    # third session. It must never release another physical Action.
    _, _, _, _, stale = s40.s39._scenario()
    with pytest.raises(PostUnknownReentryRejected):
        gate.admit_new_action(stale, _binding(), _grant(unknown, receipt, stale))
    assert s.get(unknown.action_id) is unknown
    assert s.open_actions == ()


@pytest.mark.parametrize("modifier", (
    "no_grant", "wrong_previous_action", "wrong_previous_session",
    "wrong_new_action", "wrong_new_binding", "same_old_action",
    "same_old_skill",
))
def test_reentry_negative_lineage_rejected_without_issuing(modifier):
    f, s, unknown, receipt = _unknown()
    gate = PostUnknownContinuationGate(f, s, unknown, receipt)
    _, _, _, _, stale = s40.s39._scenario()
    binding = _binding()
    grant = _grant(unknown, receipt, stale)
    if modifier == "no_grant":
        grant = replace(grant, granted=False)
    elif modifier == "wrong_previous_action":
        grant = replace(grant, previous_action_id="some-other-old-action")
    elif modifier == "wrong_previous_session":
        grant = replace(grant, previous_session_id="foreign-stale-session")
    elif modifier == "wrong_new_action":
        grant = replace(grant, new_action_id="wrong-new-action")
    elif modifier == "wrong_new_binding":
        grant = replace(grant, new_binding_id="wrong-binding")
    elif modifier == "same_old_action":
        binding = replace(binding, action_id=unknown.action_id)
    elif modifier == "same_old_skill":
        binding = replace(binding, skill_execution_id=unknown.skill_execution_id)
    with pytest.raises(PostUnknownReentryRejected):
        gate.admit_new_action(stale, binding, grant)
    assert s.get(unknown.action_id).state is ActionState.UNKNOWN
    assert s.open_actions == ()


def test_unknown_receipt_must_match_exact_quarantined_action():
    f, s, unknown, receipt = _unknown()
    with pytest.raises(PostUnknownReentryRejected):
        PostUnknownContinuationGate(
            f, s, unknown, replace(receipt, session_id="forged-session"),
        )
    with pytest.raises(PostUnknownReentryRejected):
        PostUnknownContinuationGate(
            f, s, unknown, replace(receipt, replay_authorized=True),
        )
    with pytest.raises(PostUnknownReentryRejected):
        PostUnknownContinuationGate(
            f, s, unknown, replace(receipt, terminal_action_state="outcome"),
        )
    assert s.get(unknown.action_id).state is ActionState.UNKNOWN


def test_reentry_grant_never_treated_as_native_telemetry():
    f, s, unknown, receipt = _unknown()
    _, _, _, _, stale = s40.s39._scenario()
    grant = _grant(unknown, receipt, stale)
    bad = replace(
        grant, provenance=s19.Provenance(
            source="mineflayer", reference="fabricated-reentry-grant",
        ),
    )
    with pytest.raises(PostUnknownReentryRejected):
        PostUnknownContinuationGate(f, s, unknown, receipt).admit_new_action(
            stale, _binding(), bad,
        )


def test_static_plan_not_the_physical_receipt():
    receipt = json.loads(
        (ROOT / "docs/postmain-s41-plan-receipt.json").read_text(),
    )
    assert receipt["status"] == "PENDING_CI"
    assert receipt["base_head"] == "1c3127d0990f23f3514c2431fcde0dd3f3837e96"
    assert receipt["qualification_requires"] == "S41_REPORT.status == PASS"
    assert receipt["s31b_wsl2_reproduction"] == "SKIPPED"
