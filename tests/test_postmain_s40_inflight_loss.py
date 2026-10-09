"""S40 offline negative controls; physical child SIGKILL is proved by CI."""
from __future__ import annotations

import json
from dataclasses import replace
from pathlib import Path
from types import SimpleNamespace

import pytest

import test_postmain_s39_fresh_action as s39
import test_postmain_two_epoch_continuation as s19
from adapters.mineflayer.execution import (
    WorldConsequence,
    WorldConsequenceStatus,
)
from adapters.mineflayer.process_session import MineflayerProcessEnded
from relay_self.action import ActionState, InvalidTransition
from relay_self.forced_node_loss_fence import WorldLossState
from relay_self.fresh_source_action import (
    FreshSourceActionGate,
    FreshSourceActionRejected,
)
from relay_self.inflight_node_loss import (
    InFlightNodeLossRejected,
    close_inflight_node_loss_unknown,
)

ROOT = Path(__file__).resolve().parents[1]


def _setup():
    fence, supervisor, intent, _old, fresh = s39._scenario()
    gate = FreshSourceActionGate(fence, supervisor, fresh)
    binding = s39._binding()
    _, proposed, result = gate.propose(
        intent, binding, s39._grant(fresh), at_ns=31,
        provenance=s19.provenance("s40-proposed"),
    )
    issued = gate.authorize_issue(
        proposed, binding, s39._grant(fresh, "ISSUE"),
        at_ns=32, deadline_ns=100,
        provenance=s19.provenance("s40-issue"),
    )
    session = SimpleNamespace(
        started=SimpleNamespace(session_id=fresh.session_id),
        process_returncode=None,
    )
    command = gate.claim_command(issued, session)
    before = fresh.ticket.correlated_probe
    effect = replace(
        s19.effect(before.seq + 1, issued.action_id, "set_control"),
        session_id=fresh.session_id,
    )
    failure = MineflayerProcessEnded("actual stdout EOF after killed child")
    consequence = WorldConsequence(
        action_id=issued.action_id, binding_id=command.binding_id,
        action_ref=command.action_ref, status=WorldConsequenceStatus.FAILED,
        session_id=fresh.session_id, before_observation=before,
        dispatch_receipt=effect, cleanup_receipt=None,
        after_observation=None, movement_distance=None,
        cleanup_attempted=False, error="MineflayerProcessEnded: actual stdout EOF",
        provenance=s19.provenance("s40-inflight-incomplete-world"),
    )
    return fence, supervisor, gate, issued, result, command, consequence, failure


def _close(fence, supervisor, issued, result, command, consequence, failure):
    return close_inflight_node_loss_unknown(
        fence, supervisor, issued, result, command, consequence,
        session_id=consequence.session_id, transport_error=failure,
        process_returncode=-9, at_ns=40,
        provenance=s19.provenance("s40-unknown-interpretation"),
    )


def test_inflight_actual_loss_requires_quarantined_world_before_closure():
    fence, supervisor, gate, issued, result, cmd, consequence, error = _setup()
    with pytest.raises(InFlightNodeLossRejected):
        _close(fence, supervisor, issued, result, cmd, consequence, error)
    assert supervisor.get(issued.action_id) is issued
    assert issued.state is ActionState.ISSUED
    fence.observe_forced_failure(
        consequence.session_id, transport_error=error, process_returncode=-9,
    )
    closed, receipt = _close(
        fence, supervisor, issued, result, cmd, consequence, error,
    )
    assert fence.state is WorldLossState.QUARANTINED
    assert closed.state is ActionState.UNKNOWN
    assert receipt.terminal_action_state == "unknown"
    assert receipt.applied_dispatch_seq > receipt.before_seq
    assert receipt.replay_authorized is False
    assert supervisor.open_actions == ()
    with pytest.raises(FreshSourceActionRejected):
        gate.claim_command(issued, SimpleNamespace(
            started=SimpleNamespace(session_id=consequence.session_id),
            process_returncode=None,
        ))
    with pytest.raises(InFlightNodeLossRejected):
        _close(fence, supervisor, issued, result, cmd, consequence, error)
    with pytest.raises(InvalidTransition):
        issued.record_outcome(
            at_ns=50, provenance=s19.provenance("s40-forbidden-known-outcome"),
        )


@pytest.mark.parametrize("modifier", [
    "no_dispatch", "rejected_dispatch", "cleanup_exists", "after_exists",
    "wrong_session", "wrong_action", "unknown_error", "missing_before",
])
def test_requires_exact_applied_dispatch_and_absent_completion(modifier):
    fence, supervisor, _, issued, result, cmd, consequence, failure = _setup()
    if modifier == "no_dispatch":
        consequence = replace(consequence, dispatch_receipt=None)
    elif modifier == "rejected_dispatch":
        consequence = replace(
            consequence,
            dispatch_receipt=replace(
                consequence.dispatch_receipt, result="rejected", error="denied",
            ),
        )
    elif modifier == "cleanup_exists":
        consequence = replace(
            consequence, cleanup_receipt=consequence.dispatch_receipt,
        )
    elif modifier == "after_exists":
        consequence = replace(
            consequence, after_observation=consequence.before_observation,
        )
    elif modifier == "wrong_session":
        consequence = replace(consequence, session_id="foreign-node")
    elif modifier == "wrong_action":
        consequence = replace(consequence, action_id="foreign-action")
    elif modifier == "unknown_error":
        consequence = replace(consequence, error="TimeoutError: unknown")
    elif modifier == "missing_before":
        consequence = replace(consequence, before_observation=None)
    fence.observe_forced_failure(
        issued_session := cmd_session(fence), transport_error=failure,
        process_returncode=-9,
    )
    with pytest.raises((InFlightNodeLossRejected, ValueError)):
        close_inflight_node_loss_unknown(
            fence, supervisor, issued, result, cmd, consequence,
            session_id=issued_session, transport_error=failure,
            process_returncode=-9, at_ns=40,
            provenance=s19.provenance("s40-invalid"),
        )
    assert supervisor.get(issued.action_id) is issued
    assert issued.state is ActionState.ISSUED


def cmd_session(fence):
    return fence.host.active_session_id


@pytest.mark.parametrize("returncode,error_type", [
    (0, "real"), (-11, "real"), (-9, "fake"),
])
def test_wrong_fault_receipt_does_not_close_unknown(returncode, error_type):
    fence, supervisor, _, issued, result, cmd, consequence, failure = _setup()
    fence.observe_forced_failure(
        consequence.session_id, transport_error=failure, process_returncode=-9,
    )
    with pytest.raises(InFlightNodeLossRejected):
        close_inflight_node_loss_unknown(
            fence, supervisor, issued, result, cmd, consequence,
            session_id=consequence.session_id,
            transport_error=failure if error_type == "real" else RuntimeError("EOF"),
            process_returncode=returncode,
            at_ns=40, provenance=s19.provenance("s40-invalid-fault"),
        )
    assert supervisor.get(issued.action_id).state is ActionState.ISSUED


def test_static_gate_must_not_be_mistaken_for_world_proof():
    receipt = json.loads((ROOT / "docs/postmain-s40-plan-receipt.json").read_text())
    assert receipt["status"] == "PENDING_CI"
    assert receipt["base_head"] == "80a8178ee9bd4c95c2f668247ba3e7c2f097895b"
    assert receipt["qualification_requires"] == "S40_REPORT.status == PASS"
    assert receipt["s31b_wsl2_reproduction"] == "SKIPPED"
