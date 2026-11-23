"""Q Lane independent read-only Git tree integrity check for stacked DEV branches.

Designed to catch destructive tree replacements before treating CI or PRE_WORLD
reports as meaningful. Reads git objects only; never checks out a commit,
moves a ref, writes the index, starts Minecraft or grants any execution.
"""
from __future__ import annotations

import argparse
import json
import re
import subprocess
from pathlib import Path


class QTreeHold(ValueError):
    """Commit identity or required historical repository contents are absent."""


_HEX40 = re.compile(r"[0-9a-f]{40}\Z")
_PROTECTED = (
    ".github/workflows/ci.yml",
    "experiments/cognitive_physical_move_issue_dev.py",
    "src/relay_self/owned_resident_physical_bridge_dev.py",
    "src/relay_self/physical_action_journal.py",
    "src/relay_self/physical_issue_admission_dev.py",
)


def _git(root: Path, *args: str) -> bytes:
    try:
        completed = subprocess.run(
            ["git", "-C", str(root), *args],
            capture_output=True, check=False, timeout=20,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise QTreeHold("Git object read unavailable") from exc
    if completed.returncode != 0:
        raise QTreeHold("Git commit/tree object unavailable or invalid")
    return completed.stdout


def _tree(root: Path, sha: str) -> dict[str, str]:
    """Enumerate only committed blobs and object modes, never worktree bytes."""
    entries: dict[str, str] = {}
    for raw in _git(root, "ls-tree", "-rz", "--full-tree", sha).split(b"\0"):
        if not raw:
            continue
        try:
            info, path_raw = raw.split(b"\t", 1)
            mode, obj_type, _obj_sha = info.split(b" ", 2)
            path = path_raw.decode("utf-8")
        except (ValueError, UnicodeError) as exc:
            raise QTreeHold("Malformed committed tree entry") from exc
        if not path or path in entries or obj_type not in (b"blob", b"commit"):
            raise QTreeHold("Unexpected or duplicate tree item")
        entries[path] = mode.decode("ascii")
    if not entries:
        raise QTreeHold("Empty Git tree is not qualified")
    return entries


def inspect_tree_integrity(
    repo_root: Path, *, base_sha: str, expected_head: str,
    protected_paths: tuple[str, ...] = _PROTECTED,
) -> dict[str, object]:
    """Fail closed if a supposedly additive integration loses prior files.

    Git history proves byte identity within the inspected repository; it does
    not prove that this remote/repo is independently authenticated, or that
    a runtime Source, WAL, checkpoint or process is genuine.
    """
    if (
        not isinstance(repo_root, Path) or not repo_root.is_dir()
        or type(base_sha) is not str or _HEX40.fullmatch(base_sha) is None
        or type(expected_head) is not str or _HEX40.fullmatch(expected_head) is None
        or type(protected_paths) is not tuple or not protected_paths
        or any(type(p) is not str or not p or p.startswith("/") or ".." in p.split("/")
               for p in protected_paths)
        or len(set(protected_paths)) != len(protected_paths)
    ):
        raise QTreeHold("Exact pinned commit and protected repository paths required")
    if _git(repo_root, "rev-parse", "HEAD").decode("ascii").strip() != expected_head:
        raise QTreeHold("Worktree HEAD is not the requested exact commit")
    # The expected before/after commits must be from the same linear history.
    _git(repo_root, "merge-base", "--is-ancestor", base_sha, expected_head)
    before, after = _tree(repo_root, base_sha), _tree(repo_root, expected_head)
    missing_preexisting = sorted(set(before) - set(after))
    missing_protected = sorted(set(protected_paths) - set(after))
    changed_protected_type = sorted(
        path for path in protected_paths
        if path in after and after[path] not in ("100644", "100755")
    )
    if missing_preexisting or missing_protected or changed_protected_type:
        raise QTreeHold(
            "Commits removed historical files or protected code: "
            f"removed={len(missing_preexisting)}, "
            f"missing_protected={','.join(missing_protected)}, "
            f"invalid_protected_modes={','.join(changed_protected_type)}"
        )
    return {
        "classification": "Q_TREE_PRESERVATION_CPU_OFFLINE_DEV_PASS",
        "base_sha": base_sha,
        "head_sha": expected_head,
        "base_files": len(before),
        "head_files": len(after),
        "removed_files": 0,
        "protected_files_verified": len(protected_paths),
        "git_repository_origin_authenticated": False,
        "external_source_authenticated": False,
        "real_world_attested": False,
        "qualification_go": False,
    }


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--repo-root", required=True, type=Path)
    p.add_argument("--base-sha", required=True)
    p.add_argument("--expected-head", required=True)
    args = p.parse_args()
    try:
        result = inspect_tree_integrity(
            args.repo_root, base_sha=args.base_sha, expected_head=args.expected_head,
        )
    except (QTreeHold, OSError, UnicodeError) as exc:
        print(json.dumps({"classification": "Q_TREE_HOLD", "reason": str(exc)}))
        return 2
    print(json.dumps(result, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
