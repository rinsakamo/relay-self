"""Stage28b pinned Paper/passive two-Self launcher never calls a model in tests."""
from __future__ import annotations

import sys
from pathlib import Path

from experiments import stage28b_pinned_typed_cut_launch_dev as launcher
from experiments.stage24g_pinned_assets_launch_dev import (
    Stage24gPinnedAssetReceipt,
)


def _argv(tmp_path: Path, mode: str) -> list[str]:
    args = [
        "stage28b_pinned_typed_cut_launch_dev",
        "--paper-jar", str(tmp_path / "paper.jar"),
        "--plugin-jar", str(tmp_path / "new-plugin.jar"),
        "--scratch-parent", str(tmp_path),
        "--eula-accepted", mode,
    ]
    if mode == "--execute-once":
        args.append("--real-world-dev-grant")
    return args


def _setup(tmp_path, monkeypatch):
    receipt = Stage24gPinnedAssetReceipt(
        tmp_path / "paper.jar", tmp_path / "new-plugin.jar", tmp_path,
        "a" * 64, "b" * 64,
    )
    monkeypatch.setattr(
        launcher, "check_stage24g_pinned_assets", lambda **kwargs: receipt,
    )
    monkeypatch.setattr(launcher, "_verify_local_runtime", lambda *args: None)


def test_stage28b_inspect_only_never_creates_world(tmp_path, monkeypatch):
    _setup(tmp_path, monkeypatch)
    monkeypatch.setattr(sys, "argv", _argv(tmp_path, "--inspect-only"))
    async def forbidden(**kwargs):
        raise AssertionError("inspect-only attempted real World")
    monkeypatch.setattr(launcher, "run_real_resident_presence", forbidden)
    assert launcher.main() == 0


def test_stage28b_passive_one_shot_exact_owner_runner(tmp_path, monkeypatch):
    _setup(tmp_path, monkeypatch)
    monkeypatch.setattr(sys, "argv", _argv(tmp_path, "--execute-once"))
    seen = []
    async def capture(**kwargs):
        seen.append(kwargs)
        return tmp_path / "result.json"
    monkeypatch.setattr(launcher, "run_real_resident_presence", capture)
    assert launcher.main() == 0
    assert len(seen) == 1
    assert seen[0]["typed_owner_cut_dev"] is True
    assert seen[0]["world_only"] is False
    assert seen[0]["real_llm_grant"] is False
    assert seen[0]["b_autonomous_l1_dev"] is False
    assert seen[0]["b_selected_move_dev"] is False
    assert seen[0]["real_world_dev_grant"] is True


def test_stage28b_refuses_execute_without_world_grant(tmp_path, monkeypatch):
    _setup(tmp_path, monkeypatch)
    argv = _argv(tmp_path, "--execute-once")
    argv.remove("--real-world-dev-grant")
    monkeypatch.setattr(sys, "argv", argv)
    async def forbidden(**kwargs):
        raise AssertionError("ungranted World attempt")
    monkeypatch.setattr(launcher, "run_real_resident_presence", forbidden)
    assert launcher.main() == 2
