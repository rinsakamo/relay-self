"""Versioned JSON codec for a *recorded* original Owner SchemaSnapshot.

The digest in a typed committed generation binds these bytes to the saved
owner; it does NOT prove a model selected the Schema or grant physical actions.
"""
from __future__ import annotations

from relay_self.innate_schema import (
    SchemaActivation,
    SchemaDependency,
    SchemaMode,
    SchemaModuleSpec,
    SchemaSnapshot,
)
from relay_self.provenance import Provenance


class RecordedSchemaHold(ValueError):
    """Unknown, forged or out-of-scope saved activation."""


def _exact(value, keys: set[str]):
    if type(value) is not dict or set(value) != keys:
        raise RecordedSchemaHold("invalid exact original Schema fields")
    return value


def encode_recorded_schema(snapshot: SchemaSnapshot) -> dict:
    """No computed defaults: encode only an already registered typed snapshot."""
    if type(snapshot) is not SchemaSnapshot:
        raise RecordedSchemaHold("original registered typed Schema required")
    return {
        "self_id": snapshot.self_id,
        "revision": snapshot.revision,
        "modules": [
            {
                "schema_id": a.spec.schema_id, "version": a.spec.version,
                "mode": a.mode.value,
                "supported_modes": sorted(x.value for x in a.spec.supported_modes),
                "signal_kinds": list(a.spec.signal_kinds),
                "dependencies": [
                    {"schema_id": d.schema_id, "minimum_mode": d.minimum_mode.value}
                    for d in a.spec.dependencies
                ],
                "provenance": {
                    "source": a.spec.provenance.source,
                    "reference": a.spec.provenance.reference,
                },
            }
            for a in snapshot.modules
        ],
    }


def decode_recorded_schema(raw, *, expected_self_id: str,
                           expected_registry_revision: int) -> SchemaSnapshot:
    """No migration: only already persisted exact versions may be recovered."""
    try:
        data = _exact(raw, {"self_id", "revision", "modules"})
        if (type(data["self_id"]) is not str
                or data["self_id"] != expected_self_id
                or type(data["revision"]) is not int
                or data["revision"] != expected_registry_revision
                or type(data["modules"]) is not list
                or len(data["modules"]) > 8):
            raise RecordedSchemaHold("foreign or stale recorded Schema")
        modules = []
        for item in data["modules"]:
            x = _exact(item, {"schema_id", "version", "mode", "supported_modes",
                              "signal_kinds", "dependencies", "provenance"})
            if (type(x["supported_modes"]) is not list
                    or type(x["signal_kinds"]) is not list
                    or type(x["dependencies"]) is not list
                    or len(x["dependencies"]) > 8):
                raise RecordedSchemaHold("unbounded recorded Schema activation")
            modes = tuple(SchemaMode(m) for m in x["supported_modes"])
            if len(set(modes)) != len(modes):
                raise RecordedSchemaHold("duplicate supported mode")
            provenance = _exact(x["provenance"], {"source", "reference"})
            spec = SchemaModuleSpec(
                x["schema_id"], x["version"], frozenset(modes),
                tuple(x["signal_kinds"]),
                tuple(SchemaDependency(
                    _exact(d, {"schema_id", "minimum_mode"})["schema_id"],
                    SchemaMode(d["minimum_mode"]),
                ) for d in x["dependencies"]),
                Provenance(provenance["source"], provenance["reference"]),
            )
            modules.append(SchemaActivation(spec, SchemaMode(x["mode"])))
        result = SchemaSnapshot(data["self_id"], data["revision"], tuple(modules))
        if encode_recorded_schema(result) != raw:
            raise RecordedSchemaHold("noncanonical recorded Schema encoding")
        return result
    except (ValueError, TypeError, KeyError, AttributeError) as exc:
        if isinstance(exc, RecordedSchemaHold):
            raise
        raise RecordedSchemaHold("invalid recorded original Schema") from exc
