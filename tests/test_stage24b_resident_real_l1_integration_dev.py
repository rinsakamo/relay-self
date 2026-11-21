"""Stage24b real wiring contract exercised with SYNTHETIC model/native fixtures.

These tests never call a real GPU, Paper, llama.cpp or Minecraft. The production
path requires an actual ResidentLlamaInferenceLane and original issuer.
"""
from __future__ import annotations

import asyncio
import json
from pathlib import Path
from types import SimpleNamespace

import pytest

from adapters.llama_cpp.relay_engine import LlamaCppRelayProvider
from adapters.mineflayer.python_protocol import (
    MINEFLAYER_NEARBY_ENTITY_MAX_DISTANCE,
    MINEFLAYER_NEARBY_ENTITY_MAX_ENTITIES,
    MINEFLAYER_NEARBY_ENTITY_SOURCE_SCOPE,
    MineflayerNearbyEntitiesCoverage,
    MineflayerObservation,
    MineflayerPosition,
    MineflayerSnapshot,
    MineflayerTime,
)
from experiments.stage24b_real_l1_move_dev import (
    Stage24bMoveRefusal,
    Stage24bNoAction,
    require_frozen_stage24b_binding,
    require_frozen_stage24b_choice,
    run_stage24b_selected_b_move,
)
from relay_self.action_supervision import ActionSupervisor
from relay_self.checkpointed_cognitive_runtime_dev import (
    CheckpointedCognitiveOwner,
    CognitiveOwnerFiles,
)
from relay_self.cognitive_minimal_dev import initial_patterns
from relay_self.intent import IntentCommitment
from relay_self.persistent_cognition import IdentitySpecification, PersistentCognition
from relay_self.physical_action_journal import PhysicalActionJournal
from relay_self.physical_issue_admission_dev import PhysicalIssueAdmission
from relay_self.provenance import Provenance
from relay_self.relay_engine import CognitionMode, ProviderDecision
from relay_self.resident_cognitive_work_owner_dev import ResidentCognitiveWorkOwner
from relay_self.resident_llama_inference_lane_dev import (
    LlamaCppSingleSlotWitness,
    ResidentLlamaInferenceLane,
)
from test_p0d_resident_move_issuer_dev import ScriptedNative


def _probe(seq, *, food=20, native="native-B"):
    return MineflayerObservation(
        native, seq, "probe",
        MineflayerSnapshot(
            health=20, food=food, food_saturation=5, oxygen_level=20,
            position=MineflayerPosition(1.0, 64.0, 2.0),
            time=MineflayerTime(100 + seq, 0, True),
            inventory=(), nearby_entities=(),
            nearby_entities_coverage=MineflayerNearbyEntitiesCoverage(
                MINEFLAYER_NEARBY_ENTITY_SOURCE_SCOPE,
                MINEFLAYER_NEARBY_ENTITY_MAX_DISTANCE,
                MINEFLAYER_NEARBY_ENTITY_MAX_ENTITIES, 0, False,
            ),
        ),
        f"stage24b-native-probe-{seq}",
    )


def _owned(tmp_path, monkeypatch, *, answer="4", food_after=20):
    root = tmp_path / "B"
    root.mkdir()
    wal = root / "physical-wal.json"
    PhysicalActionJournal.create(wal, self_id="B")
    owner = CheckpointedCognitiveOwner(
        retained=PersistentCognition(
            IdentitySpecification(
                "B", ("Cognitive Self owns this MOVE",),
                Provenance("test-identity", "B"),
            ),
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
        {"B": "native-B"}, resident_mode=True, allow_resident_move=True,
    )
    native = ScriptedNative("native-B")

    # Synthetic source capture exists to exercise the DEV handoff only.
    def capture(path):
        Path(path).open("xb").close()

    monkeypatch.setattr(native, "start_raw_source_audit", capture)
    monkeypatch.setattr(native, "finish_raw_source_audit", lambda: None)
    provider = LlamaCppRelayProvider(
        endpoint="http://127.0.0.1:8080/v1/chat/completions",
        systemone_endpoint="http://127.0.0.1:8080/v1/systemone",
        model="synthetic-test-only",
    )
    witness = LlamaCppSingleSlotWitness(provider=provider, backend_ref="synthetic")
    lane = ResidentLlamaInferenceLane(
        provider=provider, cognitive_work=work, witness=witness,
    )
    requests = []

    def submit(self, self_id, *, work_ref, request, mode):
        assert self_id == "B" and mode is CognitionMode.BOUNDED
        requests.append(request)
        return SimpleNamespace(
            self_id="B", work_ref=work_ref, self_epoch=1, world_epoch=0,
            backend_ref="synthetic", mode=mode, request_id=request.request_id,
        )

    async def await_result(self, ticket, *, timeout_s=60.0):
        return ProviderDecision.resolved(answer)

    monkeypatch.setattr(ResidentLlamaInferenceLane, "submit", submit)
    monkeypatch.setattr(ResidentLlamaInferenceLane, "await_result", await_result)
    rows = [_probe(10), _probe(11), _probe(12, food=food_after)]

    async def read_probe(session):
        assert session is native
        return rows.pop(0)

    return owner, gate, native, lane, read_probe, requests, wal


def _run(tmp_path, monkeypatch, *, answer="4", food_after=20):
    owner, gate, native, lane, probe, requests, wal = _owned(
        tmp_path, monkeypatch, answer=answer, food_after=food_after,
    )
    return owner, gate, native, lane, probe, requests, wal


def test_actual_numbered_choice_only_reaches_original_issue_port(monkeypatch, tmp_path):
    owner, gate, native, lane, read_probe, requests, wal = _run(tmp_path, monkeypatch)
    calls = []

    class CapturedBeforeNative(Exception):
        pass

    async def original_issue(self, session, **kwargs):
        calls.append(kwargs)
        assert session is native
        assert kwargs["proposal"].binding.goal_id == "EXPLORE_WORLD"
        assert kwargs["proposal"].binding.target_ref == "relative:right"
        assert kwargs["proposal"].state == "PROPOSED_NOT_AUTHORIZED"
        assert kwargs["pulse_seconds"] == 0.35
        assert kwargs["previous_probe"].seq == 11
        assert kwargs["current_probe"].seq == 12
        assert kwargs["proposal"].binding.native_request_id == (
            "stage24b-native-probe-12"
        )
        assert not PhysicalActionJournal.restore(wal, self_id="B").records
        raise CapturedBeforeNative

    monkeypatch.setattr(PhysicalIssueAdmission, "issue_move", original_issue)
    with pytest.raises(CapturedBeforeNative):
        asyncio.run(run_stage24b_selected_b_move(
            session=native, owner=owner, physical=gate, lane=lane,
            evidence_dir=tmp_path, read_probe=read_probe,
            real_world_granted=True, real_llm_granted=True,
        ))
    assert len(calls) == 1 and len(requests) == 1
    assert len(requests[0].choices) == 6
    assert owner.intent.current_intent.objective == "EXPLORE_WORLD"
    assert requests[0].think_allowed is False
    source = tmp_path / "B-original-systemone-choice.json"
    data = json.loads(source.read_text())
    assert data["actual_model_choice_id"] == "4"
    assert data["selected_target_ref"] == "relative:right"
    assert data["selected_pulse_seconds"] == 0.35
    assert data["actual_original_action_issued"] is False
    assert data["physical_action_authorized_by_model"] is False
    binding = json.loads(
        (tmp_path / "B-stage24b-preissue-binding.json").read_text()
    )
    assert len(binding["actual_model_choice_sha256"]) == 64
    assert binding["physical_binding"]["target_ref"] == "relative:right"
    assert binding["physical_binding"]["intent_id"] == owner.intent.current_intent.intent_id
    assert binding["physical_authorized"] is False
    assert binding["physical_issued"] is False


@pytest.mark.parametrize("answer", ["5", "6", "999"])
def test_model_nonphysical_choice_cannot_issue(monkeypatch, tmp_path, answer):
    owner, gate, native, lane, read_probe, requests, wal = _run(
        tmp_path, monkeypatch, answer=answer,
    )

    async def unexpected_issue(self, session, **kwargs):
        raise AssertionError("a declined/out-of-set L1 choice must not issue")

    monkeypatch.setattr(PhysicalIssueAdmission, "issue_move", unexpected_issue)
    with pytest.raises(Stage24bNoAction):
        asyncio.run(run_stage24b_selected_b_move(
            session=native, owner=owner, physical=gate, lane=lane,
            evidence_dir=tmp_path, read_probe=read_probe,
            real_world_granted=True, real_llm_granted=True,
        ))
    assert owner.intent.current_intent is None
    assert not PhysicalActionJournal.restore(wal, self_id="B").records
    recorded = json.loads((tmp_path / "B-original-systemone-choice.json").read_text())
    assert recorded["actual_model_choice_id"] == answer
    assert recorded["selected_status"] != "READY"


def test_changed_body_after_model_choice_reaches_original_issuer(monkeypatch, tmp_path):
    owner, gate, native, lane, read_probe, requests, wal = _run(
        tmp_path, monkeypatch, answer="1", food_after=11,
    )
    calls = []

    class IssuerIntercepted(Exception):
        pass

    async def original_issue(self, session, **kwargs):
        assert session is native
        calls.append(kwargs)
        assert kwargs["current_probe"].snapshot.food == 11
        assert kwargs["proposal"].binding.goal_id == "EXPLORE_WORLD"
        assert kwargs["proposal"].state == "PROPOSED_NOT_AUTHORIZED"
        # No actual issue: capture right at the original physical owner.
        raise IssuerIntercepted

    monkeypatch.setattr(PhysicalIssueAdmission, "issue_move", original_issue)
    with pytest.raises(IssuerIntercepted):
        asyncio.run(run_stage24b_selected_b_move(
            session=native, owner=owner, physical=gate, lane=lane,
            evidence_dir=tmp_path, read_probe=read_probe,
            real_world_granted=True, real_llm_granted=True,
        ))
    assert len(calls) == 1
    assert owner.intent.current_intent.objective == "EXPLORE_WORLD"
    assert not PhysicalActionJournal.restore(wal, self_id="B").records


def test_l1_selected_move_can_have_terminal_no_net_outcome_without_fake_success(
    monkeypatch, tmp_path,
):
    owner, gate, native, lane, read_probe, requests, wal = _run(
        tmp_path, monkeypatch, answer="1",
    )
    native.gate = lambda session, effect, action: gate.require_native_effect(
        self_id="B", native_session_id=session, effect=effect,
        action_id=action,
    )
    # Fixture's last original model-binding probe is native seq=12.
    # The original scripted emitter normally begins at 2, so synchronize
    # the synthetic stream without altering production source validation.
    native.seq = 12
    original_send = native.send_set_control

    async def real_command_but_no_net_motion(action_id, *, control, state):
        await original_send(action_id, control=control, state=state)
        native.x -= 0.8

    monkeypatch.setattr(native, "send_set_control", real_command_but_no_net_motion)

    def independently_read_back_stub(*, receipt, **kwargs):
        # Only exercises Stage24b's already-verified control-flow branch.
        # Actual raw/WAL independent verification is tested separately by
        # test_p0d_stage23_raw_source_audit_dev.py.
        return {
            "classification": "OWNED_NATIVE_MOVE_RAW_SOURCE_READBACK_DEV",
            "original_wal_terminal_status": (
                "NATIVE_MOVE_NO_NET_DISPLACEMENT"
            ),
            "all_stop_probes": [
                {"seq": x.seq} for x in receipt.all_stop_probes
            ],
            "native_start_ack": {"seq": receipt.start_ack.seq},
            "native_stop_ack": {"seq": receipt.stop_ack.seq},
        }

    monkeypatch.setattr(
        "experiments.stage24b_real_l1_move_dev.readback_owned_move_native_source",
        independently_read_back_stub,
    )
    result = asyncio.run(run_stage24b_selected_b_move(
        session=native, owner=owner, physical=gate, lane=lane,
        evidence_dir=tmp_path, read_probe=read_probe,
        real_world_granted=True, real_llm_granted=True,
    ))
    assert result["classification"] == (
        "DEV_ORIGINAL_B_NATIVE_MOVE_NO_NET_DISPLACEMENT"
    )
    assert result["original_wal_terminal_status"] == (
        "NATIVE_MOVE_NO_NET_DISPLACEMENT"
    )
    assert result["native_net_displacement_m"] == 0.0
    assert result["native_start_dispatch_monotonic_ns"] >= result[
        "intent_commit_monotonic_ns"
    ]
    assert result["intent_to_native_start_dispatch_ns"] >= 0
    assert result["autonomous_l1_skill_selection"] is True
    assert result["skill_success_attested"] is False
    assert result["paper_action_causation"] is False
    readback = PhysicalActionJournal.restore(wal, self_id="B")
    assert not readback.unresolved
    assert readback.records[-1]["status"] == (
        "NATIVE_MOVE_NO_NET_DISPLACEMENT"
    )
    assert len(requests) == 1
    choice = json.loads((tmp_path / "B-original-systemone-choice.json").read_text())
    assert choice["actual_model_choice_id"] == "1"
    assert choice["selected_skill_id"] == "MOVE"
    assert choice["physical_action_authorized_by_model"] is False


def test_grant_missing_refuses_without_model_or_probe(monkeypatch, tmp_path):
    owner, gate, native, lane, read_probe, requests, wal = _run(tmp_path, monkeypatch)
    with pytest.raises(Stage24bMoveRefusal):
        asyncio.run(run_stage24b_selected_b_move(
            session=native, owner=owner, physical=gate, lane=lane,
            evidence_dir=tmp_path, read_probe=read_probe,
            real_world_granted=False, real_llm_granted=True,
        ))
    assert not requests
    assert not (tmp_path / "B-original-move-native-source.jsonl").exists()


def test_frozen_choice_source_digest_and_target_cannot_be_changed(tmp_path):
    file = tmp_path / "choice.json"
    body = {
        "classification": "STAGE24B_ACTUAL_L1_CHOICE_SOURCE_DEV",
        "self_id": "B", "mode": "bounded",
        "actual_model_status": "resolved", "actual_model_choice_id": "4",
        "selected_status": "READY", "selected_target_ref": "relative:right",
        "selected_goal_id": "EXPLORE_WORLD", "selected_skill_id": "MOVE",
        "selected_pulse_seconds": 0.35,
        "actual_original_action_issued": False,
        "model_raw_http_bytes_archived": False,
        "physical_action_authorized_by_model": False,
        "candidates_sha256": "a" * 64,
        "request_choices": [
            {"id": "4", "description": "MOVE(relative:right) pulse=0.35s"},
        ],
    }
    file.write_text(json.dumps(body))
    from experiments.p0d_real_paper_smoke_dev import file_sha256

    original = file_sha256(file)
    assert require_frozen_stage24b_choice(
        file, original, original_action_id="a", intent_id="i",
        skill_execution_id="r", target_ref="relative:right",
        model_choice_id="4",
    ) == body
    file.write_text(json.dumps({**body, "selected_target_ref": "relative:left"}))
    with pytest.raises(Stage24bMoveRefusal):
        require_frozen_stage24b_choice(
            file, original, original_action_id="a", intent_id="i",
            skill_execution_id="r", target_ref="relative:right",
            model_choice_id="4",
        )


def test_frozen_preissue_binding_detects_tampered_original_lineage(tmp_path):
    from experiments.p0d_real_paper_smoke_dev import file_sha256

    path = tmp_path / "B-stage24b-preissue-binding.json"
    row = {
        "classification": "STAGE24B_PREISSUE_L1_OPTION_BINDING_DEV",
        "actual_model_choice_sha256": "f" * 64,
        "selected_number": "3",
        "physical_authorized": False,
        "physical_issued": False,
        "physical_binding": {
            "action_id": "action-1",
            "intent_id": "intent-1",
            "skill_execution_id": "skill-run-1",
            "target_ref": "relative:left",
            "native_seq": 12,
            "native_request_id": "probe-12",
            "goal_id": "EXPLORE_WORLD",
            "skill_id": "MOVE",
            "skill_version": 1,
            "target_kind": "RELATIVE",
            "capability_ref": "MOVE",
        },
    }
    path.write_text(json.dumps(row))
    kwargs = {
        "model_choice_sha256": "f" * 64,
        "action_id": "action-1", "intent_id": "intent-1",
        "skill_execution_id": "skill-run-1",
        "target_ref": "relative:left", "chosen_number": "3",
        "native_probe_seq": 12, "native_request_id": "probe-12",
    }
    sha = file_sha256(path)
    assert require_frozen_stage24b_binding(path, sha, **kwargs) == row
    with pytest.raises(Stage24bMoveRefusal, match="diverged"):
        require_frozen_stage24b_binding(
            path, sha, **{**kwargs, "target_ref": "relative:right"},
        )
    path.write_text(json.dumps({**row, "selected_number": "4"}))
    with pytest.raises(Stage24bMoveRefusal, match="digest changed"):
        require_frozen_stage24b_binding(path, sha, **kwargs)
