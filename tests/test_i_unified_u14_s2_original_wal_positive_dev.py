"""U14: positive S2 PREPARED append on the SAME original B Owner and WAL.

Synthetic old PLACE/Native Action, and a deliberately stubbed historical
I4a L1 boundary verifier to exercise the NEW common issuer's WAL transition.
Does not attest real original S1 producer, L1 selection, Native or World.
"""
from __future__ import annotations

from dataclasses import replace
from types import SimpleNamespace

import pytest

from adapters.mineflayer.process_session import MineflayerProcessSession
from experiments.cognitive_physical_executor_dev import (
    PhysicalDevGrant,
    PhysicalGrantStage,
    begin_physical_issue_dev,
)
from relay_self.action import ActionState
from relay_self.i_lane_i4a_s2_run_boundary_dev import I4AS2EmptyRunBoundary
from relay_self.intent import IntentCommitment
from relay_self.physical_action_journal import PhysicalActionJournal
from relay_self.physical_action_port import (
    PhysicalCapability,
    PhysicalReadback,
    propose_bound_physical_action,
)
from relay_self.physical_issue_admission_dev import (
    PhysicalIssueAdmission,
    PhysicalIssueFenceError,
)
from relay_self.provenance import Provenance
from relay_self.resident_llama_inference_lane_dev import ResidentLlamaInferenceLane
from relay_self.skill import SkillExecution
from test_bd1b_owner_present_dev import _configured
from test_i_unified_i4a_place_lease_dev import (
    P,
    _acks,
    _probes,
    _terminal,
    _typed_place,
)
from test_p0d_resident_move_issuer_dev import _probe


class ScriptedS2(MineflayerProcessSession):
    """No Node process, native encoder, decoder, stdout or Physical IO."""

    def __init__(self, native):
        self._synthetic_session = SimpleNamespace(session_id=native)

    @property
    def started(self):
        return self._synthetic_session

    @property
    def process_returncode(self):
        return None


def _boundary(owner, native, original, journal, fresh):
    b = object.__new__(I4AS2EmptyRunBoundary)
    for name, value in {
        "owner": owner,
        "self_id": owner.self_id,
        "native_session_id": native,
        "old_intent_id": original.intent_id,
        "old_skill_id": original.skill_execution_id,
        "new_intent_id": "new-intent-S2",
        "new_skill_id": "new-skill-S2",
        "prefix_count": len(journal.records),
        "prefix_digest": journal.digest,
        "prefix_action_ids": tuple(r["action_id"] for r in journal.records),
        "post_model_probe_id": fresh.request_id,
        "post_model_probe_seq": fresh.seq,
    }.items():
        object.__setattr__(b, name, value)
    return b


def _case(tmp_path, monkeypatch):
    case = _configured(tmp_path, monkeypatch)
    bridge = case[1]
    owner = bridge.owners["A"]
    native = owner.native_session_id
    gate = PhysicalIssueAdmission(
        bridge.physical.current_native_sessions,
        resident_mode=True, allow_resident_move=True,
        allow_resident_place_move=True,
    )
    bridge.physical = gate
    journal = PhysicalActionJournal.restore(
        owner.files.physical_wal_file, self_id="A",
    )
    old, before, invocation, motion = _typed_place(
        native, action_id="original-S1-place",
    )
    journal.prepare_place_move(old, before, invocation, motion)
    terminal, supervisor = _terminal(old)
    look, start, stop = _acks(native, old.action_id)
    assert journal.close_place_move(
        old, invocation, before, look, start, stop,
        *_probes(native), terminal, supervisor,
    ) == "NATIVE_PLACE_MOVE_SETTLED"
    owner.supervisor = supervisor
    gate.arm_original_place_s1(bridge=bridge, self_id="A", journal=journal)
    old_wal_bytes = journal.path.read_bytes()

    intent = IntentCommitment()
    intent.commit(
        "new-intent-S2", objective="EXPLORE_WORLD",
        at_ns=200000, provenance=P,
    )
    skill = SkillExecution.start(
        "new-skill-S2", skill_id="MOVE", intent_commitment=intent,
        at_ns=200001, provenance=P,
    )
    owner.intent = intent
    owner.skills[skill.execution_id] = skill
    current = _probe(native, 14, "s2-source-probe", 180, 2.0)
    old_binding, _, s2_invocation, s2_motion = _typed_place(
        native, action_id="new-S2-place",
    )
    binding = replace(
        old_binding, intent_id="new-intent-S2",
        skill_execution_id=skill.execution_id,
        native_seq=current.seq, native_request_id=current.request_id,
        native_source=current.provenance,
    )
    motion = replace(
        s2_motion, intent_id=binding.intent_id,
        skill_execution_id=binding.skill_execution_id,
        native_probe_seq=current.seq,
        native_probe_request_id=current.request_id,
    )
    proposal = propose_bound_physical_action(
        binding,
        capability=PhysicalCapability(
            "MOVE", 1, "locomotion", "DESTINATION", True,
        ),
        readback=PhysicalReadback(
            binding.scope, current.provenance,
            current.seq, current.request_id, (binding.target_ref,), True,
        ),
        intent_owner=intent, skill_execution=skill,
        supervisor=supervisor, at_ns=200002, provenance=P,
    )
    boundary = _boundary(owner, native, old, journal, current)
    lane = object.__new__(ResidentLlamaInferenceLane)
    # Important: only the original *source proof* is stubbed for this CPU
    # unit test. The product always invokes its strict real verifier.
    monkeypatch.setattr(
        "relay_self.i_lane_i4a_s2_run_boundary_dev."
        "verify_i4a_s2_empty_run_boundary",
        lambda *_a, **_kw: None,
    )

    def grant(stage):
        return PhysicalDevGrant(
            stage, "operator-" + stage.value,
            Provenance("operator-" + stage.value, native),
            binding.intent_id, binding.action_id,
            native, binding.native_seq, binding.native_request_id,
            binding.target_ref, True,
        )

    return (
        bridge, owner, gate, journal, old_wal_bytes, boundary, lane,
        ScriptedS2(native), proposal, current, s2_invocation, motion,
        grant(PhysicalGrantStage.PROPOSE),
        grant(PhysicalGrantStage.ISSUE),
    )


def _reserve(parts, *, prior=True):
    (
        bridge, owner, gate, journal, old_wal, boundary, lane,
        native, proposal, current, invocation, motion, propose_grant,
        issue_grant,
    ) = parts
    with gate.original_i4a_s2_first_wal_window(
        owner=owner, boundary=boundary, lane=lane,
        action_id=proposal.binding.action_id,
    ):
        gate.consume_original_i4a_s2_action_once(
            owner=owner, boundary=boundary,
            action_id=proposal.binding.action_id,
        )
        begin_physical_issue_dev(
            native, capability="MOVE", proposal=proposal,
            current_probe=current, propose_grant=propose_grant,
            issue_grant=issue_grant, intent_owner=owner.intent,
            skill_execution=owner.skills[boundary.new_skill_id],
            supervisor=owner.supervisor, journal=journal,
            at_ns=200003, refusal=ValueError,
            place_invocation=invocation, place_motion=motion,
            allow_prior_original_place_terminals=prior,
            i4a_s2_boundary=boundary, i4a_s2_owner=owner,
            i4a_s2_physical=gate,
        )


def test_original_b_cpu_s2_appends_one_prepared_without_native(
    tmp_path, monkeypatch,
):
    parts = _case(tmp_path, monkeypatch)
    bridge, owner, gate, journal, old_wal, boundary, lane = parts[:7]
    old_rows = journal.records
    _reserve(parts)
    rows = PhysicalActionJournal.restore(
        owner.files.physical_wal_file, self_id="A",
    ).records
    assert rows[:len(old_rows)] == old_rows
    assert len(rows) == 2
    assert rows[-1]["status"] == "PREPARED_UNRESOLVED"
    assert rows[-1]["action_id"] == "new-S2-place"
    assert journal.unresolved
    assert owner.supervisor.get("new-S2-place").state is ActionState.ISSUED
    assert gate.active_action_ids == ()
    with pytest.raises(PhysicalIssueFenceError):
        gate.submit_native_effect(
            self_id="A", native_session_id=owner.native_session_id,
            effect="set_control", action_id="new-S2-place-start",
            write=lambda: pytest.fail("S2 CPU fixture must never send Native"),
        )
    with pytest.raises(PhysicalIssueFenceError, match="replay refused"):
        with gate.lease(
            self_id="A", native_session_id=owner.native_session_id,
            action_id="new-S2-place", effect_family="MOVE_PLACE",
        ):
            pytest.fail("prepared original S2 replay")
    # The old S1 prefix is preserved, but this is not a real source proof.
    assert owner.files.physical_wal_file.read_bytes() != old_wal


def test_s2_original_issue_refuses_unqualified_prior_history_before_wal(
    tmp_path, monkeypatch,
):
    parts = _case(tmp_path, monkeypatch)
    owner, gate, journal = parts[1:4]
    unchanged = journal.path.read_bytes()
    with pytest.raises(ValueError, match="invalid PLACE reservation parameters"):
        _reserve(parts, prior=False)
    assert journal.path.read_bytes() == unchanged
    assert not journal.unresolved
    assert gate.active_action_ids == ()
    with pytest.raises(PhysicalIssueFenceError, match="replay refused"):
        with gate.lease(
            self_id="A", native_session_id=owner.native_session_id,
            action_id="new-S2-place", effect_family="NONE",
        ):
            pytest.fail("early rejection must still consume Action ID")
