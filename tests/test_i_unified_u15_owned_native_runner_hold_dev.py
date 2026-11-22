"""U15: the real S2 Q4 entry must not accept synthetic bridge/Native.

No Paper, Minecraft, Node, socket, GPU or actual world is started here.
The tests deliberately supply a forged only-CPU S2 proposal to prove the
old scripted B bridge is rejected BEFORE any WAL or Native effect.
"""
from __future__ import annotations

import asyncio
import inspect
from types import SimpleNamespace

import pytest

from relay_self.i_lane_i4a_s2_first_move_proposal_dev import (
    I4AS2FirstMoveProposal,
)
from relay_self.i_lane_i4a_s2_owned_native_runner_dev import (
    I4AS2OwnedNativeHold,
    issue_i4a_s2_place_on_original_owned_native_dev,
)
from relay_self.q4_place_abort_dev import Q4DevOperatorPermit
from test_i_unified_i4a_place_lease_dev import P
from test_i_unified_u14_s2_original_wal_positive_dev import _case


def _kwargs(tmp_path, monkeypatch):
    bridge, owner, gate, journal, _, boundary, lane, _, proposal, current, inv, motion, g1, g2 = _case(
        tmp_path, monkeypatch,
    )
    synthetic = I4AS2FirstMoveProposal(
        boundary, current, proposal.binding.action_id,
        inv.invocation_ref, motion, object(), object(), object(), proposal,
    )
    return dict(
        bridge=bridge, candidate=synthetic,
        previous_probe=current,
        propose_grant=g1, issue_grant=g2,
        operator_permit=Q4DevOperatorPermit("A", owner.native_session_id),
        native_stdout_path=tmp_path / "native-new.jsonl",
        at_ns=200003, provenance=P,
        grant_real_world=True,
        acknowledge_dev_unverified_principal=True,
    ), journal


def test_real_s2_runner_does_not_accept_injected_native_or_new_owner():
    assert inspect.iscoroutinefunction(
        issue_i4a_s2_place_on_original_owned_native_dev,
    )
    names = inspect.signature(
        issue_i4a_s2_place_on_original_owned_native_dev,
    ).parameters
    assert "session" not in names
    assert "native_sender" not in names
    assert "physical" not in names
    assert "bridge" in names
    assert "operator_permit" in names
    assert "native_stdout_path" in names


def test_real_runner_refuses_synthetic_native_before_any_wal_or_stdout(
    tmp_path, monkeypatch,
):
    arguments, journal = _kwargs(tmp_path, monkeypatch)
    original = journal.path.read_bytes()
    with pytest.raises(I4AS2OwnedNativeHold, match="original B Owner-bound S2"):
        asyncio.run(issue_i4a_s2_place_on_original_owned_native_dev(**arguments))
    assert journal.path.read_bytes() == original
    assert not arguments["native_stdout_path"].exists()
    assert arguments["bridge"].physical.active_action_ids == ()


@pytest.mark.parametrize("mutation", [
    "grant_off", "no_operator", "foreign_owner", "foreign_session",
    "missing_source", "unbounded_native",
])
def test_real_runner_never_reaches_native_on_unqualified_owner(
    tmp_path, monkeypatch, mutation,
):
    arguments, journal = _kwargs(tmp_path, monkeypatch)
    original = journal.path.read_bytes()
    owner = arguments["bridge"].owners["A"]
    if mutation == "grant_off":
        arguments["grant_real_world"] = False
    elif mutation == "no_operator":
        arguments["operator_permit"] = None
    elif mutation == "foreign_owner":
        arguments["bridge"].owners["A"] = object()
    elif mutation == "foreign_session":
        arguments["operator_permit"] = Q4DevOperatorPermit("A", "foreign-native")
    elif mutation == "missing_source":
        arguments["bridge"].owners["A"].current_worldbody_observation = None
    else:
        arguments["bridge"].sessions["A"] = SimpleNamespace(
            bounded_place_dev_mode=False,
        )
    with pytest.raises((I4AS2OwnedNativeHold, AttributeError, TypeError)):
        asyncio.run(issue_i4a_s2_place_on_original_owned_native_dev(**arguments))
    assert journal.path.read_bytes() == original
    assert not arguments["native_stdout_path"].exists()
    assert arguments["bridge"].physical.active_action_ids == ()
