"""Offline original Owner/Resident schema bootstrap, no login substitution."""
from dataclasses import replace

import pytest

from relay_self.action_supervision import ActionSupervisor
from relay_self.checkpointed_cognitive_runtime_dev import CognitiveOwnerFiles
from relay_self.cognitive_minimal_dev import initial_patterns, initial_patterns_with_relative_move
from relay_self.innate_schema import SchemaMode
from relay_self.intent import IntentCommitment
from relay_self.persistent_cognition import IdentitySpecification, PersistentCognition
from relay_self.physical_action_journal import PhysicalActionJournal
from relay_self.provenance import Provenance
from relay_self.resident_cognitive_work_owner_dev import (
    ResidentCognitiveWorkError,
    ResidentCognitiveWorkOwner,
)
from relay_self.schema_bootstrap_dev import (
    SchemaBootstrapConfig,
    SchemaBootstrapHold,
    bootstrap_fresh_schemas,
    bootstrap_restored_schemas,
    create_fresh_owner,
    fresh_pattern_registry,
)


def make_resident(tmp_path, registry, config=None):
    owners = {}
    for sid in ("A", "B"):
        root = tmp_path / sid
        root.mkdir()
        wal = root / "physical-wal.json"
        PhysicalActionJournal.create(wal, self_id=sid)
        owners[sid] = create_fresh_owner(
            config=config or SchemaBootstrapConfig(registry == initial_patterns_with_relative_move()),
            retained=PersistentCognition(IdentitySpecification(sid, ("identity",), Provenance("test", sid))),
            intent=IntentCommitment(),
            native_session_id="offline-" + sid, last_observed_tick=0,
            files=CognitiveOwnerFiles(root, root / "cognition.json", wal),
            physical_supervisor=ActionSupervisor(),
        )
    return ResidentCognitiveWorkOwner(owners)


@pytest.mark.parametrize("enabled", [True, False])
def test_fresh_original_owners_before_login_and_no_mutation(tmp_path, enabled):
    config = SchemaBootstrapConfig(enabled)
    resident = make_resident(tmp_path, fresh_pattern_registry(config))
    before = {sid: (o.pattern_registry, o.retained, o.intent, dict(o.skills),
                    set(o.pending_questions), o.files.physical_wal_file.read_bytes())
              for sid, o in resident.owners.items()}
    bootstrap_fresh_schemas(resident, config)
    snapshots = [resident._present_schemas[sid][0] for sid in ("A", "B")]
    assert snapshots[0] is not snapshots[1]
    for sid, snapshot in zip(("A", "B"), snapshots):
        assert resident._states[sid].epoch == 0
        assert snapshot.self_id == sid
        assert snapshot.revision == resident.owners[sid].pattern_registry.revision
        assert snapshot.get("exploratory").mode is (SchemaMode.FULL if enabled else SchemaMode.OFF)
        resident.bind_login(self_id=sid, native_session_id="new-" + sid, world_epoch=1, world_tick=0)
        assert resident.present_schema(sid) == snapshot
    assert all((o.pattern_registry, o.retained, o.intent, o.skills, o.pending_questions,
                o.files.physical_wal_file.read_bytes()) == before[sid]
               for sid, o in resident.owners.items())


def test_registration_rejects_foreign_stale_duplicate_and_registry_change(tmp_path):
    resident = make_resident(tmp_path, initial_patterns_with_relative_move())
    config = SchemaBootstrapConfig(True)
    bootstrap_fresh_schemas(resident, config)
    a, b = (resident._present_schemas[sid][0] for sid in ("A", "B"))
    with pytest.raises(ResidentCognitiveWorkError):
        resident.register_present_schema("A", b)
    with pytest.raises(SchemaBootstrapHold):
        bootstrap_fresh_schemas(resident, config)
    del resident._present_schemas["A"]
    with pytest.raises(ResidentCognitiveWorkError):
        resident.register_present_schema("A", b)
    with pytest.raises(ResidentCognitiveWorkError):
        resident.register_present_schema("A", replace(a, revision=2))
    resident.register_present_schema("A", a)
    resident.bind_login(self_id="A", native_session_id="new-A", world_epoch=1, world_tick=0)
    resident.owners["A"].pattern_registry = replace(resident.owners["A"].pattern_registry, revision=2)
    with pytest.raises(ResidentCognitiveWorkError):
        resident.present_schema("A")


@pytest.mark.parametrize("registry", [initial_patterns(), initial_patterns_with_relative_move()])
@pytest.mark.parametrize("enabled", [True, False])
def test_restored_activation_absent_holds_without_registry_or_file_changes(tmp_path, registry, enabled):
    resident = make_resident(tmp_path, registry)
    before = {sid: (o.pattern_registry, o.files.physical_wal_file.read_bytes())
              for sid, o in resident.owners.items()}
    with pytest.raises(SchemaBootstrapHold, match="not recorded"):
        bootstrap_restored_schemas(resident, SchemaBootstrapConfig(enabled))
    assert not resident._present_schemas
    assert all((o.pattern_registry, o.files.physical_wal_file.read_bytes()) == before[sid]
               for sid, o in resident.owners.items())


def test_fresh_mismatch_holds_before_any_registration(tmp_path):
    resident = make_resident(tmp_path, initial_patterns())
    with pytest.raises(SchemaBootstrapHold):
        bootstrap_fresh_schemas(resident, SchemaBootstrapConfig(True))
    assert not resident._present_schemas


def test_actual_checkpoint_recovery_holds_before_login_without_modification(tmp_path, monkeypatch):
    from relay_self.stage28c2_recovered_resident_owner_dev import Stage28c2OwnerHold
    from test_stage28c2_recovered_resident_owner_dev import _context, _reattach

    generation, restored, prepared = _context(tmp_path, monkeypatch)
    before = {p.relative_to(restored): p.read_bytes() for p in restored.rglob("*") if p.is_file()}
    recovered = _reattach(generation, restored, prepared)
    registries = {sid: owner.pattern_registry for sid, owner in recovered.owners.items()}
    with pytest.raises(SchemaBootstrapHold):
        bootstrap_fresh_schemas(recovered.cognitive_work, SchemaBootstrapConfig(False))
    with pytest.raises(SchemaBootstrapHold, match="not recorded"):
        bootstrap_restored_schemas(recovered.cognitive_work, SchemaBootstrapConfig(True))
    assert registries == {sid: owner.pattern_registry for sid, owner in recovered.owners.items()}
    with pytest.raises(Stage28c2OwnerHold, match="not recorded"):
        _reattach(generation, restored, prepared, schema_bootstrap=SchemaBootstrapConfig(True))
    assert before == {p.relative_to(restored): p.read_bytes() for p in restored.rglob("*") if p.is_file()}


def test_pattern_presence_does_not_enable_schema_and_forged_pattern_rejected(tmp_path):
    resident = make_resident(tmp_path, initial_patterns_with_relative_move())
    bootstrap_fresh_schemas(resident, SchemaBootstrapConfig(True))
    snapshot = resident._present_schemas.pop("A")[0]
    off = replace(snapshot, modules=(replace(snapshot.modules[0], mode=SchemaMode.OFF),))
    resident.register_present_schema("A", off)
    assert resident._present_schemas["A"][0].get("exploratory").mode is SchemaMode.OFF
    del resident._present_schemas["A"]
    owner = resident.owners["A"]
    pattern = owner.pattern_registry.patterns[-1]
    owner.pattern_registry = replace(owner.pattern_registry, patterns=(
        *owner.pattern_registry.patterns[:-1], replace(pattern, goal_id="FORGED"),
    ))
    with pytest.raises(ResidentCognitiveWorkError, match="mapping"):
        resident.register_present_schema("A", snapshot)
