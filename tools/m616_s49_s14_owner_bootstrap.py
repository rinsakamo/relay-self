"""Pin the newer S-owner planned post-Action seam separately from M #683.

Do not change M #683's historic S49 #674 pin; this new M-only runner is
explicitly restricted to verified S #701 source and uses no synthetic owner.
"""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

S14_OWNER_SHA = "2e76ba467def10c1e0675eb3ebbe325682d5e8d2"


class S14OwnerBootstrapRejected(ValueError):
    """Missing, modified, wrong SHA or preloaded foreign S49 source."""


def bootstrap_original_s14_owner(directory: Path) -> Path:
    if not isinstance(directory, Path):
        raise S14OwnerBootstrapRejected("explicit S14 owner directory required")
    try:
        root = directory.expanduser().resolve(strict=True)
        if not root.is_dir():
            raise S14OwnerBootstrapRejected("original S14 checkout is not a directory")
        head = subprocess.run(
            ["git", "-C", str(root), "rev-parse", "--verify", "HEAD"],
            capture_output=True, text=True, check=True, timeout=10,
        ).stdout.strip()
        tracked = subprocess.run(
            ["git", "-C", str(root), "status", "--porcelain", "--untracked-files=no"],
            capture_output=True, text=True, check=True, timeout=10,
        ).stdout.strip()
    except (OSError, RuntimeError, subprocess.SubprocessError) as exc:
        raise S14OwnerBootstrapRejected("cannot verify original S owner checkout") from exc
    if head != S14_OWNER_SHA or tracked:
        raise S14OwnerBootstrapRejected("S14 owner must have exact clean frozen SHA")
    for f in (
        "adapters/mineflayer/s49_normal_session_real_ci.py",
        "adapters/mineflayer/s49_original_planned_postaction.py",
        "adapters/mineflayer/s49_completed_decision_bridge.py",
        "adapters/mineflayer/self_action_evidence.py",
    ):
        if not (root / f).is_file():
            raise S14OwnerBootstrapRejected("original S owner module absent")
    for name in ("adapters", "relay_self", "test_postmain_two_epoch_continuation"):
        loaded = sys.modules.get(name)
        location = getattr(loaded, "__file__", None)
        if location and not Path(location).resolve().is_relative_to(root):
            raise S14OwnerBootstrapRejected("foreign S owner package loaded")
    for folder in (root, root / "src", root / "tests"):
        value = str(folder)
        if value in sys.path:
            sys.path.remove(value)
        sys.path.insert(0, value)

    import adapters.mineflayer.s49_normal_session_real_ci as owner
    import adapters.mineflayer.s49_original_planned_postaction as planned

    import experiments

    m_experiments = str(Path(__file__).resolve().parents[1] / "experiments")
    if m_experiments not in experiments.__path__:
        experiments.__path__.append(m_experiments)
    if (
        not Path(owner.__file__).resolve().is_relative_to(root)
        or not Path(planned.__file__).resolve().is_relative_to(root)
    ):
        raise S14OwnerBootstrapRejected("wrong owner source import")
    return root
