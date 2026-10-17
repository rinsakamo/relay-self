"""S #627 synthetic negatives: reference/order audit is NOT real-world proof."""
from __future__ import annotations

from copy import deepcopy

import pytest

from adapters.mineflayer.m02_paper_dev.s50_control_loop_order import (
    ControlLoopOrderRejected,
    audit_control_loop_order,
)


def valid():
    rows = [
        {"kind": "SETUP_TP", "writer": "setup"},
        {
            "kind": "SETUP_HANDOFF", "writer": "executor",
            "teleport_confirm_ref": "raw-teleport-confirm",
            "client_pose_ref": "raw-native-client-pose",
            "paper_pose_ref": "raw-paper-pose",
            "correction_settlement_ref": "raw-correction-window",
        },
        {"kind": "ACTION_ISSUED", "writer": "supervisor", "action_id": "move-1"},
        {"kind": "LOOK", "writer": "executor", "action_id": "move-1"},
        {"kind": "FORWARD_ON", "writer": "executor", "action_id": "move-1"},
        {"kind": "CLEAR_ALL", "writer": "executor", "action_id": "move-1"},
        {
            "kind": "EXECUTOR_RESULT", "writer": "executor",
            "action_id": "move-1", "terminal": "OUTCOME",
            "world_evidence_ref": "original-paper-motion",
        },
        {"kind": "STOP", "writer": "executor"},
    ]
    return [
        {
            "ordinal": i, "session_id": "native-session-1",
            "source_ref": f"original-source-{i}", "action_id": None,
            **row,
        }
        for i, row in enumerate(rows, 1)
    ]


def test_single_writer_and_real_outcome_reference_order_is_only_offline():
    result = audit_control_loop_order(valid())
    assert result["classification"] == "S50_OFFLINE_CONTROL_LOOP_ORDER_ONLY"
    assert result["terminal"] == "OUTCOME"
    assert result["source_references_authenticated"] is False
    assert result["self_feedback_delivered"] is False
    assert result["pending_server_corrections_excluded"] is False
    assert result["actual_server_effective_control_ticks"] == "NOT_ATTESTED"
    assert result["P1_wait_ticks_admitted"] == 0
    assert result["science_go"] is False


def test_read_only_observer_cannot_issue_motor_or_grant_action():
    rows = valid()
    rows.insert(2, {
        "ordinal": 3, "session_id": "native-session-1",
        "source_ref": "original-probe", "kind": "OBSERVE", "writer": "observer",
        "action_id": None,
    })
    for i, row in enumerate(rows, 1):
        row["ordinal"] = i
    assert audit_control_loop_order(rows)["terminal"] == "OUTCOME"
    for kind, writer in (("LOOK", "observer"), ("ACTION_ISSUED", "observer")):
        mutated = deepcopy(rows)
        mutated[2]["kind"] = kind
        mutated[2]["writer"] = writer
        with pytest.raises(ControlLoopOrderRejected):
            audit_control_loop_order(mutated)
    mutated = deepcopy(rows)
    mutated[2]["effect"] = "set_control"
    with pytest.raises(ControlLoopOrderRejected):
        audit_control_loop_order(mutated)


def test_look_gate_failure_must_return_unknown_not_imaginary_outcome():
    rows = valid()
    rows = [rows[i] for i in (0, 1, 2, 3, 6, 7)]
    for i, row in enumerate(rows, 1):
        row["ordinal"] = i
    rows[4]["terminal"] = "UNKNOWN"
    rows[4]["error_ref"] = "original-failed-paper-look"
    rows[4].pop("world_evidence_ref")
    assert audit_control_loop_order(rows)["terminal"] == "UNKNOWN"
    rows[4]["terminal"] = "OUTCOME"
    with pytest.raises(ControlLoopOrderRejected):
        audit_control_loop_order(rows)


@pytest.mark.parametrize(("index", "changes"), [
    (0, {"writer": "observer"}),
    (0, {"source_ref": ""}),
    (1, {"teleport_confirm_ref": ""}),
    (1, {"correction_settlement_ref": None}),
    (2, {"writer": "setup"}),
    (3, {"action_id": "other"}),
    (4, {"writer": "observer"}),
    (4, {"session_id": "other"}),
    (4, {"kind": "LOOK"}),
    (5, {"kind": "FORWARD_ON"}),
    (6, {"terminal": "OUTCOME", "world_evidence_ref": ""}),
    (6, {"terminal": "UNKNOWN", "error_ref": ""}),
    (7, {"writer": "setup"}),
    (7, {"ordinal": 1}),
])
def test_rejects_unauthorized_lost_or_forged_control_evidence(index, changes):
    rows = valid()
    rows[index].update(changes)
    with pytest.raises(ControlLoopOrderRejected):
        audit_control_loop_order(rows)


def test_no_stop_duplicate_setup_or_parallel_action_is_rejected():
    rows = valid()
    with pytest.raises(ControlLoopOrderRejected):
        audit_control_loop_order(rows[:-1])
    other = valid()
    other.insert(4, {
        "ordinal": 5, "session_id": "native-session-1",
        "source_ref": "interloper", "kind": "ACTION_ISSUED",
        "writer": "supervisor", "action_id": "move-2",
    })
    for i, row in enumerate(other, 1):
        row["ordinal"] = i
    with pytest.raises(ControlLoopOrderRejected):
        audit_control_loop_order(other)
    other = valid()
    other[3]["kind"] = "SETUP_TP"
    other[3]["writer"] = "setup"
    other[3]["action_id"] = None
    with pytest.raises(ControlLoopOrderRejected):
        audit_control_loop_order(other)
