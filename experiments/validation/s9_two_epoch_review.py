"""Independent *reported source* review of S8→S9 bounded two-epoch evidence.

Never convert S-owned operator issue claims into original-byte RSEE/R9 clearance,
causal Memory benefit, goal learning or scientific GO. No World/model startup.
"""
from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any

REPORT = Path(__file__).with_name("s9_two_epoch_report.json")
SCHEMA = "RELAYSELF_V1_S8_S9_REPORTED_TWO_EPOCH_REVIEW"
HEX = re.compile(r"[0-9a-f]{64}\Z")
S8_HEAD = "eac08081d497b11f8386edd1229704c816d1a78d"
S9_HEAD = "916814742567f8ff396b5c078d22f897d8418927"
S8_ISSUE = "https://github.com/rinsakamo/relay-self/issues/537#issuecomment-6119140571"
S9_ISSUE = "https://github.com/rinsakamo/relay-self/issues/537#issuecomment-6120089028"
S8_IN = "474eb0b20a7a93852e17a1e7239301e812b81c62f800727db2d6e58f2371b5c3"
S8_OUT = "a4f65dafb801fcf00c34297e6e786a669d2da4bbb845d4cb85aaa9dc9f5294e1"
S9_IN = "614bdb6be1cff97ad598b49be5dd0beaf21bc5a440933d8af91a1f5860703844"
S9_OUT = "23d5feb0ebff8c43c374817bcd1e05f72714dcbf55db9792075ba072a4895000"
S9_INDEX = "da9858667ab4e3b38a8ab53819f7d55edf2bba14bede8bc364d01709c40ee70e"


class VRejected(ValueError):
    """Unqualified source or scientific conclusion was asserted."""


def check(ok: bool, why: str) -> None:
    if not ok:
        raise VRejected(why)


def equals(d: dict[str, Any], key: str, expected: Any) -> None:
    value = d.get(key)
    check(type(value) is type(expected) and value == expected,
          "original report identity/claim drift: " + key)


def review(report: dict[str, Any]) -> dict[str, Any]:
    check(type(report) is dict and set(report) == {
        "schema", "evidence_origin", "s8", "s9",
    }, "strict frozen two-epoch reported-source schema")
    equals(report, "schema", SCHEMA)
    equals(report, "evidence_origin",
           "GITHUB_OPERATOR_REPORT_NOT_NATIVE_ORIGINAL_BYTES_V_VERIFIED")
    s8, s9 = report["s8"], report["s9"]
    check(type(s8) is dict and type(s9) is dict, "both distinct source sessions required")
    # Pin reported values. Nothing here reads original physical bytes or attests
    # a historical event independently of the operator.
    expected_s8: dict[str, Any] = {
        "issue_url": S8_ISSUE, "source_head": S8_HEAD,
        "terminal": "S8_PHYSICAL_UNKNOWN_OR_BLOCKED", "exit_code": 2,
        "physical_session_count": 1, "native_actions_reported": 1,
        "retained_observations_reported": 1, "read_only_recall_reported": 1,
        "second_action_closed": False, "retry_count": 0,
        "grant_consumed": True, "source_sha256_received": S8_IN,
        "source_sha256_sent": S8_OUT,
    }
    expected_s9: dict[str, Any] = {
        "issue_url": S9_ISSUE, "source_head": S9_HEAD,
        "parent_source_head": S8_HEAD,
        "terminal": "S9_TWO_CONTROLLED_ACTION_OUTCOMES_OBSERVED",
        "budget_terminal": "ACTION_BUDGET_ENDED", "exit_code": 0,
        "session_id": "dacf338b-4ba9-4e91-8eea-d4aebd0aef22",
        "physical_session_count": 1, "retry_count": 0,
        "grant_consumed": True,
        "target_type": "CONTROLLED_NOAI_ZOMBIES_NOT_NATURAL_OR_ACTIVE_HOSTILE",
        "source_native_bounded_clearance_probes": 3,
        "old_entity_id": 2, "second_entity_id": 4,
        "external_server_command_attempts": 3,
        "summon_ack_verified": False,
        "world_global_absence_attested": False,
        "action_requests_reported": 2,
        "native_executed_outcomes_reported": 2,
        "observed_memories_retained_reported": 2,
        "read_only_recall_reported": True,
        "memory_caused_second_decision_attested": False,
        "action_distances_m_reported": [0.792923118, 0.944431178],
        "native_bridge_received_lines": 39,
        "native_bridge_received_bytes": 21924,
        "native_bridge_sent_lines": 14,
        "native_bridge_sent_bytes": 897,
        "native_bridge_received_sha256": S9_IN,
        "native_bridge_sent_sha256": S9_OUT,
        "pre_posting_index_sha256": S9_INDEX,
        "s10_learning_updates_reported": 0,
        "s11_habit_grants_reported": 0,
        "l2_model_posts_reported": 0,
        "independently_attested_task_goal": False,
        "learned_advantage_vs_matched_cheap_control": False,
        "matched_cheap_control_performed": False,
        "heldout_transfer_verified": False,
        "measured_resource_adjusted_gain": False,
        "native_stop_ack_verified": False,
        "original_bridge_bytes_independently_read_by_v": False,
        "r9_exact_head_verified_by_v": False,
        "r9_source_receipt_verified_by_v": False,
    }
    check(set(s8) == set(expected_s8) and set(s9) == set(expected_s9),
          "extra/absent scientific or evidence claim fields")
    for key, expected in expected_s8.items():
        equals(s8, key, expected)
    for key, expected in expected_s9.items():
        equals(s9, key, expected)
    for digest in (S8_IN, S8_OUT, S9_IN, S9_OUT, S9_INDEX):
        check(HEX.fullmatch(digest) is not None,
              "source index/digest invalid")
    check(s8["source_head"] != s9["source_head"]
          and s9["old_entity_id"] != s9["second_entity_id"],
          "independent session/code/entity identity required")
    # The S8 and S9 cases are distinct code, sessions and action opportunities.
    # Counting one vs two is NOT a matched cheap-control experiment or a
    # counterfactual test of Memory's causal influence on Action 2.
    return {
        "schema": "RELAYSELF_V1_TWO_EPOCH_V_OWNER_REVIEW",
        "input_provenance": "FROZEN_GITHUB_OPERATOR_REPORT_ONLY",
        "s8": "ONE_OUTCOME_THEN_FAIL_CLOSED_RECALL_OBSERVED_REPORTED",
        "s9": "TWO_CONTROLLED_NATIVE_OUTCOMES_TWO_MEMORIES_REPORTED",
        "engineering_progress": "NEW_PROSPECTIVE_BRIDGE_BYTES_REPORTED_NOT_R9_V_VERIFIED",
        "two_episodes_same_session": "REPORTED_S9_ONLY",
        "two_episodes_v_original_independent_authentication": "NOT_RUN",
        "controlled_target_clearance": "THREE_BOUNDED_FRESH_PROBES_REPORTED",
        "physical_goal": "NOT_ATTESTED",
        "memory_effect_on_second_action": "NOT_DEMONSTRATED",
        "cheap_control_counterfactual": "NOT_RUN_UNMATCHED_S8_S9",
        "learning_revision": "NONE_REPORTED",
        "learned_habit": "NONE_REPORTED",
        "native_stop_ack": "UNVERIFIED",
        "r9_qualification": "NOT_CHECKED_UNTIL_EXACT_PUBLIC_HEAD_AND_ORIGINALS",
        "v_science_gates": {
            "G0": "UNDETERMINED_UNREAD_ORIGINAL_BRIDGE_BYTES",
            "G1": "NO_PROSPECTIVE_HELDOUT_GOAL_MEASUREMENT",
            "G2": "NO_SOURCE_MATCHED_CHEAP_BASELINE",
            "G3": "NO_GO_GOAL_AND_INCREMENTAL_UTILITY_NOT_ATTESTED",
            "G4": "UNMEASURED_RESOURCE_ADJUSTED_BENEFIT",
            "G5": "UNTESTED_TRANSFER_OR_CAUSAL_MEMORY_REUSE",
        },
        "science_qualified": False, "production_qualified": False,
        "new_physical_world_runs": 0, "new_model_calls": 0,
        "s8_s9_permissions": "BOTH_CONSUMED_NO_REPLAY",
        "classification": "V_S9_TWO_EPOCH_OPERATOR_REPORTED_NOT_LEARNING_OR_SCIENCE",
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--report", type=Path, default=REPORT)
    args = parser.parse_args(argv)
    try:
        file = args.report
        check(file.is_file() and not file.is_symlink()
              and 0 < file.stat().st_size <= 100_000,
              "bounded nonsymlink original report required")
        output = review(json.loads(file.read_text(encoding="utf-8")))
        print(json.dumps(output, indent=2, sort_keys=True))
        return 0
    except (ValueError, OSError, TypeError, KeyError) as exc:
        print(json.dumps({
            "classification": "V_S9_EVIDENCE_REJECTED",
            "error": type(exc).__name__ + ":" + str(exc),
            "science_qualified": False, "production_qualified": False,
        }, sort_keys=True))
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
