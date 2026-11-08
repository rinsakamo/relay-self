"""D12 negative provenance tests (no Minecraft World or physical issuer)."""
from __future__ import annotations

from copy import deepcopy

import pytest

from tools.bug0_d12_third_intent_rearm_post import (
    D12ThirdAuditRejected,
    require_third_rearm,
)


WORLD = "11111111-1111-4111-8111-111111111111"
Z1 = "22222222-2222-4222-8222-222222222222"
Z2 = "33333333-3333-4333-8333-333333333333"
Z3 = "44444444-4444-4444-8444-444444444444"
S = "original-native-session"
THIRD = (
    f"RSELF_RESPAWN_SPAWN world={WORLD} generation=3 "
    f"entity={Z3} tick=1600"
)


def sample() -> tuple[dict, str]:
    return {
        "status": "PASS_DEV",
        "session_id": S,
        "initial_paper": f"RSELF_RESPAWN_INITIAL world={WORLD} entity={Z1} tick=1",
        "native_initial": {"zombie_entity_id": 70},
        "native_respawn": {"zombie_entity_id": 81},
        "d8_intent_rearm": {"next_intent": "food-gen2"},
        "d8_second_generation": {
            "death_tick": 1000, "paper_zombie_uuid": Z2,
            "d7f_eat_outcome": {"action_id": "second-original-s51"},
        },
        "d8_second_generation_food_proven": True,
        "d12_third_intent_rearm_optin": True,
        "d12_third_rearm_proven": True,
        "d12_third_rearm_stage": "THIRD_WORLD_NEW_INTENT_NO_ACTION_DEV_PASS",
        "d12_third_paper_spawn": THIRD,
        "learning_updated": False,
        "real_model_calls": 0,
        "d12_third_rearm": {
            "session_id": S,
            "same_supervisor": True,
            "same_world": True,
            "original_s49_epoch": 3,
            "completed_intent_id": "food-gen2",
            "new_intent_id": "food-gen3",
            "third_zombie_native_id": 92,
            "previous_zombie_native_id": 81,
            "third_paper_zombie_uuid": Z3,
            "native_source_seq": 333,
            "native_request_id": "read-third",
            "paper_spawn_tick": 1600,
            "second_death_tick": 1000,
            "prior_original_action_count": 6,
            "after_rearm_original_action_count": 6,
            "third_physical_action_count": 0,
            "prior_second_s51_action_id": "second-original-s51",
            "prior_s51_receipt_consumed": True,
            "no_physical_reissue": True,
            "no_new_learning": True,
        },
    }, THIRD + "\n"


def test_genuine_three_epoch_zero_new_action() -> None:
    report, paper = sample()
    a = require_third_rearm(report, paper)
    assert a["status"] == "PASS_DEV"
    assert a["third_spawn_after_exactly_600_world_ticks"] is True
    assert a["third_real_attack_or_eat"] is False


@pytest.mark.parametrize(
    ("path", "value"),
    [
        (("d12_third_rearm", "original_s49_epoch"), 2),
        (("d12_third_rearm", "same_supervisor"), False),
        (("d12_third_rearm", "prior_s51_receipt_consumed"), False),
        (("d12_third_rearm", "third_physical_action_count"), 1),
        (("d12_third_rearm", "after_rearm_original_action_count"), 7),
        (("d12_third_rearm", "prior_second_s51_action_id"), "reused-first"),
        (("d12_third_rearm", "completed_intent_id"), "stale-previous"),
        (("d12_third_rearm", "third_zombie_native_id"), 81),
        (("d12_third_rearm", "second_death_tick"), 999),
        (("d12_third_rearm_proven",), False),
        (("d8_second_generation_food_proven",), False),
        (("real_model_calls",), 1),
        (("learning_updated",), True),
    ],
)
def test_reject_forged_rearm_fields(path: tuple[str, ...], value: object) -> None:
    report, paper = sample()
    altered = deepcopy(report)
    node = altered
    for p in path[:-1]:
        node = node[p]
    node[path[-1]] = value
    with pytest.raises(D12ThirdAuditRejected):
        require_third_rearm(altered, paper)


def test_reject_non_600_tick_paper() -> None:
    report, paper = sample()
    forged = THIRD.replace("tick=1600", "tick=1599")
    report["d12_third_paper_spawn"] = forged
    with pytest.raises(D12ThirdAuditRejected):
        require_third_rearm(report, forged + "\n")


def test_reject_missing_or_duplicate_original_paper() -> None:
    report, paper = sample()
    with pytest.raises(D12ThirdAuditRejected):
        require_third_rearm(report, "")
    with pytest.raises(D12ThirdAuditRejected):
        require_third_rearm(report, paper + paper)


def test_reject_paper_other_world_or_reused_zombie() -> None:
    report, paper = sample()
    for replace in (WORLD, Z3):
        forged = THIRD.replace(
            replace, Z1 if replace == Z3 else "55555555-5555-4555-8555-555555555555",
        )
        changed = deepcopy(report)
        changed["d12_third_paper_spawn"] = forged
        with pytest.raises(D12ThirdAuditRejected):
            require_third_rearm(changed, forged + "\n")
