"""S4 exact outer-source observability and #537 zero-decision regression.

Offline typed native fixtures only. The 181-frame reproduction is synthetic:
it is NOT a reconstruction of the sealed S2 run or the real World.
"""
from __future__ import annotations

import asyncio
import json
from dataclasses import replace
from types import SimpleNamespace

import pytest

import test_postmain_s42_world_contrast as s42
from adapters.mineflayer.normal_action import NormalWorldL0
from adapters.mineflayer.self_continuous_host import (
    AppendOnlySessionEvents,
    BoundedSessionDriver,
    SessionBudget,
)
from adapters.mineflayer.self_s4_observation import (
    ObservationAuditRejected,
    S4NativeObservationAudit,
)
from test_self_continuous_host import _fixture


def _non_target(frame, *, kind="health", seq=1):
    snapshot = replace(
        frame.snapshot,
        nearby_entities=(),
        nearby_entities_coverage=replace(
            frame.snapshot.nearby_entities_coverage, candidate_count=0,
        ),
    )
    return replace(frame, seq=seq, kind=kind, snapshot=snapshot)


def test_181_source_shaped_outer_frames_zero_decision_cannot_prove_world_absence(tmp_path):
    retained, _, _, event, _ = s42._pair()
    sid = event.session_id
    audit = S4NativeObservationAudit(sid, max_frames=181)
    budget = SessionBudget(
        max_events=12, max_actions=3, max_frames=181,
        max_seconds=5, poll_seconds=.02,
    )
    host = NormalWorldL0(sid, "escape-threat", retained,
                         max_events=12, max_action_requests=3)
    sink = AppendOnlySessionEvents(tmp_path / "events.jsonl", sid)

    class OriginalNativeSource:
        started = SimpleNamespace(session_id=sid)
        count = 0
        ignored_non_target_entities = 0
        ignored_duplicate_target_updates = 0
        ignored_hurt_frames = 0

        async def receive(self):
            self.count += 1
            return _non_target(event, kind="health", seq=self.count)

    original = OriginalNativeSource()
    driver = BoundedSessionDriver(host, original, budget, sink)

    async def forbidden_probe(*_):
        raise AssertionError("no correlated probe without original entity target")

    def forbidden_grant(*_):
        raise AssertionError("no grant without native source")

    result = asyncio.run(driver.run(
        probe=forbidden_probe, grant=forbidden_grant,
        on_action=forbidden_probe, observation_audit=audit,
    ))
    assert result["frames"] == 181
    assert result["events"] == result["action_requests"] == result["closed_outcomes"] == 0
    rows = [json.loads(x) for x in (tmp_path / "events.jsonl").read_text().splitlines()]
    assert [x["kind"] for x in rows] == [
        "session_started", "native_observation_audit", "session_terminal",
    ]
    a = rows[-2]
    assert a["classification"] == "NO_ZOMBIE_IN_OUTER_OBSERVED_SNAPSHOTS"
    assert a["accepted_outer_frames"] == 181
    assert a["outer_observation_kind_counts"] == {"health": 181}
    assert a["first_outer_source_seq"] == 1 and a["last_outer_source_seq"] == 181
    assert a["underlying_world_absence_proven"] is False
    assert a["all_native_decoded_messages_observed"] is False
    assert a["source_frames_archived_individually"] is False
    assert a["action_authority"] is False
    assert rows[-1]["terminal"] == "FRAME_BUDGET_ENDED"


def test_zombie_seen_in_non_entity_snapshot_does_not_fake_decision(tmp_path):
    retained, _, _, event, _ = s42._pair()
    sid = event.session_id
    host = NormalWorldL0(sid, "escape-threat", retained,
                         max_events=1, max_action_requests=1)
    source = SimpleNamespace(
        started=SimpleNamespace(session_id=sid),
    )
    source.receive = lambda: asyncio.sleep(0, result=replace(event, kind="health", seq=3))
    driver = BoundedSessionDriver(
        host, source, SessionBudget(max_events=1, max_actions=1, max_frames=1,
                                    max_seconds=2, poll_seconds=.02),
        AppendOnlySessionEvents(tmp_path / "events.jsonl", sid),
    )
    audit = S4NativeObservationAudit(sid, max_frames=1)

    async def forbidden(*_):
        raise AssertionError("not an eligible entity event")

    def no_grant(*_):
        raise AssertionError("not an Action candidate")

    result = asyncio.run(driver.run(
        probe=forbidden, grant=no_grant, on_action=forbidden,
        observation_audit=audit,
    ))
    assert result["events"] == 0
    rows = [json.loads(x) for x in (tmp_path / "events.jsonl").read_text().splitlines()]
    a = rows[-2]
    assert a["classification"] == "ZOMBIE_ONLY_IN_NON_ENTITY_SNAPSHOTS"
    assert a["non_entity_frames_with_zombie"] == 1
    assert a["entity_frames_with_zombie"] == 0
    assert a["s49_decisions"] == 0


def test_qualified_original_s49_decisions_and_action_remain_unchanged(tmp_path):
    driver, probe, grant, execute, _, source = _fixture(tmp_path)
    audit = S4NativeObservationAudit(driver.host.session_id,
                                     max_frames=driver.budget.max_frames)
    result = asyncio.run(driver.run(
        probe=probe, grant=grant, on_action=execute,
        observation_audit=audit,
    ))
    assert result["events"] == 2
    assert result["action_requests"] == result["closed_outcomes"] == 1
    rows = [json.loads(x) for x in (tmp_path / "events.jsonl").read_text().splitlines()]
    a = rows[-2]
    assert a["classification"] == "S49_DECISION_PATH_ENTERED"
    assert a["entity_frames_with_zombie"] == 2
    assert a["accepted_outer_frames"] == 2
    assert a["action_authority"] is False


def test_foreign_replay_and_unbounded_source_fail_closed():
    _, _, _, event, _ = s42._pair()
    audit = S4NativeObservationAudit(event.session_id, max_frames=1)
    with pytest.raises(ObservationAuditRejected):
        audit.observe(replace(event, session_id="other"))
    audit.observe(replace(event, seq=3))
    with pytest.raises(ObservationAuditRejected):
        audit.observe(replace(event, seq=3))
    with pytest.raises(ObservationAuditRejected):
        audit.observe(replace(event, seq=4))
    with pytest.raises(ObservationAuditRejected):
        S4NativeObservationAudit("", max_frames=1)


def test_no_archive_retroactive_old_run_not_reclassified():
    """Old #597 summary lacks all 181 individual decoded frame details."""
    audit = S4NativeObservationAudit("prior-s2-session", max_frames=500)
    result = audit.report(object(), decisions=0)
    assert result["classification"] == "NO_OUTER_NATIVE_OBSERVATIONS"
    assert result["accepted_outer_frames"] == 0
    assert not result["underlying_world_absence_proven"]
