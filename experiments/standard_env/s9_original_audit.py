"""RSEE R6: passive S9 predecode bridge / source-receipt / S3 Memory readback.

Exact historical S9 expectations are OPERATOR-REPORTED, not independently
attested by this repository. The local original bytes must be read and hashed
on the actual operator host. Passing is review-only, never V admission.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from experiments.standard_env import s3_v_projection as r4
from experiments.standard_env import source_handoff as r2

RECEIVED = "native_bridge_received_original.jsonl"
SENT = "native_bridge_sent_original.jsonl"
INDEX = "native_bridge_source_receipt.json"
SESSION = "dacf338b-4ba9-4e91-8eea-d4aebd0aef22"
S9_HEAD = "916814742567f8ff396b5c078d22f897d8418927"
MAX_CAPTURE = 16 * 1024 * 1024
MAX_LINES = 4096


@dataclass(frozen=True, slots=True)
class ExpectedS9:
    head: str
    session: str
    received_sha256: str
    sent_sha256: str
    received_lines: int
    sent_lines: int
    received_bytes: int
    sent_bytes: int


# These values are independently declared in S9's #537 operator report.
# They are expected comparands, NOT independent host-byte attestations.
OPERATOR_REPORTED_S9 = ExpectedS9(
    head=S9_HEAD,
    session=SESSION,
    received_sha256="614bdb6be1cff97ad598b49be5dd0beaf21bc5a440933d8af91a1f5860703844",
    sent_sha256="23d5feb0ebff8c43c374817bcd1e05f72714dcbf55db9792075ba072a4895000",
    received_lines=39, sent_lines=14,
    received_bytes=21924, sent_bytes=897,
)


class S9AuditRejected(ValueError):
    """Missing, foreign, inconsistent or modified original bytes."""


def _must(ok: bool, reason: str) -> None:
    if not ok:
        raise S9AuditRejected(reason)


def _raw_stream(
    path: Path, root: Path, *, session: str, incoming: bool,
) -> tuple[str, int, int]:
    # R2's physical path gate rejects symlinks, foreign paths and aliases.
    r4._check_file(path, root, MAX_CAPTURE)
    try:
        raw = path.read_bytes()
        lines = raw.splitlines(keepends=True)
        _must(bool(lines) and len(lines) <= MAX_LINES, "source stream line bound")
        _must(all(0 < len(line) <= 1024 * 1024 and line.endswith(b"\n")
                  for line in lines), "partial/oversized predecode bridge line")
        for number, line in enumerate(lines):
            row = json.loads(line.decode("utf-8"), object_pairs_hook=r2._unique_pairs)
            _must(type(row) is dict, "original bridge row must be object")
            if incoming:
                _must(row.get("session_id") == session
                      and type(row.get("seq")) is int
                      and row["seq"] == number,
                      "original bridge session/sequence mismatch")
                if number == 0:
                    _must(row.get("type") == "adapter_started",
                          "first original bridge line not startup")
    except (ValueError, UnicodeError, OSError) as exc:
        raise S9AuditRejected("invalid predecode bridge original") from exc
    return hashlib.sha256(raw).hexdigest(), len(lines), len(raw)


def audit(root: Path, *, expected: ExpectedS9 = OPERATOR_REPORTED_S9) -> dict[str, Any]:
    """Opt-in read-only actual host check; no R1 envelope/World process issued."""
    _must(type(expected) is ExpectedS9, "independent frozen expectations required")
    _must(expected.head == S9_HEAD and expected.session == SESSION,
          "S9 exact source HEAD/session required")
    try:
        r2._physical_receipt_root(root)
    except (ValueError, OSError) as exc:
        raise S9AuditRejected("physical canonical S9 original directory required") from exc
    received = root / RECEIVED
    sent = root / SENT
    recv_hash, recv_count, recv_bytes = _raw_stream(
        received, root, session=expected.session, incoming=True,
    )
    sent_hash, sent_count, sent_bytes = _raw_stream(
        sent, root, session=expected.session, incoming=False,
    )
    _must((recv_hash, sent_hash, recv_count, sent_count, recv_bytes, sent_bytes) == (
        expected.received_sha256, expected.sent_sha256,
        expected.received_lines, expected.sent_lines,
        expected.received_bytes, expected.sent_bytes,
    ), "original bridge differs from independent S9 reported hashes/counts")

    index = r4._read_json(root / INDEX, root, 1024 * 1024)
    _must(type(index) is dict
          and index.get("schema") == "SELF_S7_RAW_MINEFLAYER_JSONL_RECEIPT_V1"
          and index.get("received_path") == str(received)
          and index.get("sent_path") == str(sent)
          and index.get("received_sha256") == recv_hash
          and index.get("sent_sha256") == sent_hash
          and index.get("received_lines") == recv_count
          and index.get("sent_lines") == sent_count
          and index.get("received_bytes") == recv_bytes
          and index.get("sent_bytes") == sent_bytes
          and index.get("received_measured_before_decode") is True
          and index.get("sent_measured_before_write") is True
          and index.get("minecraft_tcp_packet_bytes") is False
          and index.get("native_execution_ack_attested") is False
          and index.get("v_science_qualified") is False,
          "S7 source receipt contradicts original stream bytes or source scope")

    # Use exactly the existing R4 interpretation, never reconstruct S16 owner.
    events = r4._events(root / "session_events.jsonl", root, expected.session)
    memories = r4._memory(root / "s3_observed_memory.json", root, expected.session)
    retained = [x for x in events if x["kind"] == "experience_retained_observation"]
    _must(len(retained) == len(memories) == 2,
          "S9 required two matching retained observations")
    _must(not any(x["kind"] in {"experience_not_retained", "session_failed"}
                  for x in events), "partial/failed S9 source event")
    seen: set[str] = set()
    action_ids: set[str] = set()
    for entry in retained:
        mid = entry.get("memory_id")
        data = memories.get(mid)
        _must(isinstance(mid, str) and mid not in seen and data is not None,
              "foreign/duplicate S9 retained Memory event")
        seen.add(mid)
        _must(entry.get("session") == expected.session
              and entry.get("evidence_sha256") == data["evidence_sha256"]
              and type(entry.get("source_seq")) is int
              and entry["source_seq"] == data["world_revision"]
              and entry.get("action_authority") is False
              and entry.get("goal_success_attested") is False
              and entry.get("learning_updates") == 0
              and entry.get("habit_grants") == 0,
              "S9 event/Memory lineage or authority mismatch")
        action_ids.add(data["action_id"])
    _must(len(action_ids) == 2, "distinct S9 action IDs required")
    _must(retained[0]["source_seq"] < retained[1]["source_seq"],
          "S9 retained source epochs not ordered")
    cleanup = r4._read_json(root / "owned_cleanup.json", root, 1024 * 1024)
    _must(type(cleanup) is dict
          and cleanup.get("schema") == r4.CLEANUP_SCHEMA
          and cleanup.get("session") == expected.session
          and cleanup.get("node_exit") == 0
          and cleanup.get("server_exit") == 0
          and cleanup.get("native_stop_ack") is False
          and cleanup.get("model_stop_ack") is False
          and cleanup.get("gpu_release_claimed") is False
          and cleanup.get("physical_action_replay") is False,
          "S9 cleanup record incomplete or falsely promoted")
    return {
        "classification": "RSEE_R6_S9_ORIGINAL_BRIDGE_AND_MEMORY_BYTES_REVIEW_ONLY",
        "source_head": expected.head,
        "source_session": expected.session,
        "received_sha256_verified": recv_hash,
        "sent_sha256_verified": sent_hash,
        "received_original_lines": recv_count,
        "sent_attempt_lines": sent_count,
        "retained_memory_count": len(retained),
        "distinct_reported_action_ids": len(action_ids),
        "source_scope": "MINEFLAYER_BRIDGE_JSONL_NOT_MINECRAFT_TCP",
        "hash_expectation_origin": "S9_OPERATOR_REPORT_NOT_INDEPENDENT_PHYSICAL_ATTESTATION",
        "r1_envelope_verified": False,
        "r2_raw_handoff_admitted": False,
        "typed_s16_semantics_attested": False,
        "memory_causal_effect_attested": False,
        "native_stop_ack_attested": False,
        "goal_success_attested": False,
        "science_qualified": False,
        "v_admission_granted": False,
        "physical_execution_authorized": False,
        "side_effects": "READ_ONLY_NO_WRITE_NO_PROCESS",
    }


def plan() -> dict[str, Any]:
    return {
        "classification": "RSEE_R6_PLAN_ONLY",
        "s9_original_host_bytes": "NOT_READ",
        "r2_raw_handoff_admitted": False,
        "v_admission_granted": False,
        "science_qualified": False,
        "physical_execution_authorized": False,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path)
    args = parser.parse_args(argv)
    try:
        output = plan() if args.root is None else audit(args.root)
    except (OSError, ValueError, TypeError, KeyError) as exc:
        output = {
            "classification": "RSEE_R6_S9_ORIGINAL_READBACK_BLOCKED",
            "error": type(exc).__name__ + ":" + str(exc),
            "r2_raw_handoff_admitted": False,
            "v_admission_granted": False,
            "science_qualified": False,
            "physical_execution_authorized": False,
        }
    print(json.dumps(output, sort_keys=True, ensure_ascii=False))
    return 0 if output["classification"] in (
        "RSEE_R6_PLAN_ONLY",
        "RSEE_R6_S9_ORIGINAL_BRIDGE_AND_MEMORY_BYTES_REVIEW_ONLY",
    ) else 2


if __name__ == "__main__":
    raise SystemExit(main())
