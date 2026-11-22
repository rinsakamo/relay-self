"""Strict durable codec for Self-owned Schema/Skill parameter hypotheses.

Only Pattern and accepted Preset knowledge is serializable here. No live
Invocation, L0 cursor, Intent/Skill run, WorldBody session or Action grant.
This codec is reusable inside the #860 typed SelfOwnerCut after stack merge.
"""
from __future__ import annotations

import hashlib
import json
from dataclasses import asdict
from typing import Any

from adapters.mineflayer.python_protocol import MineflayerPosition
from relay_self.cognitive_minimal_dev import (
    AcceptedSkillPreset,
    Origin,
    PatternKind,
    PatternRegistry,
    Predicate,
    PresetAcceptanceReceipt,
    SchemaPattern,
)
from relay_self.common_io import ScopeRef
from relay_self.provenance import Provenance
from relay_self.skill_invocation import (
    ArgumentKind,
    SkillArgument,
    SkillBudget,
    SkillConstraints,
    SkillCostEstimate,
    SkillParameterPreset,
    SkillTarget,
)
from relay_self.target_contract import (
    ArrivalCondition,
    ReferenceFrame,
    TargetContract,
    TargetKind,
)


class PresetCheckpointRefusal(ValueError):
    """Malformed, incomplete, wrong-Self or non-round-tripping registry cut."""


def _exact(value: object, fields: set[str], name: str) -> dict[str, Any]:
    if type(value) is not dict or set(value) != fields:
        raise PresetCheckpointRefusal(f"{name} requires exact fields")
    return value


def _array(value: object, name: str, limit: int = 64) -> list:
    if type(value) is not list or len(value) > limit:
        raise PresetCheckpointRefusal(f"{name} must be bounded JSON array")
    return value


def _prov(value: Provenance) -> dict[str, str]:
    return {"source": value.source, "reference": value.reference}


def _unprov(value: object) -> Provenance:
    obj = _exact(value, {"source", "reference"}, "provenance")
    return Provenance(obj["source"], obj["reference"])


def _position(value: MineflayerPosition | None) -> dict | None:
    return None if value is None else {
        "x": value.x, "y": value.y, "z": value.z,
    }


def _unposition(value: object) -> MineflayerPosition | None:
    if value is None:
        return None
    obj = _exact(value, {"x", "y", "z"}, "position")
    return MineflayerPosition(obj["x"], obj["y"], obj["z"])


def _contract(value: TargetContract | None) -> dict | None:
    if value is None:
        return None
    return {
        "scope": {"self_id": value.scope.self_id,
                  "world_session_id": value.scope.world_session_id},
        "goal_id": value.goal_id,
        "target_ref": value.target_ref,
        "kind": value.kind.value,
        "reference_frame": value.reference_frame.value,
        "provenance": _prov(value.provenance),
        "condition": asdict(value.condition),
        "bound_seq": value.bound_seq,
        "anchor": _position(value.anchor),
        "bound_origin": _position(value.bound_origin),
        "entity_id": value.entity_id,
        "max_entity_age_seq": value.max_entity_age_seq,
        "contract_ref": value.contract_ref,
    }


def _uncontract(value: object) -> TargetContract | None:
    if value is None:
        return None
    obj = _exact(value, {
        "scope", "goal_id", "target_ref", "kind", "reference_frame",
        "provenance", "condition", "bound_seq", "anchor", "bound_origin",
        "entity_id", "max_entity_age_seq", "contract_ref",
    }, "target contract")
    scope = _exact(obj["scope"], {"self_id", "world_session_id"}, "scope")
    condition = _exact(obj["condition"], set(ArrivalCondition.__dataclass_fields__),
                       "arrival condition")
    result = TargetContract(
        scope=ScopeRef(**scope), goal_id=obj["goal_id"],
        target_ref=obj["target_ref"], kind=TargetKind(obj["kind"]),
        reference_frame=ReferenceFrame(obj["reference_frame"]),
        provenance=_unprov(obj["provenance"]),
        condition=ArrivalCondition(**condition), bound_seq=obj["bound_seq"],
        anchor=_unposition(obj["anchor"]),
        bound_origin=_unposition(obj["bound_origin"]),
        entity_id=obj["entity_id"], max_entity_age_seq=obj["max_entity_age_seq"],
    )
    if result.contract_ref != obj["contract_ref"]:
        raise PresetCheckpointRefusal("target contract revision changed")
    return result


def _argument(value: SkillArgument) -> dict:
    if value.kind is ArgumentKind.TARGET:
        assert isinstance(value.value, SkillTarget)
        raw = {"ref": value.value.ref, "kind": value.value.kind,
               "contract": _contract(value.value.contract)}
    elif value.kind is ArgumentKind.POSITION:
        raw = _position(value.value)
    else:
        raw = value.value
    return {"name": value.name, "kind": value.kind.value, "value": raw}


def _unargument(value: object) -> SkillArgument:
    obj = _exact(value, {"name", "kind", "value"}, "parameter argument")
    kind = ArgumentKind(obj["kind"])
    raw = obj["value"]
    if kind is ArgumentKind.TARGET:
        t = _exact(raw, {"ref", "kind", "contract"}, "typed target argument")
        raw = SkillTarget(t["ref"], t["kind"], _uncontract(t["contract"]))
    elif kind is ArgumentKind.POSITION:
        raw = _unposition(raw)
    return SkillArgument(obj["name"], kind, raw)


def _pattern(value: SchemaPattern) -> dict:
    return {
        "pattern_id": value.pattern_id, "version": value.version,
        "schema_id": value.schema_id, "kind": value.kind.value,
        "predicate": value.predicate.value, "goal_id": value.goal_id,
        "skill_id": value.skill_id, "skill_version": value.skill_version,
        "target_kind": value.target_kind, "origin": value.origin.value,
        "provenance": _prov(value.provenance),
    }


def _unpattern(value: object) -> SchemaPattern:
    obj = _exact(value, {
        "pattern_id", "version", "schema_id", "kind", "predicate", "goal_id",
        "skill_id", "skill_version", "target_kind", "origin", "provenance",
    }, "Schema pattern")
    return SchemaPattern(
        pattern_id=obj["pattern_id"], version=obj["version"],
        schema_id=obj["schema_id"], kind=PatternKind(obj["kind"]),
        predicate=Predicate(obj["predicate"]), goal_id=obj["goal_id"],
        skill_id=obj["skill_id"], skill_version=obj["skill_version"],
        target_kind=obj["target_kind"], origin=Origin(obj["origin"]),
        provenance=_unprov(obj["provenance"]),
    )


def _preset(value: SkillParameterPreset) -> dict:
    return {
        "pattern_id": value.pattern_id, "preset_id": value.preset_id,
        "version": value.version, "definition_ref": value.definition_ref,
        "constraints": [_argument(a) for a in value.constraints.requirements],
        "budget": asdict(value.budget),
        "provenance": _prov(value.provenance),
        "arguments": [_argument(a) for a in value.arguments],
        "expected_cost": (None if value.expected_cost is None
                          else asdict(value.expected_cost)),
        "preset_ref": value.preset_ref,
    }


def _unpreset(value: object) -> SkillParameterPreset:
    obj = _exact(value, {
        "pattern_id", "preset_id", "version", "definition_ref", "constraints",
        "budget", "provenance", "arguments", "expected_cost", "preset_ref",
    }, "Skill Preset")
    budget = _exact(obj["budget"], set(SkillBudget.__dataclass_fields__), "budget")
    raw_cost = obj["expected_cost"]
    cost = None if raw_cost is None else SkillCostEstimate(
        **_exact(raw_cost, set(SkillCostEstimate.__dataclass_fields__), "cost")
    )
    result = SkillParameterPreset(
        pattern_id=obj["pattern_id"], preset_id=obj["preset_id"],
        version=obj["version"], definition_ref=obj["definition_ref"],
        constraints=SkillConstraints(tuple(
            _unargument(a) for a in _array(obj["constraints"], "constraints", 12)
        )),
        budget=SkillBudget(**budget), provenance=_unprov(obj["provenance"]),
        arguments=tuple(_unargument(a) for a in
                        _array(obj["arguments"], "arguments", 9)),
        expected_cost=cost,
    )
    if result.preset_ref != obj["preset_ref"]:
        raise PresetCheckpointRefusal("Preset digest changed in checkpoint")
    return result


def _registry_digest(payload: dict[str, Any]) -> str:
    return hashlib.sha256(json.dumps(
        payload, sort_keys=True, separators=(",", ":"), allow_nan=False,
    ).encode("utf-8")).hexdigest()


def encode_pattern_registry(registry: PatternRegistry, *, self_id: str) -> dict:
    """Produce data-only cognition knowledge for an existing quiesced owner cut."""
    if not isinstance(registry, PatternRegistry) or not self_id:
        raise PresetCheckpointRefusal("typed registry and Self ID required")
    if any(e.receipt.self_id != self_id for e in registry.accepted_presets):
        raise PresetCheckpointRefusal("foreign Self Preset cannot be checkpointed")
    record = {
        "schema": 2, "self_id": self_id, "revision": registry.revision,
        "patterns": [_pattern(p) for p in registry.patterns],
        "accepted_presets": [{
            "pattern_version": e.pattern_version,
            "preset": _preset(e.preset),
            "receipt": {
                "self_id": e.receipt.self_id,
                "event_id": e.receipt.event_id,
                "preset_ref": e.receipt.preset_ref,
                "provenance": _prov(e.receipt.provenance),
            },
        } for e in registry.accepted_presets],
    }
    record["registry_ref"] = "schema-registry:v2@" + _registry_digest(record)
    return record


def decode_pattern_registry(value: object, *, expected_self_id: str) -> PatternRegistry:
    """Rehydrate knowledge only; still needs fresh WorldBody/Skill admission.

    For old typed P0-D owner schema1 Pattern registries, the caller must
    deliberately migrate separately. A malformed/missing v2 record fails closed.
    """
    obj = _exact(value, {
        "schema", "self_id", "revision", "patterns", "accepted_presets",
        "registry_ref",
    }, "typed Schema checkpoint")
    if (type(obj["schema"]) is not int or obj["schema"] != 2
            or type(obj["self_id"]) is not str
            or obj["self_id"] != expected_self_id
            or type(obj["revision"]) is not int):
        raise PresetCheckpointRefusal("wrong Self or unsupported registry checkpoint")
    body = {key: value for key, value in obj.items()
            if key != "registry_ref"}
    if obj["registry_ref"] != "schema-registry:v2@" + _registry_digest(body):
        raise PresetCheckpointRefusal("Schema Registry digest changed")
    try:
        patterns = tuple(_unpattern(x) for x in
                         _array(obj["patterns"], "patterns"))
        accepted = []
        for raw in _array(obj["accepted_presets"], "accepted Presets"):
            entry = _exact(raw, {"pattern_version", "preset", "receipt"},
                           "accepted Preset")
            r = _exact(entry["receipt"], {
                "self_id", "event_id", "preset_ref", "provenance",
            }, "Self acceptance receipt")
            receipt = PresetAcceptanceReceipt(
                r["self_id"], r["event_id"], r["preset_ref"],
                _unprov(r["provenance"]),
            )
            accepted.append(AcceptedSkillPreset(
                entry["pattern_version"], _unpreset(entry["preset"]), receipt,
            ))
        result = PatternRegistry(obj["revision"], patterns, tuple(accepted))
        if encode_pattern_registry(result, self_id=expected_self_id) != obj:
            raise PresetCheckpointRefusal("Schema checkpoint failed canonical recheck")
        return result
    except (TypeError, ValueError, KeyError, AttributeError) as exc:
        if isinstance(exc, PresetCheckpointRefusal):
            raise
        raise PresetCheckpointRefusal("invalid or ambiguous Skill Preset checkpoint") from exc
