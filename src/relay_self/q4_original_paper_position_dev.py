"""U18 original owned Paper player positions for isolated MOVE/STOP DEV.

Uses only the existing Paper observer and OwnedPaperWorld.read_owned_log.
This is a source-correlated stability *window*, not a native motor or
unqualified claim that a particular Action caused Paper movement.
"""
from __future__ import annotations

import asyncio
import hashlib
import math
import time
from dataclasses import dataclass

from experiments.cognitive_physical_place_move_issue_dev import Stage27PlaceMoveReceipt
from relay_self.owned_paper_world_dev import PaperTickReceipt
from relay_self.owned_resident_physical_bridge_dev import OwnedResidentPhysicalBridge
from relay_self.resident_paper_presence_join_dev import (
    OwnedPaperResidentTrace,
    PaperResidentEvent,
    ResidentPaperJoinError,
    parse_owned_paper_resident_trace,
)


class Q4OriginalPaperHold(RuntimeError):
    """Owned Paper log lacks a genuine stable 8+8 tick position window."""


@dataclass(frozen=True, slots=True)
class Q4OriginalPaperPositionWindow:
    """Actual OwnedPaperWorld log prefix and three main-thread positions."""

    paper_session_id: str
    world_uuid: str
    native_session_id: str
    actor_uuid: str
    actor_name: str
    log_prefix_size: int
    log_prefix_sha256: str
    points: tuple[PaperResidentEvent, PaperResidentEvent, PaperResidentEvent]
    receipts: tuple[PaperTickReceipt, PaperTickReceipt, PaperTickReceipt]
    causal_action_attested: bool = False


def _position(sample: PaperResidentEvent) -> tuple[float, float, float]:
    return sample.x, sample.y, sample.z


def _native_position(receipt: Stage27PlaceMoveReceipt, n: int):
    pos = (
        receipt.initial_stop_probe,
        receipt.first_stable_probe,
        receipt.settled_probe,
    )[n].snapshot.position
    return pos.x, pos.y, pos.z


def _owned_log_source(
    bridge: OwnedResidentPhysicalBridge,
    self_id: str,
) -> tuple[OwnedPaperResidentTrace, bytes]:
    session = bridge.paper.owned_session_id
    if (
        type(bridge) is not OwnedResidentPhysicalBridge
        or type(self_id) is not str
        or session is None or bridge.paper.held_uncertain
        or self_id not in bridge.sessions or self_id not in bridge.configs
    ):
        raise Q4OriginalPaperHold("original live Paper/Native source required")
    bridge._check_world()
    raw = bridge.paper.read_owned_log(session)
    if type(raw) is not bytes or not 0 < len(raw) <= 32 * 1024 * 1024:
        raise Q4OriginalPaperHold("owned Paper log absent or unbounded")
    try:
        trace = parse_owned_paper_resident_trace(
            owned_paper_session_id=session,
            expected_world_uuid=bridge.lifecycle.world.world_id,
            owned_paper_log=raw,
            log_ref="owned-paper-process:" + session,
        )
    except (ResidentPaperJoinError, UnicodeError, ValueError) as exc:
        raise Q4OriginalPaperHold("owned Paper player source invalid") from exc
    return trace, raw


def _build_window(
    bridge: OwnedResidentPhysicalBridge,
    self_id: str,
    receipt: Stage27PlaceMoveReceipt,
) -> Q4OriginalPaperPositionWindow:
    trace, raw = _owned_log_source(bridge, self_id)
    name = bridge.configs[self_id].username
    session = bridge.sessions[self_id]
    if (
        not isinstance(receipt, Stage27PlaceMoveReceipt)
        or receipt.native_session_id != session.started.session_id
        or receipt.journal_status != "NATIVE_PLACE_MOVE_SETTLED"
        or not 0.1 <= receipt.displacement_m <= 1.0
    ):
        raise Q4OriginalPaperHold("original Native MOVE terminal missing")
    people = [e for e in trace.events if e.name == name]
    if (
        not people or people[0].event != "JOIN"
        or any(e.event in {"QUIT", "JOIN"} for e in people[1:])
        or len({e.actor_uuid for e in people}) != 1
    ):
        raise Q4OriginalPaperHold("one continuously owned Paper actor required")
    origin = _position(people[0])
    # A Paper position must be independently different from the login body,
    # but this temporal correlation alone does not authenticate motor cause.
    visible = [
        e for e in people[1:]
        if e.event in {"PRESENT", "MOVE"}
        and math.dist(origin, _position(e)) >= 0.1
    ]
    chosen = None
    for i, stop in enumerate(visible):
        if math.dist(_position(stop), _native_position(receipt, 0)) > 0.25:
            continue
        for j in range(i + 1, len(visible)):
            first = visible[j]
            if (
                first.tick - stop.tick < 8
                or math.dist(_position(first), _native_position(receipt, 1)) > 0.16
            ):
                continue
            for settled in visible[j + 1:]:
                if (
                    settled.tick - first.tick >= 8
                    and math.dist(
                        _position(settled), _native_position(receipt, 2),
                    ) <= 0.12
                    and math.dist(
                        _position(first), _position(settled),
                    ) <= 0.06
                ):
                    chosen = (stop, first, settled)
                    break
            if chosen is not None:
                break
        if chosen is not None:
            break
    if chosen is None:
        raise Q4OriginalPaperHold(
            "Paper did not observe stable position over independent 8+8 ticks"
        )
    refs = tuple(
        PaperTickReceipt(
            trace.paper_session_id, x.tick,
            f"paper-owned-position:{trace.boot_id}:{x.actor_uuid}:{x.line}",
        )
        for x in chosen
    )
    return Q4OriginalPaperPositionWindow(
        trace.paper_session_id, trace.world_uuid,
        session.started.session_id, people[0].actor_uuid, name,
        len(raw), hashlib.sha256(raw).hexdigest(), chosen, refs,
    )


async def await_original_q4_paper_position_window(
    bridge: OwnedResidentPhysicalBridge,
    self_id: str,
    receipt: Stage27PlaceMoveReceipt,
    *,
    timeout_s: float = 7.0,
) -> Q4OriginalPaperPositionWindow:
    """Bounded append-only Paper sampling; never fabricates a position/tick."""
    if type(timeout_s) not in (int, float) or not 0 < timeout_s <= 12:
        raise Q4OriginalPaperHold("bounded Paper position observation required")
    deadline = time.monotonic() + timeout_s
    while time.monotonic() < deadline:
        try:
            return _build_window(bridge, self_id, receipt)
        except Q4OriginalPaperHold:
            await asyncio.sleep(0.1)
    raise Q4OriginalPaperHold("owned Paper position 8+8 tick evidence timed out")


def verify_original_q4_paper_position_window(
    bridge: OwnedResidentPhysicalBridge,
    self_id: str,
    receipt: Stage27PlaceMoveReceipt,
    window: Q4OriginalPaperPositionWindow,
) -> None:
    """Re-read same owned Paper log prefix; reject forged typed tick receipts."""
    if (
        not isinstance(window, Q4OriginalPaperPositionWindow)
        or window.causal_action_attested
        or window.paper_session_id != bridge.paper.owned_session_id
        or window.native_session_id != receipt.native_session_id
        or window.actor_name != bridge.configs[self_id].username
    ):
        raise Q4OriginalPaperHold("foreign original Paper actor/World window")
    trace, current = _owned_log_source(bridge, self_id)
    if (
        len(current) < window.log_prefix_size
        or hashlib.sha256(current[:window.log_prefix_size]).hexdigest()
        != window.log_prefix_sha256
        or trace.world_uuid != window.world_uuid
        or trace.paper_session_id != window.paper_session_id
    ):
        raise Q4OriginalPaperHold("original Paper log prefix changed")
    try:
        prefix = parse_owned_paper_resident_trace(
            owned_paper_session_id=window.paper_session_id,
            expected_world_uuid=window.world_uuid,
            owned_paper_log=current[:window.log_prefix_size],
            log_ref="owned-paper-process:" + window.paper_session_id,
        )
    except (ResidentPaperJoinError, UnicodeError, ValueError) as exc:
        raise Q4OriginalPaperHold("Paper log prefix cannot be replayed") from exc
    if (
        any(x not in prefix.events for x in window.points)
        or any(x.actor_uuid != window.actor_uuid or x.name != window.actor_name
               for x in window.points)
    ):
        raise Q4OriginalPaperHold("Paper event identity or position replaced")
    accepted = _build_from_verified_points(window)
    if accepted != window.receipts:
        raise Q4OriginalPaperHold("typed Paper tick refs not from original positions")


def _build_from_verified_points(
    window: Q4OriginalPaperPositionWindow,
) -> tuple[PaperTickReceipt, PaperTickReceipt, PaperTickReceipt]:
    return tuple(
        PaperTickReceipt(
            window.paper_session_id, p.tick,
            f"paper-owned-position:{p.boot_id}:{p.actor_uuid}:{p.line}",
        )
        for p in window.points
    )
