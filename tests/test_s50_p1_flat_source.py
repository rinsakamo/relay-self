"""Future S50/P1 FLAT ground DEV preflight; synthetic, no World starts."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest

from adapters.mineflayer.m02_paper_dev import s50_flat_base_foraging_dev as base
from adapters.mineflayer.m02_paper_dev import s50_flat_ground_dev as flat
from adapters.mineflayer.m02_paper_dev.s50_p1_flat_source import (
    CLASSIFICATION,
    admit_flat_original,
    verify_copy,
)
from adapters.mineflayer.m02_paper_dev.v8_stopped_world_clone_dev import (
    CloneDevRejected,
    world_index,
)


def fixture(tmp_path: Path, monkeypatch) -> tuple[Path, Path, Path]:
    archive = tmp_path / "archived"
    source = archive / base.FLAT_SOURCE
    (source / "region").mkdir(parents=True)
    (source / "region/r.0.0.mca").write_bytes(b"synthetic-only-region")
    level = source / "level.dat"
    level.write_bytes(b"synthetic-level-dat-NOT-real")
    monkeypatch.setattr(base, "LEVEL_SHA", hashlib.sha256(level.read_bytes()).hexdigest())
    (archive / "flat-source/server/server.properties").write_bytes(
        b"level-seed=63101\nlevel-type=minecraft:flat\n")
    (archive / "flat-source/paper_console.log").write_text(
        "\n".join("[Server] " + marker for marker, _ in flat.native_surface_commands()))
    (archive / "flat-source/flat_dev_receipt.json").write_text(json.dumps({
        "status": "FLAT_GROUND_NATIVE_WITNESSED_DEV_ONLY",
        "classification": flat.CLASSIFICATION,
        "native_surface_witnesses": 25,
        "native_missing_markers": [],
        "requested_seed": flat.FLAT_DEV_SEED,
        "java_exit": 0,
        "mineflayer_sessions": 0,
        "stopped_world_index": world_index(source),
    }))
    return archive, source, tmp_path / "fresh-output"


def test_flat_original_is_preflight_only_and_copy_identity(monkeypatch, tmp_path):
    archive, source, target = fixture(tmp_path, monkeypatch)
    expected = admit_flat_original(archive, target)
    copied = tmp_path / "disposable"
    import shutil

    shutil.copytree(source, copied)
    reviewed = verify_copy(source, copied, expected)
    assert reviewed["classification"] == CLASSIFICATION
    assert reviewed["source_seed"] == 63101
    assert reviewed["copied_world_bytes_equal_to_original"]
    assert not reviewed["independent_new_world_uuid"]
    assert reviewed["p1_wait_ticks_admitted"] == 0
    assert reviewed["p1_fatigue_recovered"] == 0
    assert not target.exists()


@pytest.mark.parametrize("corruption", [
    "wrong_world", "wrong_receipt", "short_witness", "wrong_seed",
    "archive_output_overlap", "source_symlink", "missing_region",
    "already_existing_output",
])
def test_tampered_or_aliased_flat_world_rejected(monkeypatch, tmp_path, corruption):
    archive, source, output = fixture(tmp_path, monkeypatch)
    if corruption == "wrong_world":
        (source / "level.dat").write_bytes(b"changed-original")
    elif corruption == "wrong_receipt":
        receipt = archive / "flat-source/flat_dev_receipt.json"
        data = json.loads(receipt.read_text())
        data["mineflayer_sessions"] = 1
        receipt.write_text(json.dumps(data))
    elif corruption == "short_witness":
        p = archive / "flat-source/paper_console.log"
        p.write_text("[Server] only-fake-surface\n")
    elif corruption == "wrong_seed":
        p = archive / "flat-source/server/server.properties"
        p.write_text("level-seed=61021\nlevel-type=normal\n")
    elif corruption == "archive_output_overlap":
        output = archive / "new-output"
    elif corruption == "source_symlink":
        level = source / "level.dat"
        level.unlink()
        level.symlink_to(tmp_path / "outside")
    elif corruption == "missing_region":
        (source / "region/r.0.0.mca").unlink()
    elif corruption == "already_existing_output":
        output.mkdir()
    with pytest.raises((CloneDevRejected, OSError)):
        admit_flat_original(archive, output)


def test_stopped_world_cannot_drift_after_copy(monkeypatch, tmp_path):
    archive, source, output = fixture(tmp_path, monkeypatch)
    expected = admit_flat_original(archive, output)
    import shutil

    copied = tmp_path / "disposable"
    shutil.copytree(source, copied)
    (copied / "level.dat").write_bytes(b"drift")
    with pytest.raises(CloneDevRejected):
        verify_copy(source, copied, expected)
