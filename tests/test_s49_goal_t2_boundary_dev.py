"""Source-negative tests for original S49->T2 DEV owner handoff."""
from types import SimpleNamespace as NS

import pytest

from adapters.mineflayer.s49_goal_t2_boundary_dev import (
    GoalT2ActionBoundaryDev,
    GoalT2BoundaryRejected,
)
from relay_self.action import ActionState


class ExistingTickOwner:
    def __init__(self, session="world-A", seq=3):
        self.session_id = session
        self.failed = False
        self.active_action = None
        self.pending_meal = None
        self.fatigue = object()
        self.previous = NS(session_id=session, seq=seq, data={"status": "ADMITTED"})
        self.rows = []

    def begin(self, action_id):
        assert self.active_action is None
        self.active_action = action_id

    def finish(self, consequence, terminal):
        assert consequence.action_id == self.active_action == terminal.action_id
        self.active_action = None

    def observe(self, frame):
        self.previous = frame


def outcome(action="goal-A", session="world-A", after_seq=12,
            clear_seq=11, state=ActionState.OUTCOME, status="executed"):
    return NS(
        terminal=NS(action_id=action, state=state),
        consequence=NS(
            action_id=action, status=NS(value=status),
            after_observation=NS(session_id=session, seq=after_seq),
            cleanup_receipt=NS(session_id=session, seq=clear_seq,
                               result="applied", effect="clear_controls"),
        ),
    )


def test_original_s16_handoff_does_not_post_or_infer_p1():
    owner = ExistingTickOwner()
    boundary = GoalT2ActionBoundaryDev(owner, session_id="world-A")
    boundary.before_issue("goal-A", probe_seq=5)
    receipt = boundary.after_terminal(outcome())
    assert receipt.s16_after_seq == 12
    assert receipt.clear_seq == 11
    assert receipt.t2_ledger_rows_at_terminal == 0
    assert not receipt.gait_world_tick_authenticated
    assert not receipt.p1_full_tick_attested
    assert not receipt.m0_or_p1_posting_from_bridge
    assert not boundary.latched
    assert owner.active_action is None


@pytest.mark.parametrize("bad_state,bad_status", [
    (ActionState.UNKNOWN, "executed"),
    (ActionState.OUTCOME, "undetermined"),
])
def test_native_unknown_latches_owner(bad_state, bad_status):
    owner = ExistingTickOwner()
    boundary = GoalT2ActionBoundaryDev(owner, session_id="world-A")
    boundary.before_issue("goal-A", probe_seq=5)
    with pytest.raises(GoalT2BoundaryRejected):
        boundary.after_terminal(outcome(state=bad_state, status=bad_status))
    assert owner.failed and boundary.latched


def test_no_new_goal_action_without_fresh_post_s16_paper_source():
    owner = ExistingTickOwner()
    boundary = GoalT2ActionBoundaryDev(owner, session_id="world-A")
    boundary.before_issue("goal-A", probe_seq=5)
    boundary.after_terminal(outcome())
    with pytest.raises(GoalT2BoundaryRejected):
        boundary.before_issue("goal-B", probe_seq=16)
    assert owner.failed


def test_source_continuity_allows_next_original_action_boundary():
    owner = ExistingTickOwner()
    boundary = GoalT2ActionBoundaryDev(owner, session_id="world-A")
    boundary.before_issue("goal-A", probe_seq=5)
    boundary.after_terminal(outcome())
    owner.observe(NS(session_id="world-A", seq=14, data={"status": "ADMITTED"}))
    boundary.before_issue("goal-B", probe_seq=16)
    boundary.after_terminal(outcome("goal-B", after_seq=20, clear_seq=19))
    assert [x.action_id for x in boundary.receipts] == ["goal-A", "goal-B"]
    assert len(boundary.receipts) == 2


@pytest.mark.parametrize("foreign", ["other-world", ""])
def test_foreign_t2_refused(foreign):
    with pytest.raises(GoalT2BoundaryRejected):
        GoalT2ActionBoundaryDev(ExistingTickOwner(foreign), session_id="world-A")


def test_foreign_terminal_and_late_clear_refused():
    owner = ExistingTickOwner()
    boundary = GoalT2ActionBoundaryDev(owner, session_id="world-A")
    boundary.before_issue("goal-A", probe_seq=5)
    with pytest.raises(GoalT2BoundaryRejected):
        boundary.after_terminal(outcome(session="foreign"))
    assert owner.failed
    owner2 = ExistingTickOwner()
    b2 = GoalT2ActionBoundaryDev(owner2, session_id="world-A")
    b2.before_issue("goal-A", probe_seq=5)
    with pytest.raises(GoalT2BoundaryRejected):
        b2.after_terminal(outcome(clear_seq=13))
    assert owner2.failed


def test_unadmitted_or_stale_paper_anchor_refused():
    owner = ExistingTickOwner()
    owner.previous.data["status"] = "UNDETERMINED"
    with pytest.raises(GoalT2BoundaryRejected):
        GoalT2ActionBoundaryDev(owner, session_id="world-A")
    owner = ExistingTickOwner(seq=5)
    boundary = GoalT2ActionBoundaryDev(owner, session_id="world-A")
    with pytest.raises(GoalT2BoundaryRejected):
        boundary.before_issue("goal-A", probe_seq=5)
    assert owner.failed


def _active_intent():
    from relay_self.intent import IntentCommitment
    from relay_self.provenance import Provenance
    intent = IntentCommitment()
    intent.commit(
        "goal-navigate", objective="source-qualified movement",
        at_ns=1, provenance=Provenance("test-owner", "goal-commit"),
    )
    return intent


def test_default_s49_goal_unbound(monkeypatch):
    from adapters.mineflayer.s49_goal_executor_dev import S49GoalExecutorDev
    monkeypatch.setenv("S49_L0_GOAL_LOOP_DEV_ONLY", "1")
    executor = S49GoalExecutorDev("world-A", _active_intent())
    assert executor._t2_boundary_dev is None
    with pytest.raises(Exception):
        executor.bind_t2_owner_dev(ExistingTickOwner())


def test_bind_once_only_before_first_action(monkeypatch):
    from adapters.mineflayer.s49_goal_executor_dev import S49GoalExecutorDev
    monkeypatch.setenv("S49_L0_GOAL_LOOP_DEV_ONLY", "1")
    monkeypatch.setenv("S49_L1_T2_BOUNDARY_DEV_ONLY", "1")
    executor = S49GoalExecutorDev("world-A", _active_intent())
    bound = executor.bind_t2_owner_dev(ExistingTickOwner())
    assert bound.session_id == executor.session_id
    with pytest.raises(Exception):
        executor.bind_t2_owner_dev(ExistingTickOwner())
