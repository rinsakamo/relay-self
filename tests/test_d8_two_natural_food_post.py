"""D8 independent audit must never promote one cycle or second zero into two."""
from __future__ import annotations

import pytest

from tools.bug0_d8_two_natural_food_post import (
    D8TwoCycleAuditRejected,
    audit_two_natural_food_cycles,
)


@pytest.mark.parametrize("mutant", [
    {},
    {"status": "PASS_DEV"},
    {"status": "PASS_DEV", "d8_two_generation_optin": True},
    {"status": "PASS_DEV", "d8_two_generation_optin": True,
     "d8_second_generation_food_proven": True},
    {"status": "PASS_DEV", "d8_two_generation_optin": True,
     "d8_second_generation_food_proven": True, "self_eat": True},
])
def test_one_original_world_report_cannot_claim_two_natural_food_cycles(
    mutant, tmp_path,
):
    with pytest.raises(D8TwoCycleAuditRejected):
        audit_two_natural_food_cycles(
            mutant, "",
            nonmotion_path=tmp_path/"absent-original-nonmotion.json",
            motion_path=tmp_path/"absent-original-motion.json",
        )


def test_operator_staged_item_never_qualifies_second_natural_food(tmp_path):
    with pytest.raises(D8TwoCycleAuditRejected):
        audit_two_natural_food_cycles(
            {
                "status": "PASS_DEV", "real_world_started": True,
                "d8_two_generation_optin": True,
                "node_exit": 0, "java_exit": 0, "cleanup_done": True,
                "original_action_issuer": "S49", "real_model_calls": 0,
                "learning_updated": False, "self_eat": True,
            },
            "RSELF_LOOT_STAGED world=forged",
            nonmotion_path=tmp_path/"missing-eat-ledger",
            motion_path=tmp_path/"missing-move-ledger",
        )
