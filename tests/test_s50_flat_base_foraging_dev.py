"""FLAT-DEV one-arm forensic foraging: no science and archive immutable."""
from __future__ import annotations

import json

import pytest

from adapters.mineflayer.m02_paper_dev import s50_flat_base_foraging_dev as subject
from adapters.mineflayer.m02_paper_dev import s50_flat_ground_dev as flat
from adapters.mineflayer.m02_paper_dev.v8_stopped_world_clone_dev import world_index


def fixture(tmp_path):
    archive = tmp_path / "archived-source"
    source = archive / subject.FLAT_SOURCE
    (source / "region").mkdir(parents=True)
    (source / "level.dat").write_bytes(b"synthetic-not-NBT")
    (source / "region/r.0.0.mca").write_bytes(b"synthetic-not-MCA")
    console = archive / "flat-source/paper_console.log"
    console.write_text("".join(
        f"[Server] {marker}\n" for marker, _ in flat.native_surface_commands()
    ))
    (archive / "flat-source/server/server.properties").write_bytes(flat.properties())
    (archive / "flat-source/flat_dev_receipt.json").write_text(json.dumps({
        "status": "FLAT_GROUND_NATIVE_WITNESSED_DEV_ONLY",
        "classification": flat.CLASSIFICATION,
        "native_surface_witnesses": 25,
        "native_missing_markers": [],
        "requested_seed": 63101,
        "java_exit": 0,
        "mineflayer_sessions": 0,
        "stopped_world_index": world_index(source),
    }))
    paper = tmp_path / "paper.jar"
    plugin = tmp_path / "plugin.jar"
    paper.write_bytes(b"synthetic-Paper")
    plugin.write_bytes(b"synthetic-plugin")
    return archive, paper, plugin, tmp_path / "new-dev-run"


def inject_asset_probes(monkeypatch):
    monkeypatch.setattr(subject.owner, "_fresh_asset", lambda p, digest: p)
    original_sha = subject.sha

    def fake_sha(path):
        return subject.LEVEL_SHA if path.name == "level.dat" else original_sha(path)

    monkeypatch.setattr(subject, "sha", fake_sha)
    monkeypatch.setattr(subject.subprocess, "run", lambda *a, **kw: None)


def test_distinct_flat_source_and_single_base_arm():
    assert subject.ARM == "BASE_ON"
    assert subject.CONFIRM != "V8-FIVE-WORLD-DEV-ONLY"
    assert subject.CONFIRM != flat.CONFIRM
    assert subject.LEVEL_SHA != "9dcbe19609a088d03b5418032f4bb618c1a6cf61dedc356cdb7e57b3e8895b70"
    assert subject.FLAT_SOURCE == "flat-source/server/world"
    assert subject.PLUGIN_SHA != "a43afa4d0a1fdaf01c633efd2543ed24b6b53b12ee38ed62a33594057e701e8f"


@pytest.mark.parametrize("confirm", ["SCIENCE", "QUALIFICATION", "", flat.CONFIRM])
def test_rejects_foreign_scope_before_writing(tmp_path, monkeypatch, confirm):
    a, paper, plugin, output = fixture(tmp_path)
    inject_asset_probes(monkeypatch)
    with pytest.raises(ValueError, match="confirmation"):
        subject.preflight(a, paper, plugin, subject.PLUGIN_SHA, output, confirm)
    assert not output.exists()


def test_rejects_unqualified_binary_even_with_same_profile(tmp_path, monkeypatch):
    a, paper, plugin, output = fixture(tmp_path)
    inject_asset_probes(monkeypatch)
    with pytest.raises(ValueError, match="pinned"):
        subject.preflight(a, paper, plugin, "0" * 64, output, subject.CONFIRM)
    assert not output.exists()


def test_rejects_archive_missing_native_clearance_proof(tmp_path, monkeypatch):
    a, paper, plugin, output = fixture(tmp_path)
    inject_asset_probes(monkeypatch)
    (a / "flat-source/paper_console.log").write_text("[Server] one fake marker\n")
    with pytest.raises(ValueError, match="markers"):
        subject.preflight(a, paper, plugin, subject.PLUGIN_SHA, output, subject.CONFIRM)


def test_rejects_archived_changed_stopped_world(tmp_path, monkeypatch):
    a, paper, plugin, output = fixture(tmp_path)
    inject_asset_probes(monkeypatch)
    (a / subject.FLAT_SOURCE / "region/r.0.0.mca").write_bytes(b"changed")
    with pytest.raises(ValueError, match="not attested"):
        subject.preflight(a, paper, plugin, subject.PLUGIN_SHA, output, subject.CONFIRM)


def test_valid_synthetic_shape_cannot_issue_science(tmp_path, monkeypatch):
    a, paper, plugin, output = fixture(tmp_path)
    inject_asset_probes(monkeypatch)
    assert len(subject.preflight(a, paper, plugin, subject.PLUGIN_SHA, output,
                                 subject.CONFIRM)) == 2
    assert not output.exists()  # Source-only preflight
    assert flat.FLAT_DEV_SEED == 63101
    assert subject.ARM == "BASE_ON"


def test_accepts_paper_normalized_flat_properties_after_native_attestation(
        tmp_path, monkeypatch):
    archive, paper, plugin, output = fixture(tmp_path)
    inject_asset_probes(monkeypatch)
    properties = archive / "flat-source/server/server.properties"
    properties.write_bytes(flat.properties().replace(b"minecraft:flat", b"flat"))
    assert len(subject.preflight(archive, paper, plugin, subject.PLUGIN_SHA,
                                 output, subject.CONFIRM)) == 2
    assert not output.exists()
