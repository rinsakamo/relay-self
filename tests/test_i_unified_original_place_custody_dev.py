"""U5 original B S1 → one canonical PLACE lease and pre-native rechecks.

All WorldBody observations and WAL outcomes are synthetic. An in-process
source anchor is NOT authenticated independent Paper/Native custody.
"""
from __future__ import annotations

import hashlib
import json
import os
import pytest

from relay_self.physical_action_journal import PhysicalActionJournal
from relay_self.physical_issue_admission_dev import (
    PhysicalIssueAdmission,
    PhysicalIssueFenceError,
)
from test_bd1b_owner_present_dev import _configured
from test_i_unified_b_wal_prefix_dev import _eat_row
from test_i_unified_i4a_place_lease_dev import _typed_place


def _setup(tmp_path, monkeypatch):
    case = _configured(tmp_path, monkeypatch)
    bridge = case[1]
    owner = bridge.owners["A"]
    original_physical = bridge.physical
    assert original_physical.observation_only
    journal = PhysicalActionJournal.restore(
        owner.files.physical_wal_file, self_id="A",
    )
    assert journal.records == ()
    # S1 synthetic terminal row: not a real action nor Native outcome.
    journal._commit([_eat_row(session=owner.native_session_id)])
    gate = PhysicalIssueAdmission(
        original_physical.current_native_sessions,
        resident_mode=True, allow_resident_move=True,
        allow_resident_place_move=True,
    )
    # Only the synthetic test bridge receives the opt-in gate. Production B
    # recovery remains observation-only/allow_move=False.
    bridge.physical = gate
    anchor_sha = gate.arm_original_place_s1(
        bridge=bridge, self_id="A", journal=journal,
    )
    assert len(anchor_sha) == 64
    binding, before, invocation, motion = _typed_place(owner.native_session_id)
    return bridge, owner, gate, journal, (binding, before, invocation, motion)


def _prepare(journal, typed, *, gait=None):
    binding, before, invocation, motion = typed
    journal.prepare_place_move(
        binding, before, invocation, motion, precision_gait=gait,
    )
    assert journal.schema_version == 2 and journal.unresolved


def _lease(gate, owner, typed):
    return gate.lease(
        self_id="A", native_session_id=owner.native_session_id,
        action_id=typed[0].action_id, effect_family="MOVE_PLACE",
    )


def _bind(gate, bridge, owner, journal, typed):
    gate.bind_original_place_children(
        bridge=bridge, self_id="A",
        native_session_id=owner.native_session_id,
        lease_action_id=typed[0].action_id,
        parent_action_id=typed[0].action_id,
        journal=journal,
    )


def _allow(gate, owner, action_id, effect="look"):
    gate.require_native_effect(
        self_id="A", native_session_id=owner.native_session_id,
        effect=effect, action_id=action_id,
    )


def _rechecksum(path, mutator):
    value = json.loads(path.read_bytes())
    mutator(value["body"])
    canonical = json.dumps(
        value["body"], ensure_ascii=False, sort_keys=True,
        separators=(",", ":"), allow_nan=False,
    ).encode()
    value["sha256"] = hashlib.sha256(canonical).hexdigest()
    path.write_text(json.dumps(value), encoding="utf-8")


def test_original_s1_pin_is_not_rearmable_with_same_epoch(tmp_path, monkeypatch):
    bridge, owner, gate, journal, typed = _setup(tmp_path, monkeypatch)
    with pytest.raises(PhysicalIssueFenceError, match="pin"):
        gate.arm_original_place_s1(
            bridge=bridge, self_id="A", journal=journal,
        )
    with _lease(gate, owner, typed):
        with pytest.raises(PhysicalIssueFenceError, match="requires original S1-bound"):
            _allow(gate, owner, typed[0].action_id + "-look")
        _prepare(journal, typed)
        with pytest.raises(PhysicalIssueFenceError, match="original Owner-held"):
            gate.bind_native_children(
                self_id="A", native_session_id=owner.native_session_id,
                lease_action_id=typed[0].action_id,
                parent_action_id=typed[0].action_id,
                family="MOVE_PLACE", journal=journal,
            )
        _bind(gate, bridge, owner, journal, typed)
        _allow(gate, owner, typed[0].action_id + "-look")
        with pytest.raises(PhysicalIssueFenceError):
            _allow(gate, owner, typed[0].action_id + "-look")
        with pytest.raises(PhysicalIssueFenceError):
            _bind(gate, bridge, owner, journal, typed)
    with pytest.raises(PhysicalIssueFenceError):
        _allow(gate, owner, typed[0].action_id + "-start")
    assert journal.unresolved


def test_cloned_wal_not_accepted_at_bind(tmp_path, monkeypatch):
    bridge, owner, gate, journal, typed = _setup(tmp_path, monkeypatch)
    with _lease(gate, owner, typed):
        _prepare(journal, typed)
        other = tmp_path / "cloned-original.json"
        other.write_bytes(journal.path.read_bytes())
        cloned = PhysicalActionJournal.restore(other, self_id="A")
        assert cloned.records == journal.records
        with pytest.raises(PhysicalIssueFenceError, match="canonical journal"):
            _bind(gate, bridge, owner, cloned, typed)
        with pytest.raises(PhysicalIssueFenceError):
            _allow(gate, owner, typed[0].action_id + "-look")
        _bind(gate, bridge, owner, journal, typed)
        _allow(gate, owner, typed[0].action_id + "-look")


@pytest.mark.parametrize("mutation", (
    "rewritten_s1", "foreign_parent", "unresolved_gait",
    "extra_terminal", "source_s1_rechecksum",
))
def test_mutated_canonical_wal_before_bind_denied(
    tmp_path, monkeypatch, mutation,
):
    bridge, owner, gate, journal, typed = _setup(tmp_path, monkeypatch)
    with _lease(gate, owner, typed):
        _prepare(journal, typed)
        def tamper(body):
            if mutation in {"rewritten_s1", "source_s1_rechecksum"}:
                body["actions"][0]["action_id"] = "fake-S1-history"
            elif mutation == "foreign_parent":
                body["actions"][-1]["action_id"] = "foreign-action"
            elif mutation == "unresolved_gait":
                body["actions"][-1].update(
                    gait_mode="SNEAK", gait_ack_seq=None,
                )
            elif mutation == "extra_terminal":
                body["actions"].insert(0, body["actions"][0].copy())
        _rechecksum(journal.path, tamper)
        fresh = None
        try:
            fresh = PhysicalActionJournal.restore(journal.path, self_id="A")
        except (ValueError, RuntimeError):
            pass
        if fresh is not None:
            with pytest.raises(PhysicalIssueFenceError):
                _bind(gate, bridge, owner, fresh, typed)
        with pytest.raises(PhysicalIssueFenceError):
            _allow(gate, owner, typed[0].action_id + "-look")


@pytest.mark.parametrize("change", (
    "resident_epoch", "world_epoch", "native_owner", "foreign_bridge",
    "foreign_owner", "physical_epoch", "physical_session", "owner_path",
))
def test_original_scope_custody_drift_before_bind_denied(
    tmp_path, monkeypatch, change,
):
    bridge, owner, gate, journal, typed = _setup(tmp_path, monkeypatch)
    with _lease(gate, owner, typed):
        _prepare(journal, typed)
        state = bridge.cognitive_work._states["A"]
        if change == "resident_epoch":
            state.epoch += 1
        elif change == "world_epoch":
            state.world_epoch += 1
        elif change == "native_owner":
            owner.native_session_id = "foreign-native"
        elif change == "foreign_bridge":
            bridge.physical = object()
        elif change == "foreign_owner":
            bridge.owners["A"] = bridge.owners["B"]
        elif change == "physical_epoch":
            gate._resident_epochs["A"] += 1
        elif change == "physical_session":
            gate._sessions["A"] = "foreign-native"
        elif change == "owner_path":
            object.__setattr__(
                owner.files, "physical_wal_file", tmp_path / "foreign-wal.json",
            )
        with pytest.raises((PhysicalIssueFenceError, AttributeError)):
            _bind(gate, bridge, owner, journal, typed)
        assert gate._native_child_ids["A"] == {}
        assert gate._used_native_children["A"] == set()


@pytest.mark.parametrize("tampering", (
    "byte_identical_replace", "rechecksum_s1", "rechecksum_prepared",
    "terminal_before_native", "symlink",
))
def test_original_pre_native_custody_detects_wal_replacement(
    tmp_path, monkeypatch, tampering,
):
    bridge, owner, gate, journal, typed = _setup(tmp_path, monkeypatch)
    with _lease(gate, owner, typed):
        _prepare(journal, typed)
        _bind(gate, bridge, owner, journal, typed)
        action = typed[0].action_id + "-look"
        if tampering == "byte_identical_replace":
            replacement = tmp_path / "same-bytes.json"
            replacement.write_bytes(journal.path.read_bytes())
            os.replace(replacement, journal.path)
        elif tampering == "rechecksum_s1":
            _rechecksum(
                journal.path,
                lambda body: body["actions"][0].__setitem__(
                    "action_id", "altered-S1",
                ),
            )
        elif tampering == "rechecksum_prepared":
            _rechecksum(
                journal.path,
                lambda body: body["actions"][-1].__setitem__(
                    "action_id", "alternate-S2",
                ),
            )
        elif tampering == "terminal_before_native":
            # A fake terminal does not qualify physical/Native issuance.
            _rechecksum(
                journal.path,
                lambda body: body["actions"][-1].__setitem__(
                    "status", "NATIVE_PLACE_MOVE_SETTLED",
                ),
            )
        elif tampering == "symlink":
            copied = tmp_path / "linked.json"
            copied.write_bytes(journal.path.read_bytes())
            journal.path.unlink()
            journal.path.symlink_to(copied)
        with pytest.raises(PhysicalIssueFenceError):
            _allow(gate, owner, action)
        assert not gate._used_native_children["A"]


@pytest.mark.parametrize("what", (
    "cognitive_fence", "physical_quarantine", "physical_close",
    "world_epoch", "bridge_physical", "original_wal_path",
))
def test_original_place_bound_pre_native_fence_denies_final_stdin(
    tmp_path, monkeypatch, what,
):
    bridge, owner, gate, journal, typed = _setup(tmp_path, monkeypatch)
    with _lease(gate, owner, typed):
        _prepare(journal, typed)
        _bind(gate, bridge, owner, journal, typed)
        if what == "cognitive_fence":
            bridge.cognitive_work.fence_self("A")
        elif what == "physical_quarantine":
            gate.quarantine_resident(
                self_id="A", native_session_id=owner.native_session_id,
            )
        elif what == "physical_close":
            try:
                gate.close()
            except PhysicalIssueFenceError:
                pass
            # Even a failed close must not create a physical grant.
        elif what == "world_epoch":
            bridge.cognitive_work._states["A"].world_epoch += 1
        elif what == "bridge_physical":
            bridge.physical = object()
        elif what == "original_wal_path":
            # Frozen OwnerFiles may prohibit in-place mutation; use an
            # adversarial alternate object at the owning bridge instead.
            bridge.owners["A"] = bridge.owners["B"]
        with pytest.raises(PhysicalIssueFenceError):
            _allow(gate, owner, typed[0].action_id + "-look")


def test_canonical_wal_swap_after_one_child_blocks_remaining(
    tmp_path, monkeypatch,
):
    bridge, owner, gate, journal, typed = _setup(tmp_path, monkeypatch)
    with _lease(gate, owner, typed):
        _prepare(journal, typed)
        _bind(gate, bridge, owner, journal, typed)
        _allow(gate, owner, typed[0].action_id + "-look")
        same = tmp_path / "replaced-byte-identical-after-look"
        same.write_bytes(journal.path.read_bytes())
        os.replace(same, journal.path)
        with pytest.raises(PhysicalIssueFenceError):
            _allow(gate, owner, typed[0].action_id + "-start",
                   effect="set_control")
        assert gate._used_native_children["A"] == {typed[0].action_id + "-look"}


def test_no_new_s1_anchor_on_original_b_observation_only(
    tmp_path, monkeypatch,
):
    case = _configured(tmp_path, monkeypatch)
    bridge = case[1]
    owner = bridge.owners["A"]
    journal = PhysicalActionJournal.restore(
        owner.files.physical_wal_file, self_id="A",
    )
    with pytest.raises(PhysicalIssueFenceError):
        bridge.physical.arm_original_place_s1(
            bridge=bridge, self_id="A", journal=journal,
        )
    assert journal.records == ()
