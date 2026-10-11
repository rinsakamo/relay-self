"""RSEE 1.0 immutable operator-supplied stopped-World byte binding.

This module never launches Java, Mineflayer, a provider or Minecraft.
It cannot attest that a stopped snapshot was physically acquired: its
manifest and source observations remain operator-supplied evidence.
"""
from __future__ import annotations

import gzip
import hashlib
import json
import shutil
import stat
import struct
from dataclasses import dataclass
from pathlib import Path, PurePosixPath

VERSION = "1.21.8"
SEED = 575
LEVEL = "s31a-ephemeral"
JAR_SHA256 = "2349d9a8f0d4be2c40e7692890ef46a4b07015e7955b075460d02793be7fbbe7"
SCHEMA = "RSEE_STOPPED_WORLD_BYTES_V1"
MAX_MANIFEST = 1024 * 1024
MAX_LEVEL = 16 * 1024 * 1024
MAX_FILES = 4096
MAX_TOTAL = 4 * 1024 * 1024 * 1024


class WorldBindingRejected(ValueError):
    """Unproven or mismatched World bytes; never substitute a new World."""


@dataclass(frozen=True, slots=True)
class WorldBinding:
    jar: Path
    snapshot: Path
    manifest: Path
    initial_evidence: Path
    files: tuple[tuple[str, int, str], ...]
    jar_sha256: str
    manifest_sha256: str
    initial_evidence_sha256: str


def _hash_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _regular(path: Path) -> Path:
    if path.is_symlink() or not path.is_file():
        raise WorldBindingRejected("artifact must be a local regular non-symlink file")
    if not stat.S_ISREG(path.lstat().st_mode):
        raise WorldBindingRejected("artifact type rejected")
    return path.resolve(strict=True)


def _json_unique(pairs):
    data = {}
    for key, value in pairs:
        if key in data:
            raise WorldBindingRejected("duplicate JSON key")
        data[key] = value
    return data


def _load_json(path: Path) -> dict:
    source = _regular(path)
    if source.stat().st_size > MAX_MANIFEST:
        raise WorldBindingRejected("World evidence manifest exceeds size bound")
    try:
        value = json.loads(source.read_text("utf-8"), object_pairs_hook=_json_unique)
    except (UnicodeError, ValueError, OSError) as exc:
        raise WorldBindingRejected("invalid World evidence manifest") from exc
    if type(value) is not dict:
        raise WorldBindingRejected("World manifest must be an object")
    return value


class _NBTLong(int):
    """Preserve native TAG_Long identity rather than accepting TAG_Int seed."""


class _NBT:
    """Bounded NBT reader: read the *stored* Data.WorldGenSettings.seed."""

    def __init__(self, raw: bytes):
        self.data = memoryview(raw)
        self.pos = 0

    def take(self, length: int) -> bytes:
        if length < 0 or self.pos + length > len(self.data):
            raise WorldBindingRejected("malformed Minecraft level.dat NBT")
        result = bytes(self.data[self.pos:self.pos + length])
        self.pos += length
        return result

    def number(self, fmt: str) -> int | float:
        return struct.unpack(">" + fmt, self.take(struct.calcsize(fmt)))[0]

    def name(self) -> str:
        size = self.number("H")
        return self.take(size).decode("utf-8")

    def value(self, tag: int, depth: int = 0):
        if depth > 64:
            raise WorldBindingRejected("NBT nesting excessive")
        if tag == 1:
            return self.number("b")
        if tag == 2:
            return self.number("h")
        if tag == 3:
            return self.number("i")
        if tag == 4:
            return _NBTLong(self.number("q"))
        if tag == 5:
            return self.number("f")
        if tag == 6:
            return self.number("d")
        if tag in (7, 11, 12):
            length = self.number("i")
            width = {7: 1, 11: 4, 12: 8}[tag]
            return self.take(length * width)
        if tag == 8:
            return self.name()
        if tag == 9:
            member, count = self.number("B"), self.number("i")
            if count < 0 or count > 100_000 or (member == 0 and count):
                raise WorldBindingRejected("NBT list invalid")
            return [self.value(member, depth + 1) for _ in range(count)]
        if tag == 10:
            contents = {}
            while True:
                kind = self.number("B")
                if kind == 0:
                    return contents
                key = self.name()
                if key in contents:
                    raise WorldBindingRejected("NBT duplicate compound key")
                contents[key] = self.value(kind, depth + 1)
        raise WorldBindingRejected("unsupported NBT tag")


def _seed_from_level(path: Path) -> int:
    source = _regular(path)
    try:
        with gzip.open(source, "rb") as handle:
            raw = handle.read(MAX_LEVEL + 1)
        if len(raw) > MAX_LEVEL:
            raise WorldBindingRejected("level.dat uncompressed size exceeded")
        reader = _NBT(raw)
        if reader.number("B") != 10:
            raise WorldBindingRejected("level.dat root must be compound")
        reader.name()
        data = reader.value(10)
        if reader.pos != len(raw):
            raise WorldBindingRejected("level.dat contains trailing bytes")
        root = data["Data"]["WorldGenSettings"]["seed"]
        if type(root) is not _NBTLong:
            raise WorldBindingRejected("World seed is not a native long")
        return root
    except (OSError, EOFError, KeyError, TypeError, UnicodeError, struct.error) as exc:
        raise WorldBindingRejected("cannot establish native level.dat seed") from exc


def _world_files(root: Path) -> tuple[tuple[str, int, str], ...]:
    if root.is_symlink() or not root.is_dir():
        raise WorldBindingRejected("snapshot root missing or symlinked")
    rows = []
    total = 0
    for path in root.rglob("*"):
        if path.is_symlink() or not (path.is_file() or path.is_dir()):
            raise WorldBindingRejected("snapshot has symlink or special file")
        if path.is_dir():
            continue
        if not stat.S_ISREG(path.lstat().st_mode):
            raise WorldBindingRejected("snapshot has nonregular file")
        rel = path.relative_to(root).as_posix()
        relative = PurePosixPath(rel)
        if (not relative.parts or rel.startswith("/") or "\\" in rel
                or any(part in (".", "..") for part in relative.parts)):
            raise WorldBindingRejected("invalid snapshot relative path")
        size = path.stat().st_size
        total += size
        if size > MAX_TOTAL or total > MAX_TOTAL or len(rows) >= MAX_FILES:
            raise WorldBindingRejected("World snapshot too large")
        rows.append((rel, size, _hash_file(path)))
    rows.sort()
    if "level.dat" not in {row[0] for row in rows}:
        raise WorldBindingRejected("native level.dat missing")
    return tuple(rows)


def verify_world_binding(
    jar: Path,
    snapshot: Path,
    manifest: Path,
    initial_evidence: Path,
    *,
    expected_jar_sha256: str = JAR_SHA256,
) -> WorldBinding:
    """Fail closed on every supplied byte; never certify source provenance."""
    try:
        jar = _regular(jar)
        manifest = _regular(manifest)
        initial_evidence = _regular(initial_evidence)
        if snapshot.is_symlink() or not snapshot.is_dir():
            raise WorldBindingRejected("World snapshot directory invalid")
        snapshot = snapshot.resolve(strict=True)
        data = _load_json(manifest)
        if set(data) != {
            "schema", "minecraft_version", "level_name", "seed",
            "jar_sha256", "initial_evidence_sha256", "files",
        } or (data["schema"] != SCHEMA or data["minecraft_version"] != VERSION
              or data["level_name"] != LEVEL
              or type(data["seed"]) is not int or data["seed"] != SEED):
            raise WorldBindingRejected("World binding contract not exact")
        digest = _hash_file(jar)
        if digest != expected_jar_sha256 or data["jar_sha256"] != digest:
            raise WorldBindingRejected("actual Minecraft jar SHA256 mismatch")
        observation_digest = _hash_file(initial_evidence)
        if data["initial_evidence_sha256"] != observation_digest:
            raise WorldBindingRejected("initial observation byte identity mismatch")
        if _seed_from_level(snapshot / "level.dat") != SEED:
            raise WorldBindingRejected("native level.dat seed mismatch")
        files = _world_files(snapshot)
        rows = data["files"]
        if (not isinstance(rows, list) or len(rows) != len(files)
                or any(type(row) is not dict or set(row) != {"path", "size", "sha256"}
                       for row in rows)
                or tuple((row["path"], row["size"], row["sha256"]) for row in rows)
                != files):
            raise WorldBindingRejected("World snapshot manifest mismatch")
        return WorldBinding(
            jar, snapshot, manifest, initial_evidence, files, digest,
            _hash_file(manifest), observation_digest,
        )
    except (OSError, UnicodeError, TypeError, AttributeError) as exc:
        raise WorldBindingRejected("World artifact binding failed") from exc


def prepare_stopped_world(root: Path, binding: WorldBinding, *, eula_accepted: bool) -> dict:
    """Copy checked bytes only into a new temporary World; never start Java.

    Original snapshot is always read-only. Reverify source and copied World
    to catch stale/tampered bytes across validation and staging.
    """
    if eula_accepted is not True:
        raise WorldBindingRejected("separate disposable-Minecraft EULA assent required")
    if root.is_symlink() or not root.is_dir():
        raise WorldBindingRejected("new owned disposable root required")
    jar_dest = root / "minecraft.jar"
    world_dest = root / LEVEL
    if (jar_dest.exists() or jar_dest.is_symlink()
            or world_dest.exists() or world_dest.is_symlink()
            or (root / "server.properties").exists()
            or (root / "eula.txt").exists()):
        raise WorldBindingRejected("World destination already used")
    verified = verify_world_binding(
        binding.jar, binding.snapshot, binding.manifest, binding.initial_evidence,
        expected_jar_sha256=binding.jar_sha256,
    )
    if verified != binding:
        raise WorldBindingRejected("source World binding changed after admission")
    shutil.copyfile(binding.jar, jar_dest)
    shutil.copytree(binding.snapshot, world_dest, symlinks=False)
    if _hash_file(jar_dest) != binding.jar_sha256 or _world_files(world_dest) != binding.files:
        raise WorldBindingRejected("restored World differs from source bytes")
    if _seed_from_level(world_dest / "level.dat") != SEED:
        raise WorldBindingRejected("restored native World seed differs")
    # Reuse the frozen S31A Minecraft settings; only explicitly bind the seed.
    from adapters.mineflayer.s31a_real_server_ci import _write_config

    _write_config(root)
    props = root / "server.properties"
    text = props.read_text("utf-8")
    if text.count("level-name=") != 1 or "level-name=" + LEVEL + "\n" not in text:
        raise WorldBindingRejected("unexpected Minecraft world name configuration")
    if "level-seed=" in text:
        raise WorldBindingRejected("existing seed override")
    props.write_text(text + f"level-seed={SEED}\n", encoding="utf-8")
    return {
        "source": "RSEE_OPERATOR_SUPPLIED_STOPPED_SNAPSHOT",
        "manifest_sha256": binding.manifest_sha256,
        "initial_evidence_sha256": binding.initial_evidence_sha256,
        "jar_sha256": binding.jar_sha256,
        "world_files": len(binding.files),
        "seed_native_level_dat": SEED,
        "snapshot_bytes_verified": True,
        "native_initial_world_attested": False,
        "world_launched": False,
        "physical_execution_authorized": False,
    }
