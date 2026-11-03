"""M #616 WorldTick energy gate, synthetic S49-report-shaped source only.

These tests do NOT execute Minecraft or admit any physical B0 energy debit.
"""
from __future__ import annotations

from copy import deepcopy
from dataclasses import replace

import pytest

from experiments.metabolism_s49_worldtick_energy_gate import (
    audit_original_s49_energy_coverage,
    bounded_world_tick_energy_gate,
)


def _saved():
    sid = "synthetic-dev-only-session"
    decisions = [
        {"selected": "WAIT", "issued": False, "event_seq": 8, "probe_seq": 9},
        {"selected": "MOVE_AWAY", "issued": True, "event_seq": 20, "probe_seq": 21},
        {"selected": "MOVE_AWAY", "issued": True, "event_seq": 48, "probe_seq": 49},
    ]
    def native(epoch, before, after, time):
        return {
            "action": f"s49-native-move-{epoch}",
            "event_seq": epoch, "probe_seq": epoch + 1,
            "terminal": "outcome",
            "execution_evidence": {
                "action_id": f"s49-native-move-{epoch}",
                "session_id": sid, "status": "executed",
                "before_observation": {
                    "session_id": sid, "kind": "probe", "seq": before,
                    "snapshot": {"time": {"time_of_day": time}},
                },
                "after_observation": {
                    "session_id": sid, "kind": "probe", "seq": after,
                    "snapshot": {"time": {"time_of_day": time}},
                },
            },
        }
    actions = [native(20, 22, 29, 239), native(48, 50, 57, 439)]
    b0 = {
        "status": "RECORDED", "session_id": sid,
        "decision_count": 3, "decision_probe_seqs": [9, 21, 49],
        "decision_kinds": ["WAIT", "WAIT", "WAIT"],
        "owner_model_tick": 0, "energy_transitions": 0,
        "energy_debits": 0, "food_credits": 0,
        "source_attested": False, "action_authority": False,
        "true_world_energy": "UNKNOWN_NO_PHYSICAL_ENERGY_TICK",
        "b0_owner_model_energy": "UNADVANCED_INITIAL_STATE_NOT_PHYSICAL_COST",
    }
    original_l0 = {
        "session_id": sid, "step_count": 3, "outcome_count": 2,
        "real_b0_decision_supplied": False,
        "source_attested": False, "action_authority": False,
        "energy_debits": 0,
    }
    s14 = {
        "session_id": sid, "status": "RECORDED",
        "move_epoch_count": 2, "wait_epoch_count": 0,
        "source_attested": False, "action_authority": False,
        "energy_debits": 0,
    }
    s49 = {
        "session_id": sid, "status": "PASS", "stage": "CLOSED",
        "node_exit": 0, "server_exit": 0, "decisions": decisions,
        "actual_native_actions": actions,
        "original_b0_decision_readback": b0,
        "original_completion_readback": original_l0,
        "original_planned_readback": s14,
        "original_b0_decision_observer": "CALLBACK_RETURNED",
        "original_completion_observer": "CALLBACK_RETURNED",
        "original_planned_observer": "CALLBACK_RETURNED",
    }
    m_b0 = dict(
        b0, decisions=[{"b0_kind": "WAIT", "probe_seq": i} for i in (9, 21, 49)],
        energy_transition_count=0,
    )
    m_s14 = {
        "status": "RECORDED",
        "m_original_s14_planned": {"status": "RECORDED"},
        "m_original_s16_receipts": {"status": "RECORDED", "session_id": sid},
        "m_admission": {"status": "RECORDED", "session_id": sid},
    }
    m = {
        "status": "RECORDED", "m_original_b0_decision_only": m_b0,
        "m_s14_original_join": m_s14,
        "original_b0_callbacks": 1, "energy_debits": 0,
        "new_native_reads": 0, "new_action_issues": 0, "new_model_calls": 0,
    }
    return s49, m


def test_historical_s49_b0_realistic_shape_stays_deferred_without_fulltick():
    s49, m = _saved()
    result = audit_original_s49_energy_coverage(s49, m)
    assert result.status == "DEFERRED"
    assert result.reason == "S49_NATIVE_EVENT_SEQ_NOT_CONTINUOUS_WORLD_TICK"
    row = bounded_world_tick_energy_gate(result)
    assert row["original_decisions"] == 3
    assert row["original_actions"] == 2
    assert row["original_b0_decisions"] == 3
    assert row["consecutive_world_ticks"] is None
    assert not row["physical_energy_debit_admitted"]
    assert row["energy_debits"] == row["paid_basal_ticks"] == 0
    assert row["native_full_tick_coverage"] == "NOT_SUPPLIED"
    assert row["true_world_energy"] == "UNKNOWN_NO_PHYSICAL_ENERGY_TICK"


@pytest.mark.parametrize("attack", [
    "wrong_session", "fake_debit", "fake_food", "wrong_b0_seq",
    "wrong_event", "wrong_native_provenance", "copy_source",
    "missing_after", "bad_s14", "no_callback", "node_nonzero",
    "wrong_b0_tick", "real_b0_claim", "duplicate_l0", "unknown_b0_status",
])
def test_foreign_inconsistent_source_is_rejected_not_charged(attack):
    s, m = _saved()
    if attack == "wrong_session":
        m["m_original_b0_decision_only"]["session_id"] = "other"
    elif attack == "fake_debit":
        m["energy_debits"] = 1
    elif attack == "fake_food":
        s["original_b0_decision_readback"]["food_credits"] = 1
    elif attack == "wrong_b0_seq":
        s["original_b0_decision_readback"]["decision_probe_seqs"] = [9, 21, 48]
    elif attack == "wrong_event":
        s["actual_native_actions"][0]["event_seq"] = 33
    elif attack == "wrong_native_provenance":
        s["actual_native_actions"][0]["execution_evidence"]["session_id"] = "other"
    elif attack == "copy_source":
        s["actual_native_actions"][0]["action"] = "fake"
    elif attack == "missing_after":
        del s["actual_native_actions"][0]["execution_evidence"]["after_observation"]
    elif attack == "bad_s14":
        s["original_planned_readback"]["move_epoch_count"] = 9
    elif attack == "no_callback":
        s["original_b0_decision_observer"] = "OBSERVER_ERROR"
    elif attack == "node_nonzero":
        s["node_exit"] = 1
    elif attack == "wrong_b0_tick":
        s["original_b0_decision_readback"]["owner_model_tick"] = 100
    elif attack == "real_b0_claim":
        s["original_completion_readback"]["real_b0_decision_supplied"] = True
    elif attack == "duplicate_l0":
        s["decisions"][2]["probe_seq"] = 21
    elif attack == "unknown_b0_status":
        m["m_original_b0_decision_only"]["status"] = "UNKNOWN"
    result = audit_original_s49_energy_coverage(s, m)
    row = bounded_world_tick_energy_gate(result)
    assert result.status == "SOURCE_REJECTED"
    assert row["energy_debits"] == 0 and row["original_actions"] == 0
    assert row["session_id"] is None


def test_arbitrary_json_clock_claim_does_not_admit_energy_debit():
    original, m = _saved()
    for s in (
        original,
        deepcopy(original),
    ):
        s["continuous_world_ticks_verified"] = True
        s["world_time_samples"] = [239, 240, 241]
        s["world_age_ticks"] = "200"
        s["real_energy_credits"] = 50
        m["source_attested"] = True
        result = audit_original_s49_energy_coverage(s, m)
        assert result.status == "DEFERRED"
        assert result.energy_debits == 0
        assert result.consecutive_world_ticks is None


@pytest.mark.parametrize("field,value", [
    ("energy_debits", 1),
    ("paid_basal_ticks", 3),
    ("consecutive_world_ticks", 20),
    ("source_attested", True),
    ("native_full_tick_coverage", "ATTESTED"),
    ("action_authority", True),
    ("physical_food_credits", 1),
])
def test_bounded_renderer_never_accepts_minted_world_tick_fields(field, value):
    s, m = _saved()
    original = audit_original_s49_energy_coverage(s, m)
    with pytest.raises(ValueError):
        bounded_world_tick_energy_gate(replace(original, **{field: value}))
