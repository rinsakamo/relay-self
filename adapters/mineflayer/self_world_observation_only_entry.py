"""W4 observation-only PREWORLD inventory, with no Java/Node launcher or grant.

All proof here is LOCAL checkout/file evidence, not authenticated World origin,
independent custody, a real process lifecycle, or physical run permission.
"""
from __future__ import annotations

import hashlib
import os
import re
import stat
import subprocess
from dataclasses import dataclass
from pathlib import Path


class ObservationOnlyEntryBlocked(ValueError):
    """No authority to proceed into World execution."""


@dataclass(frozen=True, slots=True)
class ObservationOnlyEntryInventory:
    schema: str
    exact_head: str
    jar_sha256: str
    bridge_sha256: str
    target_version: str = "1.21.8"
    binding_scope: str = "LOCAL_CHECKOUT_AND_OPERATOR_SUPPLIED_JAR_PIN_ONLY"
    java_process_launched: bool = False
    node_process_launched: bool = False
    world_provisioned: bool = False
    action_count: int = 0
    outcome_count: int = 0
    s10_update_count: int = 0
    external_grant_verified: bool = False
    external_source_qualified: bool = False
    physical_run_permitted: bool = False
    science_qualified: bool = False
    disposition: str = "PREWORLD_BLOCKED"


def _check_original_path(path: Path, *, directory: bool) -> None:
    if not isinstance(path, Path) or not path.is_absolute():
        raise ObservationOnlyEntryBlocked("absolute Path required")
    try:
        for item in (path, *path.parents):
            if stat.S_ISLNK(item.lstat().st_mode):
                raise ObservationOnlyEntryBlocked("symlink path component denied")
        if directory and not path.is_dir():
            raise ObservationOnlyEntryBlocked("directory expected")
        if not directory and not path.is_file():
            raise ObservationOnlyEntryBlocked("regular file expected")
    except OSError as exc:
        raise ObservationOnlyEntryBlocked("path unavailable") from exc


def _sha256_file(path: Path, *, max_size: int) -> str:
    _check_original_path(path, directory=False)
    fd = None
    try:
        fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_CLOEXEC)
        before = os.fstat(fd)
        if (
            not stat.S_ISREG(before.st_mode) or before.st_nlink != 1
            or not 1024 <= before.st_size <= max_size
        ):
            raise ObservationOnlyEntryBlocked("file type, size or link count invalid")
        digest = hashlib.sha256()
        with os.fdopen(fd, "rb", closefd=True) as handle:
            fd = None
            while chunk := handle.read(1024 * 1024):
                digest.update(chunk)
            after = os.fstat(handle.fileno())
        current = path.stat(follow_symlinks=False)
        def fingerprint(value):
            return (
                value.st_dev, value.st_ino, value.st_size,
                value.st_mtime_ns, value.st_ctime_ns,
            )
        if (
            fingerprint(before) != fingerprint(after)
            or (before.st_dev, before.st_ino) != (current.st_dev, current.st_ino)
        ):
            raise ObservationOnlyEntryBlocked("file changed during inventory")
        return digest.hexdigest()
    except OSError as exc:
        raise ObservationOnlyEntryBlocked("cannot inspect original file") from exc
    finally:
        if fd is not None:
            os.close(fd)


def _clean_head(repository: Path) -> str:
    results = []
    for args in (
        ("rev-parse", "--verify", "HEAD"),
        ("status", "--porcelain", "--untracked-files=normal"),
    ):
        try:
            proc = subprocess.run(
                ["git", "-C", str(repository), *args],
                capture_output=True, text=True, timeout=5, check=False,
            )
        except (OSError, subprocess.TimeoutExpired) as exc:
            raise ObservationOnlyEntryBlocked("local git inspection unavailable") from exc
        if proc.returncode != 0:
            raise ObservationOnlyEntryBlocked("local git inspection failed")
        results.append(proc.stdout.strip())
    if results[1]:
        raise ObservationOnlyEntryBlocked("checkout not clean")
    if re.fullmatch(r"[0-9a-f]{40}", results[0]) is None:
        raise ObservationOnlyEntryBlocked("invalid HEAD")
    return results[0]


def inventory_observation_only_entry(
    *, repository: Path, expected_head: str,
    server_jar: Path, expected_server_sha256: str,
    disposable_root: Path,
) -> ObservationOnlyEntryInventory:
    """Check preconditions only; matching assertions cannot mint a DEV grant.

    There is no World launcher, Action path, --confirm or grant argument.
    The checkout/JAR pins are operator-local, not external signer proof.
    """
    if os.environ.get("NODE_OPTIONS"):
        raise ObservationOnlyEntryBlocked("NODE_OPTIONS injection denied")
    if (
        type(expected_head) is not str
        or re.fullmatch(r"[0-9a-f]{40}", expected_head) is None
        or type(expected_server_sha256) is not str
        or re.fullmatch(r"[0-9a-f]{64}", expected_server_sha256) is None
    ):
        raise ObservationOnlyEntryBlocked("invalid exact pins")
    _check_original_path(repository, directory=True)
    _check_original_path(disposable_root, directory=True)
    if (
        disposable_root == repository
        or disposable_root.is_relative_to(repository)
        or repository.is_relative_to(disposable_root)
        or any(disposable_root.iterdir())
    ):
        raise ObservationOnlyEntryBlocked("disposable root must be isolated and empty")
    head = _clean_head(repository)
    if head != expected_head:
        raise ObservationOnlyEntryBlocked("exact HEAD mismatch")
    jar_hash = _sha256_file(server_jar, max_size=200_000_000)
    if jar_hash != expected_server_sha256:
        raise ObservationOnlyEntryBlocked("JAR SHA256 mismatch")
    bridge = repository / "adapters" / "mineflayer" / "bridge.mjs"
    bridge_hash = _sha256_file(bridge, max_size=4_000_000)
    return ObservationOnlyEntryInventory(
        schema="W4_OBSERVATION_ONLY_PREWORLD_INVENTORY_V1",
        exact_head=head, jar_sha256=jar_hash, bridge_sha256=bridge_hash,
    )
