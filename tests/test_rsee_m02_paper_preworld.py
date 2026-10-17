"""Synthetic negative controls for a distinct Paper M0.2 RSEE preworld profile."""
from __future__ import annotations

import copy
import hashlib
import json

import pytest

from experiments.standard_env import m02_paper_preworld as r


def specimen(tmp_path):
    source = json.loads(r.PROFILE_FILE.read_text())
    root = tmp_path / "separate-paper"
    root.mkdir()
    values = {
        "paper-1.21.8.jar": b"paper-server-jar-fixture",
        "relay-metabolism-paper-dev.jar": b"dev-plugin-jar-fixture",
        "config.yml": b"dev-enabled: true\ntarget-player: RelaySelf\n",
        "server.properties": b"online-mode=false\nserver-ip=127.0.0.1\n",
    }
    for name, content in values.items():
        (root / name).write_bytes(content)
    source["expected_assets_sha256"] = {
        name: hashlib.sha256(content).hexdigest()
        for name, content in values.items()
    }
    return root, source


def test_default_has_no_reads(monkeypatch):
    monkeypatch.setattr(r, "inspect", lambda _: pytest.fail("unexpected asset I/O"))
    assert r.main([]) == 0


def test_profile_v1_fixed_historical_source_scope():
    profile = r.load_manifest()
    assert profile["source_s_head"] == r.PAPER_HEAD
    assert profile["reference_m_head"] == r.M_HEAD
    assert profile["vanilla_golden_replacement_allowed"] is False
    assert profile["virtual_m0_ledger_allowed"] is False


def test_synthetic_fresh_assets_nonpromotion_and_no_write(tmp_path):
    root, profile = specimen(tmp_path)
    before = {p.name: p.read_bytes() for p in root.iterdir()}
    report = r.inspect(root, profile)
    assert report["classification"] == "M02_PAPER_ASSETS_PINNED_PREWORLD_REVIEW_ONLY"
    assert not report["qualified"] and not report["science_go"]
    assert not report["new_physical_qualification_authorized"]
    assert report["physical_world_launches_by_review"] == 0
    assert {p.name: p.read_bytes() for p in root.iterdir()} == before


@pytest.mark.parametrize("field,value", [
    ("source_s_head", "stale"),
    ("reference_m_head", "stale"),
    ("qualification_status", "QUALIFIED"),
    ("science_status", "SUCCESS"),
    ("production_status", "GO"),
    ("server_flavor", "Mojang"),
    ("minecraft_version", "1.21.7"),
    ("world_mode", "REUSE_VANILLA_GOLDEN"),
    ("vanilla_golden_replacement_allowed", True),
    ("virtual_m0_ledger_allowed", True),
    ("cognition_cost_enabled", True),
    ("rates_calibration", "qualified"),
    ("basal_exhaustion_per_world_tick_candidate", -0.001),
    ("walk_exhaustion_per_observed_block_candidate", 0.0),
    ("required_jvm_major", 17),
    ("required_node_major", 20),
    ("physical_dev_source_artifact_id", 0),
    ("owner_player", "unknown"),
])
def test_profile_scope_fail_closed(tmp_path, field, value):
    root, profile = specimen(tmp_path)
    broken = copy.deepcopy(profile)
    broken[field] = value
    with pytest.raises(r.Blocked):
        r.inspect(root, broken)


@pytest.mark.parametrize("name", [
    "paper-1.21.8.jar", "relay-metabolism-paper-dev.jar",
    "config.yml", "server.properties",
])
def test_source_asset_tampering_rejected(tmp_path, name):
    root, profile = specimen(tmp_path)
    (root / name).write_bytes((root / name).read_bytes() + b"tampered")
    with pytest.raises(r.Blocked, match="digest"):
        r.inspect(root, profile)


def test_unexpected_extra_file_rejected(tmp_path):
    root, profile = specimen(tmp_path)
    (root / "world").mkdir()
    with pytest.raises(r.Blocked, match="four-file"):
        r.inspect(root, profile)


def test_symlink_asset_refused(tmp_path):
    root, profile = specimen(tmp_path)
    real = root / "target"
    (root / "paper-1.21.8.jar").rename(real)
    (root / "paper-1.21.8.jar").symlink_to(real)
    with pytest.raises(r.Blocked):
        r.inspect(root, profile)


def test_duplicate_json_fields_and_nonfinite_are_refused(tmp_path):
    obj = r.PROFILE_FILE.read_text()
    path = tmp_path / "duplicated.json"
    path.write_text(obj.replace('"schema": ', '"schema": "DUPLICATE", "schema": ', 1))
    with pytest.raises(r.Blocked, match="manifest"):
        r.load_manifest(path)
    path.write_text(obj.replace("0.001", "NaN"))
    with pytest.raises(r.Blocked, match="manifest"):
        r.load_manifest(path)
