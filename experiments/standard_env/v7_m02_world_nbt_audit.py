"""Independent R read-only Paper 1.21.8 level.dat NBT World identity.

A save snapshot proves only the serialized seed/spawn at its save phase. It
does NOT prove equal generated blocks/collisions or a shared Action origin.
No server launch, grant use, or engineering/scientific qualification.
"""
from __future__ import annotations

import gzip
import hashlib
import io
import math
import struct
from typing import Any

MAX_GZIP = 4 * 1024 * 1024
MAX_NBT = 16 * 1024 * 1024
MAX_LIST = 100_000
MAX_DEPTH = 32
CLASS = "RSEE_V7_PAPER_LEVEL_DAT_WORLD_IDENTITY_SOURCE_REVIEW_ONLY"


class InvalidWorld(ValueError):
    pass


def required(ok: bool, why: str) -> None:
    if not ok:
        raise InvalidWorld(why)


class Reader:
    def __init__(self, raw: bytes):
        self.file = io.BytesIO(raw)

    def take(self, n: int) -> bytes:
        required(type(n) is int and 0 <= n <= MAX_NBT, "invalid NBT byte count")
        b = self.file.read(n)
        required(len(b) == n, "truncated NBT source")
        return b

    def unpack(self, fmt: str) -> Any:
        return struct.unpack(">" + fmt, self.take(struct.calcsize(">" + fmt)))[0]

    def name(self) -> str:
        n = self.unpack("H")
        required(n <= 4096, "unbounded NBT name")
        try:
            return self.take(n).decode("utf-8")
        except UnicodeError as exc:
            raise InvalidWorld("non-UTF8 NBT field name") from exc

    def read(self, tag: int, depth: int = 0) -> Any:
        required(1 <= tag <= 12 and depth <= MAX_DEPTH, "foreign/deep NBT tag")
        fixed = {1: "b", 2: "h", 3: "i", 4: "q", 5: "f", 6: "d"}
        if tag in fixed:
            value = self.unpack(fixed[tag])
            required(not isinstance(value, float) or math.isfinite(value),
                     "nonfinite NBT field")
            return value
        if tag == 8:
            return self.name()
        if tag in (7, 11, 12):
            count = self.unpack("i")
            size = {7: 1, 11: 4, 12: 8}[tag]
            required(0 <= count <= MAX_LIST and count * size <= MAX_NBT,
                     "invalid NBT array size")
            raw = self.take(count * size)
            # Hash the raw bytes for opaque non-identity arrays.
            return ("ARRAY", tag, count, hashlib.sha256(raw).hexdigest())
        if tag == 9:
            element = self.unpack("B")
            count = self.unpack("i")
            required(0 <= count <= MAX_LIST and (count == 0 or 1 <= element <= 12),
                     "invalid NBT list shape")
            return [self.read(element, depth + 1) for _ in range(count)]
        if tag == 10:
            result: dict[str, Any] = {}
            while True:
                element = self.unpack("B")
                if element == 0:
                    return result
                required(1 <= element <= 12, "foreign NBT compound entry")
                name = self.name()
                required(name not in result, "duplicate NBT compound field")
                result[name] = self.read(element, depth + 1)


def review_level_dat(original: bytes, expected_seed: int = 61021) -> dict[str, Any]:
    required(type(original) is bytes and 0 < len(original) <= MAX_GZIP,
             "missing/oversized initial World source")
    required(type(expected_seed) is int and expected_seed >= 0,
             "invalid expected seed")
    # Bounded streaming decompression; gzip.decompress has no output cap.
    decompressor = gzip.GzipFile(fileobj=io.BytesIO(original), mode="rb")
    try:
        raw = decompressor.read(MAX_NBT + 1)
        required(len(raw) <= MAX_NBT, "unbounded World NBT decompression")
        required(decompressor.read(1) == b"", "excess World NBT")
        decompressor.close()
    except (OSError, EOFError) as exc:
        raise InvalidWorld("corrupt compressed initial World") from exc
    stream = Reader(raw)
    required(stream.unpack("B") == 10, "NBT root must be compound")
    required(stream.name() == "", "unexpected named NBT root")
    root = stream.read(10)
    required(stream.file.tell() == len(raw), "trailing or foreign NBT content")
    required(type(root) is dict and type(root.get("Data")) is dict,
             "no root Data compound")
    data = root["Data"]
    settings = data.get("WorldGenSettings")
    required(type(settings) is dict, "WorldGenSettings missing")
    seed = settings.get("seed")
    required(type(seed) is int and seed == expected_seed,
             "initial World NBT seed differs from requested value")
    spawn_fields = ("SpawnX", "SpawnY", "SpawnZ")
    spawn = {}
    for name in spawn_fields:
        v = data.get(name)
        # Some valid initial versions defer spawn generation; preserve missing.
        if v is not None:
            required(type(v) is int, "invalid NBT spawn coordinate")
            spawn[name] = v
    return {
        "classification": CLASS,
        "original_level_dat_sha256": hashlib.sha256(original).hexdigest(),
        "world_seed_from_nbt": seed,
        "spawn_xyz_from_nbt": spawn if len(spawn) == 3 else None,
        "world_time_from_nbt": data.get("Time") if type(data.get("Time")) is int else None,
        "nbt_root_fields_read": len(data),
        "world_seed_source_shape_attested": True,
        "identical_generated_terrain_or_collision_attested": False,
        "identical_agent_spawn_pose_attested": False,
        "s50_action_tick_bracket_attested": False,
        "changed_plugin_engineering_qualified": False,
        "science_trials_credited": 0,
        "science_go": False,
    }


def summarize_worlds(originals: dict[str, bytes]) -> dict[str, Any]:
    expected = {"BASE_ON", "SHAM_ON", "BASAL_ZERO", "WALK_ZERO", "BOTH_ZERO"}
    required(type(originals) is dict and set(originals) == expected,
             "five original World arms required")
    rows = {arm: review_level_dat(originals[arm]) for arm in sorted(expected)}
    found = [x["spawn_xyz_from_nbt"] for x in rows.values()]
    return {
        "classification": "RSEE_V7_FIVE_NBT_SEEDS_REVIEW_ONLY",
        "world_nbt_seeds_identical": True,
        "initial_spawns_all_present": all(x is not None for x in found),
        "initial_spawns_equal": all(x is not None for x in found)
        and all(x == found[0] for x in found),
        "identical_world_snapshot_bytes": len(
            {x["original_level_dat_sha256"] for x in rows.values()}) == 1,
        "equal_terrain_and_collision_geometry_attested": False,
        "r_new_plugin_engineering_qualified": False,
        "science_trials_credited": 0,
        "v7_paired_0_005_block_path_admitted": False,
        "arms": rows,
    }
