"""S58 every-native-Action durable timings: synthetic UNIT tests, not physics."""
from __future__ import annotations

import asyncio
import json

import pytest

from adapters.mineflayer.s56_real_model_world_ci import qualify
from adapters.mineflayer.s58_action_timing import (
    ActionKey,
    ActionTimelineRejected,
    ActionTimingJournal,
)


def key(index: int) -> ActionKey:
    return ActionKey(
        session_id="one-native-session",
        action_id=f"issued-action-{index}",
        grant_authority_id=f"independent-grant-{index}",
        event_seq=index * 10 + 1,
        probe_seq=index * 10 + 2,
        entity_id=index + 7,
    )


def close_action(journal: ActionTimingJournal, action: ActionKey):
    journal.begin(action)
    return journal.outcome(
        action, terminal_action_id=action.action_id,
        terminal_outcome=True, physical_movement_m=0.6269065734210617,
        source_session_id=action.session_id,
    )


def test_all_actions_each_get_independent_monotonic_start_and_outcome(tmp_path):
    path = tmp_path / "native-timings.jsonl"
    with ActionTimingJournal(path, session_id="one-native-session") as journal:
        one = close_action(journal, key(1))
        two = close_action(journal, key(2))
        summary = journal.summary(required=2)
        assert one["time_ns"] < two["time_ns"]
        assert summary["action_ids"] == ["issued-action-1", "issued-action-2"]
        assert len(summary["action_durations_ms"]) == 2
        assert summary["physical_issue_instant_known"] is False
        assert summary["physical_movement_start_instant_known"] is False
        assert len(summary["sha256"]) == 64
    rows = [json.loads(line) for line in path.read_text().splitlines()]
    assert len(rows) == 4
    assert [r["kind"] for r in rows] == [
        "ACTION_EXECUTOR_INVOCATION", "ACTION_TERMINAL_OUTCOME_OBSERVED",
        "ACTION_EXECUTOR_INVOCATION", "ACTION_TERMINAL_OUTCOME_OBSERVED",
    ]
    assert len({r["key"]["entity_id"] for r in rows}) == 2
    assert all(r["key"]["session_id"] == "one-native-session" for r in rows)
    with pytest.raises(FileExistsError):
        ActionTimingJournal(path, session_id="one-native-session")


def test_second_action_without_separate_outcome_cannot_claim_all_actions(tmp_path):
    with ActionTimingJournal(
        tmp_path / "journal.jsonl", session_id="one-native-session",
    ) as journal:
        close_action(journal, key(1))
        journal.begin(key(2))
        with pytest.raises(ActionTimelineRejected):
            journal.summary(required=2)


def test_replay_action_id_or_independent_grant_denied(tmp_path):
    with ActionTimingJournal(
        tmp_path / "journal.jsonl", session_id="one-native-session",
    ) as journal:
        action = key(1)
        journal.begin(action)
        with pytest.raises(ActionTimelineRejected):
            journal.begin(action)
        grant_replay = ActionKey(
            session_id=action.session_id, action_id="other-action",
            grant_authority_id=action.grant_authority_id,
            event_seq=31, probe_seq=32, entity_id=9,
        )
        with pytest.raises(ActionTimelineRejected):
            journal.begin(grant_replay)


def test_wrong_terminal_id_world_source_and_nonphysical_distance_denied(tmp_path):
    with ActionTimingJournal(
        tmp_path / "journal.jsonl", session_id="one-native-session",
    ) as journal:
        action = key(1)
        journal.begin(action)
        for wrong_id, wrong_source, movement in [
            ("unrelated-action", action.session_id, 0.63),
            (action.action_id, "foreign-native-session", 0.63),
            (action.action_id, action.session_id, 0.0),
            (action.action_id, action.session_id, True),
        ]:
            with pytest.raises(ActionTimelineRejected):
                journal.outcome(
                    action, terminal_action_id=wrong_id,
                    terminal_outcome=True, physical_movement_m=movement,
                    source_session_id=wrong_source,
                )
        with pytest.raises(ActionTimelineRejected):
            journal.outcome(
                action, terminal_action_id=action.action_id,
                terminal_outcome=False, physical_movement_m=0.63,
                source_session_id=action.session_id,
            )


def test_wrong_session_or_world_sequence_denied(tmp_path):
    with pytest.raises(ActionTimelineRejected):
        ActionKey("sid", "action", "grant", 19, 18, 4)
    with ActionTimingJournal(
        tmp_path / "journal.jsonl", session_id="one-native-session",
    ) as journal:
        with pytest.raises(ActionTimelineRejected):
            journal.begin(ActionKey("another-session", "action", "grant", 2, 3, 4))


def test_fail_closed_incomplete_action_survives_crash_receipt(tmp_path):
    path = tmp_path / "journal.jsonl"
    with ActionTimingJournal(path, session_id="one-native-session") as journal:
        journal.begin(key(1))
        journal.incomplete_action(key(1), error_type="RuntimeError")
        with pytest.raises(ActionTimelineRejected):
            journal.summary(required=1)
        with pytest.raises(ActionTimelineRejected):
            journal.outcome(
                key(1), terminal_action_id=key(1).action_id,
                terminal_outcome=True, physical_movement_m=1.0,
                source_session_id=key(1).session_id,
            )
    rows = [json.loads(row) for row in path.read_text().splitlines()]
    assert rows[-1]["kind"] == "ACTION_OUTCOME_NOT_OBSERVED"
    assert "RuntimeError" == rows[-1]["error_type"]


def test_no_opt_in_local_model_fails_before_journal_or_action(tmp_path, monkeypatch):
    monkeypatch.delenv("S56_LOCAL_REAL_MODEL", raising=False)
    private = tmp_path / "timing.jsonl"
    report = tmp_path / "report.json"
    rc = asyncio.run(qualify(
        report, tmp_path / "minecraft.log",
        model="not-a-real-local-model",
        endpoint="http://127.0.0.1:1234/v1/chat/completions",
        gguf=tmp_path / "missing-model.gguf",
        expected_sha256="0" * 64,
        timeout_s=1, max_tokens=8, action_timing_jsonl=private,
    ))
    obj = json.loads(report.read_text())
    assert rc == 2 and obj["status"] == "BLOCKED"
    assert not private.exists()
    assert obj["actual_native_actions"] == []


def test_world_event_identity_unique_even_with_distinct_action_ids(tmp_path):
    with ActionTimingJournal(
        tmp_path / "journal.jsonl", session_id="one-native-session",
    ) as journal:
        close_action(journal, key(1))
        collision = ActionKey(
            session_id="one-native-session",
            action_id="independent-but-same-event",
            grant_authority_id="new-grant",
            event_seq=key(1).event_seq, probe_seq=key(1).probe_seq,
            entity_id=key(1).entity_id,
        )
        close_action(journal, collision)
        with pytest.raises(ActionTimelineRejected):
            journal.summary(required=2)
