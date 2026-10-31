"""L15: S49 original dispatch/clear compatibility, synthetic source-shaped only."""
from __future__ import annotations

import hashlib
import json
from dataclasses import replace

import pytest

import test_l13_independent_goal_receipt as l13
import test_l14_original_bridge_goal_window as l14
from adapters.mineflayer.python_protocol import (
    encode_clear_controls,
    encode_observe,
    encode_set_control,
)
from relay_self.l14_original_bridge_goal_window import (
    L14SourceRejected,
    audit_l14_native_goal_window,
)


def _replace_seq(line: bytes, seq: int) -> bytes:
    data = json.loads(line)
    data["seq"] = seq
    return l13.raw(data)


def s49_original_source() -> dict:
    """Emulate S49's real command sequence, not a physical Minecraft trace."""
    args = l14.source(status="REACHED")
    item = args["item"]
    action_id = item.action.action_id
    started, pre, _, first, second = args["received_original"].splitlines(
        keepends=True,
    )
    dispatch = l13.raw({
        "type": "effect_result", "session_id": item.native.observation.session_id,
        "seq": 2, "action_id": action_id,
        "effect": "set_control", "result": "applied", "error": None,
    })
    cleanup = l13.raw({
        "type": "effect_result", "session_id": item.native.observation.session_id,
        "seq": 3, "action_id": f"{action_id}-s15-clear",
        "effect": "clear_controls", "result": "applied", "error": None,
    })
    # S49's existing executor takes its own after-observation once clear is ACKed.
    # Two *additional* terminal probes are required for a Goal window.
    after = _replace_seq(first, 4)
    goal_one = json.loads(first)
    goal_one.update({"seq": 5, "request_id": "goal-probe-5"})
    first_goal = l13.raw(goal_one)
    goal_two = json.loads(second)
    goal_two.update({"seq": 6, "request_id": "goal-probe-6"})
    second_goal = l13.raw(goal_two)
    received = started + pre + dispatch + cleanup + after + first_goal + second_goal
    sent = (
        encode_observe().encode()
        + encode_set_control(action_id, control="back", state=True).encode()
        + encode_clear_controls(f"{action_id}-s15-clear").encode()
        + encode_observe().encode()
        + encode_observe("goal-probe-5").encode()
        + encode_observe("goal-probe-6").encode()
    )
    s16 = json.loads(item.raw_s16_action)
    s16["after_seq"] = 4
    raw_s16 = l13.raw(s16)
    goal = json.loads(item.raw_external_goal)
    goal.update({
        "source_action_sha256": l13.sha(raw_s16),
        "action_end_seq": 4,
        "goal_observed_seq": 5,
    })
    raw_goal = l13.raw(goal)
    args["item"] = replace(
        item, raw_s16_action=raw_s16, raw_external_goal=raw_goal,
    )
    args["admission"] = replace(
        args["admission"],
        admitted_action_sha256=frozenset({l13.sha(raw_s16)}),
        admitted_goal_sha256=frozenset({l13.sha(raw_goal)}),
    )
    args["received_original"] = received
    args["sent_original"] = sent
    args["s7_source_receipt"] = l14._index(received, sent)
    return args


def test_s49_single_motor_and_separate_s15_clear_is_one_goal_window():
    args = s49_original_source()
    result = audit_l14_native_goal_window(**args)
    assert result.action_end_native_seq == 4
    assert result.goal_probe_seq == 5
    assert result.second_stable_probe_seq == 6
    assert result.observed_goal_status == "REACHED"
    assert result.original_received_sha256 == hashlib.sha256(
        args["received_original"],
    ).hexdigest()
    assert result.no_other_outbound_action_in_captured_bytes
    assert result.captured_native_effect_ack_for_action
    assert not result.independent_physical_goal_authenticated
    assert not result.actual_intervention_absence_proven
    assert not result.physical_learning_attested
    assert result.qualified_real_learning_pairs == 0
    assert result.s10_updates == result.habit_grants == result.action_issues == 0


@pytest.mark.parametrize("fault", [
    "other_cleanup_id", "cleanup_effect_wrong", "cleanup_rejected",
    "cleanup_duplicate", "cleanup_before_dispatch", "no_cleanup_ack",
    "dispatch_rejected", "post_action_wrong_kind", "second_outbound_motor",
    "outbound_cleanup_wrong_id", "outbound_cleanup_missing",
    "sent_cleanup_before_motor", "wrong_goal_request",
])
def test_s49_cleanup_and_two_goal_probes_fail_closed(fault):
    args = s49_original_source()
    lines = args["received_original"].splitlines(keepends=True)
    sent = args["sent_original"]
    if fault in {
        "other_cleanup_id", "cleanup_effect_wrong", "cleanup_rejected",
        "cleanup_before_dispatch", "dispatch_rejected",
        "post_action_wrong_kind", "wrong_goal_request",
    }:
        index = 2 if fault == "dispatch_rejected" else (
            5 if fault == "wrong_goal_request" else (
                4 if fault == "post_action_wrong_kind" else 3
            )
        )
        data = json.loads(lines[index])
        if fault == "other_cleanup_id":
            data["action_id"] = "another-motor"
        elif fault == "cleanup_effect_wrong":
            data["effect"] = "set_control"
        elif fault in {"cleanup_rejected", "dispatch_rejected"}:
            data["result"] = "rejected"
            data["error"] = "not-applied"
        elif fault == "cleanup_before_dispatch":
            data["seq"] = 2
        elif fault == "wrong_goal_request":
            data["request_id"] = "replaced-probe-5"
        else:
            data["kind"] = "entities"
        lines[index] = l13.raw(data)
    elif fault == "cleanup_duplicate":
        data = json.loads(lines[3])
        data["seq"] = 4
        lines = [*lines[:4], l13.raw(data), *(
            _replace_seq(line, i+1) for i, line in enumerate(lines[4:], start=4)
        )]
    elif fault == "no_cleanup_ack":
        lines = [*lines[:3], *(
            _replace_seq(line, i) for i, line in enumerate(lines[4:], start=3)
        )]
    elif fault == "second_outbound_motor":
        sent += encode_set_control("intruding", control="back", state=True).encode()
    elif fault == "outbound_cleanup_wrong_id":
        sent = sent.replace(
            f'"action_id":"{args["item"].action.action_id}-s15-clear"'.encode(),
            b'"action_id":"foreign-clear"',
        )
    elif fault == "outbound_cleanup_missing":
        sent = b"".join(
            row for row in sent.splitlines(keepends=True)
            if b"-s15-clear" not in row
        )
    elif fault == "sent_cleanup_before_motor":
        out = sent.splitlines(keepends=True)
        out[1], out[2] = out[2], out[1]
        sent = b"".join(out)
    args["received_original"] = b"".join(lines)
    args["sent_original"] = sent
    args["s7_source_receipt"] = l14._index(args["received_original"], sent)
    with pytest.raises((L14SourceRejected, ValueError)):
        audit_l14_native_goal_window(**args)
