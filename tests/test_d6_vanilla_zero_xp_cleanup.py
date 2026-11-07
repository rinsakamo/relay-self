"""DEV-only XP residual cleanup after a genuine vanilla random zero.

The operator never creates/despawns meat or changes doMobLoot in this phase.
These are source-only negative tests, World0 and physical Action0.
"""
from __future__ import annotations

import pytest

from tools.bug0_d6_multigen_post import (
    MultigenAuditRejected,
    require_vanilla_zero_xp_cleanup,
)


XP_COMMAND = (
    "execute at RelaySelf run kill "
    "@e[type=minecraft:experience_orb,distance=..8]"
)


def epoch(natural_count: int) -> dict:
    return {"real_rotten_count": natural_count}


def scoped(generation: int) -> dict:
    return {
        "generation": generation,
        "after_real_zero_generation": generation-1,
        "command": XP_COMMAND,
        "only_experience_orbs": True,
        "all_item_entities_untouched": True,
        "world_loot_rule_unchanged": True,
        "operator_dev_intervention": True,
    }


def test_no_cleanup_when_first_normal_zombie_drops_real_food():
    require_vanilla_zero_xp_cleanup([epoch(1)], [])


def test_actual_zero_then_next_real_zombie_requires_xp_only_operator_cleanup():
    require_vanilla_zero_xp_cleanup(
        [epoch(0), epoch(1)], [scoped(2)],
    )
    require_vanilla_zero_xp_cleanup(
        [epoch(0), epoch(0), epoch(2)], [scoped(2), scoped(3)],
    )


@pytest.mark.parametrize("mutation", [
    "no_cleanup", "wrong_generation", "wrong_previous",
    "kill_all_items", "give_rotten", "world_loot_modified", "no_operator",
    "meat_entity_discarded", "not_xp_only", "prior_positive",
])
def test_zero_loot_continuation_never_admits_forged_or_broad_cleanup(mutation):
    generations = [epoch(0), epoch(1)]
    rows = [scoped(2)]
    if mutation == "no_cleanup":
        rows = []
    elif mutation == "wrong_generation":
        rows[0]["generation"] = 3
    elif mutation == "wrong_previous":
        rows[0]["after_real_zero_generation"] = 0
    elif mutation == "kill_all_items":
        rows[0]["command"] = "kill @e[type=!minecraft:player]"
    elif mutation == "give_rotten":
        rows[0]["command"] = "give RelaySelf minecraft:rotten_flesh 1"
    elif mutation == "world_loot_modified":
        rows[0]["world_loot_rule_unchanged"] = False
    elif mutation == "no_operator":
        rows[0]["operator_dev_intervention"] = False
    elif mutation == "meat_entity_discarded":
        rows[0]["all_item_entities_untouched"] = False
    elif mutation == "not_xp_only":
        rows[0]["only_experience_orbs"] = False
    elif mutation == "prior_positive":
        generations[0]["real_rotten_count"] = 1
    with pytest.raises(MultigenAuditRejected):
        require_vanilla_zero_xp_cleanup(generations, rows)
