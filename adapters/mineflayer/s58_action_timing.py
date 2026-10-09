"""S58 independently correlated per-Action monotonic timeline, append-only.

The start instant means "Python invoked previously admitted native Action
executor"; the terminal instant means "Python observed genuine World OUTCOME
receipt". Neither is the precise motor-issue instant / real movement onset.
"""
from __future__ import annotations

import hashlib
import json
import os
import time
from dataclasses import asdict, dataclass
from pathlib import Path


class ActionTimelineRejected(ValueError):
    """Action identity or clock, durable order, or native outcome denied."""


@dataclass(frozen=True, slots=True)
class ActionKey:
    session_id: str
    action_id: str
    grant_authority_id: str
    event_seq: int
    probe_seq: int
    entity_id: int

    def __post_init__(self) -> None:
        if (
            not all(
                isinstance(s, str) and 0 < len(s) <= 256
                for s in (self.session_id, self.action_id, self.grant_authority_id)
            )
            or type(self.event_seq) is not int
            or type(self.probe_seq) is not int
            or type(self.entity_id) is not int
            or self.event_seq < 0
            or self.probe_seq <= self.event_seq
            or self.entity_id <= 0
        ):
            raise ActionTimelineRejected("exact Action/session/World identity required")


class ActionTimingJournal:
    """Crash-aware 2-Action audit: every event flushed, fsynced, never overwritten."""

    def __init__(self, path: Path, *, session_id: str, max_actions: int = 2):
        if (
            not isinstance(path, Path) or not isinstance(session_id, str)
            or not session_id
            or type(max_actions) is not int or not 1 <= max_actions <= 16
        ):
            raise ActionTimelineRejected("one bounded local journal required")
        self.path = path
        self.session_id = session_id
        self.max_actions = max_actions
        self.started: dict[str, tuple[ActionKey, int]] = {}
        self.closed: dict[str, dict[str, object]] = {}
        self.incomplete: set[str] = set()
        self.used_grants: set[str] = set()
        path.parent.mkdir(parents=True, exist_ok=True)
        # Exclusive create prevents silently blending distinct native sessions.
        self._stream = path.open("x", encoding="utf-8")

    def _write(self, record: dict[str, object]) -> None:
        self._stream.write(json.dumps(record, sort_keys=True) + "\n")
        self._stream.flush()
        os.fsync(self._stream.fileno())

    def begin(self, key: ActionKey) -> None:
        if (
            not isinstance(key, ActionKey)
            or key.session_id != self.session_id
            or key.action_id in self.started
            or key.grant_authority_id in self.used_grants
            or len(self.started) >= self.max_actions
        ):
            raise ActionTimelineRejected("duplicate, foreign or over-budget physical Action")
        stamp = time.monotonic_ns()
        self._write({
            "schema": "relay-self.s58.action-timing.v1",
            "kind": "ACTION_EXECUTOR_INVOCATION",
            "clock": "host_monotonic_ns",
            "time_ns": stamp,
            "key": asdict(key),
        })
        self.started[key.action_id] = key, stamp
        self.used_grants.add(key.grant_authority_id)

    def outcome(
        self, key: ActionKey, *,
        terminal_action_id: str,
        terminal_outcome: bool,
        physical_movement_m: float,
        source_session_id: str,
    ) -> dict[str, object]:
        if (
            not isinstance(key, ActionKey)
            or key.action_id not in self.started
            or self.started[key.action_id][0] != key
            or key.action_id in self.closed or key.action_id in self.incomplete
            or terminal_action_id != key.action_id
            or terminal_outcome is not True
            or source_session_id != key.session_id
            or type(physical_movement_m) not in (int, float)
            or not 0.05 <= physical_movement_m <= 20
        ):
            raise ActionTimelineRejected("matching native physical OUTCOME required")
        now = time.monotonic_ns()
        start = self.started[key.action_id][1]
        if now <= start:
            raise ActionTimelineRejected("Action monotonic timeline regressed")
        record: dict[str, object] = {
            "schema": "relay-self.s58.action-timing.v1",
            "kind": "ACTION_TERMINAL_OUTCOME_OBSERVED",
            "clock": "host_monotonic_ns",
            "time_ns": now,
            "key": asdict(key),
            "physical_movement_m": physical_movement_m,
            "duration_ms": round((now - start) / 1_000_000, 3),
            "terminal": "outcome",
        }
        self._write(record)
        self.closed[key.action_id] = record
        return record

    def incomplete_action(self, key: ActionKey, *, error_type: str) -> None:
        if (
            not isinstance(key, ActionKey)
            or key.action_id not in self.started
            or self.started[key.action_id][0] != key
            or key.action_id in self.closed or key.action_id in self.incomplete
        ):
            raise ActionTimelineRejected("unmatched incomplete Action")
        if not isinstance(error_type, str) or not error_type.isidentifier():
            raise ActionTimelineRejected("only exception type is logged")
        self._write({
            "schema": "relay-self.s58.action-timing.v1",
            "kind": "ACTION_OUTCOME_NOT_OBSERVED",
            "clock": "host_monotonic_ns",
            "time_ns": time.monotonic_ns(),
            "key": asdict(key),
            "error_type": error_type,
        })
        self.incomplete.add(key.action_id)

    def summary(self, *, required: int = 2) -> dict[str, object]:
        if (
            type(required) is not int
            or required <= 0
            or len(self.started) != required
            or len(self.closed) != required
            or bool(self.incomplete)
        ):
            raise ActionTimelineRejected("two separately timed terminal Actions required")
        records = sorted(
            self.closed.values(), key=lambda record: record["time_ns"],
        )
        seen_events = [r["key"]["event_seq"] for r in records]
        if len(set(seen_events)) != required:
            raise ActionTimelineRejected("each Action requires distinct native World event")
        with self.path.open("rb") as stream:
            digest = hashlib.sha256(stream.read()).hexdigest()
        return {
            "schema": "relay-self.s58.action-timing.v1",
            "classification": "EVERY_NATIVE_ACTION_INVOCATION_AND_OUTCOME_TIMED",
            "action_count": required,
            "action_ids": [r["key"]["action_id"] for r in records],
            "action_durations_ms": [r["duration_ms"] for r in records],
            "native_event_seqs": seen_events,
            "sha256": digest,
            "clock": "host_monotonic_ns",
            "meaning": "executor invocation -> observed native terminal OUTCOME",
            "physical_issue_instant_known": False,
            "physical_movement_start_instant_known": False,
        }

    def close(self) -> None:
        self._stream.close()

    def __enter__(self) -> ActionTimingJournal:
        return self

    def __exit__(self, *args: object) -> None:
        self.close()
