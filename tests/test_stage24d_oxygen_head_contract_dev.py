"""Stage24d contract tests: source-qualified oxygen and head volume; no World."""
from __future__ import annotations

from dataclasses import replace
from pathlib import Path

import pytest

from relay_self.head_breathing_context_dev import (
    HeadBreathingContext,
    HeadVolumeCell,
    assess_head_breathing_context,
)
from relay_self.mineflayer_oxygen_patch_dev import (
    OWNERLESS,
    SELF_OWNED,
    MineflayerOxygenPatchRefusal,
    require_owned_mineflayer_oxygen_patch,
)
from relay_self.provenance import Provenance


def _fixture(tmp_path: Path, source: str) -> Path:
    bridge = tmp_path / "adapters" / "mineflayer"
    f = bridge / "node_modules" / "mineflayer" / "lib" / "plugins" / "entities.js"
    f.parent.mkdir(parents=True)
    f.write_text(source)
    return bridge


def test_owner_backport_fails_on_original_and_unrecognized_file(tmp_path):
    bridge = _fixture(tmp_path, OWNERLESS)
    with pytest.raises(MineflayerOxygenPatchRefusal, match="not verified"):
        require_owned_mineflayer_oxygen_patch(bridge)
    source = bridge / "node_modules" / "mineflayer" / "lib" / "plugins" / "entities.js"
    source.write_text("garbled version")
    with pytest.raises(MineflayerOxygenPatchRefusal, match="not verified"):
        require_owned_mineflayer_oxygen_patch(bridge)


def test_owner_backport_accepts_exact_one_guard_and_rejects_ambiguous_mix(tmp_path):
    bridge = _fixture(tmp_path, SELF_OWNED)
    assert require_owned_mineflayer_oxygen_patch(bridge).startswith("mineflayer-4.39.0+")
    path = bridge / "node_modules" / "mineflayer" / "lib" / "plugins" / "entities.js"
    path.write_text(SELF_OWNED + "\n" + OWNERLESS)
    with pytest.raises(MineflayerOxygenPatchRefusal, match="not verified"):
        require_owned_mineflayer_oxygen_patch(bridge)


def test_owner_backport_never_follows_source_symlink(tmp_path):
    bridge = _fixture(tmp_path, SELF_OWNED)
    source = bridge / "node_modules" / "mineflayer" / "lib" / "plugins" / "entities.js"
    external = tmp_path / "foreign.js"
    external.write_text(SELF_OWNED)
    source.unlink()
    source.symlink_to(external)
    with pytest.raises(MineflayerOxygenPatchRefusal, match="missing"):
        require_owned_mineflayer_oxygen_patch(bridge)


AIR = HeadVolumeCell(loaded=True, material="AIRLIKE", fluid="NONE")
WATER = HeadVolumeCell(loaded=True, material="FLUID", fluid="WATER")
SOLID = HeadVolumeCell(loaded=True, material="SOLID", fluid="NONE")


def _head(**changes):
    fields = {
        "session_id": "synthetic-source",
        "source_seq": 12,
        "source_request_id": "read-12",
        "source": Provenance("synthetic", "not-paper"),
        "measured_head_position": True,
        "fresh": True,
        "eye_cell": AIR,
        "upper_head_cell": AIR,
        "is_in_water": False,
    }
    fields.update(changes)
    return HeadBreathingContext(**fields)


@pytest.mark.parametrize(
    ("modified", "classification"),
    [
        ({}, "HEAD_AIRLIKE_OBSERVED"),
        ({"eye_cell": WATER}, "HEAD_FLUID_PRESENT"),
        ({"upper_head_cell": WATER}, "HEAD_FLUID_PRESENT"),
        ({"eye_cell": SOLID}, "HEAD_OBSTRUCTED"),
        ({"eye_cell": HeadVolumeCell(False, None, None)}, "UNKNOWN"),
        ({"upper_head_cell": HeadVolumeCell(True, "OTHER", None)}, "UNKNOWN"),
        ({"measured_head_position": False}, "UNKNOWN"),
        ({"fresh": False}, "UNKNOWN"),
        ({"eye_cell": AIR, "is_in_water": True}, "HEAD_AIRLIKE_OBSERVED"),
    ],
)
def test_head_space_medium_never_proves_breathability_or_grants_move(
    modified, classification,
):
    actual = assess_head_breathing_context(_head(**modified))
    assert actual.classification == classification
    assert actual.proven_breathable is False
    assert actual.grants_move is False


def test_inwater_false_alone_never_proves_airlike_head():
    assessment = assess_head_breathing_context(_head(
        eye_cell=WATER, is_in_water=False,
    ))
    assert assessment.classification == "HEAD_FLUID_PRESENT"
    assert not assessment.proven_breathable


def test_head_context_is_source_bound_and_rejects_invalid_cases():
    with pytest.raises(ValueError, match="source-qualified"):
        _head(source_request_id="")
    with pytest.raises(ValueError, match="typed or unknown"):
        HeadVolumeCell(True, "DIAMOND", "NONE")
    with pytest.raises(ValueError, match="explicit"):
        HeadVolumeCell("yes", "AIRLIKE", "NONE")
    assert replace(AIR, loaded=False).loaded is False
