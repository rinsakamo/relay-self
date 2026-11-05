"""R1 post-audit rejects fake 600-tick / native-source success."""
from copy import deepcopy

import pytest

from tools.bug0_zombie_respawn_r1_post import RespawnAuditError, audit

W = "11111111-1111-4111-8111-111111111111"
A = "22222222-2222-4222-8222-222222222222"
B = "33333333-3333-4333-8333-333333333333"
LOG = (
    f"RSELF_RESPAWN_INITIAL world={W} entity={A} generation=1 tick=100\n"
    f"RSELF_RESPAWN_DEATH world={W} entity={A} generation=1 tick=130 due_tick=730\n"
    f"RSELF_RESPAWN_SPAWN world={W} entity={B} generation=2 tick=730\n"
)
REPORT = {
    "status": "PASS_DEV", "operator_kill": True, "original_s49_actions": 0,
    "node_exit": 0, "java_exit": 0, "session_id": "s",
    "native_initial": {"session_id": "s", "seq": 10, "zombie_entity_id": 8},
    "native_respawn": {"session_id": "s", "seq": 20, "zombie_entity_id": 9},
    "paper_initial": "RSELF_RESPAWN_INITIAL world=" + W,
    "paper_death": "RSELF_RESPAWN_DEATH world=" + W,
    "paper_respawn": "RSELF_RESPAWN_SPAWN world=" + W,
}


def test_positive():
    result = audit(LOG, REPORT)
    assert result["delay_ticks_observed"] == 600
    assert result["autonomous_self_kill"] is False


@pytest.mark.parametrize("log", [
    LOG.replace("due_tick=730", "due_tick=729"),
    LOG.replace("generation=2", "generation=1"),
    LOG.replace(f"entity={B}", f"entity={A}"),
    LOG.replace("tick=730\n", "tick=729\n"),
    LOG + LOG.splitlines()[-1] + "\n",
    LOG.replace("RSELF_RESPAWN_DEATH", "RSELF_NOT_DEATH"),
    LOG + "RSELF_RESPAWN_FAULT reason=BAD\n",
])
def test_bad_paper(log):
    with pytest.raises(RespawnAuditError):
        audit(log, REPORT)


@pytest.mark.parametrize("key,val", [
    ("status", "FAIL"),
    ("operator_kill", False),
    ("original_s49_actions", 1),
    ("node_exit", 1),
    ("session_id", "other"),
])
def test_bad_report(key, val):
    report = deepcopy(REPORT)
    report[key] = val
    with pytest.raises(RespawnAuditError):
        audit(LOG, report)


def test_native_duplicate():
    report = deepcopy(REPORT)
    report["native_respawn"]["zombie_entity_id"] = 8
    with pytest.raises(RespawnAuditError):
        audit(LOG, report)
