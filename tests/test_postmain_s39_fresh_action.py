"""S39 deterministic negative gates; real OS/Minecraft is qualified separately."""
from __future__ import annotations

import asyncio
import json
from dataclasses import replace
from pathlib import Path
from types import SimpleNamespace

import pytest

import test_postmain_s37_host_loop as s37
import test_postmain_two_epoch_continuation as s19
from adapters.mineflayer.process_session import MineflayerProcessEnded
from adapters.mineflayer.s34_native_world_cognition_ci import (
    _native_epoch_two, _native_threat,
)
from relay_self.action import ActionState
from relay_self.action_supervision import ActionSupervisor
from relay_self.execution_binding import ExecutionBinding
from relay_self.forced_node_loss_fence import ForcedNodeLossFence
from relay_self.fresh_source_action import (
    FreshSourceActionGate, FreshSourceActionGrant, FreshSourceActionRejected,
)

ROOT = Path(__file__).resolve().parents[1]


def _binding():
    return ExecutionBinding(
        binding_id="s39-binding-fresh", candidate_ref="MOVE_AWAY",
        required_intent_id="escape-threat",
        skill_execution_id="s39-skill-fresh",
        skill_ref="escape-movement", action_id="s39-action-fresh",
        action_ref="MOVE_BACKWARD", provenance=s19.provenance("s39-binding"),
    )


def _grant(event, purpose="PROPOSE", *, granted=True):
    return FreshSourceActionGrant(
        authority_id=f"s39-separate-{purpose.lower()}-authority",
        purpose=purpose, session_id=event.session_id,
        event_seq=event.event_seq, probe_seq=event.probe_seq,
        entity_id=event.entity_id, action_id="s39-action-fresh",
        binding_id="s39-binding-fresh", granted=granted,
        provenance=s19.provenance(f"s39-separate-{purpose.lower()}-grant"),
    )


def _scenario():
    async def run():
        _past, committed, _, _, _, _ = s19._epoch_one()
        supervisor = ActionSupervisor()
        intent = s19.IntentCommitment()
        intent.commit(
            "escape-threat", objective="escape nearby zombie", at_ns=1,
            provenance=s19.provenance("s39-current-intent"),
        )
        fence = ForcedNodeLossFence()

        def cognition(ticket):
            native = _native_threat(
                ticket.correlated_probe, ticket.probe_request_id,
                expected_entity_id=ticket.candidate.target_entity_id,
            )
            values, epoch = _native_epoch_two(
                supervisor, intent, committed.new_state,
                committed.new_state, expected_revision=1, native=native,
            )
            assert epoch.cognition_requested is False
            assert values["plan"].selected.candidate_id == "MOVE_AWAY"
            return {
                "selected": "MOVE_AWAY", "admission": "admitted",
                "source": ticket.correlated_probe.provenance.reference,
                "values": values,
            }

        first_session = s37._Session("s39-old", [s37._event("s39-old", 10, 2)])
        fence.begin_initial("s39-old")
        first = await fence.run_active(
            first_session, probe=s37._probe, grant=s37._grant,
            cognition=cognition,
        )
        fence.observe_forced_failure(
            "s39-old", transport_error=MineflayerProcessEnded("EOF"),
            process_returncode=-9,
        )
        fence.begin_successor("s39-new")
        second = await fence.revalidate_successor(
            s37._Session("s39-new", [s37._event("s39-new", 4, 3)]),
            probe=s37._probe, grant=s37._grant, cognition=cognition,
        )
        return fence, supervisor, intent, first, second
    return asyncio.run(run())


def test_first_event_old_generation_cannot_propose_or_issue():
    fence, supervisor, intent, first, second = _scenario()
    gate = FreshSourceActionGate(fence, supervisor, first)
    with pytest.raises(FreshSourceActionRejected):
        gate.propose(
            intent, _binding(), _grant(first), at_ns=31,
            provenance=s19.provenance("old-action-proposal"),
        )
    assert supervisor.open_actions == ()
    with pytest.raises(Exception):
        supervisor.get("s39-action-fresh")
    assert second.session_id != first.session_id


def test_fresh_event_separate_grants_and_exact_one_physical_command():
    fence, supervisor, intent, first, second = _scenario()
    gate = FreshSourceActionGate(fence, supervisor, second)
    with pytest.raises(FreshSourceActionRejected):
        gate.propose(
            intent, _binding(), _grant(second, granted=False),
            at_ns=31, provenance=s19.provenance("denied-action"),
        )
    skill, proposed, binding_result = gate.propose(
        intent, _binding(), _grant(second), at_ns=31,
        provenance=s19.provenance("s39-propose"),
    )
    assert proposed.state is ActionState.PROPOSED
    assert skill.state.value == "started"
    assert binding_result.action_id == proposed.action_id
    with pytest.raises(FreshSourceActionRejected):
        gate.propose(
            intent, _binding(), _grant(second), at_ns=31,
            provenance=s19.provenance("duplicate-propose"),
        )
    with pytest.raises(FreshSourceActionRejected):
        gate.authorize_issue(
            proposed, _binding(), _grant(second, "PROPOSE"),
            at_ns=32, deadline_ns=100,
            provenance=s19.provenance("wrong-purpose"),
        )
    with pytest.raises(FreshSourceActionRejected):
        gate.authorize_issue(
            proposed, _binding(), replace(
                _grant(second, "ISSUE"), session_id="s39-old",
            ), at_ns=32, deadline_ns=100,
            provenance=s19.provenance("old-grant"),
        )
    issued = gate.authorize_issue(
        proposed, _binding(), _grant(second, "ISSUE"),
        at_ns=32, deadline_ns=100,
        provenance=s19.provenance("s39-issued"),
    )
    assert issued.state is ActionState.ISSUED
    with pytest.raises(FreshSourceActionRejected):
        gate.authorize_issue(
            proposed, _binding(), _grant(second, "ISSUE"),
            at_ns=33, deadline_ns=100,
            provenance=s19.provenance("duplicate-issue"),
        )
    with pytest.raises(FreshSourceActionRejected):
        gate.claim_command(issued, SimpleNamespace(
            started=SimpleNamespace(session_id="s39-old"),
            process_returncode=None,
        ))
    session = SimpleNamespace(
        started=SimpleNamespace(session_id="s39-new"),
        process_returncode=None,
    )
    cmd = gate.claim_command(issued, session)
    assert cmd.action_id == "s39-action-fresh"
    with pytest.raises(FreshSourceActionRejected):
        gate.claim_command(issued, session)
    assert len(supervisor.open_actions) == 1
    assert first.session_id != issued.action_id


def test_issued_during_later_source_failure_cannot_dispatch():
    fence, supervisor, intent, _, second = _scenario()
    gate = FreshSourceActionGate(fence, supervisor, second)
    _, proposed, _ = gate.propose(
        intent, _binding(), _grant(second), at_ns=31,
        provenance=s19.provenance("s39-propose"),
    )
    issued = gate.authorize_issue(
        proposed, _binding(), _grant(second, "ISSUE"),
        at_ns=32, deadline_ns=100,
        provenance=s19.provenance("s39-issue"),
    )
    fence.host.end_session("s39-new")
    with pytest.raises(FreshSourceActionRejected):
        gate.claim_command(issued, SimpleNamespace(
            started=SimpleNamespace(session_id="s39-new"),
            process_returncode=None,
        ))


def test_static_receipt_is_prospective_not_real_server_proof():
    report = json.loads((ROOT / "docs/postmain-s39-plan-receipt.json").read_text())
    assert report["status"] == "PENDING_CI"
    assert report["base_head"] == "f02db77e22ee7348ac1289c5be0ec9e142a1dbb5"
    assert report["qualification_requires"] == "S39_REPORT.status == PASS"
    assert report["s31b_wsl2_reproduction"] == "SKIPPED"
