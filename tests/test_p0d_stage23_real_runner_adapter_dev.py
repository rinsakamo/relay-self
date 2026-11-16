"""#904: real-runner adapter call shape, frozen evidence, no real Paper."""
from __future__ import annotations

import asyncio
from pathlib import Path

import pytest

from experiments.p0d_real_resident_presence_dev import (
    RealResidentPresenceRefusal,
    _immutable_cognition,
    _immutable_receipt,
    _issue_original_selected_b_move,
)
from relay_self.action_supervision import ActionSupervisor
from relay_self.checkpointed_cognitive_runtime_dev import (
    CheckpointedCognitiveOwner,
    CognitiveOwnerFiles,
)
from relay_self.cognitive_minimal_dev import initial_patterns
from relay_self.intent import IntentCommitment
from relay_self.persistent_cognition import (
    IdentitySpecification,
    PersistentCognition,
)
from relay_self.physical_action_journal import PhysicalActionJournal
from relay_self.physical_issue_admission_dev import PhysicalIssueAdmission
from relay_self.provenance import Provenance
from relay_self.resident_cognitive_work_owner_dev import ResidentCognitiveWorkOwner
from relay_self.world_resident_lifecycle_dev import LogoutFenceEvidence
from test_p0d_resident_move_issuer_dev import ScriptedNative


def test_real_audit_directory_accepts_concrete_path_before_action(tmp_path):
    class CaptureSentinel(Exception):
        pass

    class Session:
        def start_raw_source_audit(self, path):
            assert path == tmp_path / "B-original-move-native-source.jsonl"
            raise CaptureSentinel

    async def invoke(directory):
        await _issue_original_selected_b_move(
            session=Session(), owner=None, physical=None,
            pulse_seconds=0.35, evidence_dir=directory,
        )

    with pytest.raises(CaptureSentinel):
        asyncio.run(invoke(tmp_path))
    with pytest.raises(RealResidentPresenceRefusal):
        asyncio.run(invoke(tmp_path / "missing"))


def test_stage23_real_runner_selected_move_reuses_exact_original_b_owners(tmp_path):
    root = tmp_path / "original-B"
    root.mkdir()
    wal = root / "physical.json"
    PhysicalActionJournal.create(wal, self_id="B")
    owner = CheckpointedCognitiveOwner(
        retained=PersistentCognition(
            IdentitySpecification(
                "B", ("Identity of independently resident Self",),
                Provenance("source-test", "B"),
            )
        ),
        intent=IntentCommitment(), pattern_registry=initial_patterns(),
        native_session_id="native-B", last_observed_tick=100,
        files=CognitiveOwnerFiles(root, root / "cognition.json", wal),
        physical_supervisor=ActionSupervisor(),
    )
    work = ResidentCognitiveWorkOwner({"B": owner})
    work.bind_login(
        self_id="B", native_session_id="native-B",
        world_epoch=0, world_tick=100,
    )
    gate = PhysicalIssueAdmission(
        {"B": "native-B"}, resident_mode=True,
        allow_resident_move=True,
    )
    native = ScriptedNative("native-B")
    native.gate = lambda sid, effect, action_id: gate.require_native_effect(
        self_id="B", native_session_id=sid,
        effect=effect, action_id=action_id,
    )

    async def scenario():
        receipt = await _issue_original_selected_b_move(
            session=native, owner=owner, physical=gate,
            pulse_seconds=0.15,
        )
        assert receipt["classification"] == "DEV_ORIGINAL_B_NATIVE_MOVE_SETTLED"
        assert receipt["original_action_id"].startswith("p0d-b-move-action-")
        assert receipt["original_canonical_wal_sha256"] == PhysicalActionJournal.restore(
            wal, self_id="B",
        ).digest
        assert receipt["native_net_displacement_m"] >= 0.8
        assert not receipt["autonomous_l1_skill_selection"]
        assert not receipt["skill_success_attested"]
        assert not receipt["paper_action_causation"]
        assert len(owner.supervisor.recorded_actions) == 1
        assert not owner.supervisor.open_actions
        assert not PhysicalActionJournal.restore(wal, self_id="B").unresolved

    asyncio.run(scenario())


def test_immutable_first_logout_and_final_receipts_retained_individually(tmp_path):
    source = tmp_path / "original-cognition.json"
    source.write_bytes(b'{"version":"first-A-logout"}\n')
    snap = _immutable_cognition(tmp_path, "A-first-cognition", source)
    assert Path(snap["path"]).read_bytes() == b'{"version":"first-A-logout"}\n'
    source.write_bytes(b'{"version":"final-A-logout"}\n')
    assert Path(snap["path"]).read_bytes() != source.read_bytes()
    with pytest.raises(FileExistsError):
        _immutable_cognition(tmp_path, "A-first-cognition", source)

    proof = LogoutFenceEvidence(
        self_id="A", world_epoch=0, native_session_id="native-A",
        source_ref="original-issuer-wal-digest",
        persisted_cognition_ref="cognition-file:/tmp/cognition",
        physical_issuer_revoked=True, no_physical_inflight=True,
        physical_wal_clear=True, native_terminated=True,
        stale_gpu_fenced=True, peer_transport_drained=True,
    )
    r = _immutable_receipt(tmp_path, "A-final-receipt", proof)
    assert Path(r["path"]).is_file()
    assert "original-issuer-wal-digest" in Path(r["path"]).read_text()
    with pytest.raises(FileExistsError):
        _immutable_receipt(tmp_path, "A-final-receipt", proof)
