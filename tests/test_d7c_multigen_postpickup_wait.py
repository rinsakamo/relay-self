"""D7-C2 passive witness: source-only wait applies to genuine later-generation pickup.

This helper never authorizes STOP or EAT or issues another physical Action.
"""
from __future__ import annotations

import pytest

from tools.bug0_d4_oneworld import d7c_has_independent_paper_pickup


def test_first_generation_authentic_paper_pickup_enables_only_passive_witness():
    assert d7c_has_independent_paper_pickup({
        "d4_paper_item_pickup": "RSELF_NATURAL_DROP_PICKUP world=real",
        "d6_original_s49_move_actions": [{"action_id": "move-first"}],
    }) is True


def test_vanilla_zero_then_next_generation_true_paper_pickup_enables_witness():
    report = {
        "d4_paper_item_pickup": None,
        "d6_multigen_generations": [
            {"generation": 1, "real_rotten_count": 0,
             "item_uuid": None, "item_pickup_tick": None},
            {"generation": 2, "real_rotten_count": 1,
             "item_uuid": "paper-genuine-uuid", "item_pickup_tick": 735},
        ],
        "d6_original_s49_move_actions": [{"action_id": "move-new-epoch"}],
    }
    assert d7c_has_independent_paper_pickup(report) is True


@pytest.mark.parametrize("bad", [
    {},
    {"d4_paper_item_pickup": None},
    {"d6_multigen_generations": []},
    {"d6_multigen_generations": [{"item_uuid": None, "item_pickup_tick": None}]},
    {"d6_multigen_generations": [{"item_uuid": "z", "item_pickup_tick": None}]},
    {"d6_multigen_generations": [{"item_uuid": "z", "item_pickup_tick": -1}]},
    {"d6_multigen_generations": [{"item_uuid": "z", "item_pickup_tick": True}]},
    {"d6_multigen_generations": [{"item_uuid": "", "item_pickup_tick": 733}]},
    {"d6_multigen_generations": "not-original-list"},
])
def test_no_source_positive_pickup_stays_unexercised(bad):
    assert d7c_has_independent_paper_pickup(bad) is False
