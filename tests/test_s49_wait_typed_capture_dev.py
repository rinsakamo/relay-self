"""S49 typed closure DEV checks; S17 original typed fixtures, no World."""
from __future__ import annotations

import asyncio
from dataclasses import replace

import pytest

import adapters.mineflayer.normal_action as normal
import test_action_feedback_qualification as s17
from adapters.mineflayer.m02_paper_dev.s50_boundary import BoundaryRejected
from adapters.mineflayer.normal_action import (
    NormalActionClosedReadback,
    NormalActionReceipt,
)
from adapters.mineflayer.s49_wait_fenced_executor_dev import S49WaitFencedExecutorDev
from adapters.mineflayer.s49_wait_typed_capture_dev import (
    S49TypedClosureCaptureDev,
    reject_incompatible_s50_control_action,
)
from relay_self.intent import IntentCommitment
from relay_self.provenance import Provenance
from test_s50_p1_control_action import fixture as s50_fixture


def fixture():
    # These are the S17 in-process typed test frames, NOT a physical S49 run.
    supervisor, _, consequence, interpretation, closed = (
        s17.executed_closed_chain()[-5:]
    )
    intent = IntentCommitment()
    intent.commit(
        "escape-threat", objective="offline DEV", at_ns=1,
        provenance=Provenance("offline", "typed-intent"),
    )
    ex = S49WaitFencedExecutorDev(
        consequence.session_id, intent, marker_id="s49-typed",
        world="paper-unattested", dev_only=True,
    )
    # Offline binding to the exact S17 ActionSupervisor instance. Not evidence
    # that the original S49 runtime issued this Action in the physical World.
    ex.supervisor = supervisor
    ex._wait_fence._supervisor = supervisor
    ex._dispatched.add(consequence.action_id)
    probe = consequence.before_observation
    receipt = NormalActionReceipt(closed, consequence, probe.provenance)
    readback = NormalActionClosedReadback(
        closed, interpretation, consequence, probe,
    )
    return ex, probe, receipt, readback


def test_typed_terminal_and_clear_ack_only_from_same_supervisor():
    ex, probe, receipt, readback = fixture()
    capture = S49TypedClosureCaptureDev(ex)
    projected = capture._project(receipt, [readback], expected_probe=probe)
    assert projected.action_id == receipt.terminal.action_id
    assert projected.session_id == ex.session_id
    assert projected.clear_ref.startswith("derived-dev-s16-clear-sha256:")
    assert projected.terminal_ref.startswith("derived-dev-s49-terminal-sha256:")
    assert projected.decoded_evidence["cleanup_receipt"]["effect"] == (
        "clear_controls"
    )
    assert projected.decoded_evidence["cleanup_receipt"]["result"] == "applied"
    assert not projected.physical_source_authenticated
    assert projected.wait_ticks_admitted == 0
    assert projected.p1_fatigue_recovered == 0


def test_owner_execute_wrapper_captures_existing_context_readback(monkeypatch):
    ex, probe, receipt, readback = fixture()

    async def original_called(_session, _step, _bound, _probe, _p, _i):
        callback = normal._READ_ONLY_CLOSURE.get()
        assert callback is not None
        callback(readback)
        return receipt

    # Replace ONLY synthetic test dispatch; runtime original execute is
    # unmodified. Proves context hookup, not physical source attestation.
    monkeypatch.setattr(ex, "execute", original_called)
    capture = S49TypedClosureCaptureDev(ex)

    async def execute():
        return await capture.execute_owned(
            None, None, None, probe, None, None,
        )

    out = asyncio.run(execute())
    assert out is receipt
    assert capture.state == "CAPTURED"
    assert capture.projection is not None
    result = capture.arm_owner_wait()
    assert result.decoded_evidence["action_id"] == ex.wait_original_rows[0][
        "action_id"
    ]
    assert ex.wait_phase == "ARMED"
    assert capture.state == "ARMED"
    with pytest.raises(BoundaryRejected, match="one-shot"):
        asyncio.run(execute())
    with pytest.raises(BoundaryRejected):
        capture.arm_owner_wait()


@pytest.mark.parametrize("failure", [
    "missing_readback", "double_readback", "foreign_terminal",
    "foreign_cleanup", "foreign_probe", "other_supervisor",
    "foreign_session",
])
def test_missing_misbound_or_replayed_s16_never_arms_wait(failure):
    ex, probe, receipt, readback = fixture()
    obs = [readback]
    if failure == "missing_readback":
        obs = []
    elif failure == "double_readback":
        obs = [readback, readback]
    elif failure == "foreign_terminal":
        obs = [replace(readback, terminal=object())]
    elif failure == "foreign_cleanup":
        original = receipt.consequence
        modified = replace(
            original, cleanup_receipt=replace(
                original.cleanup_receipt, action_id="foreign-clear",
            ),
        )
        receipt = replace(receipt, consequence=modified)
        obs = [replace(readback, consequence=modified)]
    elif failure == "foreign_probe":
        probe = object()
    elif failure == "other_supervisor":
        ex.supervisor._lifecycles.pop(receipt.terminal.action_id)
    elif failure == "foreign_session":
        ex.session_id = "foreign"
    capture = S49TypedClosureCaptureDev(ex)
    with pytest.raises((BoundaryRejected, ValueError)):
        capture._project(receipt, obs, expected_probe=probe)
    assert ex.wait_phase == "NEW"


def test_original_async_cancellation_no_replay(monkeypatch):
    ex, probe, _, _ = fixture()

    async def stopped(*args, **kwargs):
        raise asyncio.CancelledError()

    monkeypatch.setattr(ex, "execute", stopped)
    capture = S49TypedClosureCaptureDev(ex)
    with pytest.raises(asyncio.CancelledError):
        asyncio.run(capture.execute_owned(None, None, None, probe, None, None))
    assert capture.state == "FAILED"
    assert capture.projection is None
    with pytest.raises(BoundaryRejected, match="one-shot"):
        asyncio.run(capture.execute_owned(None, None, None, probe, None, None))
    with pytest.raises(BoundaryRejected):
        capture.arm_owner_wait()


def test_legacy_s50_forward_source_cannot_be_aliased_as_s49_backward():
    ex, probe, receipt, readback = fixture()
    result = S49TypedClosureCaptureDev(ex)._project(
        receipt, [readback], expected_probe=probe,
    )
    _, _, commands, _, movement = s50_fixture()
    with pytest.raises(BoundaryRejected, match="session or Action"):
        reject_incompatible_s50_control_action(
            result, source_session=movement["source_session"],
            action_id=movement["action_id"], commands=commands,
        )
    # Even with a caller-forged alias ID, forward != S49 MOVE_BACKWARD.
    aliased = [dict(c) for c in commands]
    for command in aliased:
        command["action_id"] = result.action_id
    with pytest.raises(BoundaryRejected, match="backward Action"):
        reject_incompatible_s50_control_action(
            result, source_session=result.session_id,
            action_id=result.action_id, commands=aliased,
        )


def test_fake_backward_command_still_lacks_native_cleanup_wire_binding():
    ex, probe, receipt, readback = fixture()
    result = S49TypedClosureCaptureDev(ex)._project(
        receipt, [readback], expected_probe=probe,
    )
    with pytest.raises(BoundaryRejected, match="not independently attested"):
        reject_incompatible_s50_control_action(
            result, source_session=result.session_id,
            action_id=result.action_id,
            commands=[{
                "action_id": result.action_id, "effect": "set_control",
                "control": "back", "state": True,
            }],
        )


@pytest.mark.parametrize("drift", [
    "second_dispatched", "owner_count", "new_supervisor", "tampered_payload",
])
def test_typed_close_to_wait_handoff_rejects_owner_drift(monkeypatch, drift):
    ex, probe, receipt, readback = fixture()

    async def original_called(_session, _step, _bound, _probe, _p, _i):
        normal._READ_ONLY_CLOSURE.get()(readback)
        return receipt

    monkeypatch.setattr(ex, "execute", original_called)
    capture = S49TypedClosureCaptureDev(ex)
    asyncio.run(capture.execute_owned(None, None, None, probe, None, None))
    if drift == "second_dispatched":
        ex._dispatched.add("unrelated")
    elif drift == "owner_count":
        ex._count += 1
    elif drift == "new_supervisor":
        from relay_self.action_supervision import ActionSupervisor
        ex.supervisor = ActionSupervisor()
    else:
        capture.projection.decoded_evidence["cleanup_receipt"]["action_id"] = (
            "tampered-clear"
        )
    with pytest.raises(BoundaryRejected):
        capture.arm_owner_wait()
    assert ex.wait_phase == "NEW"
    assert capture.state == "CAPTURED"


def test_nested_original_closure_observer_is_not_silently_replaced(monkeypatch):
    ex, probe, _, _ = fixture()
    called = []

    async def should_not_run(*a, **kw):
        called.append(True)
        raise AssertionError("competing observer permitted execution")

    monkeypatch.setattr(ex, "execute", should_not_run)
    capture = S49TypedClosureCaptureDev(ex)

    async def scenario():
        with normal.observe_closed_native_actions(called.append):
            with pytest.raises(BoundaryRejected, match="another original"):
                await capture.execute_owned(
                    None, None, None, probe, None, None,
                )
    asyncio.run(scenario())
    assert called == []
    assert capture.state == "NEW"
