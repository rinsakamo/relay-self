"""Original Owner Schema 3 checkpoint and same-generation A/B restore.

Every fixture is synthetic. A checksum is not an external source signature.
"""
from __future__ import annotations

import asyncio
import hashlib
import json
from dataclasses import replace

import pytest

from relay_self.cognitive_minimal_dev import (
    initial_patterns,
    initial_patterns_with_relative_move,
)
from relay_self.coordinated_checkpoint_dev import CoordinatedCheckpointError
from relay_self.exploration_schema_record_dev import (
    RecordedSchemaHold,
    canonical_exploration_snapshot,
    decode_recorded_schema,
    encode_recorded_schema,
)
from relay_self.innate_schema import SchemaMode
from relay_self.persistent_cognition import save_persistent_cognition
from relay_self.resident_cognitive_work_owner_dev import ResidentCognitiveWorkOwner
from relay_self.schema_bootstrap_dev import SchemaBootstrapConfig
from relay_self.self_owner_checkpoint_dev import (
    SelfOwnerCheckpointError,
    SelfOwnerCut,
    load_self_owner_cut,
    save_self_owner_cut,
    verify_typed_generation,
)
from relay_self.stage28b_retired_resident_typed_cut_dev import (
    Stage28bRetiredCutHold,
    capture_retired_resident_typed_world,
)
from relay_self.stage28c2_recovered_resident_owner_dev import (
    Stage28c2OwnerHold,
    prepare_recovered_a_b_resident_owners,
)
from test_stage28b_retired_typed_cut_dev import _setup
from test_stage28c1_inert_restore_dev import _prepare


def _v3_cut(*, sid="A", mode=SchemaMode.FULL):
    registry = initial_patterns_with_relative_move()
    snapshot = canonical_exploration_snapshot(
        self_id=sid, registry=registry, mode=mode,
    )
    return SelfOwnerCut(
        generation_id="g-000000000000", self_id=sid,
        world_id="world-1", branch_id="source",
        former_native_session_id="retired-" + sid,
        last_observed_world_tick=105,
        intent_events=(), skill_executions=(), pattern_registry=registry,
        cognition_sha256="a" * 64, schema_snapshot=snapshot,
    )


@pytest.mark.parametrize("mode", [SchemaMode.FULL, SchemaMode.OFF])
def test_schema3_canonical_owner_record_roundtrips_without_authority(
    tmp_path, mode,
):
    cut = _v3_cut(mode=mode)
    path = tmp_path / "owner-state.json"
    save_self_owner_cut(path, cut)
    root = json.loads(path.read_bytes())
    assert root["payload"]["schema"] == 3
    assert root["payload"]["exploration_schema"]["mode"] == mode.value
    assert root["payload"]["cognition_sha256"] == "a" * 64
    assert load_self_owner_cut(path) == cut


@pytest.mark.parametrize("alter", [
    "foreign-self", "revision", "mode-fast", "mode-unknown",
    "version", "provenance", "missing", "extra", "bool-version",
])
def test_schema3_tampered_payload_rejected_after_inner_sha_resign(
    tmp_path, alter,
):
    cut = _v3_cut()
    path = tmp_path / "owner-state.json"
    save_self_owner_cut(path, cut)
    envelope = json.loads(path.read_bytes())
    value = envelope["payload"]["exploration_schema"]
    if alter == "foreign-self":
        value["self_id"] = "B"
    elif alter == "revision":
        value["registry_revision"] = 99
    elif alter == "mode-fast":
        value["mode"] = "FAST"
    elif alter == "mode-unknown":
        value["mode"] = "INFERRED"
    elif alter == "version":
        value["module_version"] = 2
    elif alter == "provenance":
        value["module_provenance"]["reference"] = "changed-after-cut"
    elif alter == "missing":
        value.pop("mode")
    elif alter == "extra":
        value["new_rights"] = True
    else:
        value["module_version"] = True
    from relay_self.self_owner_checkpoint_dev import _bytes

    envelope["sha256"] = hashlib.sha256(_bytes(envelope["payload"])).hexdigest()
    path.write_bytes(_bytes(envelope))
    with pytest.raises((SelfOwnerCheckpointError, RecordedSchemaHold)):
        load_self_owner_cut(path)


def test_schema3_cannot_upgrade_unregistered_pattern():
    cut = _v3_cut()
    empty = initial_patterns()
    with pytest.raises(RecordedSchemaHold):
        canonical = canonical_exploration_snapshot(
            self_id="A", registry=empty, mode=SchemaMode.FULL,
        )
        encode_recorded_schema(canonical, self_id="A", registry=empty)
    value = encode_recorded_schema(cut.schema_snapshot, self_id="A",
                                   registry=cut.pattern_registry)
    with pytest.raises(RecordedSchemaHold):
        decode_recorded_schema(value, self_id="B", registry=cut.pattern_registry)
    with pytest.raises(SelfOwnerCheckpointError):
        replace(cut, schema_snapshot=canonical_exploration_snapshot(
            self_id="B", registry=cut.pattern_registry, mode=SchemaMode.FULL,
        ))


def _retired_v3_source(tmp_path, monkeypatch, *, mode=SchemaMode.FULL):
    bridge, paper, store, evidence = _setup(tmp_path, monkeypatch)
    for name in ("world_nether", "world_the_end"):
        dim = tmp_path / name
        dim.mkdir()
        (dim / "region").mkdir()
        (dim / "region" / "r.0.0.mca").write_bytes(b"source")
    # A/B are ORIGINAL resident owners. Their trusted fresh creation must
    # already have placed exact registry state in retained cognition BEFORE cut.
    for owner in bridge.owners.values():
        registry = initial_patterns_with_relative_move()
        owner.pattern_registry = registry
        owner.retained = replace(owner.retained, pattern_registry=registry)
        save_persistent_cognition(owner.files.cognition_file, owner.retained)
    resident = ResidentCognitiveWorkOwner(bridge.owners)
    bridge.cognitive_work = resident
    for sid in ("A", "B"):
        snapshot = canonical_exploration_snapshot(
            self_id=sid, registry=resident.owners[sid].pattern_registry,
            mode=mode,
        )
        resident.register_present_schema(sid, snapshot)
        resident.bind_login(
            self_id=sid, native_session_id="native-retired-" + sid,
            world_epoch=0, world_tick=105,
        )
        resident.fence_self(sid)
        receipt = asyncio.run(resident.retire_self(sid))
        resident.mark_offline(receipt)
        assert resident.retired_clean(sid)
    return bridge, paper, store, evidence


def _generation(tmp_path, monkeypatch, *, mode=SchemaMode.FULL):
    bridge, paper, store, evidence = _retired_v3_source(tmp_path, monkeypatch, mode=mode)
    generation = capture_retired_resident_typed_world(
        bridge=bridge, paper=paper, store=store, evidence_dir=evidence,
    ).generation
    return generation, bridge, paper


def _recover(generation, destination, *, enabled=None):
    prepared = _prepare(generation, destination)
    return prepare_recovered_a_b_resident_owners(
        generation, destination, expected_world_id="world-1",
        expected_source_branch_id="source",
        expected_committed_sha256=prepared.source_commit_sha256,
        expected_fork_branch_id=prepared.restored_branch_id,
        observation_only=True,
        **({} if enabled is None else {
            "schema_bootstrap": SchemaBootstrapConfig(enabled),
        }),
    )


def test_original_retired_a_b_schema3_typed_generation_inert_restore(
    tmp_path, monkeypatch,
):
    generation, bridge, paper = _generation(tmp_path, monkeypatch)
    cuts = verify_typed_generation(generation)
    assert paper.stop_count == 1
    assert all(c.schema_snapshot is not None for c in cuts)
    assert all(c.cognition_sha256 is not None for c in cuts)
    assert all(c.schema_snapshot.get("exploratory").mode is SchemaMode.FULL for c in cuts)
    for sid in ("A", "B"):
        cut = next(c for c in cuts if c.self_id == sid)
        assert cut.pattern_registry == bridge.owners[sid].pattern_registry
    restored = tmp_path / "recovered"
    result = _recover(generation, restored, enabled=True)
    assert result.physical.all_residents_offline
    assert result.physical.observation_only
    assert set(result.cognitive_work._present_schemas) == {"A", "B"}
    for sid in ("A", "B"):
        state = result.cognitive_work._state(sid)
        saved = next(c.schema_snapshot for c in cuts if c.self_id == sid)
        assert result.cognitive_work._present_schemas[sid][0] == saved
        assert state.mode == "OFFLINE" and state.epoch == 0
        assert result.owners[sid].fresh_native_observation_required
        assert result.owners[sid].retained == bridge.owners[sid].retained
        assert not result.owners[sid].supervisor.open_actions
    assert result.receipt.l1_reevaluation_eligible is False


def test_recorded_source_auto_restore_without_new_enable_flag(
    tmp_path, monkeypatch,
):
    generation, _, _ = _generation(tmp_path, monkeypatch)
    result = _recover(generation, tmp_path / "auto")
    assert set(result.cognitive_work._present_schemas) == {"A", "B"}
    assert all(result.cognitive_work._present_schemas[sid][0]
               .get("exploratory").mode is SchemaMode.FULL for sid in ("A", "B"))


def test_request_cannot_switch_original_saved_activation(
    tmp_path, monkeypatch,
):
    generation, _, _ = _generation(tmp_path, monkeypatch)
    with pytest.raises(Stage28c2OwnerHold, match="activation differs"):
        _recover(generation, tmp_path / "wrong-mode", enabled=False)


@pytest.mark.parametrize("failure", [
    "partial", "registry-change", "missing-persisted-registry",
])
def test_retired_schema_cut_refuses_forged_or_partial_original(
    tmp_path, monkeypatch, failure,
):
    bridge, paper, store, evidence = _retired_v3_source(tmp_path, monkeypatch)
    if failure == "partial":
        bridge.cognitive_work._present_schemas.pop("B")
    elif failure == "registry-change":
        bridge.owners["B"].pattern_registry = replace(
            bridge.owners["B"].pattern_registry, revision=2,
        )
    else:
        owner = bridge.owners["A"]
        owner.retained = replace(owner.retained, pattern_registry=None)
        save_persistent_cognition(owner.files.cognition_file, owner.retained)
    with pytest.raises(Stage28bRetiredCutHold):
        capture_retired_resident_typed_world(
            bridge=bridge, paper=paper, store=store, evidence_dir=evidence,
        )
    assert paper.stop_count == 0
    assert not list(store.glob("g-*/COMMITTED.json"))

def test_explicit_off_remains_off_after_source_recorded_restore(
    tmp_path, monkeypatch,
):
    generation, _, _ = _generation(tmp_path, monkeypatch, mode=SchemaMode.OFF)
    result = _recover(generation, tmp_path / "off-source", enabled=False)
    assert all(
        result.cognitive_work._present_schemas[sid][0]
        .get("exploratory").mode is SchemaMode.OFF
        for sid in ("A", "B")
    )
    with pytest.raises(Stage28c2OwnerHold, match="activation differs"):
        _recover(generation, tmp_path / "off-upgrade-denied", enabled=True)


def _resign_owner_only(path, *, mode="OFF"):
    from relay_self.self_owner_checkpoint_dev import _bytes

    envelope = json.loads(path.read_bytes())
    envelope["payload"]["exploration_schema"]["mode"] = mode
    envelope["sha256"] = hashlib.sha256(_bytes(envelope["payload"])).hexdigest()
    path.write_bytes(_bytes(envelope))


def test_resigned_original_owner_activation_fails_committed_generation(
    tmp_path, monkeypatch,
):
    generation, _, _ = _generation(tmp_path, monkeypatch)
    original = generation / "selves" / "A" / "owner-state.json"
    _resign_owner_only(original)
    # Inner JSON integrity is valid, but original COMMITTED generation byte
    # manifest is not: retagging after the cut cannot change past activation.
    assert load_self_owner_cut(original).schema_snapshot.get("exploratory").mode is SchemaMode.OFF
    with pytest.raises(CoordinatedCheckpointError):
        verify_typed_generation(generation)


def test_restored_copy_resigned_inner_owner_rejected_against_original(
    tmp_path, monkeypatch,
):
    generation, _, _ = _generation(tmp_path, monkeypatch)
    destination = tmp_path / "forged-restored"
    prepared = _prepare(generation, destination)
    _resign_owner_only(destination / "selves" / "B" / "owner-state.json")
    with pytest.raises(Stage28c2OwnerHold):
        prepare_recovered_a_b_resident_owners(
            generation, destination, expected_world_id="world-1",
            expected_source_branch_id="source",
            expected_committed_sha256=prepared.source_commit_sha256,
            expected_fork_branch_id=prepared.restored_branch_id,
            observation_only=True,
        )
