"""Readback of bounded DEV fault evidence; injection intent is not observation."""
from __future__ import annotations


def audit_fault_dev(case, commands, native, report):
    aid = "t1j-T1J-R1-move"
    effects = [x for x in commands if x.get("type") == "effect"]
    ids = [x["action_id"] for x in effects]
    sends = [x for x in effects if x.get("effect") == "set_control"
             and x.get("action_id", "").startswith("t1j-")]
    clears = [x for x in effects if x.get("effect") == "clear_controls"
              and x.get("action_id") == aid + "-clear"]
    raw = [x for x in native if x.get("session_id") == report.get("session_id")]
    receipts = [x for x in raw if x.get("type") == "effect_result"
                and x.get("action_id") == aid and x.get("effect") == "set_control"]
    clear_receipts = [x for x in raw if x.get("type") == "effect_result"
                      and x.get("action_id") == aid + "-clear"
                      and x.get("effect") == "clear_controls" and x.get("result") == "applied"]
    ends = [x for x in raw if x.get("type") == "connection_end"
            and x.get("reason") != "RelaySelf adapter shutdown"]
    attempts = report.get("resume_attempts_dev", [])
    attempt = attempts[0] if attempts else {}
    permitted = attempt.get("permit_consumed") is True
    consequence = attempt.get("consequence", {})
    terminal = attempt.get("terminal", {}).get("state")
    dropped = report.get("dropped_clear_receipts", [])
    if case == "t1k_fault_before_send":
        observed = bool(permitted and report.get("fault_injection") and ends and not sends)
        boundary = "BEFORE_MOTOR_SEND" if observed else "UNDETERMINED"
        closed = observed and not attempt.get("motor_send_attempted") and terminal is None
    elif case == "t1k_fault_set_ack":
        observed = bool(permitted and report.get("fault_injection") and ends and len(sends) == 1)
        applied = any(x.get("result") == "applied" and x["seq"] < ends[0]["seq"]
                      for x in receipts) if ends else False
        boundary = ("AFTER_SET_APPLIED_ACK" if applied else "AFTER_SEND_ACK_UNCONFIRMED") if observed else "UNDETERMINED"
        closed = observed and terminal == "unknown" and consequence.get("status") == "failed"
    else:
        # Native wire objects carry `type`; parsed consumer dataclasses do
        # not. Bind the same receipt identity/content, not wire-only fields.
        dropped_matching = any(
            all(x.get(k) == receipt.get(k) for k in (
                "session_id", "seq", "action_id", "effect", "result", "error"))
            for x in dropped for receipt in clear_receipts
        )
        observed = bool(permitted and len(sends) == len(clears) == 1
                        and clear_receipts and dropped_matching)
        boundary = "CLEAR_APPLIED_ACK_DROPPED_AT_PYTHON" if observed else "UNDETERMINED"
        closed = (observed and terminal == "unknown" and consequence.get("status") == "failed"
                  and consequence.get("cleanup_receipt") is None)
    duplicates = len(ids) - len(set(ids))
    violation = bool(duplicates or len(sends) > 1 or len(clears) > 1
                     or (case == "t1k_fault_before_send" and sends)
                     or terminal == "outcome" or consequence.get("status") == "executed"
                     or len(attempts) > 1)
    closed = bool(closed and not violation and attempt.get("permission_cleared")
                  and attempt.get("old_owner_still_latched")
                  and attempt.get("old_ledger_unchanged") and report.get("status") == "FAIL")
    return {
        "fault_case": case, "native_fault_observed": observed,
        "native_classification": "NATIVE_FAULT_OBSERVED" if observed else "NATIVE_UNVERIFIED",
        "classification": ("SAFETY_VIOLATION" if violation else
                           "FAULT_INJECTED_FAIL_CLOSED_DEV_OBSERVED" if closed else
                           "NATIVE_FAULT_UNDETERMINED"),
        "fault_boundary": boundary, "safety_violation": violation,
        "resume_motor_sends": len(sends), "resume_clear_sends": len(clears),
        "effect_id_duplicates": duplicates, "set_receipts": receipts,
        "clear_receipts": clear_receipts, "disconnects": ends,
        "no_resume_action_reissued": len(sends) <= 1,
        "expected_refusal_not_normal_shutdown_pass": True,
        "raw_cleanup_separate": report.get("cleanup_complete"),
    }
