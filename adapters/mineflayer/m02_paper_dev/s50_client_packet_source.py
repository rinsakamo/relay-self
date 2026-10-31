"""S50 DEV independent readback of native client.write observations and Paper input.

A write-return is not wire delivery, server acceptance, or a shared clock.
Only the existing Mineflayer process writes the optional JSONL sidecar.
"""
from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass

MAX_CLIENT_BYTES = 4_000_000
MAX_PAPER_BYTES = 16_000_000
PACKETS = frozenset({
    "player_input", "position", "position_look", "look", "flying",
    "entity_action",
})
KINDS = frozenset({
    "PHYSICS_EVENT_SAMPLE", "PACKET_WRITE_RETURNED",
    "NATIVE_CONTROL_EFFECT_RETURNED",
})


class S50PacketSourceRejected(ValueError):
    """Incomplete/foreign/ambiguous DEV source; never infer packet delivery."""


@dataclass(frozen=True)
class S50InputPacketReview:
    native_session_id: str
    marker_id: str
    paper_world_uuid: str
    client_packet_write_returns: int
    client_player_input_write_returns: int
    client_motion_write_returns: int
    native_control_effect_samples: int
    paper_player_input_callbacks: int
    client_trace_complete: bool
    diagnostic: str
    native_write_is_network_delivery: bool = False
    paper_packet_identity_proven: bool = False
    effective_s15_clear_tick: str = "NOT_ATTESTED"
    full_tick_input_coverage: bool = False
    p1_wait_ticks_admitted: int = 0
    l10_pairs_admitted: int = 0


def inspect_s50_client_packets(
    original: bytes, paper_log: bytes, *, session_id: str,
    marker_id: str, world: str,
) -> dict[str, object]:
    if (
        not isinstance(original, bytes) or not 0 < len(original) <= MAX_CLIENT_BYTES
        or not isinstance(paper_log, bytes)
        or not 0 < len(paper_log) <= MAX_PAPER_BYTES
        or not all(isinstance(v, str) and 0 < len(v) <= 128
                   for v in (session_id, marker_id, world))
        or not marker_id.endswith(session_id)
    ):
        raise S50PacketSourceRejected("invalid client/Paper DEV originals or identity")
    try:
        packets = [json.loads(line) for line in original.decode("utf-8").splitlines()]
        paper = paper_log.decode("utf-8")
    except (ValueError, UnicodeError) as exc:
        raise S50PacketSourceRejected("malformed native/Paper original") from exc
    if len(packets) < 2 or any(not isinstance(row, dict) for row in packets):
        raise S50PacketSourceRejected("missing client rows or footer")
    footer = packets[-1]
    if (
        footer.get("kind") != "TRACE_END"
        or footer.get("revision") != 1 or footer.get("complete") is not True
        or footer.get("lost") is not False
        or footer.get("recorded_rows") != len(packets) - 1
        or footer.get("input_write_authority") is not False
        or footer.get("server_packet_received") is not False
        or footer.get("effective_s15_clear_tick") != "NOT_ATTESTED"
    ):
        raise S50PacketSourceRejected("incomplete client capture")
    writes = 0
    player_input = 0
    motion = 0
    effects = 0
    previous_node = -1
    for index, row in enumerate(packets[:-1], 1):
        try:
            node_ns = int(row["node_ns"])
        except (ValueError, TypeError, KeyError) as exc:
            raise S50PacketSourceRejected("missing monotonic Node clock") from exc
        if (
            row.get("revision") != 1 or row.get("index") != index
            or row.get("session_id") != session_id
            or row.get("kind") not in KINDS
            or row.get("clock_scope") != "NODE_ONLY"
            or row.get("server_world_tick") != "NOT_OBSERVED"
            or row.get("source") != "CLIENT_WRITE_RETURNED_NOT_NETWORK_DELIVERY"
            or node_ns < previous_node
        ):
            raise S50PacketSourceRejected("client source identity/order/clock mismatch")
        previous_node = node_ns
        if row["kind"] == "PACKET_WRITE_RETURNED":
            if (
                row.get("packet_name") not in PACKETS
                or row.get("paper_received") is not False
                or row.get("network_delivered") is not False
                or type(row.get("packet_index")) is not int
                or row["packet_index"] != writes + 1
            ):
                raise S50PacketSourceRejected("client packet origin not supported")
            writes += 1
            if row["packet_name"] == "player_input":
                player_input += 1
            if row["packet_name"] in {"position", "position_look", "flying", "look"}:
                motion += 1
        elif row["kind"] == "NATIVE_CONTROL_EFFECT_RETURNED":
            effects += 1
    expected_prefix = f"S50_DEV_INPUT_EVENT marker_id={marker_id} "
    ticks_prefix = f"S50_DEV_INPUT_TICK marker_id={marker_id} "
    callbacks = 0
    tick_count = 0
    for line in paper.splitlines():
        if "S50_DEV_INPUT_EVENT marker_id=" in line:
            if expected_prefix not in line:
                raise S50PacketSourceRejected("foreign Paper INPUT_EVENT")
            if f" world={world} " not in line:
                raise S50PacketSourceRejected("wrong Paper event World")
            callbacks += 1
        if "S50_DEV_INPUT_TICK marker_id=" in line:
            if ticks_prefix not in line or f" world={world} " not in line:
                raise S50PacketSourceRejected("foreign Paper INPUT_TICK")
            tick_count += 1
    if tick_count != 8:
        raise S50PacketSourceRejected("not eight Paper input tick samples")
    if player_input == 0:
        diagnostic = "NO_PLAYER_INPUT_WRITE_ON_OBSERVED_CLIENT_PATH"
    elif callbacks == 0:
        diagnostic = "PLAYER_INPUT_WRITE_SEEN_PAPER_CALLBACK_ABSENT"
    else:
        diagnostic = "BOTH_WRITE_AND_CALLBACK_SEEN_IDENTITY_UNPROVEN"
    result = S50InputPacketReview(
        native_session_id=session_id, marker_id=marker_id,
        paper_world_uuid=world,
        client_packet_write_returns=writes,
        client_player_input_write_returns=player_input,
        client_motion_write_returns=motion,
        native_control_effect_samples=effects,
        paper_player_input_callbacks=callbacks,
        client_trace_complete=True,
        diagnostic=diagnostic,
    )
    return {
        "readback": asdict(result),
        "client_original_sha256": hashlib.sha256(original).hexdigest(),
        "paper_original_sha256": hashlib.sha256(paper_log).hexdigest(),
        "source_ceiling": "WRITE_RETURNED_NOT_WIRE_OR_ACCEPTANCE",
        "qualification": "DEV_ONLY",
        "science": "NOT_RUN",
    }
