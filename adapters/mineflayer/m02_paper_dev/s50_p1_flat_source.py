"""Admit only the frozen native-proven seed63101 FLAT World as a DEV source.

The original stopped World is never booted.  This validates a fresh copy
source for P1 *candidate* sampling, without R qualification or P1 credit.
"""
from __future__ import annotations

import json
from pathlib import Path

from adapters.mineflayer.m02_paper_dev import s50_flat_base_foraging_dev as base
from adapters.mineflayer.m02_paper_dev import s50_flat_ground_dev as flat
from adapters.mineflayer.m02_paper_dev.v8_stopped_world_clone_dev import (
    need,
    sha,
    world_index,
)

CLASSIFICATION = "S50_P1_FLAT_SOURCE_DEV_ONLY_NOT_R_QUALIFIED"


def admit_flat_original(archive: Path, output: Path) -> list[dict]:
    """Read source bytes and canonical receipt; NEVER launch Minecraft."""
    need(archive.is_absolute() and archive.is_dir()
         and not archive.is_symlink() and output.is_absolute()
         and not output.exists() and output.parent.is_dir(),
         "FLAT P1 source must be an existing absolute archive and fresh output")
    for path in (archive, output.parent, archive / base.FLAT_SOURCE):
        need(not path.is_symlink()
             and not any(p.is_symlink() for p in path.parents),
             "symlinked FLAT archive/output/source forbidden")
    source = archive / base.FLAT_SOURCE
    need(source.is_dir() and (source / "level.dat").is_file(),
         "missing stopped FLAT World")
    expected = world_index(source)
    need(expected and sha(source / "level.dat") == base.LEVEL_SHA,
         "unexpected saved FLAT World original")
    receipt = json.loads((archive / "flat-source/flat_dev_receipt.json").read_text())
    need(receipt["status"] == "FLAT_GROUND_NATIVE_WITNESSED_DEV_ONLY"
         and receipt["classification"] == flat.CLASSIFICATION
         and receipt["native_surface_witnesses"] == 25
         and receipt["native_missing_markers"] == []
         and receipt["requested_seed"] == flat.FLAT_DEV_SEED
         and receipt["java_exit"] == 0
         and receipt["mineflayer_sessions"] == 0
         and receipt["stopped_world_index"] == expected,
         "FLAT native surface receipt mismatch")
    original_log = (archive / "flat-source/paper_console.log").read_text()
    need(len(flat.extract_native_witnesses(original_log)) == 25,
         "missing native flat 25/25 ground/air source markers")
    props = (archive / "flat-source/server/server.properties").read_bytes()
    need(b"level-seed=63101" in props and b"level-type=" in props
         and b"flat" in props and b"normal" not in props,
         "FLAT world properties did not originate from flat source")
    resolved_source, resolved_archive = source.resolve(), archive.resolve()
    resolved_output = output.resolve(strict=False)
    need(resolved_source != resolved_output
         and resolved_output not in resolved_archive.parents
         and resolved_archive not in resolved_output.parents
         and not resolved_output.is_relative_to(resolved_archive)
         and not resolved_archive.is_relative_to(resolved_output),
         "FLAT original overlaps mutable DEV output")
    return expected


def verify_copy(original: Path, copied: Path, expected: list[dict]) -> dict:
    """Bytes before starting Java. Never equate a copy with new World UUID."""
    need(original.is_dir() and copied.is_dir()
         and world_index(original) == expected
         and world_index(copied) == expected,
         "FLAT source or its DEV copy drifted")
    return {
        "classification": CLASSIFICATION,
        "source_level_sha256": base.LEVEL_SHA,
        "source_seed": flat.FLAT_DEV_SEED,
        "copied_world_bytes_equal_to_original": True,
        "independent_new_world_uuid": False,
        "R_qualified": False,
        "p1_wait_ticks_admitted": 0,
        "p1_fatigue_recovered": 0.0,
    }
