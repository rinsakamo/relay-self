"""Stage28b synthetic original owner + one stopped Paper typed cut; no Minecraft."""
from __future__ import annotations

from types import SimpleNamespace

import pytest

from relay_self import stage28b_retired_resident_typed_cut_dev as stage28b
from relay_self.action_supervision import ActionSupervisor
from relay_self.checkpointed_cognitive_runtime_dev import (
    CheckpointedCognitiveOwner,
    CognitiveOwnerFiles,
)
from relay_self.cognitive_minimal_dev import initial_patterns
from relay_self.coordinated_autosave_runtime_dev import StoppedWorldReceipt
from relay_self.coordinated_checkpoint_dev import restore_generation
from relay_self.intent import IntentCommitment
from relay_self.persistent_cognition import (
    IdentitySpecification,
    PersistentCognition,
    save_persistent_cognition,
)
from relay_self.physical_action_journal import PhysicalActionJournal
from relay_self.provenance import Provenance
from relay_self.self_owner_checkpoint_dev import verify_typed_generation
from relay_self.stage28_cognitive_recovery_gate_dev import (
    stage28_inert_cognitive_recovery,
)
from relay_self.world_resident_lifecycle_dev import (
    WorldLifetime,
    WorldOnlyQuiescenceEvidence,
)


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
            self_roster=("A", "B"),
        )
        self.quiescence_checks = 0
        self.dirty_after_first = False

    def world_only_quiescence(self):
        self.quiescence_checks += 1
        if self.dirty_after_first and self.quiescence_checks > 1:
            raise stage28b.Stage28bRetiredCutHold("late native rejoin/lease")
        return WorldOnlyQuiescenceEvidence(
            0, ("A", "B"), "original-retirement-world0",
            True, True, True, True, True,
        )


def _setup(tmp_path, monkeypatch):
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
    for sid in ("A", "B"):
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
