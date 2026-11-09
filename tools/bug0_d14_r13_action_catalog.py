"""R13: read-only, owner-checked S49 Action Catalog and bounded Skill DSL.

The Catalog describes already implemented interfaces. Introspection verifies
their ABI, not physical suitability, safety, or permission to invoke them.
It never constructs authorizations, calls a method, or issues an Action.
"""
from __future__ import annotations

import hashlib
import inspect
import json
from dataclasses import fields
from typing import Any

from adapters.mineflayer.normal_action import (
    NormalActionAuthorization,
    NormalAttackingAuthorization,
    NormalEatingAuthorization,
    NormalSessionActionExecutor,
)
from adapters.mineflayer.s49_basic_priority_l0 import S49BasicPriorityL0
from tools.bug0_d14_natural_motion import NaturalOriginalS49Motion

CATALOG_VERSION = "D14_R13_OWNER_CHECKED_ACTION_CATALOG_V1"
ACTIONS = ("MOVE_AWAY", "ATTACK", "EAT", "REST", "WAIT")
GUARDS = (
    "S49_NATIVE_MOVE_CANDIDATE",
    "STABLE_CLOSE_ZOMBIE",
    "S51_SAFE_EAT_CANDIDATE",
    "REST_EXPLICITLY_REQUESTED",
    "ALWAYS",
)
BINDINGS = (
    "NATIVE_S49_MOVE_SOURCE",
    "NATIVE_STABLE_ZOMBIE_ID",
    "S51_OBSERVED_EAT_CHOICE",
    "NONE",
)
UNAVAILABLE = ("STOP", "SKIP")


class CatalogRejected(ValueError):
    """Read-only API contract drift or invalid Skill program."""


# The prose is an *authored interface description*, not generated permission.
# Signature+dataclass checks below prevent presenting stale API parameters.
_DEFINITIONS: tuple[dict[str, Any], ...] = (
    {
        "action": "MOVE_AWAY",
        "kind": "physical_s49_action",
        "description": "Attempt a bounded backward movement away from the observed threat.",
        "owner": "NaturalOriginalS49Motion",
        "guard": "S49_NATIVE_MOVE_CANDIDATE",
        "binding": "NATIVE_S49_MOVE_SOURCE",
        "parameters": ("event_seq", "probe_seq", "entity_id"),
        "preconditions": (
            "unsolicited native entities event and fresh own-session probe",
            "current_candidate plus frozen S49/S14 selection",
            "separate physical pre-ISSUE fence and operator-scoped grants",
        ),
        "possible_observations": (
            "S16 action outcome and bounded observed movement distance",
            "post-clear effective physical STOP remains unqualified",
        ),
        "limits": ("one original S49 issuer", "no implicit post-MOVE EAT"),
        "source": "tools/bug0_d14_natural_motion.py:"
                  "NaturalOriginalS49Motion.issue_original_move",
    },
    {
        "action": "ATTACK",
        "kind": "physical_s49_action",
        "description": "Attempt an attack on one currently stable, near zombie.",
        "owner": "NormalSessionActionExecutor",
        "guard": "STABLE_CLOSE_ZOMBIE",
        "binding": "NATIVE_STABLE_ZOMBIE_ID",
        "parameters": ("target_entity_id",),
        "preconditions": (
            "two fresh native probes in the same session with the same zombie",
            "target is 0.1..2.8m and the coverage is not truncated",
            "physical STOP eligible and two separately scoped Action grants",
        ),
        "possible_observations": (
            "native ATTACK ACK / S16 outcome / target hurt event",
            "S16 outcome alone does not prove damage, kill, or drop",
        ),
        "limits": ("bounded sequential ATTACKs", "owner S49 admission"),
        "source": "adapters/mineflayer/normal_action.py:"
                  "NormalSessionActionExecutor.require_attack_authorizations",
    },
    {
        "action": "EAT",
        "kind": "physical_s49_action",
        "description": "Try consuming an own-inventory food candidate.",
        "owner": "NormalSessionActionExecutor",
        "guard": "S51_SAFE_EAT_CANDIDATE",
        "binding": "S51_OBSERVED_EAT_CHOICE",
        "parameters": ("food_item", "food_slot"),
        "preconditions": (
            "S51/native observed eligible food choice and current slot",
            "stable fresh own-session native probes, no nearby entity",
            "post-MOVE settling qualified and two scoped Action grants",
        ),
        "possible_observations": (
            "S51 food/inventory change and S16 Action outcome",
            "food delta is not proof of long-run survival or learning",
        ),
        "limits": ("owner S49/S51 admission", "no fabricated food slot"),
        "source": "adapters/mineflayer/normal_action.py:"
                  "NormalSessionActionExecutor.require_eating_authorizations",
    },
    {
        "action": "REST",
        "kind": "intent_only",
        "description": "Select a rest intent; NOT a physical REST command.",
        "owner": "S49BasicPriorityL0",
        "guard": "REST_EXPLICITLY_REQUESTED",
        "binding": "NONE",
        "parameters": (),
        "preconditions": ("rest_requested=True on the existing priority cursor",),
        "possible_observations": (
            "a REST intent selection, not fatigue recovery proof",
        ),
        "limits": ("no physical Action and no S49 grant from this selection",),
        "source": "adapters/mineflayer/s49_basic_priority_l0.py:"
                  "S49BasicPriorityL0.decide",
    },
    {
        "action": "WAIT",
        "kind": "non_issuing_choice",
        "description": "Choose not to issue a physical Action on this step.",
        "owner": "S49BasicPriorityL0",
        "guard": "ALWAYS",
        "binding": "NONE",
        "parameters": (),
        "preconditions": ("owner still observes real source state",),
        "possible_observations": ("later native state may change",),
        "limits": ("not a guaranteed physical rest or timed wait",),
        "source": "adapters/mineflayer/s49_basic_priority_l0.py:"
                  "S49BasicPriorityL0.decide",
    },
)


def _require_params(owner: type, method: str,
                    expected: tuple[str, ...]) -> dict[str, Any]:
    fn = getattr(owner, method, None)
    if fn is None or not callable(fn):
        raise CatalogRejected("OWNER_METHOD_MISSING:" + owner.__name__ + "." + method)
    signature = inspect.signature(fn)
    actual = tuple(signature.parameters)
    if any(name not in actual for name in expected):
        raise CatalogRejected("OWNER_SIGNATURE_DRIFT:" + method)
    return {
        "method": owner.__name__ + "." + method,
        "parameter_names": list(actual),
    }


def _require_fields(kind: type, expected: tuple[str, ...]) -> list[str]:
    actual = tuple(field.name for field in fields(kind))
    if any(name not in actual for name in expected):
        raise CatalogRejected("ACTION_AUTHORIZATION_FIELDS_DRIFT:" + kind.__name__)
    return list(actual)


def _owner_contracts() -> dict[str, dict[str, Any]]:
    """Verify the real Python owner interfaces BEFORE exposing the Catalog."""
    move = _require_params(NaturalOriginalS49Motion, "issue_original_move",
                           ("session", "event", "probe", "cycle"))
    move["candidate"] = _require_params(
        NaturalOriginalS49Motion, "current_candidate", ("probe",),
    )
    move["authorization_fields"] = _require_fields(
        NormalActionAuthorization,
        ("stage", "event_seq", "probe_seq", "entity_id", "granted"),
    )
    attack = _require_params(
        NormalSessionActionExecutor, "require_attack_authorizations",
        ("previous_probe", "probe", "target_entity_id", "propose", "issue"),
    )
    attack["authorization_fields"] = _require_fields(
        NormalAttackingAuthorization,
        ("stage", "probe_seq", "probe_request_id",
         "target_entity_id", "granted"),
    )
    eat = _require_params(
        NormalSessionActionExecutor, "require_eating_authorizations",
        ("choice", "probe", "propose", "issue", "previous_probe"),
    )
    eat["authorization_fields"] = _require_fields(
        NormalEatingAuthorization,
        ("stage", "probe_seq", "probe_request_id",
         "food_item", "food_slot", "granted"),
    )
    decision = _require_params(
        S49BasicPriorityL0, "decide", ("probe", "rest_requested"),
    )
    return {
        "MOVE_AWAY": move,
        "ATTACK": attack,
        "EAT": eat,
        "REST": decision,
        "WAIT": decision,
    }


def _digest(value: object) -> str:
    return hashlib.sha256(json.dumps(
        value, ensure_ascii=False, sort_keys=True,
        separators=(",", ":"), allow_nan=False,
    ).encode("utf-8")).hexdigest()


def action_catalog() -> dict[str, Any]:
    """Deterministic, read-only Catalog; no physical authority or writer."""
    contracts = _owner_contracts()
    if set(contracts) != set(ACTIONS):
        raise CatalogRejected("CATALOG_OWNER_SET_CHANGED")
    entries = []
    for item in _DEFINITIONS:
        action = item["action"]
        if action not in contracts:
            raise CatalogRejected("UNOWNED_ACTION_IN_CATALOG")
        if item["guard"] not in GUARDS or item["binding"] not in BINDINGS:
            raise CatalogRejected("INVALID_CATALOG_GUARD_OR_BINDING")
        entries.append({**item, "parameters": list(item["parameters"]),
                        "preconditions": list(item["preconditions"]),
                        "possible_observations": list(item["possible_observations"]),
                        "limits": list(item["limits"]),
                        "owner_contract": contracts[action]})
    if len(entries) != len(ACTIONS):
        raise CatalogRejected("CATALOG_DUPLICATED_OR_MISSING_ACTION")
    catalog = {
        "version": CATALOG_VERSION,
        "scope": "POST_WORLD_L2_REFERENCE_ONLY",
        "owner": "ORIGINAL_S49_S51_WITH_FROZEN_ADMISSION",
        "entries": entries,
        "no_implicit_action_grant": True,
        "no_skill_execution_or_installation": True,
    }
    catalog["catalog_sha256"] = _digest(catalog)
    return catalog


def skill_step_schema() -> dict[str, Any]:
    return {
        "type": "object", "additionalProperties": False,
        "properties": {
            "action": {"type": "string", "enum": list(ACTIONS)},
            "guard": {"type": "string", "enum": list(GUARDS)},
            "binding": {"type": "string", "enum": list(BINDINGS)},
            "repeat": {"type": "integer", "enum": [1, 2, 3]},
            "if_unavailable": {"type": "string", "enum": list(UNAVAILABLE)},
        },
        "required": ["action", "guard", "binding", "repeat", "if_unavailable"],
    }


def skill_program_schema() -> dict[str, Any]:
    return {
        "type": "object", "additionalProperties": False,
        "properties": {
            "name": {"type": "string", "minLength": 1, "maxLength": 80},
            "cue": {"type": "string", "minLength": 1, "maxLength": 240},
            "steps": {"type": "array", "items": skill_step_schema(),
                      "minItems": 1, "maxItems": 10},
            "max_actions": {"type": "integer", "enum": list(range(1, 11))},
            "stop_condition": {"type": "string",
                               "enum": ["GOAL_OR_SOURCE_CHANGE"]},
            "on_failure": {"type": "string", "enum": ["ESCALATE"]},
        },
        "required": ["name", "cue", "steps", "max_actions",
                     "stop_condition", "on_failure"],
    }


def _nonempty(value: object, limit: int) -> bool:
    return type(value) is str and 0 < len(value) <= limit


def validate_skill_program(program: object, catalog: dict[str, Any]) -> dict:
    """Static typed Skill validation, never a pre-flight physical admission."""
    if not isinstance(catalog, dict) or catalog != action_catalog():
        raise CatalogRejected("SKILL_CATALOG_NOT_CURRENT_OWNER_CONTRACT")
    if type(program) is not dict or set(program) != {
        "name", "cue", "steps", "max_actions", "stop_condition", "on_failure",
    }:
        raise CatalogRejected("SKILL_PROGRAM_SHAPE_INVALID")
    if (not _nonempty(program["name"], 80)
            or not _nonempty(program["cue"], 240)
            or type(program["steps"]) is not list
            or not 1 <= len(program["steps"]) <= 10
            or type(program["max_actions"]) is not int
            or not 1 <= program["max_actions"] <= 10
            or program["stop_condition"] != "GOAL_OR_SOURCE_CHANGE"
            or program["on_failure"] != "ESCALATE"):
        raise CatalogRejected("SKILL_PROGRAM_BUDGET_OR_METADATA_INVALID")
    by_action = {entry["action"]: entry for entry in catalog["entries"]}
    budget = 0
    for step in program["steps"]:
        if type(step) is not dict or set(step) != {
            "action", "guard", "binding", "repeat", "if_unavailable",
        }:
            raise CatalogRejected("SKILL_STEP_SHAPE_INVALID")
        action = step["action"]
        if type(action) is not str or action not in by_action:
            raise CatalogRejected("SKILL_UNKNOWN_ACTION")
        entry = by_action[action]
        if (step["guard"] != entry["guard"]
                or step["binding"] != entry["binding"]
                or type(step["repeat"]) is not int
                or not 1 <= step["repeat"] <= 3
                or step["if_unavailable"] not in UNAVAILABLE):
            raise CatalogRejected("SKILL_STEP_OWNER_BINDING_INVALID")
        # This is a static cap on *attempts*, not a grant to issue them.
        budget += step["repeat"]
    if budget > program["max_actions"]:
        raise CatalogRejected("SKILL_TOTAL_ATTEMPTS_EXCEED_BUDGET")
    return program


def shadow_compile(program: object, catalog: dict[str, Any]) -> dict[str, Any]:
    """A reproducible inert read-only plan, NOT executable S49 grants."""
    checked = validate_skill_program(program, catalog)
    return {
        "classification": "R13_TYPED_CONDITIONAL_SKILL_SHADOW_COMPILED",
        "program_sha256": _digest(checked),
        "catalog_sha256": catalog["catalog_sha256"],
        "max_attempts": checked["max_actions"],
        "total_declared_attempts": sum(
            item["repeat"] for item in checked["steps"]
        ),
        "conditional_steps": [
            {
                "step_index": i, "action": item["action"],
                "guard": item["guard"], "argument_source": item["binding"],
                "repeat_cap": item["repeat"],
                "otherwise": item["if_unavailable"],
                "original_owner": next(
                    e["owner"] for e in catalog["entries"]
                    if e["action"] == item["action"]
                ),
            } for i, item in enumerate(checked["steps"])
        ],
        "authority": "NONE",
        "physical_actions_issued": 0,
        "memory_writes": 0, "learning_updates": 0,
        "skill_installs": 0,
    }
