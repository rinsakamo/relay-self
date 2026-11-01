"""Pin and import the ORIGINAL S49 DEV owner without a manual sys.path shim.

This is local source selection, NOT an independent native attestation.
No network, World or LLM is contacted. Invoke BEFORE importing S49 modules.
"""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

S49_OWNER_SHA = "702f75c9fab3c42053ca0c89af670db1e306c892"


class S49OwnerBootstrapRejected(ValueError):
    """M cannot identify the exact source-owning S49 checkout."""


def bootstrap_original_s49_owner(directory: Path) -> Path:
    if not isinstance(directory, Path):
        raise S49OwnerBootstrapRejected("explicit S49 product checkout required")
    try:
        root = directory.expanduser().resolve(strict=True)
        if not root.is_dir():
            raise S49OwnerBootstrapRejected("owner checkout is not a directory")
        head = subprocess.run(
            ["git", "-C", str(root), "rev-parse", "--verify", "HEAD"],
            check=True, capture_output=True, text=True, timeout=10,
        ).stdout.strip()
        changes = subprocess.run(
            ["git", "-C", str(root), "status", "--porcelain", "--untracked-files=no"],
            check=True, capture_output=True, text=True, timeout=10,
        ).stdout.strip()
    except (OSError, RuntimeError, subprocess.SubprocessError) as exc:
        raise S49OwnerBootstrapRejected("cannot verify original S49 checkout") from exc
    if head != S49_OWNER_SHA or changes:
        raise S49OwnerBootstrapRejected("S49 owner is unpinned or has tracked changes")
    if not all(p.is_file() for p in (
        root / "adapters/mineflayer/s49_completed_decision_bridge.py",
        root / "adapters/mineflayer/self_action_evidence.py",
        root / "adapters/mineflayer/s49_normal_session_real_ci.py",
    )):
        raise S49OwnerBootstrapRejected("exact S49 source files are not available")

    # Reject an already-loaded foreign S49 module; the original package is
    # the authority for types and evidence validators, never a synthesized
    # M copy. This check is deliberately process-local, not cryptographic.
    for package in ("adapters", "relay_self", "test_postmain_two_epoch_continuation"):
        mod = sys.modules.get(package)
        location = getattr(mod, "__file__", None)
        if location and not Path(location).resolve().is_relative_to(root):
            raise S49OwnerBootstrapRejected("foreign S49 package already imported")

    for folder in (root, root / "src", root / "tests"):
        value = str(folder)
        if value in sys.path:
            sys.path.remove(value)
        sys.path.insert(0, value)
    import adapters.mineflayer.s49_completed_decision_bridge as owner
    import adapters.mineflayer.self_action_evidence as native

    if (
        not Path(owner.__file__).resolve().is_relative_to(root)
        or not Path(native.__file__).resolve().is_relative_to(root)
    ):
        raise S49OwnerBootstrapRejected("wrong original S49 module source")
    return root
