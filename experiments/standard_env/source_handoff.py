"""RSEE R2: read-only cross-lane raw evidence handoff (not new authority).

Only an R1 provenance envelope with already-existing, byte-matched original
files can be passed to an independent S/L/V reviewer. SHA checks do NOT
authenticate native World provenance, ownership, permissions, or science.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import stat
from pathlib import Path
from typing import Any

from experiments.standard_env import shared_runtime as r1

MAX_ENVELOPE_BYTES = 1024 * 1024
MAX_ORIGINALS = 256


class HandoffRejected(ValueError):
    """Unbound/unsafe raw evidence, without fallback or inferred proof."""


def _must(value: bool, message: str) -> None:
    if not value:
        raise HandoffRejected(message)


def _physical_file(path: Path) -> Path:
    _must(path.is_absolute(), "original file path must be absolute")
    _must(path.is_file() and not path.is_symlink(), "original regular file required")
    _must(stat.S_ISREG(path.lstat().st_mode), "special file rejected")
    try:
        _must(not any(parent.is_symlink() for parent in (path.parent, *path.parent.parents)),
              "symlinked ancestor rejected")
        _must(path.resolve(strict=True) == path, "noncanonical source path rejected")
    except OSError as exc:
        raise HandoffRejected("original path could not be read") from exc
    return path


def _physical_receipt_root(path: Path) -> Path:
    _must(path.is_absolute() and path.is_dir() and not path.is_symlink(),
          "absolute physical receipt root required")
    _must(not any(parent.is_symlink() for parent in (path.parent, *path.parent.parents)),
          "symlinked original receipt root ancestry")
    try:
        _must(path.resolve(strict=True) == path, "receipt root must be canonical")
    except OSError as exc:
        raise HandoffRejected("receipt root unavailable") from exc
    return path


def plan(producer_lane: str, consumer_lane: str) -> dict[str, Any]:
    """Pure/no-files default, safe for arbitrary S/L/V worktrees."""
    _must(producer_lane in r1.LANES and consumer_lane in r1.LANES,
          "R1 S/L/V lane required")
    _must(producer_lane != consumer_lane, "independent cross-lane reviewer required")
    return {
        "classification": "RSEE_R2_PLAN_ONLY",
        "producer_lane": producer_lane,
        "consumer_lane": consumer_lane,
        "original_receipts": "NOT_READ",
        "native_provenance_attested": False,
        "physical_execution_authorized": False,
        "science_qualified": False,
        "side_effects": "NONE",
    }


def audit(
    record: dict[str, Any], *, producer_lane: str, consumer_lane: str,
    expected_head: str, expected_profile_sha256: str, expected_session: str,
    receipt_root: Path, require_action_outcome: bool = False,
) -> dict[str, Any]:
    """Strict expected-source comparison, external original SHA verification.

    Input expectations come from the independent consumer; record claims cannot
    supply or overwrite their values. This verifies bytes ONLY, not physical
    source, process exit, STOP ACK, World outcome or scientific benefit.
    """
    planned = plan(producer_lane, consumer_lane)
    _must(type(record) is dict, "R1 provenance object required")
    _must(isinstance(expected_head, str) and bool(r1.HEAD.fullmatch(expected_head)),
          "independent expected HEAD invalid")
    _must(isinstance(expected_profile_sha256, str)
          and bool(r1.SHA.fullmatch(expected_profile_sha256)),
          "independent expected profile SHA invalid")
    _must(isinstance(expected_session, str) and bool(expected_session.strip()),
          "independent expected native session required")
    _must(type(require_action_outcome) is bool, "typed Action requirement required")

    try:
        r1.validate_evidence(record)
    except (ValueError, TypeError, KeyError) as exc:
        raise HandoffRejected("R1 provenance envelope rejected") from exc

    _must(record["lane"] == producer_lane, "producer lane mismatch")
    _must(record["source_head"] == expected_head, "source HEAD mismatch")
    _must(record["environment_profile_sha256"] == expected_profile_sha256,
          "RSEE profile SHA mismatch")
    _must(record["source_session"] == expected_session, "native session mismatch")
    _must(not require_action_outcome or bool(record["action_outcome_refs"]),
          "required original Action/OUTCOME evidence missing")

    originals = record["original_receipt_refs"]
    outcomes = record["action_outcome_refs"]
    index = record["evidence_sha256_index"]
    _must(bool(originals), "original native receipts missing")
    _must(bool(index) and len(index) <= MAX_ORIGINALS, "original index empty or excessive")
    _must(len(originals) <= MAX_ORIGINALS and len(outcomes) <= MAX_ORIGINALS,
          "receipt reference count excessive")
    original_paths = [row["path"] for row in originals]
    outcome_paths = [row["path"] for row in outcomes]
    _must(len(original_paths) == len(set(original_paths)), "duplicate original receipt")
    _must(len(outcome_paths) == len(set(outcome_paths)), "duplicate original outcome")
    _must(set(index) == set(original_paths) | set(outcome_paths),
          "unreferenced or missing indexed original")
    root = _physical_receipt_root(receipt_root)
    for source in index:
        path = _physical_file(Path(source))
        _must(path.is_relative_to(root), "foreign receipt root rejected")
        _must(not any(word in path.name.lower() for word in ("timeline", "replay")),
              "display projection cannot be primary physical receipt")

    # Reuse R1's byte-level readback, never rewrite, copy, or fabricate receipts.
    try:
        r1.validate_evidence(record, verify_receipts=True)
    except (ValueError, TypeError, KeyError, OSError) as exc:
        raise HandoffRejected("original receipt SHA256 mismatch/unavailable") from exc
    canonical = json.dumps(record, sort_keys=True, separators=(",", ":"),
                           ensure_ascii=False, allow_nan=False).encode("utf-8")
    return {
        **planned,
        "classification": "RSEE_R2_RAW_BYTES_MATCH_REVIEW_ONLY",
        "source_head": expected_head,
        "environment_profile_sha256": expected_profile_sha256,
        "source_session_claim": expected_session,
        "receipt_root": str(root),
        "original_files_sha256_checked": len(index),
        "action_outcome_original_files_declared": len(outcomes),
        "evidence_envelope_sha256": hashlib.sha256(canonical).hexdigest(),
        "terminal_classification_reported": record["terminal_classification"],
        "cleanup_claims_only": record["cleanup_observations"],
        "source_native_event_semantics_attested": False,
        "backend_stop_ack_attested": False,
        "lease_release_attested": False,
        "physical_execution_authorized": False,
        "science_qualified": False,
        "side_effects": "NO_WRITE_NO_LAUNCH_NO_GRANT",
    }


def audit_file(
    path: Path, *, producer_lane: str, consumer_lane: str,
    expected_head: str, expected_profile_sha256: str, expected_session: str,
    receipt_root: Path, require_action_outcome: bool = False,
) -> dict[str, Any]:
    """Opt-in read-only envelope loading, bounded before parsing."""
    _physical_file(path)
    _must(path.stat().st_size <= MAX_ENVELOPE_BYTES, "oversized evidence envelope")
    try:
        with path.open("rb") as handle:
            raw = handle.read(MAX_ENVELOPE_BYTES + 1)
        _must(len(raw) <= MAX_ENVELOPE_BYTES, "oversized evidence envelope")
        data = json.loads(raw, object_pairs_hook=_unique_pairs)
    except (OSError, ValueError, UnicodeError) as exc:
        raise HandoffRejected("invalid existing evidence envelope") from exc
    return audit(
        data, producer_lane=producer_lane, consumer_lane=consumer_lane,
        expected_head=expected_head,
        expected_profile_sha256=expected_profile_sha256,
        expected_session=expected_session,
        receipt_root=receipt_root,
        require_action_outcome=require_action_outcome,
    )


def _unique_pairs(rows: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in rows:
        _must(key not in result, "duplicate JSON envelope key")
        result[key] = value
    return result


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--from-lane", required=True, choices=r1.LANES)
    parser.add_argument("--to-lane", required=True, choices=r1.LANES)
    parser.add_argument("--envelope", type=Path)
    parser.add_argument("--receipt-root", type=Path)
    parser.add_argument("--expected-head")
    parser.add_argument("--expected-profile-sha256")
    parser.add_argument("--expected-session")
    parser.add_argument("--require-action-outcome", action="store_true")
    args = parser.parse_args(argv)
    try:
        if args.envelope is None:
            _must(not any((args.receipt_root, args.expected_head,
                           args.expected_profile_sha256, args.expected_session,
                           args.require_action_outcome)),
                  "evidence fields require --envelope")
            result = plan(args.from_lane, args.to_lane)
        else:
            _must(args.receipt_root is not None
                  and args.expected_head is not None
                  and args.expected_profile_sha256 is not None
                  and args.expected_session is not None,
                  "independent expected source and original root are required")
            result = audit_file(
                args.envelope,
                producer_lane=args.from_lane, consumer_lane=args.to_lane,
                receipt_root=args.receipt_root,
                expected_head=args.expected_head,
                expected_profile_sha256=args.expected_profile_sha256,
                expected_session=args.expected_session,
                require_action_outcome=args.require_action_outcome,
            )
    except (OSError, ValueError, TypeError) as exc:
        result = {
            "classification": "RSEE_R2_HANDOFF_BLOCKED",
            "failure": type(exc).__name__ + ":" + str(exc),
            "physical_execution_authorized": False,
            "science_qualified": False,
        }
    print(json.dumps(result, sort_keys=True, ensure_ascii=False, indent=2))
    return 0 if result["classification"] in (
        "RSEE_R2_PLAN_ONLY", "RSEE_R2_RAW_BYTES_MATCH_REVIEW_ONLY"
    ) else 2


if __name__ == "__main__":
    raise SystemExit(main())
