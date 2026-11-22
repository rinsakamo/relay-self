"""Stage28b synthetic original owner + one stopped Paper typed cut; no Minecraft."""
from __future__ import annotations

import asyncio
from dataclasses import replace
from types import SimpleNamespace

import pytest

from relay_self import stage28b_retired_resident_typed_cut_dev as stage28b
from relay_self.action_supervision import ActionSupervisor
from relay_self.checkpointed_cognitive_runtime_dev import (
    CheckpointedCognitiveOwner,
    CognitiveOwnerFiles,
)
from relay_self.cognitive_minimal_dev import (
    initial_patterns,
    initial_patterns_with_relative_move,
)
from relay_self.coordinated_autosave_runtime_dev import StoppedWorldReceipt
from relay_self.coordinated_checkpoint_dev import restore_generation
from relay_self.initial_skill_ir import initial_skill_definitions
from relay_self.intent import IntentCommitment
from relay_self.p0d_stage26_gemma_l1_dev import Stage26L1Refusal, build_stage26_move_round
from relay_self.persistent_cognition import (
    IdentitySpecification,
    PersistentCognition,
    save_persistent_cognition,
)
from relay_self.physical_action_journal import PhysicalActionJournal
from relay_self.provenance import Provenance
from relay_self.resident_cognitive_work_owner_dev import (
    ResidentCognitiveWorkError,
    ResidentCognitiveWorkOwner,
)
from relay_self.schema_bootstrap_dev import (
    SchemaBootstrapConfig,
    bootstrap_fresh_schemas,
    create_fresh_owner,
)
from relay_self.self_owner_checkpoint_dev import verify_typed_generation
from relay_self.skill_invocation import SkillBudget, SkillConstraints, SkillParameterPreset
from relay_self.stage28_cognitive_recovery_gate_dev import (
    stage28_inert_cognitive_recovery,
)
from relay_self.world_resident_lifecycle_dev import (
    WorldLifetime,
    WorldOnlyQuiescenceEvidence,
)
from test_stage24a_resident_l1_move_dev import probe


class FakeOwnedPaper:
    def __init__(self, world_dir):
        self.world_dir = world_dir
        self.world_id = "world-1"
        self.branch_id = "source"
        self.owned_session_id = "paper-owned-original"
        self.held_uncertain = False
        self.stop_count = 0
        self.logical_tick = 110

    def stop_and_save(self):
        self.stop_count += 1
        self.owned_session_id = None
        return StoppedWorldReceipt(
            "world-1", "source", "paper-owned-original",
            self.logical_tick, "paper:main-thread-tick:110",
            "paper:owned-process-exit:0", 0, True,
        )


class FakeRetiredBridge:
    def __init__(self, paper, owners):
        self.paper = paper
        self.owners = owners
        self.lifecycle = SimpleNamespace(
            world=WorldLifetime(
                "world-1", "source", "paper-owned-original", 0, 100,
            ),
            self_roster=tuple(sorted(owners)),
        )
        self.quiescence_checks = 0
        self.dirty_after_first = False

    def world_only_quiescence(self):
        self.quiescence_checks += 1
        if self.dirty_after_first and self.quiescence_checks > 1:
            raise stage28b.Stage28bRetiredCutHold("late native rejoin/lease")
        return WorldOnlyQuiescenceEvidence(
            0, self.lifecycle.self_roster, "original-retirement-world0",
            True, True, True, True, True,
        )


def _setup(tmp_path, monkeypatch, *, roster=("A", "B")):
    monkeypatch.setattr(stage28b, "OwnedPaperWorld", FakeOwnedPaper)
    monkeypatch.setattr(stage28b, "OwnedResidentPhysicalBridge", FakeRetiredBridge)
    world = tmp_path / "world"
    world.mkdir()
    (world / "level.dat").write_bytes(b"fake-W100")
    (world / "entities").mkdir()
    (world / "entities" / "r.0.0.mca").write_bytes(b"zombie-alive")
    store = tmp_path / "generations"
    store.mkdir()
    evidence = tmp_path / "evidence"
    evidence.mkdir()
    owners = {}
    for sid in roster:
        root = tmp_path / ("self-" + sid)
        root.mkdir()
        wal = root / "physical-wal.json"
        PhysicalActionJournal.create(wal, self_id=sid)
        retained = PersistentCognition(
            IdentitySpecification(sid, ("Stable identity",), Provenance("self", sid)),
        )
        cognition = root / "cognition.json"
        save_persistent_cognition(cognition, retained)
        owner = CheckpointedCognitiveOwner(
            retained=retained, intent=IntentCommitment(),
            pattern_registry=initial_patterns(),
            native_session_id="native-retired-" + sid,
            last_observed_tick=105,
            files=CognitiveOwnerFiles(root, cognition, wal),
            physical_supervisor=ActionSupervisor(),
        )
        owners[sid] = owner
    paper = FakeOwnedPaper(world)
    bridge = FakeRetiredBridge(paper, owners)
    return bridge, paper, store, evidence


def test_stage28b_original_a_b_retired_typed_capture_and_inert_restore(
    tmp_path, monkeypatch,
):
    bridge, paper, store, evidence = _setup(tmp_path, monkeypatch)
    result = stage28b.capture_retired_resident_typed_world(
        bridge=bridge, paper=paper, store=store, evidence_dir=evidence,
    )
    assert result.verified_self_ids == ("A", "B")
    assert result.stopped_world_tick == 110
    assert result.real_60_second_autosave_attested is False
    assert result.automatic_l1_replay is False
    assert result.physical_action_issue_authorized is False
    assert paper.stop_count == 1
    assert bridge.quiescence_checks == 2
    assert len(verify_typed_generation(result.generation)) == 2
    assert (result.generation / "COMMITTED.json").exists()
    assert not (result.generation / "WORLD_ONLY_COMMITTED.json").exists()
    dest = tmp_path / "new-branch"
    restore_generation(result.generation, dest, restore_id="28b-restore")
    plan = stage28_inert_cognitive_recovery(
        result.generation, dest,
        expected_self_ids=("A", "B"), expected_source_world_id="world-1",
    )
    assert plan.roster == ("A", "B")
    assert plan.l1_reevaluation_eligible is False


def test_stage28b_rejects_missing_b_before_paper_stop(tmp_path, monkeypatch):
    bridge, paper, store, evidence = _setup(tmp_path, monkeypatch)
    del bridge.owners["B"]
    with pytest.raises(stage28b.Stage28bRetiredCutHold, match="exact A/B"):
        stage28b.capture_retired_resident_typed_world(
            bridge=bridge, paper=paper, store=store, evidence_dir=evidence,
        )
    assert paper.stop_count == 0
    assert not list(store.iterdir())


def test_stage28b_late_native_rejoin_held_before_paper_stop(tmp_path, monkeypatch):
    bridge, paper, store, evidence = _setup(tmp_path, monkeypatch)
    bridge.dirty_after_first = True
    with pytest.raises(stage28b.Stage28bRetiredCutHold, match="late native"):
        stage28b.capture_retired_resident_typed_world(
            bridge=bridge, paper=paper, store=store, evidence_dir=evidence,
        )
    assert paper.stop_count == 0
    assert not list(store.iterdir())


def test_stage28b_future_cognition_tick_blocks_typed_commit(tmp_path, monkeypatch):
    bridge, paper, store, evidence = _setup(tmp_path, monkeypatch)
    bridge.owners["B"].last_observed_tick = 120
    with pytest.raises(stage28b.Stage28bRetiredCutHold, match="stopped Paper tick"):
        stage28b.capture_retired_resident_typed_world(
            bridge=bridge, paper=paper, store=store, evidence_dir=evidence,
        )
    assert paper.stop_count == 1
    assert not list(store.glob("g-*/COMMITTED.json"))


def test_stage28b_tampered_original_cognition_refused_before_stop(
    tmp_path, monkeypatch,
):
    bridge, paper, store, evidence = _setup(tmp_path, monkeypatch)
    bridge.owners["A"].files.cognition_file.write_bytes(b"not persisted cognition")
    with pytest.raises(Exception):
        stage28b.capture_retired_resident_typed_world(
            bridge=bridge, paper=paper, store=store, evidence_dir=evidence,
        )
    assert paper.stop_count == 0
    assert not list(store.iterdir())


def test_single_b_cpu_preset_survives_typed_cut_and_builds_stage26_l1(tmp_path, monkeypatch):
    """Synthetic lifecycle fixture. No Paper, native process, or model is called."""
    bridge, paper, store, evidence = _setup(tmp_path, monkeypatch, roster=("B",))
    initial = bridge.owners["B"]
    config = SchemaBootstrapConfig(exploration_enabled=True, destination_move=True)
    owner = create_fresh_owner(
        config=config, retained=initial.retained, intent=initial.intent,
        native_session_id=initial.native_session_id, last_observed_tick=105,
        files=initial.files, physical_supervisor=initial.supervisor,
    )
    bridge.owners["B"] = owner
    resident = ResidentCognitiveWorkOwner(bridge.owners)
    bridge.cognitive_work = resident
    bootstrap_fresh_schemas(resident, config)
    resident.bind_login(self_id="B", native_session_id="native-original", world_epoch=0,
                        world_tick=6000)
    paper.logical_tick = 6005

    definition = next(d for d in initial_skill_definitions() if d.skill_id == "MOVE")
    first = probe(10, native="native-fresh")
    for registry in (owner.pattern_registry, initial_patterns_with_relative_move()):
        with pytest.raises(Stage26L1Refusal, match="fully bound accepted MOVE"):
            build_stage26_move_round(
                self_id="B", registry=registry, first=first,
                definition=definition, intent=IntentCommitment(),
            )
    preset = SkillParameterPreset(
        "exploration-move", "Walk", 1, definition.definition_ref,
        SkillConstraints(), SkillBudget(1, 1500, 2.0, 4),
        Provenance("test-fixture", "proposed"),
    )
    with pytest.raises(ResidentCognitiveWorkError, match="policy declined"):
        resident.decide_initial_move_preset(preset)
    body = probe(5, native="native-original", request_id="login-B")
    owner.accept_rejoined_worldbody(body, request_id="login-B")
    with pytest.raises(ResidentCognitiveWorkError, match="policy declined"):
        resident.decide_initial_move_preset(replace(preset, budget=SkillBudget(2, 1500, 2.0, 4)))
    receipt = resident.decide_initial_move_preset(preset)
    assert receipt.provenance == Provenance(
        "original-b-initial-move-policy-v1", body.provenance.reference,
    )
    with pytest.raises(ResidentCognitiveWorkError, match="policy declined"):
        resident.decide_initial_move_preset(preset)
    resident.fence_self("B")
    retired = asyncio.run(resident.retire_self("B"))
    save_persistent_cognition(owner.files.cognition_file, owner.retained)
    resident.mark_offline(retired)

    result = stage28b.capture_retired_resident_typed_world(
        bridge=bridge, paper=paper, store=store, evidence_dir=evidence,
        expected_self_ids=("B",),
    )
    (cut,) = verify_typed_generation(result.generation)
    assert cut.self_id == "B"
    assert cut.pattern_registry.accepted_presets[0].receipt == receipt
    assert cut.schema_snapshot.revision == cut.pattern_registry.revision
    dest = tmp_path / "restored-b"
    restore_generation(result.generation, dest, restore_id="single-b-restore")
    plan = stage28_inert_cognitive_recovery(
        result.generation, dest,
        expected_self_ids=("B",), expected_source_world_id="world-1",
    )
    assert not plan.candidates[0].issue_authorized
    round_, target = build_stage26_move_round(
        self_id="B", registry=plan.candidates[0].semantic.pattern_registry, first=first,
        definition=definition, intent=IntentCommitment(),
    )
    option, = round_.frame.options
    assert tuple(n for n, _ in round_.numbered) == ("1", "2", "3")
    assert option.invocation.parameter_preset_ref == preset.preset_ref
    assert option.invocation.target.contract == target.arrival_contract
    assert option.invocation.budget == preset.budget
    assert option.invocation.target.kind == "DESTINATION"
