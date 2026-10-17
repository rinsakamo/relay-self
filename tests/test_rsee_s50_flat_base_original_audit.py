"""R FLAT BASE source-original checker: adversarial path and hash guards."""
from __future__ import annotations

import hashlib

import pytest

from experiments.standard_env import s50_flat_base_original_audit as r


def test_pinned_identity_and_science_ceiling():
    assert r.SOURCE_LEVEL_SHA == "1cd714e9607a8015ca37918f11717ab92f2e0d44718c439d7d83a9a36dac1845"
    assert len(r.PLUGIN_SHA) == 64
    assert r.ARMS == {"BASE_ON"}


def test_manifest_rejects_missing_or_changed_bytes(tmp_path):
    (tmp_path / "report.json").write_bytes(b"original")
    item = {"report.json": hashlib.sha256(b"original").hexdigest()}
    for i in range(9):
        name = f"data/f{i}.txt"
        (tmp_path / "data").mkdir(exist_ok=True)
        (tmp_path / name).write_bytes(str(i).encode())
        item[name] = r.digest(str(i).encode())
    n, missing, mismatch = r.validate_manifest(tmp_path, item)
    assert n == 10 and not missing and not mismatch
    (tmp_path / "report.json").write_bytes(b"mutated")
    n, missing, mismatch = r.validate_manifest(tmp_path, item)
    assert mismatch == ["report.json"]
    (tmp_path / "report.json").unlink()
    n, missing, mismatch = r.validate_manifest(tmp_path, item)
    assert missing == ["report.json"]


@pytest.mark.parametrize("name", ["../secret", "/tmp/secret", "./secret",
                                   "a//b", "a/../b", ""])
def test_manifest_rejects_traversal_and_aliases(tmp_path, name):
    manifest = {f"x{i}": "a" * 64 for i in range(9)}
    manifest[name] = "a" * 64
    with pytest.raises(r.FlatBaseAuditRejected, match="invalid manifest path"):
        r.validate_manifest(tmp_path, manifest)


def test_world_index_requires_region_and_level(tmp_path):
    (tmp_path / "level.dat").write_bytes(b"not-real")
    with pytest.raises(r.FlatBaseAuditRejected, match="terrain"):
        r.independent_index(tmp_path)


def test_manifest_symlink_does_not_follow(tmp_path):
    (tmp_path / "existing").write_bytes(b"hello")
    (tmp_path / "link").symlink_to(tmp_path / "existing")
    manifest = {f"x{i}": "a" * 64 for i in range(9)}
    manifest["link"] = r.digest(b"hello")
    _, missing, mismatch = r.validate_manifest(tmp_path, manifest)
    assert "link" in missing and not mismatch


def test_real_world_audit_requires_source_not_made_up(tmp_path):
    with pytest.raises(r.FlatBaseAuditRejected):
        r.audit(tmp_path / "original", tmp_path / "forged")
