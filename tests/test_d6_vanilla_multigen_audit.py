"""D6-D5: vanilla Paper loot mode and read-only item rejection preworld negatives.

No Paper World or physical S49 Action is launched by this test.
"""
from __future__ import annotations

import pytest

from tools.bug0_d6_multigen_post import (
    MultigenAuditRejected,
    require_vanilla_paper_loot,
)


def paper(*events: str) -> str:
    return "\n".join(f"[Server thread/INFO]: {e}" for e in events)


def test_original_paper_world_temporarily_cleans_then_restores_vanilla_loot():
    raw = paper(
        "Gamerule doMobLoot is now set to: false",
        "Gamerule doMobLoot is now set to: true",
        "RSELF_RESPAWN_DEATH world=one generation=1 tick=80 paper_drops=0",
        "RSELF_RESPAWN_SPAWN world=one generation=2 tick=680",
        "RSELF_RESPAWN_DEATH world=one generation=2 tick=701 paper_drops=1",
    )
    require_vanilla_paper_loot(raw)


@pytest.mark.parametrize("events", [
    (),
    ("Gamerule doMobLoot is now set to: false",
     "RSELF_RESPAWN_DEATH world=one generation=1 tick=80 paper_drops=0"),
    ("RSELF_RESPAWN_DEATH world=one generation=1 tick=80 paper_drops=0",
     "Gamerule doMobLoot is now set to: true"),
    ("Gamerule doMobLoot is now set to: true",
     "Gamerule doMobLoot is now set to: false",
     "RSELF_RESPAWN_DEATH world=one generation=1 tick=80 paper_drops=0"),
    ("Gamerule doMobLoot is now set to: true",
     "RSELF_RESPAWN_DEATH world=one generation=1 tick=80 paper_drops=0",
     "Gamerule doMobLoot is now set to: false",
     "RSELF_RESPAWN_DEATH world=one generation=2 tick=701 paper_drops=0"),
])
def test_audit_rejects_forced_zero_or_missing_normal_world_law(events):
    with pytest.raises(MultigenAuditRejected):
        require_vanilla_paper_loot(paper(*events))


def test_audit_accepts_world_true_through_real_multigen_deaths():
    require_vanilla_paper_loot(paper(
        "Gamerule doMobLoot is now set to: true",
        "RSELF_RESPAWN_DEATH world=one generation=1 tick=80 paper_drops=0",
        "RSELF_RESPAWN_SPAWN world=one generation=2 tick=680",
        "RSELF_RESPAWN_DEATH world=one generation=2 tick=710 paper_drops=0",
        "RSELF_RESPAWN_SPAWN world=one generation=3 tick=1310",
        "RSELF_RESPAWN_DEATH world=one generation=3 tick=1340 paper_drops=2",
    ))
