"""Isolated, byte-verified Stage 28c-1 copy; never starts a World."""
from __future__ import annotations

import hashlib
import shutil
from dataclasses import dataclass
from pathlib import Path

from relay_self.stage28c2_recovered_resident_owner_dev import (
    Stage28c2aOfflineOwners,
    prepare_recovered_a_b_resident_owners,
)


class ExecutionCopyHold(RuntimeError):
    """Copy or typed recovery could not be established; retain partial copy."""


@dataclass(slots=True)
class ExecutionCopy:
    directory: Path
    files: tuple[tuple[str, str], ...]
    recovered: Stage28c2aOfflineOwners


def _inventory(root: Path) -> tuple[tuple[str, str], ...]:
    if root.is_symlink() or not root.is_dir():
        raise ExecutionCopyHold("source or copy root unavailable")
    rows = []
    for path in sorted(root.rglob("*")):
        if path.is_symlink():
            raise ExecutionCopyHold("symlink in restored source or copy")
        if path.is_dir():
            continue
        if not path.is_file():
            raise ExecutionCopyHold("non-regular source or copy node")
        digest = hashlib.sha256()
        with path.open("rb") as stream:
            while chunk := stream.read(1024 * 1024):
                digest.update(chunk)
        rows.append((path.relative_to(root).as_posix(), digest.hexdigest()))
    return tuple(rows)


def create_execution_copy(
    generation: Path, restored: Path, destination: Path, *,
    expected_world_id: str, expected_source_branch_id: str,
    expected_committed_sha256: str, expected_fork_branch_id: str,
) -> ExecutionCopy:
    """Copy all bytes, verify both inventories, then bind owners to the copy.

    A failure leaves the destination for inspection and never retries. Source
    must be quiescent; its inventory is checked again after owner construction.
    This is a preparation primitive, not an executable-session authorization.
    """
    source = Path(restored).absolute()
    destination = Path(destination).absolute()
    gen = Path(generation).resolve()
    if source.is_symlink() or destination.exists() or destination.is_symlink():
        raise ExecutionCopyHold("source symlink or non-fresh destination")
    source = source.resolve()
    dest = destination.resolve()
    if (dest == source or source in dest.parents or dest in source.parents
            or dest == gen or gen in dest.parents or dest in gen.parents):
        raise ExecutionCopyHold("source, generation and copy must be separate")
    try:
        before = _inventory(source)
        shutil.copytree(source, dest, symlinks=True)
        if _inventory(dest) != before or _inventory(source) != before:
            raise ExecutionCopyHold("source or copy byte inventory changed")
        recovered = prepare_recovered_a_b_resident_owners(
            gen, dest, expected_world_id=expected_world_id,
            expected_source_branch_id=expected_source_branch_id,
            expected_committed_sha256=expected_committed_sha256,
            expected_fork_branch_id=expected_fork_branch_id,
            observation_only=True,
        )
        if _inventory(source) != before or _inventory(dest) != before:
            raise ExecutionCopyHold("inventory changed during owner preparation")
        return ExecutionCopy(dest, before, recovered)
    except ExecutionCopyHold:
        raise
    except (OSError, ValueError, RuntimeError) as exc:
        raise ExecutionCopyHold("isolated execution copy not qualified") from exc
