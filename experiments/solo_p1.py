"""P1-C: offline, fail-closed SOLO_NO_AGENTS World-evidence admission contract.

No Minecraft runner, server mutation, policy, scientific qualification, or claim
that a caller-provided receipt is an authenticated original. R/S own sources.
"""
from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass, replace
from pathlib import Path
from typing import Any, Literal

_CLASS_INVALID = "SOLO_PROFILE_INVALID"
_CLASS_SOURCE = "SOLO_SOURCE_UNQUALIFIED"
_SERVER_KEYS = frozenset(("spawn-monsters",))
_RULE_KEYS = frozenset(("doMobSpawning", "doTraderSpawning", "doPatrolSpawning", "doInsomnia", "doWardenSpawning"))
_INERT_TYPES = frozenset({
    "minecraft:item", "minecraft:experience_orb", "minecraft:falling_block",
    "minecraft:painting", "minecraft:item_frame", "minecraft:glow_item_frame",
    "minecraft:armor_stand", "minecraft:interaction", "minecraft:block_display",
    "minecraft:item_display", "minecraft:text_display", "minecraft:arrow",
})
_SHA256 = re.compile(r"[0-9a-f]{64}\Z")
_ENTITY_ID = re.compile(r"[a-z0-9_:.\-/]+\Z")
_SOURCE_SCOPE = "server_all_loaded_chunks_and_entity_lifecycle"


class SoloRejected(ValueError):
    """Source absent is unqualified; witnessed other agency invalidates solo."""

    def __init__(self, message: str, *, contamination: bool = False) -> None:
        super().__init__(message)
        self.classification = _CLASS_INVALID if contamination else _CLASS_SOURCE


def _nonblank(value: object) -> bool:
    return type(value) is str and bool(value.strip())


def _typed_kv(value: object, expected_keys: frozenset[str]) -> tuple[tuple[str, bool], ...]:
    if not isinstance(value, dict) or set(value) != expected_keys or any(
        type(x) is not bool or x is not False for x in value.values()
    ):
        raise SoloRejected("all 1.21.8 anti-spawn controls must be explicitly false")
    return tuple(sorted(value.items()))


@dataclass(frozen=True)
class SoloProfile:
    profile_id: str
    minecraft_version: str
    dimension: str
    self_player_id: str
    server_settings: tuple[tuple[str, bool], ...]
    gamerules: tuple[tuple[str, bool], ...]
    inert_entity_types: tuple[str, ...]
    world_mode: str
    science_qualified: bool = False

    def __post_init__(self) -> None:
        if (not _nonblank(self.profile_id)
                or self.minecraft_version != "1.21.8"
                or self.dimension != "minecraft:overworld"
                or not _nonblank(self.self_player_id)
                or self.world_mode != "R_S_ISOLATED_DISPOSABLE"
                or self.science_qualified is not False
                or self.server_settings != tuple(sorted((k, False) for k in _SERVER_KEYS))
                or self.gamerules != tuple(sorted((k, False) for k in _RULE_KEYS))
                or self.inert_entity_types != tuple(sorted(_INERT_TYPES))):
            raise SoloRejected("unsupported or permissive SOLO_NO_AGENTS profile")

    @property
    def sha256(self) -> str:
        body = {
            "profile_id": self.profile_id,
            "minecraft_version": self.minecraft_version,
            "dimension": self.dimension,
            "self_player_id": self.self_player_id,
            "server_settings": dict(self.server_settings),
            "gamerules": dict(self.gamerules),
            "inert_entity_types": list(self.inert_entity_types),
            "world_mode": self.world_mode,
            "science_qualified": self.science_qualified,
        }
        return hashlib.sha256(json.dumps(body, sort_keys=True, separators=(",", ":")).encode()).hexdigest()


def parse_profile(document: object) -> SoloProfile:
    if not isinstance(document, dict) or set(document) != {
        "version", "profile_id", "minecraft_version", "dimension", "self_player_id",
        "server_settings", "gamerules", "inert_entity_types", "world_mode", "science_qualified",
    } or document["version"] != "P1_C_SOLO_V1":
        raise SoloRejected("unsupported or incomplete solo profile")
    inert = document["inert_entity_types"]
    if not isinstance(inert, list) or any(type(x) is not str for x in inert):
        raise SoloRejected("inert entity whitelist must be explicit")
    return SoloProfile(
        profile_id=document["profile_id"],
        minecraft_version=document["minecraft_version"],
        dimension=document["dimension"],
        self_player_id=document["self_player_id"],
        server_settings=_typed_kv(document["server_settings"], _SERVER_KEYS),
        gamerules=_typed_kv(document["gamerules"], _RULE_KEYS),
        inert_entity_types=tuple(inert),
        world_mode=document["world_mode"],
        science_qualified=document["science_qualified"],
    )


def load_profile(path: str | Path) -> SoloProfile:
    def unique(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
        result: dict[str, Any] = {}
        for key, value in pairs:
            if key in result:
                raise SoloRejected("duplicate profile field")
            result[key] = value
        return result

    def bad_constant(value: str) -> None:
        raise SoloRejected(f"invalid numeric profile constant {value}")

    try:
        value = json.loads(Path(path).read_text(encoding="utf-8"),
                           object_pairs_hook=unique, parse_constant=bad_constant)
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise SoloRejected("solo profile cannot be read") from exc
    return parse_profile(value)


@dataclass(frozen=True)
class Entity:
    entity_id: str
    kind: str


@dataclass(frozen=True)
class EntityEvent:
    sequence: int
    kind: Literal["SPAWN", "LOAD", "TRANSFORM", "DESPAWN", "UNLOAD"]
    entity: Entity


@dataclass(frozen=True)
class ServerCensus:
    """Descriptor that R must back with original, full-scope server evidence.

    Minecraft Mineflayer's capped 16m/16-entity nearby listing is *not* this
    source. Static config flags and digest strings are never proof on their own.
    """

    session_id: str
    world_tick: int
    dimension: str
    self_player_id: str
    source_scope: str
    source_original_sha256: str
    server_settings_readback: tuple[tuple[str, bool], ...]
    gamerules_readback: tuple[tuple[str, bool], ...]
    loaded_chunks: tuple[str, ...]
    scanned_chunks: tuple[str, ...]
    connected_players: tuple[str, ...]
    entities: tuple[Entity, ...]
    lifecycle_events: tuple[EntityEvent, ...]
    all_loaded_chunks_included: bool
    lifecycle_stream_contiguous: bool
    original_source_independently_verified: bool


@dataclass(frozen=True)
class SoloAudit:
    session_id: str
    profile_sha256: str
    world_tick: int
    last_event_sequence: int
    census_ticks: int
    transcript_sha256: str
    classification: str = "SOLO_OFFLINE_SHAPE_PASS_NOT_QUALIFIED"


def _valid_entity(profile: SoloProfile, entity: object) -> None:
    if (not isinstance(entity, Entity)
            or not _nonblank(entity.entity_id)
            or not _nonblank(entity.kind)
            or _ENTITY_ID.fullmatch(entity.kind) is None):
        raise SoloRejected("invalid or unknown entity source shape")
    if entity.kind == "minecraft:player":
        if entity.entity_id != profile.self_player_id:
            raise SoloRejected("additional autonomous player detected", contamination=True)
    elif entity.kind not in _INERT_TYPES:
        # Default deny: zombies, cows, villagers, pets, golems, unknown modded
        # entities, and future entities alike are not solo subjects.
        raise SoloRejected(f"autonomous/unknown entity {entity.kind} detected", contamination=True)


def _frame(profile: SoloProfile, census: ServerCensus, last_seq: int) -> int:
    if not isinstance(census, ServerCensus):
        raise SoloRejected("typed R source census required")
    if (not _nonblank(census.session_id)
            or type(census.world_tick) is not int or census.world_tick < 0
            or census.dimension != profile.dimension
            or census.self_player_id != profile.self_player_id
            or census.source_scope != _SOURCE_SCOPE
            or type(census.source_original_sha256) is not str
            or _SHA256.fullmatch(census.source_original_sha256) is None
            or census.original_source_independently_verified is not True
            or census.all_loaded_chunks_included is not True
            or census.lifecycle_stream_contiguous is not True
            or census.server_settings_readback != profile.server_settings
            or census.gamerules_readback != profile.gamerules):
        raise SoloRejected("R server source, anti-spawn readback or scope not qualified")
    if (not isinstance(census.loaded_chunks, tuple)
            or not census.loaded_chunks
            or not isinstance(census.scanned_chunks, tuple)
            or not isinstance(census.connected_players, tuple)
            or len(set(census.loaded_chunks)) != len(census.loaded_chunks)
            or len(set(census.scanned_chunks)) != len(census.scanned_chunks)
            or any(not _nonblank(x) for x in census.loaded_chunks + census.scanned_chunks)
            or set(census.loaded_chunks) != set(census.scanned_chunks)):
        raise SoloRejected("incomplete or ambiguous all-loaded-chunk census")
    if (not isinstance(census.connected_players, tuple)
            or any(not _nonblank(p) for p in census.connected_players)):
        raise SoloRejected("invalid connected-player census shape")
    if any(p != profile.self_player_id for p in census.connected_players):
        raise SoloRejected("additional independent player detected", contamination=True)
    if census.connected_players != (profile.self_player_id,):
        raise SoloRejected("self player absent or duplicated in player census")
    if (not isinstance(census.entities, tuple)
            or not isinstance(census.lifecycle_events, tuple)):
        raise SoloRejected("entity census and lifecycle must be complete tuples")
    seen: set[str] = set()
    own = 0
    for entity in census.entities:
        _valid_entity(profile, entity)
        if entity.entity_id in seen:
            raise SoloRejected("duplicate entity identity in census")
        seen.add(entity.entity_id)
        if entity.kind == "minecraft:player":
            own += 1
    if own != 1:
        raise SoloRejected("self player missing from server entity census")
    for event in census.lifecycle_events:
        if (not isinstance(event, EntityEvent)
                or type(event.sequence) is not int
                or event.sequence != last_seq + 1
                or event.kind not in ("SPAWN", "LOAD", "TRANSFORM", "DESPAWN", "UNLOAD")):
            raise SoloRejected("missing/duplicate/invalid server lifecycle event sequence")
        _valid_entity(profile, event.entity)
        last_seq = event.sequence
    return last_seq


def _digest_step(previous: str, census: ServerCensus) -> str:
    # Local reproducibility hash; NOT a substitute for original capture bytes.
    material = (previous, census.session_id, census.world_tick,
                census.source_original_sha256,
                tuple((e.entity_id, e.kind) for e in census.entities),
                tuple((e.sequence, e.kind, e.entity.entity_id, e.entity.kind)
                      for e in census.lifecycle_events))
    return hashlib.sha256(repr(material).encode("utf-8")).hexdigest()


def begin(profile: SoloProfile, census: ServerCensus) -> SoloAudit:
    if not isinstance(profile, SoloProfile):
        raise SoloRejected("P1 solo profile required")
    last = _frame(profile, census, -1)
    return SoloAudit(census.session_id, profile.sha256, census.world_tick,
                     last, 1, _digest_step(profile.sha256, census))


def advance(profile: SoloProfile, audit: SoloAudit, census: ServerCensus) -> SoloAudit:
    if (not isinstance(profile, SoloProfile) or not isinstance(audit, SoloAudit)
            or not isinstance(census, ServerCensus)
            or audit.profile_sha256 != profile.sha256
            or census.session_id != audit.session_id
            or type(census.world_tick) is not int
            or census.world_tick != audit.world_tick + 1):
        raise SoloRejected("solo provenance/profile or consecutive World tick mismatch")
    last = _frame(profile, census, audit.last_event_sequence)
    return replace(audit, world_tick=census.world_tick,
                   last_event_sequence=last, census_ticks=audit.census_ticks + 1,
                   transcript_sha256=_digest_step(audit.transcript_sha256, census))