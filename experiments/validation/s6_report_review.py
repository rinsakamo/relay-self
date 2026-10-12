"""Independent V review of the single S6 reported controlled Minecraft trial.

This is an issue-report adjudication, NEVER byte-level original readback or
physical source authentication. R5 controls R1/R2 native original admission.
"""
from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any

REPORT = Path(__file__).with_name("s6_report_claims.json")
SOURCE_HEAD = "a6ed8ed6b99dd09edcaa6cc9e5cefc08778aec8f"
SOURCE_SESSION = "a5cdc400-572a-41ee-b411-e7399bbb80fd"
R5_HEAD = "364f4cc66fbe393717d31adce22747be17446dd8"
S7_HEAD = "d23378d0c2d8271997389f6296a9bd018e488327"
SHA = re.compile(r"[0-9a-f]{64}\Z")
KNOWN_ORIGINAL_INDEXES = {
    "SHA256SUMS": ("b22598cc985d5fce4f8c8ffbb15452a8e6f79578aa18d5326650eaa4143536e7", 32),
    "FINAL_SHA256SUMS": ("baa0e633a10f2cfd64107d1aee77250e56b4fa56405c826ff27e2f3f3652fd47", 39),
}
KNOWN_DERIVED = {
    "physical/session_events.jsonl": "6626e94d23fcf5df91514c9355d07315165441d64643e5caefc45e536a56f645",
    "physical/s3_observed_memory.json": "15440763030b6bb3ddd11ac4e3fcf5dfef46638223d376b6151be1127fb0a2e7",
    "physical/owned_cleanup.json": "a3f2e0c9c86afcb99e287af3c70aaa1eb7155e60b66285186e5a52f3ba1721e4",
}
EXPECTED_COUNTS = {
    "physical_reported_runs": 1, "physical_retry_reported": 0,
    "native_outer_frames_reported": 187,
    "native_entity_frames_reported": 1, "l0_decisions_reported": 1,
    "action_requests_reported": 1, "terminal_outcomes_reported": 1,
    "retained_observational_memories_reported": 1,
    "s10_updates_reported": 0, "s11_habit_grants_reported": 0,
    "l2_model_calls_reported": 0,
}
MISSING_WITNESS = (
    "task_goal_attested", "natural_hostile_threat_attested",
    "physical_origin_independently_verified_by_v",
    "native_predecode_bridge_original_archived",
    "r1_r2_original_action_envelope_present", "s6_late_reconstruction_allowed",
    "native_stop_ack_attested", "same_source_cheap_control_run",
    "heldout_goal_outcomes_attested", "measured_resource_net_benefit",
    "independent_transfer_attested",
)


class VRejected(ValueError):
    """Source claim or evidence class drift cannot be promoted."""


def require(predicate: bool, message: str) -> None:
    if not predicate:
        raise VRejected(message)


def assess(row: dict[str, Any]) -> dict[str, Any]:
    require(type(row) is dict
            and row.get("schema") == "RELAYSELF_V1_S6_FROZEN_OPERATOR_CLAIMS_V1"
            and row.get("evidence_kind") == "GITHUB_ISSUE_OPERATOR_REPORT_NOT_ORIGINAL_WSL2_BYTES",
            "only frozen issue-reported evidence can be assessed")
    identities = {
        "source_head": SOURCE_HEAD, "session": SOURCE_SESSION,
        "r5_source_head": R5_HEAD, "prospective_s7_head": S7_HEAD,
        "target_type": "CONTROLLED_NOAI_ZOMBIE_NOT_NATURAL",
        "native_action_id": "s49-native-move-4",
        "source_issue_comment": "https://github.com/rinsakamo/relay-self/issues/537#issuecomment-6116683016",
        "sha_audit_comment": "https://github.com/rinsakamo/relay-self/issues/537#issuecomment-6117549533",
    }
    for name, expected in identities.items():
        require(row.get(name) == expected, "source identity changed: " + name)
    for name, expected in EXPECTED_COUNTS.items():
        require(type(row.get(name)) is int and row[name] == expected,
                "operator count changed: " + name)
    require(type(row.get("movement_m_reported")) is float
            and row["movement_m_reported"] == 0.6269065734210617,
            "original operator movement claim drift")
    digest = row.get("native_evidence_sha256_reported")
    require(isinstance(digest, str) and SHA.fullmatch(digest) is not None
            and digest == "c39c85598f34770ce89d59852e911ea419898df9c1f54984381308f5eb1fa0ad",
            "decoded source digest drift")
    require(all(row.get(k) is False for k in MISSING_WITNESS),
            "an absent source, reward, scientific or STOP witness was promoted")
    require(row.get("derived_files_reported") == KNOWN_DERIVED,
            "derived source names/hashes changed or invented raw files")
    indices = row.get("sha_indexes_reported")
    require(type(indices) is dict and set(indices) == set(KNOWN_ORIGINAL_INDEXES),
            "original vs final SHA index scope changed")
    for name, (digest, count) in KNOWN_ORIGINAL_INDEXES.items():
        actual = indices[name]
        require(type(actual) is dict
                and set(actual) == {"sha256", "checked_entries"}
                and actual["sha256"] == digest
                and type(actual["checked_entries"]) is int
                and actual["checked_entries"] == count,
                "two different index artifacts were conflated")
    return {
        "schema": "RELAYSELF_V1_S6_INDEPENDENT_ISSUE_REVIEW",
        "source_head": SOURCE_HEAD, "source_session": SOURCE_SESSION,
        "source_of_claims": "GITHUB_ISSUE_OPERATOR_REPORT_ONLY",
        "v_host_original_bytes_read": False,
        "engineering": {
            "index_integrity": "OPERATOR_REPORTED_32_AND_39_DIFFERENT_INDEX_FILES",
            "native_bridge_predecode": "NOT_ARCHIVED_S6",
            "r5_original_admission": "S6_DERIVED_ONLY_RAW_NOT_ARCHIVED",
            "native_stop_ack": "UNATTESTED",
            "v_verified_raw": False,
        },
        "behavioral": {
            "result": "ONE_CONTROLLED_NOAI_MOVE_AWAY_OUTCOME_REPORTED",
            "reported_physical_actions": 1,
            "reported_movement_m": row["movement_m_reported"],
            "reported_observational_memories": 1,
            "natural_survival": "NOT_ESTABLISHED",
            "s10_learning_updates": 0, "s11_habit_grants": 0,
            "product_acceptance": "UNDETERMINED",
        },
        "scientific": {
            "G0": "BLOCKED_V_ORIGINAL_NATIVE_SOURCE_UNVERIFIED",
            "G1": "NOT_RUN_ACTION_CONDITIONED_HELDOUT_MEASUREMENT",
            "G2": "NOT_RUN_CHEAP_MATCHED_CONTROL",
            "G3": "NO_GO_NO_ATTESTED_GOAL_DELTA",
            "G4": "NOT_RUN_RESOURCE_NET_GAIN",
            "G5": "NOT_RUN_INDEPENDENT_LATER_REUSE",
            "science_qualified": False,
        },
        "s6_permission": "CONSUMED_DO_NOT_REPLAY",
        "s7_physical": "NOT_RUN",
        "new_world_actions": 0, "new_model_calls": 0,
        "terminal": "V_S6_BEHAVIOR_REPORTED_WITHOUT_NATIVE_ORIGINAL_OR_SCIENCE_GO",
    }


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--report", type=Path, default=REPORT)
    args = p.parse_args(argv)
    try:
        file = args.report
        require(file.is_file() and not file.is_symlink()
                and 0 < file.stat().st_size <= 100_000,
                "bounded existing non-symlink report required")
        output = assess(json.loads(file.read_text(encoding="utf-8")))
        print(json.dumps(output, ensure_ascii=False, indent=2, sort_keys=True))
        return 0
    except (OSError, ValueError, TypeError, KeyError) as exc:
        print(json.dumps({
            "terminal": "V_S6_REPORT_REJECTED",
            "error": type(exc).__name__ + ":" + str(exc),
            "science_qualified": False, "physical_execution_authorized": False,
        }, sort_keys=True))
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
