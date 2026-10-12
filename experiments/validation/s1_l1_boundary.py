"""V-owned read-only S1 JSONL -> L1 admission boundary audit.

Checks decoded evidence consistency, NEVER fabricates ActionLifecycle, S16
interpretation, World revision, S-owned digest admission or World origin.
Runs on real pinned S1 emitter output using synthetic fixtures in CI.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import re
from pathlib import Path
from typing import Any

SCHEMA = "RELAYSELF_V1_S1_L1_BOUNDARY_V1"
S1_SCHEMA = "SELF1_BOUNDED_WORLD_EVENT_V1"
S1_SOURCE = "S49_OWNER_EXPLICIT_REAL_OR_SYNTHETIC"
NATIVE_SCHEMA = "SELF_NATIVE_ACTION_DECODED_FRAMES_V1"
_SHA = re.compile(r"[0-9a-f]{64}\Z")
KINDS = {
    "session_started", "world_decision", "action_requested_not_yet_issued",
    "action_not_dispatched", "action_outcome", "action_outcome_unknown",
    "session_terminal", "session_failed",
}


class BoundaryRejected(ValueError):
    """A forged, missing, or inconsistent source-shaped S1 frame."""


def require(ok: bool, why: str) -> None:
    if not ok:
        raise BoundaryRejected(why)


def number(x: object, *, minimum: float = 0) -> float:
    require(type(x) in (int, float) and math.isfinite(x) and x >= minimum,
            "finite nonnegative source number required")
    return float(x)


def nat(x: object) -> int:
    require(type(x) is int and x >= 0, "nonnegative integer required")
    return x


def text(x: object) -> str:
    require(isinstance(x, str) and bool(x), "nonempty source token required")
    return x


def verify_decoded(row: dict[str, Any], session: str, action_id: str) -> str:
    """V-owned native evidence cross-check; no real World attestation."""
    source = row.get("native_execution_evidence")
    require(isinstance(source, dict), "original decoded receipt missing")
    serialized = json.dumps(
        source, sort_keys=True, separators=(",", ":"), ensure_ascii=False,
        allow_nan=False,
    ).encode("utf-8")
    digest = hashlib.sha256(serialized).hexdigest()
    require(_SHA.fullmatch(str(row.get("native_execution_sha256", ""))) is not None
            and row["native_execution_sha256"] == digest,
            "original native receipt hash mismatch")
    require(source.get("schema") == NATIVE_SCHEMA
            and source.get("action_id") == action_id
            and source.get("session_id") == session
            and source.get("status") == "executed"
            and source.get("action_ref") == "MOVE_BACKWARD"
            and text(source.get("binding_id"))
            and source.get("cleanup_attempted") is True
            and source.get("goal_success_attested") is False
            and source.get("learning_feedback_qualified") is False,
            "decoded native evidence provenance or permission mismatch")
    frames = [
        source.get(k) for k in (
            "before_observation", "dispatch_receipt",
            "cleanup_receipt", "after_observation",
        )
    ]
    require(all(isinstance(f, dict) and f.get("session_id") == session
                and type(f.get("seq")) is int and f["seq"] >= 0
                and f.get("provenance") == {
                    "source": "mineflayer", "reference": f"{session}:{f['seq']}"
                } for f in frames), "native original frame provenance mismatch")
    seq = [f["seq"] for f in frames]
    require(seq == sorted(set(seq))
            and row.get("before_seq") == seq[0]
            and row.get("after_seq") == seq[3],
            "native dispatch/cleanup order or projection mismatch")
    require(
        frames[1].get("action_id") == action_id
        and frames[1].get("effect") == "set_control"
        and frames[1].get("result") == "applied"
        and frames[1].get("error") is None
        and frames[2].get("action_id") == f"{action_id}-s15-clear"
        and frames[2].get("effect") == "clear_controls"
        and frames[2].get("result") == "applied"
        and frames[2].get("error") is None,
        "original dispatch/cleanup missing")
    for f in (frames[0], frames[3]):
        require(f.get("kind") in ("entities", "probe")
                and isinstance(f.get("snapshot"), dict)
                and isinstance(f["snapshot"].get("position"), dict)
                and isinstance(f["snapshot"].get("nearby_entities"), list)
                and isinstance(f["snapshot"].get("nearby_entities_coverage"), dict),
                "original native observation incomplete")
    before = frames[0]["snapshot"]["position"]
    after = frames[3]["snapshot"]["position"]
    require(set(before) == set(after) == {"x", "y", "z"},
            "original coordinates incomplete")
    movement = math.hypot(
        number(after["x"], minimum=-math.inf) - number(before["x"], minimum=-math.inf),
        number(after["z"], minimum=-math.inf) - number(before["z"], minimum=-math.inf),
    )
    require(
        movement >= .05 and
        math.isclose(movement, number(source.get("movement_m")), abs_tol=1e-9)
        and math.isclose(movement, number(row.get("movement_m")), abs_tol=1e-9),
        "native movement not independently reproducible")
    require(
        row.get("original_action_state") == "outcome"
        and row.get("original_world_status") == "executed"
        and row.get("physical_outcome") == "outcome"
        and row.get("original_source_session") == session
        and row.get("goal_success_attested") is False
        and row.get("learning_feedback_qualified") is False
        and row.get("habit_granted") is False
        and text(row.get("source_provenance")),
        "S1 positive outcome projection illegally promoted")
    return digest


def audit_rows(rows: list[dict[str, Any]]) -> dict[str, Any]:
    require(isinstance(rows, list) and len(rows) >= 2, "missing bounded S1 stream")
    session = text(rows[0].get("session"))
    require(rows[0].get("kind") == "session_started", "S1 start missing")
    require(rows[-1].get("kind") in ("session_terminal", "session_failed"),
            "S1 terminal missing")
    decisions: dict[str, dict[str, Any]] = {}
    requests: dict[str, dict[str, Any]] = {}
    closures: set[str] = set()
    unknowns: set[str] = set()
    last_epoch = 0
    for i, row in enumerate(rows):
        require(isinstance(row, dict)
                and row.get("schema") == S1_SCHEMA
                and row.get("source") == S1_SOURCE
                and row.get("session") == session
                and type(row.get("index")) is int and row["index"] == i
                and row.get("kind") in KINDS,
                "S1 index/session/origin/kind drift")
        kind = row["kind"]
        if kind in ("session_started", "session_terminal", "session_failed"):
            require(i in (0, len(rows) - 1),
                    "duplicate or midstream session delimiter")
        if kind == "world_decision":
            epoch = nat(row.get("epoch"))
            require(epoch == last_epoch + 1, "nonsequential S1 cognition epoch")
            last_epoch = epoch
            require(row.get("layer") == "L0"
                    and row.get("source_type") == "MINEFLAYER_NATIVE"
                    and row.get("selection") in ("WAIT", "MOVE_AWAY")
                    and nat(row.get("event_seq")) < nat(row.get("probe_seq"))
                    and text(row.get("event_source"))
                    and text(row.get("probe_source"))
                    and text(row.get("probe_request_id"))
                    and row.get("goal_success_attested") is False,
                    "untrustworthy S1 cognition/probe lineage")
            # Important: retained_revision is learning state, NOT a World revision.
            nat(row.get("retained_revision"))
            rid = row.get("action_request_id")
            if row["selection"] == "MOVE_AWAY":
                require(isinstance(rid, str) and rid and rid not in decisions,
                        "missing/duplicate Action request id")
                decisions[rid] = row
            else:
                require(rid is None, "WAIT must not request an Action")
        if kind == "action_requested_not_yet_issued":
            aid = text(row.get("action_id"))
            require(aid in decisions and aid not in requests
                    and row.get("epoch") == decisions[aid]["epoch"]
                    and row.get("event_seq") == decisions[aid]["event_seq"]
                    and row.get("probe_seq") == decisions[aid]["probe_seq"]
                    and text(row.get("authority_id")),
                    "Action request without independent selected source")
            requests[aid] = row
        if kind == "action_outcome":
            aid = text(row.get("action_id"))
            require(aid in requests and aid not in closures and aid not in unknowns
                    and row.get("epoch") == requests[aid]["epoch"],
                    "Action outcome without unique S1 request")
            verify_decoded(row, session, aid)
            closures.add(aid)
        if kind in ("action_outcome_unknown", "action_not_dispatched"):
            aid = text(row.get("action_id"))
            require(aid in requests and aid not in closures and aid not in unknowns
                    and row.get("safe_to_replay") is False
                    and row.get("physical_outcome") in ("UNKNOWN", "NOT_ISSUED"),
                    "unlinked / replayable uncertain Action")
            unknowns.add(aid)
        if kind == "session_failed":
            require(row.get("no_replay") is True
                    and row.get("physical_outcome") == "UNKNOWN_IF_IN_FLIGHT",
                    "failed session must fail closed")
    require(set(requests) == closures | unknowns, "unclosed S1 Action request")
    terminal = rows[-1]
    if terminal["kind"] == "session_terminal":
        require(nat(terminal.get("events")) == last_epoch
                and nat(terminal.get("action_requests")) == len(requests)
                and nat(terminal.get("closed_outcomes")) == len(closures)
                and terminal.get("learning_updates") == 0
                and terminal.get("habit_grants") == 0
                and terminal.get("l2_attempts") == 0
                and terminal.get("model_stop_ack") is False,
                "S1 terminal counts or learning claim changed")
    else:
        require(nat(terminal.get("action_requests")) == len(requests)
                and nat(terminal.get("closed_outcomes")) == len(closures)
                and terminal.get("learning_updates") == 0
                and terminal.get("habit_grants") == 0,
                "failed S1 terminal claim drift")
    # A source log never embeds a current typed S16 ActionLifecycle, admissible
    # World revision, verified World origin or S-owned original digest consent.
    # There is NO conversion, no success witness, and no implicit L1 recall.
    status = (
        "S1_FAILURE_NO_L1_PROMOTION" if terminal["kind"] == "session_failed"
        else "S1_UNCERTAIN_ACTION_NO_L1_PROMOTION" if unknowns
        else "S1_LOG_CONSISTENT_NO_L1_ADMISSION"
    )
    return {
        "schema": SCHEMA, "terminal": status,
        "source_kind": "S1_REAL_OR_SYNTHETIC_UNDETERMINED_FROM_LOG",
        "source_session": session, "decisions": last_epoch,
        "action_requests": len(requests), "closed_outcomes": len(closures),
        "uncertain_actions": len(unknowns),
        "L1_admission": "NOT_AUTHORIZED_FROM_LOG",
        "missing_from_log": [
            "S_OWNER_VERIFIED_PHYSICAL_ORIGIN",
            "CURRENT_S16_ACTION_LIFECYCLE",
            "MATCHED_S16_ACTION_OUTCOME_INTERPRETATION",
            "WORLD_SOURCE_REVISION_NOT_RETAINED_REVISION",
            "S_OWNER_ADMITTED_SOURCE_DIGEST",
        ],
        "goal_success": "NOT_ATTESTED", "S10_learning": "NOT_RUN",
        "S11_habit": "NOT_RUN", "science_go": False,
    }


def audit_file(path: Path) -> dict[str, Any]:
    require(path.is_absolute() and path.is_file() and not path.is_symlink()
            and path.stat().st_size <= 8_000_000,
            "bounded existing nonsymlink S1 log required")
    raw = path.read_bytes()
    require(raw.endswith(b"\n") and raw and b"\x00" not in raw,
            "truncated/empty/unsafe S1 JSONL")
    parsed = [json.loads(line) for line in raw.splitlines()]
    return audit_rows(parsed)


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--stream", type=Path, required=True)
    a = p.parse_args(argv)
    try:
        result = audit_file(a.stream)
    except (BoundaryRejected, ValueError, TypeError, OSError, OverflowError) as exc:
        print(json.dumps({
            "schema": SCHEMA, "terminal": "S1_LOG_REJECTED",
            "error": str(exc), "L1_admission": "NOT_AUTHORIZED_FROM_LOG",
            "science_go": False,
        }, sort_keys=True))
        return 2
    print(json.dumps(result, sort_keys=True, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
