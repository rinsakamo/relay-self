"""Synthetic NBT negatives. No Paper World or protected original rewritten."""
from __future__ import annotations

import gzip
import struct

import pytest

from experiments.standard_env import v7_m02_world_nbt_audit as audit


def pack(fmt, val):
    return struct.pack(">" + fmt, val)


def tag(kind: int, name: str, value: bytes) -> bytes:
    key = name.encode()
    return pack("B", kind) + pack("H", len(key)) + key + value


def original(*, seed=61021, spawn=12, duplicate=False,
             world_settings=True, include_spawn=True) -> bytes:
    settings = tag(4, "seed", pack("q", seed)) + b"\x00"
    payload = tag(10, "WorldGenSettings", settings) if world_settings else b""
    if include_spawn:
        payload += (tag(3, "SpawnX", pack("i", spawn))
                    + tag(3, "SpawnY", pack("i", 65))
                    + tag(3, "SpawnZ", pack("i", -8)))
    if duplicate:
        payload += tag(3, "SpawnX", pack("i", spawn))
    payload += tag(4, "Time", pack("q", 0)) + b"\x00"
    root = tag(10, "Data", payload) + b"\x00"
    return gzip.compress(b"\x0a\x00\x00" + root, mtime=0)


def test_read_initial_world_seed_and_saved_spawn_from_nbt_not_properties():
    x = audit.review_level_dat(original())
    assert x["world_seed_from_nbt"] == 61021
    assert x["spawn_xyz_from_nbt"] == {
        "SpawnX": 12, "SpawnY": 65, "SpawnZ": -8,
    }
    assert x["world_time_from_nbt"] == 0
    assert not x["identical_generated_terrain_or_collision_attested"]
    assert not x["changed_plugin_engineering_qualified"]
    assert not x["science_go"]


def test_initial_seed_same_does_not_claim_same_world_or_action_pose():
    sources = {name: original(spawn=12 if name != "BOTH_ZERO" else 99)
               for name in ("BASE_ON", "SHAM_ON", "BASAL_ZERO",
                            "WALK_ZERO", "BOTH_ZERO")}
    x = audit.summarize_worlds(sources)
    assert x["world_nbt_seeds_identical"]
    assert not x["initial_spawns_equal"]
    assert not x["equal_terrain_and_collision_geometry_attested"]
    assert not x["v7_paired_0_005_block_path_admitted"]
    assert x["science_trials_credited"] == 0


def test_missing_spawn_is_unknown_not_zero():
    x = audit.review_level_dat(original(include_spawn=False))
    assert x["spawn_xyz_from_nbt"] is None
    assert x["world_seed_source_shape_attested"]


@pytest.mark.parametrize(("world", "why"), [
    (original(seed=123), "seed"),
    (original(duplicate=True), "duplicate"),
    (original(world_settings=False), "WorldGenSettings"),
    (original()[:-9], "corrupt|truncated"),
    (b"notgzip", "corrupt"),
    (gzip.compress(b"\x00\x00\x00"), "root"),
    (gzip.compress(b"\x0a\x00\x00"), "truncated"),
])
def test_forged_or_corrupt_world_fails_closed(world, why):
    with pytest.raises(audit.InvalidWorld, match=why):
        audit.review_level_dat(world)


def test_all_five_required_and_uncalibrated_world_not_qualified():
    x = {"BASE_ON": original()}
    with pytest.raises(audit.InvalidWorld, match="five"):
        audit.summarize_worlds(x)
    sources = {arm: original()
               for arm in ("BASE_ON", "SHAM_ON", "BASAL_ZERO",
                           "WALK_ZERO", "BOTH_ZERO")}
    res = audit.summarize_worlds(sources)
    assert res["initial_spawns_equal"]
    assert res["identical_world_snapshot_bytes"]
    assert res["r_new_plugin_engineering_qualified"] is False
