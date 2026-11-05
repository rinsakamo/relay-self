"""D1 Paper original pickup UUID and native inventory source negatives."""
from copy import deepcopy

import pytest

from tools.bug0_pickup_d1_post import PickupD1AuditRejected, audit


W = "11111111-1111-4111-8111-111111111111"
P = "22222222-2222-4222-8222-222222222222"
I = "33333333-3333-4333-8333-333333333333"
LOG = (
    f"RSELF_LOOT_STAGED world={W} owner={P} entity={I} item=rotten_flesh "
    "count=1 tick=120 source=OPERATOR_FIXTURE_NOT_ZOMBIE_DROP\n"
    f"RSELF_LOOT_PICKED world={W} owner={P} entity={I} item=rotten_flesh "
    "count=1 tick=122 source=ACTUAL_PAPER_PICKUP_EVENT\n"
)
REPORT = {
    "status": "PASS_DEV",
    "item_origin": "OPERATOR_FIXTURE_NOT_ZOMBIE_DROP",
    "original_s49_actions": 0, "self_action_issued": False,
    "zombie_kill_attested": False,
    "node_exit": 0, "java_exit": 0,
    "session_id": "s",
    "native_before": {"session_id": "s", "seq": 4, "rotten_flesh": 0},
    "native_after": {"session_id": "s", "seq": 9, "rotten_flesh": 1},
    "native_pickup_gain": {
        "item_name": "rotten_flesh",
        "outcome_scope": "NATIVE_INVENTORY_DELTA_ONLY",
        "before_count": 0, "after_count": 1,
    },
    "paper_staged": LOG.splitlines()[0],
    "paper_pickup": LOG.splitlines()[1],
}


def test_positive():
    x = audit(LOG, REPORT)
    assert x["native_rotten_flesh_delta"] == 1
    assert x["vanilla_zombie_drop_proven"] is False


@pytest.mark.parametrize("log", [
    LOG.replace(f"entity={I}", "entity=aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa", 1),
    LOG.replace("count=1 tick=122", "count=2 tick=122"),
    LOG.replace("tick=122", "tick=119"),
    LOG.replace("ACTUAL_PAPER_PICKUP_EVENT", "OPERATOR_FIXTURE_NOT_ZOMBIE_DROP"),
    LOG + LOG.splitlines()[-1] + "\n",
    LOG.replace("RSELF_LOOT_PICKED", "RSELF_NOT_PICKED"),
    LOG + "[ERROR] Paper plugin fault\n",
])
def test_paper_fail_closed(log):
    with pytest.raises(PickupD1AuditRejected):
        audit(log, REPORT)


@pytest.mark.parametrize("key,value", [
    ("original_s49_actions", 1),
    ("zombie_kill_attested", True),
    ("item_origin", "VANILLA_DROP"),
    ("node_exit", 1),
    ("status", "FAIL"),
])
def test_report_fail_closed(key, value):
    report = deepcopy(REPORT)
    report[key] = value
    with pytest.raises(PickupD1AuditRejected):
        audit(LOG, report)


def test_wrong_native_session_or_count():
    r = deepcopy(REPORT)
    r["native_after"]["session_id"] = "other"
    with pytest.raises(PickupD1AuditRejected):
        audit(LOG, r)
    r = deepcopy(REPORT)
    r["native_after"]["rotten_flesh"] = 2
    with pytest.raises(PickupD1AuditRejected):
        audit(LOG, r)
