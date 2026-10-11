"""Pinned external Node runtime for RSEE, independent from Git worktrees.

Runtime root holds a physical npm ci installation, not a symlink to
node_modules. This only validates bytes/paths and never installs dependencies.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path


class NodeRuntimeRejected(ValueError):
    """Do not substitute another physical dependency tree."""


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def verify_node_runtime(root: Path, adapter: Path) -> dict[str, str]:
    """Verify physical external npm root with original exact lock/package bytes."""
    if not isinstance(root, Path) or not root.is_absolute():
        raise NodeRuntimeRejected("absolute explicit Node runtime root required")
    if root.is_symlink() or not root.is_dir() or root.resolve() != root:
        raise NodeRuntimeRejected("external Node runtime root must be physical")
    if root == adapter or adapter in root.parents or root in adapter.parents:
        raise NodeRuntimeRejected("Node runtime must be outside the source worktree")
    modules = root / "node_modules"
    if modules.is_symlink() or not modules.is_dir():
        raise NodeRuntimeRejected("physical external node_modules required")
    entries: dict[str, str] = {}
    for name in ("package.json", "package-lock.json"):
        original = adapter / name
        external = root / name
        if (original.is_symlink() or not original.is_file()
                or external.is_symlink() or not external.is_file()):
            raise NodeRuntimeRejected("source and runtime npm manifests must be real files")
        source_sha = _sha256(original)
        if _sha256(external) != source_sha:
            raise NodeRuntimeRejected("external npm package/lock differs from source")
        entries[name] = source_sha
    installed = modules / "mineflayer" / "package.json"
    if installed.is_symlink() or not installed.is_file():
        raise NodeRuntimeRejected("external Mineflayer package missing or symlinked")
    try:
        package = json.loads(installed.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, ValueError) as exc:
        raise NodeRuntimeRejected("external Mineflayer metadata unreadable") from exc
    if not isinstance(package, dict) or package.get("version") != "4.39.0":
        raise NodeRuntimeRejected("external Mineflayer version differs")
    return {
        "node_runtime_root": str(root),
        "source_package_sha256": entries["package.json"],
        "source_lock_sha256": entries["package-lock.json"],
        "mineflayer_installed_version": package["version"],
        "symlinked_dependency_root": "false",
    }
