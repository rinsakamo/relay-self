"""I2c: original registered Schema -> new typed cut -> pinned A/B restore.

Offline synthetic World/cognition fixtures only. Older actual I1/Stage28b
evidence remains unmodified, with no inferred exploratory FULL activation.
"""
from __future__ import annotations

import asyncio
import json
from dataclasses import replace

import pytest

from relay_self.cognitive_minimal_dev import initial_patterns_with_relative_move
from relay_self.i_lane_i2c_original_schema_restore_dev import (
    I2cRestoredSchemaHold,
    bootstrap_original_recorded_a_b_schemas,
)
from relay_self.i_lane_i2c_recorded_schema_dev import (
    RecordedSchemaHold,
    decode_recorded_schema,
    encode_recorded_schema,
)
from relay_self.innate_schema import (
    SchemaActivation,
    SchemaMode,
    SchemaModuleSpec,
    SchemaSnapshot,
)
from relay_self.persistent_cognition import save_persistent_cognition
from relay_self.provenance import Provenance
from relay_self.resident_cognitive_work_owner_dev import (
    ResidentCognitiveWorkError,
    ResidentCognitiveWorkOwner,
)
from relay_self.self_owner_checkpoint_dev import load_self_owner_cut
from relay_self.stage28b_retired_resident_typed_cut_dev import capture_retired_resident_typed_world
from test_stage28b_retired_typed_cut_dev import _setup
from test_stage28c1_inert_restore_dev import _prepare
from test_stage28c2_recovered_resident_owner_dev import _reattach


def _snapshot(sid, revision):
    module = SchemaModuleSpec(
        "exploratory", 1, frozenset({SchemaMode.FULL}),
        ("QUESTION_CANDIDATE", "EXPLORATION_NEED"), (),
        Provenance("innate-schema", "recorded-original-config"),
    )
    return SchemaSnapshot(sid, revision, (SchemaActivation(module, SchemaMode.FULL),))


def _new_cut(tmp_path, monkeypatch, *, registered=("A", "B"), retire=True):
    bridge, paper, store, evidence = _setup(tmp_path, monkeypatch)
    for name in ("world_nether", "world_the_end"):
        target = tmp_path / name
        target.mkdir()
        (target / "region").mkdir()
        (target / "region" / "r.0.0.mca").write_bytes(b"synthetic-dimension")
    for sid in registered:
        owner = bridge.owners[sid]
        owner.pattern_registry = initial_patterns_with_relative_move()
        owner.retained = replace(owner.retained, pattern_registry=owner.pattern_registry)
        save_persistent_cognition(owner.files.cognition_file, owner.retained)
    resident = ResidentCognitiveWorkOwner(bridge.owners)
    bridge.cognitive_work = resident
    for sid in ("A", "B"):
        if sid in registered:
            resident.register_present_schema(
                sid, _snapshot(sid, bridge.owners[sid].pattern_registry.revision),
            )
        resident.bind_login(
            self_id=sid, native_session_id=bridge.owners[sid].native_session_id,
            world_epoch=0, world_tick=105,
        )
    if retire:
        for sid in ("A", "B"):
            resident.fence_self(sid)
            retired = asyncio.run(resident.retire_self(sid))
            resident.mark_offline(retired)
    return bridge, paper, store, evidence


def _restored(tmp_path, monkeypatch, *, registered=("A", "B")):
    bridge, paper, store, evidence = _new_cut(
        tmp_path, monkeypatch, registered=registered,
    )
    generation = capture_retired_resident_typed_world(
        bridge=bridge, paper=paper, store=store, evidence_dir=evidence,
    ).generation
    dest = tmp_path / "recorded-restored"
    prepared = _prepare(generation, dest)
    recovered = _reattach(generation, dest, prepared, observation_only=True)
    return generation, dest, recovered


def test_i2c_exact_original_full_schema_survives_generation_and_inert_restore(
    tmp_path, monkeypatch,
):
    generation, dest, recovered = _restored(tmp_path, monkeypatch)
    before = {
        (sid, filename): (dest / "selves" / sid / filename).read_bytes()
        for sid in ("A", "B")
        for filename in ("cognition.json", "owner-state.json", "physical-wal.json")
    }
    for sid in ("A", "B"):
        raw = json.loads((generation / "selves" / sid / "owner-state.json").read_bytes())
        assert raw["payload"]["schema"] == 3
        cut = load_self_owner_cut(generation / "selves" / sid / "owner-state.json")
        assert cut.recorded_schema == _snapshot(sid, 1)
        assert cut.cognition_sha256 is not None
        assert cut.pattern_registry == recovered.owners[sid].pattern_registry
    receipt = bootstrap_original_recorded_a_b_schemas(
        recovered=recovered, generation=generation, restored_directory=dest,
    )
    assert receipt.restored_self_ids == ("A", "B")
    assert receipt.generation_id == generation.name
    assert len(receipt.recorded_schema_by_self) == 2
    assert not receipt.live_native_bound and not receipt.model_invoked
    assert not receipt.goal_adopted and not receipt.question_adopted
    assert not receipt.schema_invented and not receipt.physical_action_authorized
    assert recovered.physical.active_action_ids == ()
    assert recovered.physical.all_residents_offline
    for sid in ("A", "B"):
        assert recovered.cognitive_work._present_schemas[sid][0] == _snapshot(sid, 1)
        assert recovered.owners[sid].fresh_native_observation_required
        for filename in ("cognition.json", "owner-state.json", "physical-wal.json"):
            assert (dest / "selves" / sid / filename).read_bytes() == before[sid, filename]
    with pytest.raises(I2cRestoredSchemaHold):
        bootstrap_original_recorded_a_b_schemas(
            recovered=recovered, generation=generation, restored_directory=dest,
        )


@pytest.mark.parametrize("registered", [(), ("A",), ("B",)])
def test_i2c_legacy_or_partial_activation_never_inferred(
    tmp_path, monkeypatch, registered,
):
    generation, dest, recovered = _restored(
        tmp_path, monkeypatch, registered=registered,
    )
    with pytest.raises(I2cRestoredSchemaHold):
        bootstrap_original_recorded_a_b_schemas(
            recovered=recovered, generation=generation, restored_directory=dest,
        )
    assert recovered.cognitive_work._present_schemas == {}
    for sid in ("A", "B"):
        raw = json.loads((generation / "selves" / sid / "owner-state.json").read_bytes())
        assert (raw["payload"]["schema"] == 3) == (sid in registered)


def test_i2c_cpu_retirement_required_before_schema_cut(tmp_path, monkeypatch):
    bridge, paper, store, evidence = _new_cut(
        tmp_path, monkeypatch, retire=False,
    )
    with pytest.raises(RuntimeError):
        capture_retired_resident_typed_world(
            bridge=bridge, paper=paper, store=store, evidence_dir=evidence,
        )
    assert paper.stop_count == 0
    assert not list(store.glob("g-*/COMMITTED.json"))


@pytest.mark.parametrize("fault", [
    "source-commit", "changed-a-owner", "changed-b-cognition",
    "changed-b-wal", "registry-drift", "already-registered",
    "not-offline", "wrong-generation",
])
def test_i2c_restore_rejects_lost_same_generation_or_owner_authority(
    tmp_path, monkeypatch, fault,
):
    generation, dest, recovered = _restored(tmp_path, monkeypatch)
    if fault == "source-commit":
        recovered.receipt = replace(
            recovered.receipt, source_committed_sha256="0" * 64,
        )
    elif fault in ("changed-a-owner", "changed-b-cognition", "changed-b-wal"):
        sid, filename = {
            "changed-a-owner": ("A", "owner-state.json"),
            "changed-b-cognition": ("B", "cognition.json"),
            "changed-b-wal": ("B", "physical-wal.json"),
        }[fault]
        (dest / "selves" / sid / filename).write_bytes(b"tampered")
    elif fault == "registry-drift":
        owner = recovered.owners["A"]
        owner.pattern_registry = replace(
            owner.pattern_registry, revision=owner.pattern_registry.revision + 1,
        )
    elif fault == "already-registered":
        recovered.cognitive_work.register_present_schema("A", _snapshot("A", 1))
    elif fault == "not-offline":
        recovered.cognitive_work._states["B"].epoch = 1
    else:
        generation = dest  # not the original generation
    with pytest.raises(I2cRestoredSchemaHold):
        bootstrap_original_recorded_a_b_schemas(
            recovered=recovered, generation=generation, restored_directory=dest,
        )
    if fault != "already-registered":
        assert recovered.cognitive_work._present_schemas == {}
    assert recovered.physical.active_action_ids == ()


@pytest.mark.parametrize("fault", [
    "foreign-self", "revision", "field", "module-version",
    "mode", "duplicate-modes", "provenance",
])
def test_i2c_recorded_schema_codec_refuses_noncanonical_and_foreign(
    fault,
):
    raw = encode_recorded_schema(_snapshot("A", 1))
    if fault == "foreign-self":
        raw["self_id"] = "B"
    elif fault == "revision":
        raw["revision"] = 9
    elif fault == "field":
        raw["extra"] = "false-evidence"
    elif fault == "module-version":
        raw["modules"][0]["version"] = 0
    elif fault == "mode":
        raw["modules"][0]["mode"] = "INVALID"
    elif fault == "duplicate-modes":
        raw["modules"][0]["supported_modes"] = ["FULL", "FULL"]
    else:
        raw["modules"][0]["provenance"] = {"source": "synthetic"}
    with pytest.raises(RecordedSchemaHold):
        decode_recorded_schema(
            raw, expected_self_id="A", expected_registry_revision=1,
        )


def test_i2c_second_self_schema_rejection_rolls_back_first_before_join(
    tmp_path, monkeypatch,
):
    generation, dest, recovered = _restored(tmp_path, monkeypatch)
    original = ResidentCognitiveWorkOwner.register_present_schema

    def reject_b(resident, self_id, snapshot):
        if self_id == "B":
            raise ResidentCognitiveWorkError("synthetic B owner rejected")
        return original(resident, self_id, snapshot)

    monkeypatch.setattr(
        ResidentCognitiveWorkOwner, "register_present_schema", reject_b,
    )
    with pytest.raises(I2cRestoredSchemaHold):
        bootstrap_original_recorded_a_b_schemas(
            recovered=recovered, generation=generation, restored_directory=dest,
        )
    assert recovered.cognitive_work._present_schemas == {}
    assert recovered.physical.all_residents_offline
    assert recovered.physical.active_action_ids == ()
