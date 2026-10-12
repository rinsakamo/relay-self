"""RSEE R4: read-only S3 derived Memory projection to a V review candidate.

The original S49/S16 typed source remains S-owned; a JSONL event plus saved
Memory is DERIVED information, never native evidence or authority. Only a
separately existing R1 envelope and R2 matching raw bytes may support review.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from experiments.standard_env import shared_runtime as r1
from experiments.standard_env import source_handoff as r2
from relay_self.persistent_cognition import (
    PersistentCognitionError,
    load_persistent_cognition,
)

MAX_EVENTS_BYTES = 4 * 1024 * 1024
MAX_EVENTS = 4096
MAX_MEMORY_BYTES = 4 * 1024 * 1024
S3_HEAD = "6f493b7a559dd72ea365998b9eadbd35fd7eb9b4"
EVENT_SCHEMA = "SELF1_BOUNDED_WORLD_EVENT_V1"
EPISODE_SCHEMA = "L1_SOURCE_EPISODE_V1"
CLEANUP_SCHEMA = "SELF1_S1_OWNER_CLEANUP_V1"


class R4Rejected(ValueError):
    """Failed identity or derivation check; never attempt repairs or replay."""


def _must(ok: bool, why: str) -> None:
    if not ok:
        raise R4Rejected(why)


def _check_file(path: Path, root: Path, max_bytes: int) -> Path:
    try:
        r2._physical_receipt_root(root)
        r2._physical_file(path)
    except (ValueError, OSError) as exc:
        raise R4Rejected("canonical physical derived file/root required") from exc
    _must(path.is_relative_to(root), "derived file outside independent output root")
    _must(0 < path.stat().st_size <= max_bytes, "missing/oversized derived file")
    return path


def _read_json(path: Path, root: Path, max_bytes: int) -> Any:
    _check_file(path, root, max_bytes)
    try:
        return json.loads(path.read_bytes(), object_pairs_hook=r2._unique_pairs)
    except (ValueError, UnicodeError, OSError) as exc:
        raise R4Rejected("invalid derived JSON") from exc


def _events(path: Path, root: Path, session: str) -> list[dict[str, Any]]:
    _check_file(path, root, MAX_EVENTS_BYTES)
    try:
        raw = path.read_bytes()
        lines = raw.splitlines()
        _must(0 < len(lines) <= MAX_EVENTS, "derived events missing or excessive")
        _must(all(line.strip() for line in lines), "blank/partial event row")
        records = [
            json.loads(line, object_pairs_hook=r2._unique_pairs)
            for line in lines
        ]
    except (ValueError, UnicodeError, OSError) as exc:
        raise R4Rejected("invalid original S3 event projection") from exc
    for number, record in enumerate(records):
        _must(type(record) is dict, "derived event row must be object")
        _must(record.get("schema") == EVENT_SCHEMA
              and record.get("session") == session
              and type(record.get("index")) is int
              and record["index"] == number
              and isinstance(record.get("kind"), str)
              and isinstance(record.get("source"), str)
              and record["source"] == "S49_OWNER_EXPLICIT_REAL_OR_SYNTHETIC",
              "S3 event identity/order/source mismatch")
    _must(records[0]["kind"] == "session_started", "missing bounded session start")
    _must(sum(row["kind"] == "session_terminal" for row in records) == 1,
          "missing or duplicate terminal")
    _must(records[-1]["kind"] == "session_terminal",
          "session terminal must close immutable event projection")
    return records


def _memory(path: Path, root: Path, session: str) -> dict[str, dict[str, Any]]:
    _check_file(path, root, MAX_MEMORY_BYTES)
    try:
        snapshot = load_persistent_cognition(path)
    except (OSError, ValueError, PersistentCognitionError) as exc:
        raise R4Rejected("existing Memory owner snapshot failed to decode") from exc
    _must(snapshot.identity.self_id == f"s3-session:{session}",
          "Memory source session identity mismatch")
    _must(not snapshot.appraisal_dispositions,
          "appraisal/learning structure not admitted by R4")
    episodes: dict[str, dict[str, Any]] = {}
    for item in snapshot.memories:
        try:
            entry = json.loads(item.content, object_pairs_hook=r2._unique_pairs)
        except (ValueError, UnicodeError) as exc:
            raise R4Rejected("invalid retained episode content") from exc
        _must(type(entry) is dict and set(entry) == {
            "schema", "session_id", "world_revision", "action_id",
            "binding_id", "action_ref", "source_status", "disposition",
            "reason_code", "evidence_sha256", "cue_tags", "hypothesis",
        }, "unexpected retained episode fields")
        _must(entry["schema"] == EPISODE_SCHEMA
              and entry["session_id"] == session
              and type(entry["world_revision"]) is int
              and entry["world_revision"] >= 0
              and isinstance(entry["action_id"], str)
              and bool(entry["action_id"])
              and item.memory_id == (
                  f"l1:{session}:{entry['action_id']}:{entry['world_revision']}"
              )
              and entry["disposition"] == "outcome"
              and entry["cue_tags"] == ["near_zombie"]
              and entry["hypothesis"] is None
              and isinstance(entry["evidence_sha256"], str)
              and r1.SHA.fullmatch(entry["evidence_sha256"])
              and item.integration_provenance.source == "self-s3-original-s16-observation"
              and item.integration_provenance.reference
              == f"{session}:{entry['action_id']}:{entry['evidence_sha256']}",
              "retained episode not S3 source-qualified projection")
        _must(item.memory_id not in episodes, "duplicate retained Memory")
        episodes[item.memory_id] = entry
    return episodes


def audit(
    *, derived_root: Path, events: Path, memory: Path, cleanup: Path,
    envelope: Path, original_root: Path, expected_head: str,
    expected_profile_sha256: str, expected_session: str,
) -> dict[str, Any]:
    """Compare S3 DERIVED event+Memory to separately checked original bytes.

    Does not produce an R1 envelope, native frames, typed S16 reconstruction,
    positive V science outcome, or on-disk review artifact.
    """
    _must(expected_head == S3_HEAD, "S3 frozen source HEAD required")
    _must(isinstance(expected_session, str) and bool(expected_session.strip()),
          "independent S49 session required")
    _must(isinstance(expected_profile_sha256, str)
          and bool(r1.SHA.fullmatch(expected_profile_sha256)),
          "independently resolved environment profile SHA256 required")
    # The derived files never count as R2 original source evidence.
    _must(len({str(events), str(memory), str(cleanup), str(envelope)}) == 4,
          "derived and original envelope paths must be distinct")
    observed = _events(events, derived_root, expected_session)
    episodes = _memory(memory, derived_root, expected_session)
    finished = _read_json(cleanup, derived_root, MAX_MEMORY_BYTES)
    _must(type(finished) is dict
          and finished.get("schema") == CLEANUP_SCHEMA
          and finished.get("session") == expected_session
          and finished.get("native_stop_ack") is False
          and finished.get("model_stop_ack") is False
          and finished.get("gpu_release_claimed") is False
          and finished.get("physical_action_replay") is False,
          "S3 owner cleanup status/source mismatch")
    retained = [row for row in observed if row["kind"] == "experience_retained_observation"]
    not_retained = [row for row in observed if row["kind"] == "experience_not_retained"]
    _must(not not_retained, "S3 had unretained Action evidence; partial projection")
    _must(len(retained) == len(episodes), "S3 event and durable Memory count mismatch")
    seen: set[str] = set()
    for row in retained:
        memory_id = row.get("memory_id")
        entry = episodes.get(memory_id)
        _must(isinstance(memory_id, str)
              and memory_id not in seen and entry is not None,
              "foreign/duplicate memory reference in S3 event")
        seen.add(memory_id)
        _must(row.get("session") == expected_session
              and row.get("evidence_sha256") == entry["evidence_sha256"]
              and type(row.get("source_seq")) is int
              and row["source_seq"] == entry["world_revision"]
              and row.get("action_authority") is False
              and row.get("goal_success_attested") is False
              and row.get("learning_updates") == 0
              and row.get("habit_grants") == 0,
              "S3 event/Memory evidence lineage or authority mismatch")
    projected = {
        "schema": "RSEE_R4_V_REVIEW_CANDIDATE_ONLY",
        "source_head": expected_head,
        "source_session": expected_session,
        "environment_profile_sha256": expected_profile_sha256,
        "s3_event_rows": len(observed),
        "retained_observation_count": len(retained),
        "no_s10_learning_or_s11_habit_attested": True,
        "native_source_semantics_attested": False,
        "action_correlation_attested": False,
        "physical_execution_authorized": False,
        "science_qualified": False,
        "v_admission_granted": False,
    }
    # Do not turn zero Action/retention or a historical 181-frame count into
    # an acceptable V Action receipt. No R2 original check can be skipped.
    if not retained:
        return {
            **projected,
            "classification": "RSEE_R4_NO_RETAINED_ACTION_NOT_V_ADMISSIBLE",
            "r2_original_bytes": "NOT_CHECKED",
            "reason": "No S3 retained Action/OUTCOME witness",
        }
    # Only consume an existing independently produced R1 envelope.
    try:
        r2_result = r2.audit_file(
            envelope, producer_lane="S", consumer_lane="V",
            expected_head=expected_head,
            expected_profile_sha256=expected_profile_sha256,
            expected_session=expected_session, receipt_root=original_root,
            require_action_outcome=True,
        )
    except (OSError, ValueError) as exc:
        raise R4Rejected("R2 independent raw-source handoff blocked") from exc
    indexed = json.loads(envelope.read_bytes(), object_pairs_hook=r2._unique_pairs)
    _must(not any(str(path) in indexed["evidence_sha256_index"]
                  for path in (events, memory, cleanup, envelope)),
          "derived files cannot masquerade as original native Action receipts")
    return {
        **projected,
        "classification": "RSEE_R4_DERIVED_MEMORY_MATCH_R2_BYTES_REVIEW_ONLY",
        "r2_original_bytes": r2_result["classification"],
        "raw_receipt_file_count": r2_result["original_files_sha256_checked"],
        "original_action_file_count": r2_result["action_outcome_original_files_declared"],
        "r2_envelope_sha256": r2_result["evidence_envelope_sha256"],
        "v_result": "UNDETERMINED_INDEPENDENT_V_OWNER_REQUIRED",
        "side_effects": "NO_WRITE_NO_ACTION_NO_PROCESS",
    }


def plan() -> dict[str, Any]:
    return {
        "classification": "RSEE_R4_PLAN_ONLY",
        "native_originals": "NOT_READ",
        "s3_derivation": "NOT_READ",
        "physical_execution_authorized": False,
        "v_admission_granted": False,
        "science_qualified": False,
    }


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--verify", action="store_true")
    p.add_argument("--derived-root", type=Path)
    p.add_argument("--original-root", type=Path)
    p.add_argument("--envelope", type=Path)
    p.add_argument("--expected-head")
    p.add_argument("--expected-profile-sha256")
    p.add_argument("--expected-session")
    args = p.parse_args(argv)
    try:
        supplied = (
            args.derived_root, args.original_root, args.envelope,
            args.expected_head, args.expected_profile_sha256, args.expected_session,
        )
        if not args.verify:
            _must(all(x is None for x in supplied),
                  "--verify required for any original-source input")
            output = plan()
        else:
            _must(all(x is not None for x in supplied),
                  "operator-selected existing originals and independent source required")
            root = args.derived_root
            output = audit(
                derived_root=root,
                events=root / "session_events.jsonl",
                memory=root / "s3_observed_memory.json",
                cleanup=root / "owned_cleanup.json",
                envelope=args.envelope,
                original_root=args.original_root,
                expected_head=args.expected_head,
                expected_profile_sha256=args.expected_profile_sha256,
                expected_session=args.expected_session,
            )
    except (OSError, ValueError, TypeError, KeyError) as exc:
        output = {
            "classification": "RSEE_R4_EVIDENCE_CHAIN_BLOCKED",
            "error": type(exc).__name__ + ":" + str(exc),
            "physical_execution_authorized": False,
            "v_admission_granted": False,
            "science_qualified": False,
        }
    print(json.dumps(output, ensure_ascii=False, sort_keys=True))
    # An informative zero-retention report is not a successful V handoff.
    return 0 if output["classification"] in (
        "RSEE_R4_PLAN_ONLY",
        "RSEE_R4_DERIVED_MEMORY_MATCH_R2_BYTES_REVIEW_ONLY",
    ) else 2


if __name__ == "__main__":
    raise SystemExit(main())
