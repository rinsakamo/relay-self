"""D6-E1 native item-approach rejection is read-only, not an Action grant."""
from __future__ import annotations

from dataclasses import replace

from test_d6_loot_approach import pair
from tools.bug0_d6_staged_move_world import item_source_readback


def test_rejected_source_preserves_both_original_native_views():
    before, current = pair()
    second = replace(
        current,
        snapshot=replace(
            current.snapshot,
            position=replace(current.snapshot.position,
                             x=current.snapshot.position.x + 0.11),
        ),
    )
    first = item_source_readback(before)
    observed = item_source_readback(second)
    assert first["native_seq"] < observed["native_seq"]
    assert first["session_id"] == observed["session_id"]
    assert first["source_ref"] == before.provenance.reference
    assert observed["request_id"] == second.request_id
    assert observed["yaw_rad"] == second.snapshot.native_orientation.yaw_rad
    assert observed["nearby_entities"][0]["id"] == 42
    assert observed["nearby_entities"][0]["name"] == "item"
    assert first["position"]["x"] != observed["position"]["x"]
    assert not first["additional_native_probe"]
    assert not first["physical_authority"]
    assert observed["read_only"]


def test_readback_records_native_coverage_without_elevating_authority():
    a, _ = pair()
    s = item_source_readback(a)
    assert s["truncated"] is False
    assert s["candidate_count"] == 1
    assert s["nearby_entities"][0]["distance"] == 2.2
    assert "position" in s["nearby_entities"][0]
    assert not s["physical_authority"] and not s["additional_native_probe"]
