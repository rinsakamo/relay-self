"""Fault classification needs native observation, not just an injection flag."""
from copy import deepcopy

import pytest

from adapters.mineflayer.t1k_fault_audit_dev import audit_fault_dev

AID = "t1j-T1J-R1-move"


def fixture(case):
    before = case == "t1k_fault_before_send"
    drop = case == "t1k_fault_clear_ack"
    commands = [] if before else [
        {"type": "effect", "effect": "set_control", "action_id": AID},
        {"type": "effect", "effect": "clear_controls", "action_id": AID + "-clear"}]
    native = [] if before else [
        {"type": "effect_result", "effect": "set_control", "action_id": AID,
         "session_id": "s", "seq": 100, "result": "applied"}]
    clear = {"type": "effect_result", "effect": "clear_controls", "action_id": AID + "-clear",
             "session_id": "s", "seq": 101, "result": "applied"}
    if drop:
        native.append(clear)
    else:
        native.append({"type": "connection_end", "session_id": "s", "seq": 102,
                       "reason": "socketClosed"})
    attempt = {"permit_consumed": True, "motor_send_attempted": not before,
               "permission_cleared": True, "old_owner_still_latched": True,
               "old_ledger_unchanged": True}
    if not before:
        attempt.update(terminal={"state": "unknown"},
                       consequence={"status": "failed", "cleanup_receipt": None})
    report = {"session_id": "s", "status": "FAIL", "fault_injection": {"kind": case},
              "resume_attempts_dev": [attempt], "dropped_clear_receipts": [clear] if drop else []}
    return commands, native, report


@pytest.mark.parametrize("case", ["t1k_fault_before_send", "t1k_fault_set_ack", "t1k_fault_clear_ack"])
def test_only_observed_fault_with_unknown_or_no_action_is_fail_closed(case):
    commands, native, report = fixture(case)
    result = audit_fault_dev(case, commands, native, report)
    assert result["classification"] == "FAULT_INJECTED_FAIL_CLOSED_DEV_OBSERVED"
    assert result["native_classification"] == "NATIVE_FAULT_OBSERVED"
    assert not result["safety_violation"]
    intent_only = audit_fault_dev(case, commands, [], report)
    assert intent_only["classification"] == "NATIVE_FAULT_UNDETERMINED"
    assert not intent_only["native_fault_observed"]


@pytest.mark.parametrize("fault", ["foreign_session", "shutdown_only", "clear_not_dropped",
                                  "duplicate_motor", "forged_outcome", "second_grant"])
def test_no_false_native_fault_pass_or_fabricated_outcome(fault):
    case = "t1k_fault_clear_ack" if fault == "clear_not_dropped" else "t1k_fault_set_ack"
    commands, native, report = fixture(case)
    if fault == "foreign_session":
        for row in native:
            row["session_id"] = "foreign"
    elif fault == "shutdown_only":
        native[-1]["reason"] = "RelaySelf adapter shutdown"
    elif fault == "clear_not_dropped":
        report["dropped_clear_receipts"] = []
    elif fault == "duplicate_motor":
        commands.append(deepcopy(commands[0]))
    elif fault == "forged_outcome":
        report["resume_attempts_dev"][0]["terminal"]["state"] = "outcome"
    else:
        report["resume_attempts_dev"].append(deepcopy(report["resume_attempts_dev"][0]))
    result = audit_fault_dev(case, commands, native, report)
    assert result["classification"] != "FAULT_INJECTED_FAIL_CLOSED_DEV_OBSERVED"
    if fault in {"duplicate_motor", "forged_outcome", "second_grant"}:
        assert result["classification"] == "SAFETY_VIOLATION"
