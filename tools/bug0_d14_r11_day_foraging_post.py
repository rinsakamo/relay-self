"""R11 read-only Paper one-day clock, sunlight/death, natural item & pickup census.

No Paper global source is projected into S49's native World view. Paper item
spawn proximity is explicitly NOT causal source attribution. Pickup event is
NOT proof of native inventory increment. No new physical MOVE, EAT, learning.
"""
from __future__ import annotations

import re
from typing import Any

from tools.bug0_d14_natural_world import R11_WORLD_TICKS


class R11SourceRejected(ValueError):
    """An R11 independent original Paper source is missing or inconsistent."""


def _fields(original: str, tag: str) -> dict[str, str]:
    if tag not in original:
        raise R11SourceRejected("R11_MISSING_PAPER_TAG")
    text = original.split(tag, 1)[1]
    values: dict[str, str] = {}
    for field in text.split():
        if "=" not in field:
            continue  # Paper message prefix or harmless suffix metadata.
        key, value = field.split("=", 1)
        if key in values or not key or not value:
            raise R11SourceRejected("R11_DUPLICATE_OR_BAD_FIELD")
        values[key] = value
    return values


def _int(row: dict[str, str], field: str) -> int:
    try:
        value = int(row[field])
    except (KeyError, TypeError, ValueError) as exc:
        raise R11SourceRejected("R11_EXPECTED_PAPER_INTEGER") from exc
    if value < 0 or str(value) != row[field]:
        raise R11SourceRejected("R11_NONCANONICAL_PAPER_INTEGER")
    return value


def _rows(lines: list[str], tag: str) -> list[dict[str, str]]:
    return [_fields(s, tag) for s in lines if tag in s]


def inspect_r11_natural_day(
    original: str, report: dict[str, Any], active: dict[str, Any],
) -> dict[str, Any]:
    if (
        type(original) is not str
        or not isinstance(report, dict)
        or not isinstance(active, dict)
        or report.get("r11_natural_day_opt_in") is not True
        or report.get("requested_paper_horizon_ticks") != R11_WORLD_TICKS
        or active.get("status") != "PASS_DEV"
        or active.get("r11_natural_day_opt_in") is not True
        or active.get("r10_operator_initial_stone_sword_attested") is not True
        or active.get("original_s49_s16_outcomes") != active.get("original_s49_actions")
        or active.get("r11_item_approach_action_granted") is not False
        or active.get("effective_physical_stop_attested") is not False
    ):
        raise R11SourceRejected("R11_REQUIRES_ORIGINAL_S49_PARENT_AUDIT")
    lines = original.split("\n")
    started = _rows(lines, "RSELF_ENDURANCE_START world=")
    stopped = _rows(lines, "RSELF_ENDURANCE_LIMIT world=")
    terminal = _rows(lines, "RSELF_ENDURANCE_TERMINAL world=")
    samples = _rows(lines, "RSELF_ENDURANCE_SAMPLE world=")
    if (
        len(started) != 1 or len(stopped) + len(terminal) != 1
        or len(_rows(lines, "RSELF_R11_LOOT_SOURCE_READY source=")) != 1
    ):
        raise R11SourceRejected("R11_MISSING_OR_DUPLICATE_WORLD_SOURCE")
    origin = started[0]
    world = origin.get("world")
    if world != active.get("world_uuid") or not re.fullmatch(
        r"[0-9a-f]{8}(?:-[0-9a-f]{4}){3}-[0-9a-f]{12}", world or "",
    ):
        raise R11SourceRejected("R11_WORLD_MISMATCH")
    start_tick = _int(origin, "start_tick")
    start_full_time = _int(origin, "world_full_time")
    start_time = _int(origin, "world_time")
    if (
        _int(origin, "stop_tick") != start_tick + R11_WORLD_TICKS
        or _int(origin, "horizon_ticks") != R11_WORLD_TICKS
        or origin.get("daylight_cycle") != "true"
        or start_time != start_full_time % R11_WORLD_TICKS
    ):
        raise R11SourceRejected("R11_DAYLIGHT_START_SOURCE_INVALID")
    for seq, sample in enumerate(samples, 1):
        elapsed = 200 * seq
        if (
            sample.get("world") != world
            or _int(sample, "elapsed_ticks") != elapsed
            or _int(sample, "tick") != start_tick + elapsed
            or _int(sample, "world_full_time") != start_full_time + elapsed
            or _int(sample, "world_time")
                != (start_time + elapsed) % R11_WORLD_TICKS
            or sample.get("daylight_cycle") != "true"
        ):
            raise R11SourceRejected("R11_DAYLIGHT_SAMPLE_OR_CYCLE_MISMATCH")
    if stopped:
        limit = stopped[0]
        if (
            len(samples) != 119
            or _int(limit, "elapsed_ticks") != R11_WORLD_TICKS
            or _int(limit, "world_full_time")
                != start_full_time + R11_WORLD_TICKS
            or _int(limit, "world_time") != start_time
            or limit.get("daylight_cycle") != "true"
        ):
            raise R11SourceRejected("R11_FULL_DAY_NOT_SOURCE_ATTESTED")
    # In a natural early terminal, the ordinary Paper timeline validates
    # terminal tick and 200-tick samples; no full-day claim is promoted.
    death = _rows(lines, "RSELF_R11_MANAGED_DEATH source=")
    source_death = _rows(lines, "RSELF_RESPAWN_DEATH world=")
    equip = _rows(lines, "RSELF_R10_INITIAL_STONE_SWORD world=")
    if len(equip) != 1:
        raise R11SourceRejected("R11_INITIAL_EQUIPMENT_PAPER_MISSING")
    self_uuid = equip[0].get("player")
    if not self_uuid:
        raise R11SourceRejected("R11_INITIAL_PLAYER_SOURCE_MISSING")
    if len(death) != len(source_death):
        raise R11SourceRejected("R11_UNPAIRED_PAPER_MANAGED_DEATH")
    paired_deaths = {
        (row.get("entity"), _int(row, "tick"))
        for row in source_death
        if row.get("world") == world
    }
    if len(paired_deaths) != len(source_death):
        raise R11SourceRejected("R11_DUPLICATE_PAPER_MANAGED_DEATH")
    spawn = _rows(lines, "RSELF_R11_ROTTEN_ITEM_SPAWN source=")
    pickup = _rows(lines, "RSELF_R11_ROTTEN_PICKUP_EVENT source=")
    drop_counts = {}
    for row in death:
        if (
            row.get("world") != world
            or row.get("source") != "PAPER_ENTITY_DEATH_MONITOR"
            or row.get("drop_source") != "PAPER_DEATH_DROPS_NOT_ITEM_SPAWN"
            or not row.get("last_damage_cause")
            or not row.get("zombie")
            or not row.get("killer")
            or (row.get("zombie"), _int(row, "tick")) not in paired_deaths
        ):
            raise R11SourceRejected("R11_MANAGED_DEATH_SOURCE_INVALID")
        zombie = row["zombie"]
        if zombie in drop_counts:
            raise R11SourceRejected("R11_DUPLICATE_MANAGED_DEATH_SOURCE")
        drop_counts[zombie] = _int(row, "rotten_flesh_drop_count")
    spawned = {}
    for row in spawn:
        if (
            row.get("world") != world
            or row.get("source") != "PAPER_ITEM_SPAWN"
            or row.get("death_link") != "PROXIMITY_AND_TICK_ONLY"
            or row.get("inventory_delta") != "NOT_ATTESTED"
            or row.get("zombie") not in drop_counts
        ):
            raise R11SourceRejected("R11_ITEM_SPAWN_SOURCE_OR_PARENT_INVALID")
        item = row.get("item")
        if not item or item in spawned:
            raise R11SourceRejected("R11_ITEM_SPAWN_DUPLICATE")
        spawned[item] = {
            "zombie": row["zombie"],
            "count": _int(row, "count"),
            "tick": _int(row, "tick"),
        }
    # Paper item events have only temporal/spatial proximity, never a
    # causal parent pointer. Do not promote matching IDs to an Action success.
    for zombie, count in drop_counts.items():
        if sum(v["count"] for v in spawned.values()
               if v["zombie"] == zombie) > count:
            raise R11SourceRejected("R11_PROXIMITY_ITEM_COUNT_EXCEEDS_DEATH_DROPS")
    picked = set()
    for row in pickup:
        item = row.get("item")
        if (
            row.get("world") != world
            or row.get("source") != "PAPER_ENTITY_PICKUP_EVENT"
            or row.get("inventory_delta") != "NOT_ATTESTED"
            or row.get("self_action") != "NOT_ISSUED_BY_WITNESS"
            or item not in spawned or item in picked
            or row.get("zombie") != spawned[item]["zombie"]
            or row.get("player") != self_uuid
            or _int(row, "tick") < spawned[item]["tick"]
        ):
            raise R11SourceRejected("R11_PICKUP_OR_ITEM_UUID_UNQUALIFIED")
        picked.add(item)
    return {
        "status": "PAPER_SOURCE_ONLY",
        "classification": "R11_24000_NATURAL_DAY_AND_PASSIVE_LOOT_WITNESSES",
        "world_uuid": world,
        "start_world_time": start_time,
        "end_world_time": (
            _int(stopped[0], "world_time") if stopped else None
        ),
        "sample_count": len(samples),
        "full_day_horizon_survived": bool(stopped),
        "world_tick_elapsed": active.get("observed_world_ticks"),
        "natural_daylight_cycle_paper_attested": True,
        "managed_zombie_death_causes": [
            {"zombie": x["zombie"], "cause": x["last_damage_cause"],
             "killer": x["killer"], "rotten_count": drop_counts[x["zombie"]]}
            for x in death
        ],
        "paper_managed_rotten_death_count": sum(drop_counts.values()),
        "paper_proximity_only_rotten_item_spawn_count": len(spawned),
        "paper_pickup_event_count_not_inventory_proof": len(picked),
        "native_positive_rotten_inventory_deltas": active.get(
            "r11_native_positive_rotten_inventory_deltas", [],
        ),
        "paper_item_link_is_independently_causal": False,
        "native_item_target_type_known": False,
        "original_s49_item_approach_authorized": False,
        "paper_effective_post_move_stop_attested": False,
        "native_item_pickup_inventory_both_sources_proven": False,
        "natural_food_to_s51_eat_proven": False,
        "learning_authorized": False,
        "qualification": "NO_GO",
        "science": "NOT_RUN",
    }
