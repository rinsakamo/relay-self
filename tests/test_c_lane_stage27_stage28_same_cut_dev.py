"""C Lane interop: Stage27 v2 MOVE_PLACE source -> Stage28 same A/B typed cut.

The canonical WAL is intentionally populated with a SYNTHETIC, schema-checked
terminal native sequence, NOT through a real Stage27 issuer or Minecraft.
The *actual* Stage27 v2 validator, C1 constructor and Stage28 original typed
World/A/B save/fork/rejoin path run without fake external verifier classes.
No actual Gemma HTTP inference, C2 or physical Action is claimed.
"""
from __future__ import annotations

from dataclasses import replace

import pytest

from adapters.mineflayer.python_protocol import MineflayerPosition
from relay_self.action import ActionLifecycle
from relay_self.c_lane_stage27_source_bridge import (
    assemble_stage27_c1_from_canonical_wal,
)
from relay_self.c_lane_stage28_typed_continuity_dev import (
    verify_c1_across_stage28_typed_epoch,
)
from relay_self.cognitive_learning_contract import OutcomeAssessment
from relay_self.cognitive_learning_owner_adapter import C1AdmissionError
from relay_self.common_io import ScopeRef
from relay_self.physical_action_journal import PhysicalActionJournal
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
from test_c_lane_stage28_typed_continuity_dev import _case
from test_p0d_resident_move_issuer_dev import _probe

P = Provenance("stage27-original-code-synthetic", "NOT_NATIVE_EVIDENCE")


def _source_with_original_v2_wal(a):
    """Build a *synthetic* v2 row through original source validators in A WAL."""
    native = a.native_session_id
    scope = ScopeRef(a.self_id, native)
    first = _probe(native, 10, "stage27-before", 100, 0.0)
    last = _probe(native, 18, "stage27-after", 110, 1.0)
    contract = TargetContract(
        scope=scope, goal_id="EXPLORE_WORLD", target_ref="destination:1",
        kind=TargetKind.PLACE, reference_frame=ReferenceFrame.WORLD,
        provenance=first.provenance,
        condition=ArrivalCondition(0.0, 0.15, 1.0),
        bound_seq=10, anchor=MineflayerPosition(1.0, 64.0, 2.0),
    )
    invocation = SkillInvocation(
        scope=scope, skill_id="MOVE", skill_version=1,
        definition_ref="skill-definition:v1@" + "d" * 64,
        goal_id="EXPLORE_WORLD",
        target=SkillTarget("destination:1", "DESTINATION", contract),
        constraints=SkillConstraints(), budget=SkillBudget(2, 10000, 2.0, 16),
        provenance=P, parameter_preset_ref="skill-preset:v1@" + "e" * 64,
    )
    a.intent.commit("stage27-intent-A", objective="EXPLORE_WORLD", at_ns=10, provenance=P)
    skill = SkillExecution.start(
        "stage27-child-skill-A", skill_id="MOVE",
        intent_commitment=a.intent, at_ns=20, provenance=P,
    )
    proposal = ActionLifecycle.propose(
        "stage27-synthetic-action-A", skill_execution=skill,
        intent_commitment=a.intent, at_ns=30, provenance=P,
    ).authorize(at_ns=31, provenance=P, authority="original-stage27-synthetic")
    a.supervisor.issue(proposal, at_ns=32, deadline_ns=50, provenance=P)
    closed = a.supervisor.record_outcome(
        "stage27-synthetic-action-A", at_ns=33, provenance=P,
    )
    terminal = skill.succeed(reason="explicit simulated owner review", at_ns=40, provenance=P)
    a.skills[terminal.execution_id] = terminal

    # Test-only canonical row generation; no real issuer or native effect is
    # implied by the validator accepting the structurally complete record.
    journal = PhysicalActionJournal.restore(a.files.physical_wal_file, self_id=a.self_id)
    journal._commit([{
        "session_id": native,
        "intent_id": terminal.intent_id,
        "skill_execution_id": terminal.execution_id,
        "action_id": closed.action_id,
        "capability": "MOVE_PLACE",
        "target_ref": invocation.target.ref,
        "probe_seq": first.seq,
        "probe_request_id": first.request_id,
        "source_ref": first.provenance.reference,
        "status": "NATIVE_PLACE_MOVE_SETTLED",
        "effect_seqs": [11, 12, 13],
        "after_seq": last.seq,
        "food_before": None, "food_after": None,
        "count_before": None, "count_after": None,
        "control": "forward",
        "started_position": {"x": 0.0, "y": 64.0, "z": 2.0},
        "settled_position": {"x": 1.0, "y": 64.0, "z": 2.0},
        "initial_stop_seq": 14,
        "first_stable_seq": 15,
        "initial_stop_tick": 100,
        "first_stable_tick": 108,
        "settled_tick": 116,
        "displacement_m": 1.0,
        "invocation_ref": invocation.invocation_ref,
        "preset_ref": invocation.parameter_preset_ref,
        "target_contract_ref": contract.contract_ref,
        "target_position": {"x": 1.0, "y": 64.0, "z": 2.0},
        "aim_yaw_rad": -1.5707963267948966,
        "budget_actions": 2,
        "budget_duration_ms": 10000,
        "budget_distance_m": 2.0,
        "gait_mode": "WALK",
        "gait_ack_seq": None,
    }], upgrade_to_v2=True)
    readback = PhysicalActionJournal.restore(
        a.files.physical_wal_file, self_id=a.self_id,
    )
    assert not readback.unresolved
    assert readback.records[0]["capability"] == "MOVE_PLACE"
    assert readback.records[0]["action_id"] == closed.action_id
    exp = assemble_stage27_c1_from_canonical_wal(
        cognition=a.retained, intent=a.intent, skill=terminal,
        actions=(closed,), journal_path=a.files.physical_wal_file,
        original_wal_sha256=readback.digest,
        selected_invocation=invocation, before_probe=first, after_probe=last,
        world_id="world-1", world_epoch=0, selected_provenance=P,
    )
    assert exp is not None
    assert exp.target_outcome is OutcomeAssessment.SUCCESS
    assert exp.action_ids == (closed.action_id,)
    return exp, readback.digest, invocation, first, last


def test_original_stage27_v2_wal_crosses_one_stage28_world_a_b_generation(
    tmp_path, monkeypatch,
):
    """One original source row, not a hand-inserted C1 synthetic readout."""
    import test_c_lane_stage28_typed_continuity_dev as longitudinal

    source_setup = longitudinal._setup
    observed = {}

    def original_plus_v2(path, monkey):
        source = source_setup(path, monkey)
        a = source[0].owners["A"]
        exp, digest, _inv, _first, _last = _source_with_original_v2_wal(a)
        observed.update(exp=exp, sha=digest)
        return source

    monkeypatch.setattr(longitudinal, "_setup", original_plus_v2)
    monkeypatch.setattr(
        longitudinal, "_historical_synthetic_c1", lambda: observed["exp"],
    )
    args, exp, bridge, _b_memory = _case(tmp_path, monkeypatch)
    assert exp == observed["exp"]
    witness = verify_c1_across_stage28_typed_epoch(**args)
    assert witness.memory_id == exp.memory_id
    assert witness.historical_memory_retained
    assert not witness.real_historical_world_action_attested
    # Reopen the actual archived WAL, not a copied synthetic Memory JSON.
    source_wal = args["source_generation"] / "selves" / "A" / "physical-wal.json"
    restored_wal = args["copy"].directory / "selves" / "A" / "physical-wal.json"
    original = PhysicalActionJournal.restore(source_wal, self_id="A")
    restored = PhysicalActionJournal.restore(restored_wal, self_id="A")
    assert original.digest == restored.digest == observed["sha"]
    assert original.records == restored.records
    assert original.records[0]["capability"] == "MOVE_PLACE"
    assert bridge.owners["A"].retained.memories[0].memory_id == exp.memory_id
    assert len(bridge.owners["B"].retained.memories) == 0


@pytest.mark.parametrize("fault", ["bad-source", "wrong-target", "wrong-sha"])
def test_original_stage27_wal_read_only_assembly_rejects_foreign_source(
    tmp_path, monkeypatch, fault,
):
    from test_stage28b_retired_typed_cut_dev import _setup

    source, _paper, _store, _evidence = _setup(tmp_path, monkeypatch)
    a = source.owners["A"]
    exp, digest, inv, first, last = _source_with_original_v2_wal(a)
    assert exp is not None
    # Source readback is verified by original Stage27, but no claim of real
    # physical Action causality is made about the synthetic fixture.
    journal = PhysicalActionJournal.restore(a.files.physical_wal_file, self_id="A")
    assert journal.digest == digest
    if fault == "bad-source":
        a.files.physical_wal_file.write_bytes(b"forged")
        with pytest.raises(Exception):
            PhysicalActionJournal.restore(a.files.physical_wal_file, self_id="A")
    elif fault == "wrong-target":
        altered_invocation = replace(
            inv, parameter_preset_ref="skill-preset:v1@" + "f" * 64,
        )
        with pytest.raises(C1AdmissionError, match="lineage mismatch"):
            assemble_stage27_c1_from_canonical_wal(
                cognition=a.retained, intent=a.intent,
                skill=a.skills["stage27-child-skill-A"],
                actions=(a.supervisor.get("stage27-synthetic-action-A"),),
                journal_path=a.files.physical_wal_file,
                original_wal_sha256=journal.digest,
                selected_invocation=altered_invocation,
                before_probe=first, after_probe=last,
                world_id="world-1", world_epoch=0, selected_provenance=P,
            )
    else:
        with pytest.raises(C1AdmissionError, match="digest"):
            # The first admission check rejects an unauthenticated digest.
            assemble_stage27_c1_from_canonical_wal(
                cognition=a.retained, intent=a.intent,
                skill=a.skills["stage27-child-skill-A"],
                actions=(a.supervisor.get("stage27-synthetic-action-A"),),
                journal_path=a.files.physical_wal_file,
                original_wal_sha256="f" * 64,
                selected_invocation=inv, before_probe=first, after_probe=last,
                world_id="world-1", world_epoch=0, selected_provenance=P,
            )
