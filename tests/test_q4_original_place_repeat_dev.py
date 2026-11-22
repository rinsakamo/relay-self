"""Q4 repeat-DEV: original B WAL terminal is prerequisite to another lease.

All ACK/Native/Paper receipts below are SYNTHETIC. No real World/custody PASS.
"""
from __future__ import annotations

from dataclasses import replace

import pytest

from relay_self.owned_paper_world_dev import PaperTickReceipt
from relay_self.physical_issue_admission_dev import PhysicalIssueFenceError
from relay_self.q4_place_repeat_source_dev import Q4PlaceTerminalReadback
from test_i_unified_i4a_place_lease_dev import _acks, _probes, _terminal
from test_i_unified_original_place_custody_dev import (
    _allow, _bind, _lease, _prepare, _setup,
)


def _bundle(bridge, owner, action_id):
    look, start, stop = _acks(owner.native_session_id, action_id)
    initial, first, settled = _probes(owner.native_session_id)
    paper_session = bridge.paper.owned_session_id
    return Q4PlaceTerminalReadback(
        look, start, stop, initial, first, settled,
        PaperTickReceipt(paper_session, 110, "nativePaper-stop"),
        PaperTickReceipt(paper_session, 120, "nativePaper-first"),
        PaperTickReceipt(paper_session, 130, "nativePaper-settled"),
        250, 450,
    )


def _settle(bridge, owner, gate, journal, typed):
    action = typed[0].action_id
    with _lease(gate, owner, typed):
        _prepare(journal, typed)
        _bind(gate, bridge, owner, journal, typed)
        _allow(gate, owner, action + "-look")
        _allow(gate, owner, action + "-start", effect="set_control")
        _allow(gate, owner, action + "-stop", effect="clear_controls")
        look, start, stop = _acks(owner.native_session_id, action)
        initial, first, settled = _probes(owner.native_session_id)
        terminal, supervisor = _terminal(typed[0])
        assert journal.close_place_move(
            typed[0], typed[2], typed[1], look, start, stop,
            initial, first, settled, terminal, supervisor,
        ) == "NATIVE_PLACE_MOVE_SETTLED"
    assert gate.active_action_ids == ()
    assert not journal.unresolved
    return _bundle(bridge, owner, action)


def test_original_second_lease_reopens_only_after_bounded_settled_wal(
    tmp_path, monkeypatch,
):
    bridge, owner, gate, journal, typed = _setup(tmp_path, monkeypatch)
    proof = _settle(bridge, owner, gate, journal, typed)
    with pytest.raises(PhysicalIssueFenceError):
        with gate.lease(
            self_id="A", native_session_id=owner.native_session_id,
            action_id="place-new", effect_family="MOVE_PLACE",
        ):
            pytest.fail("second PLACE cannot run before source renewal")

    before = journal.records
    sha = gate.rearm_original_place_after_q4_settled(
        bridge=bridge, self_id="A", evidence=proof,
    )
    assert len(sha) == 64
    assert journal.records == before and not journal.unresolved
    with gate.lease(
        self_id="A", native_session_id=owner.native_session_id,
        action_id="place-new", effect_family="MOVE_PLACE",
    ):
        assert gate.active_action_ids == ("place-new",)
        # No PREPARED or new original parent-child grant by rearming itself.
        with pytest.raises(PhysicalIssueFenceError):
            _allow(gate, owner, "place-new-look")
    assert journal.records == before
    with pytest.raises(PhysicalIssueFenceError):
        gate.rearm_original_place_after_q4_settled(
            bridge=bridge, self_id="A", evidence=proof,
        )


@pytest.mark.parametrize("tamper", [
    "bad_stop_result", "wrong_native", "wrong_paper", "short_paper_ticks",
    "long_forward", "long_host", "wrong_look", "same_paper_refs",
    "wrong_initial_tick", "missing_stable", "unrelated_self",
])
def test_q4_rearm_denies_synthetic_incomplete_or_replayed_receipts(
    tmp_path, monkeypatch, tamper,
):
    bridge, owner, gate, journal, typed = _setup(tmp_path, monkeypatch)
    proof = _settle(bridge, owner, gate, journal, typed)
    sid = bridge.paper.owned_session_id
    if tamper == "bad_stop_result":
        proof = replace(proof, stop=replace(proof.stop, result="rejected"))
    elif tamper == "wrong_native":
        proof = replace(proof, stop=replace(proof.stop, session_id="foreign"))
    elif tamper == "wrong_paper":
        proof = replace(proof, paper_first=PaperTickReceipt("other", 120, "other"))
    elif tamper == "short_paper_ticks":
        proof = replace(proof, paper_first=PaperTickReceipt(sid, 111, "quick"))
    elif tamper == "long_forward":
        proof = replace(proof, forward_ms=801)
    elif tamper == "long_host":
        proof = replace(proof, host_ms=2001)
    elif tamper == "wrong_look":
        proof = replace(proof, look=replace(proof.look, action_id="forged-look"))
    elif tamper == "same_paper_refs":
        proof = replace(
            proof, paper_first=PaperTickReceipt(sid, 120, "nativePaper-stop"),
        )
    elif tamper == "wrong_initial_tick":
        proof = replace(
            proof, initial_stop=replace(
                proof.initial_stop,
                seq=1000,
            ),
        )
    elif tamper == "missing_stable":
        proof = replace(
            proof, first_stable=replace(
                proof.first_stable, request_id="",
            ),
        )
    elif tamper == "unrelated_self":
        gate.hold_for_operator()

    with pytest.raises(PhysicalIssueFenceError, match="Q4"):
        gate.rearm_original_place_after_q4_settled(
            bridge=bridge, self_id="A", evidence=proof,
        )
    assert not journal.unresolved
    assert gate.active_action_ids == ()
    with pytest.raises(PhysicalIssueFenceError):
        with gate.lease(
            self_id="A", native_session_id=owner.native_session_id,
            action_id="place-new", effect_family="MOVE_PLACE",
        ):
            pytest.fail("no new lease after bad Q4 terminal evidence")


def test_q4_prepared_unresolved_never_rearms(tmp_path, monkeypatch):
    bridge, owner, gate, journal, typed = _setup(tmp_path, monkeypatch)
    with _lease(gate, owner, typed):
        _prepare(journal, typed)
        _bind(gate, bridge, owner, journal, typed)
        _allow(gate, owner, typed[0].action_id + "-start", effect="set_control")
    assert journal.unresolved
    with pytest.raises(PhysicalIssueFenceError):
        gate.rearm_original_place_after_q4_settled(
            bridge=bridge, self_id="A",
            evidence=_bundle(bridge, owner, typed[0].action_id),
        )
    assert journal.unresolved


def test_q4_terminal_not_rearmable_after_quarantine(tmp_path, monkeypatch):
    bridge, owner, gate, journal, typed = _setup(tmp_path, monkeypatch)
    proof = _settle(bridge, owner, gate, journal, typed)
    gate.quarantine_resident(
        self_id="A", native_session_id=owner.native_session_id,
    )
    with pytest.raises(PhysicalIssueFenceError):
        gate.rearm_original_place_after_q4_settled(
            bridge=bridge, self_id="A", evidence=proof,
        )
