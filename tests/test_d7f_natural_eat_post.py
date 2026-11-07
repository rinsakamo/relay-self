"""Reject forged D7-F full natural food cycles before physical source reads."""
from __future__ import annotations

import pytest

from tools.bug0_d7f_natural_eat_post import D7FNaturalAuditRejected, audit


@pytest.mark.parametrize("bad", [
    {},
    {"status": "PASS_DEV"},
    {"status": "PASS_DEV", "real_world_started": True},
    {"status": "PASS_DEV", "real_world_started": True,
     "d7f_live_eat_optin": True},
    {"status": "PASS_DEV", "real_world_started": True,
     "d7f_live_eat_optin": True, "original_action_issuer": "S49"},
])
def test_cannot_invent_natural_food_from_a_report(bad, tmp_path):
    with pytest.raises(D7FNaturalAuditRejected):
        audit(
            "RSELF_LOOT_STAGED fake=true",
            bad,
            "",
            nonmotion_path=tmp_path/"not-a-physical-attack-ledger",
            motion_path=tmp_path/"not-a-MOVE-ledger",
        )


def test_staged_food_never_qualifies_original_natural_drop(tmp_path):
    report = {
        "status": "PASS_DEV", "cleanup_done": True,
        "node_exit": 0, "java_exit": 0, "real_world_started": True,
        "d7f_live_eat_optin": True,
        "original_action_issuer": "S49",
        "operator_staged_no_ai": True,
        "d7f_operator_hunger_effect_dev": True,
        "d6_no_hunger_intervention": False,
        "real_model_calls": 0, "learning_updated": False,
        "self_eat": True,
    }
    with pytest.raises(D7FNaturalAuditRejected):
        audit(
            "RSELF_LOOT_STAGED item=rotten_flesh",
            report, "SESSION_START", nonmotion_path=tmp_path/"no-attacks",
            motion_path=tmp_path/"no-move",
        )
