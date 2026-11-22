"""U13 Q4 phased original host motor watchdog CPU/Native-fixture tests.

These are synthetic Owner/Native/WAL acknowledgements. NOT a real World PASS.
"""
from __future__ import annotations

import asyncio
import inspect

import pytest

from experiments.cognitive_physical_place_move_issue_dev import (
    Stage27PlaceMoveReceipt,
    complete_prepared_place_move_dev,
)
from relay_self.physical_issue_admission_dev import PhysicalIssueFenceError
from relay_self.q4_place_abort_dev import (
    Q4DevMotorBoundary,
    Q4DevOperatorPermit,
    Q4PlaceAbortHold,
    run_q4_dev_place_with_motor_deadline,
)
from test_i_unified_i4a_place_lease_dev import _acks, _probes, _terminal
from test_i_unified_original_place_custody_dev import (
    _allow,
    _bind,
    _lease,
    _prepare,
    _setup,
)
from test_q4_place_abort_dev import FakeOwnedNative, _host, _start


def _case(tmp_path, monkeypatch):
    original, owner, gate, journal, typed = _setup(tmp_path, monkeypatch)
    native = FakeOwnedNative(owner.native_session_id, gate)
    host = _host(gate, native)
    host.owners = {"A": owner}
    return original, owner, gate, journal, typed, native, host


def _run(host, owner, typed, issue, **limits):
    return run_q4_dev_place_with_motor_deadline(
        bridge=host, self_id="A", action_id=typed[0].action_id,
        issue_original=issue,
        operator_permit=Q4DevOperatorPermit("A", owner.native_session_id),
        pre_start_s=limits.get("pre_start_s", 0.15),
        motor_s=limits.get("motor_s", 0.15),
        settlement_s=limits.get("settlement_s", 0.25),
    )


def _issue(original, owner, gate, journal, typed, *, delay=0.0,
           fail_stop=False, no_close=False):
    async def issue(boundary: Q4DevMotorBoundary):
        parent = typed[0].action_id
        native = owner.native_session_id
        with _lease(gate, owner, typed):
            _prepare(journal, typed)
            _bind(gate, original, owner, journal, typed)
            _allow(gate, owner, parent + "-look")
            look, start, stop = _acks(native, parent)
            boundary.before_native_start(
                action_id=parent + "-start", session_id=native,
            )
            _start(gate, owner, typed)
            boundary.accept_start_ack(start)
            if fail_stop:
                await asyncio.sleep(1)
            _allow(gate, owner, parent + "-stop", effect="clear_controls")
            boundary.accept_stop_ack(stop)
            await asyncio.sleep(delay)
            if no_close:
                return None
            initial, first, settled = _probes(native)
            terminal, supervisor = _terminal(typed[0])
            status = journal.close_place_move(
                typed[0], typed[2], typed[1], look, start, stop,
                initial, first, settled, terminal, supervisor,
            )
            return Stage27PlaceMoveReceipt(
                typed[2].invocation_ref,
                typed[2].parameter_preset_ref,
                typed[3].target_contract_ref,
                parent, native, look, start, stop,
                initial, first, settled, 0.5,
                status, journal.digest, (initial, first, settled),
            )

    return issue


def test_phased_watchdog_separates_motor_from_longer_settling(tmp_path, monkeypatch):
    original, owner, gate, journal, typed, native, host = _case(
        tmp_path, monkeypatch,
    )
    issue = _issue(original, owner, gate, journal, typed, delay=0.08)
    receipt = asyncio.run(_run(host, owner, typed, issue, motor_s=0.03))
    assert receipt.action_id == typed[0].action_id
    assert receipt.journal_status == "NATIVE_PLACE_MOVE_SETTLED"
    assert not journal.unresolved
    assert native.kill_attempts == 0
    assert gate.resident_states["A"] == "ONLINE"
    assert "motor_boundary" in inspect.signature(
        complete_prepared_place_move_dev,
    ).parameters


def test_phased_watchdog_refuses_false_success_with_unclosed_wal(tmp_path, monkeypatch):
    original, owner, gate, journal, typed, native, host = _case(
        tmp_path, monkeypatch,
    )
    issue = _issue(original, owner, gate, journal, typed, no_close=True)
    with pytest.raises(Q4PlaceAbortHold, match="terminal WAL"):
        asyncio.run(_run(host, owner, typed, issue))
    assert journal.unresolved
    assert native.kill_attempts == 1
    assert gate.resident_states["A"] == "QUARANTINED"


def test_phased_watchdog_requires_original_start_milestone(tmp_path, monkeypatch):
    _original, owner, gate, _journal, typed, native, host = _case(
        tmp_path, monkeypatch,
    )

    async def never_starts(_boundary):
        await asyncio.sleep(1)

    with pytest.raises(TimeoutError, match="pre-START"):
        asyncio.run(_run(
            host, owner, typed, never_starts, pre_start_s=0.01,
        ))
    assert native.kill_attempts == 1
    assert gate.resident_states["A"] == "QUARANTINED"


def test_phased_watchdog_never_accepts_unacknowledged_stop(tmp_path, monkeypatch):
    original, owner, gate, journal, typed, native, host = _case(
        tmp_path, monkeypatch,
    )
    issue = _issue(original, owner, gate, journal, typed, fail_stop=True)
    with pytest.raises(TimeoutError, match="START-to-STOP"):
        asyncio.run(_run(host, owner, typed, issue, motor_s=0.015))
    assert journal.unresolved
    assert native.kill_attempts == 1
    assert gate.resident_states["A"] == "QUARANTINED"


def test_phased_watchdog_settling_timeout_aborts_even_after_stop_ack(
    tmp_path, monkeypatch,
):
    original, owner, gate, journal, typed, native, host = _case(
        tmp_path, monkeypatch,
    )
    issue = _issue(original, owner, gate, journal, typed, delay=1.0)
    with pytest.raises(TimeoutError, match="post-STOP"):
        asyncio.run(_run(
            host, owner, typed, issue, settlement_s=0.015,
        ))
    assert journal.unresolved
    assert native.kill_attempts == 1
    assert gate.resident_states["A"] == "QUARANTINED"


def test_phased_watchdog_no_fake_success_without_start(tmp_path, monkeypatch):
    _original, owner, gate, _journal, typed, native, host = _case(
        tmp_path, monkeypatch,
    )

    async def fake_success(_boundary):
        return "not a native result"

    with pytest.raises(Q4PlaceAbortHold, match="without START"):
        asyncio.run(_run(host, owner, typed, fake_success))
    assert native.kill_attempts == 1
    assert gate.resident_states["A"] == "QUARANTINED"


def test_phased_watchdog_refuses_foreign_stop_ack(tmp_path, monkeypatch):
    original, owner, gate, journal, typed, native, host = _case(
        tmp_path, monkeypatch,
    )

    async def wrong_stop(boundary):
        parent = typed[0].action_id
        with _lease(gate, owner, typed):
            _prepare(journal, typed)
            _bind(gate, original, owner, journal, typed)
            _allow(gate, owner, parent + "-look")
            _, start, _ = _acks(owner.native_session_id, parent)
            boundary.before_native_start(
                action_id=parent + "-start",
                session_id=owner.native_session_id,
            )
            _start(gate, owner, typed)
            boundary.accept_start_ack(start)
            _, _, other = _acks(owner.native_session_id, "foreign")
            boundary.accept_stop_ack(other)

    with pytest.raises(Q4PlaceAbortHold, match="STOP ACK"):
        asyncio.run(_run(host, owner, typed, wrong_stop))
    assert journal.unresolved
    assert native.kill_attempts == 1


def test_motor_boundary_rejects_forged_cross_task_callback(tmp_path, monkeypatch):
    _original, owner, gate, _journal, typed, native, host = _case(
        tmp_path, monkeypatch,
    )

    async def attempt_from_other_task(boundary):
        async def attacker():
            boundary.before_native_start(
                action_id=typed[0].action_id + "-start",
                session_id=owner.native_session_id,
            )
        await asyncio.create_task(attacker())

    with pytest.raises(Q4PlaceAbortHold, match="outside original runner"):
        asyncio.run(_run(host, owner, typed, attempt_from_other_task))
    assert native.kill_attempts == 1
    assert gate.resident_states["A"] == "QUARANTINED"


def test_phased_watchdog_refuses_second_live_self_before_any_native(
    tmp_path, monkeypatch,
):
    _original, owner, gate, journal, typed, native, host = _case(
        tmp_path, monkeypatch,
    )
    host.sessions["B"] = FakeOwnedNative("other-native", gate)

    async def unexpected(_boundary):
        pytest.fail("second live Self must deny before task creation")

    with pytest.raises(Q4PlaceAbortHold, match="one bounded"):
        asyncio.run(_run(host, owner, typed, unexpected))
    assert native.kill_attempts == 0
    assert not journal.unresolved


def test_phased_watchdog_closed_gate_rejects_replay_after_cancel(
    tmp_path, monkeypatch,
):
    original, owner, gate, journal, typed, native, host = _case(
        tmp_path, monkeypatch,
    )
    issue = _issue(original, owner, gate, journal, typed, fail_stop=True)
    with pytest.raises(TimeoutError):
        asyncio.run(_run(host, owner, typed, issue, motor_s=0.015))
    with pytest.raises(PhysicalIssueFenceError):
        with _lease(gate, owner, typed):
            pytest.fail("no action replay on failed stop")
    assert journal.unresolved and native.kill_attempts == 1
