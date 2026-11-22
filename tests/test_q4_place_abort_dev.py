"""Q4 CPU hostile host abort: canceled PLACE lease may never retain motion.

Synthetic physical WAL/Native only. Termination is not an ACK/settle proof.
"""
from __future__ import annotations

import asyncio
from types import SimpleNamespace

import pytest

from relay_self.physical_issue_admission_dev import PhysicalIssueFenceError
from relay_self.q4_place_abort_dev import (
    Q4PlaceAbortHold,
    abort_original_place_after_start,
    run_q4_dev_place_with_watchdog,
)
from test_i_unified_original_place_custody_dev import (
    _bind,
    _lease,
    _prepare,
    _setup,
)


class FakeOwnedNative:
    def __init__(self, session_id, physical, *, fail_stop=False, fail_exit=False):
        self.started = SimpleNamespace(session_id=session_id)
        self.process_returncode = None
        self.physical = physical
        self.fail_stop = fail_stop
        self.fail_exit = fail_exit
        self.stop_attempts = []
        self.kill_attempts = 0

    async def send_clear_controls(self, action_id):
        self.stop_attempts.append(action_id)
        if self.fail_stop:
            raise BrokenPipeError("STOP native bytes rejected")
        self.physical.submit_native_effect(
            self_id="A", native_session_id=self.started.session_id,
            effect="clear_controls", action_id=action_id,
            write=lambda: None,  # synthetic original Native stdin
        )

    async def force_terminate_owned(self, *, timeout_s):
        self.kill_attempts += 1
        if self.fail_exit:
            raise TimeoutError("OS child refuses termination")
        self.process_returncode = -15
        return -15


def _host(gate, native):
    def quarantine(sid):
        assert sid == "A"
        gate.quarantine_resident(
            self_id="A", native_session_id=native.started.session_id,
        )

    return SimpleNamespace(
        sessions={"A": native},
        physical=gate,
        quarantine=quarantine,
    )


def _start(gate, owner, typed):
    gate.submit_native_effect(
        self_id="A", native_session_id=owner.native_session_id,
        effect="set_control", action_id=typed[0].action_id + "-start",
        write=lambda: None,
    )


def test_cancel_after_start_and_lease_expiry_forces_native_termination(
    tmp_path, monkeypatch,
):
    bridge, owner, gate, journal, typed = _setup(tmp_path, monkeypatch)
    native = FakeOwnedNative(owner.native_session_id, gate)
    host = _host(gate, native)

    async def issue():
        with _lease(gate, owner, typed):
            _prepare(journal, typed)
            _bind(gate, bridge, owner, journal, typed)
            _start(gate, owner, typed)
            await asyncio.sleep(30)

    async def scenario():
        with pytest.raises(TimeoutError):
            await run_q4_dev_place_with_watchdog(
                bridge=host, self_id="A",
                stop_action_id=typed[0].action_id + "-stop",
                issue_original=issue, operator_one_shot_opt_in=True,
                watchdog_s=0.01,
            )

    asyncio.run(scenario())
    assert gate.active_action_ids == ()
    assert gate.resident_states["A"] == "QUARANTINED"
    assert native.kill_attempts == 1
    assert native.process_returncode is not None
    assert native.stop_attempts == [typed[0].action_id + "-stop"]
    assert journal.unresolved
    with pytest.raises(PhysicalIssueFenceError):
        with _lease(gate, owner, typed):
            pytest.fail("same session replay after cancel")


def test_stop_denied_even_with_active_lease_falls_back_to_owned_kill(
    tmp_path, monkeypatch,
):
    bridge, owner, gate, journal, typed = _setup(tmp_path, monkeypatch)
    native = FakeOwnedNative(owner.native_session_id, gate, fail_stop=True)
    host = _host(gate, native)

    async def scenario():
        with _lease(gate, owner, typed):
            _prepare(journal, typed)
            _bind(gate, bridge, owner, journal, typed)
            _start(gate, owner, typed)
            receipt = await abort_original_place_after_start(
                bridge=host, self_id="A",
                stop_action_id=typed[0].action_id + "-stop",
            )
            assert receipt.process_terminated and receipt.stop_attempted
            assert not receipt.stop_ack_attested
            assert not receipt.world_settled_attested
            assert not receipt.wal_resolved

    asyncio.run(scenario())
    assert native.kill_attempts == 1
    assert gate.resident_states["A"] == "QUARANTINED"
    assert journal.unresolved


def test_even_buffered_stop_without_ack_must_terminate_original_bot(
    tmp_path, monkeypatch,
):
    bridge, owner, gate, journal, typed = _setup(tmp_path, monkeypatch)
    native = FakeOwnedNative(owner.native_session_id, gate)
    host = _host(gate, native)

    async def scenario():
        with _lease(gate, owner, typed):
            _prepare(journal, typed)
            _bind(gate, bridge, owner, journal, typed)
            _start(gate, owner, typed)
            return await abort_original_place_after_start(
                bridge=host, self_id="A",
                stop_action_id=typed[0].action_id + "-stop",
            )

    receipt = asyncio.run(scenario())
    assert receipt.stop_attempted and receipt.process_terminated
    assert not receipt.stop_ack_attested
    assert native.kill_attempts == 1
    assert journal.unresolved


def test_failed_kill_is_explicit_hold_not_false_safe_stop(
    tmp_path, monkeypatch,
):
    bridge, owner, gate, journal, typed = _setup(tmp_path, monkeypatch)
    native = FakeOwnedNative(owner.native_session_id, gate, fail_exit=True)
    host = _host(gate, native)

    async def scenario():
        with _lease(gate, owner, typed):
            _prepare(journal, typed)
            _bind(gate, bridge, owner, journal, typed)
            _start(gate, owner, typed)
            with pytest.raises(Q4PlaceAbortHold, match="termination not confirmed"):
                await abort_original_place_after_start(
                    bridge=host, self_id="A",
                    stop_action_id=typed[0].action_id + "-stop",
                )

    asyncio.run(scenario())
    assert native.kill_attempts == 1
    assert native.process_returncode is None
    assert journal.unresolved
    assert gate.closed


def test_explicit_dev_operator_opt_in_is_not_optional(tmp_path, monkeypatch):
    bridge, owner, gate, journal, typed = _setup(tmp_path, monkeypatch)
    native = FakeOwnedNative(owner.native_session_id, gate)
    host = _host(gate, native)
    invoked = []

    async def issue():
        invoked.append(True)

    async def scenario():
        with pytest.raises(Q4PlaceAbortHold, match="one-time DEV"):
            await run_q4_dev_place_with_watchdog(
                bridge=host, self_id="A",
                stop_action_id=typed[0].action_id + "-stop",
                issue_original=issue, operator_one_shot_opt_in=False,
            )
        with pytest.raises(Q4PlaceAbortHold, match="one-time DEV"):
            await run_q4_dev_place_with_watchdog(
                bridge=host, self_id="A",
                stop_action_id=typed[0].action_id + "-stop",
                issue_original=issue, operator_one_shot_opt_in=True,
                watchdog_s=2.01,
            )

    asyncio.run(scenario())
    assert invoked == []
    assert native.kill_attempts == 0
    assert not journal.unresolved


def test_foreign_native_session_cannot_revoke_another_self(tmp_path, monkeypatch):
    bridge, owner, gate, journal, typed = _setup(tmp_path, monkeypatch)
    native = FakeOwnedNative("foreign-session", gate)
    host = _host(gate, native)

    async def scenario():
        with pytest.raises(Q4PlaceAbortHold, match="old/foreign"):
            await abort_original_place_after_start(
                bridge=host, self_id="A",
                stop_action_id=typed[0].action_id + "-stop",
            )

    asyncio.run(scenario())
    assert gate.resident_states["A"] == "ONLINE"
    assert native.kill_attempts == 0
