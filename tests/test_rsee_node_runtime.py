"""Shared RSEE Node runtime: no worktree npm installation/symlinks required."""
from __future__ import annotations

import json
import shutil
from pathlib import Path
from types import SimpleNamespace

import pytest

from adapters.mineflayer import self_owned_llama
from experiments.standard_env.node_runtime import (
    NodeRuntimeRejected,
    verify_node_runtime,
)


@pytest.fixture
def runtime(tmp_path):
    source = tmp_path / "worktree" / "adapters" / "mineflayer"
    source.mkdir(parents=True)
    for name in ("package.json", "package-lock.json"):
        (source / name).write_text(
            json.dumps({"version": "4.39.0", "name": name}, sort_keys=True),
            encoding="utf-8",
        )
    (source / "bridge.mjs").write_text("// fixture for bridge-context probe\n")
    root = tmp_path / "central" / "node-mineflayer"
    root.mkdir(parents=True)
    for name in ("package.json", "package-lock.json"):
        shutil.copyfile(source / name, root / name)
    mineflayer = root / "node_modules" / "mineflayer"
    mineflayer.mkdir(parents=True)
    (mineflayer / "package.json").write_text('{"version":"4.39.0"}')
    (mineflayer / "index.js").write_text("// actual Node probe stub\n")
    protocol = root / "node_modules" / "minecraft-protocol"
    protocol.mkdir()
    (protocol / "index.js").write_text("// protocol stub\n")
    return source, root


def test_shared_runtime_frozen_manifests_without_worktree_node_modules(runtime):
    source, root = runtime
    assert not (source / "node_modules").exists()
    receipt = verify_node_runtime(root, source)
    assert receipt["mineflayer_installed_version"] == "4.39.0"
    assert len(receipt["source_lock_sha256"]) == 64
    assert receipt["node_runtime_root"] == str(root)
    assert receipt["symlinked_dependency_root"] == "false"


def test_external_node_runtime_import_preflight_anchors_exact_npm_root(
    runtime, monkeypatch,
):
    source, root = runtime
    monkeypatch.setattr(self_owned_llama, "__file__", str(source / "self_owned_llama.py"))
    expected_mineflayer = root / "node_modules" / "mineflayer" / "index.js"
    expected_protocol = root / "node_modules" / "minecraft-protocol" / "index.js"
    calls = []

    def node_probe(argv, *, cwd, check, capture_output, text, timeout):
        calls.append((argv, cwd))
        assert argv[0] == "node"
        assert str(root / "package.json") in argv[2]
        assert cwd == source
        return SimpleNamespace(
            returncode=0,
            stdout=json.dumps({
                "mineflayer": "4.39.0",
                "mineflayer_entry": str(expected_mineflayer),
                "minecraft_protocol_entry": str(expected_protocol),
            }),
        )

    monkeypatch.setattr(self_owned_llama.subprocess, "run", node_probe)
    result = self_owned_llama._preflight_mineflayer_dependencies(root)
    assert result["node_runtime_root"] == str(root)
    assert result["source_lock_sha256"] == verify_node_runtime(root, source)["source_lock_sha256"]
    assert len(calls) == 1


def test_shared_module_escaping_runtime_root_is_rejected(runtime, monkeypatch):
    source, root = runtime
    monkeypatch.setattr(self_owned_llama, "__file__", str(source / "self_owned_llama.py"))

    def forged_node(*_args, **_kwargs):
        return SimpleNamespace(returncode=0, stdout=json.dumps({
            "mineflayer": "4.39.0",
            "mineflayer_entry": str(source / "bridge.mjs"),
            "minecraft_protocol_entry": str(source / "bridge.mjs"),
        }))

    monkeypatch.setattr(self_owned_llama.subprocess, "run", forged_node)
    with pytest.raises(self_owned_llama.OwnedModelRejected, match="outside verified root"):
        self_owned_llama._preflight_mineflayer_dependencies(root)


@pytest.mark.parametrize("kind", [
    "lock_drift", "package_drift", "runtime_symlink", "modules_symlink",
    "wrong_mineflayer_version", "missing_node_modules",
])
def test_external_root_drift_and_symlinks_fail_closed(runtime, tmp_path, kind):
    source, root = runtime
    if kind == "lock_drift":
        (root / "package-lock.json").write_text("{}")
    if kind == "package_drift":
        (root / "package.json").write_text("{}")
    if kind == "runtime_symlink":
        link = tmp_path / "aliased_runtime"
        link.symlink_to(root, target_is_directory=True)
        root = link
    if kind == "modules_symlink":
        source_mod = root / "node_modules"
        moved = root / "installed-modules"
        source_mod.rename(moved)
        source_mod.symlink_to(moved, target_is_directory=True)
    if kind == "wrong_mineflayer_version":
        (root / "node_modules" / "mineflayer" / "package.json").write_text(
            '{"version":"4.38.0"}'
        )
    if kind == "missing_node_modules":
        shutil.rmtree(root / "node_modules")
    with pytest.raises(NodeRuntimeRejected):
        verify_node_runtime(root, source)


def test_relative_or_nested_runtime_is_rejected(runtime):
    source, _ = runtime
    with pytest.raises(NodeRuntimeRejected):
        verify_node_runtime(Path("node-runtime"), source)
    nested = source / "runtime"
    nested.mkdir()
    with pytest.raises(NodeRuntimeRejected):
        verify_node_runtime(nested, source)
