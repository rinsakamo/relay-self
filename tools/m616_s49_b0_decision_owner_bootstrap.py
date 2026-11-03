"""Pin independently authored S B0 owner (not an M synthetic ledger).

This *new* read-only product selection does not relax the historical M #683
S #674 or M #705 S #701 source pin. Same-process object identity requires
only original S source modules, no rewritten imports after first load.
"""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

S_B0_DECISION_OWNER_SHA = "42921b3f6a66f4cb622f9f628ffdc2c1cd12ba5d"


class B0OwnerBootstrapRejected(ValueError):
    """Exact B0 owner source is absent/dirty or foreign module was preloaded."""


def bootstrap_original_s49_b0_decision_owner(directory: Path) -> Path:
    if not isinstance(directory, Path):
        raise B0OwnerBootstrapRejected("explicit original S B0 owner directory required")
    try:
        root = directory.expanduser().resolve(strict=True)
        if not root.is_dir():
            raise B0OwnerBootstrapRejected("S B0 owner directory missing")
        sha = subprocess.run(
            ["git", "-C", str(root), "rev-parse", "--verify", "HEAD"],
            check=True, capture_output=True, text=True, timeout=10,
        ).stdout.strip()
        dirty = subprocess.run(
            ["git", "-C", str(root), "status", "--porcelain", "--untracked-files=no"],
            check=True, capture_output=True, text=True, timeout=10,
        ).stdout.strip()
    except (OSError, RuntimeError, subprocess.SubprocessError) as exc:
        raise B0OwnerBootstrapRejected("cannot verify original S B0 checkout") from exc
    if sha != S_B0_DECISION_OWNER_SHA or dirty:
        raise B0OwnerBootstrapRejected("B0 owner source not exact clean SHA")
    for name in (
        "adapters/mineflayer/s49_b0_owner_decision_witness.py",
        "adapters/mineflayer/s49_original_planned_postaction.py",
        "adapters/mineflayer/s49_completed_decision_bridge.py",
        "adapters/mineflayer/s49_normal_session_real_ci.py",
        "adapters/mineflayer/b0_energy_bridge.py",
        "adapters/mineflayer/self_body_m0_projection.py",
    ):
        if not (root / name).is_file():
            raise B0OwnerBootstrapRejected("original S B0 typed owner missing")
    for name in ("adapters", "relay_self", "test_postmain_two_epoch_continuation"):
        existing = sys.modules.get(name)
        location = getattr(existing, "__file__", None)
        if location and not Path(location).resolve().is_relative_to(root):
            raise B0OwnerBootstrapRejected("foreign S package already loaded")
    for path in (root, root / "src", root / "tests"):
        location = str(path)
        if location in sys.path:
            sys.path.remove(location)
        sys.path.insert(0, location)

    import adapters.mineflayer.s49_normal_session_real_ci as original_s49
    import adapters.mineflayer.s49_b0_owner_decision_witness as original_b0

    import experiments

    mpath = str(Path(__file__).resolve().parents[1] / "experiments")
    if mpath not in experiments.__path__:
        experiments.__path__.append(mpath)
    if (
        not Path(original_s49.__file__).resolve().is_relative_to(root)
        or not Path(original_b0.__file__).resolve().is_relative_to(root)
    ):
        raise B0OwnerBootstrapRejected("original S package resolved elsewhere")
    return root
