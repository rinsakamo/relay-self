"""Exercise the *original* S49 execute() with the DEV issuer fence.

All native/process/World input is synthetic, with zero Java/Node or issued
physical commands. The original S49 source and Executor blobs are unchanged.
"""
from __future__ import annotations

import asyncio
from types import SimpleNamespace

import pytest

from adapters.mineflayer.m02_paper_dev.s50_boundary import BoundaryRejected
from adapters.mineflayer.normal_action import NormalSessionActionExecutor
from adapters.mineflayer.process_session import MineflayerProcessSession
from adapters.mineflayer.s49_wait_fenced_executor_dev import (
    S49WaitFencedExecutorDev,
)
from relay_self.action import ActionState
from relay_self.intent import IntentCommitment
from relay_self.provenance import Provenance

SESSION = "native-dev-session"
MARKER = "s49-action-session-marker"
WORLD = "paper-world-uuid"


def owner():
    intent = IntentCommitment()
    intent.commit(
        "escape-threat", objective="escape zombie", at_ns=1,
        provenance=Provenance("offline-dev", "test-intent"),
    )
    return S49WaitFencedExecutorDev(
        SESSION, intent, marker_id=MARKER, world=WORLD, dev_only=True,
    )


def arm(executor):
    # A terminal synthetic fixture is NOT an authenticated World OUTCOME.
    # The actual original ActionSupervisor and _dispatched identities are
    # deliberately used rather than a second supervisor.
    executor._dispatched.add("prior-move")
    executor.supervisor._lifecycles["prior-move"] = SimpleNamespace(
        state=ActionState.OUTCOME,
    )
    executor.arm_after_original_outcome(
        closed_action_id="prior-move",
        terminal_outcome_ref="prior-supervisor-outcome-original",
        controls_clear_ref="prior-native-clear-original",
    )


def fake_session():
    # isinstance check in original execute() remains active. No process runs.
    p = SimpleNamespace(stdin=object(), stdout=object(), returncode=None)
    session = MineflayerProcessSession(p)
    session._started = SimpleNamespace(session_id=SESSION)
    return session


def test_no_implicit_dev_activation_and_no_second_action_supervisor():
    i = IntentCommitment()
    i.commit(
        "escape-threat", objective="escape zombie", at_ns=1,
        provenance=Provenance("offline-dev", "test-intent"),
    )
    with pytest.raises(BoundaryRejected, match="DEV-only"):
        S49WaitFencedExecutorDev(SESSION, i, marker_id=MARKER, world=WORLD)
    ex = owner()
    assert S49WaitFencedExecutorDev.execute is NormalSessionActionExecutor.execute
    assert ex._wait_fence._supervisor is ex.supervisor
    assert ex.wait_phase == "NEW"


def test_earlier_outcome_must_be_owned_and_terminal():
    ex = owner()
    with pytest.raises(BoundaryRejected, match="dispatched"):
        ex.arm_after_original_outcome(
            closed_action_id="unknown", terminal_outcome_ref="outcome",
            controls_clear_ref="clear",
        )
    ex._dispatched.add("prior-move")
    ex.supervisor._lifecycles["prior-move"] = SimpleNamespace(
        state=ActionState.UNKNOWN,
    )
    with pytest.raises(BoundaryRejected, match="non-OUTCOME"):
        ex.arm_after_original_outcome(
            closed_action_id="prior-move", terminal_outcome_ref="outcome",
            controls_clear_ref="clear",
        )
    assert ex.wait_phase == "NEW"


def test_original_execute_is_denied_before_issue_or_physical_command(monkeypatch):
    ex = owner()
    arm(ex)
    assert ex.wait_phase == "ARMED"
    dispatched_before = set(ex._dispatched)
    import adapters.mineflayer.normal_action as original

    async def no_native_command(*args, **kwargs):
        raise AssertionError("unsafe physical dispatch reached")

    monkeypatch.setattr(original, "execute_mineflayer_command", no_native_command)

    async def attempt():
        return await NormalSessionActionExecutor.execute(
            ex, fake_session(),
            SimpleNamespace(action_request_id="new-move"),
            None, SimpleNamespace(request_id="native-probe-1"), None, None,
        )

    with pytest.raises(BoundaryRejected, match="inside owner WAIT"):
        asyncio.run(attempt())
    assert ex.wait_phase == "ABORTED"
    assert ex.wait_original_rows[-1]["kind"] == "BLOCKED_ISSUE"
    assert ex.supervisor.open_actions == ()
    assert ex._dispatched == dispatched_before
    assert ex._count == 0


def test_abort_and_replay_cannot_rearm():
    ex = owner()
    arm(ex)
    ex.abort_wait(reason_source_ref="caller-cancelled")
    assert ex.wait_phase == "ABORTED"
    assert ex.wait_original_rows[-1]["kind"] == "ABORT"
    with pytest.raises(BoundaryRejected):
        ex.arm_after_original_outcome(
            closed_action_id="prior-move", terminal_outcome_ref="outcome",
            controls_clear_ref="clear",
        )


def test_async_cancel_mid_window_invalidates_partial_rows_and_propagates():
    ex = owner()
    arm(ex)

    async def never_complete():
        yield 61, "paper-tick-61"
        await asyncio.Future()
        yield 62, "paper-tick-62"

    async def run():
        task = asyncio.create_task(
            ex.screen_wait_samples(
                never_complete(), seal_source_ref="local-seal",
            ),
        )
        await asyncio.sleep(0)
        task.cancel()
        with pytest.raises(asyncio.CancelledError):
            await task

    asyncio.run(run())
    assert ex.wait_phase == "ABORTED"
    assert [r["kind"] for r in ex.wait_original_rows] == [
        "ARM", "PAPER_SAMPLE", "ABORT",
    ]
    assert ex.supervisor.open_actions == ()


@pytest.mark.parametrize("ticks", [
    (61, 62, 64, 65, 66, 67, 68),
    tuple(range(61, 68)),
    tuple(range(61, 70)),
])
def test_incomplete_gapped_or_excessive_paper_source_is_never_sealed(ticks):
    ex = owner()
    arm(ex)

    async def samples():
        for tick in ticks:
            yield tick, f"paper-tick-{tick}"

    async def run():
        with pytest.raises(BoundaryRejected):
            await ex.screen_wait_samples(
                samples(), seal_source_ref="local-seal",
            )

    asyncio.run(run())
    assert ex.wait_phase == "ABORTED"
    assert ex.wait_original_rows[-1]["kind"] == "ABORT"


def test_eight_rows_seal_then_original_action_gate_remains_unmodified():
    ex = owner()
    arm(ex)

    async def samples():
        for tick in range(61, 69):
            yield tick, f"paper-tick-{tick}"

    result = asyncio.run(
        ex.screen_wait_samples(samples(), seal_source_ref="local-seal"),
    )
    assert ex.wait_phase == "SEALED"
    assert len(result) == 10
    assert all(row["source_ref"] for row in result)
    assert ex.supervisor.open_actions == ()
    # A sealed local fence is NOT a physical/authorization grant.
    with pytest.raises(ValueError):
        ex.require_authorizations(
            SimpleNamespace(action_request_id="next-action"),
            None, SimpleNamespace(request_id="probe"), None, None,
        )
