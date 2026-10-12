"""V source-shaped S1→L1 negative and tamper controls; no physical model/World."""
from __future__ import annotations

import copy
import json

import pytest

from experiments.validation import s1_l1_boundary as v


def row(kind, index, **kwargs):
    return dict(schema=v.S1_SCHEMA, source=v.S1_SOURCE, session="v-offline-only",
                kind=kind, index=index, **kwargs)


def wait_stream():
    return [
        row("session_started", 0, max_events=1, max_actions=1, max_seconds=2),
        row(
            "world_decision", 1, epoch=1, layer="L0", source_type="MINEFLAYER_NATIVE",
            event_seq=1, probe_seq=2, event_source="v:1", probe_source="v:2",
            probe_request_id="v-reprobe", selection="WAIT", action_request_id=None,
            retained_revision=1, goal_success_attested=False,
        ),
        row("session_terminal", 2, events=1, action_requests=0, closed_outcomes=0,
            learning_updates=0, habit_grants=0, l2_attempts=0,
            model_stop_ack=False),
    ]


def test_s1_wait_without_action_cannot_authorize_learning():
    out = v.audit_rows(wait_stream())
    assert out["decisions"] == 1 and out["closed_outcomes"] == 0
    assert out["L1_admission"] == "NOT_AUTHORIZED_FROM_LOG"
    assert out["goal_success"] == "NOT_ATTESTED"
    assert out["science_go"] is False
    assert "WORLD_SOURCE_REVISION_NOT_RETAINED_REVISION" in out["missing_from_log"]


@pytest.mark.parametrize(("index", "change"), [
    (1, {"schema": "FAKE_SOURCE"}),
    (1, {"source": "S49_REAL_VERIFIED"}),
    (1, {"session": "foreign"}),
    (1, {"index": 7}),
    (1, {"epoch": 2}),
    (1, {"selection": "MOVE_AWAY", "action_request_id": None}),
    (1, {"goal_success_attested": True}),
    (1, {"event_seq": 3}),
    (2, {"closed_outcomes": 1}),
    (2, {"learning_updates": 1}),
    (2, {"habit_grants": 1}),
    (2, {"model_stop_ack": True}),
    (2, {"source": "PHYSICAL"}),
])
def test_tamper_in_known_s1_fields_fail_closed(index, change):
    events = wait_stream()
    events[index].update(change)
    with pytest.raises(v.BoundaryRejected):
        v.audit_rows(events)


def test_truncated_event_source_blocks_read_only(tmp_path):
    p = tmp_path / "events.jsonl"
    p.write_text("\n".join(json.dumps(x) for x in wait_stream()))
    with pytest.raises(v.BoundaryRejected, match="truncated"):
        v.audit_file(p)
    p.write_text("\n".join(json.dumps(x) for x in wait_stream()) + "\n")
    assert v.audit_file(p)["L1_admission"] == "NOT_AUTHORIZED_FROM_LOG"
    symlink = tmp_path / "foreign"
    symlink.symlink_to(p)
    with pytest.raises(v.BoundaryRejected):
        v.audit_file(symlink)


def test_unknown_and_failure_never_count_as_learning():
    events = wait_stream()
    events.pop()
    events[1]["selection"] = "MOVE_AWAY"
    events[1]["action_request_id"] = "a-1"
    events.extend([
        row("action_requested_not_yet_issued", 2, epoch=1, action_id="a-1",
            event_seq=1, probe_seq=2, authority_id="only-s-fixture"),
        row("action_outcome_unknown", 3, action_id="a-1", physical_outcome="UNKNOWN",
            safe_to_replay=False, error_type="RuntimeError"),
        row("session_failed", 4, action_requests=1, closed_outcomes=0,
            physical_outcome="UNKNOWN_IF_IN_FLIGHT", no_replay=True,
            learning_updates=0, habit_grants=0),
    ])
    out = v.audit_rows(events)
    assert out["terminal"] == "S1_FAILURE_NO_L1_PROMOTION"
    assert out["uncertain_actions"] == 1
    assert out["L1_admission"] == "NOT_AUTHORIZED_FROM_LOG"
    tampered = copy.deepcopy(events)
    tampered[3]["safe_to_replay"] = True
    with pytest.raises(v.BoundaryRejected):
        v.audit_rows(tampered)


def test_requested_action_not_sufficient_for_s16_closure():
    events = wait_stream()
    events.pop()
    events[1]["selection"] = "MOVE_AWAY"
    events[1]["action_request_id"] = "a-1"
    events.append(row("action_requested_not_yet_issued", 2, epoch=1, action_id="a-1",
                      event_seq=1, probe_seq=2, authority_id="fixture"))
    events.append(row("session_terminal", 3, events=1, action_requests=1,
                      closed_outcomes=0, learning_updates=0, habit_grants=0,
                      l2_attempts=0, model_stop_ack=False))
    with pytest.raises(v.BoundaryRejected, match="unclosed"):
        v.audit_rows(events)
