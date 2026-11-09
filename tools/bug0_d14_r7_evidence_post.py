"""R7 source-only forensics for an original S49 natural-World MOVE.

Never reissue, resolve a PREPARED_UNRESOLVED entry, infer dispatch from a
prepared fence, or classify S50 client quietness as Paper-effective STOP.
W3 is received Node stdout JSONL, NOT raw Minecraft TCP traffic.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

from adapters.mineflayer.self_world_stage_w3_capture import (
    W3CaptureRejected,
    audit_w3_sealed_stdout,
)
from relay_self.c1_physical_action_fence import OriginalS49PhysicalFence

W3_LIMIT = 32 * 1024 * 1024
S50_LIMIT = 16 * 1024 * 1024


class R7ForensicsRejected(ValueError):
    """A source cannot safely be used even for unqualified diagnostics."""


def _jsonl(path: Path, *, max_bytes: int) -> list[dict[str, Any]]:
    if path.is_symlink() or not path.is_file() or path.stat().st_size > max_bytes:
        raise R7ForensicsRejected("missing, symlinked or oversized forensic file")
    blob = path.read_bytes()
    if not blob or not blob.endswith(b"\n"):
        raise R7ForensicsRejected("missing final complete source record")
    rows = []
    for raw in blob.splitlines(keepends=True):
        if not raw.endswith(b"\n") or len(raw) > 1024 * 1024:
            raise R7ForensicsRejected("truncated or oversized native source frame")
        try:
            row = json.loads(raw)
        except (ValueError, UnicodeError) as exc:
            raise R7ForensicsRejected("invalid original native JSONL") from exc
        if not isinstance(row, dict):
            raise R7ForensicsRejected("native source record must be mapping")
        rows.append(row)
    return rows


def _w3(evidence: Path) -> tuple[list[dict[str, Any]], str]:
    raw = evidence / "w3-node-stdout.raw.jsonl"
    receipt = evidence / "w3-node-stdout-receipt.json"
    if not raw.exists() and not receipt.exists():
        return [], "NOT_CAPTURED"
    if raw.is_symlink() or receipt.is_symlink() or not raw.is_file() or not receipt.is_file():
        return [], "INCOMPLETE_CAPTURE"
    try:
        rows = _jsonl(raw, max_bytes=W3_LIMIT)
        rec = json.loads(receipt.read_bytes())
        actual_sha = hashlib.sha256(raw.read_bytes()).hexdigest()
    except (OSError, ValueError, UnicodeError, R7ForensicsRejected):
        return [], "CORRUPT_OR_INCOMPLETE_CAPTURE"
    if (
        not isinstance(rec, dict)
        or rec.get("scope") != "NODE_BRIDGE_STDOUT_JSONL_BYTES_NOT_MINECRAFT_TCP"
        or rec.get("stdout_sha256") != actual_sha
        or rec.get("byte_count") != raw.stat().st_size
        or rec.get("frame_count") != len(rows)
        or rec.get("first_seq") != 0
        or rec.get("last_seq") != len(rows) - 1
        or any(type(row.get("seq")) is not int or row["seq"] != i
               for i, row in enumerate(rows))
        or any(row.get("session_id") != rec.get("session_id") for row in rows)
    ):
        return [], "RECEIPT_OR_SEQUENCE_MISMATCH"
    if rec.get("status") == "COMPLETE_NODE_STDOUT":
        try:
            audit_w3_sealed_stdout(evidence)
        except (W3CaptureRejected, ValueError):
            return [], "INVALID_COMPLETE_NODE_STDOUT_SEAL"
        return rows, "COMPLETE_SAME_PROCESS_NODE_STDOUT_ONLY"
    return rows, "INCOMPLETE_SAME_PROCESS_NODE_STDOUT_ONLY"


def _s50(evidence: Path) -> tuple[list[dict[str, Any]], str]:
    path = evidence / "r7-s50-client-readback.jsonl"
    if not path.exists():
        return [], "NOT_CAPTURED"
    try:
        rows = _jsonl(path, max_bytes=S50_LIMIT)
    except (OSError, R7ForensicsRejected):
        return [], "CORRUPT_OR_INCOMPLETE_CAPTURE"
    if (
        not rows or rows[0].get("kind") != "SESSION_START"
        or not isinstance(rows[0].get("session_id"), str)
        or not rows[0]["session_id"]
        or any(
            row.get("source") != "S50_DEV_NATIVE_READBACK_V1"
            or type(row.get("ordinal")) is not int or row["ordinal"] != i
            or row.get("session_id") != rows[0].get("session_id")
            or type(row.get("client_physics_tick")) is not int
            for i, row in enumerate(rows, 1)
        )
        or any(
            rows[i]["client_physics_tick"] < rows[i - 1]["client_physics_tick"]
            for i in range(1, len(rows))
        )
        or any(row.get("kind") in ("TRUNCATED", "READBACK_ERROR", "READBACK_UNAVAILABLE",
                                     "NATIVE_FRAME_PARSE_ERROR")
               for row in rows)
    ):
        return [], "UNQUALIFIED_CLIENT_SOURCE"
    return rows, "SAME_CLIENT_READBACK_ONLY"


def _client_tail(rows: list[dict[str, Any]], clear_id: str) -> dict[str, Any]:
    ack_indices = [
        i for i, row in enumerate(rows)
        if row.get("kind") == "EFFECT_ACK"
        and row.get("native_action_id") == clear_id
    ]
    if len(ack_indices) != 1:
        return {"clear_ack_seen": False, "postclear_quiet_physics_ticks": 0}
    idx = ack_indices[0]
    quiet = 0
    controls = ("forward", "back", "left", "right", "jump", "sprint", "sneak")
    for row in rows[idx:]:
        states = row.get("controls")
        if (
            not isinstance(states, dict) or set(states) != set(controls)
            or any(type(states[c]) is not bool for c in controls)
            or any(states.values())
        ):
            break
        if row["kind"] == "PHYSICS_TICK" and row is not rows[idx]:
            quiet += 1
    return {"clear_ack_seen": True, "postclear_quiet_physics_ticks": quiet}


def inspect_r7_source_only(evidence: Path) -> dict[str, Any]:
    """Read already-created originals only. This does not mutate Action state."""
    if not evidence.is_dir() or evidence.is_symlink():
        raise R7ForensicsRejected("existing non-symlink evidence directory required")
    fence = OriginalS49PhysicalFence.restore(
        evidence / "original_s49_motion_fence.json", self_id="s49-original-self",
    )
    w3, w3_scope = _w3(evidence)
    s50, s50_scope = _s50(evidence)
    # A source with a different client session can never attach to this
    # original S49 persistent owner, even for a diagnostic readout.
    sessions = {row["session_id"] for row in fence.actions}
    if w3 and ({row["session_id"] for row in w3} != sessions):
        w3, w3_scope = [], "FOREIGN_ORIGINAL_S49_SESSION"
    if s50 and ({row["session_id"] for row in s50} != sessions):
        s50, s50_scope = [], "FOREIGN_ORIGINAL_S49_SESSION"
    actions = []
    for row in fence.actions:
        action_id = row["action_id"]
        ack_ids = (action_id, action_id + "-s15-clear")
        native_acks = [
            {
                "action_id": e["action_id"],
                "effect": e.get("effect"),
                "result": e.get("result"),
                "seq": e["seq"],
            }
            for e in w3 if e.get("type") == "effect_result"
            and e.get("action_id") in ack_ids
        ]
        tail = (
            _client_tail(s50, action_id + "-s15-clear") if s50
            else {"clear_ack_seen": False, "postclear_quiet_physics_ticks": 0}
        )
        stdout_clear = [
            ack["seq"] for ack in native_acks
            if ack["action_id"] == action_id + "-s15-clear"
        ]
        client_clear = [
            item["native_seq"] for item in s50
            if item.get("kind") == "EFFECT_ACK"
            and item.get("native_action_id") == action_id + "-s15-clear"
        ]
        actions.append({
            "action_id": action_id,
            "fence_status": row["status"],
            "native_decision_seq": row["decision_seq"],
            "original_s16_terminal": row["terminal_state"],
            "fence_is_unresolved": row["status"] == "PREPARED_UNRESOLVED",
            "node_stdout_effect_results": native_acks,
            "s50_same_client_clear_ack_seen": tail["clear_ack_seen"],
            "s50_postclear_quiet_client_ticks": tail["postclear_quiet_physics_ticks"],
            "stdout_s50_clear_seq_match": (
                len(stdout_clear) == len(client_clear) == 1
                and stdout_clear[0] == client_clear[0]
            ),
            "physical_dispatch_attested": False,
            "paper_effective_stop_attested": False,
            "physical_result_of_unresolved_action": (
                "UNKNOWN" if row["status"] == "PREPARED_UNRESOLVED"
                else "S16_OUTCOME_SOURCE_ONLY"
            ),
            "reissue_authorized": False,
        })
    return {
        "status": "PARTIAL_SOURCE_ONLY_NOT_QUALIFIED",
        "source_scope": "ORIGINAL_S49_FENCE_PLUS_NODE_STDOUT_AND_S50_CLIENT",
        "original_motion_fence_sha256": fence.sha256,
        "original_motion_fence_unresolved": fence.unresolved,
        "w3_received_node_stdout_scope": w3_scope,
        "s50_same_client_scope": s50_scope,
        "actions": actions,
        "minecraft_tcp_attested": False,
        "paper_tick_aligned_stop_attested": False,
        "self_disconnect_causal_order_proven": False,
        "learning_authorized": False,
        "world_replay_authorized": False,
        "qualification": "NO_GO",
        "science": "NOT_RUN",
    }


def main() -> None:
    """Inspect existing evidence without writing into the original directory."""
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("--evidence-dir", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    if args.out.exists() or args.out.is_symlink():
        raise R7ForensicsRejected("forensic output must be new and immutable")
    result = inspect_r7_source_only(args.evidence_dir)
    with args.out.open("x", encoding="utf8") as stream:
        json.dump(result, stream, sort_keys=True, indent=2)
        stream.write("\n")
    print(result["status"], result["original_motion_fence_unresolved"])


if __name__ == "__main__":
    main()
