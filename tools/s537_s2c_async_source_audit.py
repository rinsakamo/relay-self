"""S #537 S2-C independent JSON audit: original physical rows + one S60 sidecar.

This checks internally consistent persisted records, not independent Paper/W3
source custody, HTTP packet capture, backend PID/model identity or GPU STOP.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from tools.s537_s2b_original_owner_audit import (
    OwnerAuditRejected,
    audit_original_rows,
)


class S2CSourceAuditRejected(ValueError):
    """S2-C source/admission/expiry evidence is not consistent."""


def audit_s2c_rows(s49: dict[str, Any], s2c: dict[str, Any]) -> dict[str, Any]:
    try:
        s60 = s2c["s60"]
        s2a = s2c["s2a"]
        s1 = s2c["s49_s1"]
        owner = s2c["owner_epoch"]
        attempts = s2c["s60_submissions"]
        if (
            s2c["status"] != "RECORDED"
            or s2c["source_join_status"] != "RECORDED"
            or type(attempts) is not int or attempts != 1
            or s60["model_attempts"] != attempts
            or s60["session_id"] != s49["session_id"]
            or s60["input_source_seq"] is None
            or s60["latest_probe_seq"] != s60["input_source_seq"]
            or s60["original_s16_invalidations"] != 1
            or s60["l0_awaited_provider"] is not False
            or s60["backend_stop_ack"] is not False
            or s60["gpu_release_verified"] is not False
            or s60["source_attested"] is not False
            or s2c["source_attested"] is not False
            or s2c["action_authority"] is not False
            or s2c["learning_authority"] is not False
            or s2c["new_native_reads"] != 0
            or s2c["new_action_issues"] != 0
            or s2c["learning_updates"] != 0
            or s2c["energy_debits"] != 0
            or s2c["http_post_sent_observed"] is not True
            or s2c["http_completion_observed"] != (
                "HTTP_COMPLETION_OBSERVED" in s60["transport_events"]
            )
            or "SOCKET_POST_SENT" not in s60["transport_events"]
            or "NEW_REQUEST_STARTED" not in s60["owner_events"]
            or s60["poll_errors"] or s60["original_source_callback_errors"]
            or s60["status"] not in (
                "EXPIRED_ORIGINAL_S16_WORLD_ADVANCED",
                "EXPIRED_WORLD_ADVANCED",
            )
        ):
            raise S2CSourceAuditRejected("S60 source/attempt/expiry mismatch")
        source_rows = s2a["inputs"]
        bound = [entry for entry in source_rows if entry["preceding_action_id"]]
        if (
            len(bound) != 1
            or s60["input_source_seq"] != bound[0]["probe_seq"]
            or not s60["owner_events"].count("L0_COMPLETED") == 0
            or (
                "DISPLACED" not in s60["owner_events"]
                and not s60["advisory_accepted_before_invalidation"]
            )
        ):
            raise S2CSourceAuditRejected("previous S16 source or stale fence missing")
        compatible = {
            "status": s2c["source_join_status"],
            "s2a_status": s2a["status"],
            "s2a": {"status": s2c["source_join_status"], "s1": s1, "s2a": s2a},
            "owner_epoch": owner,
            "model_calls": attempts,
            "s60_submissions": attempts,
            "source_attested": False,
        }
        source = audit_original_rows(
            s49, compatible, expected_sidecar_model_attempts=1,
        )
        return {
            "schema": "S537_S2C_ORIGINAL_SOURCE_AND_S60_CROSS_AUDIT_DEV_V1",
            "status": "PASS",
            "session_id": source["session_id"],
            "native_input_count": source["native_input_count"],
            "original_closed_actions": source["original_closed_actions"],
            "previous_s16_bound": source["previous_s16_bound"],
            "s60_model_attempts": attempts,
            "http_post_sent_observed": True,
            "http_completion_observed": s2c["http_completion_observed"],
            "expired_by_original_s16": True,
            "source_attested": False,
            "backend_stop_ack": False,
            "qualification": "NO_GO",
            "science": "NOT_RUN",
        }
    except (KeyError, IndexError, TypeError, ValueError, OwnerAuditRejected) as exc:
        raise S2CSourceAuditRejected("original S2-C cross-audit rejected") from exc


def main() -> int:
    parser = argparse.ArgumentParser("S2-C original S49 and S60 source-row audit")
    parser.add_argument("--s49", required=True, type=Path)
    parser.add_argument("--s2c", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    if (
        args.output.exists() or args.output.is_symlink()
        or not args.output.parent.is_dir() or args.output.parent.is_symlink()
        or not args.s49.is_file() or not args.s2c.is_file()
    ):
        print(json.dumps({"status": "BLOCKED", "reason": "fresh_source_required"}))
        return 2
    try:
        checked = audit_s2c_rows(
            json.loads(args.s49.read_text(encoding="utf-8")),
            json.loads(args.s2c.read_text(encoding="utf-8")),
        )
    except (OSError, ValueError):
        checked = {
            "status": "FAIL",
            "reason": "S2C_SOURCE_OR_S60_AUDIT_REJECTED",
            "source_attested": False,
        }
    args.output.write_text(json.dumps(checked, indent=2, sort_keys=True) + "\n")
    print(json.dumps({"status": checked["status"], "output": str(args.output)}))
    return 0 if checked["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
