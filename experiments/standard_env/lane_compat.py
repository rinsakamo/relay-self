"""RSEE R3: passive pinned-source compatibility across unmerged S/L/V drafts.

Only read files and local Git metadata. This is independent of, and never
substitutes for, R1 host preflight, R2 raw receipt audit or the lane-owned tests.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import stat
import subprocess
from pathlib import Path

PINNED_HEADS = {
    "R": "0ab360375a797141e8bc0f2a9c04188a2db9e650",
    "S": "6f493b7a559dd72ea365998b9eadbd35fd7eb9b4",
    "L": "40db58d548ea31c4a70acabcc71b0954c7b6ce42",
    "V": "fc76b89638487eadda752e61e9bd7913e67088e5",
}

# Actual Git blob identities read independently from exact source branches.
SHARED_BLOBS = {
    "experiments/standard_env/profile.v1.json":
        "9058aa0913b5d7dcfe04c55f2a323fa912188dde",
    "adapters/mineflayer/package.json":
        "a09393edcd7aad83debad430820f828401c4173a",
    "adapters/mineflayer/package-lock.json":
        "8e4259d0d7523578e5f9262cf223a2af23c7758c",
}
BRIDGE_PATH = "src/relay_self/experience_bridge.py"
BRIDGE_BLOB = "326d4f14e2addc465f97ff452572865f3494325d"
MAX_SOURCE_BYTES = 8 * 1024 * 1024


class SiblingCompatibilityRejected(ValueError):
    """Source lineage/byte identity is missing, changed, or unqualified."""


def _require(ok: bool, why: str) -> None:
    if not ok:
        raise SiblingCompatibilityRejected(why)


def _git(root: Path, *args: str) -> str:
    result = subprocess.run(
        ["git", "-C", str(root), *args],
        text=True, capture_output=True, timeout=10, check=False,
    )
    _require(result.returncode == 0, "read-only Git inspection failed")
    return result.stdout.strip()


def _source_root(root: Path) -> Path:
    _require(root.is_absolute() and root.is_dir() and not root.is_symlink(),
             "absolute physical checkout required")
    _require(not any(parent.is_symlink() for parent in (root.parent, *root.parents)),
             "symlinked checkout ancestry")
    _require(root.resolve(strict=True) == root, "canonical checkout root required")
    return root


def _blob(path: Path) -> str:
    _require(not path.is_symlink() and path.is_file()
             and stat.S_ISREG(path.lstat().st_mode), "source file not regular")
    _require(path.stat().st_size <= MAX_SOURCE_BYTES, "source file exceeds bound")
    raw = path.read_bytes()
    _require(len(raw) <= MAX_SOURCE_BYTES, "source file exceeds bound")
    return hashlib.sha1(b"blob " + str(len(raw)).encode("ascii") + b"\0" + raw).hexdigest()


def plan() -> dict:
    """No Git/file probing until the operator explicitly requests --verify."""
    return {
        "classification": "RSEE_R3_PLAN_ONLY",
        "pinned_source_heads": PINNED_HEADS,
        "cross_lane_code_execution": "NOT_RUN",
        "shared_npm_host_installation": "NOT_PROBED",
        "runtime_permission": False,
        "physical_execution_authorized": False,
        "science_qualified": False,
    }


def inspect(roots: dict[str, Path]) -> dict:
    """Verify pinned HEADs, cleanliness and content identity, never run code."""
    _require(type(roots) is dict and set(roots) == set(PINNED_HEADS),
             "four independent lane roots required")
    observed_roots = {k: _source_root(v) for k, v in roots.items()}
    _require(len(set(observed_roots.values())) == 4,
             "same checkout cannot impersonate independent lanes")
    source_blobs: dict[str, dict[str, str]] = {}
    for lane, root in observed_roots.items():
        _require(_git(root, "rev-parse", "HEAD") == PINNED_HEADS[lane],
                 f"{lane} source HEAD mismatch")
        _require(not _git(root, "status", "--porcelain", "--untracked-files=all"),
                 f"{lane} source checkout dirty or untracked")
        source_blobs[lane] = {}
        for path, expected in SHARED_BLOBS.items():
            actual = _blob(root / path)
            _require(actual == expected, f"{lane} shared artifact drift: {path}")
            source_blobs[lane][path] = actual
    for lane in ("S", "L"):
        _require(_blob(observed_roots[lane] / BRIDGE_PATH) == BRIDGE_BLOB,
                 f"{lane} experience bridge drift")
    return {
        "classification": "RSEE_R3_PINNED_SOURCE_IDENTITY_MATCH_ONLY",
        "pinned_heads": PINNED_HEADS,
        "shared_blobs": source_blobs,
        "s3_l1_bridge_blob": BRIDGE_BLOB,
        "source_files_read_only": True,
        "sibling_behavior_tests": "NOT_RUN_BY_THIS_COMMAND",
        "physical_host_package_resolution": "UNKNOWN",
        "original_world_receipt_verified": False,
        "r2_handoff_live_producer_connected": False,
        "physical_execution_authorized": False,
        "science_qualified": False,
        "side_effects": "NO_INSTALL_NO_WORLD_NO_MODEL_NO_WRITE",
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--verify", action="store_true")
    for lane in PINNED_HEADS:
        parser.add_argument("--" + lane.lower() + "-root", type=Path)
    args = parser.parse_args(argv)
    try:
        roots = {k: getattr(args, k.lower() + "_root") for k in PINNED_HEADS}
        if args.verify:
            _require(all(isinstance(path, Path) for path in roots.values()),
                     "--verify requires R/S/L/V source roots")
            result = inspect(roots)
        else:
            _require(all(v is None for v in roots.values()),
                     "source roots require --verify")
            result = plan()
    except (OSError, ValueError, subprocess.SubprocessError) as exc:
        result = {
            "classification": "RSEE_R3_SOURCE_COMPATIBILITY_BLOCKED",
            "error": type(exc).__name__ + ":" + str(exc),
            "physical_execution_authorized": False,
            "science_qualified": False,
        }
    print(json.dumps(result, ensure_ascii=False, sort_keys=True))
    return 0 if result["classification"] in (
        "RSEE_R3_PLAN_ONLY", "RSEE_R3_PINNED_SOURCE_IDENTITY_MATCH_ONLY"
    ) else 2


if __name__ == "__main__":
    raise SystemExit(main())
