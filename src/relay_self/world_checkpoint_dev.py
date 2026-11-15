"""#853 P0-A: non-destructive stopped-Minecraft-world file checkpoint DEV.

No server control, automatic cleanup, restore-overwrite, physical Action issue,
World/Body semantic authority or distributed World+WAL transaction. The stop
receipt and logical tick are *operator claims*, not verified live evidence.
"""
from __future__ import annotations

import hashlib
import json
import os
import stat
import uuid
from pathlib import Path, PurePosixPath
from typing import Any


class WorldCheckpointError(ValueError):
    """Unsafe, incomplete or inconsistent World file checkpoint."""


def _text(name: str, value: object) -> str:
    if type(value) is not str or not value.strip() or "\n" in value or "\r" in value:
        raise WorldCheckpointError(f"{name} requires nonempty single-line text")
    return value


def _tick(value: object) -> int:
    if type(value) is not int or value < 0:
        raise WorldCheckpointError("nonnegative declared logical tick required")
    return value


def _canon(value: object) -> bytes:
    return (json.dumps(value, sort_keys=True, separators=(",", ":"),
                       ensure_ascii=False, allow_nan=False) + "\n").encode("utf-8")


def _sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _check_optional_manifest_pin(archive: Path, expected: str | None) -> None:
    """Optional out-of-band metadata pin for DEV investigations.

    Without a pin, valid but rewritten Manifest metadata is unverified;
    this is intentional and NOT a production authenticity claim.
    """
    if expected is None:
        return
    if (type(expected) is not str or len(expected) != 64
            or any(ch not in "0123456789abcdef" for ch in expected)):
        raise WorldCheckpointError("expected manifest SHA256 must be lowercase hex")
    if _hash_file(archive / "manifest.json")[0] != expected:
        raise WorldCheckpointError("manifest differs from externally pinned SHA256")


def _hash_file(path: Path) -> tuple[str, int]:
    digest = hashlib.sha256()
    count = 0
    fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW)
    try:
        if not stat.S_ISREG(os.fstat(fd).st_mode):
            raise WorldCheckpointError("hash source must be a regular file")
        while chunk := os.read(fd, 1024 * 1024):
            digest.update(chunk)
            count += len(chunk)
    finally:
        os.close(fd)
    return digest.hexdigest(), count


def _safe_root(path: str | Path, *, must_exist: bool) -> Path:
    original = Path(path)
    if ".." in original.parts:
        raise WorldCheckpointError("parent traversal forbidden")
    p = original.absolute()
    if not p.is_absolute():
        raise WorldCheckpointError("absolute path required")
    # Never silently traverse symlinked source, archive or destination parents.
    for part in (p, *p.parents):
        if part.is_symlink():
            raise WorldCheckpointError("symlink path component forbidden")
    if must_exist and (not p.is_dir() or not stat.S_ISDIR(p.stat().st_mode)):
        raise WorldCheckpointError("pre-existing directory required")
    if not must_exist and (p.exists() or p.is_symlink() or not p.parent.is_dir()):
        raise WorldCheckpointError("new destination with pre-existing parent required")
    return p


def _nonoverlap(a: Path, b: Path) -> None:
    if a == b or a in b.parents or b in a.parents:
        raise WorldCheckpointError("World, archive and destination must not overlap")


def _rel(path: str) -> str:
    p = PurePosixPath(path)
    if (type(path) is not str or not path or path.startswith("/")
            or "\\" in path or "\n" in path or "\r" in path
            or any(x in ("", ".", "..") for x in path.split("/"))
            or p.as_posix() != path):
        raise WorldCheckpointError("unsafe relative World file path")
    return path


def _scan(root: Path, *, require_level_dat: bool = True) -> tuple[str, ...]:
    """Complete, deterministic inventory; refuse links and special files."""
    found: list[str] = []
    for directory, dirs, files in os.walk(root, followlinks=False):
        for name in [*dirs, *files]:
            entry = Path(directory) / name
            mode = entry.lstat().st_mode
            if stat.S_ISLNK(mode):
                raise WorldCheckpointError("symlink in World tree")
            if name in (".", "..") or "\n" in name or "\r" in name:
                raise WorldCheckpointError("unsupported World file name")
            if name in dirs and not stat.S_ISDIR(mode):
                raise WorldCheckpointError("non-directory in directory inventory")
            if name in files and not stat.S_ISREG(mode):
                raise WorldCheckpointError("nonregular World file")
        for name in files:
            found.append(_rel((Path(directory) / name).relative_to(root).as_posix()))
    found.sort()
    if require_level_dat and "level.dat" not in found:
        raise WorldCheckpointError("Minecraft level.dat missing")
    return tuple(found)


def _copy_hashed(source: Path, target: Path) -> tuple[str, int]:
    """Exclusive target creation, source O_NOFOLLOW, fsync and source stability."""
    input_fd = os.open(source, os.O_RDONLY | os.O_NOFOLLOW)
    target_fd = -1
    try:
        before = os.fstat(input_fd)
        if not stat.S_ISREG(before.st_mode):
            raise WorldCheckpointError("source World file not regular")
        target.parent.mkdir(parents=True, exist_ok=True)
        target_fd = os.open(target, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
        hasher = hashlib.sha256()
        size = 0
        while True:
            chunk = os.read(input_fd, 1024 * 1024)
            if not chunk:
                break
            hasher.update(chunk)
            size += len(chunk)
            view = memoryview(chunk)
            while view:
                n = os.write(target_fd, view)
                if n <= 0:
                    raise WorldCheckpointError("short World checkpoint write")
                view = view[n:]
        os.fsync(target_fd)
        after = os.fstat(input_fd)
        if (before.st_dev, before.st_ino, before.st_size, before.st_mtime_ns,
                before.st_ctime_ns) != (
                after.st_dev, after.st_ino, after.st_size, after.st_mtime_ns,
                after.st_ctime_ns) or size != before.st_size:
            raise WorldCheckpointError("World source changed during capture")
        return hasher.hexdigest(), size
    finally:
        os.close(input_fd)
        if target_fd >= 0:
            os.close(target_fd)


def _sync_dir(path: Path) -> None:
    fd = os.open(path, os.O_RDONLY | os.O_DIRECTORY)
    try:
        os.fsync(fd)
    finally:
        os.close(fd)


def _write_new(path: Path, data: bytes) -> None:
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
    try:
        view = memoryview(data)
        while view:
            n = os.write(fd, view)
            if n <= 0:
                raise WorldCheckpointError("short manifest write")
            view = view[n:]
        os.fsync(fd)
    finally:
        os.close(fd)


def _checksums(rows: list[dict[str, Any]]) -> bytes:
    return "".join(f"{row['sha256']}  world/{row['path']}\n" for row in rows).encode("utf-8")


def capture_stopped_world(
    source_world: str | Path,
    archive_dir: str | Path,
    *,
    world_id: str,
    branch_id: str,
    checkpoint_id: str,
    logical_tick: int,
    tick_source_ref: str,
    stopped_server_ref: str,
    paper_companion: bool = False,
) -> dict[str, Any]:
    """Capture a *declared stopped* World to a new archive, leaving originals intact.

    A failure leaves an INCOMPLETE archive for inspection; never silently
    deletes evidence or reuses the partially created directory.
    """
    src = _safe_root(source_world, must_exist=True)
    dest = _safe_root(archive_dir, must_exist=False)
    _nonoverlap(src, dest)
    for name, value in (
        ("world_id", world_id), ("branch_id", branch_id),
        ("checkpoint_id", checkpoint_id),
        ("tick_source_ref", tick_source_ref),
        ("stopped_server_ref", stopped_server_ref),
    ):
        _text(name, value)
    _tick(logical_tick)
    if type(paper_companion) is not bool:
        raise WorldCheckpointError("Paper companion role must be explicit boolean")
    inventory = _scan(src, require_level_dat=not paper_companion)
    if not inventory:
        raise WorldCheckpointError("empty Paper companion cannot be captured")
    dest.mkdir(mode=0o700)
    payload = dest / "world"
    payload.mkdir(mode=0o700)
    rows: list[dict[str, Any]] = []
    for rel in inventory:
        digest, size = _copy_hashed(src / rel, payload / rel)
        rows.append({"path": rel, "sha256": digest, "size": size})
    # Check for added, removed or changed files across the copy window.
    if _scan(src, require_level_dat=not paper_companion) != inventory:
        raise WorldCheckpointError("World inventory changed during capture")
    for row in rows:
        if _hash_file(src / row["path"]) != (row["sha256"], row["size"]):
            raise WorldCheckpointError("World source drift after copy")
        if _hash_file(payload / row["path"]) != (row["sha256"], row["size"]):
            raise WorldCheckpointError("World archive copy checksum mismatch")
    manifest: dict[str, Any] = {
        "schema": 2 if paper_companion else 1,
        "state": "CAPTURED_STOPPED_WORLD_FILES_DEV",
        "world_id": world_id, "branch_id": branch_id,
        "checkpoint_id": checkpoint_id, "declared_logical_tick": logical_tick,
        "tick_source_ref": tick_source_ref,
        "stopped_server_ref": stopped_server_ref,
        "stop_attestation_is_external": True,
        "world_effect_coverage_attested": False,
        "files": rows,
    }
    if paper_companion:
        manifest["world_file_role"] = "PAPER_COMPANION"
    _write_new(dest / "SHA256SUMS", _checksums(rows))
    _sync_dir(payload)
    # Last-written manifest acts as a completion marker; no implicit repair.
    _write_new(dest / "manifest.json", _canon(manifest))
    _sync_dir(dest)
    _sync_dir(dest.parent)
    return manifest


def verify_world_checkpoint(
    archive_dir: str | Path, *, expected_manifest_sha256: str | None = None,
) -> dict[str, Any]:
    """Check file integrity; optionally pin metadata provenance outside archive."""
    root = _safe_root(archive_dir, must_exist=True)
    if any(x.is_symlink() for x in (root / "world", root / "manifest.json", root / "SHA256SUMS")):
        raise WorldCheckpointError("symlink checkpoint component")
    if not (root / "world").is_dir():
        raise WorldCheckpointError("checkpoint World payload missing")
    if set(os.listdir(root)) != {"world", "manifest.json", "SHA256SUMS"}:
        raise WorldCheckpointError("archive must have exactly three entries")
    _check_optional_manifest_pin(root, expected_manifest_sha256)
    try:
        manifest = json.loads((root / "manifest.json").read_bytes())
    except (OSError, ValueError, UnicodeError) as exc:
        raise WorldCheckpointError("checkpoint manifest invalid") from exc
    keys = {"schema", "state", "world_id", "branch_id", "checkpoint_id",
            "declared_logical_tick", "tick_source_ref", "stopped_server_ref",
            "stop_attestation_is_external", "world_effect_coverage_attested", "files"}
    if type(manifest) is not dict:
        raise WorldCheckpointError("unknown checkpoint manifest schema")
    paper_companion = manifest.get("schema") == 2
    if (
        set(manifest) != (keys | {"world_file_role"} if paper_companion else keys)
        or (paper_companion and manifest["world_file_role"] != "PAPER_COMPANION")
    ):
        raise WorldCheckpointError("unknown checkpoint manifest schema")
    if (manifest["schema"] not in (1, 2)
            or manifest["state"] != "CAPTURED_STOPPED_WORLD_FILES_DEV"
            or manifest["stop_attestation_is_external"] is not True
            or manifest["world_effect_coverage_attested"] is not False):
        raise WorldCheckpointError("unsupported checkpoint status")
    for name in ("world_id", "branch_id", "checkpoint_id",
                 "tick_source_ref", "stopped_server_ref"):
        _text(name, manifest[name])
    _tick(manifest["declared_logical_tick"])
    rows = manifest["files"]
    if type(rows) is not list or not rows:
        raise WorldCheckpointError("checkpoint file list empty")
    rels: list[str] = []
    for row in rows:
        if type(row) is not dict or set(row) != {"path", "sha256", "size"}:
            raise WorldCheckpointError("invalid checkpoint file entry")
        rel = _rel(row["path"])
        if type(row["size"]) is not int or row["size"] < 0:
            raise WorldCheckpointError("invalid checkpoint file size")
        digest = row["sha256"]
        if (type(digest) is not str or len(digest) != 64
                or any(x not in "0123456789abcdef" for x in digest)):
            raise WorldCheckpointError("invalid checkpoint digest")
        rels.append(rel)
    if (
        rels != sorted(set(rels))
        or _scan(root / "world", require_level_dat=not paper_companion)
        != tuple(rels)
    ):
        raise WorldCheckpointError("World checkpoint inventory mismatch")
    for row in rows:
        if _hash_file(root / "world" / row["path"]) != (row["sha256"], row["size"]):
            raise WorldCheckpointError(f"checkpoint World file modified: {row['path']}")
    if (root / "SHA256SUMS").read_bytes() != _checksums(rows):
        raise WorldCheckpointError("checkpoint SHA256SUMS mismatch")
    return manifest


def restore_world_to_new_branch(
    archive_dir: str | Path,
    destination_world: str | Path,
    *,
    restore_id: str,
    expected_manifest_sha256: str | None = None,
    new_branch_id: str | None = None,
) -> dict[str, Any]:
    """Restore into a never-existing directory; issue a new branch in sidecar.

    Does not start Minecraft, mutate the source archive, or authorize physical
    replay. The sidecar written LAST is needed to identify a complete restore.
    """
    archive = _safe_root(archive_dir, must_exist=True)
    dest = _safe_root(destination_world, must_exist=False)
    _nonoverlap(archive, dest)
    _text("restore_id", restore_id)
    sidecar = dest.parent / f"{dest.name}.restore.json"
    if sidecar.exists() or sidecar.is_symlink():
        raise WorldCheckpointError("restore receipt already exists")
    manifest = verify_world_checkpoint(
        archive, expected_manifest_sha256=expected_manifest_sha256,
    )
    if new_branch_id is None:
        new_branch = f"fork-{uuid.uuid4()}"
    else:
        try:
            if new_branch_id != "fork-" + str(uuid.UUID(new_branch_id[5:])):
                raise WorldCheckpointError("noncanonical fork branch identity")
        except (ValueError, TypeError, AttributeError) as exc:
            raise WorldCheckpointError("invalid shared fork branch identity") from exc
        new_branch = new_branch_id
    if new_branch == manifest["branch_id"]:
        raise WorldCheckpointError("restore must create a new branch")
    dest.mkdir(mode=0o700)
    for row in manifest["files"]:
        digest, size = _copy_hashed(archive / "world" / row["path"], dest / row["path"])
        if (digest, size) != (row["sha256"], row["size"]):
            raise WorldCheckpointError("restore copy differs from verified checkpoint")
    if (
        _scan(dest, require_level_dat=manifest["schema"] == 1)
        != tuple(x["path"] for x in manifest["files"])
    ):
        raise WorldCheckpointError("restore World inventory differs from snapshot")
    for row in manifest["files"]:
        if _hash_file(dest / row["path"]) != (row["sha256"], row["size"]):
            raise WorldCheckpointError("restored World file digest differs")
    receipt: dict[str, Any] = {
        "schema": 1, "state": "RESTORED_NEW_BRANCH_FILES_DEV",
        "restore_id": restore_id, "world_id": manifest["world_id"],
        "source_branch_id": manifest["branch_id"],
        "new_branch_id": new_branch,
        "source_checkpoint_id": manifest["checkpoint_id"],
        "source_declared_logical_tick": manifest["declared_logical_tick"],
        "manifest_sha256": _sha((archive / "manifest.json").read_bytes()),
        "world_effect_coverage_attested": False,
        "physical_action_authorized": False,
        "semantic_owner_restored": False,
    }
    _write_new(sidecar, _canon(receipt))
    _sync_dir(dest)
    _sync_dir(dest.parent)
    return receipt



def verify_restored_world(
    archive_dir: str | Path, destination_world: str | Path, *,
    expected_manifest_sha256: str | None = None,
) -> dict[str, Any]:
    """Pre-launch World copy + explicit new-branch receipt integrity gate.

    Must run before the restored Minecraft process starts modifying files.
    A correct file manifest still does NOT authorize native physical issue.
    """
    archive = _safe_root(archive_dir, must_exist=True)
    dest = _safe_root(destination_world, must_exist=True)
    _nonoverlap(archive, dest)
    manifest = verify_world_checkpoint(
        archive, expected_manifest_sha256=expected_manifest_sha256,
    )
    sidecar = dest.parent / f"{dest.name}.restore.json"
    if sidecar.is_symlink() or not sidecar.is_file():
        raise WorldCheckpointError("final restore receipt is missing or linked")
    fd = os.open(sidecar, os.O_RDONLY | os.O_NOFOLLOW)
    try:
        if not stat.S_ISREG(os.fstat(fd).st_mode):
            raise WorldCheckpointError("restore receipt is not regular file")
        with os.fdopen(fd, "rb", closefd=False) as stream:
            receipt = json.load(stream)
    except (ValueError, UnicodeError, OSError) as exc:
        raise WorldCheckpointError("restore receipt cannot be trusted") from exc
    finally:
        os.close(fd)
    fields = {
        "schema", "state", "restore_id", "world_id", "source_branch_id",
        "new_branch_id", "source_checkpoint_id", "source_declared_logical_tick",
        "manifest_sha256", "world_effect_coverage_attested",
        "physical_action_authorized", "semantic_owner_restored",
    }
    if type(receipt) is not dict or set(receipt) != fields:
        raise WorldCheckpointError("restore receipt schema mismatch")
    if receipt["schema"] != 1 or receipt["state"] != "RESTORED_NEW_BRANCH_FILES_DEV":
        raise WorldCheckpointError("restore receipt status mismatch")
    if (receipt["world_effect_coverage_attested"] is not False
            or receipt["physical_action_authorized"] is not False
            or receipt["semantic_owner_restored"] is not False):
        raise WorldCheckpointError("restore receipt must not grant authorities")
    _text("restore_id", receipt["restore_id"])
    branch = _text("new_branch_id", receipt["new_branch_id"])
    try:
        parsed_uuid = uuid.UUID(branch.removeprefix("fork-"))
    except ValueError as exc:
        raise WorldCheckpointError("restore branch UUID malformed") from exc
    if not branch.startswith("fork-") or parsed_uuid.version != 4:
        raise WorldCheckpointError("restored history branch must be new UUIDv4")
    if (
        receipt["world_id"] != manifest["world_id"]
        or receipt["source_branch_id"] != manifest["branch_id"]
        or receipt["new_branch_id"] == manifest["branch_id"]
        or receipt["source_checkpoint_id"] != manifest["checkpoint_id"]
        or receipt["source_declared_logical_tick"] != manifest["declared_logical_tick"]
        or receipt["manifest_sha256"] != _sha((archive / "manifest.json").read_bytes())
    ):
        raise WorldCheckpointError("restore receipt/archive identity mismatch")
    if (
        _scan(dest, require_level_dat=manifest["schema"] == 1)
        != tuple(row["path"] for row in manifest["files"])
    ):
        raise WorldCheckpointError("restored World file inventory changed")
    for row in manifest["files"]:
        if _hash_file(dest / row["path"]) != (row["sha256"], row["size"]):
            raise WorldCheckpointError("restored World file hash mismatch")
    return receipt
