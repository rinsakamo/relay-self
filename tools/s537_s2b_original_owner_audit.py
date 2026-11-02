"""Independent *offline source-row* audit for S2-B owner witness DEV.

Reads the two JSON original outputs only. This checks their internal
cross-consistency; it DOES NOT attest Paper/W3/TCP custody, original process
identity or a real provider call. No retries, World access or model calls.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


class OwnerAuditRejected(ValueError):
    """Claim would require unknown/foreign/future original source evidence."""


def audit_original_rows(s49: dict[str, Any], report: dict[str, Any]) -> dict[str, Any]:
    """Fail closed on mismatched S49 native, S2-A host and S2-B owner sequence."""
    try:
        root = report["s2a"]
        s1 = root["s1"]["typed_join"]
        s2a = root["s2a"]
        owner = report["owner_epoch"]
        source_rows = s49["original_completion_readback"]["decisions"]
        native_actions = s49["actual_native_actions"]
        inputs = s2a["inputs"]
        events = s2a["host_events"]
        owner_rows = owner["epoch_contexts"]
        original_epochs = owner["original_owner"]["epochs"]
        sid = s49["session_id"]
        if (
            s49["status"] != "PASS"
            or report["status"] != "RECORDED"
            or owner["status"] != "RECORDED"
            or root["status"] != "RECORDED"
            or s2a["status"] != "RECORDED"
            or s1["status"] != "RECORDED"
            or s1["m_status"] != "RECORDED"
            or s1["s49"]["m_status"] != "ORIGINAL_PYTHON_BATCH_RECORDED"
            or report["s2a_status"] != "RECORDED"
            or s49["original_completion_readback"]["session_id"] != sid
            or s2a["session_id"] != sid
            or s1["session_id"] != sid
            or owner["original_owner"]["session_id"] != sid
            or not isinstance(source_rows, list)
            or not 2 <= len(source_rows) <= 8
            or not (len(source_rows) == len(inputs) == len(owner_rows) == len(original_epochs))
            or len(s1["wb_rows"]) != len(inputs)
            or s2a["input_count"] != len(inputs)
            or s2a["closed_s16_count"] != len(native_actions)
            or s49["real_model_calls"] != 0
            or report["model_calls"] != 0
            or report["s60_submissions"] != 0
            or report["source_attested"] is not False
            or s2a["source_attested"] is not False
            or owner["source_attested"] is not False
        ):
            raise OwnerAuditRejected("original S49/S2A/S2B status/source mismatch")
        used_actions = {}
        for action in native_actions:
            evidence = action["execution_evidence"]
            aid = action["action"]
            if (
                aid in used_actions
                or action["terminal"] != "outcome"
                or evidence["status"] != "executed"
                or evidence["session_id"] != sid
                or evidence["action_id"] != aid
                or evidence["cleanup_receipt"]["result"] != "applied"
                or evidence["dispatch_receipt"]["result"] != "applied"
                or evidence["before_observation"]["seq"]
                >= evidence["dispatch_receipt"]["seq"]
                or evidence["dispatch_receipt"]["seq"]
                >= evidence["cleanup_receipt"]["seq"]
                or evidence["cleanup_receipt"]["seq"]
                >= evidence["after_observation"]["seq"]
            ):
                raise OwnerAuditRejected("native original Action not closed")
            used_actions[aid] = (action["probe_seq"], evidence["after_observation"]["seq"])
        previous_probe = -1
        previous_intent_gen = -1
        previous_retained_rev = -1
        for decision, incoming, owner_row, original_epoch, wb in zip(
            source_rows, inputs, owner_rows, original_epochs, s1["wb_rows"],
            strict=True,
        ):
            seq, rid = decision["probe_seq"], decision["request_id"]
            if (
                seq <= previous_probe
                or not (
                    seq == incoming["probe_seq"] == owner_row["native_probe_seq"]
                    == original_epoch["native_probe_seq"] == wb["probe_seq"]
                )
                or not (
                    rid == incoming["request_id"] == owner_row["request_id"]
                    == wb["request_id"]
                )
                or incoming["session_id"] != sid
                or incoming["epoch_id"] != f"native-{seq}"
                or incoming["world_source_ref"] != wb["world_source_ref"]
                or incoming["body_source_ref"] != wb["body_source_ref"]
                or owner_row["intent_generation"] != original_epoch["intent_generation"]
                or owner_row["retained_revision"] != original_epoch["retained_revision"]
                or owner_row["intent_generation"] < previous_intent_gen
                or owner_row["retained_revision"] < previous_retained_rev
                or wb["tier"] != "L1"
                or owner_row["preceding_action_id"] != incoming["preceding_action_id"]
            ):
                raise OwnerAuditRejected("same original epoch/revision join failed")
            previous_probe = seq
            previous_intent_gen = owner_row["intent_generation"]
            previous_retained_rev = owner_row["retained_revision"]
        active_previous = None
        active_after = None
        input_count = 0
        observed_actions: set[str] = set()
        prev_with_s16 = 0
        for event in events:
            if event["session_id"] != sid:
                raise OwnerAuditRejected("foreign host callback")
            if event["event"] == "input_built":
                source = inputs[input_count]
                input_count += 1
                if (
                    event["probe_seq"] != source["probe_seq"]
                    or event["epoch_id"] != source["epoch_id"]
                    or event["preceding_action_id"] != active_previous
                    or source["preceding_action_id"] != active_previous
                    or source["preceding_s16_after_seq"] != active_after
                    or (
                        active_after is not None
                        and active_after >= source["probe_seq"]
                    )
                ):
                    raise OwnerAuditRejected("S16 future or injected into past epoch")
                prev_with_s16 += int(active_previous is not None)
            elif event["event"] == "closed_s16":
                aid = event["action_id"]
                if (
                    aid not in used_actions
                    or aid in observed_actions
                    or event["terminal"] != "outcome"
                    or (event["source_probe_seq"], event["s16_after_seq"])
                    != used_actions[aid]
                    or event["source_probe_seq"] != inputs[input_count - 1]["probe_seq"]
                ):
                    raise OwnerAuditRejected("forged or reordered native S16")
                active_previous = aid
                active_after = event["s16_after_seq"]
                observed_actions.add(aid)
            else:
                raise OwnerAuditRejected("unknown original callback event")
        if (
            input_count != len(inputs)
            or observed_actions != set(used_actions)
            or prev_with_s16 != s2a["with_previous_s16"]
            or prev_with_s16 < 1
        ):
            raise OwnerAuditRejected("S2-B previous-S16 host chronology incomplete")
        return {
            "schema": "S537_S2B_ORIGINAL_ROW_CROSS_AUDIT_DEV_V1",
            "status": "PASS",
            "session_id": sid,
            "native_input_count": len(inputs),
            "original_closed_actions": len(used_actions),
            "previous_s16_bound": prev_with_s16,
            "source_attested": False,
            "model_calls": 0,
            "qualification": "NO_GO",
            "science": "NOT_RUN",
        }
    except (KeyError, IndexError, TypeError, ValueError) as exc:
        raise OwnerAuditRejected("original S49/S2B report rejected") from exc


def main() -> int:
    parser = argparse.ArgumentParser(description="S2B independent row audit, no World")
    parser.add_argument("--s49", required=True, type=Path)
    parser.add_argument("--s2b", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    if (
        args.output.exists() or args.output.is_symlink()
        or not args.output.parent.is_dir() or args.output.parent.is_symlink()
        or not args.s49.is_file() or not args.s2b.is_file()
    ):
        print(json.dumps({"status": "BLOCKED", "reason": "source_or_fresh_output_missing"}))
        return 2
    try:
        verified = audit_original_rows(
            json.loads(args.s49.read_text(encoding="utf-8")),
            json.loads(args.s2b.read_text(encoding="utf-8")),
        )
    except (OSError, ValueError, json.JSONDecodeError):
        verified = {
            "status": "FAIL",
            "reason": "SOURCE_ROW_CROSS_AUDIT_REJECTED",
            "source_attested": False,
        }
    args.output.write_text(json.dumps(verified, sort_keys=True, indent=2) + "\n")
    print(json.dumps({"status": verified["status"], "output": str(args.output)}))
    return 0 if verified["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
