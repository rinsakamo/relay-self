"""Q1g read-only, conservative physical MOVE_PLACE WAL shape readback.

Reference: src/relay_self/physical_action_journal.py at the I integration
branch, inspected HEAD 0e7a29565853dd8cf044bb81f5a19dace81dce64.

This Q verifier checks a deliberately bounded SAME SESSION, MOVE_PLACE-only
subset of the original persisted schema. It is not the original authoritative
PhysicalActionJournal._validate, authenticated WAL writer, Native/Paper source
audit, Original Owner, checkpoint restore or real World attestation.
"""
from __future__ import annotations

import hashlib
import json
import math
from pathlib import Path
from typing import Any

from experiments.q_lane_evidence_audit_dev import QEvidenceHold, _raw_file


class QMovePlaceWalHold(QEvidenceHold):
    """Original MOVE_PLACE WAL envelope or historical S1/S2 source unqualified."""


_BASE = {
    "session_id", "intent_id", "skill_execution_id", "action_id",
    "capability", "target_ref", "probe_seq", "probe_request_id",
    "source_ref", "status", "effect_seqs", "after_seq", "food_before",
    "food_after", "count_before", "count_after",
}
_MOVE = {
    "control", "started_position", "settled_position",
    "initial_stop_seq", "first_stable_seq", "initial_stop_tick",
    "first_stable_tick", "settled_tick", "displacement_m",
}
_PLACE = {
    "invocation_ref", "preset_ref", "target_contract_ref", "aim_yaw_rad",
    "target_position", "budget_actions", "budget_duration_ms",
    "budget_distance_m",
}
_GAIT = {"gait_mode", "gait_ack_seq"}
_STATUS = {
    "NATIVE_PLACE_MOVE_SETTLED", "NATIVE_PLACE_MOVE_NO_PROGRESS",
    "NATIVE_PLACE_MOVE_OVERSHOOT",
}
_MAX_ROWS = 64


def _strict(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    obj: dict[str, Any] = {}
    for key, value in pairs:
        if key in obj:
            raise QMovePlaceWalHold("duplicate original WAL JSON key")
        obj[key] = value
    return obj


def _canon(value: object) -> bytes:
    return json.dumps(
        value, sort_keys=True, separators=(",", ":"),
        ensure_ascii=False, allow_nan=False,
    ).encode("utf-8")


def _sha(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def _nonblank(value: object) -> bool:
    return type(value) is str and bool(value) and not any(c.isspace() for c in value)


def _number(value: object) -> bool:
    return type(value) in (float, int) and math.isfinite(value)


def _nat(value: object) -> bool:
    return type(value) is int and value >= 0


def _pos(value: object) -> tuple[float, float, float]:
    if (
        type(value) is not dict or set(value) != {"x", "y", "z"}
        or any(not _number(q) for q in value.values())
    ):
        raise QMovePlaceWalHold("original MOVE_PLACE 3D position invalid")
    return (float(value["x"]), float(value["y"]), float(value["z"]))


def _row(row: object, prev_seq: int, expected_session: str) -> int:
    if type(row) is not dict:
        raise QMovePlaceWalHold("original WAL Action row must be object")
    has_gait = bool(set(row) & _GAIT)
    if set(row) != _BASE | _MOVE | _PLACE | (_GAIT if has_gait else set()):
        raise QMovePlaceWalHold("original MOVE_PLACE exact row fields required")
    if any(not _nonblank(row[key]) for key in (
        "session_id", "intent_id", "skill_execution_id", "action_id",
        "capability", "target_ref", "probe_request_id", "source_ref",
    )):
        raise QMovePlaceWalHold("original Action scope/ID missing")
    if (
        row["session_id"] != expected_session or row["capability"] != "MOVE_PLACE"
        or not row["target_ref"].startswith("destination:")
        or row["control"] != "forward"
        or not row["invocation_ref"].startswith("skill-invocation:v1@")
        or not row["preset_ref"].startswith("skill-preset:v1@")
        or not row["target_contract_ref"].startswith("target-contract:v1@")
        or not _number(row["aim_yaw_rad"])
        or not -math.pi <= row["aim_yaw_rad"] <= math.pi
        or type(row["budget_actions"]) is not int
        or not 1 <= row["budget_actions"] <= 64
        or type(row["budget_duration_ms"]) is not int
        or not 1 <= row["budget_duration_ms"] <= 3_600_000
        or (
            row["budget_distance_m"] is not None
            and (not _number(row["budget_distance_m"])
                 or row["budget_distance_m"] <= 0)
        )
    ):
        raise QMovePlaceWalHold("S1/S2 PLACE original binding/preset/budget invalid")
    _pos(row["target_position"])
    start, end = _pos(row["started_position"]), _pos(row["settled_position"])
    probe, initial, first, final = (
        row["probe_seq"], row["initial_stop_seq"], row["first_stable_seq"],
        row["after_seq"],
    )
    ticks = (
        row["initial_stop_tick"], row["first_stable_tick"], row["settled_tick"],
    )
    if any(not _nat(x) for x in (probe, initial, first, final, *ticks)):
        raise QMovePlaceWalHold("original native sequence/tick invalid")
    if probe <= prev_seq or row["source_ref"] != f"{expected_session}:{probe}":
        raise QMovePlaceWalHold("native source not strictly monotonic")
    effects = row["effect_seqs"]
    if (
        type(effects) is not list or len(effects) != 3
        or any(not _nat(v) for v in effects)
    ):
        raise QMovePlaceWalHold("original PLACE needs look/start/stop ACK sequences")
    look, run, stop = effects
    if has_gait:
        if row["gait_mode"] not in ("WALK", "SNEAK"):
            raise QMovePlaceWalHold("unsupported original native gait")
        gait_seq = row["gait_ack_seq"]
        if row["gait_mode"] == "SNEAK":
            if not _nat(gait_seq) or not look < gait_seq < run:
                raise QMovePlaceWalHold("SNEAK ACK missing/out of order")
        elif gait_seq is not None:
            raise QMovePlaceWalHold("WALK cannot claim extra gait effect")
    else:
        gait_seq = None
    if (
        not probe < look < run < stop < initial < first < final
        or not 8 <= ticks[1] - ticks[0] <= 200
        or not 8 <= ticks[2] - ticks[1] <= 200
        or any(row[k] is not None for k in (
            "food_before", "food_after", "count_before", "count_after",
        ))
    ):
        raise QMovePlaceWalHold("S1/S2 PLACE STOP/settlement sequence invalid")
    delta = row["displacement_m"]
    if not _number(delta) or not 0 <= delta <= 8:
        raise QMovePlaceWalHold("original PLACE displacement invalid")
    if abs(math.dist(start, end) - delta) > 1e-6:
        raise QMovePlaceWalHold("PLACE displacement not equal to position readback")
    expected_status = (
        "NATIVE_PLACE_MOVE_NO_PROGRESS" if delta < 0.1
        else "NATIVE_PLACE_MOVE_OVERSHOOT"
        if row["budget_distance_m"] is not None
        and delta > row["budget_distance_m"] + 1e-6
        else "NATIVE_PLACE_MOVE_SETTLED"
    )
    if type(row["status"]) is not str or row["status"] not in _STATUS:
        raise QMovePlaceWalHold("original S1/S2 terminal status not supported")
    if row["status"] != expected_status:
        raise QMovePlaceWalHold("terminal status disagrees with physical displacement")
    return final


def _wal(raw: bytes, *, expected_self: str, session: str) -> tuple[dict, str]:
    try:
        envelope = json.loads(raw, object_pairs_hook=_strict)
        if type(envelope) is not dict or set(envelope) != {"body", "sha256"}:
            raise QMovePlaceWalHold("original physical WAL envelope missing")
        body = envelope["body"]
        if (
            type(body) is not dict or set(body) != {"schema", "self_id", "actions"}
            or type(body["schema"]) is not int or body["schema"] != 2
            or body["self_id"] != expected_self or type(body["actions"]) is not list
            or not 1 <= len(body["actions"]) <= _MAX_ROWS
        ):
            raise QMovePlaceWalHold("original body schema/self/action count invalid")
        # Original PhysicalActionJournal writes canonical JSON + one LF.
        if _canon(envelope) + b"\n" != raw:
            raise QMovePlaceWalHold("original WAL canonical bytes not preserved")
        digest = _sha(_canon(body))
        if envelope["sha256"] != digest:
            raise QMovePlaceWalHold("original WAL body SHA mismatch")
        ids: set[str] = set()
        prev = -1
        for entry in body["actions"]:
            prev = _row(entry, prev, session)
            if entry["action_id"] in ids:
                raise QMovePlaceWalHold("original Action ID replay in canonical history")
            ids.add(entry["action_id"])
        return body, digest
    except (UnicodeError, ValueError, TypeError, OverflowError) as exc:
        if isinstance(exc, QMovePlaceWalHold):
            raise
        raise QMovePlaceWalHold("original WAL is not strict canonical JSON") from exc


def audit_q1g_original_move_place_wal(
    evidence_dir: Path, *, s1_wal_file: str, s2_wal_file: str,
    expected_s1_wal_sha256: str, expected_self_id: str,
    expected_native_session_id: str, expected_s1_action_count: int,
    expected_last_s1_action_id: str, expected_s2_action_id: str,
) -> dict[str, object]:
    """Conservative same-Session canonical MOVE_PLACE S1->one S2 WAL audit.

    expected_s1_wal_sha256 is an externally provided independent raw-file
    digest, NOT derived from S2, the current original Owner, or Q itself.
    """
    if (
        not isinstance(evidence_dir, Path)
        or not evidence_dir.is_dir() or evidence_dir.is_symlink()
        or type(s1_wal_file) is not str or type(s2_wal_file) is not str
        or s1_wal_file == s2_wal_file
        or type(expected_s1_wal_sha256) is not str
        or len(expected_s1_wal_sha256) != 64
        or any(x not in "0123456789abcdef" for x in expected_s1_wal_sha256)
        or not all(_nonblank(x) for x in (
            expected_self_id, expected_native_session_id,
            expected_last_s1_action_id, expected_s2_action_id,
        ))
        or expected_last_s1_action_id == expected_s2_action_id
        or type(expected_s1_action_count) is not int
        or not 1 <= expected_s1_action_count < _MAX_ROWS
    ):
        raise QMovePlaceWalHold("exact original S1/S2 source scope missing")
    try:
        old_raw = _raw_file(evidence_dir, s1_wal_file)
        new_raw = _raw_file(evidence_dir, s2_wal_file)
    except QEvidenceHold as exc:
        raise QMovePlaceWalHold("original WAL file missing or untrusted") from exc
    if _sha(old_raw) != expected_s1_wal_sha256:
        raise QMovePlaceWalHold("S1 raw canonical WAL differs from external pin")
    old, old_digest = _wal(
        old_raw, expected_self=expected_self_id, session=expected_native_session_id,
    )
    after, new_digest = _wal(
        new_raw, expected_self=expected_self_id, session=expected_native_session_id,
    )
    first = old["actions"]
    later = after["actions"]
    if (
        len(first) != expected_s1_action_count
        or len(later) != len(first) + 1
        or later[:len(first)] != first
        or first[-1]["action_id"] != expected_last_s1_action_id
        or later[-1]["action_id"] != expected_s2_action_id
        or any(row["status"] != "NATIVE_PLACE_MOVE_SETTLED" for row in first)
        or later[-1]["skill_execution_id"] == first[-1]["skill_execution_id"]
        or later[-1]["intent_id"] == first[-1]["intent_id"]
        or after["schema"] != old["schema"]
        or old_digest == new_digest
    ):
        raise QMovePlaceWalHold("one new S2 does not preserve canonical S1 prefix")
    return {
        "classification": "Q1G_CANONICAL_MOVE_PLACE_WAL_SHAPE_CPU_OFFLINE_DEV",
        "original_wal_format": "physical-action-journal-v2-envelope",
        "self_id": expected_self_id,
        "native_session_id": expected_native_session_id,
        "s1_wal_raw_sha256": _sha(old_raw),
        "s2_wal_raw_sha256": _sha(new_raw),
        "s1_canonical_body_sha256": old_digest,
        "s2_canonical_body_sha256": new_digest,
        "s1_action_count": len(first),
        "s2_action_count": len(later),
        "s1_last_action_id": expected_last_s1_action_id,
        "s1_intent_id": first[-1]["intent_id"],
        "s1_skill_execution_id": first[-1]["skill_execution_id"],
        "s2_intent_id": later[-1]["intent_id"],
        "s2_skill_execution_id": later[-1]["skill_execution_id"],
        "s2_action_id": expected_s2_action_id,
        "s2_terminal_status_label": later[-1]["status"],
        "s2_outcome_original_native_paper_attested": False,
        "original_owner_attested": False,
        "independent_external_s1_origin_attested": False,
        "original_checkpoint_attested": False,
        "real_world_attested": False,
        "qual_go": False,
        "science_run": False,
    }
