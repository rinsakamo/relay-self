"""S40 offline negative cases; only real Minecraft CI proves actual SIGKILL.

These are *simulated typed receipts*, never physical evidence.
"""
from __future__ import annotations

import json
from dataclasses import replace
from pathlib import Path

import pytest

import test_postmain_second_action_closure as s20
import test_postmain_two_epoch_continuation as s19
from adapters.mineflayer.execution import (
    WorldConsequence,
    WorldConsequenceStatus,
    build_mineflayer_command,
)
from adapters.mineflayer.process_session import MineflayerProcessEnded
from relay_self.action import ActionState, InvalidTransition
from relay_self.forced_node_loss_fence import ForcedNodeLossFence
from relay_self.inflight_node_loss import (
    InFlightNodeLossRejected,
    close_inflight_node_loss_unknown,
)

ROOT = Path(__file__).resolve().parents[1]


def _inputs():
    data = s20._prepare_second()
    _, issued = s20._issue_second(data)
    supervisor = data["supervisor"]
    binding = data["binding_result2"]
    command = build_mineflayer_command(issued, binding)
    session_id = s20.SESSION2
    fence = ForcedNodeLossFence()
    fence.begin_initial(session_id)
    fault = MineflayerProcessEnded("real EOF typed fixture")
    fence.observe_forced_failure(
        session_id, transport_error=fault, process_returncode=-9,
    )
    before = replace(s19.observation(1, 0.0), session_id=session_id)
    dispatch = replace(
        s19.effect(2, issued.action_id, "set_control"),
        session_id=session_id,
    )
    consequence = WorldConsequence(
        action_id=issued.action_id, binding_id=binding.binding_id,
        action_ref=binding.action_ref, status=WorldConsequenceStatus.FAILED,
        session_id=session_id, before_observation=before,
        dispatch_receipt=dispatch, cleanup_receipt=None,
        after_observation=None, movement_distance=None,
        cleanup_attempted=True,
        error="MineflayerProcessEnded: child EOF after applied effect",
        provenance=s20.p("s40-offline-simulated-failed-consequence"),
    )
    opts = dict(
        session_id=session_id, transport_error=fault, process_returncode=-9,
        at_ns=40, provenance=s20.p("s40-offline-interpretation"),
    )
    return fence, supervisor, issued, binding, command, consequence, opts


def test_applied_dispatch_real_shaped_evidence_closes_exact_unknown_without_retry():
    f, s, issued, binding, command, consequence, opts = _inputs()
    assert consequence.dispatch_receipt.result == "applied"
    closed, receipt = close_inflight_node_loss_unknown(
        f, s, issued, binding, command, consequence, **opts,
    )
    assert closed.state is ActionState.UNKNOWN
    assert s.get(issued.action_id) is closed
    assert s.open_actions == ()
    assert not receipt.replay_authorized
    assert receipt.interpretation_reason == "adapter_failure_consequence_unknown"
    assert receipt.before_seq < receipt.applied_dispatch_seq
    with pytest.raises((InvalidTransition, InFlightNodeLossRejected)):
        close_inflight_node_loss_unknown(
            f, s, issued, binding, command, consequence, **opts,
        )
    with pytest.raises(InvalidTransition):
        s.record_outcome(
            closed.action_id, at_ns=41,
            provenance=s20.p("s40-forged-later-success"),
        )
    assert s.get(issued.action_id).state is ActionState.UNKNOWN


@pytest.mark.parametrize("variant", (
    "not_quarantined", "different_session", "positive_exit",
    "wrong_action", "foreign_binding", "missing_dispatch",
    "rejected_dispatch", "post_after_exists", "post_cleanup_exists",
    "claimed_movement", "wrong_effect", "no_EOF_error",
))
def test_uncertain_loss_negative_controls_fail_without_owner_transition(variant):
    f, s, issued, binding, command, consequence, opts = _inputs()
    if variant == "not_quarantined":
        f = ForcedNodeLossFence()
        f.begin_initial(s20.SESSION2)
    elif variant == "different_session":
        opts["session_id"] = "foreign-world"
    elif variant == "positive_exit":
        opts["process_returncode"] = 0
    elif variant == "wrong_action":
        consequence = replace(consequence, action_id="foreign-action")
    elif variant == "foreign_binding":
        consequence = replace(consequence, binding_id="foreign-binding")
    elif variant == "missing_dispatch":
        consequence = replace(consequence, dispatch_receipt=None)
    elif variant == "rejected_dispatch":
        consequence = replace(
            consequence,
            dispatch_receipt=replace(
                consequence.dispatch_receipt, result="rejected", error="denied",
            ),
        )
    elif variant == "post_after_exists":
        consequence = replace(consequence, after_observation=replace(
            s19.observation(4, 0.2), session_id=s20.SESSION2,
        ))
    elif variant == "post_cleanup_exists":
        consequence = replace(consequence, cleanup_receipt=replace(
            s19.effect(3, command.cleanup_action_id, "clear_controls"),
            session_id=s20.SESSION2,
        ))
    elif variant == "claimed_movement":
        consequence = replace(consequence, movement_distance=0.5)
    elif variant == "wrong_effect":
        consequence = replace(
            consequence, dispatch_receipt=replace(
                consequence.dispatch_receipt, effect="attack_entity",
            ),
        )
    elif variant == "no_EOF_error":
        consequence = replace(consequence, error="TimeoutError: generic")
    with pytest.raises(InFlightNodeLossRejected):
        close_inflight_node_loss_unknown(
            f, s, issued, binding, command, consequence, **opts,
        )
    assert s.get(issued.action_id) is issued
    assert issued.state is ActionState.ISSUED


def test_prospective_static_plan_cannot_qualify_real_world():
    receipt = json.loads(
        (ROOT / "docs/postmain-s40-plan-receipt.json").read_text(),
    )
    assert receipt["status"] == "PENDING_CI"
    assert receipt["base_head"] == "80a8178ee9bd4c95c2f668247ba3e7c2f097895b"
    assert receipt["qualification_requires"] == "S40_REPORT.status == PASS"
    assert receipt["s31b_wsl2_reproduction"] == "SKIPPED"
