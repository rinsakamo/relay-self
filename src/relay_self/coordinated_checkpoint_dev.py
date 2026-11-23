"""#860 DEV: 60-second policy and coarse World + multi-Self checkpoint generations.

This is an offline capture/restore boundary, NOT a live Paper scheduler, a
distributed transaction, semantic owner resurrection, or Action permission.
The caller must stop/quiesce the World and every Self before capture.
"""
from __future__ import annotations

import hashlib
import json
import math
import os
import re
import stat
from dataclasses import dataclass
from pathlib import Path
from typing import Callable

from relay_self.persistent_cognition import load_persistent_cognition
from relay_self.physical_action_journal import PhysicalActionJournal
from relay_self.world_checkpoint_dev import (
    capture_stopped_world,
    restore_world_to_new_branch,
    verify_world_checkpoint,
)


class CoordinatedCheckpointError(ValueError):
    """A generation is incomplete, corrupted, or not safe for DEV recovery."""


@dataclass(frozen=True)
class SelfSnapshotSource:
    self_id: str
    cognition_file: Path
    physical_wal_file: Path
    owner_state_file: Path | None = None  # Opaque until the real owner contract exists.


def _name(value: str) -> str:
    if type(value) is not str or not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_-]{0,79}", value):
        raise CoordinatedCheckpointError("unsafe generation or Self identifier")
    return value


_PAPER_COMPANIONS = ("world_nether", "world_the_end")


def _paper_siblings(source_world: Path) -> tuple[tuple[str, Path], ...]:
    """Only the two standard Paper sibling dimensions in a disposable World."""
    root = Path(source_world).absolute()
    if root.name != "world":
        raise CoordinatedCheckpointError("Paper layout requires the world directory")
    for entry in root.parent.iterdir():
        if (entry.name.startswith("world_")
                and entry.name not in _PAPER_COMPANIONS):
            raise CoordinatedCheckpointError(
                "unrecognized Paper world companion; refuse partial save"
            )
    found: list[tuple[str, Path]] = []
    for name in _PAPER_COMPANIONS:
        sibling = root.parent / name
        if sibling.is_symlink():
            raise CoordinatedCheckpointError("symlink Paper dimension forbidden")
        if sibling.exists():
            if not sibling.is_dir():
                raise CoordinatedCheckpointError("non-directory Paper dimension")
            found.append((name, sibling))
    return tuple(found)


def _hash(path: Path) -> str:
    if path.is_symlink() or not path.is_file():
        raise CoordinatedCheckpointError(f"snapshot file unavailable: {path}")
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _copy_stable(source: Path, destination: Path) -> str:
    source = Path(source)
    if source.is_symlink() or not source.is_file() or destination.exists():
        raise CoordinatedCheckpointError("unsafe source or existing destination")
    fd = os.open(source, os.O_RDONLY | os.O_NOFOLLOW)
    try:
        before = os.fstat(fd)
        if not stat.S_ISREG(before.st_mode):
            raise CoordinatedCheckpointError("non-regular Self state")
        out = os.open(destination, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
        digest = hashlib.sha256()
        try:
            while chunk := os.read(fd, 1024 * 1024):
                digest.update(chunk)
                view = memoryview(chunk)
                while view:
                    written = os.write(out, view)
                    if written <= 0:
                        raise CoordinatedCheckpointError("short Self file write")
                    view = view[written:]
            os.fsync(out)
        finally:
            os.close(out)
        after = os.fstat(fd)
        if (before.st_dev, before.st_ino, before.st_size, before.st_mtime_ns,
                before.st_ctime_ns) != (
                after.st_dev, after.st_ino, after.st_size, after.st_mtime_ns,
                after.st_ctime_ns):
            raise CoordinatedCheckpointError("Self file changed during capture")
        if _hash(destination) != digest.hexdigest():
            raise CoordinatedCheckpointError("Self snapshot copy mismatch")
        return digest.hexdigest()
    finally:
        os.close(fd)


def _new_json(path: Path, payload: dict) -> None:
    data = (json.dumps(payload, sort_keys=True, ensure_ascii=False,
                       separators=(",", ":"), allow_nan=False) + "\n").encode()
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
    try:
        view = memoryview(data)
        while view:
            written = os.write(fd, view)
            if written <= 0:
                raise CoordinatedCheckpointError("short commit marker write")
            view = view[written:]
        os.fsync(fd)
    finally:
        os.close(fd)
    directory_fd = os.open(path.parent, os.O_RDONLY | os.O_DIRECTORY)
    try:
        os.fsync(directory_fd)
    finally:
        os.close(directory_fd)


def capture_generation(
    source_world: Path, store: Path, *,
    sequence: int, expected_self_ids: tuple[str, ...],
    selves: tuple[SelfSnapshotSource, ...],
    world_id: str, branch_id: str, logical_tick: int,
    tick_source_ref: str, stopped_server_ref: str, quiesced_selves_ref: str,
    precommit_validator: Callable[[Path], None] | None = None,
    paper_layout: bool = False,
) -> Path:
    """Capture one externally quiesced cohort; commit marker is written LAST.

    The operator-supplied references do not prove a distributed atomic capture.
    Partial generations are retained but cannot be adopted as checkpoints.
    """
    if type(sequence) is not int or sequence < 0:
        raise CoordinatedCheckpointError("invalid autosave sequence")
    if type(paper_layout) is not bool:
        raise CoordinatedCheckpointError("Paper layout flag must be bool")
    companions = (
        _paper_siblings(source_world) if Path(source_world).name == "world"
        else ()
    )
    if paper_layout and Path(source_world).name != "world":
        raise CoordinatedCheckpointError("Paper layout requires the world directory")
    if not paper_layout and companions:
        raise CoordinatedCheckpointError(
            "Paper sibling dimensions would be omitted without paper_layout"
        )
    if (not expected_self_ids or len(set(expected_self_ids)) != len(expected_self_ids)
            or set(expected_self_ids) != {s.self_id for s in selves}
            or len(selves) != len(expected_self_ids)):
        raise CoordinatedCheckpointError("missing or duplicate Self in roster")
    for self_id in expected_self_ids:
        _name(self_id)
    if not stopped_server_ref or not quiesced_selves_ref:
        raise CoordinatedCheckpointError("externally stopped/quiesced receipts required")
    store = Path(store)
    if store.is_symlink() or not store.is_dir():
        raise CoordinatedCheckpointError("checkpoint store must preexist")
    gen = store / f"g-{sequence:012d}"
    if gen.exists() or gen.is_symlink():
        raise CoordinatedCheckpointError("generation must be new")
    gen.mkdir(mode=0o700)
    archive = gen / "world"
    world = capture_stopped_world(
        source_world, archive, world_id=world_id, branch_id=branch_id,
        checkpoint_id=gen.name, logical_tick=logical_tick,
        tick_source_ref=tick_source_ref, stopped_server_ref=stopped_server_ref,
    )
    paper_records: dict[str, str] = {}
    if paper_layout:
        paper_root = gen / "paper-dimensions"
        paper_root.mkdir(mode=0o700)
        for name, dimension in companions:
            capture_stopped_world(
                dimension, paper_root / name,
                world_id=world_id, branch_id=branch_id,
                checkpoint_id=gen.name, logical_tick=logical_tick,
                tick_source_ref=tick_source_ref,
                stopped_server_ref=stopped_server_ref,
                paper_companion=True,
            )
            paper_records[name] = _hash(paper_root / name / "manifest.json")
    self_dir = gen / "selves"
    self_dir.mkdir(mode=0o700)
    records = {}
    for item in sorted(selves, key=lambda s: s.self_id):
        if load_persistent_cognition(item.cognition_file).identity.self_id != item.self_id:
            raise CoordinatedCheckpointError("foreign Self cognition identity")
        journal = PhysicalActionJournal.restore(
            item.physical_wal_file, self_id=item.self_id,
        )
        if any(row["status"] == "PREPARED_UNRESOLVED" for row in journal.records):
            raise CoordinatedCheckpointError("in-flight physical Action at checkpoint cut")
        target = self_dir / item.self_id
        target.mkdir(mode=0o700)
        files = {
            "cognition.json": item.cognition_file,
            "physical-wal.json": item.physical_wal_file,
        }
        if item.owner_state_file is not None:
            files["owner-state.json"] = item.owner_state_file
        records[item.self_id] = {
            name: _copy_stable(Path(src), target / name)
            for name, src in files.items()
        }
    manifest = {
        "schema": 2 if paper_layout else 1,
        "sequence": sequence, "generation_id": gen.name,
        "world_id": world_id, "branch_id": branch_id,
        "world_manifest_sha256": _hash(archive / "manifest.json"),
        "declared_tick": world["declared_logical_tick"],
        "roster": sorted(expected_self_ids), "selves": records,
        "quiesced_selves_ref": quiesced_selves_ref,
        "small_save_time_skew_accepted": True,
        "atomic_capture_attested": False, "full_self_owner_restored": False,
        "physical_action_issue_authorized": False,
    }
    if paper_layout:
        manifest["paper_dimensions"] = paper_records
    # The complete verified contents precede this exclusive commit marker.
    verify_world_checkpoint(archive)
    if precommit_validator is not None:
        precommit_validator(gen)
    _new_json(gen / "COMMITTED.json", manifest)
    verify_generation(gen)
    return gen


def verify_generation(generation: Path) -> dict:
    """Strict inventory/hash gate; no replay, owner mutation, or issue grant."""
    root = Path(generation)
    if root.is_symlink() or not root.is_dir():
        raise CoordinatedCheckpointError("generation unavailable")
    entries = set(p.name for p in root.iterdir())
    if entries not in (
        {"world", "selves", "COMMITTED.json"},
        {"world", "paper-dimensions", "selves", "COMMITTED.json"},
    ):
        raise CoordinatedCheckpointError("uncommitted or unexpected generation entries")
    marker = root / "COMMITTED.json"
    if marker.is_symlink():
        raise CoordinatedCheckpointError("symlink commit marker")
    try:
        body = json.loads(marker.read_bytes())
    except (OSError, ValueError) as exc:
        raise CoordinatedCheckpointError("invalid generation marker") from exc
    required = {
        "schema", "sequence", "generation_id", "world_id", "branch_id",
        "world_manifest_sha256", "declared_tick", "roster", "selves",
        "quiesced_selves_ref", "small_save_time_skew_accepted",
        "atomic_capture_attested", "full_self_owner_restored",
        "physical_action_issue_authorized",
    }
    if type(body) is not dict:
        raise CoordinatedCheckpointError("invalid generation metadata")
    schema = body.get("schema")
    if schema == 2:
        required.add("paper_dimensions")
    if (set(body) != required
            or schema not in (1, 2)
            or (schema == 2) != ("paper-dimensions" in entries)
            or body["generation_id"] != root.name
            or type(body["sequence"]) is not int or body["sequence"] < 0
            or root.name != f'g-{body["sequence"]:012d}'
            or body["atomic_capture_attested"] is not False
            or body["physical_action_issue_authorized"] is not False
            or body["full_self_owner_restored"] is not False
            or body["small_save_time_skew_accepted"] is not True):
        raise CoordinatedCheckpointError("invalid generation metadata")
    manifest = verify_world_checkpoint(root / "world")
    if manifest["schema"] != 1:
        raise CoordinatedCheckpointError("main Paper World must retain level.dat schema")
    if (body["world_id"] != manifest["world_id"]
            or body["branch_id"] != manifest["branch_id"]
            or body["declared_tick"] != manifest["declared_logical_tick"]
            or body["world_manifest_sha256"] != _hash(root / "world" / "manifest.json")):
        raise CoordinatedCheckpointError("World does not belong to generation")
    if schema == 2:
        dimensions = body["paper_dimensions"]
        root_dims = root / "paper-dimensions"
        if (
            type(dimensions) is not dict
            or set(dimensions) - set(_PAPER_COMPANIONS)
            or root_dims.is_symlink()
            or not root_dims.is_dir()
            or set(p.name for p in root_dims.iterdir()) != set(dimensions)
        ):
            raise CoordinatedCheckpointError("Paper dimensions not complete")
        for name, digest in dimensions.items():
            archive = root_dims / name
            if (
                type(digest) is not str
                or len(digest) != 64
                or any(x not in "0123456789abcdef" for x in digest)
                or _hash(archive / "manifest.json") != digest
            ):
                raise CoordinatedCheckpointError("Paper dimension checksum mismatch")
            other = verify_world_checkpoint(archive)
            if (
                other["schema"] != 2
                or other["world_file_role"] != "PAPER_COMPANION"
            ):
                raise CoordinatedCheckpointError(
                    "Paper companion must have a role-qualified archive"
                )
            if any(other[key] != manifest[key] for key in (
                "world_id", "branch_id", "checkpoint_id", "declared_logical_tick",
                "tick_source_ref", "stopped_server_ref",
            )):
                raise CoordinatedCheckpointError("Paper dimension generation mismatch")
    roster = body["roster"]
    if type(body["selves"]) is not dict:
        raise CoordinatedCheckpointError("invalid Self manifest")
    if (type(roster) is not list or not roster or roster != sorted(set(roster))
            or not all(type(x) is str for x in roster)
            or set(body["selves"]) != set(roster)):
        raise CoordinatedCheckpointError("Self roster mismatch")
    root_selves = root / "selves"
    if root_selves.is_symlink() or set(p.name for p in root_selves.iterdir()) != set(roster):
        raise CoordinatedCheckpointError("Self inventory mismatch")
    for sid in roster:
        _name(sid)
        d = root_selves / sid
        files = body["selves"][sid]
        if (d.is_symlink() or type(files) is not dict
                or not {"cognition.json", "physical-wal.json"} <= set(files)
                or set(files) - {"cognition.json", "physical-wal.json", "owner-state.json"}
                or set(p.name for p in d.iterdir()) != set(files)):
            raise CoordinatedCheckpointError("unexpected Self file inventory")
        for filename, digest in files.items():
            if type(digest) is not str or _hash(d / filename) != digest:
                raise CoordinatedCheckpointError("Self snapshot checksum mismatch")
    return body


def latest_verified_generation(store: Path) -> Path | None:
    """Newest usable committed generation; skip partial/corrupt generations."""
    root = Path(store)
    for generation in sorted(root.glob("g-*"), reverse=True):
        try:
            verify_generation(generation)
        except (CoordinatedCheckpointError, ValueError, OSError):
            continue
        return generation
    return None


def restore_generation(
    generation: Path, destination: Path, *, restore_id: str,
) -> dict:
    """Create NEW fork World + Self file copies; owners remain uninitialized."""
    body = verify_generation(generation)
    dest = Path(destination)
    if dest.exists() or dest.is_symlink() or not dest.parent.is_dir():
        raise CoordinatedCheckpointError("restore destination must be new")
    dest.mkdir(mode=0o700)
    receipt = restore_world_to_new_branch(
        Path(generation) / "world", dest / "world", restore_id=restore_id,
    )
    if body["schema"] == 2:
        for name in body["paper_dimensions"]:
            companion = restore_world_to_new_branch(
                Path(generation) / "paper-dimensions" / name,
                dest / name, restore_id=restore_id + "-" + name,
                new_branch_id=receipt["new_branch_id"],
            )
            if (
                companion["new_branch_id"] != receipt["new_branch_id"]
                or companion["source_checkpoint_id"] != body["generation_id"]
            ):
                raise CoordinatedCheckpointError("Paper dimension fork mismatch")
    recovered = dest / "selves"
    recovered.mkdir(mode=0o700)
    for sid in body["roster"]:
        (recovered / sid).mkdir(mode=0o700)
        for filename, digest in body["selves"][sid].items():
            got = _copy_stable(
                Path(generation) / "selves" / sid / filename,
                recovered / sid / filename,
            )
            if got != digest:
                raise CoordinatedCheckpointError("restored Self digest mismatch")
    result = {
        "generation_id": body["generation_id"],
        "fork_branch_id": receipt["new_branch_id"],
        "self_ids": body["roster"],
        "replay_performed": False, "post_checkpoint_state_discarded": True,
        "physical_action_issue_authorized": False,
        "full_self_owner_restored": False,
    }
    _new_json(dest / "RESTORE_PREPARED.json", result)
    return result


class AutosaveGate:
    """Pollable 60-second DEV policy. No background task/server control."""

    interval_seconds = 60.0

    def __init__(self) -> None:
        self.last_success_monotonic: float | None = None

    def due(self, now_monotonic: float) -> bool:
        if (type(now_monotonic) not in (int, float)
                or not math.isfinite(now_monotonic) or now_monotonic < 0):
            raise CoordinatedCheckpointError("invalid monotonic clock")
        return (self.last_success_monotonic is None
                or now_monotonic - self.last_success_monotonic >= self.interval_seconds)

    def run_if_due(
        self, now_monotonic: float, capture: Callable[[], Path],
    ) -> Path | None:
        if not self.due(now_monotonic):
            return None
        # A callback returning is insufficient: independently check COMMITTED.
        candidate = Path(capture())
        verify_generation(candidate)
        self.last_success_monotonic = now_monotonic
        return candidate
