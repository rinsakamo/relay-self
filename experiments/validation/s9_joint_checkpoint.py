"""V: joint engineering/behavior/science decision after real R6 host audit.

Consumes frozen *GitHub operator report claims*. This GitHub reviewer does not
read WSL2 original bytes; R6 operator already performed a separate real audit.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

CHECKPOINT = Path(__file__).with_name("s9_joint_checkpoint.json")
R6_COMMENT = "https://github.com/rinsakamo/relay-self/issues/575#issuecomment-6121953835"
S10_PR = "https://github.com/rinsakamo/relay-self/pull/611"
L4_PR = "https://github.com/rinsakamo/relay-self/pull/612"
R6_HEAD = "b5ca2afc0e2cb8b419e7d2f18afc3e24f991ad4a"
S9_HEAD = "916814742567f8ff396b5c078d22f897d8418927"
S9_SESSION = "dacf338b-4ba9-4e91-8eea-d4aebd0aef22"
S10_HEAD = "cd6edc11f390c759feeb437dd5a14ad03bf8ee98"
L4_HEAD = "28b90ad2f2d204a808610a36a8b619f2c194be73"
FILES: dict[str, tuple[int, str, int | None]] = {
    "native_bridge_received_original.jsonl": (
        21924, "614bdb6be1cff97ad598b49be5dd0beaf21bc5a440933d8af91a1f5860703844", 39),
    "native_bridge_sent_original.jsonl": (
        897, "23d5feb0ebff8c43c374817bcd1e05f72714dcbf55db9792075ba072a4895000", 14),
    "native_bridge_source_receipt.json": (
        720, "e2bca3882d8088833857753cd085eec3db31cbb721cc0c3ec73a63cdf177a4ad", None),
    "session_events.jsonl": (
        19628, "432cac8be4c1d80050e91ec6c651b170929d91252384862f7a5ece799f4b6856", None),
    "s3_observed_memory.json": (
        2297, "e4c789040827817a3f5e3b0192296046eb31b7ba9ec63c60203a6ddad03263c9", None),
    "owned_cleanup.json": (
        345, "e964ee0bf0ad5f0cfe8502939a7f56b5e25630390708f6ad2c30b7b399870b7b", None),
}
INDEXES = {
    "pre_post_index": ("da9858667ab4e3b38a8ab53819f7d55edf2bba14bede8bc364d01709c40ee70e", 47),
    "final_index": ("e3ba0bd21028bd753bb97b9e7bc84e154e1078c922c86c339aaeeaaf9918ea57", 56),
}
R6_NO = (
    "independent_v_host_readback", "raw_minecraft_tcp_packets_attested",
    "existing_r1_envelope_qualified", "independent_r2_typed_action_outcome_qualified",
    "native_stop_ack_attested", "goal_success_attested",
    "memory_caused_action_attested", "science_qualified",
)


class JointRejected(ValueError):
    """Wrong source identity or impermissible inference."""


def require(p: bool, why: str) -> None:
    if not p:
        raise JointRejected(why)


def exactly(row: dict[str, Any], name: str, expected: Any) -> None:
    value = row.get(name)
    require(type(value) is type(expected) and value == expected, "report drift: " + name)


def adjudicate(data: dict[str, Any]) -> dict[str, Any]:
    require(type(data) is dict and set(data) == {
        "schema", "evidence_class", "r6", "s10", "l4",
    }, "joint report scope")
    exactly(data, "schema", "RELAYSELF_V1_R6_S10_L4_JOINT_CHECKPOINT")
    exactly(data, "evidence_class",
            "GITHUB_OPERATOR_REPORTED_REAL_WSL2_R6_READBACK_NOT_V_LOCAL_BYTES")
    r, s, l = data["r6"], data["s10"], data["l4"]
    require(all(type(x) is dict for x in (r, s, l)), "typed lane source evidence required")
    fixed_r: dict[str, Any] = {
        "authority_url": R6_COMMENT,
        "source_head": R6_HEAD,
        "physical_producer_head": S9_HEAD,
        "source_session": S9_SESSION,
        "operator_audit_terminal":
            "RSEE_R6_S9_ORIGINAL_BRIDGE_AND_MEMORY_BYTES_REVIEW_ONLY",
        "exit_status": 0, "read_only": True,
        "independent_v_host_readback": False,
        "existing_files_prepost_identical": 57,
        "independent_report_sha256":
            "1579167489e67cd9fb3a4d174abc1831cd8d3569e0de615de60cacde0d779432",
        "r6_stdout_sha256":
            "92be26ce4ef646a91c4beea92780cd84985995dbd67db08f70385daedf464949",
        "replay_count": 0,
    }
    require(set(r) == set(fixed_r) | {"original_files", *INDEXES, *R6_NO},
            "host report missing or unexpected attestation field")
    for k, v in fixed_r.items():
        exactly(r, k, v)
    for k in R6_NO:
        exactly(r, k, False)
    originals = r["original_files"]
    require(type(originals) is dict and set(originals) == set(FILES),
            "six historical original names required")
    for name, (size, digest, lines) in FILES.items():
        record = originals[name]
        require(type(record) is dict and set(record) == (
            {"bytes", "sha256", "lines"} if lines is not None else {"bytes", "sha256"}
        ), "original file attribute drift: " + name)
        exactly(record, "bytes", size)
        exactly(record, "sha256", digest)
        if lines is not None:
            exactly(record, "lines", lines)
    for name, (digest, count) in INDEXES.items():
        record = r[name]
        require(type(record) is dict and set(record) == {"sha256", "entries"},
                "distinct existing SHA index identity missing")
        exactly(record, "sha256", digest)
        exactly(record, "entries", count)

    expected_s: dict[str, Any] = {
        "source_pr": S10_PR, "source_head": S10_HEAD,
        "physical_s9_data_replayed": False,
        "same_source_synthetic_readonly": True,
        "memory_on_hint": "recall", "memory_off_hint": "not_recall",
        "l0_action_equal": True, "action_authorized": False,
        "measured_goal_delta": None, "scientific_go": False,
    }
    expected_l: dict[str, Any] = {
        "source_pr": L4_PR, "source_head": L4_HEAD,
        "exact_head_offline_ci": "COMPLETED_SUCCESS_2_OF_2",
        "prospective_matched_trial_contract": True,
        "independent_original_goals_verified": False,
        "physical_matched_retained_vs_cheap_trials": 0,
        "minimum_heldout_pairs": 2, "scientific_go": False,
    }
    for row, expected in ((s, expected_s), (l, expected_l)):
        require(set(row) == set(expected), "unqualified lane or goal fields")
        for name, value in expected.items():
            exactly(row, name, value)
    return {
        "schema": "RELAYSELF_V1_INDEPENDENT_CROSSLANE_JUDGMENT",
        "engineering_g0_r_host":
            "REAL_S9_ORIGINAL_BYTE_READBACK_REPORTED_FROM_R6_WSL2_OPERATOR",
        "engineering_g0_v_direct": "NOT_RUN",
        "engineering_r1_r2_typed_s16": "NOT_ADMITTED",
        "s9_behavior": "TWO_CONTROLLED_ACTION_OUTCOMES_AND_TWO_MEMORIES_REPORTED",
        "s10_offline_ablation": "MEMORY_RECALL_CONTRAST_NO_L0_CHOICE_DELTA",
        "s10_real_behavior_effect": "NOT_MEASURED",
        "l4_prospective_comparator": "CONTRACT_QUALIFIED_NO_PHYSICAL_PAIRS",
        "scientific_g1": "NO_INDEPENDENT_MATCHED_HELDOUT_GOAL_MEASUREMENT",
        "scientific_g2": "NO_EXECUTED_SAME_SOURCE_CHEAP_BASELINE",
        "scientific_g3": "NO_GO_NO_QUALIFIED_INCREMENTAL_GOAL_GAIN",
        "scientific_g4": "NOT_MEASURED_RESOURCE_ADJUSTED_VALUE",
        "scientific_g5": "NOT_MEASURED_INDEPENDENT_TRANSFER",
        "science_qualified": False,
        "product_qualified": False,
        "permissions": "S8_S9_CONSUMED_NO_REPLAY",
        "new_physical_runs": 0,
        "new_model_posts": 0,
        "classification": "V_R6_HOST_ORIGINAL_REPORTED_PASS_S10_NULL_L4_DESIGN_SCIENCE_NO_GO",
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--report", type=Path, default=CHECKPOINT)
    args = parser.parse_args(argv)
    try:
        src = args.report
        require(src.is_file() and not src.is_symlink()
                and 0 < src.stat().st_size <= 100_000,
                "existing read-only bounded lane report required")
        print(json.dumps(adjudicate(json.loads(src.read_text(encoding="utf-8"))),
                         indent=2, sort_keys=True))
        return 0
    except (OSError, ValueError, KeyError, TypeError) as exc:
        print(json.dumps({
            "classification": "V_JOINT_REPORT_SOURCE_REJECTED",
            "error": type(exc).__name__ + ":" + str(exc),
            "science_qualified": False, "product_qualified": False,
        }, sort_keys=True))
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
