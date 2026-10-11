"""RSEE R3 source-only checks: mismatch, symlink and default purity."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest

from experiments.standard_env import lane_compat as r3


def git_blob(raw: bytes) -> str:
    return hashlib.sha1(
        b"blob " + str(len(raw)).encode("ascii") + b"\0" + raw
    ).hexdigest()


@pytest.fixture
def checkouts(tmp_path, monkeypatch):
    roots: dict[str, Path] = {}
    shared = {
        "experiments/standard_env/profile.v1.json": b"profile",
        "adapters/mineflayer/package.json": b"package",
        "adapters/mineflayer/package-lock.json": b"lock",
    }
    monkeypatch.setattr(
        r3, "SHARED_BLOBS",
        {name: git_blob(value) for name, value in shared.items()},
    )
    monkeypatch.setattr(r3, "BRIDGE_BLOB", git_blob(b"experience"))
    facts = {"head_mismatch": None, "dirty": None}

    for lane in r3.PINNED_HEADS:
        root = tmp_path / lane.lower()
        root.mkdir()
        roots[lane] = root
        for name, raw in shared.items():
            path = root / name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(raw)
        if lane in ("S", "L"):
            path = root / r3.BRIDGE_PATH
            path.parent.mkdir(parents=True)
            path.write_bytes(b"experience")

    def git(root, *args):
        lane = next(k for k, value in roots.items() if value == root)
        if args == ("rev-parse", "HEAD"):
            return "a" * 40 if facts["head_mismatch"] == lane else r3.PINNED_HEADS[lane]
        if args == ("status", "--porcelain", "--untracked-files=all"):
            return "?? foreign.py" if facts["dirty"] == lane else ""
        raise AssertionError("unexpected Git command")

    monkeypatch.setattr(r3, "_git", git)
    return roots, facts


def test_default_plan_no_file_or_git_read(monkeypatch, capsys):
    def forbidden(*_args, **_kwargs):
        pytest.fail("R3 default must not inspect source or external host")

    monkeypatch.setattr(r3, "_git", forbidden)
    monkeypatch.setattr(r3, "_blob", forbidden)
    assert r3.main([]) == 0
    result = json.loads(capsys.readouterr().out)
    assert result["classification"] == "RSEE_R3_PLAN_ONLY"
    assert result["physical_execution_authorized"] is False


def test_source_compatibility_is_not_runtime_or_science_qualification(checkouts):
    roots, _ = checkouts
    result = r3.inspect(roots)
    assert result["classification"] == "RSEE_R3_PINNED_SOURCE_IDENTITY_MATCH_ONLY"
    assert result["s3_l1_bridge_blob"] == git_blob(b"experience")
    assert set(result["shared_blobs"]) == {"R", "S", "L", "V"}
    assert result["physical_host_package_resolution"] == "UNKNOWN"
    assert result["original_world_receipt_verified"] is False
    assert result["r2_handoff_live_producer_connected"] is False
    assert result["physical_execution_authorized"] is False
    assert result["science_qualified"] is False


@pytest.mark.parametrize(("lane", "fact", "message"), [
    ("R", "head_mismatch", "R source HEAD mismatch"),
    ("S", "head_mismatch", "S source HEAD mismatch"),
    ("L", "dirty", "L source checkout dirty"),
    ("V", "dirty", "V source checkout dirty"),
])
def test_foreign_head_and_dirty_source_block(checkouts, lane, fact, message):
    roots, facts = checkouts
    facts[fact] = lane
    with pytest.raises(r3.SiblingCompatibilityRejected, match=message):
        r3.inspect(roots)


@pytest.mark.parametrize("lane", ["R", "S", "L", "V"])
def test_npm_lock_drift_rejected_for_any_lane(checkouts, lane):
    roots, _ = checkouts
    (roots[lane] / "adapters/mineflayer/package-lock.json").write_bytes(b"evil")
    with pytest.raises(r3.SiblingCompatibilityRejected, match="shared artifact drift"):
        r3.inspect(roots)


def test_l1_s3_bridge_drift_and_symlink_refused(checkouts, tmp_path):
    roots, _ = checkouts
    sbridge = roots["S"] / r3.BRIDGE_PATH
    sbridge.write_bytes(b"not same bridge")
    with pytest.raises(r3.SiblingCompatibilityRejected, match="S experience bridge drift"):
        r3.inspect(roots)
    sbridge.unlink()
    target = tmp_path / "outside-bridge.py"
    target.write_bytes(b"experience")
    sbridge.symlink_to(target)
    with pytest.raises(r3.SiblingCompatibilityRejected, match="source file not regular"):
        r3.inspect(roots)


def test_checkout_aliasing_and_symlinked_root_rejected(checkouts, tmp_path):
    roots, _ = checkouts
    with pytest.raises(r3.SiblingCompatibilityRejected, match="same checkout"):
        r3.inspect({**roots, "L": roots["S"]})
    alias = tmp_path / "symlink-l"
    alias.symlink_to(roots["L"], target_is_directory=True)
    with pytest.raises(r3.SiblingCompatibilityRejected, match="physical checkout"):
        r3.inspect({**roots, "L": alias})


def test_missing_source_and_limit_fail_closed(checkouts, monkeypatch):
    roots, _ = checkouts
    f = roots["V"] / "adapters/mineflayer/package.json"
    f.unlink()
    with pytest.raises(r3.SiblingCompatibilityRejected, match="source file not regular"):
        r3.inspect(roots)
    f.write_bytes(b"x" * 20)
    monkeypatch.setattr(r3, "MAX_SOURCE_BYTES", 10)
    with pytest.raises(r3.SiblingCompatibilityRejected, match="exceeds bound"):
        r3.inspect(roots)


def test_cli_requires_all_roots_in_verified_mode(capsys):
    assert r3.main(["--verify"]) == 2
    result = json.loads(capsys.readouterr().out)
    assert result["classification"] == "RSEE_R3_SOURCE_COMPATIBILITY_BLOCKED"
    assert result["physical_execution_authorized"] is False
    assert r3.main(["--s-root", "/tmp/unused"]) == 2
    result = json.loads(capsys.readouterr().out)
    assert result["classification"] == "RSEE_R3_SOURCE_COMPATIBILITY_BLOCKED"
