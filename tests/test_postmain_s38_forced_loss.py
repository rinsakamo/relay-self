"""S38 forced Node loss: quarantine, fresh revalidation, no Action authority.

The typed source fixtures here come from frozen S37. The negative tests
DO NOT claim actual Node SIGKILL or genuine World recovery, which the
dedicated Minecraft CI job separately qualifies.
"""
from __future__ import annotations

import asyncio
import json
from pathlib import Path

import pytest

import test_postmain_s37_host_loop as s37
from adapters.mineflayer.process_session import MineflayerProcessEnded
from relay_self.bounded_native_host_loop import (
    HostLoopBoundaryError,
    HostLoopBudget,
    HostLoopResourceError,
)
from relay_self.forced_node_loss_fence import (
    ForcedNodeLossFence,
    WorldLossBoundaryError,
    WorldLossState,
)

ROOT = Path(__file__).resolve().parents[1]


def _fixture(*, second=True):
    return (
        s37._Session("node-a", [s37._event("node-a", 10, 2)]),
        s37._Session("node-b", [s37._event("node-b", 4, 3)]) if second else None,
    )


def test_actual_process_error_type_and_negative_os_exit_required():
    h = ForcedNodeLossFence()
    h.begin_initial("node-a")
    with pytest.raises(WorldLossBoundaryError):
        h.observe_forced_failure(
            "node-a",
            transport_error=MineflayerProcessEnded("stdout EOF"),
            process_returncode=0,
        )
    with pytest.raises(WorldLossBoundaryError):
        h.observe_forced_failure(
            "node-a",
            transport_error=RuntimeError("not a process EOF"),
            process_returncode=-9,
        )
    with pytest.raises(WorldLossBoundaryError):
        h.observe_forced_failure(
            "node-other",
            transport_error=MineflayerProcessEnded("stdout EOF"),
            process_returncode=-9,
        )
    assert h.state is WorldLossState.ACTIVE
    assert h.host.active_session_id == "node-a"


def test_abrupt_node_loss_quarantines_and_requires_real_new_session_ticket():
    async def run():
        h = ForcedNodeLossFence()
        first_session, new_session = _fixture()
        h.begin_initial("node-a")
        first = await h.run_active(
            first_session,
            probe=s37._probe, grant=s37._grant,
            cognition=lambda ticket: ticket.event_id,
        )
        assert first.session_id == "node-a" and h.host.total_epochs == 1
        fault = h.observe_forced_failure(
            "node-a",
            transport_error=MineflayerProcessEnded("returncode=-9"),
            process_returncode=-9,
        )
        assert fault.session_id == first.session_id
        assert fault.process_returncode == -9
        assert fault.old_epochs == 1
        assert h.state is WorldLossState.QUARANTINED
        assert h.host.active_session_id is None

        with pytest.raises(WorldLossBoundaryError):
            h.require_active_ticket(first.ticket)
        with pytest.raises(WorldLossBoundaryError):
            await h.run_active(
                first_session, probe=s37._probe, grant=s37._grant,
                cognition=lambda t: t.event_id,
            )
        with pytest.raises(WorldLossBoundaryError):
            h.begin_successor("node-a")

        h.begin_successor("node-b")
        assert h.state is WorldLossState.PROBATION
        with pytest.raises(WorldLossBoundaryError):
            h.require_active_ticket(first.ticket)

        second = await h.revalidate_successor(
            new_session,
            probe=s37._probe, grant=s37._grant,
            cognition=lambda ticket: ticket.event_id,
        )
        assert second.session_id == "node-b"
        assert second.entity_id != first.entity_id
        assert second.event_seq < second.probe_seq
        assert h.state is WorldLossState.ACTIVE
        assert h.host.total_sessions == 2
        assert h.host.total_epochs == 2
        with pytest.raises(HostLoopBoundaryError):
            h.require_active_ticket(first.ticket)
        h.require_active_ticket(second.ticket)
        h.close_successor("node-b")
        assert h.state is WorldLossState.CLOSED
        assert h.host.active_session_id is None
    asyncio.run(run())


def test_reconnect_without_fresh_world_event_remains_quarantined_probation():
    async def run():
        h = ForcedNodeLossFence(HostLoopBudget(
            max_sessions=2, max_epochs_per_session=1, max_total_epochs=2,
            max_frames_per_event=2, receive_timeout_s=0.01,
        ))
        h.begin_initial("node-a")
        h.observe_forced_failure(
            "node-a",
            transport_error=MineflayerProcessEnded("EOF"),
            process_returncode=-9,
        )
        h.begin_successor("node-b")
        with pytest.raises(HostLoopResourceError):
            await h.revalidate_successor(
                s37._Session("node-b", []),
                probe=s37._probe, grant=s37._grant,
                cognition=lambda ticket: ticket.event_id,
            )
        assert h.state is WorldLossState.PROBATION
        assert h.host.total_epochs == 0
        with pytest.raises(WorldLossBoundaryError):
            h.require_active_ticket(None)
    asyncio.run(run())


def test_invalid_new_session_or_denied_grant_does_not_clear_quarantine():
    async def run():
        h = ForcedNodeLossFence()
        h.begin_initial("node-a")
        h.observe_forced_failure(
            "node-a",
            transport_error=MineflayerProcessEnded("stdout EOF"),
            process_returncode=-9,
        )
        h.begin_successor("node-b")
        denied = lambda candidate: s37.replace(
            s37._grant(candidate), granted=False,
        )
        from relay_self.native_event_cognition import EventCognitionNotAdmitted
        with pytest.raises(EventCognitionNotAdmitted):
            await h.revalidate_successor(
                s37._Session("node-b", [s37._event("node-b", 10, 2)]),
                probe=s37._probe, grant=denied,
                cognition=lambda t: t.event_id,
            )
        assert h.state is WorldLossState.PROBATION
        with pytest.raises(WorldLossBoundaryError):
            h.close_successor("node-b")
    asyncio.run(run())


def test_active_reentry_before_fault_or_duplicate_fault_is_denied():
    h = ForcedNodeLossFence()
    with pytest.raises(WorldLossBoundaryError):
        h.begin_successor("node-b")
    h.begin_initial("node-a")
    with pytest.raises(WorldLossBoundaryError):
        h.begin_initial("node-c")
    with pytest.raises(WorldLossBoundaryError):
        h.close_successor("node-a")
    h.observe_forced_failure(
        "node-a",
        transport_error=MineflayerProcessEnded("EOF"), process_returncode=-9,
    )
    with pytest.raises(WorldLossBoundaryError):
        h.observe_forced_failure(
            "node-a", transport_error=MineflayerProcessEnded("EOF"),
            process_returncode=-9,
        )


def test_prospective_no_action_and_genuine_dynamic_receipt_gate():
    plan = json.loads((ROOT / "docs/postmain-s38-plan-receipt.json").read_text())
    assert plan["status"] == "PENDING_CI"
    assert plan["base_head"] == "3f1298b4e485a7721af3b7fe1608a58d9f0fcce7"
    assert plan["qualification_requires"] == "S38_REPORT.status == PASS"
    assert plan["real_fault_method"] == "OS_SIGKILL_MINEFLAYER_NODE_CHILD"
    assert plan["action_authority"] == "NONE"
    code = (ROOT / "src/relay_self/forced_node_loss_fence.py").read_text()
    assert "ActionSupervisor" not in code
    assert "send_set_control(" not in code
    assert "issue(" not in code
