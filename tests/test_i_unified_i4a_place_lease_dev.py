"""U4: opt-in original PhysicalIssueAdmission + typed v2 PLACE WAL contracts.

ALL successful observations/ACKs are synthesized in this test. This test
NEVER contacts Mineflayer, Paper, GPU or World and NEVER grants real S2.
"""
from __future__ import annotations

from dataclasses import replace

import pytest

from adapters.mineflayer.python_protocol import (
    MineflayerEffectResult,
    MineflayerPosition,
)
from relay_self.action import ActionLifecycle, ActionState
from relay_self.action_supervision import ActionSupervisor
from relay_self.common_io import ScopeRef
from relay_self.intent import IntentCommitment
from relay_self.p0d_stage27b_place_motion_dev import Stage27PlaceMotionPlan
from relay_self.physical_action_journal import (
    PhysicalActionJournal,
    PhysicalJournalError,
    PhysicalJournalUnresolved,
)
from relay_self.physical_action_port import PhysicalActionBinding
from relay_self.physical_issue_admission_dev import (
    PhysicalIssueAdmission,
    PhysicalIssueFenceError,
)
from relay_self.provenance import Provenance
from relay_self.skill import SkillExecution
from relay_self.skill_invocation import (
    SkillBudget,
    SkillConstraints,
    SkillInvocation,
    SkillTarget,
)
from relay_self.target_contract import (
    ArrivalCondition,
    ReferenceFrame,
    TargetContract,
    TargetKind,
)
from test_bd1b_owner_present_dev import _configured
from test_p0d_resident_move_issuer_dev import _probe

P = Provenance("i-unified-synthetic-place", "original-contract-test-not-native")


def _typed_place(native="native-A", *, action_id="place-A", gait=None):
    before = _probe(native, 1, "place-source-1", 100, 1.0)
    scope = ScopeRef("A", native)
    target_ref = "destination:waypoint-A"
    goal_id = "EXPLORE_WORLD"
    target_contract = TargetContract(
        scope=scope, goal_id=goal_id, target_ref=target_ref,
        kind=TargetKind.PLACE, reference_frame=ReferenceFrame.WORLD,
        provenance=P,
        condition=ArrivalCondition(0.0, 0.15, 1.0),
        bound_seq=before.seq,
        anchor=MineflayerPosition(4.0, 64.0, 2.0),
    )
    invocation = SkillInvocation(
        scope=scope, skill_id="MOVE", skill_version=1,
        definition_ref="skill-definition:v1@test", goal_id=goal_id,
        target=SkillTarget(target_ref, "DESTINATION", target_contract),
        constraints=SkillConstraints(),
        budget=SkillBudget(4, 2000, 2.5),
        provenance=P,
        parameter_preset_ref="skill-preset:v1@test",
    )
    binding = PhysicalActionBinding(
        scope, "intent-A", goal_id, "MOVE", 1, "skill-A", action_id,
        "MOVE", 1, "locomotion", "DESTINATION", target_ref,
        before.seq, before.request_id, before.provenance,
    )
    motion = Stage27PlaceMotionPlan(
        self_id="A", native_session_id=native, world_epoch=1,
        native_probe_request_id=before.request_id,
        native_probe_seq=before.seq,
        inference_request_id="synthetic-L1-question",
        intent_id=binding.intent_id,
        skill_execution_id=binding.skill_execution_id,
        invocation_ref=invocation.invocation_ref,
        parameter_preset_ref=invocation.parameter_preset_ref,
        target_contract_ref=target_contract.contract_ref,
        target_ref=target_ref, gap_to_arrival_envelope_m=2.85,
        horizontal_distance_m=3.0, desired_mineflayer_yaw_rad=0.0,
        observation_status="OUTSIDE",
        next_step="NATIVE_LOOK_AND_BOUNDED_MOVE_RESOLUTION_REQUIRED_NOT_ISSUABLE",
    )
    return binding, before, invocation, motion


def _terminal(binding):
    intent = IntentCommitment()
    intent.commit(binding.intent_id, objective="EXPLORE_WORLD", at_ns=1,
                  provenance=P)
    skill = SkillExecution.start(
        binding.skill_execution_id, skill_id="MOVE",
        intent_commitment=intent, at_ns=2, provenance=P,
    )
    proposal = ActionLifecycle.propose(
        binding.action_id, skill_execution=skill,
        intent_commitment=intent, at_ns=3, provenance=P,
    )
    allowed = proposal.authorize(
        at_ns=4, provenance=P, authority="synthetic-explicit-owner",
    )
    supervisor = ActionSupervisor()
    supervisor.issue(allowed, at_ns=5, deadline_ns=100, provenance=P)
    terminal = supervisor.record_outcome(
        binding.action_id, at_ns=6, provenance=P,
    )
    assert terminal.state is ActionState.OUTCOME
    return terminal, supervisor


def _acks(native, action):
    return (
        MineflayerEffectResult(native, 2, action + "-look", "look",
                              "applied", None),
        MineflayerEffectResult(native, 3, action + "-start", "set_control",
                              "applied", None),
        MineflayerEffectResult(native, 4, action + "-stop", "clear_controls",
                              "applied", None),
    )


def _probes(native):
    return (
        _probe(native, 5, "initial-stop", 110, 1.5),
        _probe(native, 6, "first-stable", 120, 1.5),
        _probe(native, 7, "settled", 130, 1.5),
    )


def _gate(*, move=True, place=True):
    return PhysicalIssueAdmission(
        {"A": "native-A", "B": "native-B"},
        resident_mode=True, allow_resident_move=move,
        allow_resident_place_move=place,
    )


def test_original_place_lease_typed_wal_prepare_native_id_gate_and_close(tmp_path):
    gate = _gate()
    journal = PhysicalActionJournal.create(tmp_path / "original-wal.json", self_id="A")
    binding, before, invocation, motion = _typed_place()
    peer = PhysicalActionJournal.create(tmp_path / "peer-wal.json", self_id="B")
    peer_bytes = peer.path.read_bytes()
    with pytest.raises(PhysicalIssueFenceError):
        gate.require_native_effect(
            self_id="A", native_session_id="native-A",
            effect="look", action_id=binding.action_id + "-look",
        )
    with gate.lease(
        self_id="A", native_session_id="native-A",
        action_id=binding.action_id, effect_family="MOVE_PLACE",
    ):
        assert gate.active_action_ids == (binding.action_id,)
        with pytest.raises(PhysicalIssueFenceError):
            gate.require_native_effect(
                self_id="A", native_session_id="native-A",
                effect="look", action_id=binding.action_id + "-look",
            )
        before_digest = journal.digest
        journal.prepare_place_move(binding, before, invocation, motion)
        assert journal.schema_version == 2
        assert journal.digest != before_digest
        assert journal.unresolved
        with pytest.raises(PhysicalJournalUnresolved):
            journal.require_clear()
        gate.bind_native_children(
            self_id="A", native_session_id="native-A",
            lease_action_id=binding.action_id,
            parent_action_id=binding.action_id,
            family="MOVE_PLACE", journal=journal,
        )
        with pytest.raises(PhysicalIssueFenceError):
            gate.require_native_effect(
                self_id="A", native_session_id="native-A",
                effect="look", action_id="forged-look",
            )
        with pytest.raises(PhysicalIssueFenceError):
            gate.require_native_effect(
                self_id="B", native_session_id="native-B",
                effect="look", action_id=binding.action_id + "-look",
            )
        for effect, suffix in (
            ("look", "-look"), ("set_control", "-start"),
            ("clear_controls", "-stop"),
        ):
            gate.require_native_effect(
                self_id="A", native_session_id="native-A",
                effect=effect, action_id=binding.action_id + suffix,
            )
            with pytest.raises(PhysicalIssueFenceError):
                gate.require_native_effect(
                    self_id="A", native_session_id="native-A",
                    effect=effect, action_id=binding.action_id + suffix,
                )
        # The simulated EffectResult objects below did not come from IO.
        terminal, supervisor = _terminal(binding)
        look, start, stop = _acks("native-A", binding.action_id)
        status = journal.close_place_move(
            binding, invocation, before, look, start, stop,
            *_probes("native-A"), terminal, supervisor,
        )
        assert status == "NATIVE_PLACE_MOVE_SETTLED"
        assert not journal.unresolved
        assert journal.records[-1]["action_id"] == binding.action_id
        assert journal.records[-1]["effect_seqs"] == [2, 3, 4]
    assert gate.active_action_ids == ()
    assert peer.path.read_bytes() == peer_bytes
    assert PhysicalActionJournal.restore(journal.path, self_id="A").records == journal.records
    with pytest.raises(PhysicalIssueFenceError):
        gate.require_native_effect(
            self_id="A", native_session_id="native-A",
            effect="look", action_id=binding.action_id + "-look",
        )


@pytest.mark.parametrize("place,move,mode", [
    (False, True, "lease"),
    (False, False, "lease"),
    (True, True, "lease-observation"),
])
def test_original_place_lease_requires_explicit_opt_in(place, move, mode):
    if mode == "lease-observation":
        gate = PhysicalIssueAdmission(
            {"A": "native-A"}, resident_mode=True,
            allow_resident_move=move, allow_resident_place_move=place,
            observation_only=True,
        )
    else:
        gate = _gate(move=move, place=place)
    with pytest.raises(PhysicalIssueFenceError):
        with gate.lease(
            self_id="A", native_session_id="native-A",
            action_id="attempt", effect_family="MOVE_PLACE",
        ):
            pytest.fail("unqualified PLACE lease admitted")


@pytest.mark.parametrize("kwargs", [
    {"resident_mode": False, "allow_resident_move": False,
     "allow_resident_place_move": True},
    {"resident_mode": True, "allow_resident_move": False,
     "allow_resident_place_move": True},
    {"resident_mode": True, "allow_resident_move": True,
     "allow_resident_place_move": 1},
])
def test_constructor_rejects_unqualified_place_scope(kwargs):
    with pytest.raises(PhysicalIssueFenceError):
        PhysicalIssueAdmission({"A": "native-A"}, **kwargs)


def test_restored_original_b_self_cannot_acquire_place_lease(tmp_path, monkeypatch):
    case = _configured(tmp_path, monkeypatch)
    bridge = case[1]
    owner = bridge.owners["A"]
    assert bridge.physical.current_native_sessions["A"] == owner.native_session_id
    assert not bridge.physical.closed
    assert bridge.physical.active_action_ids == ()
    # B restored recovery is observation-only: it rejects before PLACE opt-in.
    assert bridge.physical.observation_only
    with pytest.raises(PhysicalIssueFenceError, match="observation-only"):
        with bridge.physical.lease(
            self_id="A", native_session_id=owner.native_session_id,
            action_id="unqualified-s2", effect_family="MOVE_PLACE",
        ):
            pytest.fail("restored B owner unexpectedly allowed physical PLACE")
    assert owner.supervisor.recorded_actions == ()
    assert PhysicalActionJournal.restore(
        owner.files.physical_wal_file, self_id="A",
    ).records == ()


def test_unresolved_place_never_binds_foreign_or_replays(tmp_path):
    gate = _gate()
    journal = PhysicalActionJournal.create(tmp_path / "original.json", self_id="A")
    binding, before, invocation, motion = _typed_place()
    with gate.lease(
        self_id="A", native_session_id="native-A",
        action_id=binding.action_id, effect_family="MOVE_PLACE",
    ):
        journal.prepare_place_move(binding, before, invocation, motion)
        with pytest.raises(PhysicalIssueFenceError):
            gate.bind_native_children(
                self_id="A", native_session_id="native-A",
                lease_action_id=binding.action_id,
                parent_action_id="forged-action", family="MOVE_PLACE",
                journal=journal,
            )
        with pytest.raises(PhysicalIssueFenceError):
            gate.bind_native_children(
                self_id="A", native_session_id="native-B",
                lease_action_id=binding.action_id,
                parent_action_id=binding.action_id, family="MOVE_PLACE",
                journal=journal,
            )
    with pytest.raises(PhysicalJournalUnresolved):
        journal.prepare_place_move(binding, before, invocation, motion)
    assert PhysicalActionJournal.restore(
        journal.path, self_id="A",
    ).unresolved
    with pytest.raises(PhysicalIssueFenceError):
        gate.require_native_effect(
            self_id="A", native_session_id="native-A",
            effect="look", action_id=binding.action_id + "-look",
        )


def test_sneak_gait_requires_separate_original_multi_control_issuer(tmp_path):
    gate = _gate()
    journal = PhysicalActionJournal.create(tmp_path / "wal.json", self_id="A")
    binding, before, invocation, motion = _typed_place()
    with gate.lease(
        self_id="A", native_session_id="native-A",
        action_id=binding.action_id, effect_family="MOVE_PLACE",
    ):
        journal.prepare_place_move(
            binding, before, invocation, motion, precision_gait="SNEAK",
        )
        with pytest.raises(PhysicalIssueFenceError):
            gate.bind_native_children(
                self_id="A", native_session_id="native-A",
                lease_action_id=binding.action_id,
                parent_action_id=binding.action_id,
                family="MOVE_PLACE", journal=journal,
            )
        with pytest.raises(PhysicalIssueFenceError):
            gate.require_native_effect(
                self_id="A", native_session_id="native-A",
                effect="look", action_id=binding.action_id + "-look",
            )
    assert journal.unresolved


def test_place_source_mismatch_rejected_before_any_wal_write(tmp_path):
    journal = PhysicalActionJournal.create(tmp_path / "wal.json", self_id="A")
    binding, before, invocation, motion = _typed_place()
    digest = journal.digest
    with pytest.raises(PhysicalJournalError):
        journal.prepare_place_move(
            replace(binding, native_request_id="forged"),
            before, invocation, motion,
        )
    with pytest.raises(PhysicalJournalError):
        journal.prepare_place_move(
            binding, before, invocation,
            replace(motion, target_contract_ref="forged"),
        )
    assert journal.digest == digest
    assert journal.schema_version == 1
    assert not journal.records
