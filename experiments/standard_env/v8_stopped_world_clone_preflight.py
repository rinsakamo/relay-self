"""R V8 stopped-World clone byte parity preflight, never SCIENCE admission.

A seed match is insufficient: inspect the complete stopped World tree *before*
server startup for five independently staged arms. This only compares stored
file bytes. Generated loaded chunks, native spawn ticks, finite food, collision,
host stop and actual L0 outcomes require future independently reviewed sources.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
from pathlib import Path
from typing import Any

ARMS = frozenset({"BASE_ON", "SHAM_ON", "BASAL_ZERO", "WALK_ZERO", "BOTH_ZERO"})
SEEDS = frozenset(range(62101, 62109))
MAX_FILES = 1024
MAX_FILE_BYTES = 64 * 1024 * 1024
MAX_TOTAL_BYTES = 512 * 1024 * 1024
CLASS = "R_V8_STOPPED_WORLD_CLONE_BYTE_PARITY_ONLY_NOT_QUALIFIED"


class CloneRejected(ValueError):
    """Foreign, incomplete, aliased or mutated candidate stopped-World bytes."""


def require(test: bool, message: str) -> None:
    if not test:
        raise CloneRejected(message)


def _safe_root(root: Path) -> Path:
    require(isinstance(root, Path) and root.is_absolute()
            and root.is_dir() and not root.is_symlink()
            and all(not p.is_symlink() for p in root.parents),
            "absent, relative or symlinked stopped World root")
    return root.resolve(strict=True)


def _hash(path: Path, limit: int) -> tuple[int, str]:
    length = 0
    h = hashlib.sha256()
    with path.open("rb") as stream:
        while data := stream.read(1 << 20):
            length += len(data)
            require(length <= limit, "unbounded World file")
            h.update(data)
    return length, h.hexdigest()


def world_index(root: Path) -> tuple[tuple[str, int, str], ...]:
    """Read all files; do not ignore session.lock, entities or datapack changes."""
    root = _safe_root(root)
    entries: list[tuple[str, int, str]] = []
    total = 0
    for entry in sorted(root.rglob("*")):
        require(not entry.is_symlink() and (entry.is_file() or entry.is_dir()),
                "symlink, device or nonregular World entry")
        if entry.is_dir():
            continue
        rel = entry.relative_to(root).as_posix()
        require(re.fullmatch(r"[A-Za-z0-9_.\-/]+", rel) is not None
                and ".." not in entry.relative_to(root).parts
                and not rel.startswith("."),
                "unsafe/foreign stopped World filename")
        require(len(entries) < MAX_FILES, "unbounded number of World files")
        size, digest = _hash(entry, MAX_FILE_BYTES)
        total += size
        require(total <= MAX_TOTAL_BYTES, "unbounded total stopped World bytes")
        entries.append((rel, size, digest))
    paths = {row[0] for row in entries}
    require("level.dat" in paths and
            any(p.startswith("region/") and p.endswith(".mca") for p in paths),
            "no serialized World metadata or generated terrain region")
    require(next(x for x in entries if x[0] == "level.dat")[1] > 0,
            "empty initial World metadata")
    require(all(x[1] > 0 for x in entries if x[0].endswith(".mca")),
            "empty terrain region")
    return tuple(entries)


def _fingerprint(index: tuple[tuple[str, int, str], ...]) -> str:
    payload = json.dumps(index, separators=(",", ":"), ensure_ascii=True)
    return hashlib.sha256(payload.encode("ascii")).hexdigest()


def review_stopped_clones(
    source: Path, candidates: dict[str, Path], *,
    seed: int,
) -> dict[str, Any]:
    """Compare complete on-disk originals, not five operator digest claims."""
    require(type(seed) is int and seed in SEEDS,
            "seed outside proposed prospective V8 candidate roster")
    require(type(candidates) is dict and set(candidates) == ARMS,
            "missing, extra or aliased V8 arm")
    roots = [_safe_root(source)] + [_safe_root(candidates[a]) for a in sorted(ARMS)]
    require(len(set(roots)) == 6, "aliased source/arm World root")
    for i, root in enumerate(roots):
        require(all(i == j or (root not in other.parents and other not in root.parents)
                    for j, other in enumerate(roots)),
                "nested/overlapping World snapshot roots")
    original = world_index(source)
    clone_indices = {a: world_index(candidates[a]) for a in sorted(ARMS)}
    for arm, value in clone_indices.items():
        require(value == original,
                "stopped World clone differs in files, size or raw SHA256: " + arm)
    # Recheck the source and arms after comparison: catches mutation during scan.
    require(world_index(source) == original
            and all(world_index(candidates[a]) == clone_indices[a] for a in ARMS),
            "World snapshot mutated during independent read-only preflight")
    return {
        "classification": CLASS,
        "prospective_seed": seed,
        "hypothetical_arm_count": len(ARMS),
        "checked_stopped_world_files": len(original),
        "original_world_tree_sha256": _fingerprint(original),
        "original_region_file_count": sum(
            name.startswith("region/") and name.endswith(".mca")
            for name, _, _ in original),
        "source_and_five_stopped_clones_exact_bytes_equal": True,
        "all_stopped_world_files_included_not_only_seed_or_level_dat": True,
        "candidate_clone_inputs_independently_source_authenticated": False,
        "world_seed_from_native_nbt_attested": False,
        "physical_server_loaded_same_chunk_geometry": False,
        "native_agent_pose_and_server_start_tick_equal": False,
        "finite_food_and_resource_controls_equal": False,
        "native_actual_trajectory_equal_or_required": False,
        "source_plugin_and_all_five_profiles_newly_qualified_for_v8": False,
        "worlds_physically_started": 0,
        "v8_trials_credited": 0,
        "science_grant_issued": False,
        "science_go": False,
        "production_go": False,
    }


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--source", type=Path, required=True)
    p.add_argument("--seed", type=int, required=True)
    p.add_argument("--arm-root", action="append", required=True,
                   help="Five ARM=/absolute/stopped/world/root entries")
    args = p.parse_args()
    try:
        roots: dict[str, Path] = {}
        for value in args.arm_root:
            arm, sep, raw = value.partition("=")
            require(sep == "=" and arm in ARMS and raw and arm not in roots,
                    "invalid or repeated V8 stopped-world arm locator")
            roots[arm] = Path(raw)
        verdict = review_stopped_clones(args.source, roots, seed=args.seed)
        code = 0
    except (CloneRejected, OSError, UnicodeError, ValueError) as exc:
        verdict = {
            "classification": "R_V8_STOPPED_WORLD_CLONE_REJECTED_NO_GO",
            "reason": f"{type(exc).__name__}: {exc}",
            "worlds_physically_started": 0, "v8_trials_credited": 0,
            "science_grant_issued": False, "science_go": False,
            "production_go": False,
        }
        code = 2
    print(json.dumps(verdict, sort_keys=True))
    return code


if __name__ == "__main__":
    raise SystemExit(main())
