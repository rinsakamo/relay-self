"""#150 DEV-only audit of the original Mineflayer terminal receive stream.

A bridge shutdown ACK is neither high-level S STOP ACK nor Paper-stationary
proof. This code never issues effects, reconstructs absent frames, or qualifies
R/V evidence. The caller must independently protect/authenticate the log.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Mapping, Sequence


class TerminalLivenessRejected(ValueError):
    """Missing, mixed-session or inconsistent raw terminal journal."""


@dataclass(frozen=True, slots=True)
class TerminalLiveness:
    classification: str
    session_id: str
    bridge_shutdown_ack_seen: bool
    connection_end_seen: bool
    bridge_transport_closed: bool
    high_level_stop_ack_attested: bool = False
    paper_world_stopped_attested: bool = False
    native_source_authenticated: bool = False


def audit_bridge_terminal(
    events: Sequence[Mapping[str, object]], *, session_id: str,
) -> TerminalLiveness:
    """Audit event ordering from the single ORIGINAL native JSONL stream.

    Clean closure requires a Node `shutdown_ack` followed by
    `connection_end`. Neither is a qualified high-level STOP receipt. An
    unexpected disconnect is not promoted by process exit code alone.
    """
    if (
        type(session_id) is not str or not session_id.strip()
        or type(events) not in (tuple, list) or not 1 <= len(events) <= 100000
    ):
        raise TerminalLivenessRejected("missing bounded session/terminal journal")
    ack = end = False
    last_seq = -1
    for row in events:
        if not isinstance(row, Mapping):
            raise TerminalLivenessRejected("nonrecord terminal row")
        if row.get("session_id") != session_id:
            raise TerminalLivenessRejected("foreign terminal session")
        seq = row.get("seq")
        if type(seq) is not int or seq <= last_seq:
            raise TerminalLivenessRejected("repeated/reordered terminal sequence")
        last_seq = seq
        kind = row.get("type")
        if type(kind) is not str or not kind:
            raise TerminalLivenessRejected("unknown terminal event type")
        if end:
            raise TerminalLivenessRejected("event after terminal connection_end")
        if kind == "shutdown_ack":
            if ack:
                raise TerminalLivenessRejected("duplicated bridge shutdown acknowledgment")
            ack = True
        elif kind == "connection_end":
            end = True
        elif ack and kind in {"effect_result", "command_error"}:
            raise TerminalLivenessRejected("post-shutdown physical effect or command")
    if ack and end:
        classification = "BRIDGE_SHUTDOWN_ACK_AND_CONNECTION_END_DEV"
    elif end:
        classification = "UNEXPECTED_DISCONNECT_NO_SHUTDOWN_ACK"
    elif ack:
        classification = "SHUTDOWN_ACK_WITHOUT_CONNECTION_END"
    else:
        classification = "NO_TERMINAL_HANDSHAKE"
    return TerminalLiveness(
        classification=classification,
        session_id=session_id,
        bridge_shutdown_ack_seen=ack,
        connection_end_seen=end,
        bridge_transport_closed=ack and end,
    )
