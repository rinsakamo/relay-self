import json

import pytest

import relay_self
from relay_self.persistent_cognition import (
    DuplicateMemoryIdentity,
    IdentitySpecification,
    InvalidPersistentCognitionData,
    Memory,
    PersistentCognition,
    PersistentCognitionLoadError,
    UnsupportedPersistentCognitionVersion,
    load_persistent_cognition,
    save_persistent_cognition,
)
from relay_self.provenance import Provenance


def _identity() -> IdentitySpecification:
    return IdentitySpecification(
        self_id="self-rin-001",
        directives=(
            "Preserve continued agency.",
            "Learn from lived consequences.",
        ),
        provenance=Provenance(source="mvp-fixture", reference="identity-v1"),
    )


def _memory() -> Memory:
    return Memory(
        memory_id="memory-safe-place-001",
        content="The stone shelter was observed to block the earlier threat.",
        source_provenance=Provenance(
            source="minecraft.consequence",
            reference="episode-001:shelter-observation",
        ),
        integration_provenance=Provenance(
            source="experience-integration",
            reference="episode-001:accepted-memory",
        ),
    )


def test_package_exports_minimum_persistent_cognition_types() -> None:
    assert relay_self.IdentitySpecification is IdentitySpecification
    assert relay_self.Memory is Memory
    assert relay_self.PersistentCognition is PersistentCognition


def test_retain_memory_is_explicit_and_preserves_source_and_integration_provenance() -> None:
    cognition = PersistentCognition(identity=_identity())

    updated = cognition.retain_memory(_memory())

    assert cognition.memories == ()
    assert len(updated.memories) == 1
    retained = updated.memories[0]
    assert retained.source_provenance.source == "minecraft.consequence"
    assert retained.integration_provenance.source == "experience-integration"


def test_duplicate_memory_identity_fails_without_mutating_existing_snapshot() -> None:
    cognition = PersistentCognition(identity=_identity()).retain_memory(_memory())

    with pytest.raises(DuplicateMemoryIdentity, match="memory-safe-place-001"):
        cognition.retain_memory(_memory())

    assert len(cognition.memories) == 1


def test_persistent_cognition_round_trips_across_a_fresh_load(tmp_path) -> None:
    path = tmp_path / "self.json"
    original = PersistentCognition(identity=_identity()).retain_memory(_memory())

    save_persistent_cognition(path, original)
    restored = load_persistent_cognition(path)

    assert restored == original
    assert restored is not original
    assert restored.identity.self_id == "self-rin-001"
    assert restored.memories[0].content.startswith("The stone shelter")
    assert restored.memories[0].source_provenance.source == "minecraft.consequence"


def test_unsupported_schema_version_fails_closed(tmp_path) -> None:
    path = tmp_path / "self.json"
    cognition = PersistentCognition(identity=_identity())
    save_persistent_cognition(path, cognition)

    payload = json.loads(path.read_text(encoding="utf-8"))
    payload["schema_version"] = 999
    path.write_text(json.dumps(payload), encoding="utf-8")

    with pytest.raises(UnsupportedPersistentCognitionVersion, match="999"):
        load_persistent_cognition(path)


def test_unknown_persistent_fields_fail_closed_instead_of_becoming_cognition(tmp_path) -> None:
    path = tmp_path / "self.json"
    cognition = PersistentCognition(identity=_identity())
    save_persistent_cognition(path, cognition)

    payload = json.loads(path.read_text(encoding="utf-8"))
    payload["identity"]["current_world_truth"] = {"night": False}
    path.write_text(json.dumps(payload), encoding="utf-8")

    with pytest.raises(InvalidPersistentCognitionData, match="identity"):
        load_persistent_cognition(path)


def test_missing_or_corrupt_snapshot_fails_explicitly(tmp_path) -> None:
    missing = tmp_path / "missing.json"
    with pytest.raises(PersistentCognitionLoadError, match="read"):
        load_persistent_cognition(missing)

    corrupt = tmp_path / "corrupt.json"
    corrupt.write_text("{not-json", encoding="utf-8")
    with pytest.raises(PersistentCognitionLoadError, match="JSON"):
        load_persistent_cognition(corrupt)
