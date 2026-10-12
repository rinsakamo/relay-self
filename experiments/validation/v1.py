"""V Lane V1: independent, offline, fail-closed claim and evidence adjudication.

No environment provisioning, LLM/model/World starts, Action issuance or writes.
R1's receipt verifier proves bytes, not independent physical origin or science.
"""
from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any

from experiments.standard_env import shared_runtime as r1

SCHEMA = "RELAYSELF_V1_INDEPENDENT_EVALUATION"
HEX40 = re.compile(r"[0-9a-f]{40}\Z")
HEX64 = re.compile(r"[0-9a-f]{64}\Z")
BASELINE = Path(__file__).with_name("v1_baseline.json")
GOLDEN_HEAD = "34820f6bf391c77f325d7c29d3b779a33e3ca835"
GOLDEN_SESSION = "6e039522-c79d-40b2-8b03-bc8c389f2a52"
GOLDEN_SHA = {
    "native_report.json": "f78b4473ca6dd3d37b2bad758b3b4b944822bc180a2a5953fd86e1727c55c6f1",
    "live_l2.jsonl": "bf1acbc6753472b62f8cde66fba1f9d6ec9197fe23188cfe6a90dd19b2ecb173",
    "observed_memory.json": "ddde5cb591c5b3d4499a3bdf440918ab1109d47ab58dcd4d2e19a4e42a830329",
}
ALLOWED_STATUS = {
    "OFFLINE_PASS_REPORTED", "SOURCE_SHAPED_PASS_REPORTED",
    "PHYSICAL_REPORTED", "NOT_RUN", "UNKNOWN", "UNDETERMINED",
    "NO_GO", "NEGATIVE_RESULT_REPORTED",
}
ALLOWED_ORIGIN = {"GITHUB_CI_REPORT", "GITHUB_ISSUE_RECEIPT", "SOURCE_CODE_CONTRACT"}


class V1Rejected(ValueError):
    """Unsupported, inconsistent or potentially promoted evidence."""


def require(ok: bool, why: str) -> None:
    if not ok:
        raise V1Rejected(why)


def is_sha(value: Any, width: int = 64) -> bool:
    regex = HEX64 if width == 64 else HEX40
    return isinstance(value, str) and bool(regex.fullmatch(value))


def inventory(path: Path = BASELINE) -> dict[str, Any]:
    """Read a frozen *reported* ledger, not actual host evidence."""
    obj = json.loads(path.read_text(encoding="utf-8"))
    require(type(obj) is dict and set(obj) == {"schema", "claims", "golden"}, "inventory schema")
    require(obj["schema"] == SCHEMA, "inventory identity")
    rows = obj["claims"]
    require(type(rows) is list and len(rows) >= 10, "incomplete claim inventory")
    ids: set[str] = set()
    for row in rows:
        require(type(row) is dict and set(row) == {
            "id", "lane", "claim", "source_head", "evidence_origin",
            "source_session", "receipt_sha256", "status", "authority",
        }, "claim shape")
        require(isinstance(row["id"], str) and row["id"] not in ids, "duplicate claim")
        ids.add(row["id"])
        require(row["lane"] in ("S", "L", "R", "V", "HISTORICAL"), "foreign lane")
        require(row["evidence_origin"] in ALLOWED_ORIGIN, "unverified origin promotion")
        require(row["status"] in ALLOWED_STATUS, "invalid qualification")
        require(row["source_head"] is None or is_sha(row["source_head"], 40),
                "exact head missing/invalid")
        require(row["receipt_sha256"] is None or is_sha(row["receipt_sha256"]),
                "receipt digest malformed")
        require(row["source_session"] is None or (
            isinstance(row["source_session"], str) and bool(row["source_session"])),
            "session shape")
        require(all(isinstance(row[k], str) and row[k] for k in ("claim", "authority")),
                "claim authority missing")
        require(not (row["status"] == "PHYSICAL_REPORTED"
                     and row["evidence_origin"] == "GITHUB_CI_REPORT"),
                "CI may not promote physical proof")
    golden = obj["golden"]
    require(type(golden) is dict and set(golden) == {
        "head", "session", "source_index_sha256_reported",
        "known_original_digests", "raw_original_verification",
        "reported_decisions", "reported_actions", "reported_memories",
        "reported_l2_status", "learning_updates", "habit_grants",
        "goal_success", "stop_ack",
    }, "golden shape")
    require(golden["head"] == GOLDEN_HEAD and golden["session"] == GOLDEN_SESSION,
            "golden source changed")
    require(golden["known_original_digests"] == GOLDEN_SHA, "golden digest claims drift")
    require(golden["raw_original_verification"] == "NOT_RUN", "remote report not local bytes")
    require(is_sha(golden["source_index_sha256_reported"]), "reported index digest")
    require(golden["reported_decisions"] == ["WAIT", "MOVE_AWAY", "MOVE_AWAY"],
            "reported choice change")
    require(golden["reported_actions"] == 2 and golden["reported_memories"] == 2,
            "reported Action/Memory change")
    require(golden["reported_l2_status"] == "EXPIRED_WORLD_ADVANCED",
            "stale status")
    require(golden["learning_updates"] == 0 and golden["habit_grants"] == 0,
            "false learning promotion")
    require(golden["goal_success"] == "UNDETERMINED"
            and golden["stop_ack"] == "UNDETERMINED", "goal/STOP proof promotion")
    return obj


def golden_audit(source: Path | None = None) -> dict[str, Any]:
    """Verify original three known bytes and existing S49+Memory projection if present.

    The known SHA declarations are from #537/#588; local recomputation is NOT
    a proof of physical process authenticity, signed goals or missing raw L2 HTTP.
    """
    info: dict[str, Any] = {
        "schema": SCHEMA, "source_head": GOLDEN_HEAD,
        "source_session": GOLDEN_SESSION, "original_bytes": "NOT_RUN",
        "native_projection": "NOT_RUN", "report_class": "GITHUB_REPORTED_ONLY",
        "reported_native_observations": 3, "reported_decisions": 3,
        "reported_physical_action_outcomes": 2, "reported_observed_memories": 2,
        "reported_l2": "EXPIRED_WORLD_ADVANCED",
        "s10_learning": "NOT_QUALIFIED", "s11_habit": "NOT_QUALIFIED",
        "goal_success": "UNDETERMINED", "stop_ack": "UNDETERMINED",
        "raw_l2_request_response": "ABSENT_REPORTED",
        "new_physical_actions": 0, "new_model_calls": 0,
    }
    if source is None:
        return info
    require(source.is_absolute() and source.is_dir() and not source.is_symlink(),
            "existing absolute original source directory required")
    paths = {name: source / name for name in GOLDEN_SHA}
    index = r1.read_only_receipt_index(paths)
    for name, digest in GOLDEN_SHA.items():
        require(index[str(paths[name])] == digest, "golden original SHA256 mismatch: " + name)
    # Reuse R1 validation for all refs and a second independent index read.
    env = r1.plan("V")
    refs = [{"path": str(p), "sha256": index[str(p)]} for p in paths.values()]
    r1.validate_evidence({
        "schema": r1.SCHEMA, "lane": "V",
        "source_head": GOLDEN_HEAD,
        "environment_profile_sha256": env["profile_sha256"],
        "source_session": GOLDEN_SESSION,
        "world_identity": None, "model_identity": None,
        "original_receipt_refs": refs, "action_outcome_refs": [],
        "cleanup_observations": {
            "backend_stop_ack": "UNKNOWN", "gpu_quiescence": "UNKNOWN",
            "native_stop_ack": "UNKNOWN",
        },
        "terminal_classification": "V1_READ_ONLY_AUDIT",
        "evidence_sha256_index": index,
        "physical_execution_authorized": False, "science_qualified": False,
        "timeline_is_physical_proof": False,
    }, verify_receipts=True)

    from adapters.mineflayer.self_timeline import _read_json, timeline
    from relay_self.persistent_cognition import load_persistent_cognition

    data = _read_json(paths["native_report.json"])
    lines = paths["live_l2.jsonl"].read_text(encoding="utf-8").splitlines()
    require(len(lines) == 1, "L2 single original sidecar required")
    l2 = json.loads(lines[0])
    memory = load_persistent_cognition(paths["observed_memory.json"])
    rows = timeline(data, live_l2=l2, memory=memory)
    summaries = [row for row in rows if row["kind"] == "summary"]
    require(len(summaries) == 1, "missing independent projection summary")
    summary = summaries[0]
    require(summary["session"] == GOLDEN_SESSION
            and summary["decisions"] == 3
            and summary["native_action_outcomes"] == 2
            and summary["observed_memory_episodes"] == 2
            and summary["world_goal_success_attested"] is False
            and summary["production_habit_promoted"] is False,
            "Golden Action/Memory/source projection mismatch")
    choices = [row["candidate"] for row in rows if row["kind"] == "selection"]
    require(choices == ["WAIT", "MOVE_AWAY", "MOVE_AWAY"],
            "Golden decisions mismatch")
    statuses = [row["status"] for row in rows if row["kind"] == "l2_observer"]
    require(statuses == ["EXPIRED_WORLD_ADVANCED"], "Golden L2 stale fence mismatch")
    info.update({
        "original_bytes": "THREE_KNOWN_SHA256_MATCH_R1_READONLY",
        "native_projection": "EXISTING_S49_L2_MEMORY_CONTRACT_PASS",
        "report_class": "ORIGINAL_DIGEST_AND_PROJECTION_VERIFIED_NOT_PHYSICAL_REATTESTATION",
    })
    return info


CASE_FIELDS = {
    "source_sha256", "cheap_source_sha256", "source_session",
    "cheap_source_session", "candidate_actions", "cheap_actions",
    "oracle_leakage", "stale_l2_as_action", "unknown_as_success",
    "heldout_lineage_disjoint", "cheap_baseline_run", "goal_receipts_verified",
    "world_outcome_delta", "resource_adjusted_delta", "costs_measured",
    "independent_reuse",
}


def admission(case: dict[str, Any]) -> dict[str, Any]:
    """Prospective conservative gates; never grants science/physical permission.

    Values are caller-supplied evaluation proposals, NOT authenticated source.
    A positive candidate still requires independent witness review.
    """
    require(type(case) is dict and set(case) == CASE_FIELDS, "comparison fields not exact")
    for key in ("source_sha256", "cheap_source_sha256"):
        require(is_sha(case[key]), "source receipt SHA missing")
    require(all(isinstance(case[k], str) and case[k]
                for k in ("source_session", "cheap_source_session")), "source session missing")
    for key in ("candidate_actions", "cheap_actions"):
        require(type(case[key]) is list and bool(case[key])
                and all(isinstance(x, str) and x for x in case[key])
                and len(set(case[key])) == len(case[key]), "invalid Action candidate set")
    for key in ("oracle_leakage", "stale_l2_as_action", "unknown_as_success",
                "heldout_lineage_disjoint", "cheap_baseline_run",
                "goal_receipts_verified", "costs_measured", "independent_reuse"):
        require(type(case[key]) is bool, "untyped evaluation flag " + key)
    for key in ("world_outcome_delta", "resource_adjusted_delta"):
        require(case[key] is None or (
            type(case[key]) in (int, float) and -1e12 < case[key] < 1e12),
            "invalid measured delta")
    gates = {f"G{i}": "UNDETERMINED" for i in range(6)}
    if (case["source_sha256"] != case["cheap_source_sha256"]
            or case["source_session"] != case["cheap_source_session"]
            or set(case["candidate_actions"]) != set(case["cheap_actions"])
            or case["oracle_leakage"] or case["stale_l2_as_action"]
            or case["unknown_as_success"]):
        gates["G0"] = "NO_GO_SOURCE_OR_AUTHORITY"
    else:
        gates["G0"] = "MATCHED_CLAIM_UNATTESTED"
        if case["heldout_lineage_disjoint"]:
            gates["G1"] = "DESIGN_ONLY_NO_MEASUREMENT_ATTESTATION"
        if case["cheap_baseline_run"]:
            gates["G2"] = "CHEAP_COMPARISON_CLAIM_UNATTESTED"
            if case["goal_receipts_verified"] and case["world_outcome_delta"] is not None:
                if case["world_outcome_delta"] <= 0:
                    gates["G3"] = "NO_GO_NO_INCREMENTAL_GOAL_GAIN"
                else:
                    gates["G3"] = "REVIEW_WITNESSES_REQUIRED"
                    if case["costs_measured"] and case["resource_adjusted_delta"] is not None:
                        gates["G4"] = (
                            "NO_GO_NO_RESOURCE_GAIN" if case["resource_adjusted_delta"] <= 0
                            else "REVIEW_WITNESSES_REQUIRED"
                        )
                        if case["independent_reuse"]:
                            gates["G5"] = "REVIEW_INDEPENDENT_LINEAGES_REQUIRED"
    return {
        "schema": SCHEMA, "gates": gates,
        "science_qualified": False, "physical_execution_authorized": False,
        "classification": (
            "NO_GO" if any(s.startswith("NO_GO") for s in gates.values())
            else "UNDETERMINED_INDEPENDENT_REVIEW_REQUIRED"
        ),
    }


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--golden-dir", type=Path, help="existing sealed original root; read only")
    p.add_argument("--comparison-json", type=Path, help="existing prospective evaluation record")
    args = p.parse_args(argv)
    try:
        ledger = inventory()
        if args.comparison_json is not None:
            out = admission(json.loads(args.comparison_json.read_text(encoding="utf-8")))
        else:
            out = {
                "schema": SCHEMA, "inventory_claims": len(ledger["claims"]),
                "golden_audit": golden_audit(args.golden_dir),
                "science_g3": "NO_GO", "self1_product": "UNDETERMINED",
                "historical_46": "NON_DISCRIMINATING",
                "historical_415": "F46_SUCCESSOR_NO_EFFECT",
                "new_physical_actions": 0, "new_model_calls": 0,
            }
        print(json.dumps(out, ensure_ascii=False, indent=2, sort_keys=True))
        return 0
    except (OSError, ValueError, KeyError, TypeError, IndexError) as exc:
        print(json.dumps({
            "schema": SCHEMA, "classification": "V1_EVIDENCE_BLOCKED",
            "error": type(exc).__name__ + ":" + str(exc),
            "science_qualified": False, "physical_execution_authorized": False,
        }, sort_keys=True))
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
