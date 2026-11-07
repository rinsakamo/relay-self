"""D6-E1 native item-approach rejection is read-only, not an Action grant."""
from __future__ import annotations

import asyncio
from dataclasses import replace
from types import SimpleNamespace

import pytest

from test_d6_loot_approach import pair
from tools import bug0_d6_staged_move_world as world
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


def test_existing_fail_closed_source_gate_records_exact_two_probes(monkeypatch):
    before, current = pair()
    current = replace(
        current,
        snapshot=replace(
            current.snapshot,
            position=replace(
                current.snapshot.position,
                x=current.snapshot.position.x + .10,
            ),
        ),
    )
    reads = [before, current]

    async def native_original_read(_session, _request_id):
        return reads.pop(0)

    async def no_wait(_seconds):
        return None

    monkeypatch.setattr(world, "_correlated_observe", native_original_read)
    monkeypatch.setattr(world.asyncio, "sleep", no_wait)
    session = SimpleNamespace(
        started=SimpleNamespace(session_id=before.session_id),
    )
    report = {}
    with pytest.raises(world.D6StagedMoveRejected, match="original D6 native"):
        asyncio.run(world.move_from_real_item(
            session, report, None, fence=None,
        ))
    assert reads == []
    assert len(report["d6_original_item_gate_rejections"]) == 1
    rec = report["d6_original_item_gate_rejections"][0]
    assert rec["reason_class"] == "D6LootApproachRejected"
    assert "not stationary" in rec["reason"]
    assert rec["issued_moves_before_rejection"] == 0
    assert rec["native_before"]["native_seq"] == before.seq
    assert rec["native_current"]["native_seq"] == current.seq
    assert rec["native_before"]["session_id"] == before.session_id
    assert not rec["reissue_on_rejection"]
    assert rec["read_only"]
    assert report["d6_original_s49_move_actions"] == []
