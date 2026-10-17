"""Preserve all present Paper dimension World bytes after isolated FLAT DEV STOP.

S DEV original evidence only; no replay, science admission, or P1 WAIT credit.
The directory tree is read AFTER Paper exit and BEFORE temporary cleanup.
"""
from __future__ import annotations

import hashlib
import shutil
import stat
from pathlib import Path

from adapters.mineflayer.m02_paper_dev.v8_stopped_world_clone_dev import need

WORLD_NAMES = ("world", "world_nether", "world_the_end")
FILE_CAP = 4096
BYTE_CAP = 512 * 1024 * 1024


def _digest(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda: f.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


def tree_index(root: Path) -> list[dict]:
    """Bounded byte-index; unlike overworld index, empty new dimensions allowed."""
    need(root.is_dir() and not root.is_symlink(), "invalid stopped dimension root")
    total = 0
    result = []
    for item in sorted(root.rglob("*")):
        mode = item.lstat().st_mode
        need(not stat.S_ISLNK(mode), "symlinked World evidence is forbidden")
        if stat.S_ISDIR(mode):
            continue
        need(stat.S_ISREG(mode), "special file in stopped World source")
        size = item.stat().st_size
        total += size
        need(len(result) < FILE_CAP and total <= BYTE_CAP
             and 0 <= size <= 64 * 1024 * 1024,
             "unbounded stopped dimension World bytes")
        result.append({
            "relative_path": item.relative_to(root).as_posix(),
            "size": size,
            "sha256": _digest(item),
        })
    return result


def preserve_stopped_flat_dimensions(server_root: Path, output_root: Path,
                                     *, paper_stopped: bool) -> dict:
    """Copy exactly the dimensions present, fail closed on any omitted bytes.

    world_nether and world_the_end can be absent if Paper did not create them;
    record absence explicitly. Any source world folder that exists is mandatory.
    """
    need(paper_stopped and server_root.is_absolute() and server_root.is_dir()
         and output_root.is_absolute() and output_root.is_dir()
         and not server_root.is_symlink() and not output_root.is_symlink(),
         "Paper STOP and distinct absolute source/output roots are required")
    source = server_root.resolve()
    output = output_root.resolve()
    destination = output / "saved_flat_dimensions_original"
    # The CLI owns a temporary server below output/owned-worlds. Check the
    # actual archive destination, which must remain outside that server tree.
    need(source != output and source != destination
         and source not in destination.parents
         and destination not in source.parents, "World evidence source/output alias")
    present = [name for name in WORLD_NAMES if (server_root / name).exists()]
    need("world" in present, "original overworld missing")
    need(not (output_root / "saved_flat_dimensions_original").exists(),
         "dimension archive already exists")
    originals = {}
    for name in present:
        originals[name] = tree_index(server_root / name)
    archived = output_root / "saved_flat_dimensions_original"
    archived.mkdir(mode=0o700)
    try:
        for name in present:
            shutil.copytree(server_root / name, archived / name, symlinks=True)
            need(tree_index(archived / name) == originals[name],
                 "copied stopped World dimension changed")
        for name in present:
            need(tree_index(server_root / name) == originals[name],
                 "original dimension changed during preservation")
    except Exception:
        # Preserve any partial evidence for forensic failure; never silently
        # present a partial copy as a complete World byte attestation.
        raise
    return {
        "classification": "S50_P1_FLAT_ALL_PRESENT_DIMENSION_BYTES_DEV_ONLY",
        "world_names_expected": list(WORLD_NAMES),
        "world_names_copied": present,
        "world_names_absent": [n for n in WORLD_NAMES if n not in present],
        "world_original_file_indices": originals,
        "dimension_byte_copy_verified": True,
        "whole_world_tick_activity_attested": False,
        "R_qualified": False,
        "wait_ticks_admitted": 0,
        "p1_fatigue_recovered": 0.0,
    }
