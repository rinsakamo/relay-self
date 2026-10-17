"""S50 #627: bounded, read-only review of FLAT DEV native packet projections.

A captured packet event is a client-local trace, not independently signed
wire evidence, Paper-effective orientation, or proof that corrections ended.
This module NEVER authorizes SETUP handoff, motor or P1 WAIT by itself.
"""
from __future__ import annotations

import json
import math

from adapters.mineflayer.m02_paper_dev.s50_boundary import BoundaryRejected

SOURCE = "S50_DEV_PASSIVE_PACKET_V1"
MAX_ROWS = 16384
MAX_BYTES = 8_000_000
INBOUND = {"position", "player_rotation"}
OUTBOUND = {"look", "position_look", "teleport_confirm"}
EVENTS = {
    "SESSION_START", "CLIENT_PHYSICS_TICK", "PACKET_IN_BEFORE",
    "PACKET_IN_AFTER", "PACKET_OUT", "NATIVE_EFFECT_ACK", "SHUTDOWN_ACK",
}


def _unique(pairs):
    row = {}
    for name, value in pairs:
        if name in row:
            raise BoundaryRejected("duplicate passive packet original field")
        row[name] = value
    return row


def _pose(row):
    for name in ("client_yaw_radians", "client_pitch_radians"):
        value = row.get(name)
        if value is not None and (type(value) not in (float, int)
                                  or not math.isfinite(value)):
            raise BoundaryRejected("invalid client pose original")
    return (row.get("client_yaw_radians"), row.get("client_pitch_radians"))


def _fields(row):
    fields = row.get("packet_fields")
    if not isinstance(fields, dict) or fields.get("shape_valid") is not True:
        raise BoundaryRejected("truncated/nonfinite passive packet fields")
    if any(isinstance(v, (dict, list)) and k != "flags" for k, v in fields.items()):
        raise BoundaryRejected("untrusted packet projection shape")
    for key, value in fields.items():
        if key == "flags":
            if type(value) is int and value >= 0:
                continue
            if not isinstance(value, dict) or any(
                name not in {"x", "y", "z", "yaw", "pitch"}
                or type(flag) is not bool for name, flag in value.items()
            ):
                raise BoundaryRejected("invalid rotation flags")
        elif key == "shape_valid":
            if value is not True:
                raise BoundaryRejected("missing valid packet shape")
        elif type(value) not in (float, int, bool) or (
            type(value) in (float, int) and not math.isfinite(value)
        ):
            raise BoundaryRejected("invalid packet scalar")
    return fields


def review_s50_packet_trace(original: str) -> dict:
    """No effective-server clock, no causal sender attribution, no live grant."""
    if not isinstance(original, str) or not 0 < len(original.encode("utf-8")) <= MAX_BYTES:
        raise BoundaryRejected("missing or unbounded passive packet originals")
    try:
        rows = [json.loads(line, object_pairs_hook=_unique)
                for line in original.splitlines()]
    except (ValueError, TypeError) as exc:
        raise BoundaryRejected("invalid passive packet JSONL") from exc
    if not 2 <= len(rows) <= MAX_ROWS:
        raise BoundaryRejected("missing or truncated packet trace")
    session = rows[0].get("session_id")
    if (not isinstance(session, str) or not session
            or rows[0].get("kind") != "SESSION_START"
            or rows[0].get("native_seq") != 0):
        raise BoundaryRejected("packet source session start absent")
    physics_tick = 0
    pending = None
    counts = {name: 0 for name in EVENTS}
    corrections = []
    first_stop = None
    native_acks = []
    for i, row in enumerate(rows, 1):
        if (not isinstance(row, dict) or row.get("source") != SOURCE
                or row.get("session_id") != session
                or type(row.get("ordinal")) is not int or row["ordinal"] != i
                or type(row.get("client_physics_tick")) is not int
                or row["client_physics_tick"] != physics_tick
                or row.get("kind") not in EVENTS):
            # physicsTick advances only at the callback line, below.
            if (not isinstance(row, dict) or row.get("kind") != "CLIENT_PHYSICS_TICK"
                    or row.get("source") != SOURCE
                    or row.get("session_id") != session
                    or type(row.get("ordinal")) is not int or row["ordinal"] != i
                    or type(row.get("client_physics_tick")) is not int
                    or row["client_physics_tick"] != physics_tick + 1):
                raise BoundaryRejected("foreign/nonconsecutive native packet order")
        kind = row["kind"]
        if i > 1 and kind == "SESSION_START":
            raise BoundaryRejected("duplicate packet trace session start")
        if first_stop is not None and kind != "SHUTDOWN_ACK":
            # Connection shutdown may continue producing source callbacks;
            # do not silently promote that interval to verified inactivity.
            raise BoundaryRejected("post-shutdown packet activity")
        if pending is not None and kind not in {"PACKET_IN_AFTER", "PACKET_OUT"}:
            raise BoundaryRejected("unterminated clientbound packet callback")
        counts[kind] += 1
        _pose(row)
        if kind == "CLIENT_PHYSICS_TICK":
            physics_tick += 1
        elif kind in {"PACKET_IN_BEFORE", "PACKET_IN_AFTER", "PACKET_OUT"}:
            name = row.get("packet_name")
            if name not in (OUTBOUND if kind == "PACKET_OUT" else INBOUND):
                raise BoundaryRejected("wrong/injected packet name")
            fields = _fields(row)
            if kind == "PACKET_IN_BEFORE":
                if pending is not None:
                    raise BoundaryRejected("nested inbound packet callbacks")
                pending = (name, fields, i, _pose(row))
            elif kind == "PACKET_IN_AFTER":
                if pending is None or pending[0] != name or pending[1] != fields:
                    raise BoundaryRejected("lost/reordered inbound correction witness")
                corrections.append({
                    "packet_name": name,
                    "before_ordinal": pending[2],
                    "after_ordinal": i,
                    "before_client_pose": pending[3],
                    "after_client_pose": _pose(row),
                    "teleport_id": fields.get("teleportId", fields.get("teleport_id")),
                })
                pending = None
        elif kind == "NATIVE_EFFECT_ACK":
            if (type(row.get("native_seq")) is not int
                    or row["native_seq"] < 1
                    or not isinstance(row.get("native_action_id"), str)
                    or not row["native_action_id"]
                    or row.get("effect") not in {
                        "look", "set_control", "clear_controls", "equip_item",
                        "consume_held", "attack_entity",
                    }
                    or row.get("result") not in {"applied", "rejected"}):
                raise BoundaryRejected("unbound native effect ACK projection")
            native_acks.append({
                "native_seq": row["native_seq"], "action_id": row["native_action_id"],
                "effect": row["effect"], "result": row["result"], "ordinal": i,
            })
        elif kind == "SHUTDOWN_ACK":
            if first_stop is not None or type(row.get("native_seq")) is not int:
                raise BoundaryRejected("duplicate/invalid packet shutdown witness")
            first_stop = i
    if pending is not None:
        raise BoundaryRejected("incomplete original inbound packet pair")
    if len({row["native_seq"] for row in native_acks}) != len(native_acks):
        raise BoundaryRejected("duplicate native-effect-ACK in packet trace")
    return {
        "classification": "S50_PASSIVE_PACKET_SOURCE_SHAPE_DEV_ONLY",
        "session_id": session, "rows": len(rows),
        "packet_inbound_callbacks": counts["PACKET_IN_BEFORE"],
        "packet_outbound_writes_observed": counts["PACKET_OUT"],
        "client_physics_callbacks": counts["CLIENT_PHYSICS_TICK"],
        "native_effect_acks": native_acks,
        "correction_callbacks": corrections,
        "shutdown_ack_seen": first_stop is not None,
        "source_bytes_authenticated": False,
        "source_packet_delivery_to_server": "NOT_ATTESTED",
        "setup_teleport_settled": False,
        "pending_server_corrections_excluded": False,
        "runtime_owner_handoff_admitted": False,
        "self_feedback_delivered": False,
        "P1_SourceBoundTick_WAIT": 0,
        "science_go": False,
    }


def reconcile_packet_native_original(
    packet_original: str, native_frames: list[dict],
) -> dict:
    """Check packet-sidecar ACK identity against separate original Node stdout.

    Same-session source shape only; not a signed or R-qualified original.
    """
    result = review_s50_packet_trace(packet_original)
    if not isinstance(native_frames, list) or not 2 <= len(native_frames) <= 8192:
        raise BoundaryRejected("missing/unbounded native bridge originals")
    session = result["session_id"]
    seen = set()
    expected_acks = []
    shutdown = []
    for i, frame in enumerate(native_frames):
        if (not isinstance(frame, dict)
                or frame.get("session_id") != session
                or type(frame.get("seq")) is not int or frame["seq"] != i):
            raise BoundaryRejected("native packet/source foreign session or seq")
        if frame.get("type") == "effect_result":
            if (not isinstance(frame.get("action_id"), str)
                    or not frame["action_id"]
                    or frame.get("result") not in {"applied", "rejected"}):
                raise BoundaryRejected("invalid original effect")
            expected_acks.append({
                "native_seq": i, "action_id": frame["action_id"],
                "effect": frame.get("effect"), "result": frame["result"],
            })
        elif frame.get("type") == "shutdown_ack":
            shutdown.append(i)
        seen.add(i)
    observed_acks = result["native_effect_acks"]
    if (len(observed_acks) != len(expected_acks)
            or [
                {k: ack[k] for k in ("native_seq", "action_id", "effect", "result")}
                for ack in observed_acks
            ] != expected_acks):
        raise BoundaryRejected("native effect receipts missing/altered in packet trace")
    if len(shutdown) != int(result["shutdown_ack_seen"]):
        raise BoundaryRejected("native shutdown ACK mismatch")
    if shutdown:
        try:
            source_rows = [
                json.loads(line, object_pairs_hook=_unique)
                for line in packet_original.splitlines()
            ]
        except (ValueError, TypeError) as exc:
            raise BoundaryRejected("changed packet originals on repeated read") from exc
        if not any(
            row.get("kind") == "SHUTDOWN_ACK"
            and row.get("native_seq") == shutdown[0]
            for row in source_rows
        ):
            raise BoundaryRejected("foreign/missing native shutdown source")
    return {
        **result,
        "native_effect_and_shutdown_projection_reconciled": True,
        "independent_original_authenticity": False,
        "paper_effective_yaw_attested": False,
        "self_feedback_delivered": False,
    }
