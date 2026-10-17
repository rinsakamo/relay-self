"""S FLAT/P1 STOP-preservation: all existing dimension bytes, not WAIT."""
from __future__ import annotations

import shutil
from pathlib import Path

import pytest

from adapters.mineflayer.m02_paper_dev.s50_p1_world_preservation import (
    preserve_stopped_flat_dimensions,
    tree_index,
)
from adapters.mineflayer.m02_paper_dev.v8_stopped_world_clone_dev import CloneDevRejected


def _world(tmp_path: Path) -> tuple[Path, Path]:
    source = tmp_path / "paper-ephemeral"
    for name, dim_path in (
        ("world", "region/r.0.0.mca"),
        ("world_nether", "DIM-1/region/r.0.0.mca"),
        ("world_the_end", "DIM1/region/r.0.0.mca"),
    ):
        root = source / name
        (root / dim_path).parent.mkdir(parents=True)
        (root / dim_path).write_bytes(("original byte " + name).encode())
        (root / "level.dat").write_bytes(("level byte " + name).encode())
    output = tmp_path / "fresh-evidence"
    output.mkdir()
    return source, output


def test_capture_three_worlds_byte_by_byte(tmp_path):
    source, output = _world(tmp_path)
    before = {name: tree_index(source / name) for name in (
        "world", "world_nether", "world_the_end")}
    proof = preserve_stopped_flat_dimensions(source, output, paper_stopped=True)
    assert proof["world_names_copied"] == list(before)
    assert proof["world_names_absent"] == []
    assert proof["dimension_byte_copy_verified"]
    assert not proof["R_qualified"]
    assert proof["wait_ticks_admitted"] == 0
    assert proof["p1_fatigue_recovered"] == 0
    assert proof["world_original_file_indices"] == before
    for name, original in before.items():
        copied = output / "saved_flat_dimensions_original" / name
        assert tree_index(copied) == original
        assert tree_index(source / name) == original


@pytest.mark.parametrize("missing", ["world_nether", "world_the_end"])
def test_absent_dimension_is_explicit(tmp_path, missing):
    source, output = _world(tmp_path)
    shutil.rmtree(source / missing)
    proof = preserve_stopped_flat_dimensions(source, output, paper_stopped=True)
    assert missing in proof["world_names_absent"]
    assert missing not in proof["world_names_copied"]
    assert not (output / "saved_flat_dimensions_original" / missing).exists()


@pytest.mark.parametrize("violation", [
    "not_stopped", "missing_world", "symlinked_file",
    "existing_archive", "alias_output",
])
def test_unsafe_preservation_fails_closed(tmp_path, violation):
    source, output = _world(tmp_path)
    stopped = True
    if violation == "not_stopped":
        stopped = False
    elif violation == "missing_world":
        shutil.rmtree(source / "world")
    elif violation == "symlinked_file":
        p = source / "world_nether/level.dat"
        p.unlink()
        p.symlink_to(source / "world/level.dat")
    elif violation == "existing_archive":
        (output / "saved_flat_dimensions_original").mkdir()
    elif violation == "alias_output":
        output = source / "world"
    with pytest.raises((CloneDevRejected, OSError)):
        preserve_stopped_flat_dimensions(source, output, paper_stopped=stopped)


def test_byte_mutation_after_copy_detectable(tmp_path):
    source, output = _world(tmp_path)
    proof = preserve_stopped_flat_dimensions(source, output, paper_stopped=True)
    copied = output / "saved_flat_dimensions_original/world_nether"
    (copied / "level.dat").write_bytes(b"modified")
    assert tree_index(copied) != proof["world_original_file_indices"]["world_nether"]
