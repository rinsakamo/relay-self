"""U14 original B S2 issue-window adversarial CPU checks.

The history verifier is deliberately stubbed ONLY in these unit tests to
exercise physical lease/one-shot semantics. It is never stubbed in product,
and these tests do not qualify real S1 history, original L1, Native or World.
"""
from __future__ import annotations

from contextlib import ExitStack

import pytest

from relay_self.i_lane_i4a_s2_run_boundary_dev import I4AS2EmptyRunBoundary
from relay_self.physical_issue_admission_dev import PhysicalIssueFenceError
from relay_self.resident_llama_inference_lane_dev import ResidentLlamaInferenceLane
from test_i_unified_original_place_custody_dev import _setup


def _mocked_boundary(owner, monkeypatch):
    boundary = object.__new__(I4AS2EmptyRunBoundary)
    object.__setattr__(boundary, "owner", owner)
    object.__setattr__(boundary, "native_session_id", owner.native_session_id)
    # The actual U14 function must still import and call the real strict
    # boundary verifier. Here only, stub it to reach local lock/consume paths.
    monkeypatch.setattr(
        "relay_self.i_lane_i4a_s2_run_boundary_dev."
        "verify_i4a_s2_empty_run_boundary",
        lambda *_args, **_kwargs: None,
    )
    lane = object.__new__(ResidentLlamaInferenceLane)
    return boundary, lane


def test_same_original_gate_s2_window_never_grants_native_child(
    tmp_path, monkeypatch,
):
    bridge, owner, gate, journal, typed = _setup(tmp_path, monkeypatch)
    boundary, lane = _mocked_boundary(owner, monkeypatch)
    candidate = "new-S2-parent"
    original = journal.path.read_bytes()
    native_sends = []
    with gate.original_i4a_s2_first_wal_window(
        owner=owner, boundary=boundary, lane=lane, action_id=candidate,
    ):
        assert gate.active_action_ids == (candidate,)
        gate.require_original_i4a_s2_wal_window(
            owner=owner, boundary=boundary, action_id=candidate,
        )
        with pytest.raises(PhysicalIssueFenceError, match="PLACE requires"):
            gate.submit_native_effect(
                self_id="A", native_session_id=owner.native_session_id,
                effect="look", action_id=candidate + "-look",
                write=lambda: native_sends.append("LOOK"),
            )
        gate.consume_original_i4a_s2_action_once(
            owner=owner, boundary=boundary, action_id=candidate,
        )
        with pytest.raises(PhysicalIssueFenceError, match="already consumed"):
            gate.consume_original_i4a_s2_action_once(
                owner=owner, boundary=boundary, action_id=candidate,
            )
    assert gate.active_action_ids == ()
    assert native_sends == []
    assert journal.path.read_bytes() == original
    with pytest.raises(PhysicalIssueFenceError, match="replay refused"):
        with gate.lease(
            self_id="A", native_session_id=owner.native_session_id,
            action_id=candidate, effect_family="NONE",
        ):
            pytest.fail("consumed original S2 Action must never re-lease")


def test_original_s2_retained_lease_cannot_send_unbound_children(
    tmp_path, monkeypatch,
):
    bridge, owner, gate, journal, typed = _setup(tmp_path, monkeypatch)
    boundary, lane = _mocked_boundary(owner, monkeypatch)
    with ExitStack() as stack:
        with gate.original_i4a_s2_first_wal_window(
            owner=owner, boundary=boundary, lane=lane,
            action_id="s2-held", retained_lease_stack=stack,
        ):
            gate.consume_original_i4a_s2_action_once(
                owner=owner, boundary=boundary, action_id="s2-held",
            )
        assert gate.active_action_ids == ("s2-held",)
        with pytest.raises(PhysicalIssueFenceError):
            gate.require_original_i4a_s2_wal_window(
                owner=owner, boundary=boundary, action_id="s2-held",
            )
        with pytest.raises(PhysicalIssueFenceError, match="PLACE requires"):
            gate.submit_native_effect(
                self_id="A", native_session_id=owner.native_session_id,
                action_id="s2-held-start", effect="set_control",
                write=lambda: pytest.fail("no original S2 native send"),
            )
    assert gate.active_action_ids == ()
    assert not journal.unresolved


def test_original_s2_consumption_is_not_rolled_back_on_cas_failure(
    tmp_path, monkeypatch,
):
    bridge, owner, gate, journal, typed = _setup(tmp_path, monkeypatch)
    boundary, lane = _mocked_boundary(owner, monkeypatch)
    original = journal.path.read_bytes()
    with pytest.raises(RuntimeError, match="injected WAL CAS"):
        with gate.original_i4a_s2_first_wal_window(
            owner=owner, boundary=boundary, lane=lane, action_id="s2-fail",
        ):
            gate.consume_original_i4a_s2_action_once(
                owner=owner, boundary=boundary, action_id="s2-fail",
            )
            raise RuntimeError("injected WAL CAS failure")
    assert journal.path.read_bytes() == original
    assert gate.active_action_ids == ()
    with pytest.raises(PhysicalIssueFenceError, match="replay refused"):
        with gate.lease(
            self_id="A", native_session_id=owner.native_session_id,
            action_id="s2-fail", effect_family="MOVE_PLACE",
        ):
            pytest.fail("failed original CAS must not recycle parent")


def test_original_s2_source_requires_actual_window_and_same_parent(
    tmp_path, monkeypatch,
):
    bridge, owner, gate, journal, typed = _setup(tmp_path, monkeypatch)
    boundary, lane = _mocked_boundary(owner, monkeypatch)
    with pytest.raises(PhysicalIssueFenceError, match="active issuer/window"):
        gate.require_original_i4a_s2_wal_window(
            owner=owner, boundary=boundary, action_id="S2",
        )
    with gate.original_i4a_s2_first_wal_window(
        owner=owner, boundary=boundary, lane=lane, action_id="S2",
    ):
        with pytest.raises(PhysicalIssueFenceError, match="active issuer/window"):
            gate.require_original_i4a_s2_wal_window(
                owner=owner, boundary=boundary, action_id="foreign-parent",
            )
        with pytest.raises(PhysicalIssueFenceError, match="active issuer/window"):
            gate.consume_original_i4a_s2_action_once(
                owner=owner, boundary=boundary, action_id="foreign-parent",
            )
    assert not journal.unresolved


def test_original_s2_window_no_second_live_lease_or_forged_owner(
    tmp_path, monkeypatch,
):
    bridge, owner, gate, journal, typed = _setup(tmp_path, monkeypatch)
    boundary, lane = _mocked_boundary(owner, monkeypatch)
    with gate.lease(
        self_id="A", native_session_id=owner.native_session_id,
        action_id="contending", effect_family="NONE",
    ):
        with pytest.raises(PhysicalIssueFenceError, match="quiescent"):
            with gate.original_i4a_s2_first_wal_window(
                owner=owner, boundary=boundary, lane=lane, action_id="S2",
            ):
                pytest.fail("must not grant competing S2")
    with pytest.raises(PhysicalIssueFenceError, match="Owner/window required"):
        with gate.original_i4a_s2_first_wal_window(
            owner=object(), boundary=boundary, lane=lane, action_id="S2",
        ):
            pytest.fail("must not grant forged Owner")
    assert not journal.unresolved
