"""L22 offline-only tests: archived L21 Run2 and synthetic stable-looking trap."""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from adapters.mineflayer.l16_first_action_goal_originals import L16GoalPlan
from adapters.mineflayer.l22_post_s16_settling import (
    L22SourceRejected,
    inspect_l22_settling,
)
from test_l16_s49_first_action_original_capture import fixture as l16_fixture

ROOT = (
    Path(__file__).resolve().parents[1]
    / "docs/evidence/l21-real-20261031/run2/capture"
)


def archived_run2():
    received = (ROOT / "native_bridge_received_original.jsonl").read_bytes()
    sent = (ROOT / "native_bridge_sent_original.jsonl").read_bytes()
    receipt = json.loads(
        (ROOT / "native_bridge_source_receipt.json").read_bytes()
    )
    s16 = (ROOT / "l18_s16_terminal_original.jsonl").read_bytes()
    terminal = json.loads(s16)
    return dict(
        received_original=received,
        sent_original=sent,
        s7_receipt=receipt,
        s16_original=s16,
        plan=L16GoalPlan(0.0, 0.0, 0.49, 0.05),
        session_id=terminal["session_id"],
        action_id=terminal["action_id"],
    )


def synthetic_no_move():
    args = l16_fixture()
    return dict(
        received_original=args["received_original"],
        sent_original=args["sent_original"],
        s7_receipt=args["s7_receipt"],
        s16_original=(
            json.dumps({
                "schema": "L13_S16_TERMINAL_SOURCE_V1",
                "session_id": args["session_id"],
                "action_id": args["action_id"],
                "source_status": "executed",
                "disposition": "outcome",
                "reason_code": "observed_execution",
                "before_seq": args["before_seq"],
                "after_seq": args["after_seq"],
            }, separators=(",", ":")) + "\n"
        ).encode(),
        plan=args["plan"],
        session_id=args["session_id"],
        action_id=args["action_id"],
    )


def test_archived_real_run2_residual_move_is_not_stability():
    review = inspect_l22_settling(**archived_run2())
    assert review.after_seq == 31
    assert (review.first_probe_seq, review.second_probe_seq) == (33, 35)
    assert review.move_event_seqs == (32, 34)
    assert review.settling_state == "SETTLING_OBSERVED"
    assert review.reason == "POST_S16_MOVE_EVENT"
    assert review.post_s16_displacement_m > 0.09
    assert 0.03 < review.two_probe_displacement_m < 0.05
    assert review.geometric_goal_candidate == "NOT_REACHED"
    assert review.accepted_goal_status == "UNDETERMINED"
    assert not review.physically_stopped_proven
    assert not review.stable_world_ticks_attested
    assert review.qualified_real_learning_pairs == 0
    assert review.s10_updates == review.s11_grants == 0


def test_synthetic_equal_probes_do_not_prove_physical_idle():
    review = inspect_l22_settling(**synthetic_no_move())
    assert review.move_event_seqs == ()
    assert review.settling_state == "STABILITY_UNPROVEN"
    assert review.reason == "NO_ATTESTED_IDLE_TICK_WINDOW"
    assert review.accepted_goal_status == "UNDETERMINED"
    assert not review.stable_world_ticks_attested
    assert review.qualified_real_learning_pairs == 0


@pytest.mark.parametrize("fault", [
    "action", "session", "not_outcome", "before", "source_sha",
    "missing_second_probe", "extra_after", "missing_clear",
    "duplicate_request", "s16_missing_newline",
])
def test_corrupt_or_foreign_source_fails_closed(fault):
    args = archived_run2()
    if fault in ("action", "session", "not_outcome", "before"):
        doc = json.loads(args["s16_original"])
        if fault == "action":
            doc["action_id"] = "wrong-owner"
        elif fault == "session":
            doc["session_id"] = "wrong-session"
        elif fault == "not_outcome":
            doc["disposition"] = "unknown"
        else:
            doc["before_seq"] = 31
        args["s16_original"] = (json.dumps(doc) + "\n").encode()
    elif fault == "source_sha":
        args["s7_receipt"]["received_sha256"] = "0" * 64
    elif fault == "missing_second_probe":
        args["received_original"] = b"".join(
            args["received_original"].splitlines(keepends=True)[:-1]
        )
    elif fault == "extra_after":
        args["received_original"] += b'{"type":"junk"}\n'
    elif fault == "missing_clear":
        args["sent_original"] = args["sent_original"].replace(
            b'"clear_controls"', b'"set_control"', 1
        )
    elif fault == "duplicate_request":
        args["sent_original"] += (
            b'{"type":"observe","request_id":"l16:'
            + args["session_id"].encode()
            + b':' + args["action_id"].encode() + b':goal-1"}\n'
        )
    elif fault == "s16_missing_newline":
        args["s16_original"] = args["s16_original"].rstrip(b"\n")
    with pytest.raises((L22SourceRejected, ValueError, TypeError)):
        inspect_l22_settling(**args)
