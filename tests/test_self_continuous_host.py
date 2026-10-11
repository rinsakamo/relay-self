"""Bounded Self 1.0 session driver, offline S49 source fixtures only."""
from __future__ import annotations

import asyncio
import json
from dataclasses import replace
from pathlib import Path
from types import SimpleNamespace

import pytest

import test_action_feedback_qualification as s17
import test_postmain_s42_world_contrast as s42
from adapters.mineflayer.normal_action import NormalActionReceipt, NormalWorldL0
from adapters.mineflayer.self_continuous_host import (
    AppendOnlySessionEvents,
    BoundedSessionDriver,
    SessionBudget,
    SessionRunRejected,
)
from relay_self.provenance import Provenance
from relay_self.reactive_l0 import L0ActionGrant


class FakeNativeFrames:
    """Exactly one session, synthetic frames, never a network or World child."""

    def __init__(self, sid, frames):
        self.started = SimpleNamespace(session_id=sid)
        self.frames = list(frames)
        self.calls = 0

    async def receive(self):
        self.calls += 1
        if not self.frames:
            await asyncio.sleep(0.001)
            raise TimeoutError
        return self.frames.pop(0)


def _fixture(tmp_path: Path, *, two_events=True):
    retained, near, far, near_event, far_event = s42._pair()
    *_, consequence, _, closed = s17.executed_closed_chain()
    sid = consequence.session_id
    # Synthetic fixtures are re-bound to the same session solely to exercise
    # the driver contract. This is NOT fresh physical evidence.
    distant = replace(far_event, session_id=sid, seq=1)
    distant_probe = replace(far.observation, session_id=sid, seq=2)
    close = replace(near_event, session_id=sid, seq=3)
    close_probe = replace(near.observation, session_id=sid, seq=4)
    frames = [distant, close] if two_events else [distant]
    source = FakeNativeFrames(sid, frames)
    host = NormalWorldL0(
        sid, "escape-threat", retained,
        max_events=2 if two_events else 1, max_action_requests=1,
    )
    budget = SessionBudget(
        max_events=2 if two_events else 1, max_actions=1,
        max_frames=6, max_seconds=3, poll_seconds=.02,
    )
    sink = AppendOnlySessionEvents(tmp_path / "events.jsonl", sid)
    driver = BoundedSessionDriver(host, source, budget, sink)
    requests = []

    async def probe(event):
        requests.append(event.seq)
        return distant_probe if event.seq == distant.seq else close_probe

    def grant(choice, event_seq):
        return L0ActionGrant(
            "independent-test-owner", closed.action_id,
            "escape-threat", sid, event_seq, choice.probe_seq, choice.entity_id,
            True, Provenance("offline-independent-authority", "synthetic"),
        )

    async def execute(step):
        return NormalActionReceipt(
            terminal=closed, consequence=consequence,
            source=close_probe.provenance,
        )

    return driver, probe, grant, execute, requests, source


def _events(root):
    return [json.loads(line) for line in (root / "events.jsonl").read_text().splitlines()]


def test_bounded_two_decisions_and_one_existing_s17_closed_outcome(tmp_path):
    driver, probe, grant, execute, requests, source = _fixture(tmp_path)
    result = asyncio.run(driver.run(probe=probe, grant=grant, on_action=execute))
    assert result["terminal"] == "ACTION_BUDGET_ENDED"
    assert result["events"] == 2
    assert result["action_requests"] == result["closed_outcomes"] == 1
    assert result["learning_updates"] == result["habit_grants"] == 0
    assert result["l2_attempts"] == 0
    rows = _events(tmp_path)
    assert [r["kind"] for r in rows] == [
        "session_started", "world_decision", "world_decision",
        "action_requested_not_yet_issued", "action_outcome", "session_terminal",
    ]
    assert [r["selection"] for r in rows if r["kind"] == "world_decision"] == [
        "WAIT", "MOVE_AWAY",
    ]
    assert rows[-2]["goal_success_attested"] is False
    assert rows[-2]["learning_feedback_qualified"] is False
    assert rows[-2]["physical_outcome"] == "outcome"
    assert requests == [1, 3]
    assert source.calls == 2
    assert [r["index"] for r in rows] == list(range(len(rows)))
    with pytest.raises(SessionRunRejected, match="one invocation"):
        asyncio.run(driver.run(probe=probe, grant=grant, on_action=execute))


def test_no_world_threat_wait_never_requests_action(tmp_path):
    driver, probe, grant, execute, _, _ = _fixture(tmp_path, two_events=False)
    called = []

    async def forbidden(step):
        called.append(step)
        raise AssertionError("WAIT invoked Action callback")

    result = asyncio.run(driver.run(probe=probe, grant=grant, on_action=forbidden))
    assert result["events"] == 1
    assert result["action_requests"] == 0
    assert result["closed_outcomes"] == 0
    assert result["terminal"] == "EVENT_BUDGET_ENDED"
    assert not called


def test_false_action_receipt_is_unknown_and_never_retried(tmp_path):
    driver, probe, grant, _, _, _ = _fixture(tmp_path)
    called = []

    async def unqualified(step):
        called.append(step.action_request_id)
        return {"fake": "success"}

    with pytest.raises(SessionRunRejected, match="unqualified S49"):
        asyncio.run(driver.run(probe=probe, grant=grant, on_action=unqualified))
    assert len(called) == 1
    rows = _events(tmp_path)
    assert [r["kind"] for r in rows][-2:] == [
        "action_outcome_unknown", "session_failed",
    ]
    assert rows[-2]["safe_to_replay"] is False
    assert rows[-1]["no_replay"] is True
    assert not any(r["kind"] == "action_outcome" for r in rows)


def test_stop_before_first_event_is_bounded_no_native_read(tmp_path):
    driver, probe, grant, execute, _, source = _fixture(tmp_path)
    driver.stop()
    result = asyncio.run(driver.run(probe=probe, grant=grant, on_action=execute))
    assert result["terminal"] == "OPERATOR_STOP"
    assert source.calls == 0
    assert result["events"] == result["closed_outcomes"] == 0


def test_paused_at_start_stops_on_wall_budget_without_invented_safety(tmp_path):
    driver, probe, grant, execute, _, source = _fixture(tmp_path)
    driver.pause()
    # Stop is an explicit operator signal; never a made-up native success.
    async def stop_from_operator():
        await asyncio.sleep(.05)
        driver.stop()
    async def trial():
        stopper = asyncio.create_task(stop_from_operator())
        result = await driver.run(probe=probe, grant=grant, on_action=execute)
        await stopper
        return result
    outcome = asyncio.run(trial())
    assert outcome["terminal"] == "OPERATOR_STOP"
    assert source.calls == 0
    assert outcome["action_requests"] == 0


def test_foreign_native_frame_is_rejected_before_grant_or_action(tmp_path):
    driver, probe, grant, execute, _, source = _fixture(tmp_path)
    source.frames[0] = replace(source.frames[0], session_id="other-world")
    with pytest.raises(SessionRunRejected, match="foreign native"):
        asyncio.run(driver.run(probe=probe, grant=grant, on_action=execute))
    assert driver.host.events == 0
    assert [x["kind"] for x in _events(tmp_path)] == [
        "session_started", "session_failed",
    ]


@pytest.mark.parametrize("bad", [
    {"max_events": 101}, {"max_actions": 0}, {"max_frames": 0},
    {"max_seconds": 0}, {"max_seconds": float("inf")},
    {"poll_seconds": 0}, {"max_events": True},
])
def test_unbounded_host_settings_are_rejected(bad):
    with pytest.raises(SessionRunRejected):
        SessionBudget(**bad)


def test_existing_event_feed_cannot_be_overwritten(tmp_path):
    path = tmp_path / "events.jsonl"
    path.write_text("immutable")
    with pytest.raises(SessionRunRejected):
        AppendOnlySessionEvents(path, "session")
    assert path.read_text() == "immutable"
    link = tmp_path / "link.jsonl"
    link.symlink_to(path)
    with pytest.raises(SessionRunRejected):
        AppendOnlySessionEvents(link, "session")
