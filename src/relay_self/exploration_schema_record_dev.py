"""Canonical opt-in exploration Schema snapshot contract for typed Owner cuts.

The Snapshot is an *existing original Resident registration*, not an inference
side flag or a restoration-time grant. Only the current exploratory v1 module
is supported. Typed generation integrity protects this record's bytes, NOT
external authorship or a true timeline before a physical event.
"""
from __future__ import annotations

from relay_self.cognitive_minimal_dev import (
    PatternRegistry,
    initial_move_pattern,
    initial_patterns_with_relative_move,
)
from relay_self.innate_schema import (
    SchemaActivation,
    SchemaMode,
    SchemaModuleSpec,
    SchemaSnapshot,
)
from relay_self.provenance import Provenance


class RecordedSchemaHold(ValueError):
    """Foreign, changed, or unsupported original Schema activation."""


def canonical_exploration_snapshot(*, self_id: str, registry: PatternRegistry,
                                   mode: SchemaMode) -> SchemaSnapshot:
    if (type(self_id) is not str or not self_id
            or type(registry) is not PatternRegistry
            or mode not in (SchemaMode.FULL, SchemaMode.OFF)):
        raise RecordedSchemaHold("typed original Self/registry/exploration mode required")
    spec = SchemaModuleSpec(
        "exploratory", 1, frozenset({SchemaMode.FULL}),
        ("QUESTION_CANDIDATE", "EXPLORATION_NEED"), (),
        Provenance("innate-schema", "cognitive-v0.1-exploration-dev"),
    )
    return SchemaSnapshot(
        self_id, registry.revision, (SchemaActivation(spec, mode),),
    )


def require_recorded_schema(snapshot: SchemaSnapshot, *, self_id: str,
                            registry: PatternRegistry) -> SchemaSnapshot:
    """Require an exact canonical registration, not registry-inferred FULL."""
    if type(snapshot) is not SchemaSnapshot or snapshot.self_id != self_id:
        raise RecordedSchemaHold("original Schema snapshot Self mismatch")
    module = snapshot.get("exploratory")
    if module is None or module.mode not in (SchemaMode.FULL, SchemaMode.OFF):
        raise RecordedSchemaHold("exploration module not recorded as FULL/OFF")
    expected = canonical_exploration_snapshot(
        self_id=self_id, registry=registry, mode=module.mode,
    )
    if snapshot != expected:
        raise RecordedSchemaHold("noncanonical or stale exploration activation")
    if module.mode is SchemaMode.FULL:
        expected_pattern = initial_patterns_with_relative_move().patterns[-1]
        matching = [p for p in registry.patterns if p.schema_id == "exploration"]
        allowed = ([expected_pattern], [initial_move_pattern()]) if self_id == "B" else ([expected_pattern],)
        if matching not in allowed:
            raise RecordedSchemaHold("exploration activation lacks exact original pattern")
    return snapshot


def encode_recorded_schema(snapshot: SchemaSnapshot, *, self_id: str,
                           registry: PatternRegistry) -> dict[str, object]:
    require_recorded_schema(snapshot, self_id=self_id, registry=registry)
    activation = snapshot.get("exploratory")
    assert activation is not None
    return {
        "self_id": self_id,
        "registry_revision": snapshot.revision,
        "schema_id": "exploratory",
        "module_version": 1,
        "module_provenance": {
            "source": "innate-schema", "reference": "cognitive-v0.1-exploration-dev",
        },
        "mode": activation.mode.value,
    }


def decode_recorded_schema(value: object, *, self_id: str,
                           registry: PatternRegistry) -> SchemaSnapshot:
    if type(value) is not dict or set(value) != {
        "self_id", "registry_revision", "schema_id", "module_version",
        "module_provenance", "mode",
    }:
        raise RecordedSchemaHold("Schema activation record has noncanonical fields")
    if (value["self_id"] != self_id
            or type(value["registry_revision"]) is not int
            or value["registry_revision"] != registry.revision
            or value["schema_id"] != "exploratory"
            or type(value["module_version"]) is not int
            or value["module_version"] != 1
            or value["module_provenance"] != {
                "source": "innate-schema",
                "reference": "cognitive-v0.1-exploration-dev",
            }
            or type(value["mode"]) is not str
            or value["mode"] not in ("FULL", "OFF")):
        raise RecordedSchemaHold("Schema activation source or version mismatch")
    return require_recorded_schema(
        canonical_exploration_snapshot(
            self_id=self_id, registry=registry, mode=SchemaMode(value["mode"]),
        ), self_id=self_id, registry=registry,
    )
