"""Opt-in S49 Goal -> existing T2 Action boundary, without new ownership.

The recipient MUST be the live, single TickAccounting owned by the same
session. This does not acquire WorldTicks or assign gait. It never calls
T2.observe; the sole original reader must deliver those source ticks.
Native S16 and Paper WorldTick are different source sequences.
"""
from __future__ import annotations

from dataclasses import dataclass

from relay_self.action import ActionState


class GoalT2BoundaryRejected(ValueError):
    """No source-safe same-session body accounting handoff."""


@dataclass(frozen=True, slots=True)
class GoalT2BoundaryReceiptDev:
    session_id: str
    action_id: str
    terminal: str
    s16_after_seq: int
    clear_seq: int
    t2_ledger_rows_at_terminal: int
    s16_outcome_attested: bool = False
    source_scope: str = "S49_S16_TO_T2_ACTION_BOUNDARY_DEV_ONLY"
    gait_world_tick_authenticated: bool = False
    p1_full_tick_attested: bool = False
    m0_or_p1_posting_from_bridge: bool = False


class GoalT2ActionBoundaryDev:
    """Only bind and close an existing T2 owner, never create another."""

    def __init__(self, owner, *, session_id: str):
        if (
            type(session_id) is not str or not session_id
            or getattr(owner, "session_id", None) != session_id
            or not callable(getattr(owner, "begin", None))
            or not callable(getattr(owner, "finish", None))
            or not callable(getattr(owner, "observe", None))
            or getattr(owner, "failed", True)
            or getattr(owner, "active_action", object()) is not None
            or getattr(owner, "pending_meal", object()) is not None
            or getattr(owner, "fatigue", None) is None
        ):
            raise GoalT2BoundaryRejected("existing live same-session T2 required")
        previous = getattr(owner, "previous", None)
        if (
            previous is None
            or getattr(previous, "session_id", None) != session_id
            or type(getattr(previous, "seq", None)) is not int
            or not isinstance(getattr(previous, "data", None), dict)
            or previous.data.get("status") != "ADMITTED"
        ):
            raise GoalT2BoundaryRejected("initial admitted T2 WorldTick required")
        self.owner = owner
        self.session_id = session_id
        self.active_action: str | None = None
        self.last_s16_seq: int | None = None
        self.receipts: list[GoalT2BoundaryReceiptDev] = []
        self.latched = False

    def latch(self) -> None:
        self.latched = True
        self.owner.failed = True

    def before_issue(self, action_id: str, *, probe_seq: int) -> None:
        """Called only AFTER the original S49 supervisor issues the Action."""
        prev = getattr(self.owner, "previous", None)
        if (
            self.latched or self.owner.failed
            or self.active_action is not None
            or self.owner.active_action is not None
            or type(action_id) is not str or not action_id
            or type(probe_seq) is not int
            or prev is None or prev.session_id != self.session_id
            or type(prev.seq) is not int
            or not isinstance(prev.data, dict)
            or prev.data.get("status") != "ADMITTED"
            or prev.seq >= probe_seq
            or (self.last_s16_seq is not None
                and prev.seq <= self.last_s16_seq)
        ):
            self.latch()
            raise GoalT2BoundaryRejected(
                "no fresh admitted T2 tick since last closed S16"
            )
        try:
            self.owner.begin(action_id)
        except BaseException:
            self.latch()
            raise
        self.active_action = action_id

    def after_terminal(self, receipt) -> GoalT2BoundaryReceiptDev:
        """Original S16 result only; P1 fatigue changes happen in T2.observe."""
        terminal = getattr(receipt, "terminal", None)
        consequence = getattr(receipt, "consequence", None)
        after = getattr(consequence, "after_observation", None)
        ack = getattr(consequence, "cleanup_receipt", None)
        status = getattr(getattr(consequence, "status", None), "value", None)
        if (
            self.latched
            or terminal is None or consequence is None
            or self.active_action is None
            or terminal.action_id != self.active_action
            or consequence.action_id != self.active_action
            or terminal.state not in (ActionState.OUTCOME, ActionState.UNKNOWN)
            or (terminal.state is ActionState.OUTCOME and status != "executed")
            or (terminal.state is ActionState.UNKNOWN and status != "undetermined")
            or after is None or after.session_id != self.session_id
            or type(after.seq) is not int
            or (self.last_s16_seq is not None
                and after.seq <= self.last_s16_seq)
            or ack is None or ack.session_id != self.session_id
            or ack.effect != "clear_controls" or ack.result != "applied"
            or type(ack.seq) is not int or ack.seq > after.seq
            or getattr(self.owner, "active_action", None) != self.active_action
        ):
            self.latch()
            raise GoalT2BoundaryRejected(
                "unclosed/foreign/inconsistent native S16; P1 admission forbidden"
            )
        try:
            self.owner.finish(consequence, terminal)
            if self.owner.failed or self.owner.active_action is not None:
                raise GoalT2BoundaryRejected("existing T2 refused original S16")
        except BaseException:
            self.latch()
            raise
        item = GoalT2BoundaryReceiptDev(
            self.session_id, self.active_action, terminal.state.value,
            after.seq, ack.seq, len(self.owner.rows),
            s16_outcome_attested=terminal.state is ActionState.OUTCOME,
        )
        self.receipts.append(item)
        self.last_s16_seq = after.seq
        self.active_action = None
        return item
