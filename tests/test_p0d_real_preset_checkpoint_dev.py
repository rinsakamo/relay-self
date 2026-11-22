"""Stage25 REAL harness strict preflight + recovered-source negative controls.

No Paper, Java, Node, live Mineflayer or Gemma in GitHub CI.
"""
from __future__ import annotations

import asyncio
import json
from dataclasses import replace
from pathlib import Path

import pytest

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
from experiments.p0d_real_preset_checkpoint_dev import (
    RealPresetCheckpointRefusal,
    _readback_native_probe_source,
    run_real_two_self_preset_checkpoint,
)
from relay_self.checkpointed_cognitive_runtime_dev import StagedRecoveredCognition
from relay_self.cognitive_minimal_dev import (
    PresetAcceptanceReceipt,
    accept_skill_parameter_preset,
    initial_patterns_with_move,
)
from relay_self.initial_skill_ir import initial_skill_definitions
from relay_self.p0d_real_preset_reselect_dev import (
    RestoredPresetRealProbeRefusal,
    reselect_restored_move_preset,
)
from relay_self.persistent_cognition import IdentitySpecification, PersistentCognition
from relay_self.provenance import Provenance
from relay_self.self_owner_checkpoint_dev import (
    SelfOwnerCut,
    rehydrate_self_owner,
)
from relay_self.skill_invocation import (
    SkillBudget,
    SkillConstraints,
    SkillParameterPreset,
)


def source_recovered(
    self_id="A", *, accepted=True, budget=None, preset_id="OperatorNearProbe",
):
    definition = next(
        d for d in initial_skill_definitions() if d.skill_id == "MOVE"
    )
    initial = initial_patterns_with_move()
    if accepted:
        preset = SkillParameterPreset(
            "exploration-move", preset_id, 1,
            definition.definition_ref, SkillConstraints(),
            budget if budget is not None else SkillBudget(1, 1500, 2.0, 4),
            Provenance("operator-dev-proposed", f"stage25:{self_id}"),
        )
        initial = accept_skill_parameter_preset(
            initial, preset, definition=definition,
            receipt=PresetAcceptanceReceipt(
                self_id, "accept-operator", preset.preset_ref,
                Provenance("self-owner", "typed-owner"),
            ),
            accepted_by_self=True, expected_revision=initial.revision,
            available_skills=frozenset({("MOVE", 1)}),
        )
    retained = PersistentCognition(
        IdentitySpecification(
            self_id, ("Protect source and provenance.",),
            Provenance("identity", self_id),
        ), pattern_registry=initial,
    )
    cut = SelfOwnerCut(
        "g-000000000001", self_id, "world-one", "source",
        f"old-native-{self_id}", 100, (), (), initial,
    )
    return StagedRecoveredCognition(
        self_id, retained, rehydrate_self_owner(cut),
        Path("/unused/WAL/never-read-by-CPU-helper"),
    )


def native_probe(
    self_id="A", seq=11, *, session=None, x=1.0,
    request_id=None,
):
    sid = session or f"new-native-{self_id}"
    return MineflayerObservation(
        sid, seq, "probe",
        MineflayerSnapshot(
            20, 20, 5, 20, MineflayerPosition(x, 64, 2),
            MineflayerTime(1200 + seq, 0, True),
            (), (),
            MineflayerNearbyEntitiesCoverage(
                MINEFLAYER_NEARBY_ENTITY_SOURCE_SCOPE,
                MINEFLAYER_NEARBY_ENTITY_MAX_DISTANCE,
                MINEFLAYER_NEARBY_ENTITY_MAX_ENTITIES, 0, False,
            ),
        ),
        request_id or f"probe-{seq}",
    )


@pytest.mark.parametrize("accepted_eula,dev_grant", [
    (False, False), (True, False), (False, True),
])
def test_real_paper_absent_explicit_flags_refuses_before_any_io(
    tmp_path, accepted_eula, dev_grant,
):
    missing = tmp_path / "must-not-create"
    with pytest.raises(RealPresetCheckpointRefusal, match="HOLD"):
        asyncio.run(run_real_two_self_preset_checkpoint(
            paper_jar=tmp_path / "bad-paper.jar", paper_sha256="0" * 64,
            plugin_jar=tmp_path / "bad-plugin.jar", plugin_sha256="0" * 64,
            scratch_parent=missing, accepted_eula=accepted_eula,
            real_world_dev_grant=dev_grant,
        ))
    assert not missing.exists()


@pytest.mark.parametrize("sid", ["A", "B"])
def test_two_distinct_original_self_presets_rebuild_from_new_native_probes(sid):
    restored = source_recovered(sid)
    first, later = native_probe(sid, 11), native_probe(sid, 12)
    proof = reselect_restored_move_preset(
        restored, first, later, source_self_id=sid,
        expected_native_session_id=f"new-native-{sid}",
    )
    assert proof.self_id == sid
    assert proof.new_native_session_id == f"new-native-{sid}"
    assert proof.old_native_session_id == f"old-native-{sid}"
    assert proof.choice_status == "READY"
    assert proof.l1_number == "1"
    assert proof.provider_kind == "SCRIPTED_NUMBER_ONLY_DEV_NOT_GEMMA"
    assert proof.preset_ref.startswith("skill-preset:v1@")
    assert proof.invocation_ref.startswith("skill-invocation:v1@")
    assert proof.target_contract_ref
    assert not proof.physical_action_issued
    assert not proof.native_action_granted
    assert not proof.old_intent_resumed
    assert not proof.old_target_reused


@pytest.mark.parametrize("mutation", [
    "unadopted", "old-native", "stale-seq", "foreign-self", "foreign-session",
    "repeat-request", "drifting-body", "unqualified-inert", "changed-retained",
])
def test_new_native_admission_fails_closed_on_source_or_owner_change(mutation):
    original = source_recovered()
    first, second = native_probe(), native_probe(seq=12)
    if mutation == "unadopted":
        original = source_recovered(accepted=False)
    elif mutation == "old-native":
        first = native_probe(session="old-native-A")
        second = native_probe(seq=12, session="old-native-A")
    elif mutation == "stale-seq":
        second = native_probe(seq=9)
    elif mutation == "foreign-self":
        original = source_recovered("B")
    elif mutation == "foreign-session":
        second = native_probe(seq=12, session="foreign-session")
    elif mutation == "repeat-request":
        second = native_probe(seq=12, request_id=first.request_id)
    elif mutation == "drifting-body":
        second = native_probe(seq=12, x=3.0)
    elif mutation == "unqualified-inert":
        original = replace(original, issue_authorized=True)
    else:
        original = replace(
            original, retained=replace(
                original.retained,
                pattern_registry=initial_patterns_with_move(),
            ),
        )
    with pytest.raises(RestoredPresetRealProbeRefusal):
        reselect_restored_move_preset(
            original, first, second, source_self_id="A",
            expected_native_session_id="new-native-A",
        )



def test_new_native_probe_file_must_replay_two_exact_sessions_sequences_and_requests(
    tmp_path: Path,
):
    source = tmp_path / "original-native.jsonl"
    native_rows = [
        {
            "type": "observation", "session_id": "new-A", "seq": i,
            "kind": "probe", "request_id": f"req-{i}",
            "snapshot": {"real_original_source_shape": True},
        } for i in (11, 12)
    ]
    source.write_text(
        "".join(json.dumps(x) + "\n" for x in native_rows),
        encoding="utf-8",
    )
    digest = _readback_native_probe_source(
        source, first_request="req-11", second_request="req-12",
        native_session="new-A", first_seq=11, second_seq=12,
    )
    assert len(digest) == 64
    with pytest.raises(RealPresetCheckpointRefusal, match="missing"):
        _readback_native_probe_source(
            source, first_request="req-11", second_request="wrong",
            native_session="new-A", first_seq=11, second_seq=12,
        )
    with pytest.raises(RealPresetCheckpointRefusal, match="missing"):
        _readback_native_probe_source(
            source, first_request="req-11", second_request="req-12",
            native_session="foreign-B", first_seq=11, second_seq=12,
        )
    with pytest.raises(RealPresetCheckpointRefusal, match="stale"):
        _readback_native_probe_source(
            source, first_request="req-11", second_request="req-11",
            native_session="new-A", first_seq=11, second_seq=12,
        )
    source.write_text(source.read_text() + json.dumps(native_rows[0]) + "\n")
    with pytest.raises(RealPresetCheckpointRefusal, match="duplicated"):
        _readback_native_probe_source(
            source, first_request="req-11", second_request="req-12",
            native_session="new-A", first_seq=11, second_seq=12,
        )


def test_live_choice_precedes_second_native_probe(monkeypatch):
    import relay_self.p0d_real_preset_reselect_dev as module

    original_engine = module.RelayEngine
    events = []

    def recording_engine(*args, **kwargs):
        engine = original_engine(*args, **kwargs)

        def choose(request):
            events.append("choice")
            return engine(request)
        return choose

    async def probe():
        events.append("probe")
        return native_probe(seq=12)

    monkeypatch.setattr(module, "RelayEngine", recording_engine)
    witness, _ = asyncio.run(module.reselect_restored_move_preset_live(
        source_recovered(), native_probe(), probe,
        source_self_id="A", expected_native_session_id="new-native-A",
    ))
    assert events == ["choice", "probe"]
    assert witness.choice_status == "READY"
