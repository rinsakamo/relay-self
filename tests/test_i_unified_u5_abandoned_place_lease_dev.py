"""U5 fail-closed abandoned PLACE lease tests on the original B fixture.

Synthetic Native/World only. Passing denial tests do not establish physical
STOP safety, independent WAL custody, or an atomic Native stdin boundary.
"""
from __future__ import annotations

import threading

import pytest

from relay_self.physical_action_journal import PhysicalActionJournal
from relay_self.physical_issue_admission_dev import PhysicalIssueFenceError
from test_i_unified_original_place_custody_dev import (
    _allow,
    _bind,
    _lease,
    _prepare,
    _rechecksum,
    _setup,
)


def test_abandoned_prepared_cannot_acquire_fresh_place_lease(tmp_path, monkeypatch):
    bridge, owner, gate, journal, typed = _setup(tmp_path, monkeypatch)
    with _lease(gate, owner, typed):
        _prepare(journal, typed)
        # Simulated cancellation / process failure before child admission.
    assert PhysicalActionJournal.restore(
        owner.files.physical_wal_file, self_id="A",
    ).unresolved
    with pytest.raises(PhysicalIssueFenceError, match="unchanged terminal"):
        with _lease(gate, owner, typed):
            pytest.fail("abandoned PREPARED received a fresh PLACE lease")
    with pytest.raises(PhysicalIssueFenceError):
        _allow(gate, owner, typed[0].action_id + "-look")
    assert journal.unresolved
    assert gate.active_action_ids == ()


def test_abandoned_after_one_child_cannot_restart(tmp_path, monkeypatch):
    bridge, owner, gate, journal, typed = _setup(tmp_path, monkeypatch)
    with _lease(gate, owner, typed):
        _prepare(journal, typed)
        _bind(gate, bridge, owner, journal, typed)
        _allow(gate, owner, typed[0].action_id + "-look")
        # Final Native dispatch and ACK are not attested; no automatic replay.
    with pytest.raises(PhysicalIssueFenceError, match="unchanged terminal"):
        with _lease(gate, owner, typed):
            pytest.fail("abandoned child admission was restarted")
    assert journal.unresolved


def test_preexisting_unresolved_before_first_lease_is_rejected(
    tmp_path, monkeypatch,
):
    _bridge, owner, gate, journal, typed = _setup(tmp_path, monkeypatch)
    # A failed/unscoped writer cannot grant itself a new issuer lease simply
    # because the PREPARED envelope has a valid recomputed checksum.
    _prepare(journal, typed)
    with pytest.raises(PhysicalIssueFenceError, match="unchanged terminal"):
        with _lease(gate, owner, typed):
            pytest.fail("unresolved journal was admitted")
    assert gate.active_action_ids == ()


def test_rechecks_original_s1_at_place_lease_entry(tmp_path, monkeypatch):
    _bridge, owner, gate, journal, typed = _setup(tmp_path, monkeypatch)
    _rechecksum(
        journal.path,
        lambda body: body["actions"][0].__setitem__(
            "action_id", "edited-after-owner-s1",
        ),
    )
    with pytest.raises(PhysicalIssueFenceError, match="unchanged terminal"):
        with _lease(gate, owner, typed):
            pytest.fail("rechecksummed pre-S2 S1 was admitted")
    assert gate.active_action_ids == ()


def test_same_self_cannot_get_second_concurrent_place_action(
    tmp_path, monkeypatch,
):
    bridge, owner, gate, journal, typed = _setup(tmp_path, monkeypatch)
    with _lease(gate, owner, typed):
        with pytest.raises(PhysicalIssueFenceError, match="already in flight"):
            with gate.lease(
                self_id="A", native_session_id=owner.native_session_id,
                action_id="second-action", effect_family="MOVE_PLACE",
            ):
                pytest.fail("two PLACE actions leased the same Self")
        # Multi-Self gate remains per Self; a separate B lease cannot emit a
        # Native child because it has no original B-held S1 source binding.
        with gate.lease(
            self_id="B", native_session_id=bridge.owners["B"].native_session_id,
            action_id="different-B", effect_family="MOVE_PLACE",
        ):
            with pytest.raises(PhysicalIssueFenceError):
                gate.require_native_effect(
                    self_id="B",
                    native_session_id=bridge.owners["B"].native_session_id,
                    effect="look", action_id="different-B-look",
                )
        _prepare(journal, typed)


def test_real_thread_contention_one_original_place_lease_only(
    tmp_path, monkeypatch,
):
    _bridge, owner, gate, _journal, typed = _setup(tmp_path, monkeypatch)
    entered = threading.Event()
    may_exit = threading.Event()
    failures: list[Exception] = []

    def hold_first() -> None:
        try:
            with _lease(gate, owner, typed):
                entered.set()
                assert may_exit.wait(timeout=5)
        except Exception as exc:
            failures.append(exc)

    thread = threading.Thread(target=hold_first)
    thread.start()
    try:
        assert entered.wait(timeout=5)
        with pytest.raises(PhysicalIssueFenceError, match="already in flight"):
            with gate.lease(
                self_id="A", native_session_id=owner.native_session_id,
                action_id="racing-action", effect_family="MOVE_PLACE",
            ):
                pytest.fail("simultaneous second lease succeeded")
    finally:
        may_exit.set()
        thread.join(timeout=5)
    assert not thread.is_alive()
    assert not failures


def test_quarantine_after_start_is_a_stop_safety_hold(
    tmp_path, monkeypatch,
):
    bridge, owner, gate, journal, typed = _setup(tmp_path, monkeypatch)
    with _lease(gate, owner, typed):
        _prepare(journal, typed)
        _bind(gate, bridge, owner, journal, typed)
        _allow(gate, owner, typed[0].action_id + "-look")
        _allow(gate, owner, typed[0].action_id + "-start", effect="set_control")
        gate.quarantine_resident(
            self_id="A", native_session_id=owner.native_session_id,
        )
        # Regression evidence: MOVE_PLACE STOP currently denied after a
        # quarantine, unlike legacy MOVE. This is PRE_WORLD_HOLD, not PASS.
        with pytest.raises(PhysicalIssueFenceError):
            _allow(gate, owner, typed[0].action_id + "-stop",
                   effect="clear_controls")
    assert journal.unresolved
