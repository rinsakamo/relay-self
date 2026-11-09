"""R10 read-only Paper damage and initial stone-sword census.

Never supplies physical Action authority or attributes Paper damage to
an exact original S49 Action ID. All data is supplied by the original
server log and independently source-consistent natural-World audit.
"""
from __future__ import annotations

import math
import re
from typing import Any

MARK_EQUIP = "RSELF_R10_INITIAL_STONE_SWORD "
MARK_ZOMBIE = "RSELF_R10_ZOMBIE_DAMAGE "
MARK_SELF = "RSELF_R10_SELF_DAMAGE "
MARK_AFTER = "RSELF_R10_DAMAGE_AFTER "
MARK_DEATH = "RSELF_RESPAWN_DEATH "
UUID = re.compile(r"^[0-9a-f]{8}(?:-[0-9a-f]{4}){3}-[0-9a-f]{12}$")


class R10PaperCombatRejected(ValueError):
    """R10 Paper damage source cannot be independently interpreted."""


def _fields(line: str, marker: str) -> dict[str, str]:
    if marker not in line:
        raise R10PaperCombatRejected("R10_PAPER_MARKER_MISSING")
    fields: dict[str, str] = {}
    for token in line.split(marker, 1)[1].split():
        if token.count("=") != 1:
            raise R10PaperCombatRejected("R10_PAPER_BAD_TOKEN")
        key, value = token.split("=", 1)
        if not key or not value or key in fields:
            raise R10PaperCombatRejected("R10_PAPER_DUPLICATE_OR_EMPTY_FIELD")
        fields[key] = value
    return fields


def _integer(fields: dict[str, str], key: str) -> int:
    try:
        value = fields[key]
        number = int(value)
    except (KeyError, TypeError, ValueError) as exc:
        raise R10PaperCombatRejected("R10_PAPER_INTEGER_MISSING") from exc
    if number < 0 or str(number) != value:
        raise R10PaperCombatRejected("R10_PAPER_INTEGER_NONCANONICAL")
    return number


def _health(fields: dict[str, str], key: str) -> float:
    try:
        number = float(fields[key])
    except (KeyError, TypeError, ValueError) as exc:
        raise R10PaperCombatRejected("R10_PAPER_HEALTH_MISSING") from exc
    if not math.isfinite(number) or not 0 <= number <= 20:
        raise R10PaperCombatRejected("R10_PAPER_HEALTH_INVALID")
    return number


def _uuid(fields: dict[str, str], key: str) -> str:
    value = fields.get(key, "")
    if not UUID.fullmatch(value):
        raise R10PaperCombatRejected("R10_PAPER_UUID_INVALID_" + key)
    return value


def inspect_r10_paper_combat(
    original: str, report: dict[str, Any], active_audit: dict[str, Any],
) -> dict[str, Any]:
    """Pure original-server event census; no inferred strike attribution."""
    if (
        not isinstance(original, str)
        or not isinstance(report, dict)
        or report.get("r10_initial_sword_opt_in") is not True
        or not isinstance(active_audit, dict)
        or active_audit.get("status") != "PASS_DEV"
        or active_audit.get("r10_operator_initial_stone_sword_attested") is not True
        or active_audit.get("r10_damage_caused_by_specific_s49_action_attested") is not False
    ):
        raise R10PaperCombatRejected("R10_SOURCE_AND_PARENT_AUDIT_REQUIRED")
    world = active_audit.get("world_uuid")
    if not isinstance(world, str) or not UUID.fullmatch(world):
        raise R10PaperCombatRejected("R10_WORLD_ID_MISSING")
    lines = original.split("\n")  # Preserve Paper CR inside each original line.
    eq = [_fields(x, MARK_EQUIP) for x in lines if MARK_EQUIP in x]
    if len(eq) != 1:
        raise R10PaperCombatRejected("R10_EXACT_ONE_INITIAL_SWORD_REQUIRED")
    equipment = eq[0]
    player = _uuid(equipment, "player")
    if (
        _uuid(equipment, "world") != world
        or equipment.get("item") != "STONE_SWORD"
        or equipment.get("count") != "1"
        or equipment.get("hand") != "MAIN_HAND"
        or equipment.get("source") != "PAPER_OPERATOR_INITIAL_ONLY"
        or equipment.get("physics") != "VANILLA"
        or equipment.get("no_auto_attack") != "true"
    ):
        raise R10PaperCombatRejected("R10_INITIAL_EQUIPMENT_SOURCE_INVALID")
    equip_tick = _integer(equipment, "tick")
    raw_events = [
        (MARK_ZOMBIE if MARK_ZOMBIE in line else MARK_SELF, line)
        for line in lines
        if MARK_ZOMBIE in line or MARK_SELF in line
    ]
    raw_after = [line for line in lines if MARK_AFTER in line]
    after_by_ordinal: dict[int, dict[str, str]] = {}
    for line in raw_after:
        row = _fields(line, MARK_AFTER)
        ordinal = _integer(row, "ordinal")
        if ordinal in after_by_ordinal:
            raise R10PaperCombatRejected("R10_DUPLICATE_PAPER_AFTER_EVENT")
        if (
            row.get("source") != "PAPER_NEXT_MAIN_THREAD_TICK"
            or _uuid(row, "world") != world
            or row.get("s49_action_id") != "NOT_ATTESTED"
            or _integer(row, "observed_tick") < _integer(row, "event_tick")
        ):
            raise R10PaperCombatRejected("R10_AFTER_EVENT_SOURCE_INVALID")
        _uuid(row, "victim")
        after_by_ordinal[ordinal] = row
    actions = []
    zombie_count = 0
    self_count = 0
    for expected, (kind, line) in enumerate(raw_events, 1):
        ev = _fields(line, kind)
        if (
            _integer(ev, "ordinal") != expected
            or ev.get("source") != "PAPER_ENTITY_DAMAGE_MONITOR"
            or _uuid(ev, "world") != world
            or _uuid(ev, "player") != player
            or ev.get("s49_action_id") != "NOT_ATTESTED"
            or ev.get("cancelled") != "false"
            or ev.get("cause") not in ("ENTITY_ATTACK", "ENTITY_SWEEP_ATTACK")
        ):
            raise R10PaperCombatRejected("R10_DAMAGE_EVENT_SOURCE_INVALID")
        tick = _integer(ev, "tick")
        if tick < equip_tick:
            raise R10PaperCombatRejected("R10_DAMAGE_BEFORE_INITIAL_SWORD")
        victim = _uuid(ev, "victim")
        attacker = _uuid(ev, "attacker")
        before = _health(ev, "health_before")
        try:
            final_damage = float(ev["final_damage"])
        except (KeyError, ValueError) as exc:
            raise R10PaperCombatRejected("R10_FINAL_DAMAGE_MISSING") from exc
        if not math.isfinite(final_damage) or not 0 <= final_damage <= 100:
            raise R10PaperCombatRejected("R10_FINAL_DAMAGE_INVALID")
        if kind == MARK_ZOMBIE:
            zombie_count += 1
            if attacker != player or ev.get("main_hand") != "STONE_SWORD":
                raise R10PaperCombatRejected("R10_NATIVE_SWORD_ATTACK_NOT_PAPER_SOURCE")
        else:
            self_count += 1
            if victim != player:
                raise R10PaperCombatRejected("R10_SELF_DAMAGE_FOREIGN_PLAYER")
        after = after_by_ordinal.pop(expected, None)
        delta = None
        if after is not None:
            if (
                _integer(after, "event_tick") != tick
                or _uuid(after, "victim") != victim
            ):
                raise R10PaperCombatRejected("R10_WRONG_VICTIM_AFTER_DAMAGE")
            if after.get("health_after") != "NOT_LIVING":
                later = _health(after, "health_after")
                delta = before - later
        actions.append({
            "ordinal": expected,
            "kind": "ZOMBIE" if kind == MARK_ZOMBIE else "SELF",
            "paper_tick": tick,
            "paper_victim_uuid": victim,
            "paper_final_damage": final_damage,
            "paper_health_before": before,
            "paper_next_tick_health_delta": delta,
            "paper_next_tick_readback": after is not None,
            "s49_action_attribution": "NOT_CAUSALLY_ATTESTED",
        })
    if after_by_ordinal:
        raise R10PaperCombatRejected("R10_ORPHAN_POST_DAMAGE_SOURCE")
    paper_deaths = [_fields(line, MARK_DEATH) for line in lines if MARK_DEATH in line]
    confirmed_self_kills = 0
    for death in paper_deaths:
        if _uuid(death, "world") != world:
            raise R10PaperCombatRejected("R10_FOREIGN_WORLD_MANAGED_DEATH")
        _uuid(death, "entity")
        _integer(death, "tick")
        if death.get("killer") == player:
            confirmed_self_kills += 1
    return {
        "classification": "R10_PAPER_WORLD_SWORD_AND_DAMAGE_SOURCE_ONLY",
        "world_uuid": world,
        "paper_player_uuid": player,
        "paper_equipped_item": "STONE_SWORD",
        "paper_equipment_count": 1,
        "paper_equipment_tick": equip_tick,
        "paper_zombie_melee_damage_event_count": zombie_count,
        "paper_self_melee_damage_event_count": self_count,
        "paper_next_tick_positive_zombie_health_delta_count": sum(
            event["kind"] == "ZOMBIE"
            and event["paper_next_tick_health_delta"] is not None
            and event["paper_next_tick_health_delta"] > 0
            for event in actions
        ),
        "paper_managed_zombie_death_count": len(paper_deaths),
        "paper_killer_is_self_death_count": confirmed_self_kills,
        "paper_damage_events": actions,
        "s49_action_to_paper_damage_causal_link_attested": False,
        "s49_auto_attack_added": False,
        "food_or_loot_staged": False,
        "physical_stop_attested": False,
        "c1_learning_authorized": False,
        "qualification": "NO_GO",
        "science": "NOT_RUN",
    }
