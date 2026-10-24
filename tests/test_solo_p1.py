"""P1-C deterministic Solo World evidence-shape negatives, no Minecraft run."""
from __future__ import annotations

import json
from dataclasses import replace
from pathlib import Path

import pytest

from experiments.solo_p1 import (
    Entity,
    EntityEvent,
    ServerCensus,
    SoloRejected,
    advance,
    begin,
    load_profile,
    parse_profile,
)

_PROFILE = (Path(__file__).resolve().parents[1] /
            "experiments/config/p1_solo_no_agents_v1.json")


@pytest.fixture
def profile():
    return load_profile(_PROFILE)


def census(profile, tick=100, **kwargs):
    fields = {
        "session_id": "test-original-source-session", "world_tick": tick,
        "dimension": profile.dimension, "self_player_id": profile.self_player_id,
        "source_scope": "server_all_loaded_chunks_and_entity_lifecycle",
        "source_original_sha256": "a" * 64,
        "server_settings_readback": profile.server_settings,
        "gamerules_readback": profile.gamerules,
        "loaded_chunks": ("0,0", "0,1"),
        "scanned_chunks": ("0,1", "0,0"),
        "connected_players": (profile.self_player_id,),
        "entities": (Entity(profile.self_player_id, "minecraft:player"),),
        "lifecycle_events": (),
        "all_loaded_chunks_included": True,
        "lifecycle_stream_contiguous": True,
        "original_source_independently_verified": True,
    }
    fields.update(kwargs)
    return ServerCensus(**fields)


def assert_class(exc, classification):
    assert isinstance(exc.value, SoloRejected)
    assert exc.value.classification == classification


def test_profile_is_immutably_offline_and_versioned(profile):
    assert profile.minecraft_version == "1.21.8"
    assert profile.science_qualified is False
    assert profile.world_mode == "R_S_ISOLATED_DISPOSABLE"
    assert all(not value for _, value in profile.gamerules)
    assert all(not value for _, value in profile.server_settings)
    assert len(profile.sha256) == 64
    assert profile == parse_profile(json.loads(_PROFILE.read_text(encoding="utf-8")))


def test_empty_solo_and_nonagent_items_and_terrain_are_allowed(profile):
    item = Entity("drop#1", "minecraft:item")
    falling = Entity("falling#1", "minecraft:falling_block")
    first = census(profile)
    prior = begin(profile, first)
    assert prior.classification == "SOLO_OFFLINE_SHAPE_PASS_NOT_QUALIFIED"
    assert prior.census_ticks == 1
    next_frame = census(profile, 101, entities=(
        Entity("RelaySelf", "minecraft:player"), item, falling,
    ), lifecycle_events=(EntityEvent(0, "SPAWN", item),))
    after = advance(profile, prior, next_frame)
    assert after.last_event_sequence == 0
    assert after.census_ticks == 2
    assert after.transcript_sha256 != prior.transcript_sha256
    assert after == advance(profile, prior, next_frame)
    assert after.classification.endswith("NOT_QUALIFIED")


@pytest.mark.parametrize("kind", [
    "minecraft:zombie", "minecraft:cow", "minecraft:sheep",
    "minecraft:villager", "minecraft:wandering_trader", "minecraft:cat",
    "minecraft:bee", "minecraft:iron_golem", "minecraft:bat",
    "minecraft:creeper", "minecraft:other_future_ai", "modded:new_ai",
])
def test_hostile_passive_npc_and_unknown_agents_invalidate_solo(profile, kind):
    frame = census(profile, entities=(
        Entity("RelaySelf", "minecraft:player"), Entity("entity2", kind),
    ))
    with pytest.raises(SoloRejected) as exc:
        begin(profile, frame)
    assert_class(exc, "SOLO_PROFILE_INVALID")


def test_other_human_or_bot_player_is_an_agent(profile):
    other = Entity("unrelated-human", "minecraft:player")
    with pytest.raises(SoloRejected) as exc:
        begin(profile, census(profile, entities=(
            Entity("RelaySelf", "minecraft:player"), other,
        ), connected_players=("RelaySelf", "unrelated-human")))
    assert_class(exc, "SOLO_PROFILE_INVALID")
    with pytest.raises(SoloRejected) as exc2:
        begin(profile, census(profile, connected_players=("RelaySelf", "unknown")))
    assert_class(exc2, "SOLO_PROFILE_INVALID")
    with pytest.raises(SoloRejected) as exc3:
        begin(profile, census(profile, connected_players=()))
    assert_class(exc3, "SOLO_SOURCE_UNQUALIFIED")


def test_ephemeral_spawn_then_despawn_within_one_tick_still_fails(profile):
    state = begin(profile, census(profile))
    enemy = Entity("z1", "minecraft:zombie")
    # The final census is empty but a trusted lifecycle would see the intruder.
    hidden = census(profile, 101, lifecycle_events=(
        EntityEvent(0, "SPAWN", enemy), EntityEvent(1, "DESPAWN", enemy),
    ))
    with pytest.raises(SoloRejected) as exc:
        advance(profile, state, hidden)
    assert_class(exc, "SOLO_PROFILE_INVALID")


@pytest.mark.parametrize("changes", [
    {"source_scope": "mineflayer_entity_registry"},
    {"source_original_sha256": "a" * 63},
    {"source_original_sha256": "Z" * 64},
    {"all_loaded_chunks_included": False},
    {"lifecycle_stream_contiguous": False},
    {"original_source_independently_verified": False},
    {"loaded_chunks": ()},
    {"scanned_chunks": ("0,0",)},
    {"scanned_chunks": ("0,0", "0,0", "0,1")},
    {"loaded_chunks": ("0,0", "0,0")},
    {"dimension": "minecraft:the_nether"},
    {"world_tick": -1},
    {"self_player_id": "another-bot"},
])
def test_incomplete_nonserver_or_inconsistent_source_is_unqualified(profile, changes):
    with pytest.raises(SoloRejected) as exc:
        begin(profile, census(profile, **changes))
    assert_class(exc, "SOLO_SOURCE_UNQUALIFIED")


def test_spawn_controls_must_be_verified_not_just_written_in_profile(profile):
    missing = (("spawn-monsters", True),)
    with pytest.raises(SoloRejected) as exc:
        begin(profile, census(profile, server_settings_readback=missing))
    assert_class(exc, "SOLO_SOURCE_UNQUALIFIED")
    with pytest.raises(SoloRejected):
        begin(profile, census(profile, gamerules_readback=()))


def test_absent_or_duplicated_census_entity_invalid(profile):
    with pytest.raises(SoloRejected):
        begin(profile, census(profile, entities=()))
    self_ent = Entity("RelaySelf", "minecraft:player")
    with pytest.raises(SoloRejected):
        begin(profile, census(profile, entities=(self_ent, self_ent)))
    with pytest.raises(SoloRejected):
        begin(profile, census(profile, entities=(self_ent, Entity("x", "Bad Format"))))


def test_monotonic_tick_and_event_sequence_are_not_action_counts(profile):
    first = begin(profile, census(profile, 40))
    for tick in (40, 42, -1, True):
        with pytest.raises(SoloRejected):
            advance(profile, first, census(profile, tick))
    e = Entity("event1", "minecraft:item")
    good = census(profile, 41, lifecycle_events=(EntityEvent(0, "SPAWN", e),))
    next_state = advance(profile, first, good)
    assert next_state.last_event_sequence == 0
    for seq in (0, 2, -1, True):
        with pytest.raises(SoloRejected):
            advance(profile, next_state, census(profile, 42, lifecycle_events=(
                EntityEvent(seq, "SPAWN", e),
            )))
    assert advance(profile, next_state, census(profile, 42)).last_event_sequence == 0


def test_session_and_profile_fences(profile):
    state = begin(profile, census(profile))
    with pytest.raises(SoloRejected):
        advance(profile, state, census(profile, 101, session_id="wrong"))
    new_profile = replace(profile, profile_id="new-solo-profile")
    with pytest.raises(SoloRejected):
        advance(new_profile, state, census(new_profile, 101))
    assert profile.sha256 != new_profile.sha256


def test_profile_strict_keys_whitelist_and_all_spawn_controls(profile, tmp_path):
    plain = json.loads(_PROFILE.read_text(encoding="utf-8"))
    cases = []
    variant = dict(plain)
    variant["science_qualified"] = True
    cases.append(variant)
    variant = dict(plain)
    variant["world_mode"] = "ALREADY_QUALIFIED"
    cases.append(variant)
    variant = dict(plain)
    variant["extra"] = 1
    cases.append(variant)
    variant = dict(plain)
    variant.pop("dimension")
    cases.append(variant)
    variant = json.loads(json.dumps(plain))
    variant["server_settings"]["spawn-monsters"] = True
    cases.append(variant)
    variant = json.loads(json.dumps(plain))
    variant["gamerules"]["doMobSpawning"] = True
    cases.append(variant)
    variant = json.loads(json.dumps(plain))
    variant["gamerules"]["doPatrolSpawning"] = 0
    cases.append(variant)
    variant = json.loads(json.dumps(plain))
    variant["gamerules"]["doWardenSpawning"] = True
    cases.append(variant)
    variant = json.loads(json.dumps(plain))
    variant["inert_entity_types"].append("minecraft:cow")
    cases.append(variant)
    variant = json.loads(json.dumps(plain))
    variant["minecraft_version"] = "1.21.9"
    cases.append(variant)
    variant = json.loads(json.dumps(plain))
    variant["server_settings"]["spawn-animals"] = False
    cases.append(variant)
    for invalid in cases:
        with pytest.raises(SoloRejected):
            parse_profile(invalid)
    file = tmp_path / "bad.json"
    file.write_text('{"version":"one","version":"two"}', encoding="utf-8")
    with pytest.raises(SoloRejected):
        load_profile(file)
    file.write_text("{" + '"value":NaN}', encoding="utf-8")
    with pytest.raises(SoloRejected):
        load_profile(file)


def test_legacy_mineflayer_radius_and_zombie_regression_remain_separate(profile):
    # S native nearby_entities_coverage: <= 16m/16 candidate entities, not
    # authoritative across all loaded chunks or per-tick spawn/despawn.
    with pytest.raises(SoloRejected):
        begin(profile, census(profile, source_scope="mineflayer_entity_registry"))
    # The existing S49 zombie fixture stays valid as *engineering* regression;
    # it cannot be used as a solo-science profile.
    with pytest.raises(SoloRejected) as exc:
        begin(profile, census(profile, entities=(
            Entity("RelaySelf", "minecraft:player"),
            Entity("zombie-id", "minecraft:zombie"),
        )))
    assert_class(exc, "SOLO_PROFILE_INVALID")