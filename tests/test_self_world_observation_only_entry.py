"""W4 observation-only inert entry: local fixtures and Git stub, never World."""
from __future__ import annotations

import hashlib
import os
import subprocess
from dataclasses import asdict

import pytest

import adapters.mineflayer.self_world_observation_only_entry as entry

HEAD = "a" * 40


@pytest.fixture
def case(tmp_path, monkeypatch):
    repository = tmp_path / "source"
    bridge = repository / "adapters" / "mineflayer" / "bridge.mjs"
    bridge.parent.mkdir(parents=True)
    bridge.write_bytes(b"// checked-in bridge fixture\n" * 80)
    jar = tmp_path / "server.jar"
    jar.write_bytes(b"local jar fixture\n" * 100)
    scratch = tmp_path / "empty-new-run"
    scratch.mkdir()
    calls = []

    def git_only(argv, **kwargs):
        calls.append(tuple(argv))
        assert argv[:3] == ["git", "-C", str(repository)]
        assert kwargs["timeout"] == 5
        stdout = HEAD + "\n" if "rev-parse" in argv else ""
        return subprocess.CompletedProcess(argv, 0, stdout, "")
    monkeypatch.setattr(entry.subprocess, "run", git_only)
    monkeypatch.delenv("NODE_OPTIONS", raising=False)
    return {
        "repository": repository, "expected_head": HEAD,
        "server_jar": jar,
        "expected_server_sha256": hashlib.sha256(jar.read_bytes()).hexdigest(),
        "disposable_root": scratch, "bridge": bridge, "calls": calls,
    }


def _input(case):
    return {k: case[k] for k in (
        "repository", "expected_head", "server_jar",
        "expected_server_sha256", "disposable_root",
    )}


def test_inventory_pass_never_enters_world(case, monkeypatch):
    def no_spawn(*args, **kwargs):
        raise AssertionError("no process may start")
    monkeypatch.setattr(entry.subprocess, "Popen", no_spawn)
    result = entry.inventory_observation_only_entry(**_input(case))
    receipt = asdict(result)
    assert receipt["schema"] == "W4_OBSERVATION_ONLY_PREWORLD_INVENTORY_V1"
    assert receipt["exact_head"] == HEAD
    assert receipt["jar_sha256"] == case["expected_server_sha256"]
    assert receipt["bridge_sha256"] == hashlib.sha256(
        case["bridge"].read_bytes()
    ).hexdigest()
    assert receipt["disposition"] == "PREWORLD_BLOCKED"
    assert all(receipt[k] is False for k in (
        "java_process_launched", "node_process_launched", "world_provisioned",
        "external_grant_verified", "external_source_qualified",
        "physical_run_permitted", "science_qualified",
    ))
    assert receipt["action_count"] == receipt["outcome_count"] == 0
    assert receipt["s10_update_count"] == 0
    assert list(case["disposable_root"].iterdir()) == []
    assert len(case["calls"]) == 2


@pytest.mark.parametrize("fault", (
    "wrong_head", "bad_head", "bad_sha", "sha_syntax", "jar_symlink",
    "bridge_symlink", "dirty_root", "root_in_repo", "missing_bridge",
    "node_options", "short_jar", "jar_hardlink", "root_symlink",
))
def test_inventory_denies_unpinned_paths_and_state(case, monkeypatch, fault):
    inputs = _input(case)
    if fault == "wrong_head":
        inputs["expected_head"] = "b" * 40
    elif fault == "bad_head":
        inputs["expected_head"] = "unverified"
    elif fault == "bad_sha":
        inputs["expected_server_sha256"] = "f" * 64
    elif fault == "sha_syntax":
        inputs["expected_server_sha256"] = "sha-unknown"
    elif fault == "jar_symlink":
        jar = inputs["server_jar"]
        moved = jar.with_name("different.jar")
        jar.rename(moved)
        jar.symlink_to(moved)
    elif fault == "bridge_symlink":
        bridge = case["bridge"]
        moved = bridge.with_name("original.mjs")
        bridge.rename(moved)
        bridge.symlink_to(moved)
    elif fault == "dirty_root":
        (inputs["disposable_root"] / "old-world").mkdir()
    elif fault == "root_in_repo":
        nested = inputs["repository"] / "world"
        nested.mkdir()
        inputs["disposable_root"] = nested
    elif fault == "missing_bridge":
        case["bridge"].unlink()
    elif fault == "node_options":
        monkeypatch.setenv("NODE_OPTIONS", "--require untrusted.js")
    elif fault == "short_jar":
        inputs["server_jar"].write_bytes(b"not a server")
    elif fault == "jar_hardlink":
        os.link(inputs["server_jar"], inputs["server_jar"].with_name("jar-alias"))
    elif fault == "root_symlink":
        root = inputs["disposable_root"]
        moved = root.with_name("moved-root")
        root.rename(moved)
        root.symlink_to(moved, target_is_directory=True)
    with pytest.raises(entry.ObservationOnlyEntryBlocked):
        entry.inventory_observation_only_entry(**inputs)


def test_inventory_denies_dirty_checkout(case, monkeypatch):
    def dirty_git(argv, **kwargs):
        text = HEAD + "\n" if "rev-parse" in argv else "?? untracked\n"
        return subprocess.CompletedProcess(argv, 0, text, "")
    monkeypatch.setattr(entry.subprocess, "run", dirty_git)
    with pytest.raises(entry.ObservationOnlyEntryBlocked, match="not clean"):
        entry.inventory_observation_only_entry(**_input(case))


def test_inventory_has_no_confirm_or_grant_port(case):
    with pytest.raises(TypeError):
        entry.inventory_observation_only_entry(**_input(case), grant="self-minted")
    with pytest.raises(TypeError):
        entry.inventory_observation_only_entry(**_input(case), confirm=True)
