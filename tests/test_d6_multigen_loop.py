"""D6-D3 continuous native zero-drop original S49 source-only DEV negatives.

Offline only. Never create a Paper World, touch a physical Action or infer a
zombie death from the owner-issued native ATTACK ACK.
"""
from __future__ import annotations

import asyncio

import pytest

from tools.bug0_d6_multigen_post import MultigenAuditRejected, audit
from tools.bug0_d6_multigen_world import (
    MultiGenerationDevRejected,
    _rotten,
    _tick,
    _uuid,
    one_source_line,
)
from tools.bug0_d4_oneworld import run


def test_paper_generation_scoped_marker_is_unique():
    log = "\n".join([
        "RSELF_RESPAWN_SPAWN world=abc entity=def generation=2 tick=667",
        "RSELF_RESPAWN_SPAWN world=abc entity=ghi generation=3 tick=1280",
        "RSELF_NATURAL_DROP_DEATH world=abc zombie=def tick=680 rotten_count=0",
    ])
    assert "tick=667" in one_source_line(
        log, "RSELF_RESPAWN_SPAWN world=", token="generation=2 ",
    )
    assert "tick=1280" in one_source_line(
        log, "RSELF_RESPAWN_SPAWN world=", token="generation=3 ",
    )
    assert one_source_line(
        log, "RSELF_RESPAWN_SPAWN world=", token="generation=4 ",
    ) is None
    assert _rotten(one_source_line(log, "RSELF_NATURAL_DROP_DEATH world=")) == 0


def test_repeated_same_generation_paper_source_is_rejected():
    raw="RSELF_RESPAWN_SPAWN world=x entity=foo generation=3 tick=100"
    with pytest.raises(MultiGenerationDevRejected):
        one_source_line(raw + "\n" + raw,
                        "RSELF_RESPAWN_SPAWN world=", token="generation=3 ")


@pytest.mark.parametrize("text", [
    "RSELF_NATURAL_DROP_DEATH world=x zombie=a rotten_count=-1",
    "RSELF_NATURAL_DROP_DEATH world=x zombie=a rotten_count=3",
    "RSELF_NATURAL_DROP_DEATH world=x zombie=a",
    "RSELF_NATURAL_DROP_DEATH world=x zombie=a rotten_count=false",
])
def test_zero_real_world_rng_never_assumes_positive_food(text):
    with pytest.raises(MultiGenerationDevRejected):
        _rotten(text)


@pytest.mark.parametrize("text", ["no tick", " tick=x", " tick=-2"])
def test_invalid_paper_ticks_refused(text):
    if text.endswith("-2"):
        assert _tick(text) == -2
        return
    with pytest.raises(MultiGenerationDevRejected):
        _tick(text)


def test_missing_uuid_refuses_fabricated_identity():
    with pytest.raises(MultiGenerationDevRejected):
        _uuid("world=none", "zombie")


def test_multigen_pre_world_refuses_without_separate_scope(monkeypatch, tmp_path):
    for key in (
        "S49_REAL_SERVER_CI", "BUG0_S49_D4_ONE_WORLD_ONLY",
        "S49_D5_NONMOTION_FENCE_DEV_ONLY",
        "D6_NATURAL_DROP_MOVE_WORLD_ONLY", "D6_NATURAL_MULTIGEN_WORLD_ONLY",
    ):
        monkeypatch.delenv(key, raising=False)
    report=tmp_path/"report.json"
    result=asyncio.run(run(
        report, tmp_path/"paper.log",
        nonmotion_fence_path=tmp_path/"attack-ledger.json",
        motion_fence_path=tmp_path/"move-ledger.json",
        post_death_loot_move_dev=lambda *args, **kwargs: None,
        post_respawn_dev=lambda *args, **kwargs: None,
        d6_multigen_dev=True,
    ))
    assert result != 0
    assert not (tmp_path/"attack-ledger.json").exists()
    assert not (tmp_path/"move-ledger.json").exists()
    assert not (tmp_path/"paper.log").exists()


def test_independent_audit_rejects_unsupported_lifetime_claim(tmp_path):
    with pytest.raises(MultigenAuditRejected):
        audit("", {"status":"PASS_DEV", "cleanup_done": True},
              nonmotion_path=tmp_path/"a.json", motion_path=tmp_path/"m.json")
    with pytest.raises(MultigenAuditRejected):
        audit("RSELF_RESPAWN_FAULT", {
            "status":"PASS_DEV", "cleanup_done": True,
            "d6_multigen_same_supervisor": True,
        }, nonmotion_path=tmp_path/"a.json",
              motion_path=tmp_path/"m.json")
