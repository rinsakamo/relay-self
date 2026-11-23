"""Q1b read-only S1 pre-boundary anchor vs S2 WAL continuity (CPU/offline).

A locally recalculated SHA, even of an anchor file, DOES NOT prove origin,
immutability or that the anchor preceded S2. The expected anchor SHA must be
obtained from a genuinely independent trusted witness BEFORE S2 by the
operator. This module can only check equality and structural continuity.
Existing original Stage28, WAL and checkpoint auditors remain necessary.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any

from experiments.q_lane_evidence_audit_dev import QEvidenceHold, _raw_file


class QS1BoundaryHold(QEvidenceHold):
    """Pinned pre-S2 S1 or append-only WAL continuity was not established."""


_FIELDS = {
    "schema", "phase", "head", "world_uuid", "owner_id", "self_id",
    "native_session_id", "checkpoint_generation",
    "s1_intent_id", "s1_skill_execution_id", "s1_action_id",
    "s1_status", "s1_wal_sha256", "s1_checkpoint_sha256",
    "s1_action_count",
}
_TERMINAL = {
    "NATIVE_MOVE_SETTLED",
    "NATIVE_MOVE_NO_NET_DISPLACEMENT",
    "NATIVE_PLACE_MOVE_SETTLED",
    "NATIVE_PLACE_MOVE_NO_PROGRESS",
    "NATIVE_PLACE_MOVE_OVERSHOOT",
    "NATIVE_EAT_OUTCOME",
    "NATIVE_ATTACK_HURT_OBSERVED",
}
_HEX = set("0123456789abcdef")


def _sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _digest(value: object) -> str:
    if type(value) is not str or len(value) != 64 or any(c not in _HEX for c in value):
        raise QS1BoundaryHold("Exact externally supplied SHA256 required")
    return value


def _identity(value: object, name: str) -> str:
    if type(value) is not str or not value or any(ch.isspace() for ch in value):
        raise QS1BoundaryHold(f"{name} must be a nonblank identifier")
    return value


def _strict_object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    out: dict[str, Any] = {}
    for key, value in pairs:
        if key in out:
            raise QS1BoundaryHold("Duplicate JSON field in WAL/anchor")
        out[key] = value
    return out


def _json(data: bytes) -> dict[str, Any]:
    try:
        parsed = json.loads(data, object_pairs_hook=_strict_object)
    except (UnicodeError, ValueError, TypeError) as exc:
        raise QS1BoundaryHold("Unparseable or noncanonical original evidence") from exc
    if type(parsed) is not dict:
        raise QS1BoundaryHold("Original evidence must be a mapping")
    return parsed


def verify_s1_s2_anchor(
    evidence_dir: Path, *, anchor_bytes: bytes,
    expected_pre_s2_anchor_sha256: str, s1_wal_path: str,
    s1_checkpoint_path: str, s2_wal_path: str,
    expected_s2_action_id: str,
    expected_head: str, expected_world_uuid: str,
    expected_owner_id: str, expected_self_id: str,
    expected_native_session_id: str,
    expected_checkpoint_generation: int,
) -> dict[str, Any]:
    """Compare pinned *historical* S1 with later WAL. No files are written."""
    if type(anchor_bytes) is not bytes or not anchor_bytes:
        raise QS1BoundaryHold("Original external anchor bytes required")
    expected_digest = _digest(expected_pre_s2_anchor_sha256)
    if _sha(anchor_bytes) != expected_digest:
        raise QS1BoundaryHold("Original pre-S2 anchor differs from external digest")
    if type(expected_head) is not str or len(expected_head) != 40 or any(
        c not in _HEX for c in expected_head
    ):
        raise QS1BoundaryHold("Exact code commit HEAD required")
    for value, name in (
        (expected_world_uuid, "world_uuid"), (expected_owner_id, "owner_id"),
        (expected_self_id, "self_id"), (expected_native_session_id, "native_session_id"),
        (expected_s2_action_id, "s2_action_id"),
    ):
        _identity(value, name)
    if (
        type(expected_checkpoint_generation) is not int
        or expected_checkpoint_generation < 0
    ):
        raise QS1BoundaryHold("Original checkpoint generation required")
    if len({s1_wal_path, s1_checkpoint_path, s2_wal_path}) != 3:
        raise QS1BoundaryHold("Original S1 snapshot and S2 WAL must be distinct files")

    anchor = _json(anchor_bytes)
    if set(anchor) != _FIELDS or anchor.get("schema") != 1 or anchor.get("phase") != (
        "S1_TERMINAL_PRE_S2"
    ):
        raise QS1BoundaryHold("S1 pre-S2 anchor format/phase mismatch")
    for field, expected in (
        ("head", expected_head), ("world_uuid", expected_world_uuid),
        ("owner_id", expected_owner_id), ("self_id", expected_self_id),
        ("native_session_id", expected_native_session_id),
        ("checkpoint_generation", expected_checkpoint_generation),
    ):
        if anchor[field] != expected or type(anchor[field]) is not type(expected):
            raise QS1BoundaryHold(f"S1 pre-S2 {field} mismatch")
    for field in ("s1_intent_id", "s1_skill_execution_id", "s1_action_id"):
        _identity(anchor[field], field)
    if anchor["s1_status"] not in _TERMINAL:
        raise QS1BoundaryHold("S1 terminal not a qualified physical outcome")
    if type(anchor["s1_action_count"]) is not int or anchor["s1_action_count"] < 1:
        raise QS1BoundaryHold("S1 Action count missing")

    root = evidence_dir.resolve(strict=True)
    try:
        old_raw = _raw_file(root, s1_wal_path)
        checkpoint_raw = _raw_file(root, s1_checkpoint_path)
        new_raw = _raw_file(root, s2_wal_path)
    except QEvidenceHold as exc:
        raise QS1BoundaryHold("Original S1/S2 artifact missing or untrusted") from exc
    if (
        _sha(old_raw) != _digest(anchor["s1_wal_sha256"])
        or _sha(checkpoint_raw) != _digest(anchor["s1_checkpoint_sha256"])
    ):
        raise QS1BoundaryHold("Original S1 WAL/checkpoint altered after external pin")
    old, new = _json(old_raw), _json(new_raw)
    if (
        old.get("self_id") != expected_self_id
        or new.get("self_id") != expected_self_id
        or old.get("schema") not in (1, 2)
        or new.get("schema") not in (1, 2)
    ):
        raise QS1BoundaryHold("Original S1/S2 WAL schema or Self mismatch")
    prior, after = old.get("actions"), new.get("actions")
    if type(prior) is not list or type(after) is not list:
        raise QS1BoundaryHold("Original WAL Action history absent")
    if len(prior) != anchor["s1_action_count"] or len(after) != len(prior) + 1:
        raise QS1BoundaryHold(
            "exactly one new S2 Action must follow the frozen S1 prefix"
        )
    if after[:len(prior)] != prior:
        raise QS1BoundaryHold("Historical S1 WAL row was altered/reordered")
    if any(type(row) is not dict for row in after):
        raise QS1BoundaryHold("Malformed original WAL Action row")
    ids = [row.get("action_id") for row in after]
    if any(type(item) is not str or not item for item in ids) or len(set(ids)) != len(ids):
        raise QS1BoundaryHold("Duplicate/replayed original WAL Action identity")
    if any(row.get("status") == "PREPARED_UNRESOLVED" for row in after):
        raise QS1BoundaryHold("Unresolved PREPARED Action cannot certify boundary")
    final_s1 = prior[-1]
    if (
        final_s1.get("action_id") != anchor["s1_action_id"]
        or final_s1.get("intent_id") != anchor["s1_intent_id"]
        or final_s1.get("skill_execution_id") != anchor["s1_skill_execution_id"]
        or final_s1.get("status") != anchor["s1_status"]
    ):
        raise QS1BoundaryHold("Anchored S1 original Intent/Skill/Action does not match")
    s2 = after[len(prior)]
    if (
        s2["action_id"] != expected_s2_action_id
        or expected_s2_action_id == anchor["s1_action_id"]
    ):
        raise QS1BoundaryHold("S2 new Action does not follow anchored S1")
    # Q1f: historical append-only identity alone is not an outcome. It
    # previously accepted arbitrary/missing S2 states as a positive receipt,
    # including PREPARED-like unknowns other than PREPARED_UNRESOLVED.
    # Accept only the narrow set of terminal physical result *labels*.
    # Original physical WAL validation/Native+Paper causality remain HOLD.
    if type(s2.get("status")) is not str or s2["status"] not in _TERMINAL:
        raise QS1BoundaryHold("S2 Action has no qualified terminal status label")
    for field in ("intent_id", "skill_execution_id", "session_id"):
        if type(s2.get(field)) is not str:
            raise QS1BoundaryHold("S2 original Intent/Skill/Native session missing")
        _identity(s2[field], field)
    if s2["session_id"] != expected_native_session_id:
        raise QS1BoundaryHold("S2 native session differs from original boundary")
    return {
        "classification": "Q1B_PINNED_S1_S2_WAL_PREFIX_CPU_OFFLINE_DEV",
        "head": expected_head,
        "self_id": expected_self_id,
        "s1_action_id": anchor["s1_action_id"],
        "s2_action_id": expected_s2_action_id,
        "s2_terminal_status_label": s2["status"],
        "s2_native_session_claim": s2["session_id"],
        "one_s2_action_appended": True,
        "s2_status_label_recognized": True,
        "s2_outcome_original_native_paper_attested": False,
        "s2_skill_success_attested": False,
        "s1_wal_sha256": _sha(old_raw),
        "s2_wal_sha256": _sha(new_raw),
        "s1_checkpoint_sha256": _sha(checkpoint_raw),
        "s1_action_count": len(prior),
        "s2_total_action_count": len(after),
        "trusted_external_anchor_origin_verified": False,
        "pre_s2_temporal_order_verified": False,
        "original_owner_semantics_verified": False,
        "original_stage28_checkpoint_restored": False,
        "real_world_attested": False,
        "qual_go": False,
        "science_run": False,
    }


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--evidence-dir", required=True, type=Path)
    p.add_argument("--external-anchor", required=True, type=Path)
    p.add_argument("--pre-s2-anchor-sha256", required=True)
    p.add_argument("--s1-wal", required=True)
    p.add_argument("--s1-checkpoint", required=True)
    p.add_argument("--s2-wal", required=True)
    p.add_argument("--s2-action-id", required=True)
    p.add_argument("--head", required=True)
    p.add_argument("--world-uuid", required=True)
    p.add_argument("--owner-id", required=True)
    p.add_argument("--self-id", required=True)
    p.add_argument("--native-session-id", required=True)
    p.add_argument("--checkpoint-generation", type=int, required=True)
    args = p.parse_args()
    try:
        root = args.evidence_dir.resolve(strict=True)
        # Separate pathname is necessary but not sufficient for independent trust.
        if args.external_anchor.resolve().is_relative_to(root):
            raise QS1BoundaryHold("External pre-S2 anchor is inside mutable evidence root")
        anchor = args.external_anchor.read_bytes()
        receipt = verify_s1_s2_anchor(
            root, anchor_bytes=anchor,
            expected_pre_s2_anchor_sha256=args.pre_s2_anchor_sha256,
            s1_wal_path=args.s1_wal, s1_checkpoint_path=args.s1_checkpoint,
            s2_wal_path=args.s2_wal, expected_s2_action_id=args.s2_action_id,
            expected_head=args.head, expected_world_uuid=args.world_uuid,
            expected_owner_id=args.owner_id, expected_self_id=args.self_id,
            expected_native_session_id=args.native_session_id,
            expected_checkpoint_generation=args.checkpoint_generation,
        )
    except (QS1BoundaryHold, OSError, ValueError, TypeError) as exc:
        print(json.dumps({"classification": "Q1B_HOLD", "reason": str(exc)}))
        return 2
    print(json.dumps(receipt, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
